import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useSelector } from 'react-redux';
import { Search, Star, TrendingUp, MessageCircle, MapPin, ArrowRight, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';
import api from '../api/axios';
import PropertyCard from '../components/property/PropertyCard';
import { PropertyCardSkeletonGrid } from '../components/ui/skeletons/PropertyCardSkeleton';

const DISTRICTS = ['Colombo','Kandy','Galle','Negombo','Kurunegala','Battaramulla','Nugegoda'];

export default function HomePage() {
  const [query, setQuery]         = useState('');
  const [district, setDistrict]   = useState('');
  const [featured, setFeatured]   = useState([]);
  const [featLoading, setFeatLoading] = useState(true);
  const [forYou, setForYou]       = useState([]);
  const token = useSelector(s => s.auth.token);
  const navigate = useNavigate();

  useEffect(() => {
    api.get('/properties?limit=6&sort=created_at')
       .then(({ data }) => setFeatured(data.data || []))
       .catch(() => {})
       .finally(() => setFeatLoading(false));
  }, []);

  // Top-3 personalized picks (only when logged in with a completed profile)
  useEffect(() => {
    if (!token) { setForYou([]); return; }
    api.get('/recommendations')
       .then(({ data }) => {
         if (!data.needs_onboarding && data.recommendations?.length) {
           setForYou(data.recommendations.slice(0, 3));
         } else {
           setForYou([]);
         }
       })
       .catch(() => setForYou([]));
  }, [token]);

  const handleSearch = (e) => {
    e.preventDefault();
    const params = new URLSearchParams();
    if (query)    params.set('search', query);
    if (district) params.set('district', district);
    navigate(`/search?${params.toString()}`);
  };

  return (
    <div>
      {/* ── Hero ───────────────────────────────────────────── */}
      <section className="relative bg-gradient-to-br from-primary-700 via-primary-600 to-primary-500 text-white py-24 px-4">
        <div className="absolute inset-0 bg-black/20" />
        <div className="relative max-w-4xl mx-auto text-center">
          <motion.h1
            initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
            className="text-4xl md:text-6xl font-extrabold mb-4 leading-tight">
            Find Your Perfect Home<br />
            <span className="text-accent-500">Powered by AI</span>
          </motion.h1>
          <p className="text-lg text-blue-100 mb-10 max-w-2xl mx-auto">
            AI-powered rental recommendations, price predictions, and smart property matching for Sri Lanka.
          </p>

          {/* Search bar */}
          <form onSubmit={handleSearch}
            className="flex flex-col sm:flex-row gap-3 bg-white rounded-2xl p-2 shadow-2xl max-w-3xl mx-auto">
            <div className="flex-1 flex items-center gap-2 px-3">
              <Search size={18} className="text-gray-400 shrink-0" />
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Search properties, areas…"
                className="flex-1 py-2 outline-none text-gray-900 bg-transparent text-sm"
              />
            </div>
            <select value={district} onChange={e => setDistrict(e.target.value)}
              className="px-3 py-2 text-gray-700 bg-gray-50 rounded-xl border-none outline-none text-sm">
              <option value="">All Districts</option>
              {DISTRICTS.map(d => <option key={d}>{d}</option>)}
            </select>
            <button type="submit" className="btn-primary shrink-0">Search</button>
          </form>
        </div>
      </section>

      {/* ── Features ───────────────────────────────────────── */}
      <section className="py-16 bg-white dark:bg-gray-950">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center mb-12 text-gray-900 dark:text-white">
            Why SmartRentAI?
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { icon: <Star size={32} className="text-primary-600" />,       title: 'AI Recommendations',  desc: 'Personalised property suggestions based on your preferences, budget, and behaviour.' },
              { icon: <TrendingUp size={32} className="text-green-600" />,   title: 'Price Prediction',    desc: 'Machine learning models predict fair rental prices using location, size, and amenities.' },
              { icon: <MessageCircle size={32} className="text-purple-600" />, title: 'AI Chatbot',          desc: 'Get instant answers about properties, lease terms, and rental advice 24/7.' },
            ].map((f) => (
              <motion.div key={f.title} whileHover={{ y: -4 }}
                className="card p-6 text-center hover:shadow-md transition-shadow">
                <div className="flex justify-center mb-4">{f.icon}</div>
                <h3 className="font-semibold text-lg mb-2 text-gray-900 dark:text-white">{f.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Recommended for You (top 3) ────────────────────── */}
      {forYou.length > 0 && (
        <section className="py-16 bg-white dark:bg-gray-950">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between mb-8">
              <h2 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <Sparkles size={26} className="text-primary-600" /> Recommended for You
              </h2>
              <Link to="/recommendations" className="flex items-center gap-1 text-primary-600 font-medium hover:underline">
                See all <ArrowRight size={16} />
              </Link>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {forYou.map(p => (
                <div key={p.id} className="relative">
                  {p.match_score != null && (
                    <div className="absolute top-3 right-3 z-10 bg-primary-100 text-primary-700 text-xs font-bold px-2.5 py-1 rounded-full shadow-sm flex items-center gap-1">
                      <Star size={11} className="fill-current" /> {Math.round(p.match_score * 100)}% match
                    </div>
                  )}
                  <PropertyCard property={p} />
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* ── Featured Listings ──────────────────────────────── */}
      {(featLoading || featured.length > 0) && (
        <section className="py-16 bg-gray-50 dark:bg-gray-900">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between mb-8">
              <h2 className="text-3xl font-bold text-gray-900 dark:text-white">Latest Properties</h2>
              <a href="/search" className="flex items-center gap-1 text-primary-600 font-medium hover:underline">
                View all <ArrowRight size={16} />
              </a>
            </div>
            {featLoading ? (
              <PropertyCardSkeletonGrid count={6} />
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
                {featured.map(p => <PropertyCard key={p.id} property={p} />)}
              </div>
            )}
          </div>
        </section>
      )}

      {/* ── CTA ────────────────────────────────────────────── */}
      <section className="py-20 bg-primary-600 text-white text-center px-4">
        <h2 className="text-3xl font-bold mb-4">Ready to find your home?</h2>
        <p className="text-blue-100 mb-8 max-w-xl mx-auto">
          Join thousands of renters who found their perfect home using SmartRentAI.
        </p>
        <div className="flex gap-4 justify-center">
          <a href="/register" className="bg-white text-primary-600 font-semibold px-6 py-3 rounded-xl hover:bg-blue-50 transition-colors">
            Get Started Free
          </a>
          <a href="/search" className="border border-white/50 text-white font-semibold px-6 py-3 rounded-xl hover:bg-white/10 transition-colors">
            Browse Properties
          </a>
        </div>
      </section>
    </div>
  );
}
