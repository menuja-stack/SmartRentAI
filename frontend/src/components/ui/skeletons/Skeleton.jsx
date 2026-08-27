import React from 'react';

/**
 * Base skeleton primitives — every skeleton screen is composed from these.
 * The `.skeleton` class (index.css) provides the shimmer animation.
 */
export function Bar({ className = '' }) {
  return <div className={`skeleton ${className}`} />;
}

export function Circle({ size = 'w-10 h-10', className = '' }) {
  return <div className={`skeleton rounded-full ${size} ${className}`} />;
}

export default Bar;
