import os
import time
import textwrap
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# --- SETUP ---
load_dotenv(dotenv_path="./.env")
DB_PATH = "./chroma_db"

import warnings
warnings.filterwarnings("ignore")

print("\n🔋 SOCIALSYNC: Powering up Agentic Core...")
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vector_db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7) 

print("✅ SOCIALSYNC: Online.")

class SocialSyncAgent:
    def __init__(self):
        self.system_prompt = """
        You are SocialSync, an empathetic AI assistant helping lonely people find social events in Bucharest.
        
        PHASE 1: GATHER INFO
        Ask conversational questions to determine:
        1. Vibe (Active, Chill, Techy, etc.)
        2. Timing
        3. Location
        4. Budget
        
        PHASE 2: SEARCH
        When you have enough info, output exactly: "SEARCH_ACTION: [summary of preferences]"
        
        PHASE 3: CLOSING
        After results are shown, the system will tell you. Then ask the user if they are happy.
        - If YES/THANKS: Output exactly "MISSION_COMPLETE".
        - If NO: Ask what they want to change.
        """
        self.chat_history = [SystemMessage(content=self.system_prompt)]

    def retrieve_events(self, search_query, k=3):
        print(f"   [DEBUG: Agent triggered search for: '{search_query}']")
        results = vector_db.similarity_search(f"Event: {search_query}", k=k)
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
                # Limit split to 1 to handle URLs with colons (http://...)
                key, val = line.split(": ", 1)
                info[key.strip()] = val.strip()

        title = info.get("Event", "Unknown Event")
        date = info.get("Date", "See details")
        loc = info.get("Location", "TBD")
        cost = info.get("Cost", "Free")
        desc = info.get("Description", "")
        # NEW: Extract Source URL
        url = info.get("Source", "No Link Available")
        
        wrapped_desc = textwrap.fill(desc, width=50)
        indented_desc = wrapped_desc.replace('\n', '\n      ')
        
        print(f"\n   🏆 MATCH #{rank}: {title.upper()}")
        print(f"   {'═'*50}")
        print(f"   📅  WHEN:  {date}")
        print(f"   📍  WHERE: {loc}")
        print(f"   💰  COST:  {cost}")
        print(f"   🔗  LINK:  {url}") # Now printing the URL
        print(f"   {'─'*50}")
        print(f"   📝  DETAILS:\n      {indented_desc}")
        print(f"   {'═'*50}\n")

    def run_agentic_loop(self):
        print("\n" + "█"*60)
        print(" 📱 SOCIALSYNC: AI-Powered Agent")
        print("    (Type 'exit' to quit)")
        print("█"*60 + "\n")

        print("🤖 SOCIALSYNC: Hi! I'm here to connect you with your tribe. Tell me, what's on your mind?")

        while True:
            user_input = input("\n👤 YOU: ")
            if user_input.lower() in ['exit', 'quit']: break
            
            self.chat_history.append(HumanMessage(content=user_input))
            print("   ⚙️  [SocialSync is thinking...]")
            
            ai_response_msg = llm.invoke(self.chat_history)
            ai_text = ai_response_msg.content

            if "SEARCH_ACTION:" in ai_text:
                search_query = ai_text.split("SEARCH_ACTION:")[1].strip()
                print("\n" + "▒"*60)
                print(f"🏁  AGENT DECISION: Searching for '{search_query}'...")
                print("▒"*60)
                
                events = self.retrieve_events(search_query, k=2)
                
                if events:
                    for i, event in enumerate(events):
                        self.pretty_print_event(event, i+1)
                    
                    self.chat_history.append(AIMessage(content="SEARCH_ACTION_EXECUTED"))
                    self.chat_history.append(SystemMessage(content="SYSTEM: Results showed to user. Ask them if they like these."))
                    
                    follow_up = llm.invoke(self.chat_history)
                    print(f"\n🤖 SOCIALSYNC: {follow_up.content}")
                    self.chat_history.append(follow_up)
                else:
                    print("\n❌ No exact matches found. Searching broadly...")
                    broad_events = self.retrieve_events(search_query, k=50)
                    if broad_events:
                         self.pretty_print_event(broad_events[0], 1)
                    else:
                         print("Sorry, nothing found.")
                    
                    self.chat_history.append(SystemMessage(content="SYSTEM: No results found. Ask user to refine."))
                    follow_up = llm.invoke(self.chat_history)
                    print(f"\n🤖 SOCIALSYNC: {follow_up.content}")
                    self.chat_history.append(follow_up)

            elif "MISSION_COMPLETE" in ai_text:
                print("\n" + "█"*60)
                print("✨  SocialSync: Glad I could help! Go have fun!  ✨")
                print("█"*60 + "\n")
                break 

            else:
                print(f"\n🤖 SOCIALSYNC: {ai_text}")
                self.chat_history.append(ai_response_msg)

if __name__ == "__main__":
    agent = SocialSyncAgent()
    agent.run_agentic_loop()