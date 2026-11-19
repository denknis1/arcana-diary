// Help lines from the API's crisis answer (spec 4.2 §3.2): links are built only from digits and https addresses.
import type { HelpLine } from './types';

/** "tel:" + the digits (and a leading +) of a number such as "800 911 2000" or "1-800-799-7233". */
export function telHref(number: string): string | null {
  const digits = number.replace(/[^\d+]/g, '').replace(/(?!^)\+/g, '');
  return /\d{3,}/.test(digits) ? `tel:${digits}` : null;
}

/** "sms:" + the same digits, for a line that takes texts but names no SMS keyword (988 in the US). */
export function smsHref(number: string): string | null {
  const tel = telHref(number);
  return tel ? `sms:${tel.slice(4)}` : null;
}

export function canText(line: HelpLine): boolean {
  return Boolean(line.number) && line.channels.includes('sms') && !line.sms;
}

export function safeUrl(url: string | undefined): string | null {
  if (!url || url !== url.trim()) return null;
  try {
    const parsed = new URL(url);
    return parsed.protocol === 'https:' && !parsed.username && !parsed.password ? parsed.href : null;
  } catch {
    return null;
  }
}

export function canCall(line: HelpLine): boolean {
  return Boolean(line.number) && line.channels.includes('call');
}
