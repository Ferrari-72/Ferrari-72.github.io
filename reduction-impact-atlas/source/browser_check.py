"""End-to-end checks for the generated static page (requires Playwright + Chrome)."""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright, expect


ROOT = Path(__file__).parent
report = json.loads((ROOT / "dist/ranking.json").read_text(encoding="utf-8"))
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto((ROOT / "dist/index.html").resolve().as_uri())
    assert page.locator(".brand-mark").evaluate("image => image.complete && image.naturalWidth > 0")
    expect(page.locator(".question-row")).to_have_count(report["question_count"])
    expect(page.get_by_text(f"{report['question_count']} open rules", exact=False)).to_be_visible()
    expect(page.locator(".question-row[data-scored='true']")).to_have_count(report["scored_count"])
    expect(page.locator(".question-row[data-scored='false']")).to_have_count(report["question_count"] - report["scored_count"])
    pilot = json.loads((ROOT / "dist/pilot.json").read_text(encoding="utf-8"))
    expect(page.locator("#calculation")).to_be_visible()
    assert page.locator("a[href='calculation.pdf']").count() >= 1
    assert page.locator("a[href='pilot.html']").count() >= 1
    assert page.locator("a[href='https://codingthrust.github.io/problem-reductions/']").count() == 1
    first = page.locator(".question-row").first
    first.locator(".relations summary").click()
    expect(first.locator(".relations li")).to_have_count(report["questions"][0]["N"])
    page.get_by_label("Search questions").fill("Q056")
    expect(page.locator(".question-row:visible")).to_have_count(1)
    expect(page.locator(".question-row:visible")).to_contain_text("Vertex Cover")
    page.get_by_label("Search questions").fill("")
    page.get_by_label("Status").select_option("submitted")
    expect(page.locator(".question-row:visible")).to_have_count(18)
    page.get_by_label("Status").select_option("all")
    page.get_by_label("Score availability").select_option("false")
    expect(page.locator(".question-row:visible")).to_have_count(report["question_count"] - report["scored_count"])
    page.get_by_label("Score availability").select_option("all")
    for width in (1280, 375):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
        page.evaluate("window.scrollTo(0, 0)")
        page.screenshot(path=str(ROOT / f"dist/check-{width}.png"), full_page=False)
    page.goto((ROOT / "dist/pilot.html").resolve().as_uri())
    expect(page.locator("#pilots .ai-pilot")).to_have_count(5)
    expect(page.locator("#pilots .ai-pilot").first).to_contain_text("B 0.277778")
    expect(page.locator("#pilots .ai-pilot").first).to_contain_text("B 0 · V 11")
    page.locator("#pilots .ai-pilot").nth(1).locator("details summary").click()
    expect(page.locator("#pilots .ai-pilot").nth(1).locator("details li")).to_have_count(8)
    page.locator("nav a[href='index.html']").click()
    expect(page.locator(".question-row")).to_have_count(report["question_count"])
    page.goto((ROOT / "dist/pilot.html").resolve().as_uri())
    for width in (1280, 375):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
    page.goto((ROOT / "dist/research.html").resolve().as_uri())
    expect(page.locator(".research-card")).to_have_count(20)
    survey=json.loads((ROOT/'dist/research.json').read_text(encoding='utf-8'))
    assert page.locator('.research-card td:first-child').all_text_contents() == [r['id'] for r in survey['questions']]
    assert all(a['marginal']['S'] >= b['marginal']['S'] for a,b in zip(survey['questions'],survey['questions'][1:]))
    expect(page.locator("thead")).to_contain_text("S / N / U / D")
    assert page.locator("a[href='research-method.pdf']").count() >= 1
    expect(page.locator("table")).to_have_count(1)
    expect(page.locator(".research-card details[open]")).to_have_count(0)
    page.locator(".research-card").first.locator("details summary").first.click()
    assert page.locator(".research-card").first.locator("details li").count() > 0
    for width in (1280, 375):
        page.set_viewport_size({"width": width, "height": 900})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
        page.locator(".research-card details").first.evaluate("el => el.open = false")
        last=page.locator(".research-card td").nth(3).bounding_box()
        assert last["x"]+last["width"] <= width, "research scores must fit viewport"
        page.evaluate("window.scrollTo(0, 0)")
        page.screenshot(path=str(ROOT / f"dist/research-{width}.png"), full_page=False)
    page.locator('#visual-analysis > summary').click()
    expect(page.locator('#score-chart g')).to_have_count(20)
    page.get_by_label('Inspect record').select_option('D004')
    expect(page.locator('#analysis-stats')).to_contain_text('S 9.367')
    expect(page.locator('#hop-total')).to_contain_text('95')
    expect(page.locator('#witness-path .assumed')).to_have_count(1)
    expect(page.locator('#witness-path .known')).to_have_count(1)
    page.get_by_label('Graph view').select_option('before')
    expect(page.locator('#witness-path .missing')).to_have_count(1)
    page.get_by_label('Graph view').select_option('after')
    expect(page.locator('#witness-path .missing')).to_have_count(0)
    page.get_by_label('Chart measure').select_option('N')
    page.locator('#score-chart g').first.press('Enter')
    expect(page.locator('#analysis-title')).to_contain_text('D004')
    page.get_by_label('Inspect record').select_option('R001')
    expect(page.locator('#witness-path .assumed')).to_have_count(0)
    expect(page.locator('#analysis-context')).to_contain_text('No open rule is assumed')
    for row in survey['questions']:
        page.get_by_label('Inspect record').select_option(row['id'])
        expect(page.locator('#hop-total')).to_contain_text(f"= {row['marginal']['S']:.3f};")
    for width in (1280,375):
        page.set_viewport_size({'width':width,'height':900})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.locator('#visual-analysis').scroll_into_view_if_needed()
        page.screenshot(path=str(ROOT/f'dist/analysis-{width}.png'),full_page=False)
    assert not errors, errors
    browser.close()
print("Browser checks passed")
