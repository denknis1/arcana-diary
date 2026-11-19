import { describe, expect, it } from 'vitest';
import { SseParser, readSse, type SseEvent } from './sse';

const STREAM =
  'event: meta\ndata: {"reading_id": "r1", "soft_line": null}\n\n' +
  'event: section\ndata: {"name": "headline"}\n\n' +
  'event: text\ndata: {"name": "headline", "text": "Un cambio que no elegiste, señal"}\n\n' +
  'event: done\ndata: {"answer_shown": "model"}\n\n';

function collect(chunks: string[]): SseEvent[] {
  const events: SseEvent[] = [];
  const parser = new SseParser((e) => events.push(e));
  for (const c of chunks) parser.feed(c);
  parser.finish();
  return events;
}

function body(parts: Uint8Array[]): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      for (const p of parts) controller.enqueue(p);
      controller.close();
    },
  });
}

describe('SseParser', () => {
  it('reads the API stream in one piece', () => {
    const events = collect([STREAM]);
    expect(events.map((e) => e.event)).toEqual(['meta', 'section', 'text', 'done']);
    expect(events[2].data).toEqual({ name: 'headline', text: 'Un cambio que no elegiste, señal' });
  });

  it('gives the same events however the stream is cut', () => {
    const whole = collect([STREAM]);
    for (let size = 1; size <= 7; size++) {
      const chunks = STREAM.match(new RegExp(`[\\s\\S]{1,${size}}`, 'g'))!;
      expect(collect(chunks)).toEqual(whole);
    }
  });

  it('accepts CRLF line ends, also split between chunks', () => {
    const crlf = STREAM.replace(/\n/g, '\r\n');
    expect(collect([crlf])).toEqual(collect([STREAM]));
    const cut = crlf.indexOf('\r\n\r\n') + 1;
    expect(collect([crlf.slice(0, cut), crlf.slice(cut)])).toEqual(collect([STREAM]));
  });

  it('skips comments and blocks without data, joins multi-line data, keeps non-JSON as text', () => {
    const events = collect([': keep-alive\n\nevent: ping\n\nevent: note\ndata: line one\ndata: line two\n\n']);
    expect(events).toEqual([{ event: 'note', data: 'line one\nline two' }]);
  });

  it('dispatches a last block that has no blank line after it', () => {
    expect(collect(['event: done\ndata: {"answer_shown": "fallback"}'])).toEqual([
      { event: 'done', data: { answer_shown: 'fallback' } },
    ]);
  });
});

describe('readSse', () => {
  it('decodes UTF-8 split across network chunks', async () => {
    const bytes = new TextEncoder().encode(STREAM);
    const at = bytes.indexOf(0xc3); // the first byte of "ñ"
    const events: SseEvent[] = [];
    await readSse(body([bytes.slice(0, at + 1), bytes.slice(at + 1)]), (e) => events.push(e));
    expect(events[2].data).toEqual({ name: 'headline', text: 'Un cambio que no elegiste, señal' });
    expect(events).toHaveLength(4);
  });

  it('rejects when the connection breaks, after passing on what arrived', async () => {
    const events: SseEvent[] = [];
    let pulls = 0;
    const broken = new ReadableStream<Uint8Array>({
      pull(controller) {
        pulls += 1;
        if (pulls === 1) controller.enqueue(new TextEncoder().encode('event: section\ndata: {"name": "card1"}\n\n'));
        else controller.error(new Error('network'));
      },
    });
    await expect(readSse(broken, (e) => events.push(e))).rejects.toThrow('network');
    expect(events).toEqual([{ event: 'section', data: { name: 'card1' } }]);
  });
});
