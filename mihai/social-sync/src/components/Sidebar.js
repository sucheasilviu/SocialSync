import React from 'react';
import { RefreshCw } from 'lucide-react';

const Sidebar = ({ onReset }) => {
  return (
    <div className="w-64 bg-gray-800 border-r border-gray-700 p-6 hidden md:block">
      <h1 className="text-2xl font-bold text-white mb-2 flex items-center gap-2">
         SocialSync <span className="text-2xl">🤝</span>
      </h1>
      <p className="text-gray-400 text-sm mb-8">
        Mission: Connect you with local events using Agentic AI.
      </p>
      
      {/* The Reset Button */}
      {/* We use the 'onReset' prop passed from App.js */}
      <button 
        onClick={onReset}
        className="w-full flex items-center justify-center gap-2 bg-red-600 text-white py-2 rounded-lg hover:bg-red-700 transition shadow-lg"
      >
        <RefreshCw size={18} /> Reset Chat
      </button>
    </div>
  );
};

export default Sidebar;