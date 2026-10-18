"""Acceptance tests for the independent ranking build."""
import json
import random
import re
from collections import Counter
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from ranker import _paths, _score, build_report, render_page, sha256_file
from snapshot_board import make_snapshot
from build import build
from estimate import build_estimate_report
from pilot import build_pilot


ROOT = Path(__file__).parent


def question(qid, source, target, status="unsolved"):
    return {"id": qid, "slug": qid.lower(), "source": source, "target": target,
            "category": "Complexity open", "status": status}


class RankingTests(unittest.TestCase):
    def setUp(self):
        self.graph = {
            "nodes": [
                {"name": "A", "variant": {"v": 1}},
                {"name": "A", "variant": {"v": 2}},
                {"name": "B", "variant": {"v": 1}},
                {"name": "B", "variant": {"v": 2}},
                {"name": "C", "variant": {}},
            ],
            "edges": [{"source": 0, "target": 2}, {"source": 3, "target": 4}],
        }
        self.hash = "a" * 64

    def test_all_questions_remain_visible_with_explicit_unscored_reason(self):
        questions = [question("Q001", "A", "C"), question("Q002", "Unknown", "Other", "submitted")]
        report = build_report(self.graph, self.hash, questions, {"graph_sha256": self.hash, "entries": {}})
        self.assertEqual([row["id"] for row in report["questions"]], ["Q001", "Q002"])
        self.assertEqual(report["scored_count"], 0)
        self.assertTrue(all(row["N"] is None and row["B"] is None and row["reason"] for row in report["questions"]))
        self.assertEqual(report["questions"][1]["status"], "submitted")
        self.assertEqual(render_page(report).count('class="question-row"'), 2)

    def test_reviewed_variant_mapping_scores_and_sorts(self):
        questions = [question("Q001", "A", "B"), question("Q002", "B", "C")]
        mapping = {"graph_sha256": self.hash, "entries": {
            "Q001": {"source_node": 1, "target_node": 2, "source_label": "A", "target_label": "B", "evidence": "Reviewed exact variants."},
            "Q002": {"source_node": 2, "target_node": 4, "source_label": "B", "target_label": "C", "evidence": "Reviewed exact variants."},
        }}
        report = build_report(self.graph, self.hash, questions, mapping)
        rows = {row["id"]: row for row in report["questions"]}
        self.assertEqual((rows["Q001"]["N"], rows["Q001"]["B"]), (0, 0.25))
        self.assertEqual((rows["Q002"]["N"], rows["Q002"]["B"]), (1, 0.5))
        self.assertEqual(report["questions"][0]["id"], "Q002")
        self.assertEqual(report["scored_count"], 2)
        self.assertIn("candidate:Q002", rows["Q002"]["witnesses"][0]["path"])

    def test_stale_or_invalid_mapping_fails_closed(self):
        q = [question("Q001", "A", "B")]
        mapping = {"graph_sha256": "wrong", "entries": {}}
        with self.assertRaisesRegex(ValueError, "hash"):
            build_report(self.graph, self.hash, q, mapping)
        mapping = {"graph_sha256": self.hash, "entries": {"Q001": {
            "source_node": 0, "target_node": 9, "source_label": "A", "target_label": "B", "evidence": "review"}}}
        with self.assertRaisesRegex(ValueError, "node index"):
            build_report(self.graph, self.hash, q, mapping)
        mapping["entries"]["Q001"].update(target_node=2, evidence="")
        with self.assertRaisesRegex(ValueError, "evidence"):
            build_report(self.graph, self.hash, q, mapping)
        mapping["entries"]["Q001"].update(evidence="review", target_label="changed")
        with self.assertRaisesRegex(ValueError, "labels"):
            build_report(self.graph, self.hash, q, mapping)

    def test_direct_edge_is_unscored_not_discarded(self):
        q = [question("Q001", "A", "B")]
        mapping = {"graph_sha256": self.hash, "entries": {"Q001": {
            "source_node": 0, "target_node": 2, "source_label": "A", "target_label": "B", "evidence": "review"}}}
        row = build_report(self.graph, self.hash, q, mapping)["questions"][0]
        self.assertIsNone(row["N"])
        self.assertIn("already registered", row["reason"])

    def test_turing_edge_is_not_a_single_call_witness_path(self):
        nodes = [{"name": name, "variant": {}} for name in ("A", "B", "C")]
        edges = [{"source": 0, "target": 1, "turing": True, "witness": False},
                 {"source": 1, "target": 2, "turing": False, "witness": True}]
        paths = _paths(nodes, edges)
        self.assertNotIn(1, paths[0])
        self.assertNotIn(2, paths[0])
        self.assertEqual(paths[1][2], (1,))

    def test_real_snapshot_and_registry_coverage(self):
        graph = json.loads((ROOT / "data/reduction_graph.json").read_text(encoding="utf-8"))
        self.assertEqual((len(graph["nodes"]), len(graph["edges"])), (257, 344))
        questions = json.loads((ROOT / "data/questions.json").read_text(encoding="utf-8"))["questions"]
        self.assertEqual(len(questions), 76)
        report = build_report(graph, sha256_file(ROOT / "data/reduction_graph.json"), questions,
                              {"graph_sha256": sha256_file(ROOT / "data/reduction_graph.json"), "entries": {}})
        self.assertEqual(len(report["questions"]), 76)
        self.assertTrue(all(row["reason"] for row in report["questions"]))

    def test_board_import_is_a_standalone_snapshot(self):
        with TemporaryDirectory(dir=ROOT) as directory:
            path = Path(directory) / "registry"
            path.mkdir()
            (path / "example.json").write_text(json.dumps({
                "id": "Q001", "source": "A", "target": "B", "category": "Complexity open",
                "source_definition": "A inputs and outputs", "target_definition": "B inputs and outputs",
                "importance": "Conditional consequence", "literature_checked": "2026-10-01",
                "solutions": [{"status": "submitted"}]}), encoding="utf-8")
            snapshot = make_snapshot(path)
            self.assertEqual(snapshot["questions"][0]["solution_statuses"], ["submitted"])
            self.assertEqual(snapshot["questions"][0]["board_importance"], "Conditional consequence")
            self.assertEqual(snapshot["questions"][0]["slug"], "example")
            self.assertEqual(len(snapshot["registry_sha256"]), 64)

    def test_static_output_contains_its_frozen_inputs(self):
        with TemporaryDirectory(dir=ROOT) as directory:
            output = Path(directory) / "dist"
            report = build(output=output)
            self.assertEqual(report["question_count"], 76)
            self.assertEqual(sha256_file(output / "reduction_graph.json"), report["graph_sha256"])
            self.assertEqual(sha256_file(output / "bridges.json"), report["bridges_sha256"])
            self.assertEqual(sha256_file(output / "mappings.json"), report["mappings_sha256"])
            self.assertEqual(len(json.loads((output / "questions.json").read_text(encoding="utf-8"))["questions"]), 76)
            self.assertIn("new isolated node", (output / "index.html").read_text(encoding="utf-8"))

    def test_build_runs_with_only_standalone_files(self):
        with TemporaryDirectory(dir=ROOT) as directory:
            isolated = Path(directory)
            for name in ("build.py", "estimate.py", "ranker.py", "pilot.py"):
                shutil.copyfile(ROOT / name, isolated / name)
            (isolated / "data").mkdir()
            for name in ("reduction_graph.json", "questions.json", "mappings.json", "bridges.json", "pilot_bridges.json"):
                shutil.copyfile(ROOT / "data" / name, isolated / "data" / name)
            (isolated / "assets").mkdir()
            shutil.copyfile(ROOT / "assets/lab-mark.svg", isolated / "assets/lab-mark.svg")
            shutil.copyfile(ROOT / "assets/calculation.pdf", isolated / "assets/calculation.pdf")
            result = subprocess.run([sys.executable, "-E", str(isolated / "build.py")],
                                    cwd=isolated, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads((isolated / "dist" / "ranking.json").read_text(encoding="utf-8"))
            self.assertIn("76 scored", result.stdout)
            self.assertEqual((report["question_count"], report["scored_count"]), (76, 76))

    def test_page_escapes_question_text(self):
        q = [question("Q001", "<script>alert(1)</script>", "B")]
        report = build_report(self.graph, self.hash, q, {"graph_sha256": self.hash, "entries": {}})
        page = render_page(report)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)

    def test_board_importance_is_quoted_and_escaped(self):
        q = [question("Q001", "New source", "New target")]
        q[0]["board_importance"] = "<script>alert(1)</script>"
        q[0]["literature_checked"] = "2026-10-01"
        report = build_estimate_report(self.graph, self.hash, q,
                                       {"graph_sha256": self.hash, "entries": {}})
        page = render_page(report)
        self.assertIn("Board-stated importance", page)
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
        self.assertNotIn("<script>alert(1)</script>", page)

    def test_isolated_unverified_rule_has_one_conditional_relation(self):
        q = [question("Q001", "New source", "New target")]
        report = build_estimate_report(self.graph, self.hash, q,
                                       {"graph_sha256": self.hash, "entries": {}})
        row = report["questions"][0]
        self.assertEqual((row["N"], row["B"], row["V"]), (1, 0, 1))
        self.assertEqual((row["D_half"], row["direct_count"], row["transitive_count"]), (1, 1, 0))
        self.assertIn("new isolated", row["assumptions"])

    def test_name_based_connection_is_labelled_provisional(self):
        q = [question("Q001", "C", "New target")]
        report = build_estimate_report(self.graph, self.hash, q,
                                       {"graph_sha256": self.hash, "entries": {}})
        row = report["questions"][0]
        self.assertEqual(row["N"], 2)  # B2 and C can reach the new target.
        self.assertEqual((row["D_half"], row["direct_count"], row["transitive_count"]), (1.5, 1, 1))
        self.assertIn("name-only", row["assumptions"])

    def test_directional_baseline_bridge_changes_candidate_reachability(self):
        graph = {"nodes": [{"name": "Core"}, {"name": "K3"}],
                 "edges": [{"source": 0, "target": 1}]}
        q = [question("Q001", "3-SAT", "New target")]
        q[0]["source_definition"] = "at most three literals per clause"
        mappings = {"graph_sha256": self.hash, "entries": {}}
        bridge = {"graph_sha256": self.hash, "registry_sha256": "board-hash", "entries": [{
            "question_ids": ["Q001"], "side": "source", "label": "3-SAT", "graph_node": 1,
            "problem_family": "K3", "direction": "graph_to_board",
            "evidence": "exact-three formulas are a subset"}]}
        report = build_estimate_report(graph, self.hash, q, mappings, bridge, "board-hash")
        row = report["questions"][0]
        self.assertEqual(row["N"], 2)
        self.assertEqual({pair["source"] for pair in row["new_problem_pairs"]}, {"Core", "K3"})
        self.assertEqual(report["baseline_bridge_edges"][0]["edge_index"], 1)
        with self.assertRaisesRegex(ValueError, "hash"):
            build_estimate_report(graph, self.hash, q, mappings, bridge, "stale-board")

    def test_four_variant_gain_classes_partition_transitive_effect(self):
        graph = {"nodes": [{"name": name} for name in ("Up", "Source", "Target", "Down")],
                 "edges": [{"source": 0, "target": 1}, {"source": 2, "target": 3}]}
        q = [question("Q001", "Source", "Target")]
        report = build_estimate_report(graph, self.hash, q,
                                       {"graph_sha256": self.hash, "entries": {}})
        row = report["questions"][0]
        self.assertEqual((row["N"], row["V"], row["D_half"]), (4, 4, 2.25))
        self.assertEqual(row["variant_gain_breakdown"],
                         {"direct": 1, "upstream": 1, "downstream": 1, "both_sides": 1})

    def test_delta_matches_independent_before_after_closure(self):
        rng = random.Random(20261016)
        for _ in range(100):
            count = rng.randint(3, 8)
            nodes = [{"name": f"P{i // 2}"} for i in range(count)]
            edges = [{"source": u, "target": v} for u in range(count) for v in range(count)
                     if u != v and rng.random() < 0.2]
            before = _paths(nodes, edges)
            problems = [node["name"] for node in nodes]
            sizes = Counter(problems)
            old_pairs = {(problems[u], problems[v]) for u in range(count) for v in before[u]
                         if problems[u] != problems[v]}
            a, b = rng.sample(range(count), 2)
            N, B, pairs, witnesses = _score(a, b, nodes, before, old_pairs, sizes)
            after = _paths(nodes, edges + [{"source": a, "target": b}])
            delta = {(u, v) for u in range(count) for v in after[u]
                     if u != v and v not in before[u]}
            expected_pairs = {(problems[u], problems[v]) for u, v in delta
                              if problems[u] != problems[v]} - old_pairs
            old_covered = Counter((problems[u], problems[v]) for u in range(count)
                                  for v in before[u] if problems[u] != problems[v])
            new_covered = Counter((problems[u], problems[v]) for u in range(count)
                                  for v in after[u] if problems[u] != problems[v])
            expected_B = sum((new_covered[pair] - old_covered[pair]) /
                             (sizes[pair[0]] * sizes[pair[1]]) for pair in old_pairs)
            self.assertEqual((N, pairs), (len(expected_pairs), sorted(expected_pairs)))
            self.assertAlmostEqual(B, expected_B, places=10)
            self.assertEqual({(item["source_node"], item["target_node"]) for item in witnesses}, delta)

    def test_all_frozen_questions_receive_an_estimate(self):
        graph = json.loads((ROOT / "data/reduction_graph.json").read_text(encoding="utf-8"))
        questions = json.loads((ROOT / "data/questions.json").read_text(encoding="utf-8"))["questions"]
        digest = sha256_file(ROOT / "data/reduction_graph.json")
        report = build_estimate_report(graph, digest, questions,
                                       {"graph_sha256": digest, "entries": {}})
        self.assertEqual((report["question_count"], report["scored_count"]), (76, 76))
        self.assertEqual(sum(bool(row["board_importance"]) for row in report["questions"]), 76)
        self.assertTrue(all(row["assumptions"] for row in report["questions"]))
        self.assertEqual(report["N_distribution"]["1"], 69)
        self.assertEqual({row["rank"] for row in report["questions"] if row["N"] == 1}, {8})

    def test_frozen_bridges_raise_supported_3sat_questions(self):
        graph = json.loads((ROOT / "data/reduction_graph.json").read_text(encoding="utf-8"))
        board = json.loads((ROOT / "data/questions.json").read_text(encoding="utf-8"))
        bridge = json.loads((ROOT / "data/bridges.json").read_text(encoding="utf-8"))
        digest = sha256_file(ROOT / "data/reduction_graph.json")
        report = build_estimate_report(graph, digest, board["questions"],
                                       {"graph_sha256": digest, "entries": {}},
                                       bridge, board["registry_sha256"])
        self.assertEqual(len(report["baseline_bridge_edges"]), 10)
        rows = {row["id"]: row for row in report["questions"]}
        self.assertGreater(rows["Q010"]["N"], 1)
        self.assertIn("baseline bridge", rows["Q010"]["assumptions"])
        self.assertEqual(report["excluded_turing_edges"], 22)
        self.assertEqual((rows["Q042"]["N"], rows["Q042"]["V"]), (5, 12))
        self.assertEqual(rows["Q042"]["D_half"], 1.5625)
        self.assertEqual((rows["Q055"]["N"], rows["Q055"]["V"]), (5, 12))
        self.assertEqual(rows["Q055"]["rank"], rows["Q056"]["rank"])
        self.assertEqual((rows["Q041"]["N"], rows["Q041"]["V"]), (1, 2))
        self.assertEqual(rows["Q041"]["rank"], 27)
        self.assertEqual(rows["Q036"]["N"], 1)
        self.assertTrue(any(edge["direction"] == "board_to_graph" and "Q036" in edge["question_ids"]
                            for edge in report["baseline_bridge_edges"]))

    def test_ai_bridge_pilots_are_isolated_from_official_ranking(self):
        with TemporaryDirectory(dir=ROOT) as directory:
            output = Path(directory) / "dist"
            build(output=output)
            baseline_hash = sha256_file(output / "ranking.json")
            bridges_hash = sha256_file(output / "bridges.json")
            report = build_pilot(output=output)
            self.assertEqual(sha256_file(output / "ranking.json"), baseline_hash)
            self.assertEqual(sha256_file(output / "bridges.json"), bridges_hash)
            cases = {case["id"]: case for case in report["cases"]}
            self.assertEqual(set(cases), {"Q001", "Q004", "Q053", "Q054", "Q057"})
            self.assertEqual((cases["Q054"]["baseline"]["N"], cases["Q054"]["baseline"]["B"],
                              cases["Q054"]["baseline"]["V"]), (4, 0.277777777778, 19))
            self.assertEqual((cases["Q054"]["scenario"]["N"], cases["Q054"]["scenario"]["B"],
                              cases["Q054"]["scenario"]["V"]), (4, 0, 11))
            self.assertEqual((cases["Q001"]["baseline"]["N"], cases["Q001"]["scenario"]["N"]), (1, 94))
            self.assertEqual((cases["Q057"]["baseline"]["V"], cases["Q057"]["scenario"]["V"]), (1, 119))
            self.assertEqual(cases["Q057"]["scenario"]["N"], 94)
            self.assertAlmostEqual(cases["Q001"]["scenario"]["D_half"], 8.8671875)
            self.assertAlmostEqual(cases["Q057"]["scenario"]["D_half"], 3.404296875)
            self.assertEqual((cases["Q001"]["scenario"]["direct_count"],
                              cases["Q001"]["scenario"]["transitive_count"]), (1, 93))
            self.assertEqual(cases["Q001"]["scenario"]["variant_gain_breakdown"],
                             {"direct": 1, "upstream": 0, "downstream": 117, "both_sides": 0})
            targets = [{pair["target"] for pair in cases[qid]["scenario"]["new_problem_pairs"]}
                       for qid in ("Q001", "Q057")]
            self.assertEqual(targets[0], targets[1])
            self.assertEqual(len(targets[0]), 94)
            self.assertTrue(all(case["review_state"].startswith("AI-proposed") for case in cases.values()))
            for case in cases.values():
                self.assertEqual(case["fixed_projection"],
                                 {case["id"]: {case["bridge"]["side"]: case["bridge"]["problem_family"]}})
                self.assertEqual({k: case["baseline"][k] for k in ("N", "B", "V")},
                                 {k: case["fixed_projection_baseline"][k] for k in ("N", "B", "V")})
            main = (output / "index.html").read_text(encoding="utf-8")
            pilot_page = (output / "pilot.html").read_text(encoding="utf-8")
            self.assertIn('id="calculation"', main)
            self.assertIn('href="calculation.pdf"', main)
            self.assertIn('href="pilot.html"', main)
            self.assertNotIn('N(r) =', main)
            self.assertNotIn('class="summary ai-pilot"', main)
            self.assertIn('These 5 bridge scenarios are isolated experiments', pilot_page)
            self.assertIn('Q054 · AI-proposed scenario', pilot_page)
            self.assertEqual(pilot_page.count('class="summary ai-pilot"'), 5)
            self.assertIn('href="index.html"', pilot_page)
            self.assertIn('href="calculation.pdf"', pilot_page)
            self.assertTrue((output / "calculation.pdf").read_bytes().startswith(b"%PDF"))
            self.assertIsNone(re.search(r'[\u4e00-\u9fff]', main))
            self.assertIsNone(re.search(r'[\u4e00-\u9fff]', pilot_page))
            self.assertIn('href="https://codingthrust.github.io/problem-reductions/"', main)


if __name__ == "__main__":
    unittest.main()
