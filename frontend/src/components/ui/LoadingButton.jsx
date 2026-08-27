import React from 'react';
import { Loader2 } from 'lucide-react';

/**
 * Button with a built-in loading state.
 *
 *   <LoadingButton loading={isLoading} loadingText="Predicting…" onClick={run}>
 *     Predict Price
 *   </LoadingButton>
 *
 * Disables itself while loading (prevents double-submit) and swaps the label
 * for a spinner + loadingText.
 */
export default function LoadingButton({
  loading = false,
  loadingText = 'Loading…',
  children,
  className = 'btn-primary',
  disabled = false,
  type = 'button',
  ...rest
}) {
  return (
    <button
      type={type}
      disabled={loading || disabled}
      aria-busy={loading}
      className={`${className} inline-flex items-center justify-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed`}
      {...rest}
    >
      {loading && <Loader2 size={16} className="animate-spin shrink-0" />}
      {loading ? loadingText : children}
    </button>
  );
}
