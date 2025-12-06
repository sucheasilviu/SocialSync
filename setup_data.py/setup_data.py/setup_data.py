import sqlite3
import requests
from bs4 import BeautifulSoup
import os
import time
import json
from openai import OpenAI 

# --- CONFIGURARE ---
# PUNE AICI CHEIA TA (cea pe care mi-ai dat-o mai devreme)
API_KEY = ""
FOLDER_TEXTE = "data_raw"
NUME_DB = "events.db"

# LINK-URI SPECIFICE (Nu folosi homepages, ci pagini de categorii/liste pentru rezultate mai bune)
urls_de_procesat = [
    "https://www.iabilet.ro/bilete-in-bucuresti/",
    "https://zilesinopti.ro/evenimente-bucuresti/concerte-bucuresti/",
    "https://www.onevent.ro/orase/bucuresti/",
]

# Inițializare Client OpenAI
client = OpenAI(api_key=API_KEY)

# ==============================================================================
# PARTEA 1: DATA ENGINEERING (Scraping + Creare Bază de Date)
# ==============================================================================

def setup_db():
    conn = sqlite3.connect(NUME_DB)
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS evenimente")
    cursor.execute("""
        CREATE TABLE evenimente (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nume_eveniment TEXT,
            pret REAL,
            data_ora TEXT,
            locuri_disponibile INTEGER,
            categorie TEXT,
            sursa_url TEXT
        )
    """)
    conn.commit()
    return conn

def extract_structured_data(text_articol):
    """ 
    MODIFICARE CRITICĂ: Cere o LISTĂ de evenimente, nu doar unul.
    """
    system_prompt = """
    Ești un expert în Data Mining. Analizează textul primit (care este o pagină web cu liste de evenimente).
    Extrage TOATE evenimentele distincte pe care le găsești.
    
    Trebuie să răspunzi DOAR cu un obiect JSON valid care conține o listă sub cheia "evenimente".
    
    Formatul cerut:
    {
        "evenimente": [
            {
                "nume": "Titlu eveniment",
                "pret": number (doar cifra, ex: 50. pune 0 daca e gratis sau nu scrie),
                "data": "YYYY-MM-DD HH:MM" (estimează anul curent, încearcă să găsești data exactă),
                "categorie": "Concert/Teatru/Standup/Altceva"
            },
            ... mai multe evenimente ...
        ]
    }
    """
    
    # Trimitem doar primele 12.000 caractere (GPT-4o-mini duce mai mult context acum)
    # ca să prindem mai multe evenimente din listă.
    user_message = f"Analizează acest text brut de pe site și scoate lista de evenimente:\n{text_articol[:12000]}"
    
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
        return {"evenimente": []}

def run_ingestion_process():
    if not os.path.exists(FOLDER_TEXTE):
        os.makedirs(FOLDER_TEXTE)

    conn = setup_db()
    cursor = conn.cursor()
    
    print(f"\n--- 1. Încep Descărcarea și Analiza ({len(urls_de_procesat)} link-uri) ---")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for url in urls_de_procesat:
        try:
            print(f"   -> Procesez: {url}...")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                print("      [!] Link inaccesibil.")
                continue
            
            # --- RAG (Text Cleaning) ---
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Eliminăm scripturile și stilurile care încurcă AI-ul
            for script in soup(["script", "style"]):
                script.extract()
                
            titlu_pag = soup.find('h1').get_text().strip() if soup.find('h1') else "Lista Evenimente"
            
            # Extragem textul curat
            text_body = soup.get_text(separator="\n")
            # Eliminăm liniile goale excesive
            lines = [line.strip() for line in text_body.splitlines() if line.strip()]
            full_text = "\n".join(lines)
            
            # Salvare Text (pentru RAG)
            nume_fisier = "raw_" + "".join([c if c.isalnum() else "_" for c in titlu_pag[:15]]) + ".txt"
            with open(os.path.join(FOLDER_TEXTE, nume_fisier), "w", encoding="utf-8") as f:
                f.write(f"Sursa: {url}\n\n{full_text}")

            # --- SQL (AI Extraction - LISTĂ) ---
            print("      [AI] OpenAI caută evenimente în text...")
            json_data = extract_structured_data(full_text)
            
            evenimente_gasite = json_data.get("evenimente", [])
            
            if not evenimente_gasite:
                print("      [!] AI-ul nu a găsit evenimente structurate aici.")
            
            count = 0
            for ev in evenimente_gasite:
                # Validare simplă
                if ev.get("nume") and ev.get("pret") is not None:
                    cursor.execute("""
                        INSERT INTO evenimente (nume_eveniment, pret, data_ora, locuri_disponibile, categorie, sursa_url)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        ev.get("nume"),
                        ev.get("pret"),
                        ev.get("data", "N/A"),
                        50, # Punem default 50 locuri că e greu de scos de pe site-uri de listă
                        ev.get("categorie", "General"),
                        url
                    ))
                    count += 1
            
            print(f"      [OK] Au fost inserate {count} evenimente din acest link.")

        except Exception as e:
            print(f"      [!] Eroare la {url}: {e}")

    conn.commit()
    conn.close()
    print("[GATA] Baza de date a fost populată masiv!\n")

# ==============================================================================
# PARTEA 2: LOGIC & CHAT (Rămâne neschimbată, funcționează perfect)
# ==============================================================================

def get_sql_from_openai(user_question):
    schema = """
    Tabel 'evenimente': id, nume_eveniment, pret, data_ora, locuri_disponibile, categorie, sursa_url
    """
    prompt = f"""
    Transformă întrebarea userului în SQL (SQLite).
    Schema: {schema}
    Reguli: DOAR codul SQL. Folosește LIKE '%...%'.
    Întrebare: "{user_question}"
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
        conn = sqlite3.connect(NUME_DB)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return "Nu am găsit evenimente conform criteriilor."
        
        raspuns = "Găsit în baza de date:\n"
        for row in results:
            raspuns += f"- {row[1]} | {row[2]} RON | {row[3]} | {row[5]}\n"
        return raspuns
    except Exception as e:
        return f"Eroare interogare: {e}"

def send_email_simulation(destinatar):
    print(f"\n   📧 [EMAIL] Trimis către {destinatar}. Rezervare confirmată.")
    return "Confirmarea a fost trimisă!"

if __name__ == "__main__":
    print("=== TRIBES AI - UPDATED DATA ENGINE ===")
    optiune = input("Actualizezi datele? (da/nu): ").lower()
    
    if optiune in ["da", "y"]:
        run_ingestion_process()
    
    print("\nRobotul e gata. Vorbește cu el.")
    while True:
        user = input("\nTu: ")
        if user in ["exit", "pa"]: break
        
        if "email" in user or "rezerv" in user:
            send_email_simulation(input("Emailul tau: "))
        else:
            print(f"AI: {execute_query_and_respond(user)}")