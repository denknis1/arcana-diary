// The phone menu button (screens 11c, 11d): opens the menu below the header; Escape or the button closes it and
// focus returns to the button. On a desktop the menu is always in the header and this button is hidden.
import { useEffect, useRef, useState } from 'preact/hooks';
import { t } from '../i18n';
import type { Lang } from '../lib/types';
import { CloseIcon, MenuIcon } from '../components/ui/icons';

export default function MenuToggle({ lang, navId }: { lang: Lang; navId: string }) {
  const d = t(lang);
  const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    document.getElementById(navId)?.classList.toggle('is-open', open);
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
        button.current?.focus();
      }
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open]);

  return (
    <button type="button" class="menu-button" ref={button} aria-expanded={open} aria-controls={navId}
      aria-label={open ? d.menuClose : d.menuOpen} onClick={() => setOpen(!open)}>
      {open ? <CloseIcon /> : <MenuIcon />}
    </button>
  );
}
