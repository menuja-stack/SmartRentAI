import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { Home } from 'lucide-react';
import { motion } from 'framer-motion';

/**
 * Full-screen page loader — used as the Suspense fallback for lazy-loaded
 * routes and anywhere a whole page is still being fetched.
 * Breathing SmartRentAI house logo + top progress bar + tagline.
 */
export default function PageLoader() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="fixed inset-0 z-50 bg-white dark:bg-gray-950 flex flex-col items-center justify-center"
    >
      {/* Top progress bar */}
      <div className="absolute top-0 left-0 right-0 h-1 overflow-hidden">
        <motion.div
          className="h-full bg-primary-600"
          initial={{ x: '-100%' }}
          animate={{ x: '100%' }}
          transition={{ duration: 1.1, repeat: Infinity, ease: 'easeInOut' }}
          style={{ width: '40%' }}
        />
      </div>

      {/* Breathing logo */}
      <motion.div
        animate={{ scale: [1, 1.12, 1], opacity: [1, 0.75, 1] }}
        transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
        className="w-16 h-16 rounded-2xl bg-primary-50 dark:bg-primary-900/20 flex items-center justify-center mb-4"
      >
        <Home size={34} className="text-primary-600" />
      </motion.div>

      <p className="font-bold text-lg text-gray-900 dark:text-white">
        Smart<span className="text-primary-600">RentAI</span>
      </p>
      <p className="text-sm text-gray-400 mt-1">Finding your perfect home…</p>
    </motion.div>
  );
}

/**
 * Thin top progress bar that flashes on every route change
 * (YouTube/GitHub style). Mount once inside the Router.
 */
export function RouteProgress() {
  const location = useLocation();
  const [key, setKey] = useState(0);

  useEffect(() => { setKey(k => k + 1); }, [location.pathname]);

  if (key === 0) return null; // skip initial mount
  return (
    <div key={key} className="fixed top-0 left-0 right-0 z-[60] h-0.5 pointer-events-none">
      <div className="route-progress-bar h-full bg-primary-600" />
    </div>
  );
}
