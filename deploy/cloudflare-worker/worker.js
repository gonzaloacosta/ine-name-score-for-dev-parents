// Serves the Vercel app under gonzaloacosta.me/name-score/ (the rest of the domain stays on
// GitHub Pages). The app uses relative URLs only, so stripping the prefix is all it takes.

const PREFIX = "/name-score";
const ALLOWED_METHODS = new Set(["GET", "HEAD"]);

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Relative URLs resolve against the directory: "/name-score" must become "/name-score/".
    if (url.pathname === PREFIX) {
      return Response.redirect(`${url.origin}${PREFIX}/${url.search}`, 301);
    }
    if (!url.pathname.startsWith(`${PREFIX}/`)) {
      return new Response("Not found", { status: 404 });
    }
    if (!ALLOWED_METHODS.has(request.method)) {
      return new Response("Method not allowed", { status: 405, headers: { Allow: "GET, HEAD" } });
    }

    // Forward only what the app uses; cookies and other headers stay at the edge.
    const headers = new Headers();
    for (const name of ["Accept", "Accept-Language"]) {
      const value = request.headers.get(name);
      if (value) headers.set(name, value);
    }
    // Assign the path onto the origin URL: never resolve it as a relative reference, or a
    // path like "//evil.example/x" would be protocol-relative and leave the origin host.
    const upstream = new URL(env.ORIGIN);
    upstream.pathname = url.pathname.slice(PREFIX.length);
    upstream.search = url.search;
    if (upstream.origin !== new URL(env.ORIGIN).origin) {
      return new Response("Bad request", { status: 400 });
    }
    const response = await fetch(upstream, { method: request.method, headers, redirect: "manual" });
    return keepRedirectUnderPrefix(response, env.ORIGIN);
  },
};

// Origin redirects point at the origin's root ("/x" or "https://<origin>/x"); without the
// prefix the browser would land on GitHub Pages. Other hosts and relative URLs pass through.
function keepRedirectUnderPrefix(response, origin) {
  const location = response.headers.get("Location");
  if (!location) return response;
  let path = null;
  if (location.startsWith("/") && !location.startsWith("//")) {
    path = location;
  } else if (/^https?:\/\//i.test(location)) {
    const target = new URL(location);
    if (target.origin === new URL(origin).origin) path = target.pathname + target.search + target.hash;
  }
  if (path === null) return response;
  const rewritten = new Response(response.body, response);
  rewritten.headers.set("Location", PREFIX + path);
  return rewritten;
}
