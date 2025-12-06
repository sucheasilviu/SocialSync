# backend/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Any
from fastapi.middleware.cors import CORSMiddleware
from rag_logic import SocialSyncAgent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

app = FastAPI()

# Allow React to talk to this server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], # React's default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global store for demo purposes (In production, use a database/Redis)
# This maps a "session_id" to an agent instance.
sessions = {}

class ChatRequest(BaseModel):
    message: str
    session_id: str

class EventData(BaseModel):
    title: str
    date: str
    location: str
    cost: str
    description: str
    url: str

class ChatResponse(BaseModel):
    text: str
    events: List[EventData] = []
    mission_complete: bool = False

def parse_event_text(raw_text):
    """Parses the raw text block from ChromaDB into a structured dict."""
    lines = raw_text.split('\n')
    info = {}
    for line in lines:
        if ": " in line:
            key, val = line.split(": ", 1)
            info[key.strip()] = val.strip()
    
    return EventData(
        title=info.get("Event", "Unknown"),
        date=info.get("Date", "TBD"),
        location=info.get("Location", "Check Link"),
        cost=info.get("Cost", "Free"),
        description=info.get("Description", ""),
        url=info.get("Source", "#")
    )

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    # 1. Get or Create Agent
    if req.session_id not in sessions:
        sessions[req.session_id] = SocialSyncAgent()
    
    agent = sessions[req.session_id]
    
    # 2. Add User Message to History
    agent.chat_history.append(HumanMessage(content=req.message))
    
    # 3. Initial LLM Call
    ai_response = agent.llm.invoke(agent.chat_history)
    ai_text = ai_response.content
    
    events_to_return = []
    final_text = ai_text
    mission_complete = False

    # 4. Logic Loop (Search / Complete)
    if "SEARCH_ACTION" in ai_text.upper():
        # --- Handle Search ---
        clean_text = ai_text.replace("**SEARCH_ACTION:**", "SEARCH_ACTION:")
        query = clean_text.split("SEARCH_ACTION:")[1].strip() if "SEARCH_ACTION:" in clean_text else clean_text
        
        # Retrieve raw strings
        raw_events = agent.retrieve_events(query, k=3)
        
        # Convert raw strings to Structured Data for React
        events_to_return = [parse_event_text(e) for e in raw_events]
        
        # Agent Follow-up
        if events_to_return:
            agent.chat_history.append(AIMessage(content="SEARCH_EXECUTED"))
            agent.chat_history.append(SystemMessage(content="SYSTEM: Events found. Ask user for feedback."))
            follow_up = agent.llm.invoke(agent.chat_history)
            final_text = follow_up.content
            agent.chat_history.append(follow_up)
        else:
            final_text = "I couldn't find any events matching that. Could you refine your request?"
            
    elif "MISSION_COMPLETE" in ai_text:
        final_text = "Mission Complete! Have a great time! 🎉"
        mission_complete = True
    else:
        # Standard Chat
        agent.chat_history.append(ai_response)

    return ChatResponse(
        text=final_text, 
        events=events_to_return, 
        mission_complete=mission_complete
    )

@app.post("/reset")
async def reset_chat(req: ChatRequest):
    sessions[req.session_id] = SocialSyncAgent()
    return {"status": "reset"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)