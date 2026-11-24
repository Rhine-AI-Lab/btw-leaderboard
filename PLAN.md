# Plan: deployment and submissions

Status, 24 Nov 2026: the leaderboard is built (static, `public/`). Both forms are drafted in `public/index.html`
(`#contribute`, `#evaluate`), and `api/submit.js` is a draft function that files them as issues in a private
repo; it answers 503 until `GITHUB_TOKEN` and `GITHUB_REPO` are set in Vercel.

Release plan (results post, "What next"): 24 Nov harness and prompts; 1 Dec bug-injection pipeline;
8 Dec all 42 problems. Hosted evaluations are offered until 8 Dec; after that anyone can run the benchmark.

## 1. Deploy on Vercel with the Cloudflare domain

Vercel hosts the site. Cloudflare stays the registrar and DNS host. No nameserver change is needed.

1. **Vercel project.** vercel.com → Add New → Project → import `Rhine-AI-Lab/btw-leaderboard` (install the Vercel
   GitHub app on the org, limited to this repo). Framework preset: *Other*. Build command: none. Output
   directory: `public` (also set in `vercel.json`). Deploy. You get `btw-leaderboard.vercel.app`.
2. **Branches.** `main` deploys to production. Every other branch and every PR gets its own preview URL, which
   is how a collaborator reviews a change before it goes live.
3. **Domain in Vercel.** Project → Settings → Domains → add `benchtheweights.com` and `www.benchtheweights.com`.
   Vercel then shows the exact DNS records it expects. Use those values; typically:
4. **DNS in Cloudflare.** benchtheweights.com → DNS → Records:

   | Type  | Name | Content                | Proxy status |
   |-------|------|------------------------|--------------|
   | A     | `@`  | `76.76.21.21`          | DNS only (grey cloud) |
   | CNAME | `www`| `cname.vercel-dns.com` | DNS only (grey cloud) |

   Keep both records **DNS only**. With the orange cloud on, Cloudflare proxies the traffic, Vercel cannot
   issue its certificate reliably, and you get two caches and redirect loops. Delete any parking A/AAAA
   records Cloudflare created at purchase.
5. **Check.** Vercel marks both domains "Valid configuration" within minutes and issues HTTPS certificates.
   `www` redirects to the apex (`vercel.json`).
6. **Email on the domain (free).** Cloudflare → Email → Email Routing: create `submit@benchtheweights.com` (and
   for example `eval@`) forwarding to the team's inboxes. It adds its own MX and TXT records, which do not touch
   the Vercel records. This gives a stable public address that is not a personal one.

## 2. Do we need a database?

No, not at first. We expect tens of requests a year, each one a conversation that ends in a yes or no. What we
need is a place where every request lands, has a status and has a discussion thread. A private GitHub repo
gives us that for free:

```
form on benchtheweights.com
  → Vercel function /api/submit   (validates fields, checks a Cloudflare Turnstile token against spam)
  → opens an issue in a PRIVATE repo, Rhine-AI-Lab/btw-submissions, labelled `problem` or `evaluation`
  → GitHub notifies the team; the submitter gets an automatic email with a reference number
```

The function holds one secret, a fine-grained GitHub token with Issues: write on that one repo, stored as a
Vercel environment variable. Status lives in labels (`received`, `in review`, `accepted`, `rejected`,
`scheduled`, `published`). If volume grows or we want a submitter-facing status page, we add a database then
(Vercel Postgres/Neon or Supabase), and the form keeps the same fields.

Even simpler option: a Tally or Google Form, no code at all. It works, but submissions then live outside the
lab's GitHub, and the form looks like a third-party page.

## 3. Contributing a problem (a new bug)

Your draft (private HF repo for the corrupted weights, HF path of the original, its val and test data) is the
right core. Refinements:

**What we ask for**

| Item | Form |
|---|---|
| Original network | public HF model id **and a pinned revision** (commit hash), so the reference never moves |
| Corrupted weights | a **private** HF repo, read access granted to our HF org (e.g. `rhine-ai-lab`). After acceptance we copy it into our own private org repo and ask them to delete theirs, so the only copy is ours |
| Data | HF dataset id + revision + the split names for **dev** (given to the solver) and **test** (hidden, used for scoring). If the data are not public, a private dataset repo shared the same way |
| Evaluation | a short Python entry point: load model, run on a split, return the metric. We give a template so it plugs into our task builder (`make_task.py`) |
| Reference repair | a script that repairs the corrupted weights **without training** and reaches near-original score. This is the oracle: it proves the problem is solvable, as Terminal-Bench requires of every task |
| Write-up | the corruption, why it is hard to spot, how one could diagnose it from the dev set; original / corrupted / repaired scores |
| Declarations | not published anywhere (weights, write-up, code); agree to keep it private while it is in the set; license allows us to redistribute inside the sandbox |

**What we check** (state it on the page, so people self-filter): the same acceptance tests our own problems pass
(a near-exact repair exists without retraining; least squares, low-rank fits and rescaling do not fix it; the
dev set identifies the damage but does not fit the fix), plus one or two frontier solver runs to confirm it is
neither trivial nor broken. We may edit the problem and say so.

**What contributors get**: named credit on the site; co-authorship on the next paper for accepted problems
(state a rule, e.g. Terminal-Bench offers co-authorship from 15 hours of contribution; HLE gave co-authorship
to top contributors).

**Ship a validator.** Publish a small `btw-validate` script (no answer keys needed) that checks the
submission format, runs their evaluation on original and corrupted weights and runs their reference repair.
Submitters run it before sending, which removes most of the back-and-forth.

## 4. Getting a model evaluated

Until 8 December the problems are private, so **only we run them** (as ARC-AGI's Verified testing and Scale's
private HLE set do). After 8 December the problems and pipeline are public: self-run results can come in with
their trajectories (as SWE-bench does), and the leaderboard should mark rows as *run by us* or *self-run*.
Results we run are shared with the owner and published only if they agree (form: publish / later / private).

**What we ask for**

- **Access**, one of:
  - an API endpoint (OpenAI- or Anthropic-compatible) plus a key with enough quota, ideally under
    **zero data retention / no training on our traffic**. The agent sends weight statistics and code to the
    model provider, so the problems leak a little through every API run. ARC Prize calls its set
    "semi-private" for exactly this reason and asks for no-retention agreements;
  - or open weights (HF id + revision + a serving recipe, e.g. vLLM settings), which we serve on our GPUs.
- **Harness**: by default the vendor's own coding agent if it has one (Claude Code, Codex, Antigravity), else
  a neutral one (Codex through OpenRouter, as in our harness ablation). They may suggest settings (reasoning
  effort, context limits); we use the highest effort available, as for every model on the board.
- **Compute**: who pays. A full v1 evaluation is 2 seeds × 42 problems. We should state a cost estimate per
  evaluation and ask for credits; ARC Prize caps each run's cost.
- **Publication**: whether the result can be published, and when. For pre-release models we offer an embargo
  (run now, publish at release), the way LMArena tests anonymous pre-release models.

**What we return**: the leaderboard row (mean recovery, solved share, per-domain means, trial medians) and a
short private report. **Not** per-problem trajectories, which would reveal the problems.

**Policy to publish on the page** (short, modeled on ARC Prize's testing policy): every model runs under the
same protocol; we run it, not the owner; results are published whatever they are, unless the owner withdraws
before the run starts; no sponsor or model owner gets access to the problems.

**Open questions**: the public harness URL and our Hugging Face org name (the page uses placeholders
`https://github.com/Rhine-AI-Lab` and `rhine-ai-lab`); whether a later private set will exist to keep hosted
evaluations meaningful once the 42 problems are public.

## 5. Next steps

1. Connect Vercel and the domain (section 1).
2. Agree on the fields above; then I build `/contribute` and `/evaluate` pages, `/api/submit` and the private
   issues repo.
3. Write the problem template, `btw-validate`, and the testing policy text.
