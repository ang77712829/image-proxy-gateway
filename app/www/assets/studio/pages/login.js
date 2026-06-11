import { login } from '../auth.js';
import { navigate } from '../router.js';
import { t } from '../i18n.js';
import { button } from '../components/buttons.js';
import { el, mount } from '../components/dom.js';
import { field, input } from '../components/forms.js';

export async function render() {
  const content = document.getElementById('content');
  const username = input({ type: 'text', autocomplete: 'username', required: true });
  const password = input({ type: 'password', autocomplete: 'current-password', required: true });
  const error = el('p', { class: 'error-text', hidden: true });
  const submit = button(t('login.button'), { variant: 'primary', type: 'submit' });
  const form = el('form', { class: 'form-stack' },
    field(t('login.username'), username),
    field(t('login.password'), password),
    error,
    submit,
  );

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    error.hidden = true;
    submit.disabled = true;
    submit.textContent = t('login.loggingIn');
    try {
      await login(username.value, password.value);
      navigate('#/dashboard');
    } catch (err) {
      error.textContent = err?.message || t('login.failed');
      error.hidden = false;
      submit.disabled = false;
      submit.textContent = t('login.button');
    }
  });

  mount(content,
    el('div', { class: 'login-page' },
      el('section', { class: 'login-card' },
        el('h2', {}, t('login.title')),
        form,
      ),
    ),
  );
}
