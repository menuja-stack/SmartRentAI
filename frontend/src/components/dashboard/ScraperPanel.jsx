import React, { useEffect, useState, useRef } from 'react';
import { Globe, Trash2, RefreshCw, Building2, TrendingUp, CheckCircle, AlertCircle, Play, Loader2, Home } from 'lucide-react';
import api from '../../api/axios';
import { getImageUrl } from '../../utils/imageUrl';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

/** Small thumbnail with a clean in-house placeholder — no external image service. */
function ListingThumb({ src, alt }) {
  const [errored, setErrored] = useState(false);
  const resolved = errored ? null : src;

  return (
    <div className="w-16 h-12 rounded-lg overflow-hidden bg-gray-100 dark:bg-gray-800 shrink-0 flex items-center justify-center">
      {resolved ? (
        <img
          src={resolved}
          alt={alt}
          loading="lazy"
          onError={() => setErrored(true)}
          className="w-full h-full object-cover"
        />
      ) : (
        <Home size={18} className="text-gray-300 dark:text-gray-600" />
      )}
    </div>
  );
}

const DISTRICTS = [
  'Colombo', 'Gampaha', 'Kalutara', 'Kandy', 'Matale', 'Nuwara Eliya',
  'Galle', 'Matara', 'Hambantota', 'Jaffna', 'Kilinochchi', 'Mannar', 'Mullaitivu',
  'Vavuniya', 'Trincomalee', 'Batticaloa', 'Ampara', 'Kurunegala', 'Puttalam',
  'Anuradhapura', 'Polonnaruwa', 'Badulla', 'Monaragala', 'Ratnapura', 'Kegalle',
];

export default function ScraperPanel() {
  const [stats,    setStats]    = useState(null);
  const [loading,  setLoading]  = useState(true);
  const [clearing, setClearing] = useState(false);
  const [toast,    setToast]    = useState(null); // { type: 'success'|'error', msg }
  const [confirmClear, setConfirmClear] = useState(false);

  // Scraper run state
  const [runForm, setRunForm] = useState({ pages: 2, district: 'all', site: 'all', noImages: true });
  const [running, setRunning] = useState(false);
  const [jobStatus, setJobStatus] = useState(null);
  const pollRef = useRef(null);

  const showToast = (type, msg) => {
    setToast({ type, msg });
    setTimeout(() => setToast(null), 4000);
  };

  const load = () => {
    setLoading(true);
    api.get('/scraper/stats')
       .then(({ data }) => setStats(data))
       .catch(() => setStats(null))
       .finally(() => setLoading(false));
  };

  const startPolling = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(async () => {
      try {
        const { data } = await api.get('/scraper/run/status');
        setJobStatus(data);
        if (!data.running) {
          clearInterval(pollRef.current);
          pollRef.current = null;
          setRunning(false);
          if (data.error) showToast('error', `Scraper failed: ${data.error}`);
          else showToast('success', `Scrape complete — saved ${data.saved ?? 0}, skipped ${data.skipped ?? 0}.`);
          load();
        }
      } catch { /* keep polling */ }
    }, 2500);
  };

  const runScraper = async () => {
    try {
      await api.post('/scraper/run', runForm);
      setRunning(true);
      setJobStatus({ running: true, tail: [] });
      showToast('success', 'Scraper started…');
      startPolling();
    } catch (e) {
      if (e.response?.status === 409) showToast('error', 'A scrape is already running.');
      else showToast('error', 'Failed to start scraper. Is Python on the server PATH?');
    }
  };

  useEffect(() => {
    load();
    // Resume polling if a scrape is already in progress
    api.get('/scraper/run/status').then(({ data }) => {
      setJobStatus(data);
      if (data.running) { setRunning(true); startPolling(); }
    }).catch(() => {});
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  const clearScraped = async () => {
    setConfirmClear(false);
    setClearing(true);
    try {
      const { data } = await api.delete('/scraper/clear-scraped');
      showToast('success', `Deleted ${data.deleted} scraped listings.`);
      load();
    } catch {
      showToast('error', 'Failed to clear scraped listings. Please try again.');
    }
    setClearing(false);
  };

  if (loading) return (
    <div className="card p-6 animate-pulse">
      <div className="h-5 bg-gray-200 rounded w-1/3 mb-4" />
      <div className="h-40 bg-gray-100 rounded" />
    </div>
  );

  if (!stats) return (
    <div className="card p-6 text-gray-500 text-sm flex items-center gap-2">
      <AlertCircle size={16} className="text-red-400" />
      Failed to load scraper stats. Make sure the backend is running.
      <button onClick={load} className="ml-2 text-primary-600 underline text-xs">Retry</button>
    </div>
  );

  const districtData = (stats.by_district || []).slice(0, 10).map(d => ({
    name:    d.district,
    total:   d.count,
    scraped: Number(d.scraped) || 0,
    manual:  d.count - (Number(d.scraped) || 0),
  }));

  const summary = stats.summary || {};

  return (
    <div className="space-y-4">

      {/* Toast notification */}
      {toast && (
        <div className={`flex items-center gap-2 p-3 rounded-xl text-sm font-medium
          ${toast.type === 'success'
            ? 'bg-green-50 text-green-700 border border-green-200'
            : 'bg-red-50 text-red-700 border border-red-200'}`}>
          {toast.type === 'success'
            ? <CheckCircle size={16} />
            : <AlertCircle size={16} />}
          {toast.msg}
        </div>
      )}

      {/* Confirm clear dialog */}
      {confirmClear && (
        <div className="card p-4 border-2 border-red-200 bg-red-50">
          <p className="text-sm font-medium text-red-700 mb-3">
            Are you sure? This will delete <strong>{summary.scraped || 0}</strong> scraped listings from the database.
          </p>
          <div className="flex gap-2">
            <button
              onClick={clearScraped}
              className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700"
            >
              Yes, Delete All Scraped
            </button>
            <button
              onClick={() => setConfirmClear(false)}
              className="px-4 py-2 rounded-lg border border-gray-300 text-gray-600 text-sm hover:bg-gray-50"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'Total Listings',    value: summary.total,   icon: <Building2 size={20} />, color: 'text-blue-600',  bg: 'bg-blue-50' },
          { label: 'Scraped (Web)',     value: summary.scraped, icon: <Globe size={20} />,     color: 'text-amber-600', bg: 'bg-amber-50' },
          { label: 'Manual (Landlord)', value: summary.manual,  icon: <TrendingUp size={20} />,color: 'text-green-600', bg: 'bg-green-50' },
        ].map(s => (
          <div key={s.label} className="card p-4">
            <div className={`w-10 h-10 ${s.bg} ${s.color} rounded-xl flex items-center justify-center mb-2`}>
              {s.icon}
            </div>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">{s.value || 0}</p>
            <p className="text-xs text-gray-500">{s.label}</p>
          </div>
        ))}
      </div>

      {/* District breakdown chart */}
      {districtData.length > 0 && (
        <div className="card p-5">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-4 text-sm">
            Listings by District (Scraped vs Manual)
          </h3>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={districtData} margin={{ left: -20 }}>
              <XAxis dataKey="name" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="scraped" stackId="a" fill="#f59e0b" name="Scraped" />
              <Bar dataKey="manual"  stackId="a" fill="#3b82f6" name="Manual" radius={[3,3,0,0]} />
            </BarChart>
          </ResponsiveContainer>
          <div className="flex gap-4 justify-center mt-2 text-xs text-gray-500">
            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-amber-400 rounded-sm inline-block" /> Scraped</span>
            <span className="flex items-center gap-1"><span className="w-3 h-3 bg-blue-500 rounded-sm inline-block" /> Manual</span>
          </div>
        </div>
      )}

      {/* Recent scraped listings */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-semibold text-gray-900 dark:text-white text-sm">Recent Listings (Last 20)</h3>
          <div className="flex gap-2">
            <button
              onClick={load}
              className="btn-secondary text-xs flex items-center gap-1 py-1.5 px-3"
            >
              <RefreshCw size={12} /> Refresh
            </button>
            <button
              onClick={() => setConfirmClear(true)}
              disabled={clearing || !summary.scraped}
              className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Trash2 size={12} />
              {clearing ? 'Clearing…' : 'Clear Scraped'}
            </button>
          </div>
        </div>

        <div className="space-y-2 max-h-96 overflow-y-auto">
          {(stats.recent || []).map(p => {
            const src = p.address_line || '';
            const isIkman   = src.includes('ikman.lk');
            const isHouseLk = src.includes('house.lk');
            const label = isIkman ? 'Ikman' : isHouseLk ? 'House.lk' : 'Manual';
            const badgeCls = isIkman
              ? 'bg-amber-100 text-amber-700'
              : isHouseLk
              ? 'bg-purple-100 text-purple-700'
              : 'bg-blue-100 text-blue-700';

            return (
              <div key={p.id}
                className="flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors">
                <ListingThumb src={getImageUrl(p.image)} alt={p.title} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{p.title}</p>
                  <p className="text-xs text-gray-500">{p.district} · {p.property_type}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-sm font-semibold text-primary-600">
                    LKR {Number(p.monthly_rent).toLocaleString()}
                  </p>
                  <p className="text-xs text-gray-400">
                    {new Date(p.created_at).toLocaleDateString()}
                  </p>
                </div>
                <span className={`text-xs font-medium px-2 py-1 rounded-full shrink-0 ${badgeCls}`}>
                  {label}
                </span>
              </div>
            );
          })}

          {(stats.recent || []).length === 0 && (
            <div className="text-center py-8 text-gray-400 text-sm">
              <Globe size={32} className="mx-auto mb-2 opacity-30" />
              <p>No listings yet.</p>
              <p className="text-xs mt-1">Run the scraper to add properties.</p>
            </div>
          )}
        </div>
      </div>

      {/* Run the scraper */}
      <div className="card p-5">
        <h3 className="font-semibold text-gray-900 dark:text-white text-sm mb-3 flex items-center gap-2">
          🕷️ Run the Scraper
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div>
            <label className="text-xs font-medium text-gray-500 block mb-1">Site</label>
            <select value={runForm.site} disabled={running}
              onChange={e => setRunForm(f => ({ ...f, site: e.target.value }))}
              className="input-field text-sm py-2">
              <option value="all">Both sites</option>
              <option value="ikman">Ikman.lk</option>
              <option value="houselk">House.lk</option>
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-gray-500 block mb-1">District</label>
            <select value={runForm.district} disabled={running}
              onChange={e => setRunForm(f => ({ ...f, district: e.target.value }))}
              className="input-field text-sm py-2">
              <option value="all">All districts</option>
              {DISTRICTS.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label className="text-xs font-medium text-gray-500 block mb-1">Pages (1–5)</label>
            <input type="number" min={1} max={5} value={runForm.pages} disabled={running}
              onChange={e => setRunForm(f => ({ ...f, pages: e.target.value }))}
              className="input-field text-sm py-2" />
          </div>
          <div className="flex items-end">
            <label className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300 pb-2">
              <input type="checkbox" checked={runForm.noImages} disabled={running}
                onChange={e => setRunForm(f => ({ ...f, noImages: e.target.checked }))}
                className="accent-primary-600" />
              No images (faster)
            </label>
          </div>
        </div>

        <div className="flex items-center gap-3 mt-4">
          <button onClick={runScraper} disabled={running}
            className="btn-primary flex items-center gap-2 text-sm disabled:opacity-60">
            {running ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
            {running ? 'Scraping…' : 'Run Scraper'}
          </button>
          <span className="text-xs text-gray-400 font-mono truncate">
            python scraper.py --pages {runForm.pages} --site {runForm.site}
            {runForm.district !== 'all' ? ` --district ${runForm.district}` : ''}
            {runForm.noImages ? ' --no-images' : ''}
          </span>
        </div>

        {/* Live status / log */}
        {jobStatus && (running || jobStatus.tail?.length > 0) && (
          <div className="mt-4">
            {!running && jobStatus.saved != null && (
              <p className="text-sm font-medium text-green-700 mb-2">
                ✓ Saved {jobStatus.saved} · skipped {jobStatus.skipped} (duplicates)
              </p>
            )}
            {jobStatus.error && (
              <p className="text-sm font-medium text-red-600 mb-2">⚠ {jobStatus.error}</p>
            )}
            <div className="bg-gray-900 text-gray-200 rounded-xl p-3 max-h-44 overflow-y-auto font-mono text-[11px] leading-relaxed">
              {(jobStatus.tail || []).length === 0
                ? <span className="text-gray-500">Starting…</span>
                : jobStatus.tail.map((l, i) => <div key={i} className="whitespace-pre-wrap break-all">{l}</div>)}
            </div>
          </div>
        )}

        <p className="text-xs text-gray-400 mt-3">
          Runs on the server. A scrape takes ~1–4 min depending on pages and image downloads;
          you can leave this page — progress resumes when you return.
        </p>
      </div>
    </div>
  );
}
