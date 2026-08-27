import React, { useState } from 'react';
import { Upload, CheckCircle, AlertCircle, Loader } from 'lucide-react';

const AI_URL = process.env.REACT_APP_LOCATION_AI_URL || 'http://localhost:8004';

export default function DatasetUpload() {
  const [file, setFile]       = useState(null);
  const [status, setStatus]   = useState(null); // null | 'uploading' | 'training' | 'done' | 'error'
  const [message, setMessage] = useState('');
  const [metrics, setMetrics] = useState(null);

  const handleUpload = async () => {
    if (!file) return;
    setStatus('uploading');
    setMessage('Uploading CSV…');

    try {
      const fd = new FormData();
      fd.append('file', file);

      const uploadRes = await fetch(`${AI_URL}/upload-dataset`, { method: 'POST', body: fd });
      const uploadData = await uploadRes.json();

      if (!uploadRes.ok) {
        setStatus('error');
        setMessage(uploadData.error || 'Upload failed');
        return;
      }

      setStatus('training');
      setMessage(`Dataset uploaded (${uploadData.columns?.length} columns). Training model — this takes 1–3 minutes…`);

      const trainRes  = await fetch(`${AI_URL}/train`, { method: 'POST', signal: AbortSignal.timeout(300000) });
      const trainData = await trainRes.json();

      if (!trainRes.ok) {
        setStatus('error');
        setMessage(trainData.error || 'Training failed');
        return;
      }

      setStatus('done');
      setMessage('Model trained successfully!');
      setMetrics(trainData.metrics);
    } catch (err) {
      setStatus('error');
      setMessage(err.message || 'Unknown error');
    }
  };

  return (
    <div className="card p-6">
      <h2 className="font-semibold text-gray-900 dark:text-white mb-1 flex items-center gap-2">
        <Upload size={18} className="text-primary-600" /> Upload Disaster Dataset
      </h2>
      <p className="text-sm text-gray-500 mb-4">
        Upload your Sri Lankan disaster/weather CSV to retrain the SafeRent AI model.
        Required columns: <code className="bg-gray-100 dark:bg-gray-800 px-1 rounded text-xs">district, rainfall_mm, humidity_pct, temp_avg_c, disaster_occurred</code>
      </p>

      <label className={`flex flex-col items-center justify-center border-2 border-dashed rounded-xl p-8 cursor-pointer transition-colors
        ${file ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20' : 'border-gray-300 hover:border-primary-400'}`}>
        <Upload size={28} className={file ? 'text-primary-600' : 'text-gray-400'} />
        <span className="text-sm mt-2 text-gray-600 dark:text-gray-400">
          {file ? file.name : 'Click to choose CSV file'}
        </span>
        {file && (
          <span className="text-xs text-gray-400 mt-1">
            {(file.size / 1024 / 1024).toFixed(1)} MB
          </span>
        )}
        <input type="file" accept=".csv" className="hidden"
          onChange={e => { setFile(e.target.files[0]); setStatus(null); setMetrics(null); }} />
      </label>

      <button
        onClick={handleUpload}
        disabled={!file || status === 'uploading' || status === 'training'}
        className="btn-primary w-full mt-4 flex items-center justify-center gap-2 disabled:opacity-50">
        {(status === 'uploading' || status === 'training')
          ? <><Loader size={16} className="animate-spin" /> {status === 'uploading' ? 'Uploading…' : 'Training model…'}</>
          : <><Upload size={16} /> Upload & Train</>}
      </button>

      {/* Status */}
      {status && (
        <div className={`mt-4 p-3 rounded-xl flex items-start gap-2 text-sm
          ${status === 'done'  ? 'bg-green-50 text-green-700 border border-green-200' :
            status === 'error' ? 'bg-red-50 text-red-700 border border-red-200' :
            'bg-blue-50 text-blue-700 border border-blue-200'}`}>
          {status === 'done'    && <CheckCircle size={16} className="shrink-0 mt-0.5" />}
          {status === 'error'   && <AlertCircle size={16} className="shrink-0 mt-0.5" />}
          {(status === 'uploading' || status === 'training') && <Loader size={16} className="shrink-0 mt-0.5 animate-spin" />}
          <span>{message}</span>
        </div>
      )}

      {/* Metrics */}
      {metrics && (
        <div className="mt-4 grid grid-cols-4 gap-3">
          {[
            ['AUC-ROC',   metrics.auc_roc],
            ['Accuracy',  metrics.accuracy],
            ['Precision', metrics.precision],
            ['F1 Score',  metrics.f1],
          ].map(([l, v]) => (
            <div key={l} className="bg-gray-50 dark:bg-gray-800 rounded-xl p-3 text-center">
              <p className="text-lg font-bold text-primary-600">{v}</p>
              <p className="text-xs text-gray-500">{l}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
