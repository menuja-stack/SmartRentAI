import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search, SlidersHorizontal, X, MapPin } from 'lucide-react';
import api from '../api/axios';
import PropertyCard from '../components/property/PropertyCard';
import { PropertyCardSkeletonGrid } from '../components/ui/skeletons/PropertyCardSkeleton';

// All 25 Sri Lankan administrative districts, grouped by province.
// Values must match the `district` field stored in the locations table exactly.
const DISTRICTS_BY_PROVINCE = {
  'Western':       ['Colombo', 'Gampaha', 'Kalutara'],
  'Central':       ['Kandy', 'Matale', 'Nuwara Eliya'],
  'Southern':      ['Galle', 'Matara', 'Hambantota'],
  'Northern':      ['Jaffna', 'Kilinochchi', 'Mannar', 'Mullaitivu', 'Vavuniya'],
  'Eastern':       ['Trincomalee', 'Batticaloa', 'Ampara'],
  'North Western': ['Kurunegala', 'Puttalam'],
  'North Central': ['Anuradhapura', 'Polonnaruwa'],
  'Uva':           ['Badulla', 'Monaragala'],
  'Sabaragamuwa':  ['Ratnapura', 'Kegalle'],
};

// Flat list for direct district-name matching while typing.
const ALL_DISTRICTS = Object.values(DISTRICTS_BY_PROVINCE).flat();

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [properties, setProperties] = useState([]);
  const [total, setTotal]           = useState(0);
  const [loading, setLoading]       = useState(false);
  const [page, setPage]             = useState(1);
  const [showFilters, setShowFilters] = useState(false);

  // Autocomplete state
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggest, setShowSuggest] = useState(false);
  const searchBoxRef = useRef(null);

  const [filters, setFilters] = useState({
    search:   searchParams.get('search')   || '',
    district: searchParams.get('district') || '',
    city:     searchParams.get('city')     || '',
    type:     '',
    min_rent: '',
    max_rent: '',
    bedrooms: '',
    sort:     'created_at',
  });

  // ── Fetch properties ──────────────────────────────────────────
  const fetchProperties = useCallback(async () => {
    setLoading(true);
    try {
      const params = { ...filters, page, limit: 12 };
      Object.keys(params).forEach(k => !params[k] && delete params[k]);
      const { data } = await api.get('/properties', { params });
      setProperties(data.data || []);
      setTotal(data.total || 0);
    } catch { setProperties([]); }
    setLoading(false);
  }, [filters, page]);

  useEffect(() => { fetchProperties(); }, [fetchProperties]);

  // ── URL sync: keep district / city / search shareable ─────────
  useEffect(() => {
    const next = {};
    if (filters.district) next.district = filters.district;
    if (filters.city)     next.city     = filters.city;
    if (filters.search)   next.search   = filters.search;
    setSearchParams(next, { replace: true });
  }, [filters.district, filters.city, filters.search, setSearchParams]);

  // ── Autocomplete: debounced town/city lookup ──────────────────
  useEffect(() => {
    const q = filters.search.trim();
    if (q.length < 2) { setSuggestions([]); return; }

    const t = setTimeout(async () => {
      try {
        const { data } = await api.get('/locations/search', { params: { q } });
        // If the typed term matches a district name directly, offer a
        // "whole district" option at the top (sets district filter only).
        const districtMatch = ALL_DISTRICTS.find(
          d => d.toLowerCase().startsWith(q.toLowerCase())
        );
        const list = [];
        if (districtMatch) {
          list.push({ city: null, district: districtMatch, _wholeDistrict: true });
        }
        // Deduplicate API rows that duplicate the whole-district entry
        for (const row of data) {
          list.push(row);
        }
        setSuggestions(list.slice(0, 10));
      } catch { setSuggestions([]); }
    }, 250);

    return () => clearTimeout(t);
  }, [filters.search]);

  // Close suggestion dropdown when clicking outside
  useEffect(() => {
    const onClick = (e) => {
      if (searchBoxRef.current && !searchBoxRef.current.contains(e.target)) {
        setShowSuggest(false);
      }
    };
    document.addEventListener('mousedown', onClick);
    return () => document.removeEventListener('mousedown', onClick);
  }, []);

  // ── Filter helpers ────────────────────────────────────────────
  const updateFilter = (key, value) => {
    setFilters(f => ({ ...f, [key]: value }));
    setPage(1);
  };

  // Selecting an autocomplete suggestion
  const selectSuggestion = (s) => {
    if (s._wholeDistrict) {
      // District-only filter
      setFilters(f => ({ ...f, district: s.district, city: '', search: '' }));
    } else {
      // Town/city filter — set both city and its district
      setFilters(f => ({ ...f, city: s.city, district: s.district, search: '' }));
    }
    setShowSuggest(false);
    setSuggestions([]);
    setPage(1);
  };

  // Enter key: if the typed term is exactly a district, apply district filter
  const onSearchKeyDown = (e) => {
    if (e.key !== 'Enter') return;
    const q = filters.search.trim();
    const exact = ALL_DISTRICTS.find(d => d.toLowerCase() === q.toLowerCase());
    if (exact) {
      setFilters(f => ({ ...f, district: exact, city: '', search: '' }));
      setShowSuggest(false);
      setSuggestions([]);
      setPage(1);
    } else if (suggestions.length) {
      selectSuggestion(suggestions[0]);
    }
  };

  const clearTownFilter = () => {
    setFilters(f => ({ ...f, city: '', district: '' }));
    setPage(1);
  };

  const clearFilters = () => {
    setFilters({ search:'', district:'', city:'', type:'', min_rent:'', max_rent:'', bedrooms:'', sort:'created_at' });
    setPage(1);
  };

  const activeFilterCount = Object.entries(filters)
    .filter(([k, v]) => v && k !== 'sort' && k !== 'search').length;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Top bar */}
      <div className="flex flex-col sm:flex-row gap-3 mb-3">
        <div className="flex-1 relative" ref={searchBoxRef}>
          <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            value={filters.search}
            onChange={e => { updateFilter('search', e.target.value); setShowSuggest(true); }}
            onFocus={() => setShowSuggest(true)}
            onKeyDown={onSearchKeyDown}
            placeholder="Search by town, area or district… (e.g. Nugegoda, Colombo)"
            className="input-field pl-10"
            autoComplete="off" />

          {/* Autocomplete dropdown */}
          {showSuggest && suggestions.length > 0 && (
            <div className="absolute z-20 mt-1 w-full bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg overflow-hidden">
              {suggestions.map((s, i) => (
                <button
                  key={`${s.district}-${s.city ?? 'all'}-${i}`}
                  onClick={() => selectSuggestion(s)}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-primary-50 dark:hover:bg-gray-800 transition-colors">
                  <MapPin size={15} className="text-primary-500 shrink-0" />
                  {s._wholeDistrict ? (
                    <span className="text-sm text-gray-900 dark:text-white">
                      All of <span className="font-semibold">{s.district}</span>
                      <span className="text-xs text-gray-400"> · whole district</span>
                    </span>
                  ) : (
                    <span className="text-sm text-gray-900 dark:text-white">
                      <span className="font-medium">{s.city}</span>
                      <span className="text-xs text-gray-400"> · {s.district}</span>
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>
        <button onClick={() => setShowFilters(!showFilters)}
          className="btn-secondary flex items-center gap-2">
          <SlidersHorizontal size={16} /> Filters
          {activeFilterCount > 0 && (
            <span className="bg-primary-600 text-white text-xs rounded-full w-4 h-4 flex items-center justify-center">
              {activeFilterCount}
            </span>
          )}
        </button>
      </div>

      {/* Active town/district chip */}
      {(filters.city || filters.district) && (
        <div className="flex items-center gap-2 mb-6">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary-50 text-primary-700 text-sm font-medium border border-primary-200">
            <MapPin size={13} />
            Showing results in:&nbsp;
            <span className="font-semibold">
              {filters.city ? `${filters.city}, ${filters.district}` : filters.district}
            </span>
            <button onClick={clearTownFilter} className="ml-1 hover:text-red-500" aria-label="Clear location filter">
              <X size={14} />
            </button>
          </span>
        </div>
      )}

      {/* Filter panel */}
      {showFilters && (
        <div className="card p-5 mb-6 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <select
            value={filters.district}
            onChange={e => setFilters(f => ({ ...f, district: e.target.value, city: '' }))}
            className="input-field">
            <option value="">All Districts</option>
            {Object.entries(DISTRICTS_BY_PROVINCE).map(([province, districts]) => (
              <optgroup key={province} label={province}>
                {districts.map(d => <option key={d} value={d}>{d}</option>)}
              </optgroup>
            ))}
          </select>
          <select value={filters.type} onChange={e => updateFilter('type', e.target.value)} className="input-field">
            <option value="">All Types</option>
            {['apartment','house','room','villa','commercial'].map(t => <option key={t} className="capitalize">{t}</option>)}
          </select>
          <input type="number" placeholder="Min rent" value={filters.min_rent}
            onChange={e => updateFilter('min_rent', e.target.value)} className="input-field" />
          <input type="number" placeholder="Max rent" value={filters.max_rent}
            onChange={e => updateFilter('max_rent', e.target.value)} className="input-field" />
          <select value={filters.bedrooms} onChange={e => updateFilter('bedrooms', e.target.value)} className="input-field">
            <option value="">Any beds</option>
            {[1,2,3,4,5].map(n => <option key={n} value={n}>{n}+ beds</option>)}
          </select>
          <select value={filters.sort} onChange={e => updateFilter('sort', e.target.value)} className="input-field">
            <option value="created_at">Newest</option>
            <option value="rent_asc">Price ↑</option>
            <option value="rent_desc">Price ↓</option>
          </select>
          <button onClick={clearFilters}
            className="col-span-full flex items-center gap-1 text-sm text-gray-500 hover:text-red-500 w-fit">
            <X size={14} /> Clear all filters
          </button>
        </div>
      )}

      {/* Results */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-gray-500 text-sm">
          {loading ? 'Loading…' : `${total} properties found`}
        </p>
      </div>

      {loading ? (
        <PropertyCardSkeletonGrid count={6} />
      ) : properties.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <Search size={48} className="mx-auto mb-4 opacity-30" />
          <p className="text-lg font-medium">No properties found</p>
          <p className="text-sm">Try adjusting your filters</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {properties.map(p => <PropertyCard key={p.id} property={p} />)}
          </div>
          {/* Pagination */}
          <div className="flex justify-center gap-2 mt-8">
            <button disabled={page === 1} onClick={() => setPage(p => p - 1)}
              className="btn-secondary disabled:opacity-40">Previous</button>
            <span className="px-4 py-2 text-sm text-gray-600">Page {page}</span>
            <button disabled={properties.length < 12} onClick={() => setPage(p => p + 1)}
              className="btn-secondary disabled:opacity-40">Next</button>
          </div>
        </>
      )}
    </div>
  );
}
