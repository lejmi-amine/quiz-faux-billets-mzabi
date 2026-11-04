// Leaderboard API — Vercel serverless function, no dependencies.
// Storage: Upstash Redis (Vercel Marketplace), reached over its REST API.
//
//   GET    /api/scores          -> { rows: [...] } best 20, score desc then time asc
//   POST   /api/scores          -> saves a candidate's attempt (best one is kept)
//   DELETE /api/scores?key=...  -> clears the board (only if ADMIN_KEY is set)

const URL = process.env.KV_REST_API_URL || process.env.UPSTASH_REDIS_REST_URL;
const TOKEN = process.env.KV_REST_API_TOKEN || process.env.UPSTASH_REDIS_REST_TOKEN;
const KEY = "quiz:scores";
const TOTAL = 15;

async function redis(cmd) {
  const r = await fetch(URL, {
    method: "POST",
    headers: { Authorization: `Bearer ${TOKEN}`, "Content-Type": "application/json" },
    body: JSON.stringify(cmd),
  });
  const j = await r.json();
  if (!r.ok || j.error) throw new Error(j.error || `HTTP ${r.status}`);
  return j.result;
}

const int = (v) => (Number.isInteger(v) ? v : NaN);
function clean(body) {
  if (!body || typeof body !== "object") return null;
  const id = String(body.id || "");
  const name = String(body.name || "").replace(/[\u0000-\u001f<>]/g, "").replace(/\s+/g, " ").trim();
  const parts = [int(body.eur), int(body.usd), int(body.gbp)];
  const score = int(body.score), ms = int(body.ms);
  if (!/^[a-z0-9]{8,40}$/i.test(id)) return null;
  if (name.length < 2 || name.length > 40) return null;
  if (parts.some((p) => !(p >= 0 && p <= 5))) return null;
  if (!(score >= 0 && score <= TOTAL) || parts[0] + parts[1] + parts[2] !== score) return null;
  if (!(ms >= 5000 && ms <= 2 * 3600 * 1000)) return null;   // 5 s .. 2 h
  return { id, name, score, total: TOTAL, ms, eur: parts[0], usd: parts[1], gbp: parts[2],
           at: new Date().toISOString() };
}

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (!URL || !TOKEN) return res.status(503).json({ error: "storage_not_configured" });

  try {
    if (req.method === "GET") {
      const flat = (await redis(["HGETALL", KEY])) || [];
      const rows = [];
      for (let i = 0; i + 1 < flat.length; i += 2) {
        try { const d = JSON.parse(flat[i + 1]); rows.push(d); } catch (_) {}
      }
      rows.sort((a, b) => b.score - a.score || a.ms - b.ms);
      return res.status(200).json({
        rows: rows.slice(0, 20).map(({ id, name, score, total, ms, eur, usd, gbp }) =>
          ({ id, name, score, total, ms, eur, usd, gbp })),
        count: rows.length,
      });
    }

    if (req.method === "POST") {
      const entry = clean(typeof req.body === "string" ? JSON.parse(req.body || "{}") : req.body);
      if (!entry) return res.status(400).json({ error: "invalid" });
      const prev = await redis(["HGET", KEY, entry.id]);
      if (prev) {
        const p = JSON.parse(prev);
        const better = entry.score > p.score || (entry.score === p.score && entry.ms < p.ms);
        if (!better) {                       // keep the best attempt, refresh the name only
          if (p.name !== entry.name) { p.name = entry.name; await redis(["HSET", KEY, entry.id, JSON.stringify(p)]); }
          return res.status(200).json({ saved: false, best: p });
        }
      }
      await redis(["HSET", KEY, entry.id, JSON.stringify(entry)]);
      return res.status(200).json({ saved: true, best: entry });
    }

    if (req.method === "DELETE") {
      const admin = process.env.ADMIN_KEY;
      if (!admin || req.query.key !== admin) return res.status(403).json({ error: "forbidden" });
      await redis(["DEL", KEY]);
      return res.status(200).json({ cleared: true });
    }

    res.setHeader("Allow", "GET, POST, DELETE");
    return res.status(405).json({ error: "method_not_allowed" });
  } catch (e) {
    return res.status(500).json({ error: "storage_error" });
  }
}

