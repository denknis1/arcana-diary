import { describe, expect, it } from 'vitest';
import { canCall, canText, safeUrl, smsHref, telHref } from './helplines';
import type { HelpLine } from './types';

describe('help lines', () => {
  it('dials only digits', () => {
    expect(telHref('800 911 2000')).toBe('tel:8009112000');
    expect(telHref('1-800-799-7233')).toBe('tel:18007997233');
    expect(telHref('988')).toBe('tel:988');
    expect(telHref('+34 024')).toBe('tel:+34024');
    expect(telHref('call us')).toBeNull();
  });

  it('texts 988 from the same digits when the line names no keyword', () => {
    expect(smsHref('988')).toBe('sms:988');
    expect(smsHref('none')).toBeNull();
    const line = { name: '988', number: '988', channels: ['call', 'sms'], hours: '24/7', topic: 'crisis', purpose: 'p' } as HelpLine;
    expect(canText(line)).toBe(true);
    expect(canText({ ...line, sms: 'START to 88788' })).toBe(false);
    expect(canText({ ...line, channels: ['call'] })).toBe(false);
  });

  it('opens only https addresses', () => {
    expect(safeUrl('https://findahelpline.com')).toBe('https://findahelpline.com/');
    expect(safeUrl('javascript:alert(1)')).toBeNull();
    expect(safeUrl('http://example.com')).toBeNull();
    expect(safeUrl(undefined)).toBeNull();
  });

  it('offers a call only for lines that take calls', () => {
    const line = { name: 'Línea 024', number: '024', channels: ['call'], hours: '24/7', topic: 'crisis', purpose: 'p' } as HelpLine;
    expect(canCall(line)).toBe(true);
    expect(canCall({ ...line, channels: ['web'] })).toBe(false);
    expect(canCall({ ...line, number: undefined })).toBe(false);
  });
});

describe('safeUrl rejects', () => {
  it.each([
    'data:text/html,<b>x</b>', '//evil.example', ' https://ok.example', 'https://user:pass@host.example',
    'https://user@host.example', 'http://host.example', 'javascript:alert(1)',
  ])('%s', (url) => expect(safeUrl(url)).toBeNull());
  it('accepts a plain https address', () => expect(safeUrl('https://host.example/a')).toBe('https://host.example/a'));
});
