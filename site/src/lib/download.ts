// A file saved from the browser (the export of spec 4.3 §8, the calendar file of spec 4.4b §7): an object URL and a
// download link, removed right after. The URL is freed only after a minute: iOS Safari asks before it saves a blob
// and may read the URL late (Fable plan review I8).
export type SaveFile = (blob: Blob, filename: string) => void;

export const REVOKE_AFTER_MS = 60_000;

export const saveFile: SaveFile = (blob, filename) => {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.rel = 'noopener';
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), REVOKE_AFTER_MS);
};
