import React, { useState, useEffect } from 'react'; // Added useEffect
import { X, Mail, Lock, User } from 'lucide-react';

export default function AuthModal({ isOpen, onClose, onLogin }) {
  const [isRegistering, setIsRegistering] = useState(false);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  // --- NEW: Reset fields whenever the modal opens ---
  useEffect(() => {
    if (isOpen) {
      setEmail('');
      setName('');
      setPassword('');
      setError('');
      setIsRegistering(false); // Optional: Always start on Login screen
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleToggle = () => {
    setIsRegistering(!isRegistering);
    setEmail('');
    setName('');
    setPassword('');
    setError('');
  };

  const handleSubmit = async () => {
    setError('');
    const endpoint = isRegistering ? '/register' : '/login';
    
    const body = { email, password };
    if (isRegistering) {
        body.name = name;
    }

    try {
      const res = await fetch(`http://localhost:8000${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });

      const data = await res.json();
      
      if (!res.ok) throw new Error(data.detail || 'Something went wrong');
      
      onLogin(data); 
      onClose();
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 backdrop-blur-sm">
      <div className="bg-gray-800 border border-gray-700 p-8 rounded-2xl w-96 shadow-2xl relative">
        <button onClick={onClose} className="absolute top-4 right-4 text-gray-400 hover:text-white">
          <X size={20} />
        </button>

        <h2 className="text-2xl font-bold text-white mb-6 text-center">
          {isRegistering ? 'Join SocialSync' : 'Welcome Back'}
        </h2>

        <div className="space-y-4">
          
          {/* Name Field (Register Only) */}
          {isRegistering && (
            <div className="relative">
                <User className="absolute left-3 top-3 text-gray-400" size={18} />
                <input
                className="w-full bg-gray-900 border border-gray-700 text-white rounded-lg py-2.5 pl-10 pr-4 focus:ring-2 focus:ring-blue-500 focus:outline-none"
                placeholder="Name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                />
            </div>
          )}

          {/* Email Field */}
          <div className="relative">
            <Mail className="absolute left-3 top-3 text-gray-400" size={18} />
            <input
              type="text" 
              className="w-full bg-gray-900 border border-gray-700 text-white rounded-lg py-2.5 pl-10 pr-4 focus:ring-2 focus:ring-blue-500 focus:outline-none"
              placeholder="Email Address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>

          {/* Password */}
          <div className="relative">
            <Lock className="absolute left-3 top-3 text-gray-400" size={18} />
            <input
              type="password"
              className="w-full bg-gray-900 border border-gray-700 text-white rounded-lg py-2.5 pl-10 pr-4 focus:ring-2 focus:ring-blue-500 focus:outline-none"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          {error && <div className="text-red-400 text-sm text-center">{error}</div>}

          {/* Submit Button */}
          <button
            onClick={handleSubmit}
            className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white py-3 rounded-lg hover:from-blue-500 hover:to-blue-600 transition-all shadow-lg hover:shadow-xl transform hover:scale-105 active:scale-95 font-medium text-base"
          >
            {isRegistering ? 'Create Account' : 'Log In'}
          </button>

          <div className="text-center text-sm text-gray-400 mt-4">
            {isRegistering ? "Already have an account? " : "New here? "}
            <button 
              onClick={handleToggle}
              className="text-blue-400 hover:underline"
            >
              {isRegistering ? 'Log In' : 'Register'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}