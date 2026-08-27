import React, { useState } from 'react';
import { User, MapPin, SlidersHorizontal, Check, ChevronLeft, ChevronRight, Car, Baby } from 'lucide-react';
import api from '../../api/axios';
import { toast } from 'react-toastify';
import LoadingButton from '../ui/LoadingButton';

// ── Option sets (kept in one place; reused by ProfilePage + onboarding modal) ──
export const PROFESSIONS = [
  'Doctor', 'Engineer', 'Teacher', 'Student', 'Business Owner',
  'IT Professional', 'Government Employee', 'Lawyer', 'Nurse', 'Other',
];

export const AGE_GROUPS = ['18-25', '26-35', '36-45', '46-60', '60+'];

export const FAMILY_SIZES = [
  { value: 'Single',       sub: '1 person' },
  { value: 'Couple',       sub: '2 people' },
  { value: 'Small Family', sub: '3–4 people' },
  { value: 'Large Family', sub: '5+ people' },
];

export const PROPERTY_TYPES = ['apartment', 'house', 'room', 'villa'];

export const DISTRICTS = [
  'Colombo', 'Gampaha', 'Kalutara', 'Kandy', 'Matale', 'Nuwara Eliya',
  'Galle', 'Matara', 'Hambantota', 'Jaffna', 'Kilinochchi', 'Mannar',
  'Mullaitivu', 'Vavuniya', 'Trincomalee', 'Batticaloa', 'Ampara',
  'Kurunegala', 'Puttalam', 'Anuradhapura', 'Polonnaruwa', 'Badulla',
  'Monaragala', 'Ratnapura', 'Kegalle',
];

const PRIORITIES = [
  { key: 'priority_safety',    label: 'Safety',            hint: 'SafeRent score weight' },
  { key: 'priority_price',     label: 'Price',             hint: 'budget sensitivity' },
  { key: 'priority_transport', label: 'Transport',         hint: 'near bus / train' },
  { key: 'priority_hospital',  label: 'Hospital Access',   hint: 'near medical facilities' },
  { key: 'priority_space',     label: 'Space',             hint: 'bedrooms / size' },
];

const DEFAULTS = {
  profession: '', age_group: '', family_size: '', has_children: false, has_vehicle: false,
  current_district: '', current_city: '', current_rent_budget: '',
  preferred_districts: [], preferred_property_type: '',
  priority_safety: 3, priority_price: 3, priority_transport: 3, priority_hospital: 3, priority_space: 3,
};

// Small reusable pieces ───────────────────────────────────────
function Pill({ active, onClick, children }) {
  return (
    <button type="button" onClick={onClick}
      className={`px-3 py-2 rounded-xl border-2 text-sm font-medium transition-all
        ${active ? 'border-primary-500 bg-primary-50 text-primary-600'
                 : 'border-gray-200 text-gray-600 hover:border-gray-300 dark:border-gray-700 dark:text-gray-300'}`}>
      {children}
    </button>
  );
}

function Toggle({ active, onClick, icon, label }) {
  return (
    <button type="button" onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border-2 text-sm font-medium transition-all
        ${active ? 'border-primary-500 bg-primary-50 text-primary-600'
                 : 'border-gray-200 text-gray-500 hover:border-gray-300 dark:border-gray-700'}`}>
      {icon} {label}: <span className="font-bold">{active ? 'Yes' : 'No'}</span>
    </button>
  );
}

const STEPS = [
  { n: 1, title: 'Tell us about yourself', icon: <User size={16} /> },
  { n: 2, title: 'Your rental needs',      icon: <MapPin size={16} /> },
  { n: 3, title: 'What matters most?',     icon: <SlidersHorizontal size={16} /> },
];

/**
 * PreferencesWizard — 3-step onboarding/profile form.
 * @param {object}   initialValues  existing prefs from the API (preferred_districts may be a CSV string)
 * @param {function} onComplete     called after a successful save
 * @param {string}   finishLabel    label for the final button
 */
export default function PreferencesWizard({ initialValues = {}, onComplete, finishLabel = 'Save & Finish' }) {
  const [step, setStep]   = useState(1);
  const [saving, setSaving] = useState(false);

  const [v, setV] = useState(() => {
    const merged = { ...DEFAULTS, ...initialValues };
    // CSV → array for the multi-select
    if (typeof merged.preferred_districts === 'string') {
      merged.preferred_districts = merged.preferred_districts
        ? merged.preferred_districts.split(',').map(s => s.trim()).filter(Boolean)
        : [];
    }
    merged.has_children = !!merged.has_children;
    merged.has_vehicle = !!merged.has_vehicle;
    return merged;
  });

  const set = (key, val) => setV(p => ({ ...p, [key]: val }));

  const toggleDistrict = (d) => {
    setV(p => {
      const has = p.preferred_districts.includes(d);
      if (has) return { ...p, preferred_districts: p.preferred_districts.filter(x => x !== d) };
      if (p.preferred_districts.length >= 3) return p; // cap at 3
      return { ...p, preferred_districts: [...p.preferred_districts, d] };
    });
  };

  const save = async () => {
    setSaving(true);
    try {
      await api.put('/users/preferences', {
        ...v,
        preferred_districts: v.preferred_districts,   // array → backend stores CSV
        onboarding_completed: 1,
      });
      toast.success('Preferences saved! Your recommendations will update.');
      onComplete?.(v);
    } catch {
      toast.error('Could not save preferences');
    }
    setSaving(false);
  };

  return (
    <div>
      {/* Stepper */}
      <div className="flex items-center justify-between mb-6">
        {STEPS.map((s, i) => (
          <React.Fragment key={s.n}>
            <div className="flex items-center gap-2">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all
                ${step > s.n ? 'bg-green-500 text-white'
                  : step === s.n ? 'bg-primary-600 text-white'
                  : 'bg-gray-200 text-gray-500 dark:bg-gray-700'}`}>
                {step > s.n ? <Check size={16} /> : s.n}
              </div>
              <span className={`text-sm font-medium hidden sm:block ${step === s.n ? 'text-primary-600' : 'text-gray-400'}`}>
                {s.title}
              </span>
            </div>
            {i < STEPS.length - 1 && <div className={`flex-1 h-0.5 mx-2 ${step > s.n ? 'bg-green-500' : 'bg-gray-200 dark:bg-gray-700'}`} />}
          </React.Fragment>
        ))}
      </div>

      {/* ── Step 1: Basic info ──────────────────────────────── */}
      {step === 1 && (
        <div className="space-y-5">
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">Profession</label>
            <select value={v.profession} onChange={e => set('profession', e.target.value)} className="input-field">
              <option value="">Select your profession…</option>
              {PROFESSIONS.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">Age group</label>
            <div className="flex flex-wrap gap-2">
              {AGE_GROUPS.map(a => (
                <Pill key={a} active={v.age_group === a} onClick={() => set('age_group', a)}>{a}</Pill>
              ))}
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">Family size</label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {FAMILY_SIZES.map(f => (
                <button key={f.value} type="button" onClick={() => set('family_size', f.value)}
                  className={`px-3 py-2.5 rounded-xl border-2 text-sm transition-all text-left
                    ${v.family_size === f.value ? 'border-primary-500 bg-primary-50 text-primary-600'
                      : 'border-gray-200 text-gray-600 hover:border-gray-300 dark:border-gray-700'}`}>
                  <span className="font-semibold block">{f.value}</span>
                  <span className="text-xs text-gray-400">{f.sub}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            <Toggle active={v.has_children} onClick={() => set('has_children', !v.has_children)} icon={<Baby size={16} />} label="Children" />
            <Toggle active={v.has_vehicle}  onClick={() => set('has_vehicle', !v.has_vehicle)}  icon={<Car size={16} />}  label="Vehicle" />
          </div>
        </div>
      )}

      {/* ── Step 2: Current situation / needs ───────────────── */}
      {step === 2 && (
        <div className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">Current district</label>
              <select value={v.current_district} onChange={e => set('current_district', e.target.value)} className="input-field">
                <option value="">Select district…</option>
                {DISTRICTS.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">Current city / town</label>
              <input value={v.current_city} onChange={e => set('current_city', e.target.value)}
                className="input-field" placeholder="e.g. Nugegoda" />
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">Monthly budget (max, LKR)</label>
            <input type="number" min="0" value={v.current_rent_budget}
              onChange={e => set('current_rent_budget', e.target.value)}
              className="input-field" placeholder="e.g. 80000" />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">
              Preferred districts <span className="text-xs text-gray-400">(pick up to 3 — {v.preferred_districts.length}/3)</span>
            </label>
            <div className="flex flex-wrap gap-2 max-h-44 overflow-y-auto p-1">
              {DISTRICTS.map(d => {
                const active = v.preferred_districts.includes(d);
                const disabled = !active && v.preferred_districts.length >= 3;
                return (
                  <button key={d} type="button" onClick={() => toggleDistrict(d)} disabled={disabled}
                    className={`px-3 py-1.5 rounded-full border-2 text-xs font-medium transition-all
                      ${active ? 'border-primary-500 bg-primary-500 text-white'
                        : disabled ? 'border-gray-100 text-gray-300 cursor-not-allowed dark:border-gray-800'
                        : 'border-gray-200 text-gray-600 hover:border-primary-300 dark:border-gray-700'}`}>
                    {d}
                  </button>
                );
              })}
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-2">Preferred property type</label>
            <div className="flex flex-wrap gap-2">
              {PROPERTY_TYPES.map(t => (
                <Pill key={t} active={v.preferred_property_type === t} onClick={() => set('preferred_property_type', t)}>
                  <span className="capitalize">{t}</span>
                </Pill>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Step 3: Lifestyle priorities ────────────────────── */}
      {step === 3 && (
        <div className="space-y-5">
          <p className="text-sm text-gray-500">Rate how important each factor is to you (1 = not important, 5 = essential).</p>
          {PRIORITIES.map(p => (
            <div key={p.key}>
              <div className="flex justify-between items-baseline mb-1">
                <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {p.label} <span className="text-xs text-gray-400">· {p.hint}</span>
                </label>
                <span className="text-sm font-bold text-primary-600">{v[p.key]}/5</span>
              </div>
              <input type="range" min="1" max="5" step="1" value={v[p.key]}
                onChange={e => set(p.key, Number(e.target.value))}
                className="w-full accent-primary-600" />
            </div>
          ))}
        </div>
      )}

      {/* ── Navigation ──────────────────────────────────────── */}
      <div className="flex justify-between items-center mt-8">
        <button type="button" onClick={() => setStep(s => Math.max(1, s - 1))}
          disabled={step === 1}
          className="btn-secondary flex items-center gap-1 disabled:opacity-40">
          <ChevronLeft size={16} /> Back
        </button>

        {step < 3 ? (
          <button type="button" onClick={() => setStep(s => Math.min(3, s + 1))}
            className="btn-primary flex items-center gap-1">
            Next <ChevronRight size={16} />
          </button>
        ) : (
          <LoadingButton onClick={save} loading={saving} loadingText="Saving…"
            className="btn-primary">
            <Check size={16} /> {finishLabel}
          </LoadingButton>
        )}
      </div>
    </div>
  );
}
