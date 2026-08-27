import React, { useEffect, useState } from 'react';
import { useSelector } from 'react-redux';
import { User, Save, Sparkles } from 'lucide-react';
import api from '../api/axios';
import { toast } from 'react-toastify';
import PreferencesWizard from '../components/profile/PreferencesWizard';
import ProfileSkeleton from '../components/ui/skeletons/ProfileSkeleton';
import LoadingButton from '../components/ui/LoadingButton';

export default function ProfilePage() {
  const { user }  = useSelector((s) => s.auth);
  const [profile, setProfile] = useState({ full_name: user?.full_name || '', phone: '' });
  const [prefs, setPrefs]     = useState(null);
  const [loaded, setLoaded]   = useState(false);
  const [saving, setSaving]   = useState(false);

  useEffect(() => {
    api.get('/users/preferences')
      .then(({ data }) => setPrefs(data || {}))
      .catch(() => setPrefs({}))
      .finally(() => setLoaded(true));
  }, []);

  const saveProfile = async (e) => {
    e.preventDefault(); setSaving(true);
    try {
      await api.put('/users/profile', profile);
      toast.success('Profile updated!');
    } catch { toast.error('Update failed'); }
    setSaving(false);
  };

  if (!loaded) return <ProfileSkeleton />;

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
        <User size={28} className="text-primary-600" /> My Profile
      </h1>

      {/* Account info */}
      <div className="card p-6">
        <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Account Information</h2>
        <form onSubmit={saveProfile} className="space-y-4">
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">Full Name</label>
            <input value={profile.full_name} onChange={e => setProfile({ ...profile, full_name: e.target.value })} className="input-field" />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">Email</label>
            <input value={user?.email} disabled className="input-field opacity-60" />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">Phone</label>
            <input value={profile.phone} onChange={e => setProfile({ ...profile, phone: e.target.value })} className="input-field" placeholder="+94 7X XXX XXXX" />
          </div>
          <div className="flex items-center gap-3">
            <span className="badge bg-primary-100 text-primary-700 capitalize">{user?.role}</span>
          </div>
          <LoadingButton type="submit" loading={saving} loadingText="Saving…" className="btn-primary">
            <Save size={16} /> Save Profile
          </LoadingButton>
        </form>
      </div>

      {/* Lifestyle preferences — drives "For You" recommendations */}
      <div className="card p-6">
        <h2 className="font-semibold text-gray-900 dark:text-white mb-1 flex items-center gap-2">
          <Sparkles size={18} className="text-primary-600" /> Lifestyle &amp; Rental Preferences
        </h2>
        <p className="text-sm text-gray-500 mb-6">
          These power your personalized <strong>“For You”</strong> recommendations.
        </p>
        <PreferencesWizard initialValues={prefs} finishLabel="Save Preferences" />
      </div>
    </div>
  );
}
