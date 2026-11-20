// The help link added to the 429, 403 and 503 messages (spec 4.2 §10.8): findahelpline.com lists free,
// confidential lines for every country.
import { t } from '../../i18n';
import { HELP_URL } from '../../lib/routes';
import type { Lang } from '../../lib/types';

export function HelpLine({ lang }: { lang: Lang }) {
  const d = t(lang);
  return (
    <p class="help-line">
      {d.helpLead}{' '}
      <a href={HELP_URL} rel="noopener noreferrer" target="_blank">{d.helpLink}</a>
    </p>
  );
}
