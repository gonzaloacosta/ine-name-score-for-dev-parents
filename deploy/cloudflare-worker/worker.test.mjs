// node --test deploy/cloudflare-worker/
import assert from "node:assert/strict";
import { test } from "node:test";

import worker from "./worker.js";

const ORIGIN = "https://origin.example";

async function proxied(path, init = {}) {
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url: String(url), options });
    return new Response("ok");
  };
  const response = await worker.fetch(new Request(`https://gonzaloacosta.me${path}`, init), { ORIGIN });
  return { response, calls };
}

test("forwards the path without the prefix to the origin", async () => {
  const { calls } = await proxied("/name-score/api/rank?top=3");
  assert.equal(calls[0].url, `${ORIGIN}/api/rank?top=3`);
});

test("never leaves the origin host (protocol-relative path)", async () => {
  for (const path of ["/name-score//evil.example/x", "/name-score///evil.example/x", "/name-score/\\\\evil.example/x"]) {
    const { calls } = await proxied(path);
    assert.equal(new URL(calls[0].url).host, "origin.example", `${path} escaped to ${calls[0].url}`);
  }
});

test("redirects the bare prefix to the directory", async () => {
  const { response, calls } = await proxied("/name-score?sexo=nino");
  assert.equal(response.status, 301);
  assert.equal(response.headers.get("Location"), "https://gonzaloacosta.me/name-score/?sexo=nino");
  assert.equal(calls.length, 0);
});

test("rejects other paths and methods without calling the origin", async () => {
  assert.equal((await proxied("/other")).response.status, 404);
  const post = await proxied("/name-score/api/rank", { method: "POST" });
  assert.equal(post.response.status, 405);
  assert.equal(post.calls.length, 0);
});

test("forwards only Accept and Accept-Language", async () => {
  const { calls } = await proxied("/name-score/", { headers: { Cookie: "a=b", Accept: "text/html" } });
  const headers = calls[0].options.headers;
  assert.equal(headers.get("Accept"), "text/html");
  assert.equal(headers.get("Cookie"), null);
});
