// @vitest-environment happy-dom
import { act } from 'preact/test-utils';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { AccountApi, DiaryEntry as Entry } from '../../lib/accountApi';
import { DAY_MS } from '../../lib/diary';
import { byText, cleanup, click, mount, queryText, settle, submit, typeInto } from '../../lib/testing/dom';
import { DiaryEntry } from './DiaryEntry';

const MADE = new Date(2026, 10, 1, 22, 0).toISOString(); // 1 November 2026, 22:00 on this device's clock (any zone)
const at = (days: number) => () => new Date(new Date(MADE).getTime() + days * DAY_MS);
const ENTRY: Entry = {
  id: 'e1', kind: 'three', topic: 'work', question: 'Will <i>the move</i> go well?', created_at: MADE,
  cards: [{ card_id: 'major-18-moon', position: 'past', reversed: false, name: 'The Moon' },
    { card_id: 'major-19-sun', position: 'present', reversed: false, name: 'The Sun' },
    { card_id: 'major-17-star', position: 'path', reversed: true, name: 'The Star' }],
  verdict: null, soft_line: 'Take it gently.', answer_shown: 'model', status: 'done', retries_left: 0,
  answer: { headline: 'Slow and steady.', card1: 'The Moon asks for patience.', synthesis: 'Step by step.', step: 'Write one list.' },
  followups: [{ n: 1, question: 'And then?', answer: 'Then rest.', soft_line: 'One day at a time.' }],
  followups_left: 1, followup_attempts_left: 7, in_diary: true, outcome: null, note: null,
};

function fakeApi(entry: Entry | null, status = 404) {
  const calls: Array<[string, unknown]> = [];
  const api: Pick<AccountApi, 'entry' | 'patchEntry' | 'deleteEntry'> = {
    entry: async (id) => {
      calls.push(['entry', id]);
      return entry ? { ok: true, status: 200, data: entry } : { ok: false, status, error: status === 404 ? 'gone' : 'other', body: null };
    },
    patchEntry: async (id, patch) => {
      calls.push(['patch', patch]);
      return { ok: true, status: 200, data: { id, outcome: patch.outcome ?? null, note: patch.note ?? null } };
    },
    deleteEntry: async (id) => {
      calls.push(['delete', id]);
      return { ok: true, status: 204, data: null };
    },
  };
  return { api, calls };
}

function entry(f: ReturnType<typeof fakeApi>, now: () => Date, extra: { navigate?: (url: string) => void; send?: () => void } = {}) {
  return <DiaryEntry lang="en" id="e1" api={f.api} onSignedOut={vi.fn()} now={now} navigate={extra.navigate} send={extra.send ?? vi.fn()} />;
}

afterEach(() => cleanup());

describe('a diary entry (screen 4b; spec 4.4b §5)', () => {
  it('shows the cards, the answer by sections and the follow-ups, all as text', async () => {
    const { root } = await mount(entry(fakeApi(ENTRY), at(3)));
    expect(root.querySelector('h2')?.textContent).toBe('Will <i>the move</i> go well?');
    expect(root.querySelector('h2 i')).toBeNull();
    expect(root.textContent).toContain('1 November 2026 · Three cards');
    for (const text of ['Slow and steady.', 'Take it gently.', 'The Moon asks for patience.', 'Step by step.', 'Write one list.',
      'Then rest.', 'One day at a time.']) { // the soft lines too (review M21)
      expect(root.textContent).toContain(text);
    }
    expect(root.querySelectorAll('.entry__cards .card-frame')).toHaveLength(3);
  });

  it('before 7 days: the day to come back, no outcome buttons (owner decision 6)', async () => {
    const { root } = await mount(entry(fakeApi(ENTRY), at(3)));
    expect(byText(root, 'Come back on 8 November 2026 to mark whether it came true.')).toBeTruthy();
    expect(queryText(root, 'Came true', 'button')).toBeNull();
  });

  it('opens on the named day from 00:00 local time, before 7 × 24 hours (owner decision 13, review I7)', async () => {
    const eve = await mount(entry(fakeApi(ENTRY), () => new Date(2026, 10, 7, 23, 59)));
    expect(byText(eve.root, 'Come back on 8 November 2026 to mark whether it came true.')).toBeTruthy();
    eve.unmount();
    const { root } = await mount(entry(fakeApi(ENTRY), () => new Date(2026, 10, 8, 9, 0))); // 8 November, 09:00
    expect(byText(root, 'Came true', 'button')).toBeTruthy();
    expect(queryText(root, 'Come back on 8 November 2026 to mark whether it came true.')).toBeNull();
  });

  it('from 7 days: Came true / Partly / No, change and clear; outcome_answered once, for the first answer', async () => {
    const f = fakeApi(ENTRY);
    const send = vi.fn();
    const { root, unmount } = await mount(entry(f, at(8), { send }));
    await click(byText(root, 'Partly', 'button'));
    expect(byText(root, 'Partly', 'button').getAttribute('aria-pressed')).toBe('true');
    await click(byText(root, 'No', 'button')); // a change, not a new answer (review M21)
    await click(byText(root, 'Remove answer', 'button'));
    expect(f.calls.filter(([name]) => name === 'patch')).toEqual([['patch', { outcome: 'partly' }], ['patch', { outcome: 'no' }],
      ['patch', { outcome: null }]]);
    expect(send).toHaveBeenCalledTimes(1);
    expect(send).toHaveBeenCalledWith({ name: 'outcome_answered', tool: null, lang: 'en', params: { after_days: 7, answer: 'partly' } });
    unmount();
    const late = vi.fn();
    const again = await mount(entry(fakeApi(ENTRY), at(40), { send: late }));
    await click(byText(again.root, 'No', 'button'));
    expect(late).toHaveBeenCalledWith({ name: 'outcome_answered', tool: null, lang: 'en', params: { after_days: 30, answer: 'no' } });
  });

  it('the note: 1000 characters at most, a counter, "Save note"', async () => {
    const f = fakeApi(ENTRY);
    const { root } = await mount(entry(f, at(3)));
    const note = root.querySelector<HTMLTextAreaElement>('textarea')!;
    expect(note.maxLength).toBe(1000);
    await typeInto(note, 'Talked to her on Friday.');
    expect(root.textContent).toContain('976 characters left');
    await submit(note.closest('form')!);
    expect(f.calls.at(-1)).toEqual(['patch', { note: 'Talked to her on Friday.' }]);
    expect(byText(root, 'Note saved.')).toBeTruthy();
  });

  it('delete asks first; Cancel keeps it, Delete removes it and goes back to the diary', async () => {
    const f = fakeApi(ENTRY);
    const navigate = vi.fn();
    const { root } = await mount(entry(f, at(3), { navigate }));
    await click(byText(root, 'Delete this entry', 'button'));
    expect(byText(root, 'Delete this reading from your diary? This cannot be undone.')).toBeTruthy();
    await click(byText(root, 'Cancel', 'button'));
    expect(document.activeElement?.textContent).toBe('Delete this entry');
    await click(byText(root, 'Delete this entry', 'button'));
    await click(byText(root, 'Delete', 'button'));
    expect(f.calls.at(-1)).toEqual(['delete', 'e1']);
    expect(navigate).toHaveBeenCalledWith('/diary');
  });

  it('a missing entry is "no longer available"; a crisis entry shows only its date and the help line', async () => {
    const gone = await mount(entry(fakeApi(null), at(3)));
    expect(byText(gone.root, 'This reading is no longer available.')).toBeTruthy();
    gone.unmount();
    const crisis = { ...ENTRY, answer_shown: 'crisis' as const, question: null, answer: null, followups: [] };
    const { root } = await mount(entry(fakeApi(crisis), at(8)));
    expect(root.querySelector('h2')?.textContent).toBe('1 November 2026');
    expect(byText(root, 'Free, confidential help lines', 'a')).toBeTruthy();
    expect(root.querySelector('textarea')).toBeNull();
    expect(queryText(root, 'Came true', 'button')).toBeNull();
  });

  it('an entry that could not be read: its line, the help line where it needs one, and "Try again" asks once more', async () => {
    let reads = 0;
    const api: Pick<AccountApi, 'entry' | 'patchEntry' | 'deleteEntry'> = {
      ...fakeApi(ENTRY).api,
      entry: async () => (reads++ === 0 ? { ok: false, status: 503, error: 'unavailable', body: { reason: 'db' } }
        : { ok: true, status: 200, data: ENTRY }),
    };
    const { root } = await mount(<DiaryEntry lang="en" id="e1" api={api} onSignedOut={vi.fn()} now={at(3)} send={vi.fn()} />);
    expect(byText(root, 'The service is unavailable right now. Please try again in a few minutes.')).toBeTruthy();
    expect(root.querySelector('.help-line')).not.toBeNull();
    await click(byText(root, 'Try again', 'button'));
    expect(root.querySelector('h2')?.textContent).toBe('Will <i>the move</i> go well?');
    expect(reads).toBe(2);
  });

  it('a refused change: 401 "sign_in" signs out here, a 401 without JSON is the stage line (review I4)', async () => {
    const onSignedOut = vi.fn();
    const answers = [{ ok: false as const, status: 401, error: 'other' as const, body: { reason: 'sign_in' } },
      { ok: false as const, status: 401, error: 'stage' as const, body: null }];
    const api: Pick<AccountApi, 'entry' | 'patchEntry' | 'deleteEntry'> = {
      ...fakeApi(ENTRY).api, patchEntry: async () => answers.shift()!,
    };
    const { root } = await mount(<DiaryEntry lang="en" id="e1" api={api} onSignedOut={onSignedOut} now={at(8)} send={vi.fn()} />);
    await click(byText(root, 'Partly', 'button'));
    expect(onSignedOut).toHaveBeenCalledTimes(1);
    await click(byText(root, 'Partly', 'button'));
    expect(onSignedOut).toHaveBeenCalledTimes(1);
    expect(byText(root, 'Your session on this preview site has expired. Reload the page to continue.')).toBeTruthy();
    expect(byText(root, 'Try again', 'button')).toBeTruthy(); // it reloads the page
    expect(queryText(root, 'Something went wrong. Please try again.')).toBeNull();
  });

  it('the outcome buttons wait while their change is saved (review M21)', async () => {
    const pending: { resolve?: () => void } = {};
    const api: Pick<AccountApi, 'entry' | 'patchEntry' | 'deleteEntry'> = {
      ...fakeApi(ENTRY).api,
      patchEntry: (id, patch) => new Promise((resolve) => {
        pending.resolve = () => resolve({ ok: true, status: 200, data: { id, outcome: patch.outcome ?? null, note: null } });
      }),
    };
    const { root } = await mount(<DiaryEntry lang="en" id="e1" api={api} onSignedOut={vi.fn()} now={at(8)} send={vi.fn()} />);
    await click(byText(root, 'Came true', 'button'));
    expect(byText<HTMLButtonElement>(root, 'No', 'button').getAttribute('aria-disabled')).toBe('true');
    expect(byText<HTMLButtonElement>(root, 'No', 'button').disabled).toBe(false); // aria-disabled keeps focus where it is
    await act(() => {
      pending.resolve?.();
    });
    await settle();
    expect(byText<HTMLButtonElement>(root, 'No', 'button').getAttribute('aria-disabled')).not.toBe('true');
    expect(byText(root, 'Came true', 'button').getAttribute('aria-pressed')).toBe('true');
  });

  it('a press while an outcome is saving does nothing, and the pressed button keeps focus', async () => {
    const patches: unknown[] = [];
    const pending: { resolve?: () => void } = {};
    const api: Pick<AccountApi, 'entry' | 'patchEntry' | 'deleteEntry'> = {
      ...fakeApi(ENTRY).api,
      patchEntry: (id, patch) => new Promise((resolve) => {
        patches.push(patch);
        pending.resolve = () => resolve({ ok: true, status: 200, data: { id, outcome: patch.outcome ?? null, note: null } });
      }),
    };
    const { root } = await mount(<DiaryEntry lang="en" id="e1" api={api} onSignedOut={vi.fn()} now={at(8)} send={vi.fn()} />);
    const yes = byText<HTMLButtonElement>(root, 'Came true', 'button');
    yes.focus();
    await click(yes);
    expect(document.activeElement).toBe(yes);
    await click(byText(root, 'No', 'button'));
    expect(patches).toEqual([{ outcome: 'yes' }]);
    await act(() => {
      pending.resolve?.();
    });
    await settle();
    expect(document.activeElement).toBe(yes);
  });

  it('after Clear, focus moves to the first outcome button', async () => {
    const { root } = await mount(entry(fakeApi({ ...ENTRY, outcome: 'no' }), at(8)));
    const clear = byText(root, 'Remove answer', 'button');
    clear.focus();
    await click(clear);
    expect(queryText(root, 'Remove answer', 'button')).toBeNull();
    expect(document.activeElement).toBe(byText(root, 'Came true', 'button'));
  });

  it('the visible note counter is quiet; a hidden status speaks only when 100, 50 and 0 are crossed', async () => {
    const { root } = await mount(entry(fakeApi(ENTRY), at(3)));
    const note = root.querySelector<HTMLTextAreaElement>('textarea')!;
    const counter = byText(root, '1000 characters left', 'p');
    expect(counter.getAttribute('aria-live')).toBeNull();
    expect(note.getAttribute('aria-describedby')).toBe(counter.id);
    expect(counter.id).not.toBe('');
    const status = root.querySelector<HTMLElement>('.visually-hidden[role="status"]')!;
    expect(status.textContent).toBe('');
    await typeInto(note, 'x'.repeat(800));
    await typeInto(note, 'x'.repeat(899));
    expect(status.textContent).toBe('');
    await typeInto(note, 'x'.repeat(900));
    expect(status.textContent).toBe('100 characters left');
    await typeInto(note, 'x'.repeat(910));
    expect(status.textContent).toBe('100 characters left'); // not re-spoken on every key
    await typeInto(note, 'x'.repeat(950));
    expect(status.textContent).toBe('50 characters left');
    await typeInto(note, 'x'.repeat(1000));
    expect(status.textContent).toBe('0 characters left');
  });

  it('a delete that answers "gone" (already deleted elsewhere) goes back to the diary like a success', async () => {
    const navigate = vi.fn();
    const api: Pick<AccountApi, 'entry' | 'patchEntry' | 'deleteEntry'> = {
      ...fakeApi(ENTRY).api, deleteEntry: async () => ({ ok: false, status: 404, error: 'gone', body: null }),
    };
    const { root } = await mount(<DiaryEntry lang="en" id="e1" api={api} onSignedOut={vi.fn()} now={at(3)} navigate={navigate} send={vi.fn()} />);
    await click(byText(root, 'Delete this entry', 'button'));
    await click(byText(root, 'Delete', 'button'));
    expect(navigate).toHaveBeenCalledWith('/diary');
  });

  it('a failure line sits next to the action that failed', async () => {
    const fail = { ok: false as const, status: 503, error: 'unavailable' as const, body: { reason: 'db' } };
    const api: Pick<AccountApi, 'entry' | 'patchEntry' | 'deleteEntry'> = {
      ...fakeApi(ENTRY).api,
      patchEntry: async (_id, patch) => (patch.outcome !== undefined ? fail : { ...fail, status: 503 }),
      deleteEntry: async () => fail,
    };
    const { root } = await mount(<DiaryEntry lang="en" id="e1" api={api} onSignedOut={vi.fn()} now={at(8)} send={vi.fn()} />);
    await click(byText(root, 'Partly', 'button'));
    expect(root.querySelector('.entry__outcome .entry__error')).not.toBeNull();
    expect(root.querySelector('.entry__note .entry__error')).toBeNull();
    await submit(root.querySelector('form')!);
    expect(root.querySelector('.entry__outcome .entry__error')).toBeNull(); // one line at a time
    expect(root.querySelector('.entry__note .entry__error')).not.toBeNull();
    await click(byText(root, 'Delete this entry', 'button'));
    await click(byText(root, 'Delete', 'button'));
    expect(root.querySelector('.entry__note .entry__error')).toBeNull();
    expect(root.querySelector('.entry__delete .entry__error')).not.toBeNull();
  });
});
