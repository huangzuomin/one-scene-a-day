# 每日创作流水线 · 操作手册（PIPELINE）

> 本文件是「AI 每日短片实验室」的**唯一权威运行手册**。
> 任何被定时任务或人工启动的创作会话，必须严格按本手册执行。
> 系统由 ZCode 会话本身充当全部创作 Agent；本手册 + PLAYBOOK.md 就是系统的全部"源代码"。

---

## 0. 系统构成

| 环节 | 承担者 |
|---|---|
| 选题/研究/导演/脚本/分镜/简报/评分 | ZCode 会话（读 PLAYBOOK.md 后亲自创作） |
| 视频渲染 | 小云雀，经 xyq-skill 的 python 脚本调用 |
| 状态与产物存储 | 本工作区文件系统（无数据库） |
| 排期 | 定时自动化：每晚 21:00 创作流水线；每周日 10:00 Learning |

环境要点：
- 本机用 `python` 命令（`python3` 不存在），Python 3.13.2
- xyq 脚本目录：`C:\Users\zooma\.agents\skills\xyq-skill\scripts\`
- 鉴权：**以 `state\xyq_access_key.txt` 文件为准**（Step 8 会自动读取）；进程环境变量仅作后备
- ffmpeg 已安装（Critic 抽帧用）

## 1. 目录约定

```text
D:\Work\AI 每日短片实验室\
├── PIPELINE.md / PLAYBOOK.md      # 手册与创作守则
├── topics\topics.json             # 选题池唯一事实源（治理规则见 §6；topic-pool.md 已归档退役）
├── state\
│   ├── budget-ledger.json         # 生成次数台账（熔断依据）
│   └── scheduler-log.md           # 每次运行追加一行日志
├── projects\
│   └── YYYY-MM-DD-<slug>\         # 每日项目文件夹
│       ├── status.json            # 状态机位置（机器读）
│       ├── status.md              # 同内容的人读版（双写）
│       ├── concept.json           # 选题+创意概念（Step1/3 产物）
│       ├── research.md            # 事实清单 A/B/C 置信标注（Step2）
│       ├── script.md              # 15秒脚本+节奏诊断（Step4）
│       ├── storyboard.json        # Beats 数组（Step5）
│       ├── prompt.txt             # 提交给小云雀的创作简报（Step6）
│       ├── generation_jobs\<job_id>\
│       │   ├── submission_receipt.json   # thread_id/run_id/提交时间
│       │   ├── status_log.jsonl          # 追加式轮询日志
│       │   ├── fetch_manifest.json       # 下载清单
│       │   └── failure_log.md            # 失败时才写
│       ├── video.mp4              # 成片（从 job 下载后复制到根）
│       ├── frames\                # Critic 抽帧
│       └── evaluation.json        # AI 八维评分+复盘（Step10）
├── review\index.html              # 审片页（每次运行重生成）
└── insights\                      # Weekly/Monthly 学习报告
```

## 2. 项目状态机

```text
idea → researched → scripted → prompted → generating → generated → evaluated → reviewed
                                                                    ↘ selected / published
任何阶段可 → failed（记录原因，不删除已有产物）
```

规则：
- 每个 Step 完成 = 对应产物落盘 + status.json 更新（`status` 字段 + `history[]` 追加 `{time, step, note}`）+ status.md 同步刷新
- **断点续跑**：每次运行先读 status.json，从最后一个完成态之后继续，绝不重复已完成步骤
- 失败时保持当前阶段、history 记录错误摘要；下次运行自动重试该步

## 3. 每日流程（11 步）

### Step 0 · 前置检查
1. 以当天日期检查 `projects\YYYY-MM-DD-*\` 是否已存在：存在则读 status.json 续跑
2. 读 `state\budget-ledger.json`：若当日 generations ≥ 2 → 只允许补全非生成阶段（研究/脚本等），不得提交新生成
3. 通读 `PLAYBOOK.md`

### Step 1 · 选题（Topic Agent）
- **只从 `topics\topics.json` 中 status=approved 的选题里挑选**（治理规则见 §6）：
  visual_potential 最高且不违反多样性规则者
- 多样性硬规则：**同一事件永不复用；与最近 7 天作品主标签相同者跳过**
- 选中即把该条选题改为 used（记 used_date 与项目文件夹），建项目文件夹，concept.json 写入选题部分，状态 idea
- **approved=0**：按 §6 红线处理——当晚不生成，建 status.json（状态 skipped）后在 scheduler-log 记跳过原因并正常结束；
  仅在 §6.5 过渡期内允许按旧规则从 candidate 挑选

### Step 2 · 研究（Research Agent）
- 用自身知识核验：时代、地点、人物、服饰形制、建筑、武器、天气、事件背景
- 写 research.md：每条事实标注置信级——**A 史料确认 / B 合理推断 / C 艺术创作**
- 不要求外部引用链接；画面将依赖的关键视觉元素（服装/建筑/道具）必须达到 B 以上

### Step 3 · 创意概念（Creative Director）
回答「这个历史时刻最值得拍的 15 秒是什么」。先按 PLAYBOOK R-105 填节奏诊断，再写 concept.json：

```json
{
  "topic": {"title": "", "event": "", "year": ""},
  "moment": "核心瞬间",
  "protagonist": "单一主角（含身份锁描述：年龄/服装/发型/随身道具）",
  "location": "单一空间",
  "action": "一个动作",
  "emotion": "一种情绪",
  "visual_hook": "视觉转折",
  "ending": "结尾定格画面",
  "pacing_diagnosis": {"genre_energy": "", "felt_speed": "", "target_duration": 15,
    "avg_beat": "", "fastest_beat": "", "slowest_beat": "", "required_pauses": "", "final_hold": ""}
}
```
铁律：一个瞬间、一个动作、一种情绪、一次视觉转折；单主角（≤3 人）、单空间。

### Step 4 · 脚本（Script Agent）
script.md：15 秒微故事。1～3 个镜头组；最多一次转折；**禁止旁白堆砌**；
按 R-305 标注声音暗示。状态 scripted。

### Step 5 · 分镜（Cinematography Agent）
storyboard.json，Story→Segment→Beat 三层中的 Beat 数组（本系列单 Segment）：

```json
{"segment": "S01", "duration_total": 15, "beats": [{
  "beat": 1, "time": "0-2s", "shot_size": "", "angle": "", "lens": "",
  "composition": "", "camera": "运镜含起止状态", "action": "",
  "lighting": "", "emotion": "", "transition": ""}]}
```
套用 PLAYBOOK R-301 七格图（可裁剪为 5~6 格）；每个镜头描述遵守 R-201 八字段公式。

### Step 6 · Prompt 简报（Prompt Agent）
prompt.txt = 一段连贯的自然语言创作简报（中文），把时代细节、主角身份锁、动作、
运镜（含起止）、光线、质感、情绪、结尾画面编织成完整描述——不是参数碎片。
末尾附加 PLAYBOOK R-401 adherence 约束段。状态 prompted。

### Step 7 · 预算熔断（提交前必查）
- 台账当日 generations < 2 才可提交；提交成功后立即 +1 并写盘
- 连续 2 次提交失败 → 当日放弃，状态 failed，写 failure_log.md

### Step 8 · 提交小云雀（Video Provider · submit/status/fetch/review 四操作之 submit+status）
> **2026-08-30 起默认通道：主链路 agent（本节），模型不加指令行（后端自动用 seedance2.0_fast_vision，720p）**。
> 用户 2026-08-30 裁定：Seedance_2.5 直连（1080p）画质虽优但积分消耗过高，日常回退 2.0/720p 原模式；
> 直连 2.5 保留为**特别场合手动选项**（如季度精选重制），日常流水线不使用。详见修订记录 v1.5。
> （2026-08-30 v1.4 曾默认直连 2.5，次日即按用户指示回退。）

```bash
# 密钥一律从工作区文件读取（定时任务继承的进程环境变量可能已过期，2026-08-22 实测教训）
export XYQ_ACCESS_KEY=$(head -1 "D:\Work\AI 每日短片实验室\state\xyq_access_key.txt" | tr -d '\r\n')
python "C:\Users\zooma\.agents\skills\xyq-skill\scripts\submit_run.py" --message "<prompt.txt 全文>"
```
- **模型策略（v1.5）**：主链路**不加任何模型指令行**，后端自动使用 seedance2.0_fast_vision（720p）——积分日常消耗模式。
  Seedance_2.5（1080p，直连）画质显著更优但积分消耗高，仅用于**特别场合手动指定**（如第 30 夜精选重制），日常流水线一律不用
- 若后端报「错误码 2 / Ak已过期」→ 提示用户更新 `state\xyq_access_key.txt` 内容后原样重试；状态保持 prompted
- 返回 JSON 取 `thread_id`、`run_id`，连同提交时间写入 `generation_jobs\<job_id>\submission_receipt.json`（job_id 形如 `j01`）
- 轮询（10 秒间隔，**thread_id 与 run_id 都必传**——2026-08-22 实测省略 run_id 会报「run id不能为空」）：
```bash
python "C:\Users\zooma\.agents\skills\xyq-skill\scripts\get_thread.py" --thread-id <id> --run-id <id>
```
  - 退出码 0 且 stderr 含「成功」→ 完成；退出码 1 → 失败（stderr 有原因）；进行中时退出码 0、stderr 为空、stdout 首行为「本次创作进行中」后接 JSON（解析取最后一个 JSON 对象）
  - 每次轮询结果追加 `status_log.jsonl` 一行
- **超过 90 分钟未完成**：停止本次运行，状态停 generating，thread_id 已入档，下次运行从本步续跑取件
- 完成后从返回 messages 中提取 assistant 内容里的产物 URL（`content[].data.url`）

### Step 9 · 下载归档（fetch 操作）
```bash
python "C:\Users\zooma\.agents\skills\xyq-skill\scripts\download_results.py" --urls <URL> --output-dir "<项目夹>\generation_jobs\<job_id>" --prefix video
```
- 下载后将成片复制为项目根 `video.mp4`，URL 与本地路径写入 fetch_manifest.json
- 状态 generated

### Step 10 · Critic（review 操作）
1. 抽帧：`ffmpeg -i video.mp4 -vf fps=1 "frames\f%02d.jpg"`（15 帧）
2. **亲自 Read 查看 4～6 张分布帧**（首、1/4、转折点、3/4、末）
3. 八维打分 0–10：视觉质量 / 人物一致性 / 时代准确性 / 镜头稳定性 / 故事可理解性 / 情绪强度 / 创意度 / 发布潜力
4. 按 PLAYBOOK R-405 回答 adherence 十问
5. 写 evaluation.json：
```json
{"ai_scores": {"visual_quality": 0, "character_consistency": 0, "era_accuracy": 0,
  "camera_stability": 0, "story_clarity": 0, "emotional_impact": 0, "creativity": 0, "publish_potential": 0},
 "verdict": "", "observations": [], "risks": [], "decision_suggestion": "",
 "adherence_review": {}, "human_rating": null, "human_comment": null}
```
状态 evaluated。

### Step 11 · 收尾
1. 重新生成 `review\index.html`：审片页列出所有项目的卡片（日期/标题/视频相对路径/AI 总分/人工评级占位），最新在前
2. `state\scheduler-log.md` 追加一行：`日期 | 结果 | 各Stage耗时 | 备注`
3. **明晚预告**：收尾消息附 approved 池前 2 条（id + 题目 + 一句话理由，按潜力与多样性排序），
   供人工在晨间评级时顺带确认或改选；不回复则次夜 AI 按原规则自行挑选
4. 若今日因熔断/失败提前结束，同样记日志

### Step 12 · 发布（收尾之后）
把当夜成果同步到公开网站（GitHub Pages，https://huangzuomin.github.io/one-scene-a-day/）：

1. 在仓库根目录运行 `python gen_site.py` —— 从 `projects/` 数据重新生成 `site/index.html` 并同步视频/抽帧资产。新夜次**不需要改代码**：标题、评分、研究事实、分镜、简报、学习规则、季况条、统计、待拍清单全部由数据驱动
2. 数据要求（创作时即应满足）：
   - `concept.json` 的 `topic` 尽量含 `tag`（标签，如「战争」）——缺省时页面回退到内置映射
   - `evaluation.json` 的 `learned[]` 条目形如 `{id, title, rule, why?, source}`；`why` 是给网站看的「为什么」，可选
   - `topics\topics.json` 是选题池板块（可拍队列/待审区/标签战绩/库存预警）的数据源，选题状态变更后重跑本脚本即可
   - 无成片夜（failed/skipped）暂不进入影片列表，只计入季况统计
3. 提交推送（先提交再对齐远端：工作区有未提交改动时 rebase 会拒绝执行）：
   ```bash
   cd site 的仓库根目录
   git add -A && git commit -m "第 NN 夜 · T00N 上线（待复核）"
   git pull --rebase origin main   # 对齐远端，避免夜间自动化与人手工提交冲突
   git push
   ```
4. GitHub Actions 自动部署（约 1 分钟）；若人工评级改变了结论（精选/废弃），更新 evaluation 后重跑 `python gen_site.py` 并以 「第 NN 夜 · T00N 上线（已精选）」 再推一次 —— 两段式发布
5. 护栏：
   - **密钥永不入库**：`state\xyq_access_key.txt` 已在 .gitignore，提交前不要用 `-f` 强加
   - 运行日志摘编如需更新，编辑 `gen_site.py` 顶部 `RUNLOG` 常量后重新生成（摘编是策展，不是全量转发 scheduler-log）
   - 推送后抽查线上页面最新夜次是否出现

### Step 12½ · 出稿（站外发布包）
视频号没有公开发布 API，只能人工经「视频号助手」（channels.weixin.qq.com）上传。自动化到此为止：

1. 运行 `python gen_publish.py` —— 为每个有成片的夜晚生成 `publish\channels\<日期>\` 发布包：成片副本（以夜次+题目命名）、末帧封面 cover.jpg、可直接粘贴的 post.txt 文案（标题/一句话/系列介绍/话题标签）、README.txt（评审信息与定时建议）。已打包的日期自动跳过
2. 发布包目录已在 .gitignore，不入库；成片本体仍在 projects\ 归档
3. 人工动作（与每晚评级合并）：打开视频号助手 → 上传对应包的视频与封面 → 粘贴 post.txt → 用「定时发表」约到次日 07:30-08:30 流量高峰

## 4. 人工评审约定

用户看片后在对话里说结论（例："喜欢，但盔甲不对"、"失败，脸崩了"），会话负责：
- evaluation.json 填入 `human_rating`（喜欢/一般/失败）与 `human_comment`（保留原话）
- 状态推进：selected（值得发布）/ rejected（废弃）；published 仅在明确说发布时使用
- 人工评价原文必须保留——它是 Weekly Learning 的 ground truth

## 5. Weekly Learning（每周日 10:00）

1. 汇总近 7 天所有 evaluation.json（AI 分 + 人工评价）
2. 分析：高分题材共性 / 稳定镜头语言 / 反复出现的失败模式 / prompt 简报模式与质量相关性
3. **仅当结论有 ≥3 个样本支撑**时写入 PLAYBOOK.md 实证规则区（带样本数与来源项目）
4. 报告存 `insights\YYYY-WW.md`（月度报告每月 1 日追加执行，汇总 30 天）
5. **选题补给（池子体检 + 新提名，写入 `topics\topics.json`）**：
   - 体检：近重复事件去重；candidate 超过 4 周未审移入 blocked（reason=stale，人工可捞回）；
     依据最新实证刷新各 candidate 的 recommend 分级
   - 补给：依据**标签战绩**（人工好评高的标签多补、连续平庸的停补）+ **覆盖矩阵缺口**
     （时代 × 标签 × 地域 分布过密处少提、空白处多提）+ **已验证的视觉钩子**（框景/剪影/光柱等
     成功母题寻找可承接的新事件），提名 3~5 条新 candidate；approved < 5 时本步必做且加量至 5~8 条
   - 每条提名必过**四关**：可考证（事件本身 A/B 级置信）/ 可拍（单主角单空间一转折的 15 秒可行）/
     不撞车（不与 used/rejected/blocked 及现有 candidate 的 event 重复，注意 7 天标签窗）/
     有钩子（一句话 pitch 写清视觉转折是什么）
   - Learning 报告末尾附**完整待审清单**（id/题目/标签/推荐级/一句话 pitch），请人工批审

## 6. 选题池治理（topics\topics.json）

分工铁律：**人管池子，AI 管挑拣**——AI 负责提名与每晚挑选，只有人工批准过的选题可以开拍。

状态机：`candidate（待审）→ approved（可拍）→ used（已拍）`；
旁路 `rejected（否决，事件永不复提）`、`blocked（冻结：敏感/疲劳/超期冷藏）`。

- **提名来源**：`seed`（初始种子）/ `ai_weekly`（周日 Learning 补给，见 §5.5）/ `user`（用户随时投喂，审核优先）
- **审核方式**：对话批审，例「T006 T014 过，T013 毙」→ 会话把对应条目改为 approved / rejected（rejected 记否决理由）；
  站点「选题池」板块是看板（gen_site 自动渲染库存状态、可拍队列、待审区、标签战绩）
- **库存红线**：approved < 3 → 站点黄色预警；approved = 0 → 当晚跳过生成（记 skipped）。
  **不做 AI 自主应急提拔**——宁可空一夜，不回到无审核状态
- **补给节奏**：正常每周 3~5 条；approved < 5 时 Learning 加量补给
- **标签治理**：标签生命周期归 Weekly Learning。新标签入系统须同时满足：
  ① 提名 ≥3 条该标签新候选入池；② 给出一句话「能量定义」及与既有标签的边界。
  样本 <3 的标签不参与标签战绩分析（Learning 按「高能量 / 静观」两大能量族聚合分析，
  直到该标签样本 ≥3）。当前标签体系（10）：战争 / 政治转折 / 探索发现 / 日常 /
  科技 / 艺术 / 灾难 / 文明交汇 / **思想**（观念诞生的瞬间）/ **营造**（巨大工程合龙的一瞬）。
  新标签须同步加入 topics_console.py 的 VALID_TAGS。
- **查重范围**：used + rejected + blocked 的事件全部永不复提

### 6.5 过渡条款（一次性，最迟 2026-09-02 失效）
首批人工批审完成前，Step 1 允许按旧规则从 candidate 中挑选拍摄（多样性硬规则仍生效），
但每晚收尾消息必须附完整待审清单催审；一旦 approved ≥ 3，本条款永久失效，之后 approved=0 一律跳过。

## 7. Plan B 备忘（小云雀备用链路）

xyq-skill python 脚本链路故障时，改用 pippit-tool-cli 直连子命令（2026-08-22 已勘察，v1.0.8 实测）：
```bash
# 提交：确定性直连视频模型，不经后端 Agent 转述（更可控，优先在简报被转述失真时使用）
pippit-tool-cli generate-video --prompt "<创作简报>" --duration 15 --ratio 16:9 \
  --resolution 1080p --model seedance2.0_direct
# 输出 thread_id / run_id

# 查询并下载成片
pippit-tool-cli query-result --thread-id <id> --run-id <id> --download-dir "<项目夹>\generation_jobs\<job_id>"
```
模型选择（2026-08-23 CLI 更新 1.0.18 后实测帮助文本）：**VIP 账号优先 `--model Seedance_2.5`**（注意大小写与下划线，用户指定默认 2.5；VIP 专享）。若报无权限/不存在，按序回退：Seedance_2.0_mini → seedance2.0_fast_vision → Seedance_2.0_mini_lite（普通账号唯一可用），回退情况记入 failure_log.md。1.0.8 时代的 seedance2.0_direct / _fast_direct 已从模型表移除。
注意：(1) 鉴权与 xyq-skill 同源，Ak 过期时两链路同挂；(2) job 工件格式与主链路一致。

**2.5 定位实验（已完成，2026-08-30）**：直连 `--model Seedance_2.5` 一次出片（1080p/17MB），证实主链路 agent「暂不可选」为误判、2.5 真实可用。但用户裁定 **1080p 积分消耗过高**，v1.5 起日常回退 2.0/720p；直连 2.5 保留为特别场合手动选项。当时记录：CLI 已确认最新（1.0.18，08-29 update 实测无新版），「暂不可选」与 CLI 版本无关。

---
*本手册是活文档：试运行期发现漏洞当天修订；重大变更在文末登记。*
*修订记录：2026-08-22 v1 初版（融合 StoryboardDrivenAIVideo 方法论蒸馏）。*
*修订记录：2026-08-23 v1.1 默认生成模型改为 Seedance 2.5（主链路消息首行指令 + Plan B 优先 seedance2.5_direct 带回退链）。*
*修订记录：2026-08-23 v1.2 pippit-tool-cli 与 xyq-skill 更新 1.0.8→1.0.18：三脚本接口兼容（get_thread 新增可选 --after-seq 增量拉取）；Plan B 模型表修正为 Seedance_2.5（VIP）等新阵容。*
*修订记录：2026-08-26 v1.3 选题池治理上线：topics.json 成为唯一事实源，Step 1 只从人工 approved 挑选；新增 §6 治理规则（提名四关/库存红线/过渡条款）、Step 11 明晚预告、§5.5 周日选题补给；站点新增选题池板块。*
*修订记录：2026-08-30 v1.4 生成通道切换：直连 generate-video --model Seedance_2.5 实验证实主链路 agent『2.5 暂不可选』为误判（T031 出片 1080p/17MB，先验污染零发生），Step 8 默认改走 Plan B 直连，主链路降为回退。*
*修订记录：2026-08-30 v1.5 按用户裁定回退：2.5/1080p 积分消耗过高，日常恢复主链路 agent 通道（无模型行，fast_vision 720p）；直连 2.5 保留为特别场合手动选项。*
