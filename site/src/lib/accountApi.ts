// The account's requests (spec 2026-11-19 stage 4.3 §4, §6, §8; spec 4.4b §4–§6): claim tokens and the claim, the
// diary list, one entry, its outcome and note, delete; the account, consent, export, delete. Everything that comes
// back is shown as text only.
import { callJson, jsonBody, readingPath, withQuery, type ApiResult, type FetchFn } from './api';
import { classifyError, type ErrorKind } from './errors';
import type { DrawnCard, Kind, Lang, ReadingView } from './types';

export type Outcome = 'yes' | 'partly' | 'no';

export interface DiaryItem {
  id: string;
  created_at: string;
  lang: Lang;
  kind: Kind;
  topic: string | null;
  question: string | null;
  headline: string | null;
  answer_shown: 'model' | 'fallback' | 'crisis' | null;
  cards: DrawnCard[];
  outcome: Outcome | null;
  has_note: boolean;
  followups: number;
}

export interface DiaryPage {
  items: DiaryItem[];
  next_before: string | null;
  hidden_count: number; // spec 4.4b §5: older readings beyond the free 10
}

/** GET /api/readings/{id} for the account that owns it. */
export interface DiaryEntry extends ReadingView {
  created_at: string;
  question: string | null;
  topic: string | null;
  in_diary: boolean;
  outcome: Outcome | null;
  note: string | null;
}

export interface EntryPatch {
  outcome?: Outcome | null;
  note?: string | null;
}

export interface Account {
  email: string | null;
  created_at: string;
  reminders_consent: boolean;
  consent_at: string | null;
  limit: number;
  used: number;
  remaining: number;
  day: string;
}

export type ExportResult = { ok: true; blob: Blob; filename: string } | { ok: false; status: number; error: ErrorKind };

export interface AccountApi {
  claimToken(readingId: string): Promise<ApiResult<{ token: string; expires_at: string }>>;
  /** `device`: also move this device's guest readings (spec 4.4b §4, owner decision 12; API Task 6). */
  claim(tokens: string[], device: boolean): Promise<ApiResult<{ claimed: string[] }>>;
  diary(before?: string, limit?: number): Promise<ApiResult<DiaryPage>>;
  entry(id: string, tz: string | undefined): Promise<ApiResult<DiaryEntry>>;
  patchEntry(id: string, patch: EntryPatch): Promise<ApiResult<{ id: string; outcome: Outcome | null; note: string | null }>>;
  deleteEntry(id: string): Promise<ApiResult<null>>;
  account(tz: string | undefined): Promise<ApiResult<Account>>;
  setConsent(on: boolean): Promise<ApiResult<Pick<Account, 'email' | 'reminders_consent' | 'consent_at'>>>;
  exportFile(): Promise<ExportResult>;
  deleteAccount(): Promise<ApiResult<{ deleted: boolean }>>;
}

const JSON_HEADERS = { 'content-type': 'application/json' };
const json = (method: string, body: unknown): RequestInit => ({ method, headers: JSON_HEADERS, body: JSON.stringify(body) });

/** The file name of Content-Disposition, else today's export name. */
export function exportName(disposition: string | null, today: string): string {
  const name = /filename="([^"]+)"/.exec(disposition ?? '')?.[1];
  return name && /^[\w.-]+$/.test(name) ? name : `arcana-diary-${today}.json`;
}

export function createAccountApi(fetchFn: FetchFn): AccountApi {
  const call = <T>(path: string, init?: RequestInit) => callJson<T>(fetchFn, path, init);
  return {
    claimToken: (readingId) => call(readingPath(readingId, '/claim-token'), { method: 'POST' }),
    claim: (tokens, device) => call('/api/account/claim', json('POST', { tokens, device })),
    diary: (before, limit) => call(withQuery('/api/diary', { before, limit: limit ? String(limit) : undefined })),
    entry: (id, tz) => call(withQuery(readingPath(id), { tz })),
    patchEntry: (id, patch) => call(`/api/diary/${encodeURIComponent(id)}`, json('PATCH', patch)),
    deleteEntry: (id) => call(`/api/diary/${encodeURIComponent(id)}`, { method: 'DELETE' }),
    account: (tz) => call(withQuery('/api/account', { tz })),
    setConsent: (on) => call('/api/account', json('PATCH', { reminders_consent: on })),
    async exportFile() {
      let response: Response;
      try {
        response = await fetchFn('/api/account/export', { method: 'GET' });
      } catch {
        return { ok: false, status: 0, error: 'network' };
      }
      if (!response.ok) return { ok: false, status: response.status, error: classifyError(response.status, await jsonBody(response)) };
      const today = new Date().toISOString().slice(0, 10);
      return { ok: true, blob: await response.blob(), filename: exportName(response.headers.get('content-disposition'), today) };
    },
    deleteAccount: () => call('/api/account', json('DELETE', { confirm: 'DELETE' })),
  };
}
