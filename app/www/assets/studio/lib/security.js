const SECRET_FIELD_NAMES = [
  'key',
  'key_hash',
  'api_key',
  '_api_key',
  'secret',
  '_secret',
  'token',
  'access_token',
  'password',
  'raw',
  'raw_body',
  'raw_response',
  'raw_error',
  'exception',
  'stack',
  'local_path',
];

const SECRET_TEXT_PATTERNS = [
  /\bsk-[A-Za-z0-9_-]{8,}/g,
  /\bam-[A-Za-z0-9_-]{8,}/g,
  /Bearer\s+[A-Za-z0-9._-]+/gi,
  /([?&](?:key|token|secret|api_key)=)[^&\s]+/gi,
];

export function hasForbiddenField(value, fields = SECRET_FIELD_NAMES) {
  if (!value || typeof value !== 'object') return false;
  if (Array.isArray(value)) return value.some((item) => hasForbiddenField(item, fields));
  return Object.keys(value).some((key) => fields.includes(key)) ||
    Object.values(value).some((item) => hasForbiddenField(item, fields));
}

export function redactInlineSecret(value) {
  let output = String(value || '');
  SECRET_TEXT_PATTERNS.forEach((pattern) => {
    output = output.replace(pattern, (match, prefix) => prefix ? `${prefix}[redacted]` : '[redacted]');
  });
  return output;
}

export function sanitizeUrlForDisplay(value) {
  if (!value) return '';
  try {
    const url = new URL(String(value));
    url.username = '';
    url.password = '';
    url.search = '';
    url.hash = '';
    return url.toString().replace(/\/$/, '');
  } catch (_) {
    return '';
  }
}

export function safeText(value, max = 160) {
  const text = redactInlineSecret(value).replace(/\s+/g, ' ').trim();
  if (text.length <= max) return text;
  return `${text.slice(0, Math.max(0, max - 1))}…`;
}
