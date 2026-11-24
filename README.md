# Bench the Weights: website

Leaderboard and submission site for [Bench the Weights](https://benchtheweights.com), the held-out
weight-repair benchmark from Rhine AI Lab. Static site, deployed on Vercel from `main`.

```
public/index.html              the whole site: leaderboard, #contribute and #evaluate forms (no build step)
public/logo.png                the mascot from the blog post (logo and favicon)
api/submit.js                  draft function that files form submissions as private GitHub issues
public/data/leaderboard.json   the results it shows
scripts/export_from_draft.py   regenerates leaderboard.json
vercel.json                    output dir, clean URLs, www -> apex redirect
PLAN.md                        deployment steps and the plan for the two submission flows
```

## Update the results

The numbers come from the curated results object in the results-post draft (built from
`weightgym/heldout/scores`, protocol v1, complete seeds only). To refresh:

1. Save the current draft HTML locally (the Artifact read of the draft gives you the file), outside this repo
   or as `*.draft.html` (ignored).
2. `python3 scripts/export_from_draft.py path/to/draft.html`
3. Check the diff of `public/data/leaderboard.json`, commit, push. Vercel deploys on push.

The data file holds only aggregate scores, per-seed means, per-domain means and trial medians. It never holds
problem identities, network names or answer keys: the held-out set stays private.

## Run locally

Any static server, from the repo root:

```bash
python3 -m http.server -d public 8000   # then open http://localhost:8000
```

Opening `index.html` as a file will not work: the page fetches `data/leaderboard.json`.
