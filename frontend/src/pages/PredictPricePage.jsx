import React, { useState } from 'react';
import { TrendingUp, Info, MapPin, Bed, Bath, Home, CheckCircle } from 'lucide-react';
import { toast } from 'react-toastify';
import api from '../api/axios';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell, ReferenceLine } from 'recharts';
import AILoader from '../components/ui/AILoader';
import LoadingButton from '../components/ui/LoadingButton';

const DISTRICTS = [
  'Colombo','Gampaha','Kalutara',
  'Kandy','Matale','Nuwara Eliya',
  'Galle','Matara','Hambantota',
  'Jaffna','Kurunegala','Anuradhapura',
  'Ratnapura','Badulla','Kegalle',
  'Trincomalee','Batticaloa',
];

export default function PredictPricePage() {
  const [form, setForm] = useState({
    district: 'Colombo', property_type: 'apartment',
    bedrooms: 2, bathrooms: 1,
    furnished: 'semi-furnished',
  });
  const [result, setResult]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true); setError('');
    try {
      const { data } = await api.post('/predictions/price', form);
      setResult(data);
    } catch (err) {
      const msg = err.response?.data?.error || 'Prediction failed. Make sure the AI service is running.';
      setError(msg);
      toast.error(msg);
    }
    setLoading(false);
  };

  const chartData = result ? [
    { name: 'Low',       value: Math.round(result.price_range?.low  || result.predicted_price * 0.7), fill: '#94a3b8' },
    { name: 'Predicted', value: Math.round(result.predicted_price),                                    fill: '#2563eb' },
    { name: 'High',      value: Math.round(result.price_range?.high || result.predicted_price * 1.3), fill: '#94a3b8' },
  ] : [];

  const confidence  = result?.confidence  ?? 0;
  const confColor   = confidence > 0.6 ? 'bg-green-500' : confidence > 0.4 ? 'bg-yellow-500' : 'bg-orange-500';
  const confLabel   = confidence > 0.6 ? 'Good' : confidence > 0.4 ? 'Moderate' : 'Low';

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
          <TrendingUp size={32} className="text-green-600" /> Rental Price Prediction
        </h1>
        <p className="text-gray-500 mt-2">
          AI-powered price estimation using Gradient Boosting trained on real Sri Lankan rental listings.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* ── Form ─────────────────────────────────────────── */}
        <div className="card p-6">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Property Details</h2>
          <form onSubmit={handleSubmit} className="space-y-4">

            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">
                <MapPin size={13} className="inline mr-1" />District
              </label>
              <select value={form.district}
                onChange={e => setForm({ ...form, district: e.target.value })}
                className="input-field">
                {DISTRICTS.map(d => <option key={d}>{d}</option>)}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">
                  <Home size={13} className="inline mr-1" />Type
                </label>
                <select value={form.property_type}
                  onChange={e => setForm({ ...form, property_type: e.target.value })}
                  className="input-field">
                  {['apartment','house','room','villa','commercial'].map(t =>
                    <option key={t} className="capitalize">{t}</option>)}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">
                  Furnished Status
                </label>
                <select value={form.furnished}
                  onChange={e => setForm({ ...form, furnished: e.target.value })}
                  className="input-field">
                  {['unfurnished','semi-furnished','furnished'].map(f => <option key={f}>{f}</option>)}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">
                  <Bed size={13} className="inline mr-1" />Bedrooms
                </label>
                <input type="number" min={0} max={10} value={form.bedrooms}
                  onChange={e => setForm({ ...form, bedrooms: Number(e.target.value) })}
                  className="input-field" />
              </div>
              <div>
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">
                  <Bath size={13} className="inline mr-1" />Bathrooms
                </label>
                <input type="number" min={0} max={6} value={form.bathrooms}
                  onChange={e => setForm({ ...form, bathrooms: Number(e.target.value) })}
                  className="input-field" />
              </div>
            </div>

            {error && (
              <p className="text-red-600 text-sm bg-red-50 dark:bg-red-900/20 p-3 rounded-xl">{error}</p>
            )}
            <LoadingButton type="submit" loading={loading} loadingText="Predicting…"
              className="btn-primary w-full text-base py-3">
              🤖 Predict Rental Price
            </LoadingButton>
          </form>
        </div>

        {/* ── Result ───────────────────────────────────────── */}
        <div>
          {loading ? (
            <div className="card p-8 h-full flex flex-col items-center justify-center">
              <AILoader
                icon={<TrendingUp size={22} />}
                messages={[
                  'Analysing property features…',
                  'Comparing district prices…',
                  'Calculating fair value…',
                ]}
              />
              {/* Animated bars building up */}
              <div className="flex items-end gap-2 h-20 mt-2">
                {[35, 60, 85, 60, 35].map((h, i) => (
                  <div key={i}
                    className="w-6 rounded-t-md bg-primary-200 dark:bg-primary-900/40 animate-pulse"
                    style={{ height: `${h}%`, animationDelay: `${i * 0.12}s` }} />
                ))}
              </div>
            </div>
          ) : result ? (
            <div className="space-y-4">
              {/* Main price card */}
              <div className="card p-6 text-center bg-gradient-to-br from-blue-50 to-white dark:from-blue-900/20 dark:to-gray-800">
                <p className="text-sm text-gray-500 mb-1">Predicted Monthly Rent</p>
                <p className="text-4xl font-extrabold text-primary-600">
                  LKR {Number(result.predicted_price).toLocaleString()}
                </p>
                {result.price_range && (
                  <p className="text-sm text-gray-500 mt-2">
                    Range: LKR {Math.max(0, Math.round(result.price_range.low)).toLocaleString()}
                    {' – '}
                    LKR {Math.round(result.price_range.high).toLocaleString()}
                  </p>
                )}
                {/* Confidence bar */}
                <div className="mt-4 flex items-center gap-3">
                  <div className="flex-1 bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div className={`h-2 rounded-full ${confColor} transition-all`}
                      style={{ width: `${Math.round(confidence * 100)}%` }} />
                  </div>
                  <span className="text-xs font-semibold text-gray-600 dark:text-gray-400 w-20 text-left">
                    {confLabel} ({Math.round(confidence * 100)}%)
                  </span>
                </div>
              </div>

              {/* Price range chart */}
              <div className="card p-4">
                <h3 className="font-medium text-gray-900 dark:text-white mb-3 text-sm">Price Range Estimate</h3>
                <ResponsiveContainer width="100%" height={160}>
                  <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
                    <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 10 }} tickFormatter={v => `${Math.round(v/1000)}k`} />
                    <Tooltip formatter={v => [`LKR ${Number(v).toLocaleString()}`, 'Rent']} />
                    <Bar dataKey="value" radius={[4,4,0,0]}>
                      {chartData.map((e, i) => <Cell key={i} fill={e.fill} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Top factors */}
              {result.top_3_factors?.length > 0 && (
                <div className="card p-4">
                  <h3 className="font-medium text-gray-900 dark:text-white mb-3 text-sm">Key Price Drivers</h3>
                  <ul className="space-y-2">
                    {result.top_3_factors.map((f, i) => (
                      <li key={i} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-400">
                        <CheckCircle size={14} className="text-green-500 mt-0.5 shrink-0" />
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Model info */}
              <div className="card p-4 flex items-start gap-3 bg-blue-50 dark:bg-blue-900/10 border border-blue-100 dark:border-blue-900/30">
                <Info size={16} className="text-blue-500 shrink-0 mt-0.5" />
                <div className="text-xs text-gray-600 dark:text-gray-400 space-y-0.5">
                  <p>
                    <span className="font-semibold">Model:</span>{' '}
                    {result.model_info?.name || 'GradientBoosting'} v{result.model_version}
                  </p>
                  <p>
                    <span className="font-semibold">Trained on:</span>{' '}
                    {result.model_info?.training_samples || 324} real Sri Lankan listings
                    {' '}(Test R²: {((result.model_info?.r2 || 0) * 100).toFixed(1)}%)
                  </p>
                  <p className="text-gray-400 italic">
                    Use as a reference only — actual rents vary by exact location and condition.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="card p-8 h-full flex flex-col items-center justify-center text-gray-400 text-center">
              <TrendingUp size={48} className="mb-4 opacity-30" />
              <p className="font-medium text-gray-600 dark:text-gray-300">Fill in the form to get an AI price prediction</p>
              <p className="text-sm mt-1">Results will appear here</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
