// The diary's rules for the screen (spec 4.4b §5): which entry the address opens and its link.
import { pagePath } from './routes';
import type { Lang } from './types';

const ID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** `?r=<id>` of the diary page: the entry to open, or null for the list. */
export function entryParam(search: string): string | null {
  const id = new URLSearchParams(search).get('r');
  return id && ID.test(id) ? id.toLowerCase() : null;
}

export function entryHref(lang: Lang, id: string): string {
  return `${pagePath('diary', lang)}?r=${encodeURIComponent(id)}`;
}
