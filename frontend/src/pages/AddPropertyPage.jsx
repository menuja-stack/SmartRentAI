import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, Plus } from 'lucide-react';
import api from '../api/axios';
import { toast } from 'react-toastify';

const DISTRICTS = ['Colombo','Gampaha','Kalutara','Kandy','Galle','Matara','Kurunegala','Negombo','Jaffna','Batticaloa','Trincomalee','Anuradhapura','Polonnaruwa','Ratnapura','Nuwara Eliya','Badulla','Hambantota','Matale','Monaragala','Puttalam'];
const AMENITY_IDS = [1,2,3,4,5,6,7,8,9,10,11,12];
const AMENITY_NAMES = ['WiFi','Parking','Air Conditioning','Gym','Swimming Pool','Security','Elevator','Generator','Water 24/7','CCTV','Garden','Laundry'];

export default function AddPropertyPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    title: '', description: '', property_type: 'apartment',
    bedrooms: 2, bathrooms: 1, area_sqft: '', monthly_rent: '',
    deposit: '', address_line: '', latitude: '', longitude: '',
    furnished: 'semi-furnished', available_from: '', city: '', district: '', province: '',
  });
  const [amenities, setAmenities] = useState([]);
  const [files, setFiles]   = useState([]);
  const [loading, setLoading] = useState(false);

  const toggleAmenity = (id) =>
    setAmenities(a => a.includes(id) ? a.filter(x => x !== id) : [...a, id]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const fd = new FormData();
      // Optional numeric/date fields: skip if empty so the backend receives them as absent (null-safe).
      // Required text fields are always appended (validator catches empty ones).
      const optionalNumeric = ['area_sqft', 'deposit', 'latitude', 'longitude', 'available_from'];
      Object.entries(form).forEach(([k, v]) => {
        if (optionalNumeric.includes(k) && v === '') return;
        fd.append(k, v);
      });
      amenities.forEach(id => fd.append('amenity_ids[]', id));
      files.forEach(f => fd.append('images', f));

      await api.post('/properties', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      toast.success('Property listed successfully!');
      navigate('/search');
    } catch (err) {
      const data = err.response?.data;
      if (data?.errors?.length) {
        const e = data.errors[0];
        toast.error(`${e.path || e.param}: ${e.msg}`);
      } else {
        toast.error(data?.error || 'Failed to create listing');
      }
    }
    setLoading(false);
  };

  const f = (k, v) => setForm(p => ({ ...p, [k]: v }));

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-2 mb-6">
        <Plus size={28} className="text-primary-600" /> List Your Property
      </h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="card p-6 space-y-4">
          <h2 className="font-semibold text-gray-900 dark:text-white">Basic Information</h2>
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">Title *</label>
            <input value={form.title} onChange={e => f('title', e.target.value)} required className="input-field" placeholder="e.g. Spacious 2BR Apartment in Colombo 7" />
          </div>
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">Description *</label>
            <textarea value={form.description} onChange={e => f('description', e.target.value)} required rows={4} className="input-field resize-none" placeholder="Describe your property in detail…" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">Type</label>
              <select value={form.property_type} onChange={e => f('property_type', e.target.value)} className="input-field">
                {['apartment','house','room','villa','commercial'].map(t => <option key={t} className="capitalize">{t}</option>)}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">Furnished</label>
              <select value={form.furnished} onChange={e => f('furnished', e.target.value)} className="input-field">
                {['unfurnished','semi-furnished','furnished'].map(o => <option key={o}>{o}</option>)}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">Bedrooms</label>
              <input type="number" min={0} max={20} value={form.bedrooms} onChange={e => f('bedrooms', e.target.value)} className="input-field" />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">Bathrooms</label>
              <input type="number" min={0} max={10} value={form.bathrooms} onChange={e => f('bathrooms', e.target.value)} className="input-field" />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">Area (sqft)</label>
              <input type="number" value={form.area_sqft} onChange={e => f('area_sqft', e.target.value)} className="input-field" placeholder="e.g. 850" />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">Available From</label>
              <input type="date" value={form.available_from} onChange={e => f('available_from', e.target.value)} className="input-field" />
            </div>
          </div>
        </div>

        <div className="card p-6 space-y-4">
          <h2 className="font-semibold text-gray-900 dark:text-white">Pricing</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">Monthly Rent (LKR) *</label>
              <input type="number" required value={form.monthly_rent} onChange={e => f('monthly_rent', e.target.value)} className="input-field" placeholder="e.g. 45000" />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">Security Deposit (LKR)</label>
              <input type="number" value={form.deposit} onChange={e => f('deposit', e.target.value)} className="input-field" placeholder="e.g. 90000" />
            </div>
          </div>
        </div>

        <div className="card p-6 space-y-4">
          <h2 className="font-semibold text-gray-900 dark:text-white">Location</h2>
          <div>
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">Address *</label>
            <input required value={form.address_line} onChange={e => f('address_line', e.target.value)} className="input-field" placeholder="Full address" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">District *</label>
              <select required value={form.district} onChange={e => { f('district', e.target.value); f('city', e.target.value); }} className="input-field">
                <option value="">Select district</option>
                {DISTRICTS.map(d => <option key={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700 dark:text-gray-300 block mb-1">City</label>
              <input value={form.city} onChange={e => f('city', e.target.value)} className="input-field" placeholder="City name" />
            </div>
          </div>
        </div>

        <div className="card p-6">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-4">Amenities</h2>
          <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
            {AMENITY_IDS.map((id, i) => (
              <label key={id}
                className={`flex items-center gap-2 p-2.5 rounded-xl border-2 cursor-pointer transition-all text-sm
                  ${amenities.includes(id) ? 'border-primary-500 bg-primary-50 text-primary-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'}`}>
                <input type="checkbox" checked={amenities.includes(id)} onChange={() => toggleAmenity(id)} className="sr-only" />
                {AMENITY_NAMES[i]}
              </label>
            ))}
          </div>
        </div>

        <div className="card p-6">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-2">Photos</h2>
          <p className="text-sm text-gray-500 mb-4">Upload up to 10 photos. First photo will be the cover.</p>
          <label className="flex flex-col items-center justify-center border-2 border-dashed border-gray-300 rounded-xl p-8 cursor-pointer hover:border-primary-500 transition-colors">
            <Upload size={32} className="text-gray-400 mb-2" />
            <span className="text-sm text-gray-600">{files.length ? `${files.length} file(s) selected` : 'Click to upload images'}</span>
            <input type="file" multiple accept="image/*" className="hidden"
              onChange={e => setFiles(Array.from(e.target.files))} />
          </label>
        </div>

        <button type="submit" disabled={loading} className="btn-primary w-full text-base py-3">
          {loading ? 'Uploading…' : '🏠 Publish Listing'}
        </button>
      </form>
    </div>
  );
}
