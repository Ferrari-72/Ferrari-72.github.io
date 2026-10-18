"""Estimate conditional topology gain for every board question.

New board endpoints become isolated nodes. A unique name-only graph match is
used provisionally; an explicitly reviewed mapping takes precedence.
"""
from collections import Counter
from fractions import Fraction

from ranker import GRAPH_URL, _name_key, _paths, _score, _validate_graph


def build_estimate_report(graph, graph_hash, questions, mappings, bridges=None, registry_hash=None,
                          family_overrides=None):
    graph_nodes, graph_edges = _validate_graph(graph)
    if mappings.get("graph_sha256") != graph_hash:
        raise ValueError("mapping graph hash does not match the frozen snapshot")
    entries = mappings.get("entries")
    if not isinstance(entries, dict):
        raise ValueError("mapping entries must be an object")
    ids = [q["id"] for q in questions]
    if len(ids) != len(set(ids)) or set(entries) - set(ids):
        raise ValueError("duplicate question ID or unknown mapping ID")
    nodes = [dict(node) for node in graph_nodes]
    edges = list(graph_edges)
    exact_names = {}
    for index, node in enumerate(graph_nodes):
        exact_names.setdefault(_name_key(node["name"]), []).append(index)
    added = {}
    endpoint_map = {}
    for q in questions:
        qid = q["id"]
        mapping = entries.get(qid)
        if mapping:
            if not isinstance(mapping.get("evidence"), str) or not mapping["evidence"].strip():
                raise ValueError(f"{qid}: mapping needs review evidence")
            if mapping.get("source_label") != q["source"] or mapping.get("target_label") != q["target"]:
                raise ValueError(f"{qid}: mapping labels differ from question")
            pair = (mapping.get("source_node"), mapping.get("target_node"))
            if any(type(x) is not int or not 0 <= x < len(graph_nodes) for x in pair):
                raise ValueError(f"{qid}: invalid node index")
            endpoint_map[qid] = (pair[0], pair[1], "Reviewed exact-variant mapping: " + mapping["evidence"], mapping["evidence"])
            continue
        pair = []
        notes = []
        for side in ("source", "target"):
            label = q[side]
            matches = exact_names.get(_name_key(label), [])
            if len(matches) == 1:
                index = matches[0]
                notes.append(f"{side}: name-only match to graph node {index}; exact definitions still need review")
            else:
                definition = q.get(side + "_definition")
                key = (label, definition) if definition else (qid, side)
                if key not in added:
                    index = len(nodes)
                    added[key] = index
                    nodes.append({"name": label, "problem_key": f"board:{index}", "variant": {}})
                index = added[key]
                notes.append(f"{side}: new isolated node ({'ambiguous graph variants' if matches else 'absent from graph names'})")
            pair.append(index)
        endpoint_map[qid] = (*pair, "; ".join(notes) + "; hypothetical rule and path composition unverified", None)
    for qid, side_families in (family_overrides or {}).items():
        if qid not in endpoint_map or not isinstance(side_families, dict):
            raise ValueError("invalid problem-family override")
        for side, family in side_families.items():
            if side not in ("source", "target") or not isinstance(family, str) or not family:
                raise ValueError("invalid problem-family override")
            board_node = endpoint_map[qid][0 if side == "source" else 1]
            if board_node < len(graph_nodes) or family not in {node["name"] for node in graph_nodes}:
                raise ValueError("problem-family override needs a board endpoint and graph family")
            previous = nodes[board_node].get("problem_key", f"board:{board_node}")
            if previous != f"board:{board_node}" and previous != family:
                raise ValueError("conflicting problem-family override")
            nodes[board_node]["problem_key"] = family
    bridge_records = []
    if bridges is not None:
        if bridges.get("graph_sha256") != graph_hash or bridges.get("registry_sha256") != registry_hash:
            raise ValueError("bridge snapshot hash does not match frozen inputs")
        if not isinstance(bridges.get("entries"), list):
            raise ValueError("bridge entries must be a list")
        question_by_id = {q["id"]: q for q in questions}
        deduplicated = {}
        for item in bridges["entries"]:
            qids = item.get("question_ids")
            side = item.get("side")
            graph_node = item.get("graph_node")
            family = item.get("problem_family")
            direction = item.get("direction")
            evidence = item.get("evidence")
            if (not isinstance(qids, list) or not qids or len(qids) != len(set(qids))
                    or side not in ("source", "target")
                    or type(graph_node) is not int or not 0 <= graph_node < len(graph_nodes)
                    or (family is not None and family != graph_nodes[graph_node]["name"])
                    or direction not in ("graph_to_board", "board_to_graph")
                    or not isinstance(evidence, str) or not evidence.strip()):
                raise ValueError("invalid bridge entry")
            for qid in qids:
                if qid not in question_by_id or question_by_id[qid][side] != item.get("label"):
                    raise ValueError(f"{qid}: bridge label or question ID mismatch")
                board_node = endpoint_map[qid][0 if side == "source" else 1]
                if board_node < len(graph_nodes):
                    raise ValueError(f"{qid}: bridge endpoint is not a new board node")
                if family is not None:
                    previous_family = nodes[board_node].get("problem_key", f"board:{board_node}")
                    if previous_family != f"board:{board_node}" and previous_family != family:
                        raise ValueError(f"{qid}: conflicting problem-family projection")
                    nodes[board_node]["problem_key"] = family
                pair = ((graph_node, board_node) if direction == "graph_to_board"
                        else (board_node, graph_node))
                key = (*pair, evidence)
                record = deduplicated.get(key)
                if record is None:
                    edge_index = len(edges)
                    edges.append({"source": pair[0], "target": pair[1]})
                    record = {"source_node": pair[0], "target_node": pair[1],
                              "edge_index": edge_index, "direction": direction,
                              "evidence": evidence, "source_url": item.get("source_url"),
                              "question_ids": []}
                    deduplicated[key] = record
                    bridge_records.append(record)
                record["question_ids"].append(qid)
                a, b, assumptions, review = endpoint_map[qid]
                endpoint_map[qid] = (a, b, assumptions + f"; baseline bridge edge {record['edge_index']} ({direction})", review)
    paths = _paths(nodes, edges)
    problems = [node.get("problem_key", node["name"]) for node in nodes]
    labels = {}
    for node in nodes:
        labels.setdefault(node.get("problem_key", node["name"]), node["name"])
    sizes = Counter(problems)
    old_problem_pairs = {(problems[u], problems[v]) for u, reached in enumerate(paths)
                         for v in reached if problems[u] != problems[v]}
    direct = {(edge["source"], edge["target"]) for edge in edges
              if not edge.get("turing", False) and edge.get("witness", True) is not False}
    rows = []
    for q in questions:
        qid = q["id"]
        a, b, assumptions, evidence = endpoint_map[qid]
        status_set = set(q.get("solution_statuses", [s["status"] for s in q.get("solutions", [])]))
        status = ("integrated" if "integrated" in status_set else "lean_checked" if "lean_checked" in status_set
                  else "submitted" if status_set else "unsolved")
        N, B, pairs, witnesses = _score(a, b, nodes, paths, old_problem_pairs, sizes)
        by_problem_pair = {}
        for witness in witnesses:
            witness["path"] = [f"candidate:{qid}" if x == "candidate:PLACEHOLDER" else x
                               for x in witness["path"]]
            current = witness["source_node"]
            node_path = [current]
            for step in witness["path"]:
                edge = ({"source": a, "target": b} if step == f"candidate:{qid}"
                        else edges[int(step.removeprefix("edge:"))])
                if edge["source"] != current:
                    raise AssertionError(f"{qid}: discontinuous witness path")
                current = edge["target"]
                node_path.append(current)
            if current != witness["target_node"]:
                raise AssertionError(f"{qid}: witness target mismatch")
            witness["node_path"] = node_path
            key = (problems[witness["source_node"]], problems[witness["target_node"]])
            if key in pairs and (key not in by_problem_pair or len(node_path) < len(by_problem_pair[key])):
                by_problem_pair[key] = node_path
        def node_label(index):
            node = nodes[index]
            variant = node.get("variant") or {}
            suffix = " (" + ", ".join(f"{key}={value}" for key, value in sorted(variant.items())) + ")" if variant else ""
            return node["name"] + suffix + (" [board]" if index >= len(graph_nodes) else "")
        reason = None
        if a == b:
            reason = "Both endpoints map to one node; this topology measure cannot represent the requested improvement."
        elif (a, b) in direct:
            reason = "The directed edge is already registered; N=0 does not assess a better construction or overhead."
        elif N == 1 and not evidence:
            reason = "Only one new problem relation appears under these sparse, provisional connections; this tie does not imply equal research value."
        pair_rows = []
        weighted = Fraction(0)
        hop_histogram = Counter()
        for p, t in pairs:
            path = by_problem_pair[(p, t)]
            hops = len(path) - 1
            weight = Fraction(1, 2 ** (hops - 1))
            weighted += weight
            hop_histogram[hops] += 1
            pair_rows.append({"source": labels[p], "target": labels[t],
                              "witness_nodes": [node_label(index) for index in path],
                              "hops": hops, "discount_weight": float(weight)})
        direct_pair = (problems[a], problems[b])
        direct_count = int(direct_pair in pairs)
        variant_classes = Counter()
        for witness in witnesses:
            source_is_candidate = witness["source_node"] == a
            target_is_candidate = witness["target_node"] == b
            category = ("direct" if source_is_candidate and target_is_candidate else
                        "upstream" if not source_is_candidate and target_is_candidate else
                        "downstream" if source_is_candidate and not target_is_candidate else
                        "both_sides")
            variant_classes[category] += 1
        variant_gain_breakdown = {name: variant_classes[name]
                                  for name in ("direct", "upstream", "downstream", "both_sides")}
        if sum(variant_gain_breakdown.values()) != len(witnesses):
            raise AssertionError(f"{qid}: variant gain partition does not equal V")
        rows.append({"id": qid, "slug": q.get("slug", qid.lower()), "source": q["source"],
                     "target": q["target"], "category": q.get("category", ""), "status": status,
                     "board_importance": q.get("board_importance", ""),
                     "literature_checked": q.get("literature_checked"),
                     "N": N, "B": B, "V": len(witnesses), "reason": reason, "assumptions": assumptions,
                     "D_half": round(float(weighted), 9), "direct_count": direct_count,
                     "transitive_count": N - direct_count,
                     "variant_gain_breakdown": variant_gain_breakdown,
                     "hop_histogram": {str(hop): count for hop, count in sorted(hop_histogram.items())},
                     "mapping_evidence": evidence, "source_node": a, "target_node": b,
                     "new_problem_pairs": pair_rows,
                     "witnesses": witnesses})
    rows.sort(key=lambda row: (-row["N"], -row["B"], -row["V"], row["id"]))
    previous_score = None
    for position, row in enumerate(rows, 1):
        score = (row["N"], row["B"], row["V"])
        if score != previous_score:
            rank = position
            previous_score = score
        row["rank"] = rank
    distribution = Counter(row["N"] for row in rows)
    return {"graph_source": GRAPH_URL, "graph_sha256": graph_hash,
            "graph_nodes": len(graph_nodes), "graph_edges": len(graph_edges),
            "excluded_turing_edges": sum(edge.get("turing", False) or edge.get("witness", True) is False
                                         for edge in graph_edges),
            "augmented_nodes": len(nodes), "baseline_bridge_edges": bridge_records,
            "question_count": len(rows), "scored_count": len(rows),
            "reviewed_count": sum(row["mapping_evidence"] is not None for row in rows),
            "N_distribution": {str(score): count for score, count in sorted(distribution.items())},
            "distance_discount": {"lambda": 0.5, "unit": "shortest witness-chain edge",
                                  "role": "diagnostic only; not the official ranking key"},
            "ranking_rule": "Provisional N descending, then B descending, then V (new variant pairs) descending; ID only sets display order within ties",
            "interpretation": "Hypothetical topology estimate under stated endpoint assumptions; not proof validity, literature openness, resource compatibility, or total research value.",
            "questions": rows}
