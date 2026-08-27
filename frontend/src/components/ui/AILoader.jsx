import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles } from 'lucide-react';

/**
 * Contextual loader for AI endpoints (1–3s responses).
 * Rotates through domain-specific messages while an animated icon pulses.
 *
 *   <AILoader
 *     icon={<TrendingUp size={22} />}
 *     messages={['Analysing property features…', 'Comparing district prices…']}
 *   />
 */
export default function AILoader({ messages = ['Thinking…'], icon = null, className = '' }) {
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    if (messages.length < 2) return undefined;
    const t = setInterval(() => setIdx(i => (i + 1) % messages.length), 1400);
    return () => clearInterval(t);
  }, [messages.length]);

  return (
    <div className={`flex flex-col items-center justify-center py-10 ${className}`}>
      {/* Pulsing icon with orbiting ring */}
      <div className="relative w-16 h-16 mb-4">
        <motion.div
          className="absolute inset-0 rounded-full border-2 border-primary-200 border-t-primary-600"
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        />
        <motion.div
          animate={{ scale: [1, 1.12, 1] }}
          transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
          className="absolute inset-0 flex items-center justify-center text-primary-600"
        >
          {icon || <Sparkles size={22} />}
        </motion.div>
      </div>

      {/* Rotating message */}
      <div className="h-5 overflow-hidden">
        <AnimatePresence mode="wait">
          <motion.p
            key={idx}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25 }}
            className="text-sm text-gray-500 dark:text-gray-400 font-medium"
          >
            {messages[idx]}
          </motion.p>
        </AnimatePresence>
      </div>
    </div>
  );
}
