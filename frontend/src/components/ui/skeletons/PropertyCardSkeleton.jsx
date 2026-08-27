import React from 'react';
import { Bar, Circle } from './Skeleton';

/** Mirrors PropertyCard: image, title, location, bed/bath row, footer. */
export default function PropertyCardSkeleton() {
  return (
    <div className="card flex flex-col">
      {/* Image */}
      <Bar className="h-52 rounded-none" />

      {/* Body */}
      <div className="p-4 space-y-3">
        <Bar className="h-4 w-3/4" />
        <div className="flex items-center gap-2">
          <Circle size="w-3.5 h-3.5" />
          <Bar className="h-3 w-1/3" />
        </div>
        <div className="flex items-center gap-4">
          <Bar className="h-3 w-14" />
          <Bar className="h-3 w-14" />
          <Bar className="h-3 w-10 ml-auto" />
        </div>
        <div className="flex items-center justify-between pt-3 border-t border-gray-100 dark:border-gray-800">
          <Bar className="h-3 w-16" />
          <Bar className="h-3 w-12" />
        </div>
      </div>
    </div>
  );
}

/** Convenience grid of card skeletons. */
export function PropertyCardSkeletonGrid({ count = 6 }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
      {[...Array(count)].map((_, i) => <PropertyCardSkeleton key={i} />)}
    </div>
  );
}
