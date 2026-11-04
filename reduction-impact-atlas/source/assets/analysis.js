/* View-only charts. Every score and witness comes from the Python report. */
(() => {
  const data = JSON.parse(document.getElementById('analysis-data').textContent);
  const select = document.getElementById('analysis-record');
  const metric = document.getElementById('analysis-metric');
  const mode = document.getElementById('analysis-mode');
  const byId = new Map(data.map(row => [row.id, row]));
  const el = (tag, text, cls) => {const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
  const svgEl = (tag, attrs, text) => {const n=document.createElementNS('http://www.w3.org/2000/svg',tag);for(const [k,v] of Object.entries(attrs))n.setAttribute(k,v);if(text!==undefined)n.textContent=text;return n;};
  for (const row of data) {const opt=el('option',`${row.id} · S ${row.S.toFixed(3)} · ${row.source}`);opt.value=row.id;select.append(opt);}
  function chart() {
    const svg=document.getElementById('score-chart');svg.replaceChildren();
    const narrow=matchMedia('(max-width:560px)').matches, plotWidth=narrow?230:460;
    svg.setAttribute('viewBox',`0 0 ${narrow?360:600} 565`);
    const key=metric.value,max=Math.max(1,...data.map(r=>r[key]));
    const ordered=[...data].sort((a,b)=>b[key]-a[key] || data.indexOf(a)-data.indexOf(b));
    for(let i=0;i<ordered.length;i++) {
      const row=ordered[i],y=18+i*27,g=svgEl('g',{role:'button',tabindex:'0','aria-label':`${row.id}, ${key} ${row[key]}, inspect`,class:row.id===select.value?'selected-bar':''});
      g.append(svgEl('text',{x:0,y:y+13,fill:'#b9cee1','font-size':12},row.id));
      g.append(svgEl('rect',{x:52,y,width:Math.max(2,row[key]/max*plotWidth),height:18,rx:3,fill:row.parent?'#5faaff':'#7ee3f4'}));
      g.append(svgEl('text',{x:Math.max(2,row[key]/max*plotWidth)+60,y:y+13,fill:'#e6f2ff','font-size':12},key==='S'?row.S.toFixed(3):row.N));
      g.append(svgEl('title',{},`${row.source} → ${row.target}; ${row.parent?'Open-rule impact':'Known-edge coverage'}`));
      const choose=()=>{select.value=row.id;render();};g.addEventListener('click',choose);g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();choose();}});svg.append(g);
    }
    document.getElementById('chart-caption').textContent=`${key==='S'?'Path-discounted score S':'Unweighted coverage N'} · descending order. Each bar is one record; overlapping score values remain separate.`;
  }
  function render() {
    const r=byId.get(select.value);chart();
    document.getElementById('analysis-title').textContent=`${r.id} · ${r.source} → ${r.target}`;
    document.getElementById('analysis-context').textContent=r.parent?`Open-rule impact: assume ${r.parent} after the known downstream relation is included. The known downstream relation is not hypothetical.`:'Known-edge coverage: include the documented relation in a graph copy. No open rule is assumed.';
    document.getElementById('analysis-stats').textContent=`S ${r.S.toFixed(3)} · N ${r.N} · upstream ${r.U} · downstream ${r.D}`;
    const hist=document.getElementById('hop-chart');hist.replaceChildren();
    const groups=Object.entries(r.hops).map(([h,count])=>({h:+h,count,value:count*0.5**(+h-1)}));
    const max=Math.max(1,...groups.map(g=>g.value));
    for(const g of groups){const row=el('div',undefined,'hop-row');row.append(el('span',`${g.h} ${g.h===1?'edge':'edges'}`));const track=el('div',undefined,'hop-track'),bar=el('div',undefined,'hop-fill');bar.style.width=`${g.value/max*100}%`;track.append(bar);row.append(track,el('span',`${g.count} pairs × ${0.5**(g.h-1)} = ${g.value.toFixed(3)}`));hist.append(row);}
    if(!groups.length)hist.append(el('p','No new family pair; S = 0.'));
    document.getElementById('hop-total').textContent=`Sum of contributions = ${r.S.toFixed(3)}; sum of pair counts = ${r.N}. Each family pair uses its shortest valid witness.`;
    const path=document.getElementById('witness-path');path.replaceChildren();
    if(r.path){for(let i=0;i<r.path.nodes.length;i++){path.append(el('li',r.path.nodes[i],'path-node'));if(i<r.path.steps.length){const step=r.path.steps[i],evaluated=step===r.evaluated,assumed=step.startsWith('assumption:'),known=step.startsWith('known:');const edge=el('li',undefined,`path-edge ${assumed?'assumed':known?'known':''} ${evaluated&&mode.value==='before'?'missing':''}`);edge.append(el('span',evaluated&&mode.value==='before'?'Not in before graph':assumed?'Hypothetical parent':known?'Known surveyed relation':'Baseline relation'));path.append(edge);}}}
    else path.append(el('li','No new family-pair witness.'));
    document.getElementById('witness-caption').textContent=r.path?`One illustrative path (${r.path.steps.length} edges), not the whole graph. In the before view only the evaluated edge is absent; every other edge shown is already in that comparison baseline.`:'No family-pair path available.';
    const a=document.getElementById('analysis-evidence');a.href=`#${r.id}`;a.textContent=`Inspect ${r.id} evidence and recovery →`;a.onclick=()=>{document.getElementById(r.id).open=true;};
  }
  select.addEventListener('change',render);metric.addEventListener('change',chart);mode.addEventListener('change',render);window.addEventListener('resize',chart);document.getElementById('visual-analysis').addEventListener('toggle',chart);render();
})();
