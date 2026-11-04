// Leaderboard API — Vercel serverless function.
// Storage: a standard Redis database (Redis Cloud via the Vercel Marketplace),
// reached over the normal Redis protocol with the `redis` client.
//
//   GET    /api/scores          -> { rows: [...] } best 20, score desc then time asc
//   POST   /api/scores          -> saves a candidate's attempt (best one is kept)
//   DELETE /api/scores?key=...  -> clears the board (only if ADMIN_KEY is set)

import { createClient } from "redis";

const REDIS_URL = process.env.REDIS_URL || process.env.KV_URL;
const KEY = "quiz:scores";
const TOTAL = 15;

// One client per warm function instance, reconnected only when it has dropped.
let client = null;
let connecting = null;

async function db() {
  if (!REDIS_URL) return null;
  if (!client) {
    client = createClient({ url: REDIS_URL });
    client.on("error", () => {});   // never let a socket error crash the function
  }
  if (!client.isOpen) {
    if (!connecting) connecting = client.connect().finally(() => { connecting = null; });
    await connecting;
  }
  return client;
}

const int = (v) => (Number.isInteger(v) ? v : NaN);
function clean(body) {
  if (!body || typeof body !== "object") return null;
  const id = String(body.id || "");
  const name = String(body.name || "").replace(/[\u0000-\u001f<>]/g, "").replace(/\s+/g, " ").trim();
  const mat = String(body.mat || "").replace(/\s+/g, "").trim();
  const parts = [int(body.eur), int(body.usd), int(body.gbp)];
  const score = int(body.score), ms = int(body.ms);
  if (!/^[a-z0-9]{8,40}$/i.test(id)) return null;
  if (name.length < 2 || name.length > 40) return null;
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{1,19}$/.test(mat)) return null;
  if (parts.some((p) => !(p >= 0 && p <= 5))) return null;
  if (!(score >= 0 && score <= TOTAL) || parts[0] + parts[1] + parts[2] !== score) return null;
  if (!(ms >= 5000 && ms <= 2 * 3600 * 1000)) return null;   // 5 s .. 2 h
  return { id, name, mat, score, total: TOTAL, ms, eur: parts[0], usd: parts[1], gbp: parts[2],
           at: new Date().toISOString() };
}

export default async function handler(req, res) {
  res.setHeader("Cache-Control", "no-store");
  if (!REDIS_URL) return res.status(503).json({ error: "storage_not_configured" });

  try {
    const r = await db();

    if (req.method === "GET") {
      const all = await r.hGetAll(KEY);           // { id: json, ... }
      const rows = [];
      for (const raw of Object.values(all || {})) {
        try { rows.push(JSON.parse(raw)); } catch (_) {}
      }
      rows.sort((a, b) => b.score - a.score || a.ms - b.ms);
      return res.status(200).json({
        rows: rows.slice(0, 20).map(({ id, name, mat, score, total, ms, eur, usd, gbp }) =>
          ({ id, name, mat, score, total, ms, eur, usd, gbp })),
        count: rows.length,
      });
    }

    if (req.method === "POST") {
      const entry = clean(typeof req.body === "string" ? JSON.parse(req.body || "{}") : req.body);
      if (!entry) return res.status(400).json({ error: "invalid" });
      const prev = await r.hGet(KEY, entry.id);
      if (prev) {
        const p = JSON.parse(prev);
        const better = entry.score > p.score || (entry.score === p.score && entry.ms < p.ms);
        if (!better) {                       // keep the best attempt, refresh the identity only
          if (p.name !== entry.name || p.mat !== entry.mat) {
            p.name = entry.name; p.mat = entry.mat;
            await r.hSet(KEY, entry.id, JSON.stringify(p));
          }
          return res.status(200).json({ saved: false, best: p });
        }
      }
      await r.hSet(KEY, entry.id, JSON.stringify(entry));
      return res.status(200).json({ saved: true, best: entry });
    }

    if (req.method === "DELETE") {
      const admin = process.env.ADMIN_KEY;
      if (!admin || req.query.key !== admin) return res.status(403).json({ error: "forbidden" });
      await r.del(KEY);
      return res.status(200).json({ cleared: true });
    }

    res.setHeader("Allow", "GET, POST, DELETE");
    return res.status(405).json({ error: "method_not_allowed" });
  } catch (e) {
    return res.status(500).json({ error: "storage_error", detail: String(e && e.message || e).slice(0, 120) });
  }
}
