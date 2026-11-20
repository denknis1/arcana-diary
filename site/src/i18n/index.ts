// One dictionary per language (spec 4.4a §7). Pages and islands take strings only from here.
import type { Lang } from '../lib/types';
import { en, enDrafts, type Dict, type DictKey } from './en';
import { es, esDrafts } from './es';

export type { Dict, DictKey };

export const DICTS: Readonly<Record<Lang, Dict>> = { en, es };
export const DRAFTS: Readonly<Record<Lang, readonly DictKey[]>> = { en: enDrafts, es: esDrafts };

export function t(lang: Lang): Dict {
  return DICTS[lang];
}

/** "{name} — full meaning" + {name: "The Moon"}; an unknown placeholder stays as it is. */
export function fill(template: string, vars: Readonly<Record<string, string | number>>): string {
  return template.replace(/\{(\w+)\}/g, (match, key: string) => (key in vars ? String(vars[key]) : match));
}

export function placeholders(template: string): string[] {
  return [...new Set([...template.matchAll(/\{(\w+)\}/g)].map((m) => m[1]))].sort();
}
