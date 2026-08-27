import React, { useState, useEffect } from 'react';
import { useSelector } from 'react-redux';
import { useNavigate } from 'react-router-dom';
import { X, Sparkles } from 'lucide-react';
import api from '../../api/axios';
import PreferencesWizard from './PreferencesWizard';

/**
 * Shows the personalization onboarding ONCE for a logged-in user who hasn't
 * completed it yet. Authoritative source is the backend (onboarding_completed /
 * profession on user_preferences); a per-user localStorage key remembers a
 * "skip" so it never re-nags on refresh. Skippable.
 */
export default function OnboardingModal() {
  const token = useSelector(s => s.auth.token);
  const user  = useSelector(s => s.auth.user);
  const navigate = useNavigate();
  const [show, setShow] = useState(false);

  const seenKey = user?.id ? `onboarding_seen_${user.id}` : null;

  useEffect(() => {
    if (!token || !user?.id) { setShow(false); return; }
    // Already dismissed/seen in this browser for this user → never auto-show
    if (localStorage.getItem(seenKey) === '1') { setShow(false); return; }

    let active = true;
    api.get('/users/preferences')
      .then(({ data }) => {
        if (!active) return;
        const done = data && (data.onboarding_completed || data.profession);
        if (done) {
          localStorage.setItem(seenKey, '1');   // already onboarded — remember it
          setShow(false);
        } else {
          setShow(true);                         // first time → show once
        }
      })
      .catch(() => { if (active) setShow(false); });

    return () => { active = false; };
  }, [token, user, seenKey]);

  if (!token || !show) return null;

  const markSeen = () => { if (seenKey) localStorage.setItem(seenKey, '1'); };

  const close = () => { markSeen(); setShow(false); };               // skip / X
  const finish = () => { markSeen(); setShow(false); navigate('/recommendations'); };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[92vh] overflow-y-auto p-6 relative">
        <button onClick={close} aria-label="Close"
          className="absolute top-4 right-4 text-gray-400 hover:text-gray-600">
          <X size={20} />
        </button>

        <div className="mb-6 pr-8">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <Sparkles size={22} className="text-primary-600" /> Welcome! Let's personalize your search
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Answer a few quick questions to unlock your <strong>“For You”</strong> recommendations.
            You can skip and finish this anytime from your profile.
          </p>
        </div>

        <PreferencesWizard
          initialValues={{}}
          finishLabel="Finish & See Recommendations"
          onComplete={finish}
        />

        <button onClick={close}
          className="mt-5 text-sm text-gray-400 hover:text-gray-600 w-full text-center">
          Skip for now
        </button>
      </div>
    </div>
  );
}
