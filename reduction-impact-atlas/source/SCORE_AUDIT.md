# Score audit

Checked against the frozen inputs on 2026-11-03. No metric or baseline changes were made for the display cleanup.

## Official open rules

49 of 76 rules have exactly (N, B, V) = (1, 0, 1). All 49 have zero baseline edges entering their mapped source and zero baseline edges leaving their mapped target. Adding the proposed edge therefore has no upstream or downstream composition: only its own pair becomes reachable. This is a precise local connectivity limitation, not evidence that all questions have the same scientific value. It also does not establish that the whole graph consists of disconnected components.

The remaining scores form five groups: 16 rules at (4,0,11), six at (6,0,12), three at (5,0,12), one at (4,0.277777777778,19), and one at (1,0,2).

## Surveyed relations

16 of 20 known edges target graph node 220 (general SAT); four target node 89 (general 3-coloring). The 16 SAT entries apply a general verifier encoding. They are not 16 distinct nontrivial literature constructions. SAT already reaches 93 other problem families in this baseline; a fresh family connected to it gains 94 family pairs, including SAT itself. Consequently all six direct SAT rows have N=94, V=117 and D_half=16.734375. Four direct coloring rows have N=13, V=19 and D_half=3.5.

Six downstream rows likewise share N=4, V=127 and D_half=1.4375, despite differing source definitions. The new known edge can add many concrete variants while adding few new family pairs for the parent. Family projection and existing overlap matter.

Path discounting does not resolve identical neighbourhoods: equal path profiles remain equal even with decimals. Adding digits or arbitrary weights would manufacture a distinction.

## Display and research decisions

- The survey is one table. A comparison column distinguishes known-edge coverage from open-rule impact in known downstream context. There is no global rank mixing these two quantities.
- N is the default visible measure; B, V, D_half, evidence and example paths are inside each expandable row.
- The next evidence improvement is to find specific, nontrivial known reductions with diverse targets and check their exact variants. Do not invent algorithm goals or arbitrary hypothetical links to fill the list.
- Add only evidence-backed, directional adapters. Recompute on graph copies. Keep the official snapshot unchanged until review.
- Report tied coverage honestly. Research importance needs a separate justified criterion; topology alone cannot supply it.

## Reproduction

Run `python build.py` then inspect `dist/ranking.json` and `dist/research.json`. Count official (N,B,V) tuples; for tied source and target indices, count incoming and outgoing baseline edges from the survey's exported baseline. Count survey `known_edge.target`, and compare N/V/D_half by group. All results above use the same frozen graph and bridge inputs as the site.
