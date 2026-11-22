// The site's API client for islands: the browser's fetch, with the token of a signed-in person on /api/* (spec 4.4b
// §3). For a guest nothing changes and the sign-in library is never loaded.
import { browserFetch, createApi, type Api, type ApiOptions, type FetchFn } from './api';
import { getAuth } from './auth';
import { authFetch } from './authFetch';

export function siteFetch(): FetchFn {
  return authFetch(browserFetch(), getAuth);
}

export function siteApi(options?: ApiOptions): Api {
  return createApi(siteFetch(), options);
}
