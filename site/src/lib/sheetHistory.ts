// The save sheet's own entry in the browser history (spec 4.4b §4, owner decision 14). Opening the sheet adds one
// entry above the night room's, so the phone's Back leaves only the sheet; closing it by × or Escape takes that entry
// back exactly once; when the room closes with the sheet open, ReadingIsland steps back over both entries at once.
// The entry keeps `arcanaNight: true`, so the room's own popstate handler (ReadingIsland) still sees a room entry.

export interface HistoryLike {
  readonly state: unknown;
  pushState(data: unknown, unused: string): void;
  back(): void;
}

export const SHEET_STATE = { arcanaNight: true, arcanaSheet: true } as const;

function isSheetEntry(state: unknown): boolean {
  return typeof state === 'object' && state !== null && (state as { arcanaSheet?: unknown }).arcanaSheet === true;
}

export class SheetHistory {
  private readonly history: HistoryLike;
  private onTop = false;

  constructor(history: HistoryLike) {
    this.history = history;
  }

  /** The sheet opened. */
  push(): void {
    if (this.onTop) return;
    this.history.pushState(SHEET_STATE, '');
    this.onTop = true;
  }

  /** popstate: true when Back left the sheet's entry (close the sheet, keep the room). */
  popped(state: unknown): boolean {
    if (!this.onTop || isSheetEntry(state)) return false;
    this.onTop = false;
    return true;
  }

  /** The sheet closes by ×, Escape or with the room: 1 when its entry is still on top (step back over it, once). */
  consume(): number {
    if (!this.onTop) return 0;
    this.onTop = false;
    return 1;
  }
}
