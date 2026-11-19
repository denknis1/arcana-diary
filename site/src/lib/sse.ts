// Server-sent events read from a fetch() body (spec 4.4a §4: not EventSource, which cannot send headers).
// The API sends `event: <name>` and one `data: <json>` line per event, blocks separated by a blank line.

export interface SseEvent {
  event: string;
  data: unknown;
}

export class SseParser {
  private buffer = '';

  constructor(private readonly onEvent: (event: SseEvent) => void) {}

  /** Any split of the stream is fine, a CRLF cut in half included. */
  feed(chunk: string): void {
    let text = this.buffer + chunk;
    const heldCR = text.endsWith('\r');
    if (heldCR) text = text.slice(0, -1);
    text = text.replace(/\r\n?/g, '\n');
    let end = text.indexOf('\n\n');
    while (end >= 0) {
      this.dispatch(text.slice(0, end));
      text = text.slice(end + 2);
      end = text.indexOf('\n\n');
    }
    this.buffer = text + (heldCR ? '\r' : '');
  }

  /** The stream ended: a last block without its blank line still counts. */
  finish(): void {
    const rest = this.buffer.replace(/\r\n?/g, '\n');
    this.buffer = '';
    if (rest.trim()) this.dispatch(rest);
  }

  private dispatch(block: string): void {
    let event = 'message';
    const data: string[] = [];
    for (const line of block.split('\n')) {
      if (!line || line.startsWith(':')) continue;
      const colon = line.indexOf(':');
      const field = colon < 0 ? line : line.slice(0, colon);
      let value = colon < 0 ? '' : line.slice(colon + 1);
      if (value.startsWith(' ')) value = value.slice(1);
      if (field === 'event') event = value;
      else if (field === 'data') data.push(value);
    }
    if (data.length === 0) return;
    const raw = data.join('\n');
    let parsed: unknown = raw;
    try {
      parsed = JSON.parse(raw);
    } catch {
      // not JSON: passed on as text
    }
    this.onEvent({ event, data: parsed });
  }
}

/** How long a stream may stay silent before it counts as broken (the API sends no heartbeat). */
export const STREAM_IDLE_MS = 60_000;

/** Reads a whole SSE body; resolves when the body ends, rejects if the connection breaks.
 *  `onChunk` is called for every received chunk (the idle watchdog resets on it). */
export async function readSse(
  body: ReadableStream<Uint8Array>,
  onEvent: (event: SseEvent) => void,
  onChunk?: () => void,
): Promise<void> {
  const parser = new SseParser(onEvent);
  const decoder = new TextDecoder('utf-8');
  const reader = body.getReader();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    onChunk?.();
    parser.feed(decoder.decode(value, { stream: true }));
  }
  parser.feed(decoder.decode());
  parser.finish();
}
