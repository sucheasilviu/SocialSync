import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import EventCard from './components/EventCard';
import Sidebar from './components/Sidebar';
import AuthModal from './components/AuthModal';
import { Send, Bot, User, LogIn, LogOut, Database, Mail } from 'lucide-react'; // Added Mail

const SESSION_ID = "user-session-1";

function App() {

  // --- EMAIL HANDLER ---
  const handleEmailEvent = async (event) => {
    let targetEmail = user ? user.email : null;

    // If not logged in, ask for email manually
    if (!targetEmail) {
      targetEmail = prompt("Where should we send this event? Enter your email:");
    }

    if (!targetEmail || !targetEmail.includes('@')) {
      alert("Please provide a valid email.");
      return;
    }

    try {
      // Optimistic UI update (optional: you could add a loading state here)
      alert(`Sending ${event.title} to ${targetEmail}...`);

      const response = await fetch('http://localhost:8000/send-event-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: targetEmail,
          event: event
        })
      });

      const data = await response.json();
      if (data.status === 'success') {
        alert("Email sent successfully! 📬");
      } else {
        alert("Failed to send email.");
      }
    } catch (error) {
      console.error("Email error:", error);
      alert("Something went wrong sending the email.");
    }
  };

  // --- USER STATE ---
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem("socialsync_user");
    return saved ? JSON.parse(saved) : null;
  });
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  
  // --- DEBUG STATE (Hidden by default) ---
  const [showDebug, setShowDebug] = useState(false);

  // --- MESSAGES STATE ---
  const [messages, setMessages] = useState(() => {
    const saved = localStorage.getItem("chat_history");
    if (saved) {
      return JSON.parse(saved);
    } else {
      return [
        { 
          role: 'assistant', 
          text: "Hey there! 👋 I'm SocialSync. I'm here to help you find your people. No pressure — just tell me, what’s your vibe lately?", 
          events: [] 
        }
      ];
    }
  });

  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    localStorage.setItem("chat_history", JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    if (user) localStorage.setItem("socialsync_user", JSON.stringify(user));
    else localStorage.removeItem("socialsync_user");
  }, [user]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  useEffect(scrollToBottom, [messages]);

  useEffect(() => {
    if (!isLoading && !isComplete) {
      inputRef.current?.focus();
    }
  }, [isLoading, isComplete]);

  // --- RESET LOGIC ---
  const handleReset = async (overriddenUser = undefined) => {
    localStorage.removeItem("chat_history");

    const activeUser = (overriddenUser !== undefined && overriddenUser?.type !== 'click') 
        ? overriddenUser 
        : user;

    await fetch('http://localhost:8000/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: "", session_id: SESSION_ID })
    });
    
    let greeting = "Hey there! 👋 I'm SocialSync. I'm here to help you find your people. No pressure — just tell me, what’s your vibe lately?";

    if (activeUser) {
        greeting = `Welcome back, ${activeUser.name}! 👋 Ready for another adventure? Tell me what you're in the mood for today.`;
    }

    setMessages([{ 
      role: 'assistant', 
      text: greeting, 
      events: [] 
    }]);
    
    setIsComplete(false);
    setIsLoading(false);
  };

  // --- AUTH HANDLERS ---
  const handleLoginSuccess = (userData) => {
    setUser(userData);
    handleReset(userData);
  };

  const handleLogout = () => {
    setUser(null);
    handleReset(null);
  };

  // --- CHAT HANDLERS ---
  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg = { role: 'user', text: input };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            message: userMsg.text, 
            session_id: SESSION_ID,
            email: user ? user.email : null 
        })
      });

      const data = await response.json();
      
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: data.text,
        events: data.events
      }]);

      if (data.mission_complete) setIsComplete(true);

      // --- LIVE VIBE UPDATE ---
      if (data.new_vibe && user) {
        setUser(prevUser => ({
            ...prevUser,
            profile: data.new_vibe
        }));
      }

    } catch (error) {
      console.error("Error:", error);
      setMessages(prev => [...prev, { role: 'assistant', text: "Sorry, I'm having trouble connecting to the brain." }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-900 font-sans text-gray-100 relative">
      
      {/* --- INVISIBLE DEBUG TOGGLE (Top Right Corner) --- */}
      <div 
        onClick={() => setShowDebug(!showDebug)}
        className="absolute top-0 right-0 w-8 h-8 z-50 cursor-pointer opacity-0 hover:bg-red-500/10 transition-colors"
        title="Toggle Debug"
      />

      <Sidebar onReset={() => handleReset()} />

      <div className="flex-1 flex flex-col max-w-5xl mx-auto w-full bg-gray-900 h-screen relative">
        
        {/* --- LIVE VIBE DISPLAY (Conditional) --- */}
        {user && showDebug && (
           <div className="absolute top-4 left-6 z-10 hidden md:block opacity-90 transition-opacity group cursor-default">
              <div className="flex items-center gap-2 text-xs font-bold text-emerald-500 uppercase tracking-wider mb-1">
                 <Database size={10} />
                 <span>AI Memory</span>
              </div>
              <div className="text-xs text-gray-400 font-mono bg-gray-800/90 p-2 rounded border border-gray-700 max-w-xs shadow-sm backdrop-blur-sm">
                  {user.profile ? `"${user.profile}"` : "No vibe detected yet..."}
              </div>
           </div>
        )}

        {/* --- AUTH BUTTON --- */}
        <div className="absolute top-4 right-6 z-10">
          {user ? (
             <div className="flex items-center gap-3 bg-gray-800 border border-gray-700 rounded-full px-4 py-2 shadow-lg">
                <div className="flex items-center gap-2">
                    <div className="w-6 h-6 bg-blue-600 rounded-full flex items-center justify-center text-xs font-bold">
                        {user.name ? user.name[0].toUpperCase() : 'U'}
                    </div>
                    <span className="text-sm font-medium text-gray-200">{user.name}</span>
                </div>
                <button 
                    onClick={handleLogout}
                    className="text-gray-400 hover:text-red-400 transition-colors border-l border-gray-600 pl-3"
                    title="Log Out"
                >
                    <LogOut size={16} />
                </button>
             </div>
          ) : (
            <button
              onClick={() => setIsAuthOpen(true)}
              className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600 text-white text-sm font-semibold px-5 py-2.5 rounded-full shadow-lg hover:shadow-xl transition-all transform hover:scale-105 active:scale-95"
            >
              <LogIn size={16} />
              <span>Login / Join</span>
            </button>
          )}
        </div>

        {/* --- AUTH MODAL --- */}
        <AuthModal 
            isOpen={isAuthOpen} 
            onClose={() => setIsAuthOpen(false)} 
            onLogin={handleLoginSuccess} 
        />

        {/* Messages List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar pt-24">
          {messages.map((msg, idx) => {
            const isEventMessage = msg.role === 'assistant' && msg.events && msg.events.length > 0;
            return (
              <div key={idx} className={`flex w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`flex max-w-[85%] gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                  
                  <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                    msg.role === 'user' 
                      ? 'bg-blue-600' 
                      : isEventMessage ? 'bg-emerald-600' : 'bg-gray-700' 
                  }`}>
                    {msg.role === 'user' ? <User size={18} /> : <Bot size={18} />}
                  </div>

                  <div className={`rounded-2xl py-2 px-4 shadow-md border ${
                    msg.role === 'user' 
                      ? 'bg-blue-600 text-white border-blue-500' 
                      : isEventMessage
                        ? 'bg-gray-800 text-gray-100 border-2 border-emerald-600/50' 
                        : 'bg-gray-800 text-gray-100 border border-gray-700' 
                    }`}
                  >
                    <div className="prose prose-invert prose-sm max-w-none mb-1">
                      <ReactMarkdown>{msg.text}</ReactMarkdown>
                    </div>
                    {msg.events && msg.events.length > 0 && (
                      <div className="flex flex-wrap gap-4 mt-3 w-full">
                        {msg.events.map((event, i) => (
                          <div 
                            key={i} 
                            // CHANGE: flex-1 allows cards to grow, min-w prevents squishing
                            className="flex flex-col gap-0 flex-1 min-w-[300px] max-w-full md:max-w-[48%]" 
                          >
                            {/* Force EventCard to fill the wrapper width */}
                            <div className="w-full h-full [&>div]:w-full [&>div]:h-full">
                              <EventCard event={event} />
                            </div>

                            {/* The Email Button - styled to attach to the bottom of the card */}
                            <button 
                              onClick={() => handleEmailEvent(event)}
                              className="flex items-center justify-center gap-2 w-full py-3 bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white 
                                        border-x border-b border-gray-700 hover:border-gray-600 rounded-b-xl text-xs font-semibold 
                                        uppercase tracking-wider transition-all mt-[-4px] z-0 relative"
                            >
                              <Mail size={14} />
                              <span>Email Details</span>
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
          
          {isLoading && (
            <div className="flex justify-start w-full">
               <div className="flex gap-3 max-w-[85%]">
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center">
                    <Bot size={18} className="text-gray-400 animate-pulse" />
                  </div>
                  <div className="bg-gray-800 border border-gray-700 text-gray-400 rounded-2xl py-2 px-4 flex items-center gap-2">
                      <span className="animate-pulse">Checking the airwaves...</span>
                  </div>
               </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-gray-800 bg-gray-800">
            <div className="flex items-center gap-3">
              <input
                ref={inputRef}
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Type your answer..."
                className="flex-1 py-2 px-6 bg-gray-900 border border-gray-700 text-white rounded-full focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent placeholder-gray-500 shadow-inner transition-all"
                disabled={isLoading}
                autoFocus
              />
              
              <button 
                onClick={handleSend}
                disabled={isLoading}
                className="flex-shrink-0 w-10 h-10 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-full flex items-center justify-center hover:from-blue-500 hover:to-blue-600 hover:scale-110 active:scale-95 disabled:opacity-50 transition-all shadow-lg hover:shadow-xl"
              >
                <Send size={18} className="-ml-0.5 mt-0.5" />
              </button>
            </div>
        </div>
      </div>
    </div>
  );
}

export default App;