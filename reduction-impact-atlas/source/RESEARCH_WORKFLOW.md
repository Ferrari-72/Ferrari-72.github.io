# Surveying known relations around open rules

The task is to find existing reductions that the frozen graph has not recorded, and use them to complete the upstream or downstream context of an open board rule. It is not a search for efficient algorithms or invented pairings.

For an open parent p: A -> B, investigate a known downstream relation k: B -> C. The literature or an explicit definition/verifier argument must establish k under compatible input, output and resource conventions. C need not already occur in the graph. Add k only to a temporary graph copy, then evaluate p in that context.

## Evidence record

Each known relation records exact endpoints, a source definition, a bounded-certificate or embedding argument, references, output recovery, and remaining graph-adapter review. A theorem-backed relation and an independently reviewed exact graph adapter are different states. Never infer a relation merely from names.

The present catalogue includes four restriction embeddings into general three-coloring and sixteen polynomial-verifier-to-SAT applications. These are existing inclusions and upper bounds, not twenty independent new theorems. Certificate length caps are supplied for binary budgets. Generic SAT encoding does not imply an efficient source algorithm.

## Calculation

- Direct group: compare G with G+k to report coverage gained from the known relation.
- Downstream group: compare G+k with G+k+p to measure the open parent's impact after its known downstream relation is available. Only p is hypothetical.
- Also report the parent impact in G, the gain of k alone, and the combined gain relative to G. Do not add these counts.

Every relation is evaluated separately. Other surveyed edges are not accumulated into its baseline. Task nodes and family projections remain fixed in each comparison. All witnesses distinguish known edges from assumption-prefixed parent edges. The original graph and ranking.json remain unchanged.

## Reproduction

Run python build.py and python -m unittest -v test_ranker.py. The research.html page links to research-method.pdf, research_candidates.json and research.json. The release packager includes all source and evidence files. The earlier algorithm-goal scenarios and unsupported downstream pairings have been replaced, including their methodology PDF.
