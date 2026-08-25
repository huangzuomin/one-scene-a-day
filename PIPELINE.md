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
├── topics\topic-pool.md           # 选题池（Candidate / Used / Blocked 三区）
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
- 从 topic-pool.md Candidate 区选 visual_potential 最高且不违反多样性规则者
- 多样性硬规则：**同一事件永不复用；与最近 7 天作品主标签相同者跳过**
- 将选中项移入 Used 区并标注日期；建项目文件夹，concept.json 写入选题部分，状态 idea

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
```bash
# 密钥一律从工作区文件读取（定时任务继承的进程环境变量可能已过期，2026-08-22 实测教训）
export XYQ_ACCESS_KEY=$(head -1 "D:\Work\AI 每日短片实验室\state\xyq_access_key.txt" | tr -d '\r\n')
python "C:\Users\zooma\.agents\skills\xyq-skill\scripts\submit_run.py" --message "使用 Seedance 2.5 模型生成视频。
<prompt.txt 全文>"
```
- **默认模型：Seedance 2.5**（2026-08-23 用户指定）。主链路无 model 参数，模型由后端 agent 从消息文本领会，故首行固定写模型指令；xyq 文档禁止代写风格描述词，但指定用户要求的模型属需求传话，不违规
- 若后端明确拒绝该模型（报错/改用其他模型且成片质量异常）→ 去掉模型行回退默认模型重提一次，并在 status_log 记录回退原因
- 轮询返回的创作信息中若可见实际使用的模型，记入 `status_log.jsonl` 最后一行（字段 `actual_model`），供 Learning 核对指令是否生效
若报「错误码 2 / Ak已过期」→ 提示用户更新 `state\xyq_access_key.txt` 内容后原样重试；状态保持 prompted。
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
3. 若今日因熔断/失败提前结束，同样记日志

### Step 12 · 发布（收尾之后）
把当夜成果同步到公开网站（GitHub Pages，https://huangzuomin.github.io/one-scene-a-day/）：

1. 在仓库根目录运行 `python gen_site.py` —— 从 `projects/` 数据重新生成 `site/index.html` 并同步视频/抽帧资产。新夜次**不需要改代码**：标题、评分、研究事实、分镜、简报、学习规则、季况条、统计、待拍清单全部由数据驱动
2. 数据要求（创作时即应满足）：
   - `concept.json` 的 `topic` 尽量含 `tag`（标签，如「战争」）——缺省时页面回退到内置映射
   - `evaluation.json` 的 `learned[]` 条目形如 `{id, title, rule, why?, source}`；`why` 是给网站看的「为什么」，可选
   - 无成片夜（failed/skipped）暂不进入影片列表，只计入季况统计
3. 提交推送：
   ```bash
   cd site 的仓库根目录
   git pull --rebase origin main   # 先对齐远端，避免夜间自动化与人手工提交冲突
   git add -A && git commit -m "第 NN 夜 · T00N 上线（待复核）" && git push
   ```
4. GitHub Actions 自动部署（约 1 分钟）；若人工评级改变了结论（精选/废弃），更新 evaluation 后重跑 `python gen_site.py` 并以 「第 NN 夜 · T00N 上线（已精选）」 再推一次 —— 两段式发布
5. 护栏：
   - **密钥永不入库**：`state\xyq_access_key.txt` 已在 .gitignore，提交前不要用 `-f` 强加
   - 运行日志摘编如需更新，编辑 `gen_site.py` 顶部 `RUNLOG` 常量后重新生成（摘编是策展，不是全量转发 scheduler-log）
   - 推送后抽查线上页面最新夜次是否出现

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

## 6. Plan B 备忘（小云雀备用链路）

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

---
*本手册是活文档：试运行期发现漏洞当天修订；重大变更在文末登记。*
*修订记录：2026-08-22 v1 初版（融合 StoryboardDrivenAIVideo 方法论蒸馏）。*
*修订记录：2026-08-23 v1.1 默认生成模型改为 Seedance 2.5（主链路消息首行指令 + Plan B 优先 seedance2.5_direct 带回退链）。*
*修订记录：2026-08-23 v1.2 pippit-tool-cli 与 xyq-skill 更新 1.0.8→1.0.18：三脚本接口兼容（get_thread 新增可选 --after-seq 增量拉取）；Plan B 模型表修正为 Seedance_2.5（VIP）等新阵容。*
