import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { registerUser, clearError } from '../store/slices/authSlice';
import { Home } from 'lucide-react';
import LoadingButton from '../components/ui/LoadingButton';

export default function RegisterPage() {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const { loading, error, token } = useSelector((s) => s.auth);
  const [form, setForm] = useState({ full_name: '', email: '', password: '', role: 'renter' });

  useEffect(() => { if (token) navigate('/'); }, [token, navigate]);
  useEffect(() => { return () => dispatch(clearError()); }, [dispatch]);

  const handleSubmit = (e) => {
    e.preventDefault();
    // The onboarding modal decides whether to show based on backend profile
    // state (OnboardingModal.jsx), so no flag needs to be set here.
    dispatch(registerUser(form));
  };

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-8">
      <div className="card w-full max-w-md p-8">
        <div className="flex items-center gap-2 justify-center mb-6 text-primary-600 font-bold text-2xl">
          <Home size={28} /> SmartRentAI
        </div>
        <h1 className="text-2xl font-bold text-center mb-1 text-gray-900 dark:text-white">Create account</h1>
        <p className="text-center text-gray-500 text-sm mb-8">Join thousands of renters in Sri Lanka</p>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-600 rounded-xl px-4 py-3 mb-4 text-sm">{error}</div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Full Name</label>
            <input type="text" required value={form.full_name}
              onChange={e => setForm({ ...form, full_name: e.target.value })}
              className="input-field" placeholder="John Doe" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input type="email" required value={form.email}
              onChange={e => setForm({ ...form, email: e.target.value })}
              className="input-field" placeholder="you@example.com" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input type="password" required minLength={6} value={form.password}
              onChange={e => setForm({ ...form, password: e.target.value })}
              className="input-field" placeholder="Min. 6 characters" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">I am a…</label>
            <div className="grid grid-cols-2 gap-3">
              {['renter','landlord'].map(r => (
                <label key={r}
                  className={`flex items-center justify-center gap-2 border-2 rounded-xl py-3 cursor-pointer transition-all
                    ${form.role === r ? 'border-primary-500 bg-primary-50 text-primary-600' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}>
                  <input type="radio" name="role" value={r} checked={form.role === r}
                    onChange={() => setForm({ ...form, role: r })} className="sr-only" />
                  <span className="font-medium capitalize">{r}</span>
                </label>
              ))}
            </div>
          </div>
          <LoadingButton type="submit" loading={loading} loadingText="Creating account…"
            className="btn-primary w-full mt-2">
            Create Account
          </LoadingButton>
        </form>

        <div className="mt-6 text-center text-sm text-gray-600">
          Already have an account?{' '}
          <Link to="/login" className="text-primary-600 font-medium hover:underline">Sign in</Link>
        </div>
      </div>
    </div>
  );
}
