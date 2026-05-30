/** Build absolute URL for a path using the current request origin. */
export function absoluteUrl(path: string, baseUrl: string): string {
  return new URL(path.startsWith("/") ? path : `/${path}`, baseUrl).toString();
}

/** `/login?redirect_url=<encoded absolute target>` */
export function loginUrlWithRedirect(redirectTarget: string, baseUrl: string): string {
  const login = new URL("/login", baseUrl);
  login.searchParams.set("redirect_url", absoluteUrl(redirectTarget, baseUrl));
  return login.pathname + login.search;
}

/** Full login URL string for middleware `unauthenticatedUrl` (must be absolute). */
export function loginRedirectForRequest(
  requestUrl: string,
  redirectPath = "/chat",
): string {
  const login = new URL("/login", requestUrl);
  login.searchParams.set("redirect_url", absoluteUrl(redirectPath, requestUrl));
  return login.toString();
}
