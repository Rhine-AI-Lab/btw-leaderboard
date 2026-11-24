// POST /api/submit — draft. Turns a form submission into an issue in a private GitHub repo.
// Env (Vercel project settings): GITHUB_TOKEN (fine-grained, Issues: write on GITHUB_REPO only),
// GITHUB_REPO (e.g. Rhine-AI-Lab/btw-submissions), optional TURNSTILE_SECRET.
// Not wired up yet: without GITHUB_TOKEN it answers 503 and the page shows "Not sent".

const KINDS = {
  problem: {
    label: "problem",
    title: (f) => `Problem: ${f.original_model} (${f.domain}) from ${f.name}`,
    required: ["name", "email", "original_model", "original_revision", "domain", "dataset", "dev_split", "test_split",
      "metric", "score_original", "score_corrupted", "score_repaired", "corrupted_repo", "repair_script", "description",
      "diagnosis", "agree_private", "agree_license", "agree_edit"],
  },
  evaluation: {
    label: "evaluation",
    title: (f) => `Evaluation: ${f.model_name} (${f.organization})`,
    required: ["name", "email", "organization", "model_name", "status", "access", "publish", "agree_protocol"],
  },
};
const MAX_FIELD = 20000;

export default async function handler(req, res) {
  if (req.method !== "POST") return res.status(405).json({ error: "use POST" });
  const body = typeof req.body === "string" ? safeJson(req.body) : req.body;
  if (!body || typeof body !== "object") return res.status(400).json({ error: "invalid request" });
  if (body.website) return res.status(200).json({ ref: "ok" }); // honeypot: pretend success for bots

  const kind = KINDS[body.kind];
  const f = body.fields || {};
  if (!kind) return res.status(400).json({ error: "unknown form" });
  const missing = kind.required.filter((k) => !f[k]);
  if (missing.length) return res.status(400).json({ error: "missing " + missing.join(", ") });
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(String(f.email))) return res.status(400).json({ error: "invalid email" });
  for (const [k, v] of Object.entries(f)) {
    if (String(v).length > MAX_FIELD) return res.status(400).json({ error: `${k} is too long` });
  }

  if (process.env.TURNSTILE_SECRET) {
    const ok = await verifyTurnstile(body.turnstile, req.headers["x-forwarded-for"]);
    if (!ok) return res.status(400).json({ error: "spam check failed, reload the page" });
  }
  const token = process.env.GITHUB_TOKEN, repo = process.env.GITHUB_REPO;
  if (!token || !repo) return res.status(503).json({ error: "submissions are not open yet" });

  const md = Object.entries(f)
    .map(([k, v]) => `**${k.replace(/_/g, " ")}**\n\n${v === true ? "yes" : "```\n" + String(v).replace(/```/g, "ˋˋˋ") + "\n```"}`)
    .join("\n\n");
  const r = await fetch(`https://api.github.com/repos/${repo}/issues`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, Accept: "application/vnd.github+json", "User-Agent": "btw-site" },
    body: JSON.stringify({ title: kind.title(f).slice(0, 200), body: md, labels: [kind.label, "received"] }),
  });
  if (!r.ok) return res.status(502).json({ error: "could not file the request" });
  const issue = await r.json();
  return res.status(200).json({ ref: `BTW-${issue.number}` });
}

function safeJson(s) { try { return JSON.parse(s); } catch { return null; } }

async function verifyTurnstile(token, ip) {
  if (!token) return false;
  const form = new URLSearchParams({ secret: process.env.TURNSTILE_SECRET, response: token });
  if (ip) form.set("remoteip", String(ip).split(",")[0]);
  const r = await fetch("https://challenges.cloudflare.com/turnstile/v0/siteverify", { method: "POST", body: form });
  return r.ok && (await r.json()).success === true;
}
