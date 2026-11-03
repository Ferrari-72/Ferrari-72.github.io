"""Regenerate the research-scenario methodology PDF; requires ReportLab."""
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
ROOT=Path(__file__).parent
styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='T',fontName='Helvetica-Bold',fontSize=21,leading=26,textColor=colors.HexColor('#123B67'),spaceAfter=18))
styles.add(ParagraphStyle(name='H',fontName='Helvetica-Bold',fontSize=12,leading=17,textColor=colors.HexColor('#123B67'),spaceBefore=15,spaceAfter=8))
styles.add(ParagraphStyle(name='B',fontName='Helvetica',fontSize=10,leading=15,spaceAfter=10))
story=[]
def add(kind,text):story.append(Paragraph(text,styles[kind]))
add('T','Research routes: calculation and review scope')
add('B','Reduction Impact Atlas | Research snapshot 2026-11-02. This appendix is project-authored. It supplements the original calculation PDF and does not claim endorsement by the source graph project.')
add('H','1. What the twenty entries mean')
add('B','There are ten new direct-route questions and ten downstream-route proposals. They share ten newly specified tasks; this is not twenty independent unresolved complexity classifications. Primary references establish an unresolved classification or remaining algorithmic gap. The ordered reduction routes are our proposals and have no construction or independent semantic review yet.')
add('B','Most new direct routes ask whether a promised search task admits a polynomial one-call reduction to 2-SAT, including witness recovery and preservation of NO-SOLUTION. The planar two-bend CPG entry instead asks for a search-preserving 3-SAT hardness route. Neither a general SAT encoding nor an unresolved classification proves either proposed route.')
add('H','2. Frozen graph and projections')
add('B','The baseline is the same frozen graph and documented board bridges used by the official ranking. It is copied, never edited. Turing and non-witness-preserving edges are excluded. Board endpoint matches retain their provisional status. All new task nodes exist in every comparison graph. Ten documented polynomial-verifier-to-SAT support routes prevent treating these NP search tasks as isolated. Their graph adapters await review. These support routes belong only to the temporary research baseline. Variant counts and the family projection stay fixed.')
add('H','3. Single-edge and two-assumption scenarios')
add('B','For a new direct route r, compare G with G+r. For a downstream route s: B -> C, first assume its board parent p: A -> B. Report the marginal gain from G+p to G+p+s and separately the combined gain from G to G+p+s. The parent is an unproved assumption, not a baseline fact. Each output witness lists every assumption it uses.')
add('B','Do not add marginal and combined counts. They have different reference graphs. Do not compare a one-assumption rank with a two-assumption rank as if they measured the same evidence. The website therefore ranks the two groups separately.')
story.append(PageBreak())
add('H','4. Measures and ordering')
add('B','Let Rv(H) be directed reachable variant pairs in H, excluding identical endpoints. Let Rp(H) be their fixed projection to distinct problem families. Given before and after graphs H0 and H1, N = |Rp(H1) minus Rp(H0)| and V = |Rv(H1) minus Rv(H0)|.')
add('B','For each family pair already reachable in H0, take its newly reachable concrete variant-pair count divided by the fixed product of source and target family sizes. Sum these fractions to obtain B. A new family pair is counted in N, not again in B. Exact rational B is included in JSON.')
add('B','Within each group, order by descending marginal (N,B,V). Equal triples share a rank. D_half sums 0.5^(h-1) over new family pairs, where h is the shortest complete witness-chain length including every assumption edge. It is diagnostic only and depends on graph representation.')
add('H','5. Literature and plausibility limits')
add('B','The catalogue records primary sources, section locators, search queries, check date and excluded solved cases. No later resolution found in a scoped search is not proof that a problem is still open. The circle-coloring, P8-free coloring and P7-free independence families have quasipolynomial algorithms in cited work; a hardness chain to them can imply quasipolynomial SAT and conflict with ETH. Such a conflict is a research obstacle, not evidence for the proposed edge.')
add('B','Downstream pairings are speculative structural analogies. A precise construction, restrictions, resource bound, output recovery and impossibility checks remain necessary. Large counts can arise from 2-SAT/SAT hubs. Ties can arise from isolated nodes. Neither is a validated research-priority judgement. After including verifier-to-SAT routes, nine proposed polynomial algorithms have N=0, B=1/9 and V=1. This is a limitation of the structure metric, not absence of algorithmic value.')
add('H','6. Reproduction and evidence')
add('B','Run python build.py and python -m unittest -v test_ranker.py from the published source. research_candidates.json records task definitions, proposed edges and primary references. research.json records frozen-input hashes, exact assumptions, marginal and combined scores, and all new family-pair witnesses. The original ranking.json is unchanged by research proposals.')
add('B','<link href="https://ferrari-72.github.io/reduction-impact-atlas/research.html" color="#1764a3">Research page</link> | <link href="https://ferrari-72.github.io/reduction-impact-atlas/research_candidates.json" color="#1764a3">Research records</link> | <link href="https://github.com/Ferrari-72/Ferrari-72.github.io/tree/main/reduction-impact-atlas/source" color="#1764a3">Source and tests</link>')
def footer(c,d):
 c.saveState();c.setStrokeColor(colors.HexColor('#BBD1E3'));c.line(42,42,553,42);c.setFont('Helvetica',8);c.drawString(42,29,'Reduction Impact Atlas | Research methodology');c.drawRightString(553,29,str(d.page));c.restoreState()
SimpleDocTemplate(str(ROOT/'assets/research-method.pdf'),pagesize=A4,leftMargin=42,rightMargin=42,topMargin=44,bottomMargin=60).build(story,onFirstPage=footer,onLaterPages=footer)
