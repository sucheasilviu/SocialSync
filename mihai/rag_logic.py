import os
import time
import textwrap
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# --- SETUP ---
load_dotenv(dotenv_path="./.env")
DB_PATH = "./chroma_db"

import warnings
warnings.filterwarnings("ignore")

print("\n🔋 SOCIALSYNC: Powering up Neural Engine...")
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vector_db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
print("✅ SOCIALSYNC: Online.")

class SocialSyncAgent:
    def __init__(self):
        self.context_memory = ""
        self.turn_count = 1
        self.max_turns = 4
        self.asked_questions = [] 

    def retrieve_profile_question(self, current_context):
        # --- PHASE 1: PERSONALITY (Use RAG) ---
        if self.turn_count == 1:
            print("   [DEBUG: Phase 1 - Matching Personality via RAG]")
            search_query = f"Tribe Personality Keywords: {current_context}"
            results = vector_db.similarity_search(search_query, k=5)
            
            for doc in results:
                content = doc.page_content
                if "Next Question:" in content:
                    try:
                        parts = content.split("Next Question:")
                        question = parts[1].strip().split("\n")[0].replace('"', '')
                        if question not in self.asked_questions:
                            self.asked_questions.append(question)
                            return question
                    except:
                        continue
            # If RAG fails to find a specific vibe, return a generic one
            return "Do you prefer quiet, creative activities or loud, energetic ones?"

        # --- PHASE 2: TIME (Fail-Safe Mode) ---
        elif self.turn_count == 2:
            print("   [DEBUG: Phase 2 - Force Logic: Time]")
            # We TRY to get it from DB to prove RAG works...
            results = vector_db.similarity_search("Logistics Time Preference", k=3)
            for doc in results:
                if "Logistics - Time" in doc.page_content and "Next Question:" in doc.page_content:
                     parts = doc.page_content.split("Next Question:")
                     return parts[1].strip().split("\n")[0].replace('"', '')
            
            # ...But if DB fails, we FORCE this question:
            return "Do you prefer an event happening on a weeknight (after work), or on the weekend?"

        # --- PHASE 3: BUDGET (Fail-Safe Mode) ---
        elif self.turn_count == 3:
            print("   [DEBUG: Phase 3 - Force Logic: Budget]")
            # We TRY to get it from DB...
            results = vector_db.similarity_search("Logistics Budget Cost", k=3)
            for doc in results:
                # Relaxed check: just look for 'Budget' in the text
                if "Budget" in doc.page_content and "Next Question:" in doc.page_content:
                     parts = doc.page_content.split("Next Question:")
                     return parts[1].strip().split("\n")[0].replace('"', '')

            # ...But if DB fails, we FORCE this question:
            return "Are you looking for a strictly free event, or are you willing to pay for a ticket/class?"
        
        return None

    def retrieve_events(self, current_context, k=3):
        # We use the full accumulated context to find the events
        results = vector_db.similarity_search(f"Event details: {current_context}", k=k)
        events = []
        for doc in results:
            if "Event:" in doc.page_content:
                events.append(doc.page_content)
        return events

    def pretty_print_event(self, raw_text, rank):
        lines = raw_text.split('\n')
        info = {}
        for line in lines:
            if ": " in line:
                key, val = line.split(": ", 1)
                info[key.strip()] = val.strip()

        title = info.get("Event", "Unknown Event")
        date = info.get("Date", "See details")
        loc = info.get("Location", "TBD")
        cost = info.get("Cost", "Free")
        desc = info.get("Description", "")
        
        wrapped_desc = textwrap.fill(desc, width=50)
        indented_desc = wrapped_desc.replace('\n', '\n      ')
        
        print(f"\n   🏆 MATCH #{rank}: {title.upper()}")
        print(f"   {'═'*50}")
        print(f"   📅  WHEN:  {date}")
        print(f"   📍  WHERE: {loc}")
        print(f"   💰  COST:  {cost}")
        print(f"   {'─'*50}")
        print(f"   📝  DETAILS:\n      {indented_desc}")
        print(f"   {'═'*50}\n")

    def run_narrowing_loop(self):
        print("\n" + "█"*60)
        print(" 📱 SOCIALSYNC: The Anti-Loneliness Agent")
        print("    (Type 'exit' to quit)")
        print("█"*60 + "\n")

        user_input = input("🤖 SOCIALSYNC: Hi! I'm here to help you find your people.\n   Tell me what you're looking for (e.g. 'I want to relax')\n\n👤 YOU: ")
        
        if user_input.lower() in ['exit', 'quit']: return

        self.context_memory = user_input

        while True:
            print(f"\n   ⚙️  [System: Analyzing Phase {self.turn_count} data...]")
            time.sleep(0.5)

            next_question = self.retrieve_profile_question(self.context_memory)
            
            # Logic: Continue asking until we hit max turns
            if self.turn_count <= 3 and next_question:
                print(f"\n🤖 SOCIALSYNC: {next_question}")
                
                answer = input("\n👤 YOU: ")
                if answer.lower() in ['exit', 'quit']: break
                
                self.context_memory += f" {answer}"
                self.turn_count += 1
            
            else:
                print("\n" + "▒"*60)
                print("🏁  CALCULATING BEST SOCIAL MATCHES...")
                print("▒"*60)
                
                events = self.retrieve_events(self.context_memory, k=2)
                
                if events:
                    for i, event in enumerate(events):
                        self.pretty_print_event(event, i+1)
                else:
                    print("\n❌ No exact matches found. Try being more specific!")
                break

if __name__ == "__main__":
    agent = SocialSyncAgent()
    agent.run_narrowing_loop()