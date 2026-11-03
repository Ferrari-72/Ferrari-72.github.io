# Researching new direct reductions

The next research step is to investigate possible **outgoing** reductions from a board target problem. If an open board rule is `A -> B`, the present frozen graph may count paths from known predecessors of `A` to `B`, while missing possible `B -> C` relations. `C` need not already occur in the graph. The senior review explicitly allows conditional counting without inserting an unproved relation into the established graph.

## Keep three states separate

1. **Established baseline:** a documented, directionally compatible reduction or definition bridge. Only reviewed records belong in `data/bridges.json` or the frozen graph.
2. **Research candidate:** a proposed direct `B -> C` open question. Record it outside the baseline with its precise source and target variants, output convention, restrictions, literature search, and unresolved proof obligation.
3. **Conditional scenario:** add the board rule and one or more explicit research candidates to a *copy* of the graph. Report the added reachable pairs, witness paths, and the exact unproved assumptions on which each result depends. Never describe this as known reachability.

For example, if the known graph contains `X -> A`, a hypothetical board rule `A -> B` gives conditional `X -> B`. If research proposes `B -> C`, then `A -> C` and `X -> C` may also be counted in the **two-assumption scenario**. Without a specific `B -> C` candidate, there is no numerical downstream gain to calculate.

## Candidate record for review

Record one proposed direct reduction per entry:

- Stable candidate ID; source and target question IDs or new problem names.
- Exact input and output definitions, variant restrictions, direction, and intended reduction type.
- Sources searched, dates, nearby known results, and why the status is still open or uncertain.
- Proposed construction or semantic link, witness recovery, and resource conditions.
- Review state: `proposed`, `literature-checked`, `semantically-reviewed`, or `proved`. A status change requires evidence.
- Scenario input hashes, separately reported conditional score, and witness paths.

## Implemented scenario layer

`research.py` reads `data/research_candidates.json` separately from the official board and bridge files. `estimate.prepare_baseline` creates a copied baseline, and the research evaluator adds only named assumption edges. It recomputes both closures for each comparison and records every assumption used by each shortest family-pair witness.

The initial catalogue has ten new direct-route questions and ten speculative downstream pairings over ten new task definitions. They are not twenty independent complexity classifications. The primary references support the task's unresolved status; they do not prove the proposed edge. Every route remains explicitly unreviewed. Some target tasks have quasipolynomial algorithms, making a hardness chain incompatible with ETH; the catalogue flags this obstacle.

New-direct records compare G to G+r. Downstream records reference a parent board ID and compare G+p to G+p+s for marginal scores, and G to G+p+s for combined scores. The two groups have separate tied rankings. Input hashes must match. Task nodes exist in both comparison graphs, with a fixed family projection. The temporary baseline includes ten documented polynomial-verifier-to-SAT support routes; the catalogue supplies a finite-certificate verifier argument for each task. They are known upper bounds, not additional new open questions. Nine proposed 2-SAT algorithms consequently have N=0, B=1/9, V=1. A scenario never changes `ranking.json`.

Build all outputs with `python build.py`. The dedicated English page is `research.html`, its evidence is in `research.json`, and its calculation appendix is `research-method.pdf`. Regenerate the appendix with `python make_research_pdf.py` using the locked docs dependency group. `package_release.py` includes these files and their source inputs.
