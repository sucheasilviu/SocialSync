import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import EventCard from './components/EventCard';
import { Send, RefreshCw, Bot } from 'lucide-react';

const SESSION_ID = "user-session-1"; // Simple session ID

function App() {
  const [messages, setMessages] = useState([
    { role: 'assistant', text: "Hi! I'm SocialSync. I'm here to connect you with your tribe. Tell me, what's on your mind?", events: [] }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isComplete, setIsComplete] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

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
        body: JSON.stringify({ message: userMsg.text, session_id: SESSION_ID })
      });

      const data = await response.json();
      
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: data.text,
        events: data.events
      }]);

      if (data.mission_complete) setIsComplete(true);

    } catch (error) {
      console.error("Error:", error);
      setMessages(prev => [...prev, { role: 'assistant', text: "Sorry, I'm having trouble connecting to the brain." }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = async () => {
    await fetch('http://localhost:8000/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: "", session_id: SESSION_ID })
    });
    setMessages([{ role: 'assistant', text: "Hi! I'm SocialSync. I'm here to connect you with your tribe. Tell me, what's on your mind?", events: [] }]);
    setIsComplete(false);
  };

  return (
    <div className="flex h-screen bg-gray-100 font-sans">
      {/* Sidebar */}
      <div className="w-64 bg-white border-r border-gray-200 p-6 hidden md:block">
        <h1 className="text-2xl font-bold text-gray-800 mb-2 flex items-center gap-2">
           SocialSync <span className="text-2xl">🤝</span>
        </h1>
        <p className="text-gray-500 text-sm mb-8">
          Mission: Connect you with local events using Agentic AI.
        </p>
        <button 
          onClick={handleReset}
          className="w-full flex items-center justify-center gap-2 bg-red-500 text-white py-2 rounded-lg hover:bg-red-600 transition"
        >
          <RefreshCw size={18} /> Reset Chat
        </button>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col max-w-4xl mx-auto w-full bg-white shadow-xl h-screen">
        
        {/* Messages List */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] ${msg.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-800'} rounded-2xl p-4 shadow-sm`}>
                
                {/* Text Content */}
                <div className="prose prose-sm max-w-none mb-2">
                  <ReactMarkdown>{msg.text}</ReactMarkdown>
                </div>

                {/* Event Cards Grid */}
                {msg.events && msg.events.length > 0 && (
                  <div className="flex flex-wrap gap-4 mt-4">
                    {msg.events.map((event, i) => (
                      <EventCard key={i} event={event} />
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex items-center gap-2 text-gray-400 p-4">
              <Bot className="animate-bounce" /> Thinking...
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 border-t border-gray-200 bg-white">
          {!isComplete ? (
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Type your answer..."
                className="flex-1 p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={isLoading}
              />
              <button 
                onClick={handleSend}
                disabled={isLoading}
                className="bg-blue-600 text-white p-3 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                <Send size={20} />
              </button>
            </div>
          ) : (
            <div className="text-center p-4">
              <div className="text-green-600 font-bold text-xl mb-2">🎉 Mission Complete!</div>
              <button 
                onClick={handleReset}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
              >
                Start New Search
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;