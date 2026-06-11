import { renderUnavailable } from '../features/wip/page.js';

export async function render() {
  await renderUnavailable({ titleKey: 'wip.generateVideoTitle' });
}
