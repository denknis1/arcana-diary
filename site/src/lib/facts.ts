// The numbers and names the stage 5 texts leave as {placeholders} (spec stage 6 §2, owner decision 36): the limits
// from api/app/config.py, the yes/no counts from the deck and the editor's name, written to src/data/facts.json by
// tools/site/sync_site_data.py. The operator's data is not there yet: pages that need it stay hidden.
import factsData from '../data/facts.json';
import { fill, placeholders } from '../i18n';

export type Facts = Readonly<Record<string, string | number>>;

export const FACTS: Facts = factsData;

export function fillFacts(text: string, facts: Facts = FACTS): string {
  return fill(text, facts);
}

/** The placeholders of these texts that have no value in the facts, once each, sorted. */
export function missingFacts(texts: readonly string[], facts: Facts = FACTS): string[] {
  return [...new Set(texts.flatMap((text) => placeholders(text)))].filter((key) => !(key in facts)).sort();
}
