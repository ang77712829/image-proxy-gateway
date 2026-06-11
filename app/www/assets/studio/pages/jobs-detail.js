import { renderUnavailable } from '../features/wip/page.js';

export async function render(params = {}) {
  await renderUnavailable({ titleKey: 'wip.jobDetailTitle', id: params.id || '' });
}
