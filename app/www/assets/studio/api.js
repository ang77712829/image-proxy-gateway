const BASE = '/v1';

let unauthorizedHandler = null;

export function setUnauthorizedHandler(handler) {
  unauthorizedHandler = handler;
}

async function request(method, path, body, isLoginRequest = false) {
  const opts = {
    method,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(`${BASE}${path}`, opts);
  if (res.status === 401 && !isLoginRequest && unauthorizedHandler) {
    unauthorizedHandler();
    throw new Error('Session expired');
  }
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    const err = new Error(`API ${res.status}: ${text || res.statusText}`);
    err.status = res.status;
    throw err;
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  get:    (path) => request('GET', path),
  post:   (path, body, isLoginRequest = false) => request('POST', path, body, isLoginRequest),
  patch:  (path, body) => request('PATCH', path, body),
  delete: (path) => request('DELETE', path),
};
