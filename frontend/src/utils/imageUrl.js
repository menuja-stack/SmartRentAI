const API_BASE = (process.env.REACT_APP_API_URL || 'http://localhost:5000/api')
  .replace('/api', '');

/**
 * Resolves a property image path to a full URL.
 * Returns null when path is missing — callers should render a CSS placeholder,
 * not a misleading stock photo.
 */
export function getImageUrl(path) {
  if (!path) return null;
  if (path.startsWith('http')) return path;   // already absolute
  return `${API_BASE}${path}`;               // /uploads/properties/xxx.jpg
}
