// Screen tests (happy-dom): mount a Preact tree, wait for effects and fetches, find and press things the way a
// person does — by their visible text or label. Every DOM test file calls cleanup() in afterEach: it unmounts what
// mount() rendered, so a test's listeners on document and its timers never outlive it (Fable plan review I11).
import { render, type ComponentChild } from 'preact';
import { act } from 'preact/test-utils';

export interface Mounted {
  root: HTMLElement;
  unmount: () => void;
}

const mounted = new Set<HTMLElement>();

function unmountRoot(root: HTMLElement): void {
  if (!mounted.delete(root)) return;
  render(null, root);
  root.remove();
}

export async function mount(tree: ComponentChild): Promise<Mounted> {
  const root = document.createElement('div');
  document.body.appendChild(root);
  mounted.add(root);
  await act(() => {
    render(tree, root);
  });
  await settle();
  return { root, unmount: () => unmountRoot(root) };
}

/** For afterEach: unmounts every tree that is still mounted (their effect cleanups run), then empties the body. */
export function cleanup(): void {
  for (const root of Array.from(mounted)) unmountRoot(root);
  document.body.replaceChildren();
}

/** Lets pending promises (fake fetches, effects) run, several rounds. */
export async function settle(rounds = 10): Promise<void> {
  for (let i = 0; i < rounds; i++) {
    await act(async () => {
      await new Promise<void>((resolve) => setTimeout(resolve, 0));
    });
  }
}

/** Waits until `check` passes — it throws or returns false until then — for at most `timeoutMs`, then fails with
 * the check's own error. For screens that make several requests one after another (the diary). */
export async function waitFor(check: () => unknown, timeoutMs = 2000): Promise<void> {
  const start = Date.now();
  for (;;) {
    let failure: unknown;
    try {
      if (check() !== false) return;
      failure = new Error('waitFor: the check stayed false');
    } catch (error) {
      failure = error;
    }
    if (Date.now() - start > timeoutMs) throw failure;
    await settle(1);
  }
}

export function byText<T extends HTMLElement = HTMLElement>(root: ParentNode, text: string, selector = '*'): T {
  const found = Array.from(root.querySelectorAll<T>(selector)).filter((el) => el.textContent?.trim() === text);
  if (found.length === 0) throw new Error(`no element with the text "${text}"`);
  return found[found.length - 1]; // the innermost
}

export function queryText(root: ParentNode, text: string, selector = '*'): HTMLElement | null {
  try {
    return byText(root, text, selector);
  } catch {
    return null;
  }
}

export async function click(el: Element): Promise<void> {
  await act(() => {
    (el as HTMLElement).click();
  });
  await settle();
}

export async function typeInto(el: Element, value: string): Promise<void> {
  await act(() => {
    const input = el as HTMLInputElement | HTMLTextAreaElement;
    input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
}

export async function submit(form: Element): Promise<void> {
  await act(() => {
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  });
  await settle();
}
