import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { MapPin, Bed, Bath, Star, Heart, ArrowLeft, PhoneCall, Mail, Home } from 'lucide-react';
import api from '../api/axios';
import { useSelector } from 'react-redux';
import PropertyCard from '../components/property/PropertyCard';
import SafeRentWidget from '../components/property/SafeRentWidget';
import PropertyDetailSkeleton from '../components/ui/skeletons/PropertyDetailSkeleton';
import { toast } from 'react-toastify';
import { getImageUrl } from '../utils/imageUrl';

export default function PropertyDetailPage() {
  const { id }    = useParams();
  const { token } = useSelector(s => s.auth);
  const [property, setProperty] = useState(null);
  const [similar, setSimilar]   = useState([]);
  const [loading, setLoading]   = useState(true);
  const [saved, setSaved]       = useState(false);
  const [activeImg, setActiveImg] = useState(0);
  const [brokenImgs, setBrokenImgs] = useState(() => new Set());

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.get(`/properties/${id}`),
      api.get(`/recommendations/similar/${id}`),
    ]).then(([{ data: p }, { data: s }]) => {
      setProperty(p);
      setSimilar(s);
    }).catch(() => toast.error('Failed to load property details'))
    .finally(() => setLoading(false));
  }, [id]);

  // Implicit feedback (Phase 7): log a 'view' when a logged-in user opens a property
  useEffect(() => {
    if (token) api.post('/users/activity', { property_id: id, action: 'view' }).catch(() => {});
  }, [id, token]);

  const handleSave = async () => {
    if (!token) return;
    try {
      const { data } = await api.post(`/properties/${id}/save`);
      setSaved(data.saved);
      toast.success(data.saved ? 'Saved to wishlist!' : 'Removed from wishlist');
      if (data.saved) api.post('/users/activity', { property_id: id, action: 'save' }).catch(() => {});
    } catch {
      toast.error('Could not update wishlist');
    }
  };

  const handleEnquiry = () => {
    if (token) api.post('/users/activity', { property_id: id, action: 'enquiry' }).catch(() => {});
  };

  if (loading) return <PropertyDetailSkeleton />;
  if (!property) return <div className="text-center py-20 text-gray-500">Property not found.</div>;

  // Only keep real, resolvable URLs — getImageUrl() returns null when a property
  // has no image row, which is common right now for listings scraped after the
  // last recoverable DB backup.
  const images = (property.images?.length
    ? property.images.map(i => getImageUrl(i.url))
    : [getImageUrl(property.primary_image)]
  ).filter(Boolean);

  const activeSrc = images[activeImg];
  const showHeroPlaceholder = images.length === 0 || brokenImgs.has(activeSrc);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      <Link to="/search" className="flex items-center gap-1 text-gray-500 hover:text-primary-600 text-sm mb-4">
        <ArrowLeft size={16} /> Back to Search
      </Link>

      {/* Image gallery */}
      <div className="rounded-2xl overflow-hidden mb-6">
        {showHeroPlaceholder ? (
          <div className="w-full h-80 bg-gray-100 dark:bg-gray-800 flex flex-col items-center justify-center gap-2">
            <Home size={48} className="text-gray-300 dark:text-gray-600" />
            <span className="text-sm text-gray-400 dark:text-gray-500">No photos available</span>
          </div>
        ) : (
          <img
            src={activeSrc}
            alt={property.title}
            onError={() => setBrokenImgs(s => new Set(s).add(activeSrc))}
            className="w-full h-80 object-cover"
          />
        )}
        {images.length > 1 && (
          <div className="flex gap-2 mt-2">
            {images.map((img, i) => (
              <button key={i} onClick={() => setActiveImg(i)}
                className={`w-16 h-12 rounded-lg overflow-hidden border-2 shrink-0 bg-gray-100 dark:bg-gray-800 flex items-center justify-center
                  ${activeImg === i ? 'border-primary-500' : 'border-transparent'}`}>
                {brokenImgs.has(img)
                  ? <Home size={14} className="text-gray-300 dark:text-gray-600" />
                  : <img src={img} alt="" loading="lazy"
                      onError={() => setBrokenImgs(s => new Set(s).add(img))}
                      className="w-full h-full object-cover" />}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left */}
        <div className="lg:col-span-2 space-y-6">
          <div>
            <div className="flex items-start justify-between gap-4">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{property.title}</h1>
              {token && (
                <button onClick={handleSave} className="p-2 rounded-full border hover:bg-red-50 transition-colors shrink-0">
                  <Heart size={20} className={saved ? 'fill-red-500 text-red-500' : 'text-gray-400'} />
                </button>
              )}
            </div>
            <div className="flex items-center gap-1 text-gray-500 mt-1">
              <MapPin size={16} /><span>{property.address_line}, {property.city}, {property.district}</span>
            </div>
            <div className="flex items-center gap-4 mt-3">
              <span className="text-2xl font-bold text-primary-600">LKR {Number(property.monthly_rent).toLocaleString()}<span className="text-sm font-normal text-gray-400">/mo</span></span>
              {property.avg_rating && (
                <span className="flex items-center gap-1 text-amber-500">
                  <Star size={16} className="fill-amber-500" />
                  {Number(property.avg_rating).toFixed(1)} ({property.review_count})
                </span>
              )}
            </div>
          </div>

          {/* Features */}
          <div className="grid grid-cols-3 gap-4 py-4 border-y border-gray-100 dark:border-gray-800">
            {[
              [`${property.bedrooms} Bedrooms`, <Bed size={20} />],
              [`${property.bathrooms} Bathrooms`, <Bath size={20} />],
              [property.furnished, <Star size={20} />],
              [property.property_type, null],
              [property.area_sqft ? `${property.area_sqft} sqft` : null, null],
            ].filter(([l]) => l).map(([label, icon]) => (
              <div key={label} className="text-center">
                {icon && <div className="text-primary-600 flex justify-center mb-1">{icon}</div>}
                <p className="text-sm font-medium text-gray-800 dark:text-gray-200 capitalize">{label}</p>
              </div>
            ))}
          </div>

          {/* SafeRent Widget */}
          {property.district && (
            <SafeRentWidget district={property.district} />
          )}

          {/* Description */}
          <div>
            <h2 className="font-semibold text-gray-900 dark:text-white mb-2">About this property</h2>
            <p className="text-gray-600 dark:text-gray-400 leading-relaxed text-sm">{property.description}</p>
          </div>

          {/* Amenities */}
          {property.amenities?.length > 0 && (
            <div>
              <h2 className="font-semibold text-gray-900 dark:text-white mb-3">Amenities</h2>
              <div className="flex flex-wrap gap-2">
                {property.amenities.map(a => (
                  <span key={a.id} className="badge bg-primary-50 text-primary-700">{a.name}</span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right — Contact */}
        <div>
          <div className="card p-5 sticky top-20">
            <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Contact Landlord</h2>
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 bg-primary-600 rounded-full flex items-center justify-center text-white font-semibold">
                {property.landlord_name?.[0]}
              </div>
              <div>
                <p className="font-medium text-gray-900 dark:text-white">{property.landlord_name}</p>
                <p className="text-xs text-gray-500">Property Owner</p>
              </div>
            </div>
            {property.landlord_phone && (
              <a href={`tel:${property.landlord_phone}`}
                className="flex items-center gap-2 btn-secondary w-full justify-center mb-2 text-sm">
                <PhoneCall size={16} /> {property.landlord_phone}
              </a>
            )}
            <a href={`mailto:${property.landlord_email}`} onClick={handleEnquiry}
              className="flex items-center gap-2 btn-primary w-full justify-center text-sm">
              <Mail size={16} /> Send Enquiry
            </a>
            {property.deposit && (
              <p className="text-xs text-gray-500 text-center mt-3">
                Deposit: LKR {Number(property.deposit).toLocaleString()}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Similar */}
      {similar.length > 0 && (
        <div className="mt-12">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">Similar Properties</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {similar.map(p => <PropertyCard key={p.id} property={p} />)}
          </div>
        </div>
      )}
    </div>
  );
}
