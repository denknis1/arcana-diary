import { describe, expect, it } from 'vitest';
import { createAccountApi, exportName } from './accountApi';
import { fakeFetch, jsonResponse } from './testing/fakes';

describe('account API', () => {
  it('asks for a claim token of the reading and claims with the tokens, with or without this device', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(201, { token: 't1', expires_at: 'x' }), jsonResponse(200, { claimed: ['r1'] }),
      jsonResponse(200, { claimed: [] }));
    const api = createAccountApi(fetch);
    expect(await api.claimToken('r 1')).toMatchObject({ ok: true, data: { token: 't1' } });
    expect(await api.claim(['t1'], false)).toMatchObject({ ok: true, data: { claimed: ['r1'] } });
    await api.claim([], true);
    expect(calls.map((c) => [c.method, c.url, c.body])).toEqual([
      ['POST', '/api/readings/r%201/claim-token', undefined], ['POST', '/api/account/claim', { tokens: ['t1'], device: false }],
      ['POST', '/api/account/claim', { tokens: [], device: true }],
    ]);
  });

  it('pages the diary with an encoded next_before', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(200, { items: [], next_before: null, hidden_count: 0 }));
    await createAccountApi(fetch).diary('2026-11-20T18:00:00+00:00', 10);
    expect(calls[0].url).toBe('/api/diary?before=2026-11-20T18%3A00%3A00%2B00%3A00&limit=10');
  });

  it('patches and deletes an entry, reads the account, sets consent and deletes the account', async () => {
    const { fetch, calls } = fakeFetch(jsonResponse(200, {}), new Response(null, { status: 204 }), jsonResponse(200, {}),
      jsonResponse(200, {}), jsonResponse(200, { deleted: true }));
    const api = createAccountApi(fetch);
    await api.patchEntry('r1', { outcome: null });
    expect(await api.deleteEntry('r1')).toEqual({ ok: true, status: 204, data: null });
    await api.account('America/Mexico_City');
    await api.setConsent(true);
    expect(await api.deleteAccount()).toMatchObject({ ok: true, data: { deleted: true } });
    expect(calls.map((c) => [c.method, c.url, c.body])).toEqual([
      ['PATCH', '/api/diary/r1', { outcome: null }], ['DELETE', '/api/diary/r1', undefined],
      ['GET', '/api/account?tz=America%2FMexico_City', undefined], ['PATCH', '/api/account', { reminders_consent: true }],
      ['DELETE', '/api/account', { confirm: 'DELETE' }],
    ]);
  });

  it('downloads the export as a file with its own name', async () => {
    const file = new Response('{"readings":[]}', { status: 200, headers: {
      'content-type': 'application/json', 'content-disposition': 'attachment; filename="arcana-diary-2026-11-22.json"' } });
    const { fetch } = fakeFetch(file, jsonResponse(401, { reason: 'sign_in' }), new TypeError('offline'));
    const api = createAccountApi(fetch);
    const ok = await api.exportFile();
    expect(ok.ok && ok.filename).toBe('arcana-diary-2026-11-22.json');
    expect(ok.ok && (await ok.blob.text())).toBe('{"readings":[]}');
    expect(await api.exportFile()).toEqual({ ok: false, status: 401, error: 'other' });
    expect(await api.exportFile()).toEqual({ ok: false, status: 0, error: 'network' });
  });

  it('never takes a strange file name from the header', () => {
    expect(exportName('attachment; filename="../../x.sh"', '2026-11-22')).toBe('arcana-diary-2026-11-22.json');
    expect(exportName(null, '2026-11-22')).toBe('arcana-diary-2026-11-22.json');
  });
});
