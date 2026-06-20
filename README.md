# WeChat Life Analyzer · 微信人生分析器

把你**自己的**微信聊天记录变成一套关系与人生的"操作系统"。产出：
- 🕸️ **关系图谱**：谁是谁、按圈层聚类、谁和谁通过共同的群连着。
- 📇 **逐人相处建议**：每个重要的人——当前是什么关系、该多久联系、**具体怎么主动开口**、相处策略。
- 🪞 **自我观察**：从你的聊天里读你在 **工作 / 投资 / 亲密关系** 三条线上的真实状况。
- 🧭 **人生诊断与建议**：把三条线串成"人生主线"，给具体可执行的建议和几句实话。

> 全部在你**本地**完成，产出只存本地。这是极度私密的东西，**别外传**。

## 安装

**方式 A · 插件一键装（推荐）** —— 在 Claude Code 里依次输入：
```
/plugin marketplace add csystrategy/wechat-life-analyzer
/plugin install wechat-life-analyzer@wechat-life-analyzer
```

**方式 B · 手动装** —— 把技能目录拷进你的 skills 文件夹：
```
git clone https://github.com/csystrategy/wechat-life-analyzer
cp -R wechat-life-analyzer/skills/wechat-life-analyzer ~/.claude/skills/
```

> 你的私密数据（解密库、抽样、报告）一律存在 `~/.wechat-life-analyzer/`，**和代码、和这个仓库彻底分开**，永远不会被提交或外传。

## 怎么用
装好后，在 Claude Code 里说：
> **「分析我的微信」** 或 **「做我的关系图谱和人生体检」**

Claude 会按 `SKILL.md` 带你走：
1. **首次**：跟着 `docs/decrypt-onboarding.md` 解密你的微信本地库（需要下载微信 4.1.2、扫码登录、输一次开机密码——稍折腾，但只此一次）。
2. **分析**：自动算指标、抽取（带时间维度的）对话、做 AI 深读、出三张网页。
3. **以后**：日常微信用着会自动同步新消息，再分析时**增量更新、免密码**。

## 要求
- macOS 12+（Apple Silicon 或 Intel）、微信 4.x（首次取密钥需降级到 **4.1.2**）。
- Xcode 命令行工具、Python 3 + `pycryptodome zstandard`。
- 解密器：首次会让你 `git clone https://github.com/ylytdeng/wechat-decrypt`。

## 目录
```
SKILL.md                 给 Claude 的总编排 + 分析铁律
config.json              自动探测生成(路径/本人wxid),可手改
docs/
  decrypt-onboarding.md  首次解密全流程(macOS·微信4.1.2)
  analysis-playbook.md   AI 分析的提示词与产出格式
engine/
  engine.py              数据引擎: setup/decrypt/metrics/timeaware/dimensions/graph
  viz.py                 三张网页生成器
decrypt/                 自带的 dump/scan 工具源码(C)
workspace/               中间产物(解密库、抽样、各JSON) —— 私密,勿外传
reports/                 生成的 HTML
history/                 历次快照(用于"谁走近/走远")
```

## 它做对的几件事（别的"顺读聊天"做不到）
- **有时间维度**：不是把聊天当文章顺读，而是看每段关系**怎么随时间变化、此刻的真实处境**（避免把"现任老板/正在离职"读成"老朋友约饭"）。
- **跨分片聚合**：一个人的消息分散在多个数据库分片里，全部合起来算，"最近对话"才真的是最近。
- **区分真心与玩笑**：聊天满是嘴炮夸张，不会把"我九位数炒股"这种段子当事实。

## ⚠️ 注意
- 解密属于微信 ToS 灰色地带，**只分析你自己设备上、你自己的数据，自担风险**。
- AI 的判断**未必都对**，看到不像你的地方就纠正它——它会据此重算。
- 不构成任何专业建议。
