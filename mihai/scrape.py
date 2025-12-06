import sqlite3
import requests
from bs4 import BeautifulSoup
import os
import json
import re
from urllib.parse import urljoin
from openai import OpenAI
from dotenv import load_dotenv

# --- CONFIGURATION ---
load_dotenv(dotenv_path="./.env")

if not os.getenv("OPENAI_API_KEY"):
    raise ValueError("ERROR: OPENAI_API_KEY not found in .env file")

API_KEY = os.getenv("OPENAI_API_KEY")
DATA_FOLDER = "data_raw"
DB_NAME = "events.db"
OUTPUT_TXT_FILE = os.path.join(DATA_FOLDER, "scraped_events.txt")

# LINKS TO SCRAPE
urls_to_process = [
    "https://www.iabilet.ro/bilete-in-bucuresti/",
    "https://zilesinopti.ro/evenimente-bucuresti/",
    "https://ticketstore.ro/ro/oras/Bucuresti",
    "https://berariah.ro/",
]

client = OpenAI(api_key=API_KEY)

def setup_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS events")
    cursor.execute("""
        CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_name TEXT,
            price REAL,
            date_time TEXT,
            available_seats INTEGER,
            category TEXT,
            source_url TEXT
        )
    """)
    conn.commit()
    return conn

def extract_structured_data(raw_text):
    """
    FIXED: Explicitly mentions 'JSON' to satisfy OpenAI API requirements.
    """
    system_prompt = """
    You are a Data Miner. Extract events from the provided text.
    
    OUTPUT MUST BE A VALID JSON OBJECT.
    
    CRITICAL RULES:
    1. LINKS: The text contains links in the format '[URL: http...]'. 
       You MUST extract this specific URL for the event. Do NOT use the generic source URL.
    2. PRICES: Look for 'RON', 'Lei', 'Bilet', 'Pret'. 
       - If a range (e.g., '50-100 RON'), use the LOWEST number (50).
       - If 'Free', 'Intrare libera', use 0.
       - If no price is found, estimate based on context or put 0.
    
    Required JSON Structure:
    {
        "events": [
            {
                "name": "Event Title",
                "price": number,
                "date": "YYYY-MM-DD HH:MM",
                "location": "Venue Name",
                "category": "Concert/Theater/Party/Workshop",
                "description": "Short summary (max 15 words)",
                "event_url": "The specific [URL: ...] you found next to the title"
            }
        ]
    }
    """
    
    user_message = f"Analyze this text and extract events:\n{raw_text[:14000]}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            response_format={"type": "json_object"}, 
            temperature=0.1
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"   [OpenAI Error] {e}")
        return {"events": []}

def append_to_txt_file(event_data, main_source_url):
    name = event_data.get("name", "Unknown")
    cat = event_data.get("category", "General")
    desc = event_data.get("description", "No description available.")
    date = event_data.get("date", "Upcoming")
    loc = event_data.get("location", "Bucharest")
    
    # Handle Price Display
    price_val = event_data.get("price", 0)
    if price_val == 0:
        price_str = "Free / Check Link"
    else:
        price_str = f"{price_val} RON"

    # Use specific URL if found, else fallback to main list
    specific_url = event_data.get("event_url")
    if not specific_url or "http" not in specific_url:
        specific_url = main_source_url

    entry = f"""Event: {name}
Category: {cat}
Description: {desc}
Target Audience: General.
Date: {date}
Location: {loc}
Cost: {price_str}
Source: {specific_url}

------------------------------------------------

"""
    with open(OUTPUT_TXT_FILE, "a", encoding="utf-8") as f:
        f.write(entry)

def preprocess_html(html_content, base_url):
    """
    Injects URLs directly into the visible text so GPT can see them.
    Turns <a href="/xyz">Event</a> into "Event [URL: https://base.com/xyz]"
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # 1. Remove noise
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.extract()

    # 2. LINK INJECTION
    count = 0
    for a in soup.find_all('a', href=True):
        href = a['href']
        # Clean relative URLs
        full_url = urljoin(base_url, href)
        
        # Only inject if it looks like an event link
        if len(a.get_text(strip=True)) > 3: 
            new_text = f"{a.get_text(strip=True)} [URL: {full_url}] "
            a.string = new_text
            count += 1

    print(f"      [Pre-Process] Injected {count} URLs into text stream.")
    
    text = soup.get_text(separator="\n")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)

def run_ingestion_process():
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
    
    if os.path.exists(OUTPUT_TXT_FILE):
        os.remove(OUTPUT_TXT_FILE)

    conn = setup_db()
    cursor = conn.cursor()
    
    print(f"\n--- 🌍 STARTING SMART SCRAPER ({len(urls_to_process)} sites) ---")
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'}

    for url in urls_to_process:
        print(f"   🔗 Scraping: {url}...")
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                print("      [!] Failed to connect.")
                continue
            
            clean_text_with_links = preprocess_html(response.content, url)
            
            print("      [AI] Extracting structured data...")
            json_data = extract_structured_data(clean_text_with_links)
            found_events = json_data.get("events", [])
            
            if not found_events:
                print("      [!] No events found.")
                continue

            count = 0
            for ev in found_events:
                if ev.get("name"):
                    # SQL (Student 1)
                    cursor.execute("""
                        INSERT INTO events (event_name, price, date_time, available_seats, category, source_url)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        ev.get("name"), 
                        ev.get("price", 0), 
                        ev.get("date"), 
                        50, 
                        ev.get("category"), 
                        ev.get("event_url", url)
                    ))
                    
                    # TXT (Student 2 - RAG)
                    append_to_txt_file(ev, url)
                    count += 1
            
            print(f"      [OK] Successfully saved {count} events.")

        except Exception as e:
            print(f"      [Error] {e}")

    conn.commit()
    conn.close()
    print(f"\n✅ SCRAPING COMPLETE.")
    print("👉 Now run 'python ingest.py'!")

if __name__ == "__main__":
    run_ingestion_process()