import React, { useEffect, useState } from 'react';
import { Shield, ChevronDown, ChevronUp, ExternalLink, AlertTriangle } from 'lucide-react';
import { Link } from 'react-router-dom';
import api from '../../api/axios';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
} from 'recharts';

const SCORE_COLOR = (s) => {
  if (s >= 81) return { bg: 'bg-green-100',  text: 'text-green-700',  bar: '#22c55e', border: 'border-green-200', label: 'Excellent' };
  if (s >= 61) return { bg: 'bg-yellow-100', text: 'text-yellow-700', bar: '#eab308', border: 'border-yellow-200', label: 'Good' };
  if (s >= 41) return { bg: 'bg-orange-100', text: 'text-orange-700', bar: '#f97316', border: 'border-orange-200', label: 'Moderate Risk' };
  return         { bg: 'bg-red-100',    text: 'text-red-700',    bar: '#ef4444', border: 'border-red-200',    label: 'High Risk' };
};

const FACTOR_LABELS = {
  crime_safety:       'Crime Safety',
  disaster_safety:    'Disaster Safety',
  flood_safety:       'Flood Safety',
  hospital_access:    'Hospital Access',
  landslide_safety:   'Landslide Safety',
  rainfall_stability: 'Rainfall Stability',
  transport_access:   'Transport Access',
};

function ScoreBar({ label, value }) {
  const color = value >= 70 ? '#22c55e' : value >= 50 ? '#eab308' : '#ef4444';
  return (
    <div>
      <div className="flex justify-between text-xs mb-0.5">
        <span className="text-gray-600 dark:text-gray-400">{label}</span>
        <span className="font-semibold text-gray-900 dark:text-white">{value}/100</span>
      </div>
      <div className="h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full">
        <div
          className="h-1.5 rounded-full transition-all duration-500"
          style={{ width: `${value}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

export default function SafeRentWidget({ district }) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);
  const [open, setOpen]       = useState(() => window.innerWidth >= 1024);

  useEffect(() => {
    if (!district) return;
    setLoading(true);
    setError(null);
    api.get(`/location/score/${encodeURIComponent(district)}`)
      .then(({ data }) => setData(data))
      .catch(err => {
        if (err.response?.status === 503 || err.code === 'ERR_NETWORK') {
          setError('offline');
        } else {
          setError('error');
        }
      })
      .finally(() => setLoading(false));
  }, [district]);

  if (!district) return null;

  const c = data ? SCORE_COLOR(data.safe_score) : null;

  const radarData = data
    ? Object.entries(data.breakdown).map(([k, v]) => ({
        name: FACTOR_LABELS[k] || k,
        value: Math.round(v),
      }))
    : [];

  const emoji = data
    ? (data.safe_score >= 81 ? '🟢' : data.safe_score >= 61 ? '🟡' : data.safe_score >= 41 ? '🟠' : '🔴')
    : null;

  const verdict = data
    ? `${district} is rated ${c.label} for rental based on historical disaster and amenity data.`
    : null;

  return (
    <div className={`rounded-2xl border ${c ? c.border : 'border-gray-200 dark:border-gray-700'} bg-white dark:bg-gray-900 overflow-hidden`}>
      {/* Header — always visible */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Shield size={20} className="text-primary-600 shrink-0" />
          <span className="font-semibold text-gray-900 dark:text-white text-sm">
            Area Safety — {district}
          </span>
          {data && !loading && (
            <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold ${c.bg} ${c.text}`}>
              {emoji} {data.safe_score}/100 — {c.label}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <Link
            to={`/safety?district=${encodeURIComponent(district)}`}
            onClick={e => e.stopPropagation()}
            className="hidden sm:flex items-center gap-1 text-xs text-primary-600 hover:underline font-medium"
          >
            View full SafeRent report <ExternalLink size={11} />
          </Link>
          {open ? <ChevronUp size={16} className="text-gray-400" /> : <ChevronDown size={16} className="text-gray-400" />}
        </div>
      </button>

      {/* Collapsible body */}
      {open && (
        <div className="border-t border-gray-100 dark:border-gray-800 px-5 py-4">

          {/* Loading */}
          {loading && (
            <div className="flex items-center gap-3 py-4 text-gray-400 text-sm">
              <Shield size={20} className="animate-pulse opacity-40" />
              Loading SafeRent data for {district}…
            </div>
          )}

          {/* Offline / error */}
          {!loading && error === 'offline' && (
            <div className="flex items-start gap-3 py-3 text-sm text-amber-700 bg-amber-50 rounded-xl px-4">
              <AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-500" />
              <div>
                <p className="font-medium">SafeRent data unavailable</p>
                <p className="text-xs text-amber-600 mt-0.5">Start the location intelligence service (<code className="bg-amber-100 px-1 rounded">python app.py</code> on port 8004).</p>
              </div>
            </div>
          )}
          {!loading && error === 'error' && (
            <p className="text-sm text-gray-500 py-2">Could not load safety data for this district.</p>
          )}

          {/* Data */}
          {!loading && data && (
            <>
              {/* Verdict */}
              <p className={`text-xs font-medium mb-4 ${c.text}`}>{verdict}</p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
                {/* Radar chart */}
                <div>
                  <ResponsiveContainer width="100%" height={200}>
                    <RadarChart data={radarData}>
                      <PolarGrid />
                      <PolarAngleAxis dataKey="name" tick={{ fontSize: 9 }} />
                      <Radar dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>

                {/* Factor bars */}
                <div className="space-y-2.5 justify-center flex flex-col">
                  {Object.entries(data.breakdown)
                    .sort((a, b) => a[0].localeCompare(b[0]))
                    .map(([k, v]) => (
                      <ScoreBar key={k} label={FACTOR_LABELS[k] || k} value={Math.round(v)} />
                    ))}
                </div>
              </div>

              {/* Mobile deep-link */}
              <div className="mt-4 sm:hidden">
                <Link
                  to={`/safety?district=${encodeURIComponent(district)}`}
                  className="flex items-center gap-1 text-xs text-primary-600 hover:underline font-medium"
                >
                  View full SafeRent report <ExternalLink size={11} />
                </Link>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
