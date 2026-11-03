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
    qb={q['id']:q for q in board['questions']};tasks={t['id']:t for t in catalogue['tasks']}
    task_nodes={}
    for tid,t in tasks.items():
        if not t.get('definition'):raise ValueError('missing task definition')
        task_nodes[tid]=len(nodes);nodes.append({'name':t['label'],'problem_key':'research:'+tid,'variant':{}})
    def endpoint(ref):
        if 'graph_node' in ref:
            i=ref['graph_node']
            if type(i)!=int or not 0<=i<len(graph['nodes']):raise ValueError('invalid graph endpoint')
            return i
        if 'task_id' in ref:return task_nodes[ref['task_id']]
        if ref.get('side') not in ('source','target'):raise ValueError('invalid board side')
        return endpoints[ref['board_question']][0 if ref['side']=='source' else 1]
    def label(i):
        variant=nodes[i].get('variant') or {}
        return nodes[i]['name']+(' ('+', '.join(f'{k}={v}' for k,v in sorted(variant.items()))+')' if variant else '')
    results=[];seen=set()
    for case in catalogue['candidates']:
        cid=case['id'];a,b=endpoint(case['source']),endpoint(case['target'])
        if cid in seen or a==b or case['group'] not in ('new-direct','downstream'):raise ValueError('invalid known relation')
        seen.add(cid)
        if not case.get('evidence') or not case.get('recovery') or set(case['source_ids'])-set(catalogue['sources']):raise ValueError('known relation needs evidence')
        known={'source':a,'target':b,'id':'known:'+cid}
        known_context=edges+[known];assumptions=[];parent_record=None
        known_gain=compare_graphs(nodes,edges,known_context)
        parent_before=None
        if case['group']=='downstream':
            qid=case['parent_question_id'];u,v,notes,_=endpoints[qid]
            if a!=v:raise ValueError('downstream source must equal parent target')
            parent={'source':u,'target':v,'id':f'assumption:{cid}:parent:{qid}'}
            assumptions=[{'id':parent['id'],'source_node':u,'target_node':v,'source':label(u),'target':label(v),'endpoint_assumptions':notes}]
            parent_record=qb[qid]
            after=known_context+[parent]
            marginal=compare_graphs(nodes,known_context,after)
            parent_before=compare_graphs(nodes,edges,edges+[parent])
        else:
            after=known_context;marginal=known_gain
        combined=compare_graphs(nodes,edges,after)
        results.append({**case,'source_label':label(a),'target_label':label(b),'task':tasks.get(case.get('task_id')),'parent_record':parent_record,'known_edge':known,'assumptions':assumptions,'known_gain':known_gain,'parent_before':parent_before,'marginal':marginal,'combined':combined})
    for group in ('new-direct','downstream'):
        rows=sorted((r for r in results if r['group']==group),key=lambda r:(-r['marginal']['N'],-r['marginal']['B'],-r['marginal']['V'],r['id']))
        last=None
        for position,row in enumerate(rows,1):
            key=tuple(row['marginal'][k] for k in ('N','B','V'))
            if key!=last:rank=position;last=key
            row['rank']=rank
    results.sort(key=lambda r:(r['group'],r['rank'],r['id']))
    report={'schema_version':2,'checked_on':catalogue['checked_on'],'graph_sha256':graph_hash,'registry_sha256':board['registry_sha256'],'research_sha256':sha256_file(research_path),'bridges_sha256':sha256_file(bridges_path),'mappings_sha256':sha256_file(mappings_path),'scope':catalogue['scope'],'sources':catalogue['sources'],'search_log':catalogue['search_log'],'questions':results}
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    compact=json.loads(json.dumps(report));compact['nodes']=nodes
    compact['baseline_edges']=[{**edge,'id':edge.get('id',f'baseline:edge:{i}')} for i,edge in enumerate(edges)]
    compact['witness_encoding']='Resolve node_ids against nodes; known edges are supplied per record and only assumption-prefixed edges are hypothetical.'
    for row in compact['questions']:
        for measure in ('marginal','combined','known_gain','parent_before'):
            if row[measure] is None:continue
            for key in ('new_problem_pairs','variant_witnesses'):
                row[measure][key]=[{k:p[k] for k in ('source_node','target_node','node_ids','steps','assumptions','hops')} for p in row[measure][key]]
    (output/'research.json').write_text(json.dumps(compact,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
    copyfile(research_path,output/'research_candidates.json');copyfile(ROOT/'assets/research-method.pdf',output/'research-method.pdf')
    (output/'research.html').write_text(render_research(report),encoding='utf-8')
    return report


def render_research(report):
    e=lambda x:html.escape(str(x),quote=True)
    sections=[]
    for group,title in [('new-direct','10 surveyed existing direct relations'),('downstream','10 existing downstream relations for open board rules')]:
        rows=[r for r in report['questions'] if r['group']==group]
        table=''.join(f'<tr><td>{r["rank"]}</td><td><a href="#{r["id"]}">{r["id"]}</a></td><td>{e(r["source_label"])} → {e(r["target_label"])}</td><td>{r["marginal"]["N"]} / {r["marginal"]["B"]:.5g} / {r["marginal"]["V"]}</td></tr>' for r in rows)
        cards=[]
        for r in rows:
            m=r['marginal'];parent=r['parent_record'];known=r['known_gain']
            definition=parent['target_definition'] if parent else r['task']['definition']
            links=' · '.join(f'<a href="{e(report["sources"][sid]["url"])}">{e(report["sources"][sid]["title"])} ↗</a>' for sid in r['source_ids'])
            if parent:links+=f' · <a href="https://github.com/GiggleLiu/autoresearch-gadgets/blob/main/registry/{e(parent["slug"])}.json">Frozen parent {e(parent["id"])}</a>'
            context=(f'<p><strong>Only hypothetical rule:</strong> {e(parent["source"])} → {e(parent["target"])} ({e(parent["id"])}). Parent impact before this known downstream relation: N {r["parent_before"]["N"]}; after including it: N {m["N"]}.</p>' if parent else '<p>This row measures the coverage gain of an existing relation absent from the frozen baseline. It is not an open-reduction claim.</p>')
            paths=m['new_problem_pairs'] or m['variant_witnesses']
            witnesses=''.join(f'<li>{e(" → ".join(p["nodes"]))}<small>Hypotheses used: {e(", ".join(p["assumptions"]) or "none")}</small></li>' for p in paths[:5])
            cards.append(f'<article class="summary research-card" id="{r["id"]}"><p class="eyebrow">{r["id"]} · rank {r["rank"]} · {e(r["relation_kind"])}</p><h3>{e(r["source_label"])} → {e(r["target_label"])}</h3><p><strong>N {m["N"]} · B {m["B"]:.6g} · V {m["V"]}</strong> · diagnostic D½ {m["D_half"]:.3f}</p>{context}<details class="route-details"><summary>Definitions, known reduction, and paths</summary><p><strong>Source task:</strong> {e(definition)}</p><p><strong>Known-relation argument:</strong> {e(r["evidence"])}</p><p><strong>Output recovery:</strong> {e(r["recovery"])}</p><p><strong>Review status:</strong> {e(r["review_state"])}</p><p>Coverage gain from the known downstream relation alone: N {known["N"]}, B {known["B"]:.6g}, V {known["V"]}. Combined graph gain is N {r["combined"]["N"]}; it must not be added to the parent impact.</p><p>{e(r["limitation"])}</p><ol>{witnesses}</ol><p>{links}</p><a href="research.json">All scores, input hashes and witnesses</a></details></article>')
        explanation='Sorted by coverage gained when the known relation is included.' if group=='new-direct' else 'Sorted by the hypothetical parent rule\'s impact after its known downstream relation is included. The downstream relation itself is not a hypothesis.'
        sections.append(f'<section><h2>{title}</h2><p>{explanation} Order: N, then B, then V; ties share a rank.</p><div class="table-wrap"><table><thead><tr><th>Rank</th><th>ID</th><th>Existing relation</th><th>N / B / V</th></tr></thead><tbody>{table}</tbody></table></div>{"".join(cards)}</section>')
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Known relations · Reduction Impact Atlas</title><style>{STYLE_CSS}.research-card{{margin:20px 0}}.research-card h3{{font-size:1.3rem;line-height:1.4}}.route-details>summary{{cursor:pointer;color:#7ee3f4;font-weight:600}}.research-card li,.research-card a{{overflow-wrap:anywhere}}.research-card small{{display:block;color:#9fbdd4}}section>h2{{margin-top:38px}}</style></head><body><header class="site-header"><div class="topbar"><a class="brand" href="index.html"><img class="brand-mark" src="lab-mark.svg" alt="Lab mark"><span>Reduction Impact Atlas</span></a><nav><a href="index.html">Full ranking</a><a href="pilot.html">AI examples</a><a href="research-method.pdf">Research PDF</a></nav></div><div class="hero"><div><p class="eyebrow">Literature and definition audit</p><h1>Known relations. Better context.</h1><p>Survey existing reductions, then measure how they extend the consequences of an open candidate.</p></div></div></header><main><div class="summary"><p><strong>Correction:</strong> the previous algorithm-goal routes and speculative downstream pairings have been withdrawn. This page now contains 10 existing direct relations and 10 existing downstream relations.</p><p>Existing means a restriction embedding or a polynomial-verifier encoding establishes the relation under the stated task model. Several entries are applications of the same general theorem, not twenty separate new theorems. Exact graph adapters still await independent review.</p><p>For downstream rows, only the parent board rule is assumed. Known relations are included in a temporary graph copy; they do not alter the original graph or the official ranking. No new efficient algorithm or complexity-class collapse is proposed.</p><p><a href="research-method.pdf">Calculation PDF ↗</a> · <a href="research_candidates.json">Evidence records</a> · <a href="research.json">All scores and paths</a></p></div>{"".join(sections)}</main></body></html>'
