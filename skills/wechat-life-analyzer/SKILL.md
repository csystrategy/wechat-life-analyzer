---
name: wechat-life-analyzer
description: 把自己的微信聊天记录变成一套"人生与关系操作系统"。从导出/解密聊天记录开始,产出:① 关系图谱(谁是谁、共群连接) ② 每个人的相处建议(联系频次/怎么主动/策略) ③ 自我观察(工作/投资/亲密关系三维深读) ④ 人生方向的诊断与建议。任何人把本技能放进 ~/.claude/skills/ 都能对自己的微信做同样的分析。当用户说"分析我的微信/做我的关系图谱/帮我看看我的人际和人生/wechat-life-analyzer/我想对自己的聊天记录做分析"时触发。仅本地处理,极度私密。
---

# wechat-life-analyzer — 用微信聊天记录给自己做一次"人生体检"

你的任务:带用户从零完成对**他自己**微信聊天记录的深度分析,产出关系图谱+逐人相处建议+三维自我观察+人生诊断。**这是用户极度私密的数据,只在本地处理,产出只存本地,绝不外传。**

> 适用:macOS + 微信 4.x。引擎全部自动探测路径/本人身份,不写死任何人。

## ⛳️ 必须遵守的分析铁律(这套方法是反复踩坑换来的,违背就会给出可笑的建议)

1. **时间维度是命根子。** 聊天记录绝不能当成一篇文章顺着读。每个人都要先看【月度时间线】和【最近的对话=当前真实处境】,**先用现实世界的大白话说清"此刻这个人对TA是什么角色、你俩最近正在发生什么"(例:现任老板/正在离职交接;刚分手的前任;即将入职公司的同事)**,再讲关系怎么随时间变化,最后才给建议。任何建议必须贴合**当前处境**——给一个"正在离职、要交接给老板"的关系建议"每季度约饭"就是笑话。
2. **跨所有 message 分片聚合。** 一个人的消息分散在多个 message_*.db 里;只读一个分片会把"最近对话"取成几年前的旧内容。引擎已内建,但你读数据时也要警惕"日期对不对得上"。
3. **区分真心 vs 玩笑/调情/夸张/别人的揶揄。** 聊天满是嘴炮和夸张——炫富、夸大的盈亏数字、调情式的玩笑话，很可能是段子或别人的调侃，不要当字面事实。逐条判断哪些是真情实感、哪些是玩笑。把这点搞错会得出严重错误的结论。
4. **不要套旧叙事/模板。** 哪怕你之前对某人有印象,也要以【最近的对话】为准重新判断。宁可说"材料不足、我不编",也不要编。
5. **诚实、不 oversell、不回避。** 该说的实话(单向消耗、回避承诺、把段子当真等)要说,但带着善意;并提醒用户"判断可能有错,觉得不对就纠正我"。

## 阶段一 · 准备数据(机械层)

1. `<venv_python> engine/engine.py setup` —— 自动探测微信加密库路径、写 `config.json`(若已解密会自动探测本人 wxid)。读出 config 给用户确认。
2. **首次取密钥+解密**:检查 `config.json` 的 `keys_file` 与 `decrypted_dir` 是否已存在。
   - 若**尚未解密** → 打开并**逐步带用户走** `docs/decrypt-onboarding.md`(下载微信4.1.2 → 重签名不可改副本 → dump内存 → 抓密钥 → 解密)。这一步需要用户输密码、登录微信,只能引导、不能全自动;敏感命令让用户在自己终端跑,你给命令并盯排错。
   - 若**已解密** → 跑 `engine/engine.py decrypt`(用已存密钥**增量免密**更新最新消息)。
3. 依次跑:`engine/engine.py metrics` → `timeaware 50` → `dimensions` → `graph`。
   产出在 `workspace/`:`metrics.json`、`people/*.txt`(每人时间线+当前处境)、`people_manifest.json`、`dimensions/my_{work,love,invest}.txt`、`edges.json`。

## 阶段二 · AI 分析(你来做,严守上面的铁律)

读 `docs/analysis-playbook.md` 拿到每一步的具体提示词与产出格式。按顺序做(数据量大时用 Workflow 工具并行,但**每个子智能体都必须遵守时间铁律、且高 effort**;若发现子智能体在套旧叙事/读错时间,改为你亲自逐个读 `workspace/people/*.txt` —— 宁慢勿错):

- **A. 逐人时序画像**:对 `people_manifest.json` 里每个人,读其 `workspace/people/<user>.txt`,产出 `current_status`(当前处境,先写)、`arc`(关系弧线)、类别、谁更主动、真心vs玩笑、建议频次、**怎么主动(贴合当前处境的具体开场)**、相处策略、优先级。汇总存 `workspace/profiles.json`。
- **B. 关系图谱数据**:把 profiles + `edges.json` 合成节点(按关系类型聚类、按聊天量定大小)与边,存 `workspace/graph_data.json`。
- **C. 三维自我观察**:分别读 `dimensions/my_work.txt`/`my_invest.txt`/`my_love.txt`(感情可加上几位情感线人物的双向对话),各做证据驱动的深读(当前状况/证据引用/模式/盲点/建议),再综合成"人生主线"。存 `workspace/life_advice.json`。
- **D. 联系策略 + 人生建议**:基于 profiles(当前处境)产出分层行动计划、本周该做的事、"如何主动"的硬原则、整体人生建议、一句实话。存 `workspace/contact_strategy.json`。

## 阶段三 · 出可视化

`<venv_python> engine/viz.py all` —— 读 workspace 的 graph_data/life_advice/contact_strategy.json,生成并可 `open`:
`reports/relationship-graph.html`(关系图谱)、`reports/life-advice.html`(人生建议)、`reports/contact-strategy.html`(联系策略)。
把三个网页打开给用户,并在对话里给出关键结论摘要。

## 周期复用(可选)
本技能也支持"每隔一段时间复跑":`decrypt`(增量) → `metrics`(生成新快照) → 对比 `history/` 里最近两次快照算"谁走近/走远",再做 B/D 的增量更新。这部分见 `docs/analysis-playbook.md` 的"周期 digest"。

## 给用户的话术
- 强调隐私:全程本地、产出只存本地、别外传。
- 诚实标注哪些是 AI 推断、可能有误,请用户纠正。
- 首次解密较折腾(需下载旧版微信、输密码、重登录),如实告知;之后增量更新免密。
