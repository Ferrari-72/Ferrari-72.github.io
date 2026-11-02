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

The current code **does not yet implement arbitrary new downstream candidate edges or compound-assumption scenarios**. `pilot_bridges.json` supports one endpoint-alignment bridge for an existing board question, not a new direct `B -> C` research question. Extend the scenario layer and add hand-checkable tests before publishing downstream scores. Keep the existing `ranking.json` unchanged until a new scoring scope is agreed and documented.
