import { api } from '../api.js';

async function fetchHealth() {
  const res = await fetch('/health', { credentials: 'include' });
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

function createCard(title) {
  const card = document.createElement('div');
  card.className = 'card';
  const h2 = document.createElement('h2');
  h2.textContent = title;
  card.appendChild(h2);
  return card;
}

export async function render() {
  const content = document.getElementById('content');
  content.innerHTML = '';

  const loading = document.createElement('div');
  loading.className = 'card';
  loading.textContent = 'Loading...';
  content.appendChild(loading);

  const healthCard = createCard('Health');
  const healthStatus = document.createElement('p');
  healthCard.appendChild(healthStatus);
  content.appendChild(healthCard);

  const sessionCard = createCard('Session');
  const sessionInfo = document.createElement('p');
  sessionCard.appendChild(sessionInfo);
  content.appendChild(sessionCard);

  try {
    const [health, session] = await Promise.all([
      fetchHealth().catch(() => ({ status: 'unavailable' })),
      api.get('/admin/session').catch(() => ({ authenticated: false })),
    ]);

    healthStatus.textContent = `Status: ${health.status || 'error'}`;

    if (session.authenticated) {
      sessionInfo.textContent = `Logged in as: ${session.username || 'unknown'}`;
    } else {
      sessionInfo.textContent = 'Not authenticated';
    }
  } catch (err) {
    healthStatus.textContent = 'Status: error';
    sessionInfo.textContent = 'Unable to load session';
  } finally {
    loading.remove();
  }
}
