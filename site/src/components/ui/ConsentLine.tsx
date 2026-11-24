// "By continuing you confirm you are 18 or older and accept the Terms and the Privacy policy." (legal review B3):
// one quiet line under the draw button and in the sign-in block. The two names are links only while their pages are
// open (hidden service pages have no address: the text stays without the link, like the provider line).
import { t } from '../../i18n';
import type { Lang } from '../../lib/types';

interface Props {
  lang: Lang;
  termsHref?: string;
  privacyHref?: string;
}

export function ConsentLine({ lang, termsHref, privacyHref }: Props) {
  const d = t(lang);
  const word = (text: string, href?: string) => (href ? <a href={href}>{text}</a> : text);
  const parts = d.consentLine.split(/(\{terms\}|\{privacy\})/);
  return (
    <p class="consent-line">
      {parts.map((part) => (part === '{terms}' ? word(d.termsLink, termsHref)
        : part === '{privacy}' ? word(d.privacyLink, privacyHref) : part))}
    </p>
  );
}
