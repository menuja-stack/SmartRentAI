import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Shield, AlertTriangle, CheckCircle, MapPin, RefreshCw, ChevronDown, ChevronUp } from 'lucide-react';
import api from '../api/axios';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, Tooltip, Cell,
} from 'recharts';
import { motion, AnimatePresence } from 'framer-motion';
import SafeRentSkeleton from '../components/ui/skeletons/SafeRentSkeleton';
import AILoader from '../components/ui/AILoader';

const SCORE_COLOR = (s) => {
  if (s >= 81) return { bg: 'bg-green-100',  text: 'text-green-700',  bar: '#22c55e', border: 'border-green-300' };
  if (s >= 61) return { bg: 'bg-yellow-100', text: 'text-yellow-700', bar: '#eab308', border: 'border-yellow-300' };
  if (s >= 41) return { bg: 'bg-orange-100', text: 'text-orange-700', bar: '#f97316', border: 'border-orange-300' };
  return         { bg: 'bg-red-100',    text: 'text-red-700',    bar: '#ef4444', border: 'border-red-300' };
};

function ScoreBadge({ score }) {
  const c = SCORE_COLOR(score);
  return (
    <span className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-bold ${c.bg} ${c.text}`}>
      {score >= 81 ? '🟢' : score >= 61 ? '🟡' : score >= 41 ? '🟠' : '🔴'} {score}/100
    </span>
  );
}

function DistrictCard({ d, onClick, selected }) {
  const c = SCORE_COLOR(d.safe_score);
  return (
    <motion.button
      whileHover={{ y: -2 }}
      onClick={() => onClick(d)}
      className={`card p-4 text-left w-full border-2 transition-all ${selected ? c.border + ' shadow-md' : 'border-transparent'}`}>
      <div className="flex justify-between items-start mb-2">
        <div>
          <p className="font-semibold text-gray-900 dark:text-white text-sm">{d.district.replace('_',' ')}</p>
          <p className="text-xs text-gray-400">{d.province}</p>
        </div>
        <ScoreBadge score={d.safe_score} />
      </div>
      <p className={`text-xs font-medium ${c.text}`}>{d.category}</p>
      <div className={`mt-2 h-1.5 rounded-full ${c.bg}`}>
        <div className={`h-1.5 rounded-full`} style={{ width: `${d.safe_score}%`, backgroundColor: c.bar }} />
      </div>
    </motion.button>
  );
}

function ScoreBreakdown({ breakdown }) {
  const labels = {
    disaster_safety:    'Disaster Safety',
    flood_safety:       'Flood Safety',
    landslide_safety:   'Landslide Safety',
    hospital_access:    'Hospital Access',
    transport_access:   'Transport Access',
    crime_safety:       'Crime Safety',
    rainfall_stability: 'Rainfall Stability',
  };
  const data = Object.entries(breakdown).map(([k, v]) => ({ name: labels[k] || k, value: Math.round(v) }));

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div>
        <ResponsiveContainer width="100%" height={260}>
          <RadarChart data={data}>
            <PolarGrid />
            <PolarAngleAxis dataKey="name" tick={{ fontSize: 10 }} />
            <Radar dataKey="value" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
      <div className="space-y-2">
        {data.map(item => (
          <div key={item.name}>
            <div className="flex justify-between text-xs mb-0.5">
              <span className="text-gray-600 dark:text-gray-400">{item.name}</span>
              <span className="font-semibold text-gray-900 dark:text-white">{item.value}/100</span>
            </div>
            <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded-full">
              <div
                className="h-2 rounded-full transition-all duration-500"
                style={{
                  width: `${item.value}%`,
                  backgroundColor: item.value >= 70 ? '#22c55e' : item.value >= 50 ? '#eab308' : '#ef4444'
                }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function SafetyDashboardPage() {
  const [searchParams] = useSearchParams();
  const [allDistricts, setAllDistricts] = useState([]);
  const [selected, setSelected]         = useState(null);
  const [loading, setLoading]           = useState(true);
  const [filter, setFilter]             = useState('all');
  const [sort, setSort]                 = useState('score_desc');
  const [compareList, setCompareList]   = useState([]);
  const [compareResult, setCompareResult] = useState([]);
  const [liveForm, setLiveForm]         = useState({ district: 'Colombo', rainfall_mm: 5, humidity_pct: 80, temp_avg_c: 27 });
  const [liveResult, setLiveResult]     = useState(null);
  const [tab, setTab]                   = useState('map');  // map | compare | live

  useEffect(() => {
    setLoading(true);
    api.get('/location/all')
       .then(({ data }) => {
         setAllDistricts(data);
         const deepLink = searchParams.get('district');
         if (deepLink) {
           const match = data.find(
             d => d.district.toLowerCase().replace('_', ' ') === deepLink.toLowerCase()
               || d.district.toLowerCase() === deepLink.toLowerCase()
           );
           setSelected(match || data[0] || null);
         } else {
           setSelected(data[0] || null);
         }
       })
       .catch(() => setAllDistricts([]))
       .finally(() => setLoading(false));
  }, [searchParams]);

  const filtered = allDistricts
    .filter(d => {
      if (filter === 'excellent') return d.safe_score >= 81;
      if (filter === 'good')      return d.safe_score >= 61 && d.safe_score < 81;
      if (filter === 'moderate')  return d.safe_score >= 41 && d.safe_score < 61;
      if (filter === 'high_risk') return d.safe_score < 41;
      return true;
    })
    .sort((a, b) => sort === 'score_desc' ? b.safe_score - a.safe_score
                  : sort === 'score_asc'  ? a.safe_score - b.safe_score
                  : a.district.localeCompare(b.district));

  const toggleCompare = (d) => {
    setCompareList(prev =>
      prev.includes(d.district) ? prev.filter(x => x !== d.district)
      : prev.length < 4         ? [...prev, d.district]
      : prev
    );
  };

  const runCompare = async () => {
    const { data } = await api.post('/location/compare', { districts: compareList });
    setCompareResult(data);
    setTab('compare');
  };

  const runLive = async (e) => {
    e.preventDefault();
    const { data } = await api.post('/location/predict-live', liveForm);
    setLiveResult(data);
  };

  const barData = allDistricts.slice(0, 25).map(d => ({
    name:  d.district.replace('Nuwara_Eliya','N.Eliya'),
    score: d.safe_score,
    fill:  SCORE_COLOR(d.safe_score).bar,
  }));

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
          <Shield size={32} className="text-primary-600" /> SafeRent Location Intelligence
        </h1>
        <p className="text-gray-500 mt-1 text-sm">
          AI-powered district safety analysis trained on <strong>401,775 weather & disaster records (1981–present)</strong> across 25 Sri Lankan districts.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-gray-200 dark:border-gray-800">
        {[['map','🗺️ District Map'],['compare','⚖️ Compare Districts'],['live','⚡ Live Prediction']].map(([t,l]) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-all ${tab===t ? 'border-primary-600 text-primary-600' : 'border-transparent text-gray-500 hover:text-gray-700'}`}>
            {l}
          </button>
        ))}
      </div>

      {loading ? (
        <div>
          <AILoader
            icon={<Shield size={22} />}
            messages={[
              'Analysing disaster records…',
              'Scoring 25 districts…',
              'Building safety profiles…',
            ]}
            className="py-2"
          />
          <SafeRentSkeleton />
          <p className="text-xs text-gray-400 text-center mt-6">
            Make sure you ran <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded">POST /train</code> on the location-intelligence service
          </p>
        </div>
      ) : (

        <>
          {/* ── TAB: Map ─────────────────────────────────────────────────── */}
          {tab === 'map' && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left — district list */}
              <div>
                <div className="flex gap-2 mb-3">
                  <select value={filter} onChange={e => setFilter(e.target.value)} className="input-field text-sm">
                    <option value="all">All Districts</option>
                    <option value="excellent">🟢 Excellent (81+)</option>
                    <option value="good">🟡 Good (61–80)</option>
                    <option value="moderate">🟠 Moderate (41–60)</option>
                    <option value="high_risk">🔴 High Risk (&lt;41)</option>
                  </select>
                  <select value={sort} onChange={e => setSort(e.target.value)} className="input-field text-sm">
                    <option value="score_desc">Score ↓</option>
                    <option value="score_asc">Score ↑</option>
                    <option value="alpha">A–Z</option>
                  </select>
                </div>
                <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
                  {filtered.map(d => (
                    <DistrictCard
                      key={d.district} d={d}
                      onClick={setSelected}
                      selected={selected?.district === d.district}
                    />
                  ))}
                </div>
              </div>

              {/* Right — selected district detail */}
              {selected && (
                <div className="lg:col-span-2 space-y-4">
                  <div className="card p-6">
                    <div className="flex items-start justify-between mb-4">
                      <div>
                        <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                          <MapPin size={22} className="text-primary-600" />
                          {selected.district.replace('_',' ')}
                        </h2>
                        <p className="text-gray-500">{selected.province} Province</p>
                      </div>
                      <div className="text-right">
                        <ScoreBadge score={selected.safe_score} />
                        <p className={`text-sm font-medium mt-1 ${SCORE_COLOR(selected.safe_score).text}`}>
                          {selected.category}
                        </p>
                      </div>
                    </div>

                    <ScoreBreakdown breakdown={selected.breakdown} />
                  </div>

                  {/* Historical stats */}
                  <div className="card p-5">
                    <h3 className="font-semibold text-gray-900 dark:text-white mb-3">📊 Historical Data (from your dataset)</h3>
                    <div className="grid grid-cols-3 gap-4 text-center">
                      {[
                        ['Disaster Rate', `${selected.historical.disaster_rate_pct}%`, 'of days had disaster'],
                        ['Avg Daily Rainfall', `${selected.historical.avg_daily_rainfall} mm`, 'per day average'],
                        ['Years of Data', `${selected.historical.total_years} yrs`, `${selected.historical.disaster_events} events`],
                      ].map(([l,v,sub]) => (
                        <div key={l} className="bg-gray-50 dark:bg-gray-800 rounded-xl p-3">
                          <p className="text-xs text-gray-500">{l}</p>
                          <p className="text-xl font-bold text-gray-900 dark:text-white">{v}</p>
                          <p className="text-xs text-gray-400">{sub}</p>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Risks & Advantages */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="card p-4">
                      <h3 className="font-semibold text-red-600 flex items-center gap-2 mb-3">
                        <AlertTriangle size={16} /> Risk Factors
                      </h3>
                      <ul className="space-y-2">
                        {selected.risks.map((r, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
                            <span className="text-red-500 mt-0.5 shrink-0">⚠</span> {r}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="card p-4">
                      <h3 className="font-semibold text-green-600 flex items-center gap-2 mb-3">
                        <CheckCircle size={16} /> Advantages
                      </h3>
                      <ul className="space-y-2">
                        {selected.advantages.map((a, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-gray-700 dark:text-gray-300">
                            <span className="text-green-500 mt-0.5 shrink-0">✓</span> {a}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <button
                    onClick={() => toggleCompare(selected)}
                    className={`btn-secondary w-full text-sm ${compareList.includes(selected.district) ? 'border-primary-500 text-primary-600' : ''}`}>
                    {compareList.includes(selected.district) ? '✓ Added to compare' : '⊕ Add to comparison'}
                    {compareList.length > 0 && ` (${compareList.length}/4)`}
                  </button>
                  {compareList.length >= 2 && (
                    <button onClick={runCompare} className="btn-primary w-full text-sm">
                      ⚖️ Compare Selected Districts
                    </button>
                  )}
                </div>
              )}
            </div>
          )}

          {/* ── TAB: All districts bar chart ─────────────────────────────── */}
          {tab === 'map' && (
            <div className="card p-5 mt-6">
              <h3 className="font-semibold text-gray-900 dark:text-white mb-4">All 25 Districts — SafeRent Score</h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={barData} margin={{ top: 0, right: 0, left: -20, bottom: 40 }}>
                  <XAxis dataKey="name" tick={{ fontSize: 9 }} angle={-45} textAnchor="end" interval={0} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                  <Tooltip formatter={(v) => [`${v}/100`, 'Safe Score']} />
                  <Bar dataKey="score" radius={[3, 3, 0, 0]}>
                    {barData.map((e, i) => <Cell key={i} fill={e.fill} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <div className="flex gap-4 justify-center mt-2 text-xs text-gray-500">
                <span>🟢 81–100 Excellent</span>
                <span>🟡 61–80 Good</span>
                <span>🟠 41–60 Moderate</span>
                <span>🔴 0–40 High Risk</span>
              </div>
            </div>
          )}

          {/* ── TAB: Compare ─────────────────────────────────────────────── */}
          {tab === 'compare' && (
            <div>
              {compareResult.length === 0 ? (
                <div className="text-center py-16 text-gray-500">
                  <p className="text-lg font-medium">No comparison yet</p>
                  <p className="text-sm mt-1">Go to District Map, select up to 4 districts, then click Compare.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  {compareResult.map(d => (
                    <div key={d.district} className="card p-5 space-y-3">
                      <div>
                        <h3 className="font-bold text-gray-900 dark:text-white">{d.district.replace('_',' ')}</h3>
                        <p className="text-xs text-gray-400">{d.province}</p>
                      </div>
                      <ScoreBadge score={d.safe_score} />
                      <p className={`text-sm font-medium ${SCORE_COLOR(d.safe_score).text}`}>{d.category}</p>
                      <div className="space-y-1">
                        {Object.entries(d.breakdown).map(([k, v]) => (
                          <div key={k} className="flex justify-between text-xs">
                            <span className="text-gray-500 capitalize">{k.replace(/_/g,' ')}</span>
                            <span className="font-medium">{Math.round(v)}</span>
                          </div>
                        ))}
                      </div>
                      <div>
                        <p className="text-xs font-semibold text-red-600 mb-1">Risks:</p>
                        {d.risks.slice(0,2).map((r,i) => <p key={i} className="text-xs text-gray-600">⚠ {r}</p>)}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* ── TAB: Live Prediction ─────────────────────────────────────── */}
          {tab === 'live' && (
            <div className="max-w-lg">
              <div className="card p-6">
                <h2 className="font-semibold text-gray-900 dark:text-white mb-1">⚡ Live Disaster Risk Prediction</h2>
                <p className="text-sm text-gray-500 mb-5">
                  Enter current weather conditions to predict real-time disaster probability using the ML model trained on your dataset.
                </p>
                <form onSubmit={runLive} className="space-y-4">
                  <div>
                    <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">District</label>
                    <select value={liveForm.district}
                      onChange={e => setLiveForm({ ...liveForm, district: e.target.value })}
                      className="input-field">
                      {allDistricts.map(d => (
                        <option key={d.district} value={d.district}>{d.district.replace('_',' ')}</option>
                      ))}
                    </select>
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    {[
                      ['rainfall_mm', 'Rainfall (mm)', 0, 300],
                      ['humidity_pct', 'Humidity (%)', 0, 100],
                      ['temp_avg_c', 'Temp (°C)', 15, 40],
                    ].map(([k, l, min, max]) => (
                      <div key={k}>
                        <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">{l}</label>
                        <input type="number" min={min} max={max} value={liveForm[k]}
                          onChange={e => setLiveForm({ ...liveForm, [k]: Number(e.target.value) })}
                          className="input-field" />
                      </div>
                    ))}
                  </div>
                  <button type="submit" className="btn-primary w-full">🤖 Predict Disaster Risk</button>
                </form>

                {liveResult && (
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                    className={`mt-5 p-4 rounded-xl border-2 ${
                      liveResult.risk_level === 'High' ? 'border-red-300 bg-red-50' :
                      liveResult.risk_level === 'Medium' ? 'border-yellow-300 bg-yellow-50' :
                      'border-green-300 bg-green-50'
                    }`}>
                    <div className="text-center">
                      <p className="text-3xl font-extrabold text-gray-900">
                        {liveResult.disaster_probability}%
                      </p>
                      <p className="text-sm text-gray-600 mb-2">Disaster Probability</p>
                      <span className={`badge font-bold ${
                        liveResult.risk_level === 'High' ? 'bg-red-200 text-red-800' :
                        liveResult.risk_level === 'Medium' ? 'bg-yellow-200 text-yellow-800' :
                        'bg-green-200 text-green-800'
                      }`}>
                        {liveResult.risk_level} Risk
                      </span>
                      <p className="text-sm mt-3 font-semibold">
                        {liveResult.safe_to_rent
                          ? '✅ Safe conditions for renting in this area'
                          : '⚠️ Exercise caution — elevated disaster risk'}
                      </p>
                    </div>
                  </motion.div>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
