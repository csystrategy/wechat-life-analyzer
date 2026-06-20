# 首次取密钥 + 解密微信本地库（macOS · 微信 4.x）

> 目标：得到 `workspace/decrypted/`（contact.db + message_*.db）和 `workspace/all_keys.json`。
> 之后所有分析、以及增量更新都基于它们，**且增量更新免密**。
> 仅处理你自己设备上、你自己的数据。这属于绕过微信加密读取本地库，处于微信 ToS 灰色地带——只分析自己的数据、自担风险。

Claude 在带用户走这个流程时：**敏感命令（sudo、给微信重签名、读内存）让用户在自己的「终端」里跑**，你给出命令并盯排错；不要替用户输开机密码。

---

## 0. 环境
- macOS 12+，Apple Silicon 或 Intel；已装 Xcode 命令行工具（`xcode-select --install`）。
- Python 3（建议建 venv）：`python3 -m venv ~/.wla-venv && ~/.wla-venv/bin/pip install pycryptodome zstandard`，把 `config.json` 的 `venv_python` 指向 `~/.wla-venv/bin/python`。
- 工作目录见 `config.json` 的 `workdir`（默认技能下的 `workspace/`）。

## 1. 准备解密工具
```bash
cd <workdir>
git clone --depth 1 https://github.com/ylytdeng/wechat-decrypt   # 解密器(纯Python,SQLCipher4)
```
本技能 `decrypt/` 下自带 `dump_mem2.c`（递归 dump 内存）和 `scan_key.c`（暴力校验密钥，备用）。编译：
```bash
cc -O2 -o <workdir>/dump_mem2 <skill>/decrypt/dump_mem2.c && codesign -s - <workdir>/dump_mem2
```

## 2. ⚠️ 关键：微信版本要对
- **微信 4.1.10 等较新版【不把密钥留在内存里】，抓不到。** 实测可行的是 **4.1.2**（也是社区工具实测版本）。
- 若当前微信 >4.1.2：从官方 CDN 降级到 4.1.2（同代、数据兼容）：
  `https://dldir1v6.qq.com/weixin/Universal/Mac/WeChatMac_4.1.2.dmg`
  下载后**务必验签**（应为 `Developer ID Application: Tencent Mobile International Limited`、已公证）再装。
- 4.0.x 也可（用 `x'...'` 字符串法），但官方 CDN 多已下架。

## 3. ⚠️ 关键：做一个"不可改的 adhoc 副本"来读内存
macOS 读别的进程内存要 `task_for_pid`，而微信是硬化运行时(hardened runtime)挡着。解法是把微信复制一份、签成 ad-hoc（去掉硬化），**全程不用关 SIP**：

```bash
SRC=/Applications/WeChat.app ; COPY=<workdir>/WeChat.app
pkill -x WeChat; sleep 2
rm -rf "$COPY"; cp -R "$SRC" "$COPY"
xattr -cr "$COPY"
codesign --force --deep --sign - "$COPY"          # 签成 adhoc
codesign -dv "$COPY" 2>&1 | grep flags             # 应为 flags=0x2(adhoc)
```
**坑：微信 4.1.2 有反篡改，重启会把签名自动改回硬化。** 破法——把副本主程序设为不可改：
```bash
chflags uchg "$COPY/Contents/MacOS/WeChat"
chflags uchg "$COPY/Contents/MacOS/WeChatAppEx.app/Contents/MacOS/WeChatAppEx" 2>/dev/null
open -n "$COPY"      # 启动副本
```
启动后再 `codesign -dv "$COPY"` 确认仍是 adhoc（没被改回）。

## 4. 登录 + 让密钥进内存
- 在弹出的副本窗口里**手机扫码登录**（重签名会让登录失效，正常）。
- 登录后**点开 5~10 个不同聊天/群**，让各数据库的密钥加载进内存。
- 想分析手机上的完整历史，先在手机微信「设置→通用→聊天记录迁移与备份」把要分析的聊天**迁移到这台电脑**。

## 5. Dump 内存（需要一次 root/密码）
让用户在终端跑（或用 `osascript ... with administrator privileges` 弹系统密码框）：
```bash
PID=$(pgrep -x WeChat | head -1)
sudo <workdir>/dump_mem2 $PID <workdir>/wechat_mem.bin      # ~4-5GB, 只读, 不联网
```
> 验证副本仍是 adhoc 且就是这个 PID 在跑（`ps -p $PID -o comm=` 路径应在 workdir）。

## 6. 抓密钥（4.1.2：x'...' 字符串法）
4.1.2 把每库密钥以 `x'<64位key><32位salt>'` 留在内存。用 Python 抓出来、按 salt 匹配到各 .db，写 `all_keys.json`：
```python
# <workdir>/extract_keys.py  —— Claude 可直接生成并运行(纯本地)
import re, mmap, os, json, hashlib, glob, sqlite3
WD=os.path.dirname(os.path.abspath(__file__))
DBDIR=json.load(open(os.path.join(os.path.dirname(WD),'config.json')))['wechat_db_storage'] if False else None
# 从 config 读 wechat_db_storage(加密库) 与 keys_file
cfg=json.load(open(glob.glob(os.path.expanduser('~/.claude/skills/wechat-life-analyzer/config.json'))[0]))
DBDIR=cfg['wechat_db_storage']
keys_by_salt={}
with open(os.path.join(WD,'wechat_mem.bin'),'rb') as f:
    mm=mmap.mmap(f.fileno(),0,prot=mmap.PROT_READ)
    for s in set(m.group().decode() for m in re.finditer(rb"x'[0-9a-fA-F]{96}'",mm)):
        inner=s[2:-1]; keys_by_salt[inner[64:].lower()]=inner[:64].lower()
all_keys={}; 
for root,_,files in os.walk(DBDIR):
    for fn in files:
        if not fn.endswith('.db') or fn.endswith(('-wal','-shm')): continue
        p=os.path.join(root,fn); hdr=open(p,'rb').read(16)
        if hdr[:15]==b'SQLite format 3': continue
        salt=hdr.hex().lower()
        if salt in keys_by_salt: all_keys[os.path.relpath(p,DBDIR)]={'enc_key':keys_by_salt[salt]}
all_keys['_db_dir']=DBDIR
json.dump(all_keys,open(cfg['keys_file'],'w'),ensure_ascii=False,indent=2)
print('抓到',len([k for k in all_keys if not k.startswith('_')]),'个库密钥 ->',cfg['keys_file'])
```
> 若抓到 0 个：微信版本可能不对(降到4.1.2)、或副本被改回硬化(看 chflags)、或还没点开足够多聊天。
> 抓完后内存 dump（含密钥）可删：`rm <workdir>/wechat_mem.bin`。

## 7. 解密
配置 `wechat-decrypt` 的 `config.json`（`db_dir` 指向 `wechat_db_storage`、`keys_file` 指向我们的 all_keys.json、`decrypted_dir` 指向 `config.decrypted_dir`），然后：
```bash
cd <workdir>/wechat-decrypt && <venv_python> decrypt_db.py        # 全量
# 之后增量(免密、免dump): <venv_python> decrypt_db.py -i
```
成功后 `workspace/decrypted/` 里就有 `contact/contact.db`、`message/message_*.db`。回到 SKILL.md 的阶段一第3步继续。

## 之后的增量更新（免密！）
密钥稳定。日常微信用着会自动把新消息同步到本地加密库，直接 `engine.py decrypt`（增量、纯Python、不用密码、不用 dump）即可刷新。只有当微信新建了"无密钥的新分片"或你换了微信版本时，才需要重跑 5-7 步补一次密钥。

## 收尾
- 用完可退出副本、用回 `/Applications` 正常微信；副本和备份可留作下次增量。
- `wechat_mem.bin` 这种含密钥的中间文件建议删除。
- 提醒：解密产物含大量隐私，妥善保管、勿外传。
