# Independent reduction-question ranking

This project is separate from both upstream repositories. It reads frozen public data, produces a static site, and does not edit either repository.

The published [source directory](https://github.com/Ferrari-72/Ferrari-72.github.io/tree/main/reduction-impact-atlas/source) includes the Python builder, tests, frozen inputs and lab-mark asset. From that directory, `python build.py` writes the complete static site to `dist/`. No upstream checkout is needed. The generated files at `reduction-impact-atlas/` are the deployed Pages copy; the source directory is a reproducible snapshot, not a second website.

## Current result

The frozen board snapshot also carries each record's stated importance and literature-check date. The site quotes these statements with a link to the source record and labels them as not independently checked; they are not numeric ranking inputs.

The frozen `data/questions.json` contains 76 board records. `data/reduction_graph.json` contains 257 variants and 344 directed edges. The site gives **all 76 a conditional topology estimate**. The one-call witness-preserving calculation excludes 22 Turing or non-witness-preserving edges. `data/bridges.json` records ten directional, definition-backed baseline links. Seventeen 3-SAT source questions return assignments and accept a graph-to-board bridge; six decision-only 3-SAT sources require the opposite direction. Independent Set and Vertex Cover use the graph's decision variants, and Triangle Partition uses the graph's matching witness model. Every bridge pins the input hashes and records evidence. An endpoint with one matching graph name connects provisionally to that node; other endpoints start as new nodes. No exact-variant mapping has yet been reviewed. The current `N` distribution is 6 questions at 6, 3 at 5, 17 at 4, and 50 at 1. The other 49 isolated questions remain tied at `(N,B,V)=(1,0,1)`. This is a conditional structural ordering, not a research-priority ranking.

The graph snapshot was downloaded from `https://codingthrust.github.io/problem-reductions/reductions/reduction_graph.json` on 2026-10-16. Its SHA-256 is pinned in `data/mappings.json`. `data/questions.json` was extracted from the local `autoresearch-gadgets-main/registry` on the same date and includes a registry content hash. The graph file does not claim to correspond to a particular Git commit of the source repository.

## Acceptance tests

1. Every question in the frozen board snapshot appears exactly once on the page and in `ranking.json`.
2. A graph-external endpoint becomes a new isolated node; a unique name-only match is labelled provisional. A genuinely unscored strict-mode question keeps a reason and a null score.
3. A reviewed exact-variant mapping gives the expected `N`, `B`, and `V` on a hand-checkable graph. A directional definition bridge changes the affected question's reachable pairs, and input-hash mismatch fails. Equal `N`, `B`, and `V` share a rank.
4. Stale graph hashes, missing mapping evidence, wrong labels and invalid node indices fail the build. An already registered direct edge remains visible with a zero topology estimate and an explicit limitation.
5. Browser checks cover all rows, search, status filter, score-availability filter, JavaScript errors and 375px layout.
6. An isolated build copies only this project's Python files and frozen inputs into a temporary directory, then builds all 76 results there.
7. A deterministic random-graph test recomputes reachability before and after each candidate edge independently and checks `N`, `B`, changed variant pairs and witnesses. A separate test verifies that a Turing edge cannot enter a single-call witness path.

Run:

```powershell
cd "F:\auto research idea\rule-ranking"
python -m unittest -v test_ranker.py
python build.py
uv sync --locked
uv run --locked python browser_check.py
```

If the sandbox blocks the default uv cache, run the browser test with `.\.venv\Scripts\python.exe browser_check.py` after `uv sync --locked`.

## Refreshing inputs

To update the board snapshot from any local checkout:

```powershell
python snapshot_board.py "PATH_TO_BOARD\registry"
```

To update the graph, replace `data/reduction_graph.json` with a downloaded upstream export and record its URL, date and SHA-256. All reviewed mappings and definition bridges must then be checked again and their graph hashes updated. The site build needs only the frozen JSON snapshots, bridge/mapping files and lab-mark SVG; neither upstream checkout is required.

Each reviewed mapping entry has the form:

```json
"Q001": {
  "source_node": 12,
  "target_node": 34,
  "source_label": "Exact source text from the board",
  "target_label": "Exact target text from the board",
  "evidence": "Why these precise graph variants have the same semantics and direction"
}
```

Indices refer to `nodes` in the pinned graph file. A reviewer must check definitions, variants, restrictions and output semantics. Until then, the provisional name match is an assumption, not an identity claim. `N` counts new directed problem pairs reachable through single-call, witness-preserving edges. `B` measures additional variant coverage only for problem pairs already connected in the baseline. `V` counts all newly reachable concrete variant pairs. `D_half` is an exploratory decimal: for each newly reachable problem pair, take the shortest witness chain of `h` edges (including the candidate) and add `0.5^(h-1)`. The output partitions `N` into direct and transitive problem pairs, gives a hop histogram, and partitions `V` into the candidate pair, old upstream, old downstream, and both sides. A bridge counts as an edge, so `D_half` depends on the graph representation; it is not a research-value score or the official sort key. Sort by `N`, `B`, then `V`; equal triples share a rank. The baseline graph and each candidate rule are combined only under the stated assumptions. New isolated endpoints often give `(N,B,V)=(1,0,1)`, which is a data-coverage effect and says little about research value. Adding arbitrary decimal offsets would create false precision.

## Three isolated AI bridge examples

`python build.py` places three labelled examples above the ranking on the main `index.html` page. Q054 is the only current official row with fractional `B=0.277778` (`N=4`, `V=19`). A separately proposed reverse 3-SAT bridge leaves N at 4 but changes its marginal B to 0 and V to 11: more baseline reachability means less *new* reachability when the hypothetical question rule is added. This is not a loss of reachability in the graph. Q001 and Q057 remain separate target-side AI bridge pilots; each changes from `(N,B,V)=(1,0,1)` to `N=94`, with V=118 and 119. All three pilots are recorded in `dist/pilot.json` from `data/pilot_bridges.json`. The old `pilot.html` URL redirects to the example section. The same page includes an English-only `#calculation` methodology with formulas, assumptions, frozen inputs and reproduction command, plus links to the upstream Problem Reductions site and lab portfolio. This methodology is authored by the Atlas project, not endorsed by the upstream graph project. Each pilot fixes its question endpoint's problem-family projection in both the before and after graphs, so the comparison changes only the bridge edge. The official `data/bridges.json`, `dist/ranking.json`, and main ranking do not change. These bridges remain AI proposals pending independent semantic review; the question rules remain hypothetical. The pilots are examples, not a completed semantic experiment on all 76 questions.

## Publishing

`dist/` contains a self-contained static page, full results, evidence, lab mark and input snapshots. The lab mark is derived by cropping the [Problem-Reductions project's SVG](https://codingthrust.github.io/problem-reductions/) with permission from the user; the page design uses its own blue palette. The current ordering still has a 49-question tie and unreviewed name matches. Keep the assumptions visible; do not present the list as a validated research-priority order. The page is live at [Reduction Impact Atlas](https://ferrari-72.github.io/reduction-impact-atlas/). Generated files and the reproducible `source/` snapshot occupy only `reduction-impact-atlas/` within the Pages repository; the portfolio home page is unchanged.
