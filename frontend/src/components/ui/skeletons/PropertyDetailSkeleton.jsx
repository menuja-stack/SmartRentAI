import React from 'react';
import { Bar, Circle } from './Skeleton';

/** Mirrors PropertyDetailPage: hero image, title/price, specs row, description, contact card. */
export default function PropertyDetailSkeleton() {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      <Bar className="h-4 w-28 mb-4" />

      {/* Hero image + thumbnails */}
      <Bar className="h-80 w-full rounded-2xl mb-2" />
      <div className="flex gap-2 mb-6">
        {[...Array(4)].map((_, i) => <Bar key={i} className="w-16 h-12" />)}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          {/* Title + location + price */}
          <div className="space-y-3">
            <Bar className="h-7 w-4/5" />
            <div className="flex items-center gap-2">
              <Circle size="w-4 h-4" />
              <Bar className="h-4 w-1/2" />
            </div>
            <Bar className="h-8 w-48" />
          </div>

          {/* Specs row */}
          <div className="grid grid-cols-3 gap-4 py-4 border-y border-gray-100 dark:border-gray-800">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="flex flex-col items-center gap-2">
                <Circle size="w-6 h-6" />
                <Bar className="h-3 w-20" />
              </div>
            ))}
          </div>

          {/* Description lines */}
          <div className="space-y-2">
            <Bar className="h-4 w-40 mb-3" />
            <Bar className="h-3 w-full" />
            <Bar className="h-3 w-full" />
            <Bar className="h-3 w-11/12" />
            <Bar className="h-3 w-2/3" />
          </div>
        </div>

        {/* Contact card */}
        <div>
          <div className="card p-5 space-y-4">
            <Bar className="h-4 w-32" />
            <div className="flex items-center gap-3">
              <Circle />
              <div className="flex-1 space-y-2">
                <Bar className="h-3 w-2/3" />
                <Bar className="h-3 w-1/3" />
              </div>
            </div>
            <Bar className="h-10 w-full rounded-xl" />
            <Bar className="h-10 w-full rounded-xl" />
          </div>
        </div>
      </div>
    </div>
  );
}
