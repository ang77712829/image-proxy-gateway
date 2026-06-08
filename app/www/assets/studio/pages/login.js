import { login } from '../auth.js';
import { navigate } from '../router.js';

export async function render() {
  const el = document.getElementById('content');
  el.innerHTML = `
    <div class="login-page">
      <div class="login-card card">
        <h2>AngeMedia Studio</h2>
        <form id="login-form">
          <label class="field-label">Username
            <input id="login-user" type="text" autocomplete="username" required>
          </label>
          <label class="field-label">Password
            <input id="login-pass" type="password" autocomplete="current-password" required>
          </label>
          <div id="login-error" class="error-text" hidden></div>
          <button id="login-btn" class="btn btn-primary" type="submit">Login</button>
        </form>
      </div>
    </div>`;
  document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const errEl = document.getElementById('login-error');
    const btn = document.getElementById('login-btn');
    errEl.hidden = true;
    btn.disabled = true;
    btn.textContent = 'Logging in...';
    try {
      await login(
        document.getElementById('login-user').value,
        document.getElementById('login-pass').value,
      );
      navigate('#/dashboard');
    } catch (err) {
      errEl.textContent = err.message || 'Login failed';
      errEl.hidden = false;
      btn.disabled = false;
      btn.textContent = 'Login';
    }
  });
}
