import React from 'react';
import { Bar } from './Skeleton';
import PropertyCardSkeleton from './PropertyCardSkeleton';

/** Mirrors the "For You" grid: summary banner + cards with match-score badges + reason tags. */
export default function RecommendationSkeleton({ count = 6 }) {
  return (
    <div>
      {/* Profile summary banner */}
      <div className="mb-6 p-4 rounded-2xl border border-gray-100 dark:border-gray-800">
        <Bar className="h-3 w-3/4 mb-2" />
        <Bar className="h-3 w-1/2" />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-x-6 gap-y-8">
        {[...Array(count)].map((_, i) => (
          <div key={i} className="relative">
            {/* Match score badge */}
            <div className="absolute top-3 right-3 z-10">
              <Bar className="h-6 w-20 rounded-full" />
            </div>
            <PropertyCardSkeleton />
            {/* Reason tags */}
            <div className="flex gap-1.5 mt-2">
              <Bar className="h-5 w-24 rounded-lg" />
              <Bar className="h-5 w-20 rounded-lg" />
              <Bar className="h-5 w-16 rounded-lg" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
