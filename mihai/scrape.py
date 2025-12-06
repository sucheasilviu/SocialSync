import sqlite3
import requests
from bs4 import BeautifulSoup
import os
import json
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
    "https://www.onevent.ro/orase/bucuresti/",
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
    UPDATED PROMPT: Now asks for 'location' explicitly.
    """
    system_prompt = """
    You are a Data Miner. Extract events from the text.
    Return a valid JSON object with a list under "events".
    Format:
    {
        "events": [
            {
                "name": "Event Title",
                "price": number (0 if free),
                "date": "YYYY-MM-DD HH:MM",
                "location": "Venue Name (e.g. Hard Rock Cafe)",
                "category": "Concert/Theater/Party/Workshop",
                "description": "Short summary (max 20 words)"
            }
        ]
    }
    """
    
    user_message = f"Analyze this text and extract events:\n{raw_text[:12000]}"
    
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

def append_to_txt_file(event_data, url):
    name = event_data.get("name", "Unknown")
    cat = event_data.get("category", "General")
    desc = event_data.get("description", "No description available.")
    date = event_data.get("date", "Upcoming")
    price = f"{event_data.get('price', 0)} RON"
    
    # FIXED: Actually use the extracted location
    loc = event_data.get("location", "Bucharest (See Link)")
    
    entry = f"""Event: {name}
Category: {cat}
Description: {desc}
Target Audience: General.
Date: {date}
Location: {loc}
Cost: {price}
Source: {url}

------------------------------------------------

"""
    with open(OUTPUT_TXT_FILE, "a", encoding="utf-8") as f:
        f.write(entry)

def run_ingestion_process():
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)
    
    if os.path.exists(OUTPUT_TXT_FILE):
        os.remove(OUTPUT_TXT_FILE)

    conn = setup_db()
    cursor = conn.cursor()
    
    print(f"\n--- 🌍 STARTING WEB SCRAPER ({len(urls_to_process)} sites) ---")
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'}

    for url in urls_to_process:
        print(f"   🔗 Scraping: {url}...")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print("      [!] Failed to connect.")
                continue
            
            soup = BeautifulSoup(response.content, 'html.parser')
            for script in soup(["script", "style"]): script.extract()
            text_body = soup.get_text(separator="\n")
            
            print("      [AI] Extracting data with GPT-4o-mini...")
            json_data = extract_structured_data(text_body)
            found_events = json_data.get("events", [])
            
            if not found_events:
                print("      [!] No events found.")
                continue

            count = 0
            for ev in found_events:
                if ev.get("name"):
                    cursor.execute("""
                        INSERT INTO events (event_name, price, date_time, available_seats, category, source_url)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (ev.get("name"), ev.get("price"), ev.get("date"), 50, ev.get("category"), url))
                    
                    append_to_txt_file(ev, url)
                    count += 1
            
            print(f"      [OK] Processed {count} events.")

        except Exception as e:
            print(f"      [Error] {e}")

    conn.commit()
    conn.close()
    print(f"\n✅ SCRAPING COMPLETE.")
    print("👉 Now run 'python ingest.py' to update the brain!")

if __name__ == "__main__":
    run_ingestion_process()