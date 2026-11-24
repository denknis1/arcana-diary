// The numbers and names the stage 5 texts leave as {placeholders} (spec stage 6 §2, owner decision 36): the limits
// from api/app/config.py, the yes/no counts from the deck and the editor's name, written to src/data/facts.json by
// tools/site/sync_site_data.py. The operator's facts come from content/operator.json, only the filled ones: a page
// that needs one that is empty stays hidden.
import factsData from '../data/facts.json';
import { fill, placeholders } from '../i18n';
import type { Lang } from './types';

/** A value is a string or a number; a date is written per language: {en: "December 14, 2026", es: "14 de …"}. */
export type Facts = Readonly<Record<string, string | number | Readonly<Record<string, string>>>>;

export const FACTS: Facts = factsData;

export function fillFacts(text: string, facts: Facts = FACTS, lang?: Lang): string {
  const values: Record<string, string | number> = {};
  for (const [key, value] of Object.entries(facts)) {
    if (typeof value !== 'object') values[key] = value;
    else if (lang && value[lang]) values[key] = value[lang];
  }
  return fill(text, values);
}

/** The placeholders of these texts that have no value in the facts, once each, sorted. */
export function missingFacts(texts: readonly string[], facts: Facts = FACTS): string[] {
  return [...new Set(texts.flatMap((text) => placeholders(text)))].filter((key) => !(key in facts)).sort();
}
