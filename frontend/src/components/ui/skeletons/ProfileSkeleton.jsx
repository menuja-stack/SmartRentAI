import React from 'react';
import { Bar, Circle } from './Skeleton';

/** Mirrors ProfilePage: heading, account card with fields, preferences card. */
export default function ProfileSkeleton() {
  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-6">
      <div className="flex items-center gap-3">
        <Circle size="w-8 h-8" />
        <Bar className="h-8 w-44" />
      </div>

      {/* Account card */}
      <div className="card p-6 space-y-5">
        <Bar className="h-4 w-44" />
        <div className="flex items-center gap-4">
          <Circle size="w-14 h-14" />
          <div className="flex-1 space-y-2">
            <Bar className="h-4 w-1/2" />
            <Bar className="h-3 w-2/3" />
          </div>
        </div>
        {[...Array(3)].map((_, i) => (
          <div key={i} className="space-y-2">
            <Bar className="h-3 w-24" />
            <Bar className="h-11 w-full rounded-xl" />
          </div>
        ))}
        <Bar className="h-10 w-32 rounded-xl" />
      </div>

      {/* Preferences card */}
      <div className="card p-6 space-y-5">
        <Bar className="h-4 w-56" />
        <div className="grid grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="space-y-2">
              <Bar className="h-3 w-20" />
              <Bar className="h-11 w-full rounded-xl" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
