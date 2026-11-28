// Stage 8.1 review fixes that live in files, not in components: the calendar's turned cards (a class alone would not
// turn anything — I1) and the page texts about the guest's days.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8');

describe('the calendar CSS and page texts (stage 8.1 review)', () => {
  it('a reversed card in the calendar grid is turned upside down (I1)', () => {
    const css = read('../styles/global.css');
    expect(css).toMatch(/\.cal__day img\.is-reversed\s*\{[^}]*transform:\s*rotate\(180deg\)/);
  });

  it('a month that loads is dimmed, not removed (I4)', () => {
    expect(read('../styles/global.css')).toMatch(/\.cal--loading\b[^{]*\{[^}]*opacity/);
  });

  it('the FAQ and the page say the calendar shows 7 days and the cards are kept 60, not that the browser keeps 7', () => {
    const en = read('../data/pages/en/daily.json');
    const es = read('../data/pages/es/carta-del-dia.json');
    expect(en).not.toContain('this browser keeps your last 7 days');
    expect(en).toContain('shows your last 7 days');
    expect(en).toContain('kept for 60 days');
    expect(es).not.toMatch(/guarda tus últimos 7 días/);
    expect(es.match(/el calendario de este navegador muestra tus últimos 7 días/g)).toHaveLength(2);
    expect(es).toContain('se guardan 60 días');
  });
});
