# Reduction Impact Atlas

This repository builds a static, conditional topology estimate for 76 frozen reduction questions. It is independent of both upstream checkouts. The live [ranking](https://ferrari-72.github.io/reduction-impact-atlas/) and [five AI bridge examples](https://ferrari-72.github.io/reduction-impact-atlas/pilot.html) link to the [calculation PDF](https://ferrari-72.github.io/reduction-impact-atlas/calculation.pdf).

**Start here:** [architecture and data boundaries](ARCHITECTURE.md) · [research workflow for new direct reductions](RESEARCH_WORKFLOW.md).

## Reproduce

Python 3.11 or newer is required. The ranking builder uses the standard library.

```powershell
python -m unittest -v test_ranker.py
python build.py
```

`dist/` contains the two pages, JSON evidence, frozen inputs, logo and methodology PDF. To regenerate the PDF, install the declared documentation dependency and run:

```powershell
uv sync --locked --group docs
uv run --locked --group docs python make_pdf.py
python build.py
```

The optional browser check requires Playwright and Chrome:

```powershell
uv sync --locked --group dev
uv run --locked --group dev python browser_check.py
```

Browser checks cover navigation, filtering, JavaScript errors, and 375px width. A browser-launch failure is a failed check; the unit tests do not substitute for it.

## Review and release

1. Review the frozen inputs and SHA-256 guards described in [ARCHITECTURE.md](ARCHITECTURE.md).
2. Run the tests and build commands above. Review the PDF after any methodology change.
3. Run `python package_release.py --output PATH_TO_NEW_EMPTY_DIRECTORY`. It creates a complete `reduction-impact-atlas/` subtree with a matching `source/` snapshot.
4. Commit only that subtree to the Pages repository. Do not copy `dist/` and source files separately.

The package command refuses to overwrite an existing target. It never edits either upstream checkout or the portfolio root. The five AI bridge proposals remain separate from the official ranking.

## Interpretation

The official sort key is descending `(N, B, V)`: newly reachable ordered problem-family pairs, fractional new concrete-variant coverage for already reachable family pairs, then all new concrete-variant pairs. `D_half` is a path-length diagnostic, not a sort key. Every question rule is hypothetical. The baseline includes ten documented directional definition bridges; exact-variant mappings have not passed review. Forty-nine questions tie at `(1,0,1)`, mostly because graph coverage is sparse. A topology rank is not a research-priority or proof-difficulty rank.
