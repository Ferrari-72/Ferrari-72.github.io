"""Independent, reproducible topology ranking for question-board records.

Only reviewed mappings to exact graph variants receive a conditional score.
All other records remain visible with a reason.
"""
from collections import Counter, deque
import hashlib
import html
import json
import re
from pathlib import Path


GRAPH_URL = "https://codingthrust.github.io/problem-reductions/reductions/reduction_graph.json"
BOARD_URL = "https://github.com/GiggleLiu/autoresearch-gadgets/blob/main/registry/"


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _name_key(value):
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _validate_graph(graph):
    nodes, edges = graph.get("nodes"), graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list) or not nodes:
        raise ValueError("graph needs nodes and edges lists")
    for index, node in enumerate(nodes):
        if not isinstance(node, dict) or not isinstance(node.get("name"), str) or not node["name"]:
            raise ValueError(f"invalid graph node {index}")
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            raise ValueError(f"invalid graph edge {index}")
        for key in ("source", "target"):
            value = edge.get(key)
            if type(value) is not int or not 0 <= value < len(nodes):
                raise ValueError(f"invalid graph edge {index} {key}")
    return nodes, edges


def _paths(nodes, edges):
    """Shortest directed paths using only single-call witness-preserving rules.

    The upstream export also contains Turing reductions. A board question asks
    for one polynomial instance map and one answer-recovery map, so those edges
    cannot be composed into its claimed one-call topology consequences.
    Edge indices remain positions in the unfiltered frozen export.
    """
    adjacency = [[] for _ in nodes]
    for index, edge in enumerate(edges):
        if edge.get("turing", False) or edge.get("witness", True) is False:
            continue
        adjacency[edge["source"]].append((edge["target"], index))
    paths = []
    for source in range(len(nodes)):
        reached = {source: ()}
        queue = deque([source])
        while queue:
            current = queue.popleft()
            for target, edge_index in adjacency[current]:
                if target not in reached:
                    reached[target] = reached[current] + (edge_index,)
                    queue.append(target)
        paths.append(reached)
    return paths


def _score(source, target, nodes, paths, base_problem_pairs, problem_sizes):
    problems = [node.get("problem_key", node["name"]) for node in nodes]
    ancestors = [u for u, reached in enumerate(paths) if source in reached]
    descendants = list(paths[target])
    new_pairs = [(u, v) for u in ancestors for v in descendants
                 if u != v and v not in paths[u]]
    new_problem_pairs = {(problems[u], problems[v]) for u, v in new_pairs
                         if problems[u] != problems[v]} - base_problem_pairs
    increments = Counter((problems[u], problems[v]) for u, v in new_pairs
                         if problems[u] != problems[v]
                         and (problems[u], problems[v]) in base_problem_pairs)
    B = sum(count / (problem_sizes[p] * problem_sizes[q])
            for (p, q), count in increments.items())
    witnesses = [{"source_node": u, "target_node": v,
                  "path": [f"edge:{index}" for index in paths[u][source]]
                          + ["candidate:PLACEHOLDER"]
                          + [f"edge:{index}" for index in paths[target][v]]}
                 for u, v in sorted(new_pairs)]
    return len(new_problem_pairs), round(B, 12), sorted(new_problem_pairs), witnesses


def build_report(graph, graph_hash, questions, mappings):
    nodes, edges = _validate_graph(graph)
    if mappings.get("graph_sha256") != graph_hash:
        raise ValueError("mapping graph hash does not match the frozen snapshot")
    entries = mappings.get("entries")
    if not isinstance(entries, dict):
        raise ValueError("mapping entries must be an object")
    ids = [q.get("id") for q in questions]
    if any(not isinstance(qid, str) or not qid for qid in ids) or len(set(ids)) != len(ids):
        raise ValueError("question IDs must be unique nonempty strings")
    if set(entries) - set(ids):
        raise ValueError("mapping references unknown question ID")
    paths = _paths(nodes, edges)
    problems = [node["name"] for node in nodes]
    problem_sizes = Counter(problems)
    base_problem_pairs = {(problems[u], problems[v]) for u, reached in enumerate(paths)
                          for v in reached if problems[u] != problems[v]}
    direct = {(edge["source"], edge["target"]) for edge in edges
              if not edge.get("turing", False) and edge.get("witness", True) is not False}
    names = {}
    for index, node in enumerate(nodes):
        names.setdefault(_name_key(node["name"]), []).append(index)
    rows = []
    for q in questions:
        qid = q["id"]
        source, target = q["source"], q["target"]
        if not isinstance(source, str) or not isinstance(target, str):
            raise ValueError(f"{qid}: source and target must be strings")
        solutions = q.get("solutions", [])
        statuses = set(q.get("solution_statuses", [s["status"] for s in solutions]))
        status = q.get("status") or ("integrated" if "integrated" in statuses else
                                    "lean_checked" if "lean_checked" in statuses else
                                    "submitted" if statuses else "unsolved")
        slug = q.get("slug", qid.lower())
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            raise ValueError(f"{qid}: invalid slug")
        row = {"id": qid, "slug": slug, "source": source, "target": target,
               "category": q.get("category", ""), "status": status,
               "N": None, "B": None, "V": None, "reason": None, "mapping_evidence": None,
               "source_node": None, "target_node": None,
               "new_problem_pairs": [], "witnesses": []}
        mapping = entries.get(qid)
        if mapping is None:
            source_matches = len(names.get(_name_key(source), []))
            target_matches = len(names.get(_name_key(target), []))
            row["reason"] = ("No reviewed variant mapping. Name-only matches in the baseline: "
                             f"source {source_matches}, target {target_matches}. "
                             "A name match alone does not establish equivalent definitions.")
        else:
            if not isinstance(mapping, dict) or not isinstance(mapping.get("evidence"), str) or not mapping["evidence"].strip():
                raise ValueError(f"{qid}: mapping needs review evidence")
            if mapping.get("source_label") != source or mapping.get("target_label") != target:
                raise ValueError(f"{qid}: mapping labels differ from the question")
            a, b = mapping.get("source_node"), mapping.get("target_node")
            if any(type(value) is not int or not 0 <= value < len(nodes) for value in (a, b)):
                raise ValueError(f"{qid}: invalid node index")
            row.update(source_node=a, target_node=b, mapping_evidence=mapping["evidence"])
            if a == b:
                row["reason"] = "Source and target map to the same graph variant; no new rule can be simulated."
            elif (a, b) in direct:
                row["reason"] = "This directed variant pair is already registered as a direct reduction; construction improvements need separate assessment."
            else:
                N, B, pairs, witnesses = _score(a, b, nodes, paths, base_problem_pairs, problem_sizes)
                for witness in witnesses:
                    witness["path"] = [f"candidate:{qid}" if x == "candidate:PLACEHOLDER" else x
                                       for x in witness["path"]]
                row.update(N=N, B=B, V=len(witnesses),
                           new_problem_pairs=[{"source": p, "target": t} for p, t in pairs],
                           witnesses=witnesses)
        rows.append(row)
    rows.sort(key=lambda row: (row["N"] is None, -(row["N"] or 0), -(row["B"] or 0), -(row["V"] or 0), row["id"]))
    previous_score = None
    for position, row in enumerate((row for row in rows if row["N"] is not None), 1):
        score = (row["N"], row["B"], row["V"])
        if score != previous_score:
            rank = position
            previous_score = score
        row["rank"] = rank
    return {"graph_source": GRAPH_URL, "graph_sha256": graph_hash,
            "graph_nodes": len(nodes), "graph_edges": len(edges),
            "excluded_turing_edges": sum(edge.get("turing", False) or edge.get("witness", True) is False
                                         for edge in edges),
            "question_count": len(rows), "scored_count": sum(row["N"] is not None for row in rows),
            "ranking_rule": "N descending, then B descending, then V descending; ID only sets display order within ties",
            "interpretation": "Conditional topology gain only. It does not certify openness, proof correctness, resource compatibility, or full research value.",
            "questions": rows}


STYLE_CSS = """
:root {font-family: Inter, "Segoe UI", system-ui, sans-serif; color:#e6f2ff; background:#061321;
  --bg:#061321; --surface:#0b2139; --surface-2:#102a47; --line:#234766;
  --ink:#e6f2ff; --muted:#a6bdd4; --blue:#65caff; --cyan:#7ee3f4}
* {box-sizing:border-box}
html {scroll-behavior:smooth}
body {margin:0;background:radial-gradient(circle at 82% 1%,#123c69 0,transparent 24rem),var(--bg)}
a {color:var(--cyan);text-decoration:none} a:hover {text-decoration:underline}
:focus-visible {outline:2px solid var(--cyan);outline-offset:3px}
.site-header {border-bottom:1px solid var(--line);background:linear-gradient(120deg,#071a2d,#082645 70%,#0a3157)}
.topbar,.hero,main {max-width:1180px;margin:auto;padding-left:24px;padding-right:24px}
.topbar {height:74px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #ffffff1c}
.brand {display:flex;align-items:center;gap:12px;color:var(--ink);font-weight:700;letter-spacing:.02em}
.brand:hover {text-decoration:none}.brand-mark {width:42px;height:42px;display:block;filter:drop-shadow(0 0 10px #6acbff50)}
nav {display:flex;gap:26px;font-size:.92rem}nav a {color:#bfd1e3}
.hero {min-height:310px;display:flex;align-items:center;justify-content:space-between;gap:32px;padding-top:42px;padding-bottom:44px}
.eyebrow {color:var(--cyan);font-weight:700;letter-spacing:.18em;font-size:.72rem;text-transform:uppercase}
h1 {font-size:clamp(2.25rem,5vw,4rem);line-height:1.04;letter-spacing:-.045em;max-width:680px;margin:14px 0 18px}
.hero p:not(.eyebrow) {color:var(--muted);max-width:600px;line-height:1.55;margin:0}
.hero-links {display:flex;flex-wrap:wrap;gap:8px 20px;margin-top:20px;font-size:.91rem}
.hero-graph {width:min(37vw,390px);min-width:240px;filter:drop-shadow(0 0 20px #32b6ff36)}
main {padding-top:30px;padding-bottom:80px}p {line-height:1.55}
.summary {background:linear-gradient(135deg,#102c49,#0b2037);border:1px solid var(--line);padding:22px 25px;border-radius:16px;box-shadow:0 18px 40px #00000030}
.summary strong {color:#fff}.summary code {overflow-wrap:anywhere;color:#9ec8ff;font-size:.77rem}
.summary p {margin:10px 0;color:#c4d5e7}.summary p:first-child {margin-top:0}.summary p:last-child {margin-bottom:0}
.method-note {margin-top:18px;padding:16px 20px;border:1px solid var(--line);border-radius:12px;background:#091d32;color:#bfd2e4}
.method-note summary {cursor:pointer;color:var(--cyan);font-weight:700}.method-note p {margin:10px 0 0;font-size:.9rem}
#calculation,#pilots {scroll-margin-top:20px}
#calculation h3 {font-size:1.02rem;color:#d7eaff;margin:22px 0 7px}
#calculation code {overflow-wrap:anywhere;color:#9ed8ff}
#calculation ol {padding-left:23px;line-height:1.6}
#pilots {margin-top:38px;margin-bottom:38px}#pilots>h2 {font-size:clamp(1.6rem,3vw,2.2rem);margin:10px 0}
#pilots article h2 {font-size:clamp(1.3rem,3vw,2rem);line-height:1.2}#pilots ol {line-height:1.65}
.controls {display:flex;gap:16px;flex-wrap:wrap;margin:28px 0 16px}
label {display:grid;gap:7px;color:#bed1e7;font-size:.88rem;font-weight:600}
input,select {font:inherit;color:var(--ink);background:var(--surface);padding:10px 12px;border:1px solid #3a617f;border-radius:9px;min-height:43px}
input::placeholder {color:#89a4be}input:focus,select:focus {border-color:var(--cyan)}
#count {color:var(--muted);font-size:.88rem;margin:18px 0}
.table-wrap {overflow-x:auto;border:1px solid var(--line);border-radius:14px;background:var(--surface)}
table {width:100%;border-collapse:collapse;min-width:710px}
th,td {padding:17px 16px;text-align:left;border-bottom:1px solid #23415b;vertical-align:top}
th {color:#adcae1;font-size:.76rem;text-transform:uppercase;letter-spacing:.08em;background:#10304e}
tr:last-child td {border-bottom:0}tbody tr:hover {background:#102d4a}
td:nth-child(1),td:nth-child(4) {white-space:nowrap}td:nth-child(1) {color:var(--cyan);font-weight:700}
td b {font-weight:650}.meta,.detail {display:block;margin-top:6px;color:var(--muted);font-size:.87rem;line-height:1.45}
.relations {margin-top:10px;color:#b8d5ea;font-size:.86rem}.relations summary {cursor:pointer;color:var(--cyan)}
.relations ol {margin:9px 0;padding-left:22px}.relations li {margin:7px 0}.relations small {display:block;color:#8fb4d0;margin:2px 0 0;white-space:normal}
.muted {color:var(--muted)}td:nth-child(4) strong {font-size:1.25rem;color:#fff}td:nth-child(4) small {display:block;color:#9fbdd4}
[hidden] {display:none!important}
@media(max-width:760px) {.topbar,.hero,main {padding-left:16px;padding-right:16px}nav {gap:13px;font-size:.8rem}.hero {min-height:260px}.hero-graph {width:180px;min-width:180px}th,td {padding:12px}}
@media(max-width:560px) {.topbar {height:64px}.brand {font-size:.9rem}nav a:nth-child(1) {display:none}.hero {display:block;min-height:0;padding-top:32px;padding-bottom:36px}.hero-graph {display:none}.summary {padding:18px}input {max-width:100%}}
"""

def render_page(report):
    escape = lambda value: html.escape(str(value), quote=True)
    rows = []
    for row in report["questions"]:
        discount = (f'D½ {row["D_half"]:.3f} · ' if "D_half" in row else "")
        score = (f'<strong>{row["N"]}</strong> <small>{discount}B {row["B"]:g} · V {row.get("V", len(row["witnesses"]))} · {"Reviewed" if row.get("mapping_evidence") else "Provisional"}</small>'
                 if row["N"] is not None else '<span class="muted">Not scored</span>')
        detail = (f'{len(row["new_problem_pairs"])} new problem pairs. '
                  + (f'{row["direct_count"]} direct, {row["transitive_count"]} transitive. '
                     if "direct_count" in row else "")
                  + (row.get("reason") or "") + " " + row.get("assumptions", "")
                  if row["N"] is not None else row["reason"])
        checked = (f' · literature checked {escape(row["literature_checked"])}'
                   if row.get("literature_checked") else "")
        importance = (f'<span class="detail"><b>Board-stated importance (not independently checked{checked}):</b> '
                      f'{escape(row["board_importance"])}</span>'
                      if row.get("board_importance") else "")
        changed = row["new_problem_pairs"]
        relation_items = "".join(
            f'<li>{escape(pair["source"])} → {escape(pair["target"])}'
            + (f'<small>{pair.get("hops", "?")} hops · weight {pair.get("discount_weight", "?")}. Witness: {escape(" → ".join(pair["witness_nodes"]))}</small>'
               if pair.get("witness_nodes") else "") + '</li>'
            for pair in changed[:12]
        )
        more = (f'<p>{len(changed) - 12} more pairs in <a href="ranking.json">ranking.json</a>.</p>'
                if len(changed) > 12 else "")
        breakdown = row.get("variant_gain_breakdown")
        variant_detail = (f'<p>Concrete variant gain: {breakdown["direct"]} direct, '
                          f'{breakdown["upstream"]} from old upstream, '
                          f'{breakdown["downstream"]} to old downstream, '
                          f'{breakdown["both_sides"]} across both sides.</p>'
                          if breakdown else "")
        relations = (f'<details class="relations"><summary>Changed reachability: {len(changed)} problem pairs</summary>'
                     f'{variant_detail}<ol>{relation_items}</ol>{more}</details>' if changed else "")
        rows.append(
            f'<tr class="question-row" data-status="{escape(row["status"])}" '
            f'data-scored="{str(row["N"] is not None).lower()}">'
            f'<td>{escape(row.get("rank", "—"))}</td>'
            f'<td><a href="{BOARD_URL}{escape(row["slug"])}.json">{escape(row["id"])}</a></td>'
            f'<td><b>{escape(row["source"])} → {escape(row["target"])}</b><span class="meta">{escape(row["category"])} · {escape(row["status"])}' 
            f'</span><span class="detail">{escape(detail)}</span>{importance}{relations}</td>'
            f'<td>{score}</td></tr>')
    table = "\n".join(rows)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Reduction question ranking</title>
<style>
{STYLE_CSS}
</style></head><body><header class="site-header"><div class="topbar"><a class="brand" href="#top"><img class="brand-mark" src="lab-mark.svg" alt="Problem-Reductions lab mark"><span>Reduction Impact Atlas</span></a><nav aria-label="Primary"><a href="#ranking" aria-current="page">Full ranking</a><a href="pilot.html">AI examples</a><a href="calculation.pdf">Calculation PDF</a></nav></div>
<div class="hero" id="top"><div><p class="eyebrow">Evidence-backed graph analysis</p><h1>See what a new reduction connects.</h1><p>Conditional structural gain for open reduction questions. Inspect each new relation and the path behind it.</p><div class="hero-links"><a href="calculation.pdf">How are these scores calculated? PDF ↗</a><a href="pilot.html">View 5 AI bridge examples →</a><a href="https://codingthrust.github.io/problem-reductions/" target="_blank" rel="noopener noreferrer">Problem Reductions source site ↗</a></div></div>
<svg class="hero-graph" viewBox="0 0 390 270" role="img" aria-label="Stylized blue reduction network"><defs><pattern id="grid" width="18" height="18" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r="1" fill="#38658a"/></pattern></defs><rect width="390" height="270" fill="url(#grid)" opacity=".5"/><g stroke="#53a5db" opacity=".26" stroke-width="1"><path d="M45 163L120 71 177 148 250 60 331 124 287 213 177 148 66 232 45 163M120 71L250 60M120 71L287 213M45 163L177 148M177 148L331 124M66 232L287 213M250 60L287 213"/></g><g fill="#76d9ff"><circle cx="45" cy="163" r="5"/><circle cx="120" cy="71" r="7"/><circle cx="177" cy="148" r="11"/><circle cx="250" cy="60" r="5"/><circle cx="331" cy="124" r="7"/><circle cx="287" cy="213" r="6"/><circle cx="66" cy="232" r="4"/></g><g fill="#cdeeff" font-size="11" font-family="system-ui"><text x="130" y="59">SAT</text><text x="191" y="142">new rule</text><text x="298" y="232">target</text></g></svg></div></header>
<main><div class="summary" id="method"><p><strong>{report["question_count"]} questions shown · {report["scored_count"]} estimated · {len(report.get("baseline_bridge_edges", []))} definition bridges · {report.get("reviewed_count", 0)} exact-variant mappings.</strong></p>
<p>Scores estimate graph reachability if each unverified rule were added. Unknown endpoints start as new nodes; documented baseline bridges connect some of them to graph variants in a stated direction. A unique name match remains provisional. N and B do not measure proof difficulty or overall importance.</p>
<p>{escape(report.get("N_distribution", {}).get("1", 0))} questions currently have N=1. D½ is an exploratory path-discount value: each additional edge in the shortest witness chain halves that relation's weight. It does not change the official N/B/V ranking. Equal N, B, and V share a rank; IDs only set their display order. Expand a row to see exactly which problem relations become reachable.</p>
<p>Baseline: {report["graph_nodes"]} variants, {report["graph_edges"]} source edges. The calculation excludes {report.get("excluded_turing_edges", 0)} Turing or non-witness-preserving edges because a candidate requires one-call recovery. SHA-256: <code>{escape(report["graph_sha256"])}</code>. <a href="ranking.json">Results and witnesses</a> · <a href="reduction_graph.json">Graph snapshot</a> · <a href="questions.json">Question snapshot</a> · <a href="bridges.json">Bridge evidence</a> · <a href="mappings.json">Reviewed mappings</a>.</p></div>
<div class="method-note" id="calculation"><p><strong>Calculation method:</strong> the formulas, assumptions, frozen inputs, and reproduction steps are in the <a href="calculation.pdf">project methodology PDF</a>. The <a href="pilot.html">5 AI bridge examples</a> use separate hypothetical baselines and do not change this ranking.</p></div>
<div class="controls"><label>Search questions<input id="search" type="search" placeholder="ID, source, or target"></label><label>Status<select id="status"><option value="all">All statuses</option><option value="unsolved">Unsolved</option><option value="submitted">Solution submitted</option><option value="lean_checked">Lean checked</option><option value="integrated">Integrated</option></select></label><label>Score availability<select id="availability"><option value="all">All questions</option><option value="true">Scored</option><option value="false">Not scored</option></select></label></div>
<p id="count" role="status"></p><div class="table-wrap" id="ranking"><table><thead><tr><th>Rank</th><th>ID</th><th>Question and reason</th><th>N / D½ / B / V</th></tr></thead><tbody>{table}</tbody></table></div></main>
<script>
const rows=[...document.querySelectorAll('.question-row')];const search=document.querySelector('#search'),status=document.querySelector('#status'),availability=document.querySelector('#availability');
function filter(){{let shown=0;for(const row of rows){{const match=row.textContent.toLowerCase().includes(search.value.trim().toLowerCase())&&(status.value==='all'||row.dataset.status===status.value)&&(availability.value==='all'||row.dataset.scored===availability.value);row.hidden=!match;if(match)shown++}}document.querySelector('#count').textContent=shown+' questions visible'}}
for(const input of [search,status,availability])input.addEventListener('input',filter);filter();
</script></body></html>'''
