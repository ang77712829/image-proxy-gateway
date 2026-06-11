import { t } from '../../i18n.js';
import { button } from '../../components/buttons.js';
import { mount } from '../../components/dom.js';
import { pageHeader, panel } from '../../components/page.js';
import { unavailableState } from '../../components/states.js';
import { navigate } from '../../router.js';

export async function renderUnavailable({ titleKey, id = '' }) {
  const content = document.getElementById('content');
  mount(content,
    pageHeader({
      kicker: 'RESERVED',
      title: t(titleKey),
      subtitle: id ? `${t('wip.message')}: ${id}` : t('wip.message'),
      actions: [button(t('nav.dashboard'), { onClick: () => navigate('#/dashboard') })],
    }),
    panel({},
      unavailableState(t('wip.message'), t('wip.copy')),
    ),
  );
}
