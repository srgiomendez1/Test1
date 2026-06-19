/**
 * Los Reyes Quiniela — live-scores CORS proxy (Cloudflare Worker).
 *
 * worldcup26.ir doesn't send CORS headers, so browsers can't fetch it directly.
 * This tiny Worker fetches it server-side and re-serves the JSON with
 * `Access-Control-Allow-Origin: *`, so the site can poll it every ~30s.
 *
 * Free tier: 100,000 requests/day — far more than this needs.
 *
 * Deploy (≈2 min, no CLI needed):
 *   1. https://dash.cloudflare.com → Workers & Pages → Create → Worker.
 *   2. Name it e.g. "quiniela-live", click Deploy, then "Edit code".
 *   3. Replace the sample with THIS file's contents → Deploy.
 *   4. Copy the URL (https://quiniela-live.<your-subdomain>.workers.dev) and
 *      put it in data/live-source.json  ->  { "proxy": "<that URL>" }
 *      (edit it on GitHub, or send it to me and I'll commit it).
 */
const UPSTREAM = "https://worldcup26.ir/get/games";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "*",
};

export default {
  async fetch(request) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: CORS });
    }
    try {
      const upstream = await fetch(UPSTREAM, {
        headers: { "User-Agent": "los-reyes-quiniela/1.0", "Accept": "application/json" },
        // Cache at Cloudflare's edge for 20s so we never hammer the source.
        cf: { cacheTtl: 20, cacheEverything: true },
      });
      const body = await upstream.text();
      return new Response(body, {
        status: upstream.status,
        headers: {
          ...CORS,
          "Content-Type": "application/json; charset=utf-8",
          "Cache-Control": "no-store",
        },
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: String(err) }), {
        status: 502,
        headers: { ...CORS, "Content-Type": "application/json" },
      });
    }
  },
};
