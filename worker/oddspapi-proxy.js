/**
 * Los Reyes Quiniela — OddsPapi proxy (Cloudflare Worker).
 *
 * Adds CORS + hides the API key + caches responses for several hours so the free
 * tier (≈250–1000 req/month) isn't exhausted. The site calls THIS worker; it
 * injects the key and forwards to OddsPapi.
 *
 * SECURITY: the API key is read from a Worker *Secret* named ODDSPAPI_KEY
 * (Settings → Variables and Secrets → add Secret). Never hardcode it.
 *
 * USAGE:
 *   GET /?path=/sports
 *   GET /?path=/odds&sportId=10&...        (path = OddsPapi v4 endpoint)
 *   GET /?path=/sports&debug=1             (debug: shows upstream status + sample)
 * `apiKey` is added server-side; all other params are forwarded. Edge-cached ~6h.
 */
const API_BASE = "https://api.oddspapi.io/v4";
const CACHE_SECONDS = 6 * 60 * 60; // 6 hours
// A browser-like UA — some APIs 403 non-browser/unknown user agents.
const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "*",
};

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { headers: CORS });
    if (request.method !== "GET") return json({ error: "method not allowed" }, 405);

    const key = (env && env.ODDSPAPI_KEY ? String(env.ODDSPAPI_KEY) : "").trim();
    if (!key) return json({ error: "ODDSPAPI_KEY secret not set on this Worker" }, 500);

    const inUrl = new URL(request.url);
    let path = inUrl.searchParams.get("path") || "/sports";
    if (!path.startsWith("/")) path = "/" + path;
    const debug = inUrl.searchParams.get("debug");

    const upstream = new URL(API_BASE + path);
    for (const [k, v] of inUrl.searchParams) {
      if (k !== "path" && k !== "apiKey" && k !== "debug") upstream.searchParams.set(k, v);
    }
    upstream.searchParams.set("apiKey", key);

    // Edge cache keyed WITHOUT the key.
    const cacheKey = new Request(new URL(inUrl.pathname + inUrl.search, inUrl.origin).toString());
    const cache = caches.default;
    if (!debug) {
      const hit = await cache.match(cacheKey);
      if (hit) return withCors(hit);
    }

    let upstreamRes, body;
    try {
      upstreamRes = await fetch(upstream.toString(), {
        headers: {
          "Accept": "application/json",
          "User-Agent": UA,
          "Referer": "https://oddspapi.io/",
        },
      });
      body = await upstreamRes.text();
    } catch (e) {
      return json({ error: "upstream fetch failed: " + String(e) }, 502);
    }

    if (debug) {
      return json({
        upstream: upstream.toString().replace(key, "***"),
        status: upstreamRes.status,
        keyLength: key.length,
        sample: body.slice(0, 400),
      }, 200);
    }

    const res = new Response(body, {
      status: upstreamRes.status,
      headers: {
        ...CORS,
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": `public, max-age=${CACHE_SECONDS}`,
      },
    });
    if (upstreamRes.ok) await cache.put(cacheKey, res.clone());
    return res;
  },
};

function json(obj, status) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: { ...CORS, "Content-Type": "application/json; charset=utf-8" },
  });
}
function withCors(res) {
  const r = new Response(res.body, res);
  for (const [k, v] of Object.entries(CORS)) r.headers.set(k, v);
  return r;
}
