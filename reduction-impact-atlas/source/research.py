"""Isolated research-route scenarios; never write into the official baseline."""
from collections import Counter
from fractions import Fraction
import html
import json
from pathlib import Path
from shutil import copyfile

from estimate import prepare_baseline
from ranker import _paths, sha256_file, STYLE_CSS, context_counts

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
    weighted=sum((Fraction(1,2**(x['hops']-1)) for x in witnesses),Fraction())
    return {'S':float(weighted),'S_fraction':str(weighted),'S_by_decay':{str(rate):sum(rate**(x['hops']-1) for x in witnesses) for rate in (0.25,0.5,0.75)},'N':len(gained_families),'B':float(coverage),'B_fraction':str(coverage),'V':len(new),'D_half':sum(0.5**(x['hops']-1) for x in witnesses),'new_problem_pairs':witnesses,'variant_witnesses':variant_witnesses}


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
        measured=parent if parent_record else known
        marginal.update(context_counts(nodes,_paths(nodes,known_context if parent_record else edges),measured['source'],measured['target']))
        combined=compare_graphs(nodes,edges,after)
        results.append({**case,'source_label':label(a),'target_label':label(b),'task':tasks.get(case.get('task_id')),'parent_record':parent_record,'known_edge':known,'assumptions':assumptions,'known_gain':known_gain,'parent_before':parent_before,'marginal':marginal,'combined':combined})
    results.sort(key=lambda r:(-r['marginal']['S'],-r['marginal']['N'],-r['marginal']['B'],-r['marginal']['V'],r['id']))
    last=None
    for position,row in enumerate(results,1):
        key=tuple(row['marginal'][k] for k in ('S','N','B','V'))
        if key!=last:rank=position;last=key
        row['rank']=rank
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
    copyfile(ROOT/'assets/analysis.js',output/'analysis.js')
    copyfile(research_path,output/'research_candidates.json');copyfile(ROOT/'assets/research-method.pdf',output/'research-method.pdf')
    (output/'research.html').write_text(render_research(report),encoding='utf-8')
    return report


def analysis_panel(report):
    records=[]
    for r in report['questions']:
        m=r['marginal'];known_id=r['known_edge']['id']
        candidates=m['new_problem_pairs']
        with_known=[p for p in candidates if known_id in p['steps']]
        path=min(with_known or candidates,key=lambda p:p['hops']) if candidates else None
        records.append({'id':r['id'],'S':m['S'],'N':m['N'],'U':m['upstream_families'],'D':m['downstream_families'],
                        'source':r['source_label'],'target':r['target_label'],'parent':r.get('parent_question_id'),
                        'hops':dict(Counter(p['hops'] for p in candidates)),
                        'evaluated':r['assumptions'][0]['id'] if r['assumptions'] else known_id,
                        'path':{'nodes':path['nodes'],'steps':path['steps']} if path else None})
    payload=json.dumps(records,ensure_ascii=True,separators=(',',':')).replace('<','\\u003c')
    return '''<details id="visual-analysis" class="analysis-panel"><summary>Visual analysis · compare scores and inspect a path</summary>
<div class="analysis-controls"><label>Chart measure<select id="analysis-metric"><option value="S">S · discounted gain</option><option value="N">N · new family pairs</option></select></label><label>Inspect record<select id="analysis-record"></select></label></div>
<p class="analysis-legend"><span>Blue: open-rule impact</span> · <span>Cyan: known-edge coverage</span>. Colors identify comparison types, not proof confidence.</p>
<div class="analysis-grid"><figure><h2>Score comparison</h2><svg id="score-chart" viewBox="0 0 600 565" role="group" aria-label="Interactive score comparison"></svg><figcaption id="chart-caption"></figcaption><p>Select a bar or use the record menu. Equal scores are shown separately.</p></figure><section aria-live="polite"><h2 id="analysis-title"></h2><p id="analysis-context"></p><p id="analysis-stats"></p><h3>Where S comes from</h3><div id="hop-chart"></div><p id="hop-total"></p><h3>Witness path</h3><label>Graph view<select id="analysis-mode"><option value="after">After evaluated rule</option><option value="before">Before evaluated rule</option></select></label><ol id="witness-path"></ol><p id="witness-caption"></p><a id="analysis-evidence" href="#">Inspect evidence →</a></section></div></details>''' + '<script type="application/json" id="analysis-data">'+payload+'</script><script src="analysis.js" defer></script>'


def render_research(report):
    e=lambda x:html.escape(str(x),quote=True)
    rows=[]
    # Unified numeric order; comparison semantics remain explicit.
    for r in sorted(report['questions'], key=lambda r:(r['rank'],r['id'])):
        m=r['marginal'];parent=r['parent_record']
        basis='Open-rule impact' if parent else 'Known-edge coverage'
        context=(f"Assume {parent['id']}: {parent['source']} → {parent['target']}. N before / after known context: {r['parent_before']['N']} / {m['N']}." if parent else 'Coverage added by this known relation; no open rule is assumed.')
        links=' · '.join(f'<a href="{e(report["sources"][sid]["url"])}">{e(report["sources"][sid]["title"])} ↗</a>' for sid in r['source_ids'])
        paths=m['new_problem_pairs'] or m['variant_witnesses']
        witnesses=''.join(f'<li>{e(" → ".join(w["nodes"]))}</li>' for w in paths[:5])
        detail=f'<p><strong>{basis}.</strong> {e(context)}</p><p><strong>Known relation:</strong> {e(r["evidence"])}</p><p><strong>Recovery:</strong> {e(r["recovery"])}</p><p>{e(r["review_state"])}. {e(r["limitation"])}</p><p>B {m["B"]:.6g} · V {m["V"]}. S at decay 0.25 / 0.5 / 0.75: {m["S_by_decay"]["0.25"]:.3f} / {m["S"]:.3f} / {m["S_by_decay"]["0.75"]:.3f}. Overall score rank: {r["rank"]}.</p><ol>{witnesses}</ol><p>{links}</p>'
        rows.append(f'<tr class="research-card"><td>{r["id"]}</td><td><details id="{r["id"]}"><summary>{e(r["source_label"])} → {e(r["target_label"])}</summary>{detail}</details></td><td>{basis}</td><td><strong>{m["S"]:.3f}</strong><small style="display:block;font-size:.75rem">N {m["N"]} · U {m["upstream_families"]} · D {m["downstream_families"]}</small></td></tr>')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Surveyed relations · Reduction Impact Atlas</title><style>{STYLE_CSS}
.analysis-panel{{margin:0 0 28px;border-top:1px solid #345577;border-bottom:1px solid #345577;padding:18px 0}}.analysis-panel>summary{{font-size:1.1rem;font-weight:600}}.analysis-controls{{display:flex;flex-wrap:wrap;gap:18px;margin-top:24px}}.analysis-controls label{{min-width:0;flex:1}}.analysis-controls select{{max-width:100%;width:100%}}.analysis-grid{{display:grid;grid-template-columns:1fr 1fr;gap:34px;margin-top:24px}}.analysis-grid figure{{margin:0;min-width:0}}.analysis-grid section{{min-width:0}}.analysis-grid h2{{font-size:1.15rem;overflow-wrap:anywhere}}.analysis-grid h3{{font-size:1rem;margin-top:28px}}.analysis-grid p,.analysis-grid figcaption,.analysis-legend{{font-size:.85rem;line-height:1.65;color:#b9cee1}}#score-chart{{width:100%;height:auto}}#score-chart g{{cursor:pointer}}#score-chart .selected-bar rect{{stroke:#fff;stroke-width:2}}#score-chart g:focus{{outline:1px solid #fff}}.hop-row{{display:grid;grid-template-columns:48px 1fr;gap:8px;font-size:.8rem;margin:14px 0}}.hop-row>span:last-child{{grid-column:2;color:#aac4df}}.hop-track{{height:16px;background:#16304a;border-radius:3px}}.hop-fill{{height:100%;background:#65caff;border-radius:3px}}#witness-path{{list-style:none;padding:0;margin:20px 0}}.path-node{{padding:10px 14px;border:1px solid #365675;border-radius:6px;overflow-wrap:anywhere}}.path-edge{{padding:8px 16px 8px 24px;margin-left:18px;border-left:2px solid #7291ad;color:#aac4df;font-size:.8rem}}.path-edge:before{{content:"↓ ";}}.path-edge.known{{border-color:#7ee3f4;color:#7ee3f4}}.path-edge.assumed{{border-color:#f2bf70;color:#f2bf70}}.path-edge.missing{{border-left-style:dashed;opacity:.6}}@media(max-width:760px){{.analysis-grid{{grid-template-columns:1fr}}.analysis-controls{{flex-direction:column}}}}.hero{{min-height:210px;padding-top:35px;padding-bottom:45px}}.catalogue-intro{{color:#b9cee1;line-height:1.65;margin:0 0 26px;max-width:850px}}td{{vertical-align:top}}td:first-child{{white-space:nowrap}}details>summary{{cursor:pointer;color:#c7e8ff;line-height:1.6}}details p,details li{{font-size:.88rem;line-height:1.65;overflow-wrap:anywhere}}.research-card td:nth-child(3){{font-size:.8rem;color:#9fbdd4}}.research-card td:last-child{{font-size:1.15rem}}.resources{{display:flex;gap:20px;flex-wrap:wrap;margin:26px 0;font-size:.85rem}}@media(max-width:560px){{th,td{{padding:10px 7px}}.research-card td:nth-child(3),th:nth-child(3){{display:none}}table{{min-width:0;table-layout:fixed}}th:first-child,td:first-child{{width:48px}}th:last-child,td:last-child{{width:94px;white-space:normal}}td:nth-child(2){{overflow-wrap:anywhere}}details>summary{{font-size:.85rem}}.research-card td:last-child{{font-size:1rem}}}}
</style></head><body><header class="site-header"><div class="topbar"><a class="brand" href="index.html"><img class="brand-mark" src="lab-mark.svg" alt="Lab mark"><span>Reduction Impact Atlas</span></a><nav aria-label="Primary"><a href="index.html">Open rules</a><a href="research.html" aria-current="page">Surveyed relations</a></nav></div><div class="hero"><div><p class="eyebrow">Newly surveyed · 20 records</p><h1>Surveyed relations</h1><p>Known connections missing from the frozen graph.</p></div></div></header><main><p class="catalogue-intro">One catalogue of direct and downstream connections. <strong>S</strong> sums shortest-path gains with a 0.5 decay per extra edge; <strong>N</strong> counts new family pairs without decay. U / D count upstream / downstream families before the evaluated rule. The comparison column identifies whether N measures a known edge or an open rule in its known downstream context; all rows sort together by descending S, then N, B, V. The comparison identifies what each score measures, not a research-priority ranking. Select a relation for evidence and paths.</p>{analysis_panel(report)}<div class="table-wrap"><table><thead><tr><th>ID</th><th>Known relation · select to inspect</th><th>Comparison</th><th>S / N / U / D</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div><p class="catalogue-intro" style="margin-top:24px">Why similar scores? Sixteen entries reuse a general SAT encoding, and four are restriction embeddings. Shared targets inherit the same reachable families. Equal coverage is expected here; it does not imply equal research value. Exact graph adapters remain pending review.</p><footer class="resources"><a href="research-method.pdf">Calculation PDF ↗</a><a href="research_candidates.json">Evidence</a><a href="research.json">Scores and paths</a><a href="pilot.html">5 exploratory AI examples</a></footer></main></body></html>'''
