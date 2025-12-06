import os
import time
import textwrap
import re
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
        self.asked_questions = [] 
        self.max_retries = 3 

    def get_logistics_question(self, logistic_type):
        """Retrieves specific Logistics card."""
        query = f"Tribe: Logistics - {logistic_type}"
        results = vector_db.similarity_search(query, k=3)
        for doc in results:
            content = doc.page_content
            if f"Logistics - {logistic_type}" in content and "Next Question:" in content:
                try:
                    parts = content.split("Next Question:")
                    return parts[1].strip().split("\n")[0].replace('"', '')
                except: continue
        
        if logistic_type == "Budget": return "What is your budget?"
        if logistic_type == "Time": return "When are you free?"
        return "Where do you want to go?"

    def get_personality_question(self, user_input):
        """Finds a NEW question to ask."""
        # Use a broad search to find relevant tribes
        results = vector_db.similarity_search(f"Tribe keywords: {user_input}", k=10)
        
        for doc in results:
            content = doc.page_content
            if "Logistics" in content: continue

            if "Next Question:" in content:
                try:
                    parts = content.split("Next Question:")
                    question = parts[1].strip().split("\n")[0].replace('"', '')
                    
                    if question not in self.asked_questions:
                        self.asked_questions.append(question)
                        return question
                except: continue
        
        # Fallback question if DB runs dry
        return "Do you prefer high-energy social events or quiet, intimate gatherings?"

    def retrieve_events(self, full_context, k=3):
        results = vector_db.similarity_search(f"Event details: {full_context}", k=k)
        events = []
        for doc in results:
            if "Event:" in doc.page_content:
                events.append(doc.page_content)
        return events

    def force_broad_search(self, full_context):
        """Emergency broad search."""
        results = vector_db.similarity_search(full_context, k=50)
        events = []
        for doc in results:
            if "Event:" in doc.page_content:
                events.append(doc.page_content)
        
        if not events:
            # Absolute fallback
            fallback = vector_db.similarity_search("Event:", k=5)
            return [doc.page_content for doc in fallback if "Event:" in doc.page_content][:2]
            
        return events[:2]

    def extract_category(self, event_text):
        """Helper to check consistency."""
        try:
            match = re.search(r"Category:\s*(.*)", event_text)
            if match: return match.group(1).strip()
        except: return "Unknown"
        return "Unknown"

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

    def run_persistent_loop(self):
        print("\n" + "█"*60)
        print(" 📱 SOCIALSYNC: The Anti-Loneliness Agent")
        print("    (Type 'exit' to quit)")
        print("█"*60 + "\n")

        user_input = input("🤖 SOCIALSYNC: Hi! I'm here to help you find your people.\n   Tell me what you're looking for (e.g. 'I want to relax')\n\n👤 YOU: ")
        if user_input.lower() in ['exit', 'quit']: return
        self.context_memory = user_input

        # --- PHASE 1: MANDATORY QUESTIONS ---
        mandatory_phases = [
            ("Personality", lambda: self.get_personality_question(self.context_memory)),
            ("Time",        lambda: self.get_logistics_question("Time")),
            ("Location",    lambda: self.get_logistics_question("Location")),
            ("Budget",      lambda: self.get_logistics_question("Budget"))
        ]

        for phase_name, question_func in mandatory_phases:
            print(f"\n   ⚙️  [System: Analyzing {phase_name} Preference...]")
            time.sleep(0.3)
            
            question = question_func()
            if question:
                print(f"\n🤖 SOCIALSYNC: {question}")
                ans = input("\n👤 YOU: ")
                self.context_memory += f" {ans}"

        # --- PHASE 2: CONFIDENCE & REFINEMENT LOOP ---
        retries = 0
        final_events = []

        while True:
            print("\n" + "▒"*60)
            print("🏁  CHECKING MATCH CONFIDENCE...")
            print("▒"*60)

            # 1. Get Events
            final_events = self.retrieve_events(self.context_memory, k=2)

            # 2. Check if we have results
            if len(final_events) < 1:
                print("   [DEBUG: 0 Matches found. Needs refinement.]")
                is_confident = False
            
            # 3. Check Consistency (Do the categories match?)
            elif len(final_events) >= 2:
                cat1 = self.extract_category(final_events[0])
                cat2 = self.extract_category(final_events[1])
                print(f"   [DEBUG: Match 1 is '{cat1}', Match 2 is '{cat2}']")
                
                if cat1 == cat2:
                    print("   [DEBUG: Confidence High. Categories Match.]")
                    is_confident = True
                else:
                    print("   [DEBUG: Confidence Low. Mixed Categories.]")
                    is_confident = False
            else:
                # Only 1 result found, pretty confident by default
                is_confident = True

            # 4. DECISION: Stop or Ask?
            if is_confident:
                break # Exit Loop
            
            if retries >= self.max_retries:
                print("\n⚠️  [System: Max retries reached. Forcing best available matches...]")
                if not final_events:
                    final_events = self.force_broad_search(self.context_memory)
                break

            # 5. ASK FOLLOW-UP
            retries += 1
            print(f"\n   [DEBUG: Asking clarification question ({retries}/{self.max_retries})...]")
            time.sleep(1)
            
            new_q = self.get_personality_question(self.context_memory)
            
            print(f"\n🤖 SOCIALSYNC: I want to be sure I find the right fit. \n   {new_q}")
            ans = input("\n👤 YOU: ")
            self.context_memory += f" {ans}"

        # --- SHOW RESULTS ---
        if final_events:
            for i, event in enumerate(final_events):
                self.pretty_print_event(event, i+1)
        else:
            print("\n❌ System Error: No events could be retrieved.")

if __name__ == "__main__":
    agent = SocialSyncAgent()
    agent.run_persistent_loop()