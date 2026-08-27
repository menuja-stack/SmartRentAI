import React, { useEffect, useState } from 'react';
import { Heart } from 'lucide-react';
import api from '../api/axios';
import PropertyCard from '../components/property/PropertyCard';
import { PropertyCardSkeletonGrid } from '../components/ui/skeletons/PropertyCardSkeleton';

export default function WishlistPage() {
  const [items, setItems]     = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/properties/saved')
       .then(({ data }) => setItems(data))
       .catch(() => setItems([]))
       .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-6">
        <Heart size={28} className="text-red-500 fill-red-500" /> My Wishlist
      </h1>
      {loading ? (
        <PropertyCardSkeletonGrid count={3} />
      ) : items.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <Heart size={48} className="mx-auto mb-4 opacity-30" />
          <p className="text-lg font-medium">No saved properties</p>
          <p className="text-sm mt-1">Click the heart icon on any property to save it here.</p>
          <a href="/search" className="btn-primary inline-block mt-4 text-sm">Browse Properties</a>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {items.map(p => <PropertyCard key={p.id} property={p} />)}
        </div>
      )}
    </div>
  );
}
