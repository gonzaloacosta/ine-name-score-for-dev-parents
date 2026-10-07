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
    const upstream = new URL(url.pathname.slice(PREFIX.length) + url.search, env.ORIGIN);
    return fetch(upstream, { method: request.method, headers, redirect: "manual" });
  },
};
