# Architecture and maintenance

## Boundaries

| Layer | Files | Responsibility |
| --- | --- | --- |
| Frozen inputs | `data/reduction_graph.json`, `data/questions.json` | Graph variants and edges; board question definitions and status |
| Reviewed or proposed connections | `data/mappings.json`, `data/bridges.json`, `data/pilot_bridges.json` | Exact mappings, baseline definition bridges, isolated AI proposals |
| Calculation | `ranker.py`, `estimate.py` | Validate graph, calculate variant reachability, project to families, record witnesses |
| Scenarios | `pilot.py` | Recalculate one proposed definition bridge at a time; never modify the official report |
| Outputs | `build.py`, `make_pdf.py`, `package_release.py` | Build static files, regenerate methodology PDF, package site plus matching source |
| Checks | `test_ranker.py`, `browser_check.py` | Numerical invariants, frozen-input failure modes, site behavior |

`snapshot_board.py` is an optional importer. The normal build reads only `data/` and `assets/`; it does not inspect an upstream checkout or fetch live network data.

## Data flow

1. `build.py` reads the five frozen JSON files. Mapping and bridge records pin the graph hash; bridge and pilot files also pin the board registry hash. A mismatch fails the build.
2. `estimate.build_estimate_report` attaches board endpoints to exact mapped variants, provisional unique-name matches, or new isolated nodes. Definition bridges have a stated direction and evidence.
3. Reachability is computed on concrete variants first. It is projected to problem families only afterward. Turing or non-witness-preserving edges do not enter the one-call path model.
4. Each hypothetical board rule is added separately. The official report sorts by `N`, `B`, `V`, with equal triples tied. Witness chains and the exploratory `D_half` are reported separately.
5. `pilot.py` holds the family projection fixed within each before/after comparison. Each AI-proposed bridge gets its own baseline; its result is not an official-rank update.
6. `package_release.py` copies only named deliverables and source files. Its output can be rebuilt without either upstream repository.

## Editing guide

- **New board snapshot:** run `python snapshot_board.py PATH_TO_REGISTRY`, inspect the changed question records, and review all hash-pinned mappings and bridges before updating their hashes.
- **New graph snapshot:** replace `data/reduction_graph.json`, record its source and SHA-256, recheck node indices, variants, edge types, mappings, and every bridge. A hash update alone is not semantic review.
- **New exact mapping:** add the question ID, node indices, exact labels, and definition evidence to `data/mappings.json`. A unique name match is only provisional.
- **New baseline bridge:** use `data/bridges.json` only after independently checking instance direction, restrictions, output recovery, and resource bounds.
- **New AI proposal:** use `data/pilot_bridges.json` for an isolated, explicitly unreviewed definition-alignment scenario. This is not a general registry for newly researched downstream reductions; see [RESEARCH_WORKFLOW.md](RESEARCH_WORKFLOW.md).
- **Method or presentation:** update the relevant Python source, regenerate `assets/calculation.pdf` when formulas or caveats change, then rebuild and package.

The frozen graph has 257 variants and 344 directed source edges. The 76-question board snapshot and graph were frozen on 2026-10-16. The graph export does not claim a specific source-repository commit. Twenty-two Turing or non-witness-preserving edges are excluded from candidate path composition. Ten directional definition bridges enter the official baseline; no exact-variant mapping has passed review.

## Review gates

Run `python -m unittest -v test_ranker.py`, `python build.py`, and the browser check. Confirm that every question appears once, every new family pair has a witness, bridge proposals do not alter `ranking.json`, and both pages link to the calculation PDF. Verify the rendered PDF and the output directory before publishing. A proposed direct reduction can be *counted conditionally* without being proved, but it must be visibly labelled and kept out of the established baseline.
