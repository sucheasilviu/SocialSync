import sqlite3
import requests
from bs4 import BeautifulSoup
import os
import time
import json
from openai import OpenAI 

# --- CONFIGURATION ---
# PLEASE PUT YOUR API KEY HERE
API_KEY = "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" 

DATA_FOLDER = "data_raw"
DB_NAME = "events.db"

# SPECIFIC LINKS (Using category pages for better results)
urls_to_process = [
    "https://www.iabilet.ro/bilete-in-bucuresti/",
    "https://zilesinopti.ro/evenimente-bucuresti/concerte-bucuresti/",
    "https://www.onevent.ro/orase/bucuresti/",
]

# Initialize OpenAI Client
client = OpenAI(api_key=API_KEY)

# ==============================================================================
# PART 1: DATA ENGINEERING (Scraping + Database Creation)
# ==============================================================================

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
    CRITICAL MODIFICATION: Asks for a LIST of events, not just one.
    """
    system_prompt = """
    You are an expert in Data Mining. Analyze the provided text (which is a web page containing lists of events).
    Extract ALL distinct events you can find.
    
    You must respond ONLY with a valid JSON object containing a list under the key "events".
    
    Required Format:
    {
        "events": [
            {
                "name": "Event Title",
                "price": number (just the number, e.g., 50. put 0 if free or not found),
                "date": "YYYY-MM-DD HH:MM" (estimate current year, try to find exact date),
                "category": "Concert/Theater/Standup/Other"
            },
            ... more events ...
        ]
    }
    """
    
    # Send only the first 12,000 chars to fit context window
    user_message = f"Analyze this raw website text and extract the list of events:\n{raw_text[:12000]}"
    
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

def run_ingestion_process():
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

    conn = setup_db()
    cursor = conn.cursor()
    
    print(f"\n--- 1. Starting Download and Analysis ({len(urls_to_process)} links) ---")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for url in urls_to_process:
        try:
            print(f"   -> Processing: {url}...")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print("      [!] Link inaccessible.")
                continue
            
            # --- RAG (Text Cleaning) ---
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove scripts and styles that confuse the AI
            for script in soup(["script", "style"]):
                script.extract()
                
            page_title = soup.find('h1').get_text().strip() if soup.find('h1') else "Event List"
            
            # Extract clean text
            text_body = soup.get_text(separator="\n")
            # Remove excessive empty lines
            lines = [line.strip() for line in text_body.splitlines() if line.strip()]
            full_text = "\n".join(lines)
            
            # Save Text (for RAG context)
            file_name = "raw_" + "".join([c if c.isalnum() else "_" for c in page_title[:15]]) + ".txt"
            with open(os.path.join(DATA_FOLDER, file_name), "w", encoding="utf-8") as f:
                f.write(f"Source: {url}\n\n{full_text}")

            # --- SQL (AI Extraction - LIST) ---
            print("      [AI] OpenAI is looking for events in the text...")
            json_data = extract_structured_data(full_text)
            
            found_events = json_data.get("events", [])
            
            if not found_events:
                print("      [!] AI found no structured events here.")
            
            count = 0
            for ev in found_events:
                # Simple validation
                if ev.get("name") and ev.get("price") is not None:
                    cursor.execute("""
                        INSERT INTO events (event_name, price, date_time, available_seats, category, source_url)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        ev.get("name"),
                        ev.get("price"),
                        ev.get("date", "N/A"),
                        50, # Defaulting to 50 seats as it's hard to scrape real-time availability
                        ev.get("category", "General"),
                        url
                    ))
                    count += 1
            
            print(f"      [OK] Inserted {count} events from this link.")

        except Exception as e:
            print(f"      [!] Error at {url}: {e}")

    conn.commit()
    conn.close()
    print("[DONE] Database has been massively populated!\n")

# ==============================================================================
# PART 2: LOGIC & CHAT (Text-to-SQL & Email)
# ==============================================================================

def get_sql_from_openai(user_question):
    schema = """
    Table 'events': id, event_name, price, date_time, available_seats, category, source_url
    """
    prompt = f"""
    Transform the user's question into a SQL query (SQLite).
    Schema: {schema}
    Rules: Return ONLY the SQL code. Use LIKE '%...%' for text searches.
    Question: "{user_question}"
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return response.choices[0].message.content.replace("```sql", "").replace("```", "").strip()

def execute_query_and_respond(user_input):
    sql_query = get_sql_from_openai(user_input)
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return "I couldn't find any events matching your criteria."
        
        response = "Found in database:\n"
        for row in results:
            # row[1] is name, row[2] is price, etc.
            response += f"- {row[1]} | {row[2]} RON | {row[3]} | {row[5]}\n"
        return response
    except Exception as e:
        return f"Query Error: {e}"

def send_email_simulation(recipient):
    print(f"\n   📧 [EMAIL] Sent to {recipient}. Reservation confirmed.")
    return "The confirmation has been sent!"

if __name__ == "__main__":
    print("=== TRIBES AI - ENGLISH VERSION ===")
    option = input("Update data from the web? (yes/no): ").lower()
    
    if option in ["da", "yes", "y"]:
        run_ingestion_process()
    
    print("\nThe Robot is ready. Talk to it.")
    while True:
        user = input("\nYou: ")
        if user.lower() in ["exit", "bye", "stop"]: 
            print("Tribes AI: Goodbye!")
            break
        
        if "email" in user.lower() or "reserve" in user.lower() or "book" in user.lower():
            email_addr = input("Tribes AI: Sure, what is your email? ")
            send_email_simulation(email_addr)
        else:
            print(f"Tribes AI: {execute_query_and_respond(user)}")