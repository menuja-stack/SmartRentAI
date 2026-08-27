import React from 'react';
import { Bar, Circle } from './Skeleton';

/** Mirrors SafetyDashboardPage map tab: district cards left, radar + bars right. */
export default function SafeRentSkeleton() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Left — district list */}
      <div className="space-y-2">
        <div className="flex gap-2 mb-3">
          <Bar className="h-10 flex-1 rounded-xl" />
          <Bar className="h-10 w-24 rounded-xl" />
        </div>
        {[...Array(6)].map((_, i) => (
          <div key={i} className="card p-4 space-y-2">
            <div className="flex justify-between">
              <Bar className="h-4 w-24" />
              <Bar className="h-5 w-16 rounded-full" />
            </div>
            <Bar className="h-3 w-16" />
            <Bar className="h-1.5 w-full rounded-full" />
          </div>
        ))}
      </div>

      {/* Right — selected district detail */}
      <div className="lg:col-span-2 space-y-4">
        <div className="card p-6">
          <div className="flex items-start justify-between mb-6">
            <div className="space-y-2">
              <Bar className="h-6 w-40" />
              <Bar className="h-3 w-28" />
            </div>
            <Bar className="h-7 w-24 rounded-full" />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Radar placeholder */}
            <div className="flex items-center justify-center h-[260px]">
              <Circle size="w-48 h-48" className="opacity-70" />
            </div>
            {/* Factor bars */}
            <div className="space-y-4">
              {[...Array(7)].map((_, i) => (
                <div key={i} className="space-y-1.5">
                  <div className="flex justify-between">
                    <Bar className="h-3 w-28" />
                    <Bar className="h-3 w-10" />
                  </div>
                  <Bar className="h-2 w-full rounded-full" />
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="card p-5">
          <Bar className="h-4 w-48 mb-4" />
          <div className="grid grid-cols-3 gap-4">
            {[...Array(3)].map((_, i) => <Bar key={i} className="h-20 rounded-xl" />)}
          </div>
        </div>
      </div>
    </div>
  );
}
