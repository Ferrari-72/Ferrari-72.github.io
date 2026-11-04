"""Build the methodology PDF for surveyed existing reductions."""
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate,Paragraph,PageBreak
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
ROOT=Path(__file__).parent
s=getSampleStyleSheet()
for name,size,leading in [('T',20,25),('H',12,17),('B',10,15)]:
 s.add(ParagraphStyle(name=name,fontName='Helvetica-Bold' if name!='B' else 'Helvetica',fontSize=size,leading=leading,spaceBefore=12 if name=='H' else 0,spaceAfter=10,textColor=colors.HexColor('#123B67') if name!='B' else colors.black))
story=[]
def p(kind,text):story.append(Paragraph(text,s[kind]))
p('T','Existing reductions: survey and calculation')
p('B','Reduction Impact Atlas | Corrected scope, 2026-11-04. This project-authored appendix replaces the earlier algorithm-goal scenario appendix.')
p('H','1. Survey existing relations')
p('B','The catalogue contains ten existing direct relations from newly recorded task variants, and ten existing downstream relations from frozen board targets. These are promise embeddings and applications of the polynomial-verifier-to-SAT construction. They are not twenty separate new theorems. The earlier invented efficient-algorithm routes and speculative downstream pairings are withdrawn.')
p('B','A restriction embedding submits the same instance to a general problem and recovers the returned witness unchanged. A verifier encoding constructs a CNF formula for a bounded certificate and its polynomial-time verifier. A satisfying assignment supplies the original certificate; unsatisfiability preserves NO-SOLUTION. The target is unrestricted SAT, with no claim of an efficient source algorithm.')
p('H','2. Known relationship versus reviewed adapter')
p('B','Each record supplies a source definition, certificate bound, verifier or embedding argument, recovery rule and references. The theoretical inclusion may be known while its precise graph-model adapter still awaits independent review. Do not infer an edge merely from similar names. A binary budget does not by itself bound certificate length; the records explain caps using the explicit instance size.')
p('H','3. Keep the original graph frozen')
p('B','Calculations use copied graph nodes, board endpoints and documented baseline bridges. Turing and non-witness-preserving edges remain excluded. A surveyed known edge is inserted only in the temporary comparison graph. Other surveyed edges are not accumulated into the baseline. Unrelated research records therefore cannot create extra paths for the current row. Endpoint and family projection remain fixed in each comparison.')
p('H','4. Two different outputs')
p('B','For a direct known relation k, report coverage gain between G and G+k. For a downstream relation k: B to C and an open board parent p: A to B, first form G+k, then evaluate the parent by comparing G+k with G+k+p. Only p is hypothetical. Also report the parent impact in G and the coverage gain of k alone. The merged table sorts all records numerically by S, N, B and V, with shared ranks for equal tuples. Each row retains its comparison type: this is a score order, not a shared research-priority scale.')
story.append(PageBreak())
p('H','5. Measures and paths')
p('B','For the stated before/after graphs H0 and H1, let Rv be reachable ordered variant pairs excluding identical endpoints, and Rp their fixed projection to distinct problem families. N counts Rp(H1) minus Rp(H0). V counts Rv(H1) minus Rv(H0).')
p('B','B sums new variant coverage only for family pairs already reachable in H0. For each such pair, divide its new concrete variant pairs by the fixed product of source and target family sizes. B is a sum of coverage fractions, not a probability or a research-value scale. JSON includes exact fractions.')
p('B','All records sort together by descending S, then N, B, V; equal tuples share a rank. S sums 0.5^(h-1) over new family pairs, where h is the shortest witness length including the evaluated rule and all known edges. N is an unweighted count; S is path-weighted, not N times a constant. D_half remains a compatibility alias. JSON includes exact S fractions and sensitivity at decay 0.25, 0.5 and 0.75. U counts upstream families reaching the evaluated source, D downstream families reachable from its target, excluding the corresponding endpoint family. Use the before graph: G for direct rows and G+k for parent rows. These are explanatory counts, not score terms. Every witness distinguishes known and assumed edges.')
p('H','6. Attribution example')
p('B','Suppose G has X to A, the literature supplies B to C, and A to B is the open candidate. Adding the known downstream relation alone creates B to C. Assuming the candidate afterward creates A to B, X to B, A to C and X to C: parent impact N=4 and S=2.25 (lengths 1, 2, 2, 3), with U=1 and D=1. Without the known downstream relation its impact is N=2. The combined gain relative to G is N=5. These values are reported separately and must not be added.')
p('H','7. Review and reproduction')
p('B','Known does not imply new to the literature. A missing graph edge is a coverage gap, not evidence of an open mathematical problem. Generic SAT encodings can create large hub-based counts; inclusion edges can be routine. Neither is a research-priority score. The frozen inputs are unchanged; the 76-question display now ranks by S first.')
p('B','Run python build.py and python -m unittest -v test_ranker.py from the published source. research_candidates.json contains relation arguments and references. research.json contains hashes, known-edge records, parent assumptions and paths. The tests check isolation, witness continuity, fractional coverage and source-package rebuilds.')
p('B','<link href="https://doi.org/10.1145/800157.805047" color="#1764a3">Cook: polynomial computation encoding</link> | <link href="https://ferrari-72.github.io/reduction-impact-atlas/research.html" color="#1764a3">Corrected survey page</link> | <link href="https://ferrari-72.github.io/reduction-impact-atlas/research_candidates.json" color="#1764a3">Evidence records</link>')
def footer(c,d):
 c.saveState();c.setStrokeColor(colors.HexColor('#BBD1E3'));c.line(42,42,553,42);c.setFont('Helvetica',8);c.drawString(42,29,'Reduction Impact Atlas | Existing relations');c.drawRightString(553,29,str(d.page));c.restoreState()
SimpleDocTemplate(str(ROOT/'assets/research-method.pdf'),pagesize=A4,leftMargin=42,rightMargin=42,topMargin=44,bottomMargin=58).build(story,onFirstPage=footer,onLaterPages=footer)
