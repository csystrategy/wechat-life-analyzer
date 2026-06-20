#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WeChat Life Analyzer — 数据引擎 (可移植, 自动探测, 不写死任何人)。
子命令:
  setup        自动探测 db_storage / 解密目录 / 本人wxid, 写 config.json
  decrypt      用已保存的 all_keys.json 增量解密(免密)。需先完成首次取密钥(见 docs/decrypt-onboarding.md)
  metrics      生成全量关系指标 + 当期快照(用于'走近/走远'对比)
  timeaware N  为最相关的 N 人(默认50)抽取【月度时间线+当前处境+一年前锚点】(跨所有分片,按真实时间)
  dimensions   抽取本人近一年关于 工作/投资/感情 的发言语料(用于人生维度分析)
  graph        计算核心人之间的共群连接(关系图谱的边) + 节点数据

关键原则(踩过的坑,已内建):
  * 一个人的消息分散在多个 message_*.db 分片里 —— 永远遍历全部分片再聚合(否则'最近对话'会取到旧的)。
  * days_since/趋势 必须基于全分片聚合的真实最大时间。
  * 抽样务必带时间戳、并把'最近段=当前处境'单列(供AI先读最近、不套旧叙事)。
所有路径/本人身份来自 config.json(由 setup 自动生成,可手改)。
"""
import sqlite3, glob, os, hashlib, json, time, datetime, re, collections, sys, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
# 可写数据放用户主目录,与安装位置解耦(普通skill clone 或 plugin 安装都能写)
DATA = os.environ.get("WLA_HOME") or os.path.expanduser("~/.wechat-life-analyzer")
os.makedirs(DATA, exist_ok=True)
CFG_PATH = os.path.join(DATA, "config.json")
try:
    import zstandard as _zs; _Z = _zs.ZstdDecompressor()
except Exception:
    _Z = None

def load_cfg():
    return json.load(open(CFG_PATH, encoding="utf-8")) if os.path.exists(CFG_PATH) else {}

def dec(b):
    if isinstance(b, (bytes, bytearray)):
        b = bytes(b)
        if _Z and b[:4] == b"\x28\xb5\x2f\xfd":
            try: b = _Z.decompress(b)
            except Exception: pass
        try: return b.decode("utf-8", "replace")
        except Exception: return ""
    return b or ""

def msg_dbs(decrypted):
    return [m for m in sorted(glob.glob(os.path.join(decrypted, "message", "message_*.db")))
            if not any(k in os.path.basename(m) for k in ["fts", "resource", "media", "biz"])]

def contact_map(decrypted):
    c = sqlite3.connect(os.path.join(decrypted, "contact", "contact.db"))
    name, lt = {}, {}
    for u, l, nick, rem in c.execute("SELECT username,local_type,nick_name,remark FROM contact"):
        name[u] = ((rem or "").strip() or (nick or "").strip() or u); lt[u] = l
    c.close()
    return name, lt

def md5h(u): return hashlib.md5(u.encode()).hexdigest()

# ---------------- setup ----------------
def cmd_setup(args):
    home = os.path.expanduser("~")
    base = os.path.join(home, "Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files")
    cands = glob.glob(os.path.join(base, "*", "db_storage"))
    # 选 message 目录最近修改的账号
    def recency(p):
        md = os.path.join(p, "message")
        try: return os.path.getmtime(md if os.path.isdir(md) else p)
        except OSError: return 0
    cands.sort(key=recency, reverse=True)
    db_storage = cands[0] if cands else ""
    cfg = load_cfg()
    cfg.setdefault("wechat_db_storage", db_storage)   # 加密库(微信容器内)
    cfg.setdefault("workdir", os.path.join(DATA, "workspace"))
    cfg.setdefault("decrypted_dir", os.path.join(cfg["workdir"], "decrypted"))
    cfg.setdefault("keys_file", os.path.join(cfg["workdir"], "all_keys.json"))
    cfg.setdefault("decrypt_tool_dir", os.path.join(cfg["workdir"], "wechat-decrypt"))
    cfg.setdefault("venv_python", sys.executable)
    os.makedirs(cfg["workdir"], exist_ok=True)
    # 若已解密, 探测本人wxid
    me = cfg.get("me", "")
    if not me and os.path.isdir(os.path.join(cfg["decrypted_dir"], "message")):
        me = detect_me(cfg["decrypted_dir"])
    cfg["me"] = me
    json.dump(cfg, open(CFG_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("[setup] 写入", CFG_PATH)
    print("  加密库(微信容器):", db_storage or "未找到(微信未登录/版本不符?)")
    print("  解密输出目录:", cfg["decrypted_dir"], "(存在)" if os.path.isdir(cfg["decrypted_dir"]) else "(尚未解密)")
    print("  本人wxid:", me or "(待解密后自动探测)")

def detect_me(decrypted):
    """1对1表里反复出现的'非对方'发送者 = 本人。"""
    name, _ = contact_map(decrypted); md5u = {md5h(u): u for u in name}
    cnt = collections.Counter()
    for mp in msg_dbs(decrypted)[:4]:
        conn = sqlite3.connect(mp); n2 = {r: u for r, u in conn.execute("SELECT rowid,user_name FROM Name2Id")}
        for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%' LIMIT 400"):
            u = md5u.get(t[4:])
            if not u or u.endswith("@chatroom"): continue
            for (sid,) in conn.execute(f'SELECT DISTINCT real_sender_id FROM "{t}" LIMIT 4'):
                su = n2.get(sid)
                if su and su != u: cnt[su] += 1
        conn.close()
    return cnt.most_common(1)[0][0] if cnt else ""

# ---------------- decrypt (incremental, no password) ----------------
def cmd_decrypt(args):
    cfg = load_cfg()
    tool = cfg.get("decrypt_tool_dir"); py = cfg.get("venv_python", sys.executable)
    if not (tool and os.path.isdir(tool) and os.path.exists(cfg.get("keys_file", ""))):
        print("[decrypt] 还没完成首次取密钥。请先按 docs/decrypt-onboarding.md 跑通一次(生成 all_keys.json)。"); return
    # wechat-decrypt 的 decrypt_db.py 走自己的 config.json; 这里直接调它的增量模式
    r = subprocess.run([py, "decrypt_db.py", "-i"], cwd=tool, capture_output=True, text=True, timeout=1800)
    print((r.stdout or "").strip().splitlines()[-1] if r.stdout.strip() else (r.stderr or "")[-300:])

# ---------------- metrics + snapshot ----------------
def per_contact_metrics(decrypted):
    name, lt = contact_map(decrypted); md5u = {md5h(u): u for u in name}; now = int(time.time())
    ind = {}
    for mp in msg_dbs(decrypted):
        conn = sqlite3.connect(mp); n2 = {r: u for r, u in conn.execute("SELECT rowid,user_name FROM Name2Id")}
        for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"):
            u = md5u.get(t[4:])
            if not u or u.endswith("@chatroom") or u.endswith("@openim"): continue
            try: rows = conn.execute(f'SELECT real_sender_id,create_time FROM "{t}" WHERE create_time>0').fetchall()
            except Exception: continue
            if not rows: continue
            d = ind.setdefault(u, dict(total=0, mine=0, theirs=0, last=0, r30=0, r90=0, p90_180=0))
            for sid, ct in rows:
                d["total"] += 1
                if n2.get(sid) != u: d["mine"] += 1
                else: d["theirs"] += 1
                d["last"] = max(d["last"], ct); age = (now - ct) / 86400
                if age <= 30: d["r30"] += 1
                if age <= 90: d["r90"] += 1
                if 90 < age <= 180: d["p90_180"] += 1
        conn.close()
    out = []
    for u, d in ind.items():
        if d["total"] < 20: continue
        out.append(dict(user=u, name=name.get(u, u), is_friend=lt.get(u) == 1, total=d["total"],
            mine=d["mine"], theirs=d["theirs"], last=d["last"], days_since=int((now - d["last"]) / 86400),
            r30=d["r30"], r90=d["r90"], trend=round(d["r90"] / max(1, d["p90_180"]), 2)))
    return out, now

def cmd_metrics(args):
    cfg = load_cfg(); decrypted = cfg["decrypted_dir"]
    recs, now = per_contact_metrics(decrypted)
    os.makedirs(os.path.join(DATA, "workspace"), exist_ok=True)
    json.dump(recs, open(os.path.join(DATA, "workspace", "metrics.json"), "w"), ensure_ascii=False)
    # 快照(供 digest 对比走近/走远)
    hist = os.path.join(DATA, "history"); os.makedirs(hist, exist_ok=True)
    snap = {"ts": now, "date": datetime.datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M"),
            "contacts": {r["user"]: {k: r[k] for k in ("name", "total", "days_since", "r30", "r90")} for r in recs}}
    fn = os.path.join(hist, "snap_" + datetime.datetime.fromtimestamp(now).strftime("%Y%m%d_%H%M") + ".json")
    json.dump(snap, open(fn, "w"), ensure_ascii=False)
    json.dump(snap, open(os.path.join(hist, "latest.json"), "w"), ensure_ascii=False)
    print(f"[metrics] {len(recs)} 个关系 -> workspace/metrics.json + 快照 {os.path.basename(fn)}")

# ---------------- time-aware per-person extraction ----------------
def select_relevant(recs, n):
    pool = [r for r in recs if (r["days_since"] <= 190 and r["total"] >= 120) or (r["total"] >= 4000 and r["days_since"] <= 420)]
    pool.sort(key=lambda x: -(x["r90"] * 3 + x["total"] / 50 - x["days_since"]))
    top = pool[:n]
    heavy = [x for x in pool[n:] if x["total"] >= 8000]
    names = {t["name"] for t in top}
    for h in heavy:
        if h["name"] not in names: top.append(h)
    return top

def cmd_timeaware(args):
    cfg = load_cfg(); decrypted = cfg["decrypted_dir"]; now = int(time.time())
    n = int(args[0]) if args else 50
    recs, _ = per_contact_metrics(decrypted)
    sel = select_relevant(recs, n)
    name, _ = contact_map(decrypted)
    outdir = os.path.join(DATA, "workspace", "people"); os.makedirs(outdir, exist_ok=True)
    dbs = msg_dbs(decrypted); manifest = []
    for c in sel:
        u = c["user"]; t = "Msg_" + md5h(u); allm = []
        for mp in dbs:
            conn = sqlite3.connect(mp); n2 = {r: un for r, un in conn.execute("SELECT rowid,user_name FROM Name2Id")}
            try:
                for sid, ct, mc in conn.execute(f'SELECT real_sender_id,create_time,message_content FROM "{t}" WHERE local_type=1 AND create_time>0'):
                    allm.append((ct, "对方" if n2.get(sid) == u else "我", dec(mc)))
            except Exception: pass
            conn.close()
        if len(allm) < 6: continue
        allm.sort(key=lambda x: x[0])
        ym = collections.Counter(datetime.datetime.fromtimestamp(ct).strftime("%Y-%m") for ct, _, _ in allm)
        months = sorted(ym)[-18:]
        def clean(rows):
            o = []
            for ct, who, x in rows:
                x = re.sub(r"^[^\s:]{1,40}:\n", "", x).strip()
                if x and not x.startswith("<"): o.append((ct, who, x[:160]))
            return o
        cur = clean(allm)[-40:]
        old = clean([r for r in allm if now - 455 * 86400 < r[0] < now - 365 * 86400])[:12]
        p = os.path.join(outdir, f"{u}.txt")
        with open(p, "w") as f:
            f.write(f"联系人:{c['name']} | 历史总{c['total']}条(我{c['mine']}/对方{c['theirs']}) 最近{c['days_since']}天前 趋势{c['trend']}\n")
            f.write("\n【月度互动时间线(条数,看关系涨落)】\n  " + " | ".join(f"{m}:{ym[m]}" for m in months) + "\n")
            f.write("\n【约一年前的对话锚点(那时)】\n")
            for ct, who, x in old: f.write(f"  [{datetime.datetime.fromtimestamp(ct).strftime('%y-%m-%d')}] {who}: {x}\n")
            f.write("\n【最近的对话 = 当前真实处境(最重要,先读这段)】\n")
            for ct, who, x in cur: f.write(f"  [{datetime.datetime.fromtimestamp(ct).strftime('%y-%m-%d')}] {who}: {x}\n")
        manifest.append({k: c[k] for k in ("name", "user", "total", "mine", "theirs", "days_since", "r90", "trend")} | {"path": os.path.abspath(p)})
    json.dump(manifest, open(os.path.join(DATA, "workspace", "people_manifest.json"), "w"), ensure_ascii=False, indent=1)
    print(f"[timeaware] {len(manifest)} 人 -> workspace/people/*.txt + people_manifest.json")

# ---------------- dimension corpora (work/love/invest) ----------------
KW = {
 "invest": "股|仓位|建仓|加仓|减仓|买入|卖出|止损|止盈|亏|涨|跌|A股|美股|港股|期权|杠杆|比特币|定投|收益|回撤|标的|大盘|德州|扑克|筹码|套牢|割肉|基金|ETF|做多|做空|打新",
 "work": "离职|跳槽|辞职|老板|项目|创业|公司|融资|赛道|商业化|招聘|猎头|年终奖|奖金|绩效|面试|offer|买方|卖方|分析师|agent|产品|合伙|股权|职业|工资|薪|平台|客户|总裁|转行|大厂|交接|汇报|团队",
 "love": "结婚|相亲|喜欢|分手|谈恋爱|女朋友|男朋友|对象|约会|暧昧|孤独|陪|想你|爱|亲密|领证|单身|前任|感情|心动|寂寞|抱抱|想要|在一起",
}
def cmd_dimensions(args):
    cfg = load_cfg(); decrypted = cfg["decrypted_dir"]; me = cfg.get("me", ""); now = int(time.time())
    if not me: print("[dimensions] config 里没有 me(本人wxid),先运行 setup"); return
    name, _ = contact_map(decrypted); md5u = {md5h(u): u for u in name}
    out = os.path.join(DATA, "workspace", "dimensions"); os.makedirs(out, exist_ok=True)
    cut = now - 365 * 86400; buckets = {k: [] for k in KW}
    for mp in msg_dbs(decrypted):
        conn = sqlite3.connect(mp); n2 = {r: u for r, u in conn.execute("SELECT rowid,user_name FROM Name2Id")}
        meids = {r for r, u in n2.items() if u == me}
        if not meids: conn.close(); continue
        for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"):
            u = md5u.get(t[4:]); peer = name.get(u, "群" if (u and u.endswith("@chatroom")) else "?")
            try:
                for sid, ct, mc in conn.execute(f'SELECT real_sender_id,create_time,message_content FROM "{t}" WHERE local_type=1 AND create_time>{cut}'):
                    if sid not in meids: continue
                    x = re.sub(r"^[^\s:]{1,40}:\n", "", dec(mc)).strip()
                    if not (3 <= len(x) <= 300) or x.startswith("<"): continue
                    for k, pat in KW.items():
                        if re.search(pat, x): buckets[k].append((ct, peer, x))
            except Exception: continue
        conn.close()
    import random; random.seed(3)
    for k in KW:
        rows = sorted(buckets[k], key=lambda x: -x[0])
        keep = rows[:180] + (random.sample(rows[180:], min(70, max(0, len(rows) - 180))) if len(rows) > 180 else [])
        keep.sort(key=lambda x: -x[0])
        with open(os.path.join(out, f"my_{k}.txt"), "w") as f:
            f.write(f"# 本人近一年关于【{k}】的发言({len(keep)}条,共匹配{len(rows)})\n\n")
            for ct, peer, x in keep:
                f.write(f"[{datetime.datetime.fromtimestamp(ct).strftime('%y-%m-%d')} 对{str(peer)[:10]}] {x}\n")
        print(f"  {k}: 匹配{len(rows)} -> 取样{len(keep)}")
    print("[dimensions] -> workspace/dimensions/my_{work,love,invest}.txt")

# ---------------- graph edges (co-membership) ----------------
def cmd_graph(args):
    cfg = load_cfg(); decrypted = cfg["decrypted_dir"]
    man = json.load(open(os.path.join(DATA, "workspace", "people_manifest.json")))
    sel = {x["user"] for x in man}; name, _ = contact_map(decrypted); md5u = {md5h(u): u for u in name}
    import itertools
    pair = collections.Counter(); via = collections.defaultdict(list)
    for mp in msg_dbs(decrypted):
        conn = sqlite3.connect(mp); n2 = {r: u for r, u in conn.execute("SELECT rowid,user_name FROM Name2Id")}
        for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'"):
            g = md5u.get(t[4:])
            if not g or not g.endswith("@chatroom"): continue
            members = set()
            for (sid,) in conn.execute(f'SELECT DISTINCT real_sender_id FROM "{t}"'):
                u = n2.get(sid)
                if u in sel: members.add(u)
            for a, b in itertools.combinations(sorted(members), 2):
                pair[(a, b)] += 1
                if len(via[(a, b)]) < 3: via[(a, b)].append(name.get(g, g))
        conn.close()
    edges = [{"a": name.get(a, a), "b": name.get(b, b), "weight": w, "via": via[(a, b)][:3]} for (a, b), w in pair.items()]
    edges.sort(key=lambda e: -e["weight"])
    json.dump(edges, open(os.path.join(DATA, "workspace", "edges.json"), "w"), ensure_ascii=False, indent=1)
    print(f"[graph] {len(edges)} 条共群连接 -> workspace/edges.json")

CMDS = {"setup": cmd_setup, "decrypt": cmd_decrypt, "metrics": cmd_metrics,
        "timeaware": cmd_timeaware, "dimensions": cmd_dimensions, "graph": cmd_graph}
if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in CMDS:
        print(__doc__); sys.exit(0)
    CMDS[sys.argv[1]](sys.argv[2:])
