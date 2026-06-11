import { safeText } from './security.js';

export function safeErrorMessage(error, fallback) {
  const hint = error?.safe?.human_hint;
  if (hint) return safeText(hint, 180);
  const message = error?.safe?.message;
  if (message) return safeText(message, 160);
  return fallback;
}

export function errorDiagnostics(error) {
  const safe = error?.safe || {};
  return {
    error_category: safe.error_category || '',
    human_hint: safe.human_hint || '',
    retryable: safe.retryable,
    gateway_stage: safe.gateway_stage || '',
    existing_job: safe.existing_job || null,
  };
}
