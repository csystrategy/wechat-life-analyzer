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
CSS="""<style>:root{--bg:#FAF9F6;--card:rgba(255,255,255,.72);--line:rgba(20,24,33,.08);--line2:rgba(20,24,33,.13);--tx:#2B2F36;--mut:#7A808C;--gold:#C2992E;--acc:#8C7BA8;--serif:'Songti SC','STSong','Noto Serif SC',ui-serif,serif;--sans:'Inter',-apple-system,'PingFang SC','Hiragino Sans GB','Microsoft Yahei',system-ui,sans-serif}
*{box-sizing:border-box}body{margin:0;color:var(--tx);line-height:1.75;font-family:var(--sans);-webkit-font-smoothing:antialiased;background:radial-gradient(1100px 800px at 84% -10%,rgba(140,123,168,.07),transparent 60%),radial-gradient(900px 720px at -6% 112%,rgba(201,169,140,.06),transparent 55%),var(--bg)}
.wrap{max-width:880px;margin:0 auto;padding:50px 26px 110px}h1{font-family:var(--serif);font-size:30px;font-weight:600;margin:0 0 6px;letter-spacing:.5px;color:#23262c}.sub{color:var(--mut);font-size:13.5px;margin-bottom:22px}
.card{background:var(--card);backdrop-filter:blur(20px);-webkit-backdrop-filter:blur(20px);border:1px solid var(--line);border-radius:16px;padding:19px 23px;margin:15px 0;box-shadow:0 10px 30px rgba(20,24,33,.05)}h2{font-family:var(--serif);font-size:20px;font-weight:600;margin:30px 0 12px;color:#2b2f36}
ul{margin:6px 0;padding-left:20px}li{margin:8px 0;font-size:14.5px;color:#454b54}.gold{color:var(--gold)}.mut{color:var(--mut)}
.chip{display:inline-block;font-size:12px;padding:4px 11px;border-radius:9px;margin:3px 5px 3px 0;background:rgba(20,24,33,.05);border:1px solid var(--line);color:#5a606b}
.banner{background:rgba(140,123,168,.08);border-left:3px solid var(--acc);border-radius:0 12px 12px 0;padding:15px 20px;margin:16px 0;font-size:14.5px;color:#4a4f57}</style>"""

def graph_html():
    D=jload("graph_data.json")
    if not D: print("缺 graph_data.json,跳过 graph"); return
    data=json.dumps(D,ensure_ascii=False).replace("</","<"+chr(92)+"/")
    tpl=open(os.path.join(HERE,"graph_template.html"),encoding="utf-8").read()
    open(os.path.join(REP,"relationship-graph.html"),"w",encoding="utf-8").write(tpl.replace("__DATA__",data))
    print("-> reports/relationship-graph.html")

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
        ppl="".join(f'<div style="padding:6px 0;border-top:1px solid var(--line);font-size:13px"><b class=gold>{e(p["name"])}</b> <span class=mut>{e(p.get("status",""))}</span><div>{e(p.get("how",""))}</div></div>' for p in t.get("people",[]))
        ap+=f'<div class=card><h2 style="font-size:16px">{e(t["tier"])} <span class=chip style="background:var(--gold);color:#fff">{e(t.get("cadence",""))}</span></h2><div class=mut>{e(t.get("purpose",""))}</div>{ppl}</div>'
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
