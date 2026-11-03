"""Package the Pages subtree and a matching, standalone source snapshot."""

import argparse
from pathlib import Path
from shutil import copy2

from build import build


ROOT = Path(__file__).parent
SITE_FILES = (
    "index.html", "pilot.html", "ranking.json", "pilot.json",
    "reduction_graph.json", "questions.json", "bridges.json",
    "mappings.json", "pilot_bridges.json", "lab-mark.svg",
    "calculation.pdf",
    "research.html", "research.json", "research_candidates.json", "research-method.pdf",
)
SOURCE_FILES = (
    "README.md", "ARCHITECTURE.md", "RESEARCH_WORKFLOW.md",
    "build.py", "estimate.py", "ranker.py", "pilot.py",
    "snapshot_board.py", "make_pdf.py", "package_release.py",
    "test_ranker.py", "browser_check.py", "pyproject.toml", "uv.lock",
    "research.py", "make_research_pdf.py",
)
DATA_FILES = (
    "reduction_graph.json", "questions.json", "bridges.json",
    "mappings.json", "pilot_bridges.json",
    "research_candidates.json",
)
ASSET_FILES = ("lab-mark.svg", "calculation.pdf", "research-method.pdf")


def package_release(output=ROOT / "release", build_output=ROOT / "dist"):
    """Create one reviewable directory without changing either upstream repo."""
    output = Path(output)
    if output.exists():
        raise FileExistsError(f"release target already exists: {output}")
    build(output=build_output)
    site = output / "reduction-impact-atlas"
    source = site / "source"
    source.mkdir(parents=True)
    for name in SITE_FILES:
        copy2(Path(build_output) / name, site / name)
    for name in SOURCE_FILES:
        copy2(ROOT / name, source / name)
    for folder, names in (("data", DATA_FILES), ("assets", ASSET_FILES)):
        (source / folder).mkdir()
        for name in names:
            copy2(ROOT / folder / name, source / folder / name)
    return site


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "release")
    args = parser.parse_args()
    print(f"Packaged {package_release(output=args.output)}")


if __name__ == "__main__":
    main()
