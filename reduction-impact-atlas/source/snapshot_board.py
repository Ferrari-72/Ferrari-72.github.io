"""Copy only public question metadata from an external board checkout."""
import argparse
import hashlib
import json
from pathlib import Path


FIELDS = ("id", "source", "target", "source_definition", "target_definition", "category", "solutions")


def make_snapshot(registry):
    directory = Path(registry)
    paths = sorted(directory.glob("*.json"))
    if not paths:
        raise ValueError("no registry JSON files found")
    digest = hashlib.sha256()
    questions = []
    for path in paths:
        raw = path.read_bytes()
        digest.update(path.name.encode("utf-8") + b"\0" + raw)
        record = json.loads(raw)
        for field in FIELDS:
            if field not in record:
                raise ValueError(f"{path.name}: missing {field}")
        questions.append({"id": record["id"], "slug": path.stem,
                          "source": record["source"], "target": record["target"],
                          "source_definition": record["source_definition"],
                          "target_definition": record["target_definition"],
                          "board_importance": record.get("importance", ""),
                          "literature_checked": record.get("literature_checked"),
                          "category": record["category"],
                          "solution_statuses": [s["status"] for s in record["solutions"]]})
    questions.sort(key=lambda q: int(q["id"][1:]))
    return {"source": "https://github.com/GiggleLiu/autoresearch-gadgets/tree/main/registry",
            "registry_sha256": digest.hexdigest(), "questions": questions}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("registry", type=Path, help="External checkout's registry directory")
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "data/questions.json")
    args = parser.parse_args()
    result = make_snapshot(args.registry)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Snapshotted {len(result['questions'])} questions: {args.output}")


if __name__ == "__main__":
    main()
