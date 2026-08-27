import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, RefreshCw } from 'lucide-react';
import { v4 as uuidv4 } from 'uuid';
import api from '../api/axios';
import { motion, AnimatePresence } from 'framer-motion';

const SESSION_KEY = 'chatbot_session_id';

const QUICK_PROMPTS = [
  'How does price prediction work?',
  'Find me a 2-bedroom apartment in Colombo',
  'What documents do I need to rent?',
  'How do I contact a landlord?',
];

export default function ChatbotPage() {
  const [messages, setMessages] = useState([
    { role: 'bot', text: "Hi! I'm SmartRentAI's AI assistant 🏠 Ask me anything about renting, properties, or pricing in Sri Lanka!" },
  ]);
  const [input, setInput]   = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => {
    let sid = localStorage.getItem(SESSION_KEY);
    if (!sid) { sid = uuidv4(); localStorage.setItem(SESSION_KEY, sid); }
    return sid;
  });
  const bottomRef = useRef(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const sendMessage = async (text) => {
    const msg = text || input.trim();
    if (!msg || loading) return;
    setInput('');
    setMessages(m => [...m, { role: 'user', text: msg }]);
    setLoading(true);

    try {
      const { data } = await api.post('/chatbot/message', { message: msg, session_id: sessionId });
      setMessages(m => [...m, { role: 'bot', text: data.reply, intent: data.intent }]);
    } catch {
      setMessages(m => [...m, { role: 'bot', text: 'Sorry, I encountered an error. Please try again.' }]);
    }
    setLoading(false);
  };

  const reset = () => {
    localStorage.removeItem(SESSION_KEY);
    window.location.reload();
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Bot size={28} className="text-primary-600" /> AI Assistant
          </h1>
          <p className="text-gray-500 text-sm mt-1">Powered by NLP intent classification</p>
        </div>
        <button onClick={reset} className="btn-secondary flex items-center gap-2 text-sm">
          <RefreshCw size={14} /> New Chat
        </button>
      </div>

      {/* Chat window */}
      <div className="card h-[500px] flex flex-col">
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          <AnimatePresence>
            {messages.map((msg, i) => (
              <motion.div key={i}
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                {msg.role === 'bot' && (
                  <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center shrink-0">
                    <Bot size={16} className="text-primary-600" />
                  </div>
                )}
                <div className={`max-w-[80%] px-4 py-3 rounded-2xl text-sm leading-relaxed
                  ${msg.role === 'user'
                    ? 'bg-primary-600 text-white rounded-br-sm'
                    : 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded-bl-sm'}`}
                  dangerouslySetInnerHTML={{ __html: msg.text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') }}
                />
                {msg.role === 'user' && (
                  <div className="w-8 h-8 bg-primary-600 rounded-full flex items-center justify-center shrink-0">
                    <User size={16} className="text-white" />
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>

          {loading && (
            <div className="flex gap-3 justify-start">
              <div className="w-8 h-8 bg-primary-100 rounded-full flex items-center justify-center">
                <Bot size={16} className="text-primary-600" />
              </div>
              <div className="bg-gray-100 dark:bg-gray-800 px-4 py-3 rounded-2xl rounded-bl-sm">
                <div className="flex gap-1">
                  {[0,1,2].map(i => (
                    <div key={i} className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                      style={{ animationDelay: `${i * 0.15}s` }} />
                  ))}
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Quick prompts */}
        <div className="px-4 pb-2 flex gap-2 flex-wrap">
          {QUICK_PROMPTS.map(q => (
            <button key={q} onClick={() => sendMessage(q)}
              className="text-xs px-3 py-1.5 rounded-full border border-gray-200 dark:border-gray-700
                         text-gray-600 dark:text-gray-400 hover:border-primary-500 hover:text-primary-600 transition-all">
              {q}
            </button>
          ))}
        </div>

        {/* Input */}
        <div className="p-4 border-t border-gray-100 dark:border-gray-800 flex gap-3">
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            placeholder="Ask about properties, prices, or rental advice…"
            className="input-field flex-1"
            disabled={loading}
          />
          <button onClick={() => sendMessage()} disabled={loading || !input.trim()}
            className="btn-primary px-4 disabled:opacity-50">
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
