import { describe, expect, it } from 'vitest';
import { applyFollowupEvent, followupBody, followupOffer, followupRefusal, newFollowup } from './followups';

describe('followupOffer', () => {
  it('offers free follow-ups while any are left', () => {
    expect(followupOffer({ followups_left: 2, followup_attempts_left: 8 })).toBe('free');
    expect(followupOffer({ followups_left: 1, followup_attempts_left: 1 })).toBe('free');
  });

  it('offers a paid one only when followups_left == 0 and attempts are left', () => {
    expect(followupOffer({ followups_left: 0, followup_attempts_left: 3 })).toBe('paid');
    expect(followupOffer({ followups_left: 0, followup_attempts_left: 0 })).toBe('none');
    expect(followupOffer({ followups_left: 2, followup_attempts_left: 0 })).toBe('none');
    expect(followupOffer(null)).toBe('none');
  });
});

describe('followupBody', () => {
  it('sends the same tz and use_reading only as asked', () => {
    expect(followupBody('  And work? ', 'Europe/Madrid', false)).toEqual({ question: 'And work?', tz: 'Europe/Madrid', use_reading: false });
    expect(followupBody('And work?', undefined, true)).toEqual({ question: 'And work?', use_reading: true });
    expect(followupBody('And work?', 'UTC', false, 'n-1')).toEqual({ question: 'And work?', tz: 'UTC', use_reading: false, request_id: 'n-1' });
  });
});

describe('followupRefusal', () => {
  it('reads 402 confirm with the readings left, 402 plus, a crisis answer and errors', () => {
    expect(followupRefusal(402, { reason: 'confirm', remaining: 1 })).toEqual({ type: 'confirm', remaining: 1 });
    expect(followupRefusal(402, { reason: 'plus', remaining: 0 })).toEqual({ type: 'plus' });
    const crisis = { group: 'crisis', crisis: {}, helplines: { lines: [] } };
    expect(followupRefusal(200, crisis)).toEqual({ type: 'crisis', payload: crisis });
    expect(followupRefusal(429, { reason: 'attempts' })).toEqual({ type: 'error', error: 'attempts' });
    expect(followupRefusal(503, { reason: 'unavailable' })).toEqual({ type: 'error', error: 'unavailable' });
    expect(followupRefusal(409, { reason: 'busy' })).toEqual({ type: 'error', error: 'other' });
  });
});

describe('applyFollowupEvent', () => {
  it('streams text and takes the counts and used_reading from done', () => {
    let f = newFollowup(' And work? ');
    f = applyFollowupEvent(f, { event: 'meta', data: { soft_line: null, paid: true } }).followup;
    f = applyFollowupEvent(f, { event: 'text', data: { name: 'followup', text: 'It may ' } }).followup;
    f = applyFollowupEvent(f, { event: 'text', data: { name: 'followup', text: 'help.' } }).followup;
    const update = applyFollowupEvent(f, { event: 'done', data: { answer_shown: 'model', followups_left: 0, followup_attempts_left: 5, used_reading: true } });
    expect(update.followup).toEqual({ question: 'And work?', text: 'It may help.', status: 'done', softLine: null, usedReading: true });
    expect(update.counts).toEqual({ followups_left: 0, followup_attempts_left: 5 });
  });

  it('shows the base line on replace and fallback', () => {
    const f = newFollowup('q');
    expect(applyFollowupEvent(f, { event: 'replace', data: { sections: { followup: 'Base' } } }).followup).toMatchObject({ text: 'Base', status: 'replaced' });
    const failed = applyFollowupEvent(f, { event: 'fallback', data: { sections: { followup: 'Not counted' } } }).followup;
    expect(failed).toMatchObject({ text: 'Not counted', status: 'failed' });
    expect(applyFollowupEvent(failed, { event: 'done', data: { answer_shown: 'fallback' } }).followup.status).toBe('failed');
  });

  it('clears the shown text on a crisis event and hands the crisis on', () => {
    let f = applyFollowupEvent(newFollowup('q'), { event: 'text', data: { name: 'followup', text: 'Some words' } }).followup;
    const update = applyFollowupEvent(f, { event: 'crisis', data: { group: 'crisis', crisis: { title: 'T' }, helplines: { lines: [] } } });
    expect(update.followup.text).toBe('');
    expect(update.crisis).toMatchObject({ group: 'crisis' });
    f = applyFollowupEvent(newFollowup('q'), { event: 'error', data: { reason: 'db' } }).followup;
    expect(f.status).toBe('failed');
  });

  it('keeps a repeated follow-up that the API is still writing as streaming (it is read back)', () => {
    const f = applyFollowupEvent(newFollowup('q'), { event: 'meta', data: { followup: 2, replay: true, soft_line: null } }).followup;
    expect(applyFollowupEvent(f, { event: 'error', data: { reason: 'in_progress' } }).followup.status).toBe('streaming');
  });
});
