# 分析手册（阶段二的具体打法）

> 前提：阶段一已跑完，`workspace/` 里有 metrics.json、people/*.txt、people_manifest.json、dimensions/my_*.txt、edges.json。
> **全程严守 SKILL.md 的 5 条铁律**（时间维度、跨分片、真心vs玩笑、不套旧叙事、诚实）。
> 数据量大时可用 Workflow 并行；但若发现子智能体读错时间/套旧模板，立刻改为你（主 Claude）亲自逐个读 `workspace/people/<user>.txt`——宁慢勿错。每个 people 文件已分三段：月度时间线 / 一年前锚点 / **最近的对话=当前处境（先读这段）**。

---

## A. 逐人时序画像 → workspace/profiles.json

对 `people_manifest.json` 的每个人，读 `path` 指向的文件。给每人产出对象（务必先写 current_status）：

```
{ name, current_status, arc, category, reciprocity, value, real_vs_banter,
  recommended_cadence, how_to_initiate, strategy, priority }
```
逐人提示词（每人一个，high effort）：
> 用 Read 读取 <path>。这是用户与「<name>」的时间感知材料：① 月度互动时间线 ② 一年前锚点 ③ 【最近的对话=当前真实处境】。指标：总<total>条(我<mine>/对方<theirs>)、最近<days_since>天前、趋势<trend>。
> 按顺序：(1) **先重点读【最近的对话】，用现实世界大白话写 current_status**——此刻这个人对用户是什么角色、你俩最近正在发生什么真实的事（如"现任老板，用户正在离职交接"），不准套旧印象。(2) arc：用时间线+对比"一年前"和"现在"两段，说关系怎么变的。(3) 类别、谁更主动、对用户的价值、(涉暧昧则)逐条标真心/玩笑、建议频次、**怎么主动（贴合当前处境的具体开场，正在离职/分手/收尾要分"现在"和"之后"）**、相处策略、优先级(高/中/低)。
> 铁律：任何建议必须和当前处境对得上。区分真心与调情/夸张。材料不足就说不足，别编。

汇总所有人 → `workspace/profiles.json`（数组，每项含上面字段 + user）。

## B. 关系图谱数据 → workspace/graph_data.json

把 profiles 聚类成关系圈层（家人/事业人脉/同事/密友/朋友玩伴/情感线/前任/功能…），结合 `edges.json`，组装：
```
{ "nodes":[{id,name,total,days_since,trend,category(=cluster),role(=current_status一句话),
            cadence,priority,how(=how_to_initiate),strategy}],
  "links":[{source,target,weight,via}],   // 来自 edges.json，两端都在 nodes 里
  "clusters":[...类型], "headline":"一句话全景" }
```
（可由你直接用 Python 拼，或让一个 agent 聚类后你组装。）

## C. 三维自我观察 → workspace/life_advice.json

分别读 `dimensions/my_work.txt`、`my_invest.txt`、`my_love.txt`（感情维度可再用 `people/*.txt` 里几位情感线人物的双向对话补充）。每维一个 high-effort agent：
> 仔细通读 <file>（用户近一年关于【X】的本人发言，每行带日期）。**注意时间**：近期发言权重更高。产出：current_picture(当前真实状况)、evidence(≥6条引用,标日期;**区分真心与玩笑/别人揶揄/夸张——别把段子当事实**)、patterns、blindspots、advice。

再综合三维 → 人生主线：
```
{ dimensions:[work,invest,love 各上面结构],
  synthesis:{ life_mainline, connections(三维如何互相牵连), priorities[{rank,focus,why}],
              by_dimension{work[],love[],invest[]}, hard_truths[], one_thing } }
```
存 `workspace/life_advice.json`。

## D. 联系策略 + 人生建议 → workspace/contact_strategy.json

基于 profiles（**每个人的 current_status**）综合：
```
{ overview,
  action_plan:[{tier, cadence, purpose, people:[{name, status(此刻处境一句话), how}]}],
  this_week:[{name, action}],            // 6-8件本周可照做的具体事
  proactive_principles:[...],            // 针对"不主动/玩笑挡真心/保留退路"的硬原则
  by_purpose:{career[],intimacy[],support[]},
  life_advice:[{area,advice}], hard_truth }
```
综合提示词要点：分层依据**当前处境**（正在离职/分手/收尾的人，建议要分"现在/之后"）；"怎么主动"具体可执行；诚实点出单向消耗、回避承诺；融入用户的整体背景（职业转型、在做什么、心理模式）。

## 谁该认真考虑/结婚（可选专题）

若用户问"该跟谁认真在一起/结婚"：只取情感线人物，逐人读其双向对话（先看当前处境+arc），**严格区分真心与调情**，评 availability（排除已婚/前任）、双向投入、情感深度、用户在这段里是敞开还是设防、marriage_fit(1-5)，再排序推荐 + 该排除谁 + 一句"真正的瓶颈往往不是人选，而是用户能否真投入"。

## 周期 digest（可选，每隔一段时间复跑）

1. `engine.py decrypt`（增量免密）→ `engine.py metrics`（生成新快照到 history/）。
2. 读 `history/` 最近两份快照，对每个联系人比较 r30/r90 → 谁**走近**(上升)、谁**走远**(下降)、有无新冒出的高频关系/突然安静的重要关系。
3. 重抽变化最大者的近期对话（`engine.py timeaware`），按 A 的方法读，做"行为诊断"（最近对某重要人物的说话/做事是否欠妥）。
4. 结合用户当前目标（可让用户维护一份 goals），给"基于目标该主动联系谁"。
5. 产出一期报告存 `reports/`，并发桌面通知。
