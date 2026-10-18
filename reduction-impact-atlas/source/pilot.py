"""Build isolated, AI-proposed bridge scenarios without changing the main ranking."""

import argparse
import html
import json
from pathlib import Path

from estimate import build_estimate_report
from ranker import sha256_file


ROOT = Path(__file__).parent


def build_pilot(output=ROOT / "dist"):
    data = ROOT / "data"
    graph_path = data / "reduction_graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    board = json.loads((data / "questions.json").read_text(encoding="utf-8"))
    mappings = json.loads((data / "mappings.json").read_text(encoding="utf-8"))
    baseline_bridges = json.loads((data / "bridges.json").read_text(encoding="utf-8"))
    pilots = json.loads((data / "pilot_bridges.json").read_text(encoding="utf-8"))
    graph_hash = sha256_file(graph_path)
    registry_hash = board["registry_sha256"]
    if pilots["graph_sha256"] != graph_hash or pilots["registry_sha256"] != registry_hash:
        raise ValueError("pilot bridge snapshot hash does not match frozen inputs")
    baseline = build_estimate_report(graph, graph_hash, board["questions"], mappings,
                                     baseline_bridges, registry_hash)
    baseline_rows = {row["id"]: row for row in baseline["questions"]}
    results = []
    seen = set()
    for case in pilots["cases"]:
        qid = case["id"]
        if qid in seen or qid not in baseline_rows or case["bridge"]["question_ids"] != [qid]:
            raise ValueError("pilot case needs one unique, matching question ID")
        seen.add(qid)
        if case.get("review_state") != "AI-proposed semantic bridge; independent review pending":
            raise ValueError("pilot review state must remain explicit")
        bridge = case["bridge"]
        projection = {qid: {bridge["side"]: bridge["problem_family"]}}
        fixed_baseline = build_estimate_report(graph, graph_hash, board["questions"], mappings,
                                               baseline_bridges, registry_hash,
                                               family_overrides=projection)
        fixed_rows = {row["id"]: row for row in fixed_baseline["questions"]}
        scenario_bridges = dict(baseline_bridges)
        scenario_bridges["entries"] = baseline_bridges["entries"] + [bridge]
        scenario = build_estimate_report(graph, graph_hash, board["questions"], mappings,
                                         scenario_bridges, registry_hash,
                                         family_overrides=projection)
        changed = {row["id"] for row in scenario["questions"]
                   if (row["N"], row["B"], row["V"]) !=
                   (fixed_rows[row["id"]]["N"], fixed_rows[row["id"]]["B"], fixed_rows[row["id"]]["V"])}
        pilot_row = next(row for row in scenario["questions"] if row["id"] == qid)
        base_row = baseline_rows[qid]
        fixed_row = fixed_rows[qid]
        results.append({"id": qid, "source": pilot_row["source"], "target": pilot_row["target"],
                        "board_importance": pilot_row.get("board_importance", ""),
                        "literature_checked": pilot_row.get("literature_checked"),
                        "review_state": case["review_state"], "bridge": bridge,
                        "fixed_projection": projection,
                        "background_url": case["background_url"],
                        "algorithmic_consequence": case["algorithmic_consequence"],
                        "limitation": case["limitation"],
                        "baseline": {key: base_row[key] for key in ("N", "B", "V", "D_half", "direct_count", "transitive_count", "rank")},
                        "fixed_projection_baseline": {key: fixed_row[key] for key in ("N", "B", "V", "D_half", "direct_count", "transitive_count", "rank")},
                        "scenario": {key: pilot_row[key] for key in ("N", "B", "V", "D_half", "direct_count", "transitive_count", "hop_histogram", "variant_gain_breakdown", "rank",
                                                                      "new_problem_pairs", "witnesses")},
                        "affected_question_ids": sorted(changed)})
    report = {"graph_sha256": graph_hash, "registry_sha256": registry_hash,
              "baseline_bridges_sha256": sha256_file(data / "bridges.json"),
              "pilot_bridges_sha256": sha256_file(data / "pilot_bridges.json"),
              "interpretation": "Each case compares graphs with and without its own AI-proposed semantic bridge under a fixed problem-family projection. Candidate question rules remain hypothetical. Neither scenario changes the official ranking.",
              "cases": results}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "pilot.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "pilot.html").write_text(render_pilot_page(report), encoding="utf-8")
    (output / "pilot_bridges.json").write_bytes((data / "pilot_bridges.json").read_bytes())
    return report


def render_pilot_section(report):
    escape = lambda value: html.escape(str(value), quote=True)
    cards = []
    for case in report["cases"]:
        before, after = case["fixed_projection_baseline"], case["scenario"]
        example_pairs = "".join(f'<li>{escape(pair["source"])} → {escape(pair["target"])}</li>'
                                for pair in after["new_problem_pairs"][:8])
        bridge = case["bridge"]
        cards.append(f'''<article class="summary ai-pilot" style="margin-top:20px">
<p class="eyebrow">{escape(case["id"])} · AI-proposed scenario</p>
<h2>{escape(case["source"])} → {escape(case["target"])}</h2>
<p><strong>Official baseline under the same problem-family projection:</strong> N {before["N"]} · B {before["B"]:g} · V {before["V"]}.
<strong>With this bridge only:</strong> N {after["N"]} · B {after["B"]:g} · V {after["V"]}. The projection stays fixed in this comparison; it does not add a graph edge.</p>
<p>Of the {after["N"]} new problem relations, {after["direct_count"]} is direct and {after["transitive_count"]} follow through older edges. Exploratory D½ = {after["D_half"]:.3f}, with every extra witness-chain edge weighted by 0.5. The official ranking does not use D½.</p>
<p>The {after["V"]} concrete variant relations split into {after["variant_gain_breakdown"]["direct"]} candidate pair, {after["variant_gain_breakdown"]["upstream"]} old-upstream relations, {after["variant_gain_breakdown"]["downstream"]} old-downstream relations, and {after["variant_gain_breakdown"]["both_sides"]} relations spanning both sides.</p>
<p>The new bridge also changes the computed scores of {len(case["affected_question_ids"]) - 1} other board questions, because they share the same baseline graph. Rankings from the two baselines are not directly comparable.</p>
<p><strong>Proposed baseline bridge:</strong> {escape(bridge["label"])}
{escape("→" if bridge["direction"] == "board_to_graph" else "←")}
graph node {bridge["graph_node"]}. {escape(bridge["evidence"])}</p>
<p><strong>Algorithmic consequence if the question rule is proved:</strong> {escape(case["algorithmic_consequence"])}</p>
<p><strong>Board-stated importance (not independently checked):</strong> {escape(case["board_importance"])}</p>
<p><strong>Why the count needs caution:</strong> {escape(case["limitation"])}</p>
<details class="method-note"><summary>First {min(8, len(after["new_problem_pairs"]))} of {len(after["new_problem_pairs"])} new problem relations</summary>
<ol>{example_pairs}</ol></details>
<p><a href="{escape(bridge["source_url"])}">Graph model evidence ↗</a> ·
<a href="{escape(case["background_url"])}">Algorithm background ↗</a></p></article>''')
    return f'''<section id="pilots" aria-labelledby="pilots-heading"><p class="eyebrow">Worked examples</p>
<h2 id="pilots-heading">{len(report["cases"])} AI bridge examples</h2>
<p>These are five selected, isolated semantic bridge proposals across different problem families. Every candidate rule remains hypothetical.</p>
<div class="summary" style="margin-top:20px"><p><strong>These {len(report["cases"])} bridge scenarios are isolated experiments, not the official ranking.</strong>
The proposed bridges await independent review. A larger or smaller marginal topology count is not a measure of research value. Compare each case's conditional consequence with its raw count.</p>
<p>Graph SHA-256: <code>{escape(report["graph_sha256"])}</code>. <a href="pilot_bridges.json">Bridge proposals</a> · <a href="pilot.json">All new relations and witnesses</a>.</p></div>
{''.join(cards)}</section>'''


def render_pilot_page(report):
    from ranker import STYLE_CSS
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AI bridge examples · Reduction Impact Atlas</title><style>{STYLE_CSS}</style></head>
<body><header class="site-header"><div class="topbar">
<a class="brand" href="index.html"><img class="brand-mark" src="lab-mark.svg" alt="Problem-Reductions lab mark"><span>Reduction Impact Atlas</span></a>
<nav aria-label="Primary"><a href="index.html">Full ranking</a><a href="pilot.html" aria-current="page">AI examples</a><a href="calculation.pdf">Calculation PDF</a></nav></div></header>
<main>{render_pilot_section(report)}<p><a href="index.html">← Return to all 76 questions</a> · <a href="calculation.pdf">Calculation PDF</a></p></main></body></html>'''


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    result = build_pilot(args.output)
    print(f"Built {len(result['cases'])} independent pilot scenarios; output: {args.output}")
