/**
 * Los Reyes Quiniela — OddsPapi proxy (Cloudflare Worker).
 *
 * Adds CORS + hides the API key + caches responses for several hours so the free
 * tier (≈250–1000 req/month) isn't exhausted. The browser/site calls THIS worker;
 * the worker injects the key and forwards to OddsPapi.
 *
 * SECURITY: the API key is read from an environment variable, never hardcoded.
 *   In the Cloudflare dashboard: your Worker → Settings → Variables and Secrets →
 *   add a *Secret* named  ODDSPAPI_KEY  with your key as the value → Deploy.
 *
 * USAGE (the site will call it like this):
 *   GET  https://<worker>.workers.dev/?path=/sports
 *   GET  https://<worker>.workers.dev/?path=/odds&sport=<key>&markets=h2h,totals&...
 * The `path` param selects the OddsPapi v4 endpoint; all other query params are
 * forwarded as-is; `apiKey` is added server-side. Responses are edge-cached.
 *
 * Deploy: dash.cloudflare.com → Workers & Pages → Create Worker → paste this →
 * add the ODDSPAPI_KEY secret → Deploy. Copy the URL and send it to me.
 */
const API_BASE = "https://api.oddspapi.io/v4";
const CACHE_SECONDS = 6 * 60 * 60; // 6 hours

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "*",
};

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") return new Response(null, { headers: CORS });
    if (request.method !== "GET") {
      return json({ error: "method not allowed" }, 405);
    }
    if (!env || !env.ODDSPAPI_KEY) {
      return json({ error: "ODDSPAPI_KEY secret not set on this Worker" }, 500);
    }

    const inUrl = new URL(request.url);
    // Endpoint path (default to /sports so a bare call verifies the key works).
    let path = inUrl.searchParams.get("path") || "/sports";
    if (!path.startsWith("/")) path = "/" + path;

    // Build the upstream URL: forward all params except `path`, add apiKey.
    const upstream = new URL(API_BASE + path);
    for (const [k, v] of inUrl.searchParams) {
      if (k !== "path" && k !== "apiKey") upstream.searchParams.set(k, v);
    }
    upstream.searchParams.set("apiKey", env.ODDSPAPI_KEY);

    // Edge cache keyed WITHOUT the API key (so the key never lands in cache keys).
    const cacheKey = new Request(new URL(inUrl.pathname + inUrl.search, inUrl.origin).toString());
    const cache = caches.default;
    let hit = await cache.match(cacheKey);
    if (hit) return withCors(hit);

    let upstreamRes;
    try {
      upstreamRes = await fetch(upstream.toString(), {
        headers: { Accept: "application/json", "User-Agent": "los-reyes-quiniela/1.0" },
        cf: { cacheTtl: CACHE_SECONDS, cacheEverything: true },
      });
    } catch (e) {
      return json({ error: "upstream fetch failed: " + String(e) }, 502);
    }

    const body = await upstreamRes.text();
    const res = new Response(body, {
      status: upstreamRes.status,
      headers: {
        ...CORS,
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": `public, max-age=${CACHE_SECONDS}`,
      },
    });
    // Only cache successful responses.
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
