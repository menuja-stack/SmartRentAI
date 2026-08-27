import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Sparkles, RefreshCw, ChevronDown, ChevronUp, Star, CheckCircle2, Info } from 'lucide-react';
import { toast } from 'react-toastify';
import api from '../api/axios';
import PropertyCard from '../components/property/PropertyCard';
import RecommendationSkeleton from '../components/ui/skeletons/RecommendationSkeleton';
import AILoader from '../components/ui/AILoader';

const scoreColor = (pct) =>
  pct >= 85 ? { ring: 'text-green-600',  bg: 'bg-green-100  text-green-700' }
: pct >= 70 ? { ring: 'text-primary-600', bg: 'bg-primary-100 text-primary-700' }
: pct >= 55 ? { ring: 'text-amber-600',  bg: 'bg-amber-100  text-amber-700' }
:             { ring: 'text-gray-500',   bg: 'bg-gray-100   text-gray-600' };

function RecommendationCard({ rec, rank }) {
  const [open, setOpen] = useState(false);
  const pct = Math.round((rec.match_score ?? 0) * 100);
  const c = scoreColor(pct);
  const reasons = rec.match_reasons || [];

  return (
    <div className="relative flex flex-col">
      {/* Match score badge */}
      <div className={`absolute top-3 right-3 z-10 ${c.bg} text-xs font-bold px-2.5 py-1 rounded-full shadow-sm flex items-center gap-1`}>
        <Star size={11} className="fill-current" /> {pct}% match
      </div>
      {rank <= 3 && (
        <div className="absolute -top-2 -left-2 z-10 bg-amber-500 text-white text-xs font-bold px-2 py-1 rounded-full shadow">
          #{rank} Pick
        </div>
      )}

      <PropertyCard property={rec} />

      {/* Reasons */}
      {reasons.length > 0 && (
        <div className="mt-2">
          <div className="flex flex-wrap gap-1.5">
            {reasons.slice(0, 3).map((r, i) => (
              <span key={i}
                className="inline-flex items-center gap-1 text-[11px] bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300 px-2 py-1 rounded-lg">
                <CheckCircle2 size={11} /> {r}
              </span>
            ))}
          </div>
          <button onClick={() => setOpen(o => !o)}
            className="mt-1.5 flex items-center gap-1 text-xs text-gray-400 hover:text-primary-600">
            <Info size={12} /> Why this? {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
          {open && (
            <div className="mt-1 text-xs text-gray-500 dark:text-gray-400 space-y-1 pl-1 border-l-2 border-primary-200">
              {reasons.map((r, i) => <p key={i} className="pl-2">• {r}</p>)}
              {rec.saferent_score != null && (
                <p className="pl-2 text-gray-400">SafeRent score for this area: <strong>{rec.saferent_score}/100</strong></p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function RecommendationsPage() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await api.get('/recommendations');
      setData(data);
    } catch (e) {
      const offline = e.response?.status === 503;
      setError(offline ? 'offline' : 'error');
      if (!offline) toast.error('Failed to load recommendations');
      setData(null);
    }
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  const recs = data?.recommendations || [];
  const needsOnboarding = data?.needs_onboarding;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-2">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <Sparkles size={28} className="text-primary-600" /> For You
        </h1>
        <button onClick={load} className="btn-secondary flex items-center gap-2 text-sm">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Profile summary banner */}
      {data?.profile_summary && (
        <div className="mb-6 p-4 rounded-2xl bg-gradient-to-r from-primary-50 to-blue-50 dark:from-gray-800 dark:to-gray-800 border border-primary-100 dark:border-gray-700">
          <p className="text-sm text-gray-700 dark:text-gray-300">{data.profile_summary}</p>
        </div>
      )}

      {/* States */}
      {loading ? (
        <div>
          <AILoader
            icon={<Sparkles size={22} />}
            messages={[
              'Reading your preferences…',
              'Scoring available properties…',
              'Ranking your best matches…',
            ]}
            className="py-4"
          />
          <RecommendationSkeleton count={6} />
        </div>
      ) : error === 'offline' ? (
        <div className="text-center py-20 text-gray-500">
          <Sparkles size={48} className="mx-auto mb-4 opacity-30" />
          <p className="text-lg font-medium">Recommendation service is offline</p>
          <p className="text-sm mt-1">Start it with <code className="bg-gray-100 px-1 rounded">python app.py</code> in <code className="bg-gray-100 px-1 rounded">ai-services/recommendation</code> (port 8001).</p>
        </div>
      ) : needsOnboarding ? (
        <div className="text-center py-20">
          <Sparkles size={48} className="mx-auto mb-4 text-primary-400" />
          <p className="text-lg font-medium text-gray-900 dark:text-white">Complete your profile to get personalized recommendations</p>
          <p className="text-sm mt-1 text-gray-500 max-w-md mx-auto">
            Tell us your profession, budget, and what matters most — we'll match you with the most suitable properties.
          </p>
          <Link to="/profile" className="btn-primary inline-block mt-5 text-sm">Complete my profile</Link>
        </div>
      ) : recs.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <Sparkles size={48} className="mx-auto mb-4 opacity-30" />
          <p className="text-lg font-medium">No matches right now</p>
          <p className="text-sm mt-1">Try widening your preferred districts or budget in your profile.</p>
          <Link to="/profile" className="btn-secondary inline-block mt-4 text-sm">Adjust preferences</Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-8">
          {recs.map((rec, i) => <RecommendationCard key={rec.id} rec={rec} rank={i + 1} />)}
        </div>
      )}
    </div>
  );
}
