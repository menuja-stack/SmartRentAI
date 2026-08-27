import React, { useEffect, useState } from 'react';
import { Users, Home, TrendingUp, MessageCircle, RefreshCw } from 'lucide-react';
import api from '../api/axios';
import DatasetUpload from '../components/dashboard/DatasetUpload';
import ScraperPanel  from '../components/dashboard/ScraperPanel';
import DashboardSkeleton from '../components/ui/skeletons/DashboardSkeleton';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';

export default function AdminDashboardPage() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError]     = useState('');

  const load = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError('');
    try {
      const { data: d } = await api.get('/analytics/dashboard');
      setData(d);
    } catch (e) {
      const msg = e.response?.data?.error || e.message || 'Failed to load analytics.';
      setError(msg);
      // Keep old data visible on refresh failure
    }
    setLoading(false);
    setRefreshing(false);
  };

  useEffect(() => { load(); }, []);

  // Skeleton only on first load — never on refresh (page stays visible)
  if (loading) return <DashboardSkeleton />;

  const stats = data ? [
    { label: 'Total Users',     value: data.stats.total_users,       icon: <Users size={24} />,        color: 'text-blue-600',  bg: 'bg-blue-50' },
    { label: 'Active Listings', value: data.stats.total_properties,  icon: <Home size={24} />,         color: 'text-green-600', bg: 'bg-green-50' },
    { label: 'AI Predictions',  value: data.stats.total_predictions, icon: <TrendingUp size={24} />,   color: 'text-purple-600',bg: 'bg-purple-50' },
    { label: 'Chat Sessions',   value: data.stats.total_chats,       icon: <MessageCircle size={24} />, color: 'text-amber-600', bg: 'bg-amber-50' },
  ] : [];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Admin Dashboard</h1>
        <button
          onClick={() => load(true)}
          disabled={refreshing}
          className="btn-secondary flex items-center gap-2 text-sm disabled:opacity-50"
        >
          <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
          {refreshing ? 'Refreshing…' : 'Refresh'}
        </button>
      </div>

      {/* Error banner — page stays visible */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-sm">
          {error} — <button onClick={() => load(true)} className="underline">Try again</button>
        </div>
      )}

      {data && (
        <>
          {/* Stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            {stats.map(s => (
              <div key={s.label} className="card p-5">
                <div className={`w-12 h-12 rounded-xl ${s.bg} ${s.color} flex items-center justify-center mb-3`}>
                  {s.icon}
                </div>
                <p className="text-2xl font-bold text-gray-900 dark:text-white">{s.value}</p>
                <p className="text-sm text-gray-500">{s.label}</p>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            {/* Top cities */}
            <div className="card p-5">
              <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Listings by City</h2>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={data.top_cities}>
                  <XAxis dataKey="city" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="listings" fill="#3b82f6" radius={[4,4,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Rent trend */}
            <div className="card p-5">
              <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Average Rent Trend</h2>
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={data.rent_trend}>
                  <XAxis dataKey="month" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `${Math.round(v/1000)}k`} />
                  <Tooltip formatter={v => `LKR ${Number(v).toLocaleString()}`} />
                  <Line type="monotone" dataKey="avg_rent" stroke="#3b82f6" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Role breakdown */}
          <div className="card p-5 mb-6">
            <h2 className="font-semibold text-gray-900 dark:text-white mb-4">User Roles</h2>
            <div className="flex gap-6">
              {data.role_breakdown.map(r => (
                <div key={r.role} className="text-center">
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{r.count}</p>
                  <p className="text-sm text-gray-500 capitalize">{r.role}s</p>
                </div>
              ))}
            </div>
          </div>
        </>
      )}

      {/* Scraper Panel — always visible even if analytics fails */}
      <div className="mb-6">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          🕷️ Web Scraper Dashboard
        </h2>
        <ScraperPanel />
      </div>

      {/* Dataset Upload — always visible */}
      <div>
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          📂 AI Model — Upload Dataset
        </h2>
        <DatasetUpload />
      </div>
    </div>
  );
}
