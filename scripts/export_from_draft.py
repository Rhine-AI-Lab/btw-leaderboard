#!/usr/bin/env python3
"""Build public/data/leaderboard.json from the blog draft's embedded results.

    python3 scripts/export_from_draft.py path/to/draft.html

The draft (the Bench the Weights results post) embeds one curated results object, `var DATA = {...}`, built from
weightgym's heldout/scores (protocol v1, complete seeds only), plus model colours and release dates. This script
copies the parts the leaderboard needs and aggregates per-problem recovery by domain. It never reads answer keys
or problem identities: problems stay anonymous, only their domain is kept.
"""
import json, re, statistics, sys, datetime

SOLVED = 0.75
PROVIDER = [("gpt-", "OpenAI", "openai"), ("claude-", "Anthropic", "anthropic"), ("gemini-", "Google", "gemini"),
            ("qwen", "Alibaba", "qwen"), ("glm", "Zhipu AI", "zhipu"), ("deepseek", "DeepSeek", "deepseek")]


def grab(src, name):
    m = re.search(r"var " + name + r" = (\{.*?\});\n", src, re.S)
    if not m:
        sys.exit(f"{name} not found in draft")
    return m.group(1)


def css_vars(block):
    return dict(re.findall(r"(--m-[a-z0-9]+):\s*(#[0-9a-fA-F]{3,8})", block))


def main(path):
    src = open(path, encoding="utf-8").read()
    data = json.loads(grab(src, "DATA"))
    color = json.loads(grab(src, "COLOR"))
    rel = json.loads(re.sub(r"\s+", " ", grab(src, "REL")))
    vendor = json.loads(grab(src, "VENDOR"))
    root = re.search(r":root \{(.*?)\n\}", src, re.S).group(1)
    dark = re.search(r':root\[data-theme="dark"\] \{(.*?)\}', src, re.S).group(1)
    light_c, dark_c = css_vars(root), css_vars(dark)
    doms = data["domains"]

    models = []
    for m in data["models"]:
        prov = next(p for p in PROVIDER if m["id"].startswith(p[0]))
        by_dom = {d: [] for d in doms}
        for s in m["scores"]:
            if s[1] is not None:
                by_dom[doms[s[0]]].append(s[1])  # unclipped, as in the seed means
        nprob = sum(1 for s in m["scores"] if s[1] is not None)
        t = m.get("trace") or {}
        models.append({
            "id": m["id"], "name": m["name"].replace(" preview", ""), "preview": "preview" in m["name"].lower() or "preview" in m["id"],
            "provider": prov[1], "logo": prov[2], "harness": m["harness"], "effort": "highest available",
            "released": rel.get(m["id"]),
            "recovery_per_seed": m["seeds"], "solved_per_seed": m["solved"], "problems": m["np"], "problems_run": nprob,
            "per_problem": [None if s[1] is None else round(s[1], 4) for s in m["scores"]],
            "domains": {d: (round(statistics.mean(v), 4) if v else None) for d, v in by_dom.items()},
            "domain_counts": {d: len(v) for d, v in by_dom.items()},
            "median_trial": {k: t.get(k) for k in ("time", "passes", "calls", "tok")} if t else None,
            "color": {"light": light_c[color[m["id"]]], "dark": dark_c[color[m["id"]]]},
        })
    out = {
        "benchmark": "Bench the Weights", "protocol": "v1", "updated": datetime.date.today().isoformat(),
        "problems": 42, "budget": {"minutes": 25, "forward_passes": 50}, "solved_threshold": SOLVED,
        "domains": doms, "problem_domains": [s[0] for s in data["models"][0]["scores"]], "domain_sizes": {d: len(s) for d, s in data["sizes"]},
        "logos": vendor, "models": models,
    }
    with open("public/data/leaderboard.json", "w") as f:
        json.dump(out, f, indent=1)
    print(f"{len(models)} models -> public/data/leaderboard.json")


if __name__ == "__main__":
    main(sys.argv[1])
