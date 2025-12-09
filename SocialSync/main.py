from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
from rag_logic import SocialSyncAgent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
import json
import os
from email_service import send_event_email

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATABASE ---
DB_FILE = "users.json"
users_db = {}

if os.path.exists(DB_FILE):
    with open(DB_FILE, "r") as f:
        users_db = json.load(f)

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(users_db, f, indent=2)

# --- MODELS ---

class AuthRequest(BaseModel):
    email: str          
    password: str
    name: Optional[str] = None 

class ChatRequest(BaseModel):
    message: str
    session_id: str
    email: Optional[str] = None 

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
    new_vibe: Optional[str] = None 

class EmailRequest(BaseModel):
    email: str
    event: EventData

# --- SESSION STORE ---
sessions = {}

# --- AUTH ENDPOINTS ---
@app.post("/register")
async def register(req: AuthRequest):
    if req.email in users_db:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    users_db[req.email] = {
        "password": req.password,
        "name": req.name or req.email.split("@")[0], 
        "profile": "" 
    }
    save_db()
    
    return {
        "status": "success", 
        "email": req.email, 
        "name": users_db[req.email]["name"],
        "profile": ""
    }

@app.post("/login")
async def login(req: AuthRequest):
    user = users_db.get(req.email)
    if not user or user["password"] != req.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    return {
        "status": "success", 
        "email": req.email, 
        "name": user["name"], 
        "profile": user["profile"]
    }

# --- CHAT ENDPOINTS ---

def parse_event_text(raw_text):
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

def strip_command_from_text(text):
    lines = text.split('\n')
    clean_lines = [line for line in lines if "SEARCH_ACTION" not in line.upper()]
    return "\n".join(clean_lines).strip()

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    # Initialize Session
    if req.session_id not in sessions:
        agent = SocialSyncAgent()
        
        # --- INJECT EXISTING VIBE ---
        if req.email and req.email in users_db:
            user_profile = users_db[req.email]["profile"]
            if user_profile:
                # We inject this as soft context
                agent.chat_history.append(SystemMessage(content=f"""
                [USER CONTEXT]
                The user has previously enjoyed: "{user_profile}".
                Use this to guide your tone, but don't obsess over it.
                """))
        
        sessions[req.session_id] = {
            "agent": agent,
            "seen_events": set()
        }
    
    session_data = sessions[req.session_id]
    agent = session_data["agent"]
    agent.chat_history.append(HumanMessage(content=req.message))
    
    # --- RESTORED CHILL PERSONA (With Stop Condition) ---
    reminder_msg = SystemMessage(content="""
    [PERSONA INSTRUCTIONS]
    You are SocialSync. Your goal is to be a helpful, excited friend who finds events.
    
    1. **Start with the VIBE.** Focus on what they feel like doing (mood, activity, energy).
    2. **Collect Details Naturally.** If you need Location/Time/Budget, ask for them casually in conversation, or assume reasonable defaults if the user is vague.
    3. **Don't be robotic.** Avoid checklists. Just chat.
    4. **Search when ready.** If you have a good idea of what they want, output 'SEARCH_ACTION'.
    
    [CRITICAL STOP CONDITION]:
    IF the user confirms they like an event (e.g., "I'll go to that", "Perfect", "That works", "Sounds good"):
    1. CELEBRATE their choice. 🥳
    2. DO NOT ask more questions.
    3. DO NOT output 'SEARCH_ACTION'.
    4. DO NOT offer more options unless they explicitly ask "what else?".
    Just say something like: "Awesome choice! Have a blast! 🎆" and stop.
    """)
    
    agent.chat_history.append(reminder_msg)
    
    ai_response = agent.llm.invoke(agent.chat_history)
    ai_text = ai_response.content
    
    # Remove reminder to save context window
    if agent.chat_history and agent.chat_history[-1] == reminder_msg:
        agent.chat_history.pop()

    events_to_return = []
    final_text = ai_text
    mission_complete = False
    new_vibe_detected = None 

    # --- 0. SATISFACTION CHECK (PRE-FILTER) ---
    # Detect if AI is celebrating a successful choice
    is_celebrating = "HAVE" in ai_text.upper() or "GREAT" in ai_text.upper() or "ENJOY" in ai_text.upper() or "AWESOME" in ai_text.upper()
    is_offering_more = "SEARCH_ACTION" in ai_text.upper() or "MORE" in ai_text.upper() or "?" in ai_text

    if is_celebrating and not is_offering_more:
         mission_complete = True

    # --- MAIN LOGIC LOOP ---
    elif "SEARCH_ACTION" in ai_text.upper():
        clean_text_for_parsing = ai_text.replace("**SEARCH_ACTION:**", "SEARCH_ACTION:")
        if "SEARCH_ACTION:" in clean_text_for_parsing:
            query = clean_text_for_parsing.split("SEARCH_ACTION:")[1].strip()
        else:
            query = clean_text_for_parsing.replace("SEARCH_ACTION", "").strip()
        
        raw_events = agent.retrieve_events(query)
        
        new_events = []
        for raw in raw_events:
            if raw not in session_data["seen_events"]:
                new_events.append(raw)
        
        events_to_show = new_events[:2]
        
        for ev in events_to_show:
            session_data["seen_events"].add(ev)

        events_to_return = [parse_event_text(e) for e in events_to_show]
        
        if events_to_return:
            agent.chat_history.append(AIMessage(content="SEARCH_EXECUTED"))
            
            if len(session_data["seen_events"]) > 2:
                sys_msg = "SYSTEM: You just showed 2 MORE events. Briefly ask if these are better."
            else:
                sys_msg = "SYSTEM: You just showed the first 2 options. Briefly ask for thoughts."
            
            agent.chat_history.append(SystemMessage(content=sys_msg))
            follow_up = agent.llm.invoke(agent.chat_history)
            final_text = follow_up.content
            agent.chat_history.append(follow_up)
            
            mission_complete = True
            
        else:
            final_text = "I've run out of new events matching that vibe! Should we try a different category?"

    else:
        # Standard conversation response
        agent.chat_history.append(ai_response)
        final_text = ai_text

    # --- AGGRESSIVE INCREMENTAL VIBE ASSESSMENT ---
    # This runs on EVERY TURN to capture updates immediately.
    if req.email and req.email in users_db:
        try:
            # Step A: Filter for relevant info
            # We explicitly ask it to ignore logistics to keep the vibe pure.
            vibe_check_prompt = SystemMessage(content=f"""
            [SYSTEM ANALYSIS]
            Analyze the USER'S last message: "{req.message}"
            
            Does this message provide ANY hint about their personality, tastes, or mood?
            (e.g., "I like jazz", "Something chill", "Not a fan of crowds", "I want to dance")
            
            Ignore purely logistic messages like "NYC" or "Tomorrow".
            
            Answer ONLY "YES" or "NO".
            """)
            
            # Check context
            check_messages = agent.chat_history[:-1] + [vibe_check_prompt] 
            check_response = agent.llm.invoke(check_messages)
            
            should_update = "YES" in check_response.content.strip().upper()

            if should_update:
                # Step B: Create Database Entry
                assessment_prompt = SystemMessage(content="""
                [ACTION: DATABASE ENTRY]
                Role: DATA ANALYST (Not a chatbot).
                Task: Update the user's "Taste Profile" based on the conversation so far.
                
                RULES:
                1. Write 1 concise sentence summarizing their general tastes/personality.
                2. DO NOT include Location/Time/Budget.
                3. DO NOT use conversational language. Be factual.
                
                Example: "Enjoys low-key acoustic music and outdoor markets."
                """)
                
                agent.chat_history.append(assessment_prompt)
                summary_response = agent.llm.invoke(agent.chat_history)
                new_vibe_detected = summary_response.content.replace('"', '').strip()
                
                users_db[req.email]["profile"] = new_vibe_detected
                save_db()
                
                agent.chat_history.pop() 
                print(f"Profile Updated: {new_vibe_detected}")

        except Exception as e:
            print(f"Failed to update vibe: {e}")

    final_text = strip_command_from_text(final_text)

    return ChatResponse(
        text=final_text, 
        events=events_to_return, 
        mission_complete=mission_complete,
        new_vibe=new_vibe_detected 
    )

@app.post("/reset")
async def reset_chat(req: ChatRequest):
    if req.session_id in sessions:
        del sessions[req.session_id]
    return {"status": "reset"}

@app.post("/send-event-email")
async def send_event_email_endpoint(req: EmailRequest):
    if not req.email or "@" not in req.email:
         raise HTTPException(status_code=400, detail="Valid email required")
    
    success, message = send_event_email(req.email, req.event.dict())
    
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {message}")
        
    return {"status": "success", "message": "Ticket info sent to your inbox!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)