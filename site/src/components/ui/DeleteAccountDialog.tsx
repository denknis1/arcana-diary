// "Delete forever?" (owner decision 4, spec 4.4b §6): what goes and that it cannot be undone; "Download", "Delete
// forever", "Cancel" — no word to type. A modal dialog: focus goes to its title and stays inside, Escape and
// "Cancel" close it — not while the account is being deleted (review M22): then the three buttons are aria-disabled
// and ignore presses, so the focus stays where it is (handoff 10). A failed deletion or download is said here, above
// the buttons (review I5).
import { useEffect, useRef } from 'preact/hooks';
import { t } from '../../i18n';
import { handleDialogKey } from '../../lib/focus';
import type { Lang } from '../../lib/types';

interface Props {
  lang: Lang;
  busy: boolean;
  error: string | null; // the line of a failed deletion or download, shown inside the dialog
  onDownload: () => void;
  onDelete: () => void;
  onCancel: () => void;
}

export function DeleteAccountDialog({ lang, busy, error, onDownload, onDelete, onCancel }: Props) {
  const d = t(lang);
  const box = useRef<HTMLDivElement>(null);
  const title = useRef<HTMLHeadingElement>(null);
  const cancel = useRef(onCancel);
  cancel.current = busy ? () => {} : onCancel; // Escape waits for the deletion too
  const unlessBusy = (action: () => void) => () => {
    if (!busy) action();
  };

  useEffect(() => {
    title.current?.focus();
    const onKey = (event: KeyboardEvent) => box.current && handleDialogKey(event, box.current, () => cancel.current());
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div class="dialog-layer">
      <div class="dialog" role="alertdialog" aria-modal="true" aria-labelledby="delete-title" aria-describedby="delete-body"
        aria-busy={busy} ref={box}>
        <h2 id="delete-title" class="h2" tabIndex={-1} ref={title}>{d.deleteTitle}</h2>
        <p id="delete-body">{d.deleteBody}</p>
        {error ? <p role="alert">{error}</p> : null}
        <div class="dialog__actions">
          <button type="button" class="btn btn--outline" aria-disabled={busy} onClick={unlessBusy(onDownload)}>{d.deleteDownload}</button>
          <button type="button" class="btn btn--ink" aria-disabled={busy} onClick={unlessBusy(onDelete)}>{d.deleteForever}</button>
          <button type="button" class="btn btn--text" aria-disabled={busy} onClick={unlessBusy(onCancel)}>{d.cancel}</button>
        </div>
      </div>
    </div>
  );
}
