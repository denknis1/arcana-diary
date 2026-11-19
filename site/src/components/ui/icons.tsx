// Thin line icons in currentColor (design system: Iconography). Decorative: hidden from screen readers.

export function CloseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
      <path d="M3 3l10 10M13 3L3 13" />
    </svg>
  );
}

export function MenuIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
      <path d="M3 7h16M3 15h16" />
    </svg>
  );
}

export function CheckIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
      <path d="M2 7.5l3 3 7-7" />
    </svg>
  );
}

/** Yes, No and Not yet differ by shape (check, cross, hourglass), never by colour alone. */
export function VerdictIcon({ value }: { value: 'yes' | 'no' | 'unclear' }) {
  const paths = {
    yes: 'M7.5 13.5l3.5 3.5 7.5-8',
    no: 'M8.5 8.5l9 9M17.5 8.5l-9 9',
    unclear: 'M9 7h8M9 19h8M10 7c0 3.5 6 4.5 6 6s-6 2.5-6 6M16 7c0 3.5-6 4.5-6 6s6 2.5 6 6',
  };
  return (
    <svg width="40" height="40" viewBox="0 0 26 26" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
      <circle cx="13" cy="13" r="12" />
      <path d={paths[value]} />
    </svg>
  );
}
