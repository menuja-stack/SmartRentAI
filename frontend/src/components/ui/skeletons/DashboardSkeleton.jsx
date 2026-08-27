import React from 'react';
import { Bar, Circle } from './Skeleton';

/** Mirrors AdminDashboardPage: 4 stat cards, chart, table rows. */
export default function DashboardSkeleton() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center justify-between mb-8">
        <Bar className="h-8 w-64" />
        <Bar className="h-9 w-28 rounded-xl" />
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="card p-5 space-y-3">
            <Bar className="w-12 h-12 rounded-xl" />
            <Bar className="h-6 w-16" />
            <Bar className="h-3 w-24" />
          </div>
        ))}
      </div>

      {/* Chart placeholder */}
      <div className="card p-5 mb-8">
        <Bar className="h-4 w-48 mb-4" />
        <div className="flex items-end gap-3 h-44">
          {[60, 90, 45, 100, 70, 85, 55, 95, 65, 80].map((h, i) => (
            <div key={i} className="skeleton flex-1 rounded-t-lg" style={{ height: `${h}%` }} />
          ))}
        </div>
      </div>

      {/* Table rows */}
      <div className="card p-5 space-y-3">
        <Bar className="h-4 w-40 mb-2" />
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex items-center gap-3 py-2">
            <Circle size="w-8 h-8" />
            <Bar className="h-3 flex-1" />
            <Bar className="h-3 w-20" />
            <Bar className="h-3 w-14" />
          </div>
        ))}
      </div>
    </div>
  );
}
