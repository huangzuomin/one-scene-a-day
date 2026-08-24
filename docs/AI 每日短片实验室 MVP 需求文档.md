# AI 每日短片实验室 MVP 需求文档

## 1. 项目名称

暂定名称：

**AI 每日短片实验室**

内部代号可使用：

**One Scene a Day / 一日一幕**

第一期主系列：

**《如果历史有镜头》**

---

## 2. 项目背景

当前用户持有小云雀等 AI 视频生成服务的月度订阅积分，但由于日常没有足够时间持续使用，订阅积分经常闲置或过期。

与其人工偶尔生成视频，不如将这些生成额度转化为一个持续运行的 AI 内容生产实验：

系统每天自动完成一次短片创作任务，从选题、资料核验、创意构思、脚本、分镜、视频提示词，到调用视频生成平台完成一条 15 秒或 30 秒短片。

项目的目标不是简单地自动消耗积分，也不是机械日更，而是建立一个长期运行的 AI 影视创作实验系统。

系统运行过程中需要持续记录：

- 什么题材生成效果最好
- 哪种叙事结构适合 15 秒
- 哪些镜头语言成功率最高
- 哪些提示词容易产生高质量画面
- 哪类场景容易失败
- 不同模型、参数和参考素材对结果有什么影响

最终形成：

**短片资产 + 创作经验 + Prompt 数据 + 模型表现数据**

长期可以演化为一个轻量的 **AI Director Runtime / AI 导演运行系统**。

---

# 3. 产品目标

## 3.1 第一阶段目标

MVP 首先验证以下闭环：

```text
选题
↓
资料核验
↓
创意设计
↓
15 秒脚本
↓
分镜设计
↓
生成提示词
↓
调用视频模型
↓
取得成片
↓
AI 自动评价
↓
人工选片
↓
经验沉淀
```

要求系统能够在没有人工每日介入的情况下，持续运行。

---

## 3.2 核心原则

整个系统遵循以下原则：

### 原则一：每天创作，不等于每天发布

每日自动生成作品。

是否公开发布，由编辑选择。

推荐机制：

```text
每日生成 1 条
↓
每周积累 7 条
↓
AI 初选 + 人工选择
↓
发布 1～3 条
```

生产与发布必须解耦。

---

### 原则二：15 秒不是压缩后的长故事

15 秒视频不追求讲完整一个事件。

每条短片原则上只呈现：

**一个瞬间、一个动作、一个情绪、一个视觉转折。**

例如赤壁之战不应该在 15 秒内讲完整场战争。

可以只拍：

```text
深夜。

士兵站在船头。

他突然感觉到风向改变。

远处第一艘火船亮起。

结束。
```

---

### 原则三：历史越宏大，镜头越具体

不优先使用：

- 大段旁白
- 历史知识介绍
- PPT 式信息罗列
- 多人物快速切换
- 复杂事件摘要

优先使用：

- 单一人物
- 单一空间
- 单一事件
- 单一动作
- 强视觉瞬间

---

### 原则四：视频只是结果，数据才是长期资产

所有创作过程必须结构化记录。

至少包括：

- 原始选题
- 资料来源
- 创意设定
- 脚本
- 分镜
- Prompt
- 视频模型
- 模型参数
- 生成时间
- 积分消耗
- 成片地址
- AI 评分
- 人工评分
- 问题标签
- 是否发布

---

# 4. 第一阶段内容定位

MVP 不同时开展大量栏目。

第一阶段建议只验证一个系列：

# 《如果历史有镜头》

基本设定：

> 假设历史上的某个关键瞬间真的留下了一段 15 秒影像。

目标不是历史科普，而是：

**创造一段不存在、但仿佛真的被摄影机记录下来的历史影像。**

---

# 5. 内容类型设计

系统未来可以支持多个 Series。

数据结构中应预留 Series 概念。

第一阶段只启用 `history_camera`。

未来可扩展如下。

## Series A：如果历史有镜头

表现历史关键瞬间。

例如：

- 赤壁之战起风前一分钟
- 凯撒渡过卢比孔河
- 敦煌藏经洞第一次被打开
- 拜占庭城墙陷落前
- 阿波罗 11 号舱门开启
- 泰坦尼克号甲板上的最后时刻

---

## Series B：无名者

不拍帝王将相。

只拍历史中的普通人。

例如：

- 修建长城的士卒
- 敦煌壁画画工
- 郑和船队里的厨师
- 清明上河图里的路人
- 古代驿站信使

---

## Series C：世界最后 15 秒

表现某个城市、文明、建筑或者时代转折前的最后瞬间。

---

## Series D：名画之外

假设名画画面继续运行 15 秒。

---

## Series E：古籍复活

从：

- 《史记》
- 《世说新语》
- 《聊斋志异》
- 《搜神记》
- 《山海经》
- 《太平广记》

等公共领域作品中寻找可以视觉化的场景。

---

## Series F：一句话科幻

每天生成一个原创世界设定。

例如：

> 人类第一次发现月亮其实是一枚尚未孵化的蛋。

然后只展示这个世界中的 15 秒。

---

## Series G：未来考古

未来文明如何误读今天留下来的东西。

例如：

- 手机
- 外卖箱
- 二维码
- 共享单车
- 自拍杆

---

# 6. 系统角色

MVP 建议采用多个逻辑 Agent，但不要求必须对应多个独立模型实例。

可以在一个 Agent Runtime 中按 Stage 执行。

---

## 6.1 Topic Agent

职责：

每日生成候选选题。

输入：

- Series
- 历史选题池
- 已完成作品
- 最近作品
- 黑名单
- 内容偏好

输出至少 3 个候选。

例如：

```json
[
  {
    "title": "赤壁之夜，东南风第一次吹来",
    "event": "Battle of Red Cliffs",
    "year": "208",
    "visual_potential": 9,
    "story_potential": 8
  }
]
```

必须避免：

- 最近重复
- 高度相似
- 无法视觉化
- 需要大量背景知识才能理解

---

# 6.2 Research Agent

负责最基础的事实核验。

Research Agent 不负责写论文。

主要确认：

- 时间
- 地点
- 时代
- 人物
- 建筑
- 服饰
- 武器
- 天气或环境
- 事件基本背景

输出：

```text
Historical Fact Sheet
```

每个关键事实尽可能附来源。

历史作品允许艺术化，但必须区分：

```text
Confirmed Fact
Probable Reconstruction
Creative Interpretation
```

---

# 6.3 Creative Director Agent

这是整个系统最核心的 Agent。

它需要回答：

> 这个历史事件最值得拍的 15 秒是什么？

不是：

> 这个历史事件发生了什么？

Director 必须选择一个具体瞬间。

输出：

```text
核心瞬间
主角
地点
动作
视觉变化
情绪
结尾画面
```

---

# 6.4 Script Agent

将创意转换成 15 秒或者 30 秒微故事。

15 秒建议：

- 1～3 个镜头
- 1 个主角
- 1 个地点
- 最多 1 次明显转折

30 秒建议：

- 3～6 个镜头
- 可以存在简单起承转合

禁止为了讲清楚历史而填塞旁白。

---

# 6.5 Cinematography Agent

负责分镜。

输出每个 Shot：

```json
{
  "shot": 1,
  "duration": 5,
  "shot_size": "medium close-up",
  "camera": "slow push-in",
  "subject": "...",
  "action": "...",
  "environment": "...",
  "lighting": "...",
  "emotion": "...",
  "transition": "cut"
}
```

---

# 6.6 Prompt Agent

负责将分镜转换为视频模型 Prompt。

Prompt 不应只是重新描述剧情。

必须包含：

- Subject
- Environment
- Historical details
- Action
- Camera
- Lighting
- Texture
- Mood
- Temporal continuity

不同视频 Provider 可以拥有独立 Prompt Adapter。

例如：

```text
PromptAdapter
├── XiaoyunqueAdapter
├── SeedanceAdapter
├── KlingAdapter
└── GenericVideoAdapter
```

这样未来切换模型时，不需要改变整个创作系统。

---

# 6.7 Video Generation Executor

职责：

真正向视频生成服务提交任务。

第一阶段目标 Provider：

**小云雀**

但是系统架构不得与小云雀强耦合。

统一接口：

```ts
interface VideoProvider {
  submit(task: VideoGenerationTask): Promise<JobId>

  getStatus(jobId: JobId): Promise<JobStatus>

  getResult(jobId: JobId): Promise<VideoResult>
}
```

如果小云雀不存在官方可用 API，需要单独研究：

1. 官方 API
2. 浏览器自动化
3. RPA
4. 其他合法稳定调用方式

Executor 必须允许后续替换其他模型。

---

# 7. Critic Agent

每条视频生成完成后进行自动评价。

Critic 不负责决定是否发布。

负责形成机器评价。

建议评分维度：

| 项目 | 分数 |
|---|---:|
| 视觉质量 | 0～10 |
| 人物一致性 | 0～10 |
| 时代准确性 | 0～10 |
| 镜头稳定性 | 0～10 |
| 故事可理解性 | 0～10 |
| 情绪强度 | 0～10 |
| 创意度 | 0～10 |
| 发布潜力 | 0～10 |

同时输出：

```text
失败原因
成功因素
异常镜头
改进建议
```

例如：

```text
人物面部在第 8 秒出现变形。
火焰运动质量很好。
历史服装整体可信。
故事转折不够明显。
```

---

# 8. Learning Agent

Learning Agent 不参与单条作品创作。

它负责周期性总结。

建议：

```text
每 7 天执行一次
每 30 天执行一次
```

分析：

- 哪类题材平均评分最高
- 哪种镜头最稳定
- 哪种 Prompt 模板效果最好
- 哪类历史时期最容易失败
- 15 秒和 30 秒质量差异
- 哪些生成参数值得继续使用
- 哪些失败模式反复出现

生成：

```text
Creative Learning Report
```

并允许将高置信经验写入：

```text
Director Playbook
```

例如：

```text
Rule 001
历史战争类视频中，超过 8 个可见人物时，角色畸变率明显上升。

Rule 002
15 秒历史短片采用 2 个镜头平均质量高于 4 个以上镜头。

Rule 003
使用前景遮挡 + 缓慢推进，比大规模运动镜头更稳定。
```

这些 Rule 应有数据来源和样本数量。

---

# 9. 每日运行流程

建议每天固定时间触发。

```text
Scheduler
   ↓
读取 Series Configuration
   ↓
读取历史作品库
   ↓
Topic Agent
   ↓
3 个候选
   ↓
Director 自动选择
   ↓
Research Agent
   ↓
Creative Director
   ↓
Script
   ↓
Storyboard
   ↓
Prompt
   ↓
Video Provider
   ↓
生成视频
   ↓
下载/归档
   ↓
Critic
   ↓
写入数据库
   ↓
进入 Review Queue
```

---

# 10. 人工审核机制

MVP 不需要复杂审核系统。

只需要一个 Review 页面。

显示：

```text
视频

标题

Series

核心创意

Prompt

AI Score

[喜欢]
[一般]
[失败]

[发布]
[重做]
[废弃]
```

人工可输入简单评价。

例如：

```text
非常有氛围，但不像三国时期。
```

人工评价必须进入 Learning 数据。

---

# 11. 内容状态

每个 Video Project 应拥有状态：

```text
idea
researched
scripted
prompted
generating
generated
evaluated
reviewed
selected
published
rejected
failed
```

---

# 12. 核心对象模型

## Project

代表每天的一次创作任务。

```json
{
  "project_id": "",
  "series_id": "",
  "date": "",
  "status": "",
  "topic": "",
  "duration": 15
}
```

---

## ResearchPack

```json
{
  "facts": [],
  "sources": [],
  "historical_risks": [],
  "creative_freedom": []
}
```

---

## CreativeConcept

```json
{
  "moment": "",
  "protagonist": "",
  "location": "",
  "action": "",
  "emotion": "",
  "visual_hook": "",
  "ending": ""
}
```

---

## Storyboard

```text
Project
└── Shot[]
```

---

## Generation

```json
{
  "provider": "",
  "model": "",
  "prompt": "",
  "parameters": {},
  "job_id": "",
  "cost": "",
  "credits": "",
  "duration": "",
  "result_url": ""
}
```

同一 Project 必须允许多次 Generation。

原因：

一次创意可能生成多个版本。

---

## Evaluation

```json
{
  "ai_scores": {},
  "ai_comment": "",
  "human_rating": "",
  "human_comment": "",
  "published": false
}
```

---

# 13. 选题数据库

系统需要维护：

```text
Topic Pool
```

分为：

```text
Candidate
Selected
Used
Rejected
Blocked
```

必须防止连续出现相似内容。

建议加入：

```text
Similarity Check
```

例如最近 30 天不能连续出现：

- 三国战争
- 拿破仑战争
- 战争类选题

可以设置 Series Diversity Policy。

---

# 14. 历史事实与艺术创作边界

历史类内容必须引入：

```text
Historical Confidence
```

三级即可。

### A：事实明确

史料可以明确确认。

### B：合理推断

没有直接证据，但符合时代背景。

### C：艺术创作

纯创作设定。

例如：

```text
曹操赤壁当晚站在船头
```

可能没有史料证明。

系统可以采用，但必须记录：

```text
Creative Reconstruction
```

这样未来如果视频发布，可以根据需要生成说明：

> 本片基于历史背景进行艺术化想象。

---

# 15. 版权策略

第一阶段尽量使用：

- 历史事件
- 公共领域作品
- 古籍
- 神话
- 民间故事
- 原创世界观

尽量避免未经授权直接使用现代商业 IP。

例如：

不建议长期依赖：

- Marvel
- Disney
- Harry Potter
- 当前热门影视角色

原因包括：

- 版权风险
- 品牌不可控
- 内容长期价值低
- 容易沦为 AI 同人作品

---

# 16. 媒体资产存储

视频必须保存到自己的资产库。

不应该只依赖视频平台链接。

目录示例：

```text
/assets
  /2026
    /08
      /2026-08-23-red-cliff
        concept.json
        research.md
        script.md
        storyboard.json
        prompt.txt
        generation.json
        video.mp4
        evaluation.json
```

如果未来已经拥有统一 Media Asset System，则这里直接写入 Asset ID。

---

# 17. 控制台

MVP 前端只需要 5 个页面。

## Dashboard

显示：

```text
本月生成数量
本月积分消耗
平均 AI Score
人工精选率
生成失败率
```

---

## Today

显示今天的创作全过程。

例如：

```text
今日题目：
赤壁之夜，风变了

Research ✓
Script ✓
Storyboard ✓
Generating...
```

---

## Library

历史视频列表。

支持：

- Series
- 日期
- Score
- Published
- Provider

筛选。

---

## Review Queue

人工看片。

---

## Insights

显示系统总结出的规律。

例如：

```text
过去 30 天：

平均最高评分题材：
普通人视角历史

成功率最高镜头：
slow push-in

最常见失败：
多人场景人物变形
```

---

# 18. Scheduler

系统必须支持定时任务。

例如：

```text
每天 02:00
启动每日创作任务

每周日
执行 Weekly Learning

每月 1 日
执行 Monthly Learning
```

所有 Scheduler 任务必须：

- 可人工关闭
- 可人工重跑
- 有执行日志
- 避免重复执行

---

# 19. 失败恢复

这是 MVP 必须具备的能力。

不能因为某一个 Agent 出错导致整条 Pipeline 报废。

例如：

```text
Research 成功
Script 成功
Generation 失败
```

应该从：

```text
Generation
```

继续。

而不是重新研究和写脚本。

每个 Stage 都应保存中间状态。

---

# 20. 成本控制

必须设置：

```text
Daily Credit Budget
Monthly Credit Budget
```

例如：

```text
每日最多生成 2 次
每月最多使用 90% 订阅积分
```

如果达到阈值：

```text
停止自动生成
```

而不是不断重试。

---

# 21. MVP 范围

第一期必须完成：

- 每日定时运行
- 历史选题生成
- 资料核验
- Creative Director
- 15 秒脚本
- 分镜
- Prompt
- 视频 Provider Adapter
- 视频生成
- 成片保存
- Critic
- Review Queue
- Generation Log
- Weekly Learning
- 基础 Dashboard

---

# 22. MVP 暂不实现

第一期明确不做：

- 自动运营多个社交媒体账号
- 自动发布
- 评论互动
- 流量预测
- 用户体系
- 商业化
- 多人协作
- 复杂权限
- 移动 App
- 完整剪辑软件
- AI 数字人
- 长视频

这些都属于后续扩展。

---

# 23. 第一阶段实验计划

建议第一阶段运行：

**30 天。**

内容只做：

# 《如果历史有镜头》

每天：

```text
1 个作品
15 秒
```

允许最多：

```text
2 次 Generation
```

---

# 24. 30 天评估指标

不要使用播放量作为第一阶段核心指标。

因为 MVP 的第一目标不是做账号。

主要判断系统本身是否成立。

核心指标：

### 运行稳定性

每日自动执行成功率：

```text
≥ 90%
```

### 有效成片率

人工判断：

```text
可以观看
```

的比例：

目标：

```text
≥ 70%
```

### 精选率

人工认为：

```text
值得公开发布
```

目标：

```text
≥ 30%
```

也就是说：

30 条至少产生约 10 条真正值得发布的作品。

### 创作学习

30 天结束时必须至少形成：

```text
10 条具有证据支持的 Director Rules
```

---

# 25. 第二阶段可能方向

如果第一阶段验证成功，再考虑：

```text
《无名者》
《世界最后15秒》
《古籍复活》
《未来考古》
《一句话科幻》
```

然后形成：

```text
Series Engine
```

---

# 26. 长期架构

未来系统可以演化为：

```text
                Creative Runtime

Topic Intelligence
        ↓
Research Runtime
        ↓
Creative Director
        ↓
Story Runtime
        ↓
Storyboard Runtime
        ↓
Prompt Compiler
        ↓
Video Provider Layer
        ↓
Media Asset Store
        ↓
Critic Runtime
        ↓
Learning Runtime
```

系统最终积累：

```text
Creative Knowledge Base
```

也就是：

**AI 怎样才能拍出更好的短片。**

---

# 27. 产品成功定义

这个项目真正成功，并不是：

> 每天成功调用了一次小云雀。

而应该是：

> 系统运行得越久，对什么样的 15 秒值得拍、应该怎么拍、什么方式生成成功率更高，判断越来越准确。

第一阶段是：

**自动生成视频。**

第二阶段是：

**自动学习怎样生成好视频。**

最终目标则是：

**形成一个持续学习的 AI 导演系统。**

---

# 28. 开发实施优先级

建议按以下顺序开发。

### P0

```text
Project
Pipeline
Scheduler
Video Provider
Asset Store
```

先把端到端跑通。

### P1

```text
Topic
Research
Director
Script
Storyboard
Prompt
Critic
```

建立创作链路。

### P2

```text
Review
Metrics
Learning
Director Playbook
```

让系统开始积累经验。

### P3

```text
更多 Series
更多 Provider
自动剪辑
自动配乐
自动字幕
发布流程
```

---

# 29. 第一版最小闭环

如果进一步压缩开发范围，最小版本甚至可以只有：

```text
Cron
↓
LLM
↓
Topic
↓
Research
↓
Script
↓
Prompt
↓
小云雀
↓
Video
↓
Critic
↓
SQLite
```

后台只做一个简单页面：

```text
今天拍了什么
生成结果
AI 怎么评价
我要不要留下
```

先连续跑满 30 天。

不要一开始就把它开发成完整内容平台。

这个项目最重要的验证不是 UI，也不是系统复杂度。

而是：

**每天自动创作这件事，连续运行一个月以后，究竟会不会产生真正有价值的东西。**