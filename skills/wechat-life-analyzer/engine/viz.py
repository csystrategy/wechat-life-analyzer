#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""可视化生成器(可移植)。读 workspace 的 graph_data.json / life_advice.json / contact_strategy.json,
生成 reports/relationship-graph.html / life-advice.html / contact-strategy.html。
用法: viz.py [graph|life|strategy|all]"""
import json, os, sys, html, datetime
HERE=os.path.dirname(os.path.abspath(__file__)); SKILL=os.path.dirname(HERE)
DATA=os.environ.get("WLA_HOME") or os.path.expanduser("~/.wechat-life-analyzer")
WS=os.path.join(DATA,"workspace"); REP=os.path.join(DATA,"reports"); os.makedirs(REP,exist_ok=True)
e=lambda s: html.escape(str(s if s is not None else ""))
def jload(p):
    fp=os.path.join(WS,p); return json.load(open(fp,encoding="utf-8")) if os.path.exists(fp) else None
CSS="""<style>:root{--bg:#0b0e14;--card:#141925;--line:#263042;--tx:#e6ebf2;--mut:#8a97ab;--gold:#f4c869;--acc:#6ea8fe}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(1100px 650px at 70% -10%,#1a2336,#0b0e14 55%);color:var(--tx);font-family:-apple-system,"PingFang SC","Microsoft Yahei",system-ui,sans-serif;line-height:1.7}
.wrap{max-width:1080px;margin:0 auto;padding:30px 22px 90px}h1{font-size:25px;margin:0 0 4px}.sub{color:var(--mut);font-size:13px;margin-bottom:16px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin:14px 0}h2{font-size:20px;margin:28px 0 10px}
ul{margin:5px 0;padding-left:18px}li{margin:6px 0;font-size:13.5px;color:#cdd7e4}.gold{color:var(--gold)}.mut{color:var(--mut)}
.chip{display:inline-block;font-size:12px;padding:3px 9px;border-radius:8px;margin:3px 4px 3px 0;background:#1b2230;border:1px solid var(--line)}
.banner{background:linear-gradient(135deg,#1c2740,#161b27);border-left:3px solid var(--gold);border-radius:12px;padding:14px 18px;margin:14px 0;font-size:14.5px}</style>"""

def graph_html():
    D=jload("graph_data.json")
    if not D: print("缺 graph_data.json,跳过 graph"); return
    DATA=json.dumps(D,ensure_ascii=False).replace("</","<\\/")
    h=f"""<!DOCTYPE html><html lang=zh><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>关系图谱</title><script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>{CSS}
<style>#g{{width:100%;height:600px;background:#0d1118;border:1px solid var(--line);border-radius:14px}}
#dt{{position:fixed;right:16px;top:16px;width:300px;max-height:80vh;overflow:auto;background:rgba(15,20,30,.95);border:1px solid var(--line);border-radius:12px;padding:14px;font-size:12.5px;display:none}}
#lg{{position:fixed;left:16px;top:80px;background:rgba(13,17,25,.8);border:1px solid var(--line);border-radius:10px;padding:9px;font-size:11.5px}}#lg div{{margin:3px 0}}#lg i{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}}</style></head>
<body><div class=wrap><h1>关系图谱</h1><div class=sub>圈=聊天量 · 颜色=圈层 · 连线=共同的群 · 点节点看详情 · 仅本地</div>
<div class=banner id=hl></div><svg id=g></svg><div id=lg></div></div><div id=dt></div><script>
const D={DATA};document.getElementById('hl').textContent='💡 '+(D.headline||'');
const cl=[...new Set(D.nodes.map(n=>n.category||n.cluster))];const pal=['#6ea8fe','#f4c869','#7ee0a0','#f78fb3','#b693f7','#5fd0d6','#f0a868','#9bb1c9','#e57373','#82c785'];
const col=d3.scaleOrdinal().domain(cl).range(pal);
document.getElementById('lg').innerHTML=cl.map(c=>`<div><i style="background:${{col(c)}}"></i>${{c}}</div>`).join('');
const W=innerWidth>1100?1040:innerWidth-44,H=600;const svg=d3.select('#g').attr('viewBox',[0,0,W,H]);const g=svg.append('g');
svg.call(d3.zoom().scaleExtent([.3,4]).on('zoom',e=>g.attr('transform',e.transform)));
const nodes=D.nodes.map(d=>({{...d}})),links=(D.links||[]).map(d=>({{...d}}));
const r=d3.scaleSqrt().domain([0,d3.max(nodes,n=>n.total||1)]).range([5,28]);
const sim=d3.forceSimulation(nodes).force('link',d3.forceLink(links).id(d=>d.id||d.name).distance(80)).force('charge',d3.forceManyBody().strength(-150)).force('center',d3.forceCenter(W/2,H/2)).force('c',d3.forceCollide().radius(d=>r(d.total||1)+4));
const lk=g.append('g').attr('stroke','#3a4760').selectAll('line').data(links).join('line').attr('stroke-opacity',d=>Math.min(.5,.12+(d.weight||1)*.02)).attr('stroke-width',d=>Math.min(4,.6+(d.weight||1)*.12));
const nd=g.append('g').selectAll('g').data(nodes).join('g').style('cursor','pointer').call(d3.drag().on('start',(e,d)=>{{if(!e.active)sim.alphaTarget(.3).restart();d.fx=d.x;d.fy=d.y}}).on('drag',(e,d)=>{{d.fx=e.x;d.fy=e.y}}).on('end',(e,d)=>{{if(!e.active)sim.alphaTarget(0);d.fx=null;d.fy=null}}));
nd.append('circle').attr('r',d=>r(d.total||1)).attr('fill',d=>col(d.category||d.cluster)).attr('fill-opacity',.9).attr('stroke','#0d1118').attr('stroke-width',1.5);
nd.append('text').text(d=>d.name).attr('y',d=>r(d.total||1)+11).attr('text-anchor','middle').attr('font-size',10).attr('fill','#c7d2e2').attr('pointer-events','none').style('text-shadow','0 1px 3px #000');
nd.on('click',(e,d)=>{{const el=document.getElementById('dt');el.style.display='block';el.innerHTML=`<b style="font-size:15px">${{d.name}}</b> <span class=mut>${{d.category||d.cluster||''}}</span>
<div style="margin:6px 0" class=mut>${{d.role||''}}</div><div><span class=gold>建议联系</span>: ${{d.cadence||''}} ｜ 优先级 ${{d.priority||''}}</div>
<div style="margin-top:6px"><span class=gold>怎么主动</span>: ${{d.how||''}}</div><div style="margin-top:6px" class=mut>${{d.strategy||''}}</div>
<div style="margin-top:6px" class=mut>聊天 ${{(d.total||0).toLocaleString()}} 条 · 最近 ${{d.days_since}} 天前 · 趋势 ${{d.trend}}</div>`}});
sim.on('tick',()=>{{lk.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y).attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);nd.attr('transform',d=>`translate(${{d.x}},${{d.y}})`)}});
</script></body></html>"""
    open(os.path.join(REP,"relationship-graph.html"),"w").write(h); print("-> reports/relationship-graph.html")

def life_html():
    R=jload("life_advice.json")
    if not R: print("缺 life_advice.json,跳过 life"); return
    syn=R.get("synthesis",{}); dims=R.get("dimensions",[])
    pr="".join(f'<div class="card" style="border-left:3px solid var(--gold)"><b>{p.get("rank","")}. {e(p["focus"])}</b><div class=mut>{e(p["why"])}</div></div>' for p in sorted(syn.get("priorities",[]),key=lambda x:x.get("rank",9)))
    conn="".join(f"<li>{e(x)}</li>" for x in syn.get("connections",[]))
    ht="".join(f"<li>{e(x)}</li>" for x in syn.get("hard_truths",[]))
    bd=syn.get("by_dimension",{})
    def bcol(k,lab):
        return f'<div class=card><h2 style="font-size:15px">{lab}</h2><ul>'+"".join(f"<li>{e(x)}</li>" for x in bd.get(k,[]))+"</ul></div>"
    dimh=""
    for d in dims:
        ev="".join(f"<li>{e(x)}</li>" for x in d.get("evidence",[]))
        ad="".join(f'<div class="card" style="padding:11px 13px;margin:8px 0"><b class=gold>{e(a.get("action",a) if isinstance(a,dict) else a)}</b>{("<div class=mut>"+e(a.get("why",""))+"</div>") if isinstance(a,dict) else ""}</div>' for a in d.get("advice",[]))
        dimh+=f'<div class=card><h2>{e(d.get("dimension",""))}</h2><div>{e(d.get("current_picture",""))}</div>{("<h2 style=font-size:14px>证据</h2><ul>"+ev+"</ul>") if ev else ""}{ad}</div>'
    h=f"""<!DOCTYPE html><html lang=zh><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>人生建议</title>{CSS}</head>
<body><div class=wrap><h1>人生主线建议</h1><div class=sub>三维深读(工作/投资/亲密关系)+综合 · {datetime.date.today()} · 仅本地</div>
<div class=banner>⚠️ AI 从聊天推断,未必都对;数字/极端说法可能是玩笑被当真,请核实纠正。</div>
<div class="card" style="border-left:3px solid var(--gold)"><h2>🧭 人生主线</h2><div>{e(syn.get("life_mainline",""))}</div></div>
<div class=card><h2>🔗 三条线如何牵连</h2><ul>{conn}</ul></div>
<h2>🎯 优先级</h2>{pr}
<div class="card" style="border-left:3px solid #b693f7"><h2>⭐ 如果只做一件事</h2>{e(syn.get("one_thing",""))}</div>
<div class=card><h2>💢 该说的实话</h2><ul>{ht}</ul></div>
<h2>📋 各维度浓缩建议</h2>{bcol("work","工作")}{bcol("love","感情")}{bcol("invest","投资")}
<h2>📖 三维度深读</h2>{dimh}</div></body></html>"""
    open(os.path.join(REP,"life-advice.html"),"w").write(h); print("-> reports/life-advice.html")

def strategy_html():
    R=jload("contact_strategy.json"); S=R if R and "action_plan" in R else (R.get("synthesis") if R else None)
    if not S: print("缺 contact_strategy.json,跳过 strategy"); return
    tw="".join(f'<label style="display:flex;gap:10px;padding:8px 0;border-bottom:1px dashed var(--line);font-size:14px"><input type=checkbox><span><b>{e(x["name"])}</b> — {e(x["action"])}</span></label>' for x in S.get("this_week",[]))
    ap=""
    for t in S.get("action_plan",[]):
        ppl="".join(f'<div style="padding:6px 0;border-top:1px solid #1d2533;font-size:13px"><b class=gold>{e(p["name"])}</b> <span class=mut>{e(p.get("status",""))}</span><div>{e(p.get("how",""))}</div></div>' for p in t.get("people",[]))
        ap+=f'<div class=card><h2 style="font-size:16px">{e(t["tier"])} <span class=chip style="background:var(--gold);color:#0b0e14">{e(t.get("cadence",""))}</span></h2><div class=mut>{e(t.get("purpose",""))}</div>{ppl}</div>'
    pp="".join(f"<li>{e(x)}</li>" for x in S.get("proactive_principles",[]))
    la="".join(f'<div class="card" style="padding:11px 13px;margin:8px 0"><b class=gold>{e(a["area"])}</b><div>{e(a["advice"])}</div></div>' for a in S.get("life_advice",[]))
    h=f"""<!DOCTYPE html><html lang=zh><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1"><title>联系策略</title>{CSS}</head>
<body><div class=wrap><h1>联系策略 + 人生建议</h1><div class=sub>逐人精读 · 频次/怎么主动/策略 · {datetime.date.today()} · 仅本地</div>
<div class=banner>💡 {e(S.get("overview",""))}</div>
<h2>✅ 本周就做</h2><div class=card>{tw}</div>
<h2>📋 分层行动计划</h2>{ap}
<h2>🎯 如何主动(硬原则)</h2><div class=card><ul>{pp}</ul></div>
<h2>🧭 人生建议</h2>{la}
<div class="card" style="border-left:3px solid #f472b6"><h2>💢 一句实话</h2>{e(S.get("hard_truth",""))}</div></div></body></html>"""
    open(os.path.join(REP,"contact-strategy.html"),"w").write(h); print("-> reports/contact-strategy.html")

if __name__=="__main__":
    what=sys.argv[1] if len(sys.argv)>1 else "all"
    if what in ("graph","all"): graph_html()
    if what in ("life","all"): life_html()
    if what in ("strategy","all"): strategy_html()
