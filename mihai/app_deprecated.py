import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from rag_logic import SocialSyncAgent

# --- PAGE CONFIG ---
st.set_page_config(page_title="SocialSync AI", page_icon="🤝", layout="centered")

# --- CUSTOM CSS ---
# We use Flexbox here (.event-container) so events align side-by-side
# automatically, both in the live view and in the history.
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .event-container {
        display: flex;
        flex-wrap: wrap;
        gap: 15px;
        width: 100%;
        margin-bottom: 15px;
    }
    .event-card {
        flex: 1;
        min-width: 280px; /* Ensures cards don't get too squashed on mobile */
        background-color: #f0f2f6;
        border-left: 5px solid #ff4b4b;
        padding: 15px;
        border-radius: 5px;
        color: #31333F;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .event-title {
        font-weight: bold;
        font-size: 1.1em;
        color: #000;
        margin-bottom: 5px;
    }
    a {
        text-decoration: none;
        color: #ff4b4b !important;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# --- SIDEBAR ---
with st.sidebar:
    st.title("SocialSync 🤝")
    st.info("**Mission:** Connect you with local events using Agentic AI.")
    if st.button("Reset Conversation", type="primary"):
        st.session_state.agent = SocialSyncAgent()
        st.session_state.messages = []
        st.session_state.mission_complete = False
        st.rerun()

# --- INITIALIZATION ---
if "agent" not in st.session_state:
    st.session_state.agent = SocialSyncAgent()

if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hi! I'm SocialSync. I'm here to connect you with your tribe. Tell me, what's on your mind?", "is_html": False}
    ]

if "mission_complete" not in st.session_state:
    st.session_state.mission_complete = False

# --- HELPER: HTML GENERATOR ---
def generate_event_html(events):
    """
    Combines multiple events into a SINGLE HTML string using Flexbox.
    This ensures they render side-by-side in history without needing st.columns.
    """
    html_buffer = '<div class="event-container">'
    
    for raw_text in events:
        lines = raw_text.split('\n')
        info = {}
        for line in lines:
            if ": " in line:
                key, val = line.split(": ", 1)
                info[key.strip()] = val.strip()

        title = info.get("Event", "Unknown Event")
        date = info.get("Date", "TBD")
        loc = info.get("Location", "Check URL")
        cost = info.get("Cost", "Free")
        url = info.get("Source", "#")
        desc = info.get("Description", "")

        card = f"""
        <div class="event-card">
            <div class="event-title">🏆 {title}</div>
            <p>📅 <b>When:</b> {date}<br>📍 <b>Where:</b> {loc}</p>
            <p>💰 <b>Cost:</b> {cost}</p>
            <p>📝 <i>{desc}</i></p>
            <br>
            <a href="{url}" target="_blank">🔗 View Event Details</a>
        </div>
        """
        html_buffer += card
    
    html_buffer += '</div>'
    return html_buffer

# --- 1. RENDER CHAT HISTORY ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        # ALWAYS use unsafe_allow_html=True if the flag is set
        # This prevents the raw HTML code from showing up
        if msg.get("is_html"):
            st.markdown(msg["content"], unsafe_allow_html=True)
        else:
            st.markdown(msg["content"])

# --- 2. MISSION COMPLETE (Bottom Button) ---
if st.session_state.mission_complete:
    st.markdown("---")
    st.success("🎉 **Mission Complete!**")
    if st.button("🔄 Start New Search", key="restart_bottom"):
        st.session_state.agent = SocialSyncAgent()
        st.session_state.messages = [{"role": "assistant", "content": "Hi! I'm SocialSync. I'm here to connect you with your tribe. Tell me, what's on your mind?", "is_html": False}]
        st.session_state.mission_complete = False
        st.rerun()

# --- 3. ACTIVE CHAT LOGIC ---
if not st.session_state.mission_complete:
    if prompt := st.chat_input("Type your answer..."):
        
        # A. Render User Message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        st.session_state.messages.append({"role": "user", "content": prompt, "is_html": False})
        st.session_state.agent.chat_history.append(HumanMessage(content=prompt))

        # B. Generate Response
        with st.chat_message("assistant"):
            final_content_to_display = ""
            is_html_response = False
            
            with st.spinner("Thinking..."):
                
                # Call Brain
                ai_response = st.session_state.agent.llm.invoke(st.session_state.agent.chat_history)
                ai_text = ai_response.content
                
                # --- LOGIC BRANCHING ---
                
                # BRANCH 1: SEARCH ACTION
                if "SEARCH_ACTION" in ai_text.upper():
                    try:
                        clean_text = ai_text.replace("**SEARCH_ACTION:**", "SEARCH_ACTION:")
                        if "SEARCH_ACTION:" in clean_text:
                            search_query = clean_text.split("SEARCH_ACTION:")[1].strip()
                        else:
                            search_query = clean_text 
                        
                        st.caption(f"🔎 Searching database for: '{search_query}'...")
                        
                        # Search
                        events = st.session_state.agent.retrieve_events(search_query, k=2)
                        
                        # Fallback
                        if not events:
                            st.caption("⚠️ Expanding search criteria...")
                            events = st.session_state.agent.retrieve_events(search_query, k=50)
                            if events: events = [events[0]]

                        # Build Output
                        if events:
                            # 1. Generate the HTML Grid
                            events_html = generate_event_html(events)
                            
                            # 2. Get Follow-up Text
                            st.session_state.agent.chat_history.append(AIMessage(content="SEARCH_EXECUTED"))
                            st.session_state.agent.chat_history.append(SystemMessage(content="SYSTEM: Results shown. Ask the user if they like these."))
                            follow_up = st.session_state.agent.llm.invoke(st.session_state.agent.chat_history)
                            
                            # 3. Combine HTML + Text
                            final_content_to_display = events_html + f"<br><br>{follow_up.content}"
                            is_html_response = True
                            
                            st.session_state.agent.chat_history.append(follow_up)
                        
                        else:
                            # No events found
                            error_msg = "❌ No matches found."
                            st.session_state.agent.chat_history.append(SystemMessage(content="SYSTEM: No results found. Ask user to refine."))
                            follow_up = st.session_state.agent.llm.invoke(st.session_state.agent.chat_history)
                            
                            final_content_to_display = f"{error_msg}\n\n{follow_up.content}"
                            is_html_response = False # Simple text fallback
                            st.session_state.agent.chat_history.append(follow_up)

                    except Exception as e:
                        final_content_to_display = f"Search Error: {e}"
                        is_html_response = False

                # BRANCH 2: MISSION COMPLETE
                elif "MISSION_COMPLETE" in ai_text:
                    st.balloons()
                    final_content_to_display = "Mission Complete! Have fun out there! 🎉"
                    is_html_response = False
                    st.session_state.mission_complete = True

                # BRANCH 3: STANDARD CHAT
                else:
                    final_content_to_display = ai_text
                    is_html_response = False
                    st.session_state.agent.chat_history.append(ai_response)

            # --- RENDER ONCE ---
            # This is the single point of truth for rendering. 
            # We never print earlier. We print exactly here.
            st.markdown(final_content_to_display, unsafe_allow_html=is_html_response)
            
            # --- SAVE TO HISTORY ---
            st.session_state.messages.append({
                "role": "assistant", 
                "content": final_content_to_display, 
                "is_html": is_html_response
            })

            # Force Button Appearance immediately if mission complete
            if st.session_state.mission_complete:
                 st.rerun()