"""Rebuild the versioned English calculation PDF asset."""
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
P=Path(__file__).parent/'assets/calculation.pdf'
blue=colors.HexColor('#123B67'); pale=colors.HexColor('#EAF3FB')
s=getSampleStyleSheet()
s.add(ParagraphStyle(name='T',parent=s['Title'],fontName='Helvetica-Bold',fontSize=20,leading=25,textColor=blue,spaceAfter=12))
s.add(ParagraphStyle(name='H',parent=s['Heading2'],fontName='Helvetica-Bold',fontSize=12,leading=16,textColor=blue,spaceBefore=15,spaceAfter=6))
s.add(ParagraphStyle(name='B',parent=s['BodyText'],fontName='Helvetica',fontSize=9.5,leading=14,spaceAfter=8))
s.add(ParagraphStyle(name='F',parent=s['BodyText'],fontName='Courier',fontSize=8.7,leading=14,backColor=pale,borderPadding=7,spaceBefore=4,spaceAfter=10))
story=[]
def add(style,text): story.append(Paragraph(text,s[style]))
add('T','Reduction Impact Atlas')
add('B','<b>Calculation method - project methodology</b><br/>Version: 2026-10-17. This method is authored by the Atlas project, not issued by the upstream graph project.')
add('B','Scope: 76 frozen board questions. Each unproved rule is added separately to the same baseline. The resulting score describes conditional graph reachability, not proof difficulty, novelty, or full research value.')
add('H','1. Frozen inputs and path rules')
add('B','The graph snapshot has 257 exact variants and 344 directed source edges. The one-call witness model excludes 22 Turing or non-witness-preserving edges. The baseline adds 10 documented directional definition bridges. Unique name matches are provisional; zero exact-variant mappings have passed review. The site publishes frozen inputs, hashes, bridge evidence, source code and tests.')
add('B','A directed path counts under the stated one-call, witness-preserving composition model. For each question, its problem-family projection stays fixed in the before/after comparison. Graph-external endpoints begin isolated unless a documented bridge connects them.')
add('H','2. Official structural measures')
add('B','Let Rv(G) be the reachable ordered variant pairs in baseline G. Let Rp(G) be their projection to ordered problem-family pairs, excluding same-family pairs. Compare G with G+r for candidate rule r.')
add('F','N(r) = | Rp(G+r) \\ Rp(G) |')
add('B','N counts newly reachable ordered family pairs once, even if several paths witness a pair.')
add('F','B(r) = sum over (P,Q) in Rp(G) of [qPQ(G+r) - qPQ(G)]')
add('B','qPQ(G) is the fraction of the |VP| x |VQ| concrete variant pairs reachable between existing families P and Q. B is fractional coverage gain for family relations already reachable in G. New family relations do not enter B.')
add('F','V(r) = | Rv(G+r) \\ Rv(G) |')
add('B','V counts new concrete variant pairs. Official sort: descending N, then B, then V. Equal triples share a rank; question ID only fixes order within a tie. There is no weighted sum or 0-100 score.')
add('H','3. Transitive paths and diagnostic discount')
add('B','N separates direct and transitive family pairs. V separates candidate, old-upstream, old-downstream, and both-sides variant pairs. Published results include a witness chain for each newly reachable family pair.')
add('F','D_half(r) = sum over new family pairs (P,Q) of 0.5^(h(P,Q)-1)')
add('B','h is the shortest witness-chain edge count, including the candidate and any definition bridge. Each extra edge halves this diagnostic weight. D_half does not change the official sort and depends on graph representation.')
story.append(PageBreak())
add('H','4. Five isolated AI bridge examples')
add('B','The examples page compares five selected questions one at a time: Q001, Q004, Q053, Q054 and Q057. Each scenario adds one AI-proposed semantic bridge under a fixed problem-family projection. These five bridge proposals span different problem families; all require independent review. None changes the official ranking.')
add('B','Q054 is a useful check. Official N=4, B=0.277778, V=19. Its proposed reverse bridge gives marginal N=4, B=0, V=11. More baseline reachability leaves less new reachability for the candidate; no existing path is removed. Q001 and Q057 illustrate hub amplification: each target-side bridge gives N=94, with 1 direct and 93 transitive family relations. These are not 94 independent research results.')
add('H','5. Reproduction and review limits')
add('B','The published source directory contains the frozen inputs and the static PDF asset. Run <font name="Courier">python build.py</font> to reproduce the pages and JSON results without checking out either upstream repository. Run <font name="Courier">python make_pdf.py</font> with ReportLab to regenerate this PDF. Automated tests check graph calculations, witness paths, bridge isolation, input hashes and browser behavior.')
add('B','Review the direction, promise conditions, input encoding, witness recovery and resource bounds of each proposed bridge. A missing edge does not show that a reduction is absent from the literature. Sparse graph coverage leaves many ties and limits what the ranking can distinguish.')
add('H','Sources and data')
add('B','<link href="https://ferrari-72.github.io/reduction-impact-atlas/" color="#1764a3">Atlas ranking</link> | <link href="https://ferrari-72.github.io/reduction-impact-atlas/pilot.html" color="#1764a3">AI examples</link> | <link href="https://github.com/Ferrari-72/Ferrari-72.github.io/tree/main/reduction-impact-atlas/source" color="#1764a3">Source and inputs</link> | <link href="https://codingthrust.github.io/problem-reductions/" color="#1764a3">Upstream graph</link>')
def footer(c,d):
 c.saveState(); c.setStrokeColor(colors.HexColor('#BBD1E3')); c.line(42,42,553,42); c.setFont('Helvetica',8); c.setFillColor(blue); c.drawString(42,30,'Reduction Impact Atlas | Project methodology'); c.drawRightString(553,30,str(d.page)); c.restoreState()
SimpleDocTemplate(str(P),pagesize=A4,rightMargin=42,leftMargin=42,topMargin=45,bottomMargin=55).build(story,onFirstPage=footer,onLaterPages=footer)
print(P)
