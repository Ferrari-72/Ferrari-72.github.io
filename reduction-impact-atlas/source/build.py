"""Build a standalone static ranking site from frozen public snapshots."""
import argparse
import json
from pathlib import Path
from shutil import copyfile

from estimate import build_estimate_report
from pilot import build_pilot, render_pilot_section
from ranker import render_page, sha256_file


ROOT = Path(__file__).parent


def build(graph_path=ROOT / "data/reduction_graph.json",
          questions_path=ROOT / "data/questions.json",
          mappings_path=ROOT / "data/mappings.json",
          bridges_path=ROOT / "data/bridges.json",
          output=ROOT / "dist"):
    graph = json.loads(Path(graph_path).read_text(encoding="utf-8"))
    board = json.loads(Path(questions_path).read_text(encoding="utf-8"))
    mappings = json.loads(Path(mappings_path).read_text(encoding="utf-8"))
    bridges = json.loads(Path(bridges_path).read_text(encoding="utf-8"))
    report = build_estimate_report(graph, sha256_file(graph_path), board["questions"], mappings,
                                   bridges, board["registry_sha256"])
    report["registry_sha256"] = board["registry_sha256"]
    report["bridges_sha256"] = sha256_file(bridges_path)
    report["mappings_sha256"] = sha256_file(mappings_path)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    (output / "ranking.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    copyfile(graph_path, output / "reduction_graph.json")
    copyfile(questions_path, output / "questions.json")
    copyfile(bridges_path, output / "bridges.json")
    copyfile(mappings_path, output / "mappings.json")
    copyfile(ROOT / "assets/lab-mark.svg", output / "lab-mark.svg")
    pilot_report = build_pilot(output)
    (output / "index.html").write_text(
        render_page(report, render_pilot_section(pilot_report, report)), encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, default=ROOT / "data/reduction_graph.json")
    parser.add_argument("--questions", type=Path, default=ROOT / "data/questions.json")
    parser.add_argument("--mappings", type=Path, default=ROOT / "data/mappings.json")
    parser.add_argument("--bridges", type=Path, default=ROOT / "data/bridges.json")
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    args = parser.parse_args()
    report = build(args.graph, args.questions, args.mappings, args.bridges, args.output)
    print(f"Built {report['question_count']} questions; {report['scored_count']} scored; output: {args.output}")


if __name__ == "__main__":
    main()
