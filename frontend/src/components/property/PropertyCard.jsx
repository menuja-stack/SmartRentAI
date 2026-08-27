import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { MapPin, Bed, Bath, Heart, Star, ArrowRight, Home } from 'lucide-react';
import { toast } from 'react-toastify';
import api from '../../api/axios';
import { useSelector } from 'react-redux';
import { getImageUrl } from '../../utils/imageUrl';

export default function PropertyCard({ property }) {
  const { token } = useSelector((s) => s.auth);
  const [saved, setSaved] = useState(false);
  const [imgError, setImgError] = useState(false);
  const [imgLoaded, setImgLoaded] = useState(false);

  const handleSave = async (e) => {
    e.preventDefault();
    if (!token) return;
    try {
      const { data } = await api.post(`/properties/${property.id}/save`);
      setSaved(data.saved);
      toast.success(data.saved ? 'Saved to wishlist!' : 'Removed from wishlist');
    } catch {
      toast.error('Could not update wishlist');
    }
  };

  // getImageUrl returns null when no image path — we render a CSS placeholder instead
  const imageSrc = imgError ? null : getImageUrl(property.primary_image);
  const showPlaceholder = !imageSrc;

  return (
    <Link to={`/property/${property.id}`}
      className="card group hover:shadow-lg hover:-translate-y-0.5 transition-all duration-200 flex flex-col">

      {/* Image */}
      <div className="relative h-52 overflow-hidden bg-gray-100 dark:bg-gray-800">
        {showPlaceholder ? (
          <div className="w-full h-full flex flex-col items-center justify-center gap-2 bg-gray-100 dark:bg-gray-800">
            <Home size={36} className="text-gray-300 dark:text-gray-600" />
            <span className="text-xs text-gray-400 dark:text-gray-500">
              {imgError ? 'Image unavailable' : 'No photo'}
            </span>
          </div>
        ) : (
          <>
            {/* Shimmer shown behind the image until it finishes loading */}
            {!imgLoaded && <div className="absolute inset-0 skeleton rounded-none" />}
            <img
              src={imageSrc}
              alt={property.title}
              loading="lazy"
              onLoad={() => setImgLoaded(true)}
              onError={() => setImgError(true)}
              className={`w-full h-full object-cover group-hover:scale-105 transition-all duration-300
                ${imgLoaded ? 'opacity-100' : 'opacity-0'}`}
            />
          </>
        )}
        <div className="absolute top-3 left-3">
          <span className="badge bg-primary-600 text-white capitalize">{property.property_type}</span>
        </div>
        {token && (
          <button onClick={handleSave}
            className="absolute top-3 right-3 p-2 bg-white rounded-full shadow hover:bg-red-50 transition-colors">
            <Heart size={16} className={saved ? 'fill-red-500 text-red-500' : 'text-gray-400'} />
          </button>
        )}
        <div className="absolute bottom-3 left-3">
          <span className="bg-black/60 text-white text-sm font-semibold px-2 py-1 rounded-lg">
            LKR {Number(property.monthly_rent).toLocaleString()}/mo
          </span>
        </div>
        {/* Scraped badge */}
        {property.source === 'ikman.lk' && (
          <div className="absolute bottom-3 right-3">
            <span className="bg-amber-500/90 text-white text-xs font-semibold px-2 py-0.5 rounded-full">
              Ikman
            </span>
          </div>
        )}
      </div>

      {/* Body */}
      <div className="p-4 flex flex-col flex-1">
        <h3 className="font-semibold text-gray-900 dark:text-white line-clamp-1 mb-1 group-hover:text-primary-600 transition-colors">
          {property.title}
        </h3>

        <div className="flex items-center gap-1 text-gray-500 text-sm mb-3">
          <MapPin size={14} />
          <span>{property.city || property.location || property.district}</span>
        </div>

        <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400 mt-auto">
          {property.bedrooms  != null && <span className="flex items-center gap-1"><Bed  size={14} /> {property.bedrooms} bed</span>}
          {property.bathrooms != null && <span className="flex items-center gap-1"><Bath size={14} /> {property.bathrooms} bath</span>}
          {property.avg_rating && (
            <span className="flex items-center gap-1 ml-auto text-amber-500">
              <Star size={14} className="fill-amber-500" />
              {Number(property.avg_rating).toFixed(1)}
            </span>
          )}
        </div>

        <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100 dark:border-gray-800">
          <span className="text-xs text-gray-400 capitalize">{property.furnished || property.property_type}</span>
          <span className="text-primary-600 text-sm font-medium flex items-center gap-1">
            View <ArrowRight size={14} />
          </span>
        </div>
      </div>
    </Link>
  );
}
