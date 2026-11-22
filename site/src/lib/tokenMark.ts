// Which responses came from a request that carried Authorization: Bearer. authFetch marks the Response of each call;
// the reader asks about that one Response, so nothing leaks from one request to the next (no flag, no global state).
const marked = new WeakSet<Response>();

export function markCarried(response: Response): Response {
  marked.add(response);
  return response;
}

export function carriedToken(response: Response): boolean {
  return marked.has(response);
}
