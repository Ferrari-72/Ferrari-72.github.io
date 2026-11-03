"""Isolated research-route scenarios; never write into the official baseline."""
from collections import Counter
from fractions import Fraction
import html
import json
from pathlib import Path
from shutil import copyfile

from estimate import prepare_baseline
from ranker import _paths, sha256_file, STYLE_CSS

ROOT = Path(__file__).parent


def compare_graphs(nodes, before_edges, after_edges):
    """Recompute both closures, deduplicate family pairs, retain shortest witnesses."""
    before, after = _paths(nodes, before_edges), _paths(nodes, after_edges)
    families = [n.get('problem_key', n['name']) for n in nodes]
    sizes = Counter(families)
    old = {(u,v) for u,p in enumerate(before) for v in p if u != v}
    new = {(u,v) for u,p in enumerate(after) for v in p if u != v} - old
    old_families = {(families[u],families[v]) for u,v in old if families[u] != families[v]}
    gained_families = {(families[u],families[v]) for u,v in new if families[u] != families[v]} - old_families
    increments = Counter((families[u],families[v]) for u,v in new if (families[u],families[v]) in old_families)
    coverage = sum((Fraction(n, sizes[a]*sizes[b]) for (a,b),n in increments.items()), Fraction())
    best = {}; variant_witnesses=[]
    for u,v in sorted(new):
        pair = families[u],families[v]
        path = after[u][v]
        cursor = u; labels = [nodes[u]['name']]; indices=[u]; steps=[]
        for index in path:
            edge=after_edges[index]
            if edge['source'] != cursor: raise AssertionError('discontinuous research witness')
            cursor=edge['target']; labels.append(nodes[cursor]['name']); indices.append(cursor)
            steps.append(edge.get('id',f'baseline:edge:{index}'))
        if cursor!=v: raise AssertionError('incorrect research witness target')
        witness={'source_node':u,'target_node':v,'node_ids':indices,'source':nodes[u]['name'],'target':nodes[v]['name'],'nodes':labels,'steps':steps,'hops':len(path),'assumptions':[s for s in steps if s.startswith('assumption:')]}
        variant_witnesses.append(witness)
        if pair in gained_families and (pair not in best or len(path)<len(best[pair]['steps'])):
            best[pair]=witness
    witnesses=sorted(best.values(),key=lambda x:(x['source'],x['target']))
    return {'N':len(gained_families),'B':float(coverage),'B_fraction':str(coverage),'V':len(new),'D_half':sum(0.5**(x['hops']-1) for x in witnesses),'new_problem_pairs':witnesses,'variant_witnesses':variant_witnesses}


def build_research(output=ROOT/'dist', *, graph_path=ROOT/'data/reduction_graph.json', questions_path=ROOT/'data/questions.json', mappings_path=ROOT/'data/mappings.json', bridges_path=ROOT/'data/bridges.json', research_path=ROOT/'data/research_candidates.json'):
    read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
    graph,board,mappings,bridges,catalogue=map(read,(graph_path,questions_path,mappings_path,bridges_path,research_path))
    graph_hash=sha256_file(graph_path)
    if catalogue['graph_sha256']!=graph_hash or catalogue['registry_sha256']!=board['registry_sha256']:
        raise ValueError('research catalogue snapshot hash mismatch')
    nodes,edges,endpoints,_,_,_=prepare_baseline(graph,graph_hash,board['questions'],mappings,bridges,board['registry_sha256'])
    board_by_id={q['id']:q for q in board['questions']}
    tasks={t['id']:t for t in catalogue['tasks']}
    if len(tasks)!=len(catalogue['tasks']): raise ValueError('duplicate research task ID')
    task_nodes={}
    for tid,t in tasks.items():
        if not t.get('definition') or not t.get('source_ids'): raise ValueError('task needs definition and primary sources')
        if set(t['source_ids'])-set(catalogue['sources']): raise ValueError('unknown primary source')
        task_nodes[tid]=len(nodes);nodes.append({'name':t['label'],'problem_key':'research:'+tid,'variant':{}})
    support_records=[]
    for support in catalogue.get('support_edges',[]):
        index=support['graph_node']
        if (support['direction']!='task_to_graph' or type(index)!=int or not 0<=index<len(graph['nodes']) or not support.get('evidence') or set(support['source_ids'])-set(catalogue['sources'])):
            raise ValueError('invalid research support edge')
        edges.append({'source':task_nodes[support['task_id']],'target':index,'id':support['id']})
        support_records.append(support)
    def endpoint(ref):
        if len(ref)!=1 and set(ref)!={'board_question','side'}: raise ValueError('endpoint needs one reference type')
        if 'graph_node' in ref:
            idx=ref['graph_node']
            if type(idx)!=int or not 0<=idx<len(graph['nodes']): raise ValueError('invalid graph endpoint')
            return idx
        if 'task_id' in ref: return task_nodes[ref['task_id']]
        if ref.get('side') not in ('source','target'): raise ValueError('invalid board endpoint side')
        return endpoints[ref['board_question']][0 if ref['side']=='source' else 1]
    results=[];seen=set()
    for case in catalogue['candidates']:
        cid=case['id']
        if cid in seen: raise ValueError('duplicate research candidate ID')
        seen.add(cid)
        if case['group'] not in ('new-direct','downstream') or case['review_state']!='AI-proposed route; no reduction construction; semantic review pending': raise ValueError('invalid research group or review state')
        a,b=endpoint(case['source']),endpoint(case['target'])
        if a==b: raise ValueError('research edge must have distinct endpoints')
        scenario_before=list(edges); assumptions=[]
        if case['group']=='downstream':
            qid=case['parent_question_id'];u,v,notes,_=endpoints[qid]
            if a!=v: raise ValueError('downstream source must equal parent target')
            parent={'source':u,'target':v,'id':f'assumption:{cid}:parent:{qid}'}
            scenario_before.append(parent)
            assumptions.append({'id':parent['id'],'source_node':u,'target_node':v,'source':nodes[u]['name'],'target':nodes[v]['name'],'endpoint_assumptions':notes})
        edge={'source':a,'target':b,'id':f'assumption:{cid}:candidate'}
        assumptions.append({'id':edge['id'],'source_node':a,'target_node':b,'source':nodes[a]['name'],'target':nodes[b]['name']})
        complete=scenario_before+[edge]
        marginal=compare_graphs(nodes,scenario_before,complete)
        total=compare_graphs(nodes,edges,complete)
        def label(index):
            variant=nodes[index].get('variant') or {}
            suffix=' ('+', '.join(f'{k}={v}' for k,v in sorted(variant.items()))+')' if variant else ''
            return nodes[index]['name']+suffix
        parent_record=board_by_id.get(case.get('parent_question_id'))
        results.append({**case,'source_label':label(a),'target_label':label(b),'task':tasks[case['task_id']],'parent_record':parent_record,'assumptions':assumptions,'marginal':marginal,'combined':total})
    for group in ('new-direct','downstream'):
        rows=sorted((r for r in results if r['group']==group),key=lambda r:(-r['marginal']['N'],-r['marginal']['B'],-r['marginal']['V'],r['id']))
        last=None
        for position,row in enumerate(rows,1):
            key=tuple(row['marginal'][k] for k in ('N','B','V'))
            if key!=last: rank=position;last=key
            row['rank']=rank
    results.sort(key=lambda r:(r['group'],r['rank'],r['id']))
    report={'schema_version':1,'checked_on':catalogue['checked_on'],'graph_sha256':graph_hash,'registry_sha256':board['registry_sha256'],'research_sha256':sha256_file(research_path),'bridges_sha256':sha256_file(bridges_path),'mappings_sha256':sha256_file(mappings_path),'scope':catalogue['scope'],'support_edges':support_records,'sources':catalogue['sources'],'search_log':catalogue['search_log'],'excluded':catalogue['excluded'],'questions':results}
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    compact=json.loads(json.dumps(report))
    compact['witness_encoding']='Resolve node_ids against nodes; baseline edge IDs use their augmented baseline index.'
    compact['nodes']=nodes
    compact['baseline_edges']=[{**edge,'id':edge.get('id',f'baseline:edge:{i}')} for i,edge in enumerate(edges)]
    for row in compact['questions']:
        for measure in ('marginal','combined'):
            for key in ('new_problem_pairs','variant_witnesses'):
                row[measure][key]=[{k:path[k] for k in ('source_node','target_node','node_ids','steps','assumptions','hops')} for path in row[measure][key]]
    (output/'research.json').write_text(json.dumps(compact,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    copyfile(research_path,output/'research_candidates.json')
    copyfile(ROOT/'assets/research-method.pdf',output/'research-method.pdf')
    (output/'research.html').write_text(render_research(report),encoding='utf-8')
    return report


def render_research(report):
    e=lambda v:html.escape(str(v),quote=True)
    sections=[]
    for group,title in [('new-direct','10 new direct-route questions'),('downstream','10 downstream-route proposals')]:
        cards=[]
        for r in (q for q in report['questions'] if q['group']==group):
            m,c=r['marginal'],r['combined'];t=r['task']
            parent=r.get('parent_record')
            parent_context=(f'<p><strong>Frozen parent:</strong> <a href="https://github.com/GiggleLiu/autoresearch-gadgets/blob/main/registry/{e(parent["slug"])}.json">{e(parent["id"])}: {e(parent["source"])} → {e(parent["target"])}</a></p><p><strong>Source of the downstream rule:</strong> {e(parent["target_definition"])}</p>' if parent else '')
            links=' · '.join(f'<a href="{e(report["sources"][s]["url"])}">{e(report["sources"][s]["title"])} ↗</a>' for s in t['source_ids'])
            evidence=' '.join(report['sources'][s]['finding'] for s in t['source_ids'])
            assumptions=''.join(f'<li>{e(a["source"])} → {e(a["target"])} <small>{e(a["id"])}</small></li>' for a in r['assumptions'])
            displayed_paths=m['new_problem_pairs'] or m['variant_witnesses']
            path_kind='family' if m['new_problem_pairs'] else 'variant'
            paths=''.join(f'<li>{e(" → ".join(p["nodes"]))}<small>Assumptions: {e(", ".join(p["assumptions"]))}</small></li>' for p in displayed_paths[:5])
            cards.append(f'''<article class="summary research-card" id="{e(r['id'])}"><p class="eyebrow">{e(r['id'])} · rank {r['rank']} in this group · {e(r['route_kind'])}</p><h3>{e(r['source_label'])} → {e(r['target_label'])}</h3><div class="scores"><span>Marginal N <b>{m['N']}</b></span><span>B <b>{m['B']:.6g}</b></span><span>V <b>{m['V']}</b></span><span>D½ <b>{m['D_half']:.3f}</b></span></div><p>{e(r['review_state'])}. No reduction construction has been established.</p><details class="route-details"><summary>Evidence, assumptions and proof obligations</summary><p><strong>Question:</strong> {e(r['question'])}</p>{parent_context}<p><strong>Task definition:</strong> {e(t['definition'])}</p><p><strong>Literature status:</strong> {e(t['status'])} Checked {e(report['checked_on'])}.</p><p><strong>Source finding:</strong> {e(evidence)}</p><p><strong>Proposed route:</strong> {e(r['rationale'])}</p><p><strong>Scoped route search:</strong> {e(r["route_search"]["query"])}. {e(r["route_search"]["outcome"])}</p><p><strong>Remaining proof:</strong> {e(r['proof_obligation'])}</p><p><strong>Conditional consequence:</strong> {e(r['consequence'])}</p><p><strong>Assumptions in this scenario:</strong></p><ul>{assumptions}</ul><p>Combined gain relative to the common frozen baseline: N {c['N']} · B {c['B']:.6g} · V {c['V']}. The marginal score above adds this candidate after its parent assumption, when present. These two counts must not be added.</p><details class="relations"><summary>First {min(5,len(displayed_paths))} of {len(displayed_paths)} marginal new {path_kind} relations</summary><ol>{paths}</ol><p><a href="research.json">All witnesses and assumptions in JSON</a></p></details><p>{links}</p></details></article>''')
        overview="".join(f'<tr><td>{r["rank"]}</td><td><a href="#{r["id"]}">{r["id"]}</a></td><td>{e(r["source_label"])} → {e(r["target_label"])}</td><td>{r["marginal"]["N"]} / {r["marginal"]["B"]:.4g} / {r["marginal"]["V"]}</td><td>{r["combined"]["N"]}</td></tr>' for r in report['questions'] if r['group']==group)
        sections.append(f'<section><h2>{title}</h2><p>Sorted within this group by marginal N, then B, then V; equal triples share a rank. D½ is diagnostic.</p><div class="table-wrap"><table><thead><tr><th>Rank</th><th>ID</th><th>Proposed route</th><th>Marginal N / B / V</th><th>Combined N</th></tr></thead><tbody>{overview}</tbody></table></div>{"".join(cards)}</section>')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Research routes · Reduction Impact Atlas</title><style>{STYLE_CSS}\n.research-card{{margin:20px 0}}.research-card h3{{font-size:1.35rem;line-height:1.3}}.scores{{display:flex;gap:12px 24px;flex-wrap:wrap;color:#a6bdd4}}.scores b{{color:#fff}}.research-card li{{overflow-wrap:anywhere;line-height:1.6}}.research-card small{{display:block;color:#9fbdd4}}section>h2{{margin-top:42px}}.research-card .eyebrow{{line-height:1.6}}.research-card a{{overflow-wrap:anywhere}}.route-details>summary{{cursor:pointer;color:#7ee3f4;font-weight:600;margin-top:14px}}</style></head><body><header class="site-header"><div class="topbar"><a class="brand" href="index.html"><img class="brand-mark" src="lab-mark.svg" alt="Lab mark"><span>Reduction Impact Atlas</span></a><nav><a href="index.html">Full ranking</a><a href="pilot.html">AI examples</a><a href="research-method.pdf">Research PDF</a></nav></div><div class="hero"><div><p class="eyebrow">Literature-led research catalogue</p><h1>Research routes, ranked.</h1><p>10 new direct-route questions and 10 downstream proposals, evaluated on copies of one frozen baseline.</p></div></div></header><main><div class="summary"><p><strong>Research proposals, not established reductions.</strong> {e(report['scope'])}</p><p>New means absent from the frozen 76-question catalogue, not newly discovered mathematics. The primary sources establish the underlying unresolved classification, not our proposed ordered edges. Downstream pairings are speculative and have no construction yet; a high topology score does not make a route plausible.</p><details class="route-details"><summary>Scoring assumptions and limitations</summary><p><strong>Metric limit:</strong> nine proposed algorithms now have N=0, B=1/9, V=1 after known verifier-to-SAT routes are included. N=0 does not mean no algorithmic value: a reduction to 2-SAT would still give a polynomial algorithm.</p><p>The new-direct group asks mostly for polynomial algorithms via 2-SAT. The downstream group tests two-assumption chains. Their scores use different conditional baselines and are ranked separately. No research edge enters the official 76-question ranking.</p><p>The temporary research baseline includes ten documented polynomial-verifier-to-SAT support routes. These known upper bounds are not new open questions; their graph adapters remain subject to review. See <a href="research_candidates.json">the verifier arguments</a>. This prevents inflating gains merely because an NP task was left isolated.</p><p>New task variants stay separate unless a semantic mapping is reviewed. Many equal scores reflect graph coverage and shared hubs, not equal scientific value.</p></details><p><a href="research-method.pdf">Calculation and review scope PDF ↗</a> · <a href="research_candidates.json">Research records and search log</a> · <a href="research.json">Scores and witnesses</a></p></div>{''.join(sections)}<section class="method-note"><h2>Excluded during research</h2>{''.join(f'<p><a href="{e(x["source_url"])}">{e(x["task"])}</a>: {e(x["reason"])}</p>' for x in report['excluded'])}</section><p><a href="index.html">← Full ranking</a></p></main></body></html>'''
