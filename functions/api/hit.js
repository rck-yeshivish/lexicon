// The page-view counter: one number for the whole site, kept in the D1
// database whatsinaword-hits (binding HITS, see wrangler.jsonc).
//
// Every page posts here once as it loads, which adds one; the home page's
// footer shows what comes back. Nothing about the visitor is read or kept,
// only the running total and the date it started. A crawler that does not
// run JavaScript never calls this, so it is not counted.

const NO_STORE = { "Cache-Control": "no-store" };

export async function onRequestPost({ env }) {
  const row = await env.HITS
    .prepare("UPDATE hits SET n = n + 1 WHERE id = 1 RETURNING n, since")
    .first();
  return Response.json(row ?? {}, { headers: NO_STORE });
}

export async function onRequestGet({ env }) {
  const row = await env.HITS.prepare("SELECT n, since FROM hits WHERE id = 1").first();
  return Response.json(row ?? {}, { headers: NO_STORE });
}
