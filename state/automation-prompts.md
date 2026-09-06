# 自动化提示词存档（automation prompts）

> 用途：ZCode 限制一个会话只能创建一个自动化；若自动化需要重建（如 2026-09-06 模型下线事故），
> 由**新开的会话**按本档原文重建。重建后把新 automationId 记入本文件与 scheduler-log.md。
>
> 背景事故：2026-09-05/09-06 连续两夜 21:00 cron 与 09-06 周日 10:00 cron 派发失败——
> 旧自动化绑定的历史会话钉死在已下线模型 `builtin:bigmodel-coding-plan/GLM-5.3-Flash` 上，
> 宿主拒绝按默认模型恢复（日志：「历史 session 模型已不可用，拒绝按默认模型恢复」）。
> 处置：删旧建新。每日自动化已由 09-06 夜会话重建；周日 Learning 自动化需新会话按本档 §2 重建。

## 1. 每日创作流水线（21:00 每日）

- cron：`0 21 * * *`
- 现状：✅ automation-b0fb692d-4d1f-41e9-b7de-e72887712216（2026-09-06 重建，已生效）

### 提示词（全文照抄）

```text
执行 AI 每日短片实验室的每日创作流水线。工作区：D:\Work\AI 每日短片实验室。

执行规则：
1. 第一步必须完整阅读该目录下的 PIPELINE.md（唯一权威操作手册，含全部 Step 0~12）和 PLAYBOOK.md（创作守则），然后严格按手册执行今日创作——手册是唯一权威，本提示词不重复手册细节，若手册与本提示词不一致，以手册为准。
2. 断点续跑：projects\ 下已存在相关项目文件夹时，读取其 status.json，从最近完成的阶段继续，绝不重复已完成步骤；今日项目已到 evaluated/reviewed 及以后则不新建作品。
3. 硬约束：当日生成次数 ≥2 则不再提交生成；同一事件永不复用，同主标签 7 天内不重复；本机用 python 命令（python3 不存在）。
4. 单个 Stage 失败时把错误摘要记入 status.json 的 history 后正常结束本次运行，不要无限重试。全程无需人工确认。
5. 手册中的发布步骤（如 gen_site.py 站点生成、git 提交推送 GitHub）属于流水线的一部分，必须执行；推送使用仓库已有 remote。
```

## 2. 每周日 Learning（10:00 周日）

- cron：`0 10 * * 0`
- 现状：⚠️ 待重建（旧 automation-29093a7f 已删除；需在**新会话**中创建）

### 提示词（全文照抄）

```text
执行「AI 每日短片实验室」的每周日 Learning 任务。工作区：D:\Work\AI 每日短片实验室。

执行规则：
1. 第一步必须完整阅读该目录下的 PIPELINE.md（唯一权威手册，重点第 5 节 Weekly Learning 与第 6 节选题池治理）和 PLAYBOOK.md（创作守则，含实证规则区格式），然后严格按手册执行本任务——手册是唯一权威，本提示词不重复细节。
2. 本任务内容（按 PIPELINE §5 + §5.5）：
   a. 汇总近 7 天所有 projects\*\evaluation.json（AI 八维评分 + human_rating 人工评价原文）
   b. 分析：高分题材共性 / 稳定镜头语言 / 反复出现的失败模式 / 简报模式与质量相关性；标签样本 <3 时按「高能量/静观」能量族聚合分析，不单标签解读
   c. 仅当结论有 ≥3 个样本支撑时，把规则写入 PLAYBOOK.md 实证规则区（格式：Rule-XXX [实证] 陈述 | 样本 N | 来源项目 | 置信度）
   d. 报告存 insights\YYYY-WW.md（YYYY=年，WW=当周 ISO 周数）
   e. 选题补给（写入 topics\topics.json）：池子体检（近重复事件、candidate 超 4 周未审移 blocked[reason=stale]、依据最新实证刷新 recommend 分级）+ 依据标签战绩/覆盖矩阵缺口/已验证视觉钩子提名 3~5 条新 candidate（approved<5 时加量至 5~8 条）；每条必过四关（可考证/可拍/不撞车/有钩子），带一句话 pitch 与推荐分级；新标签入系统须 ≥3 条候选+一句话能量定义并同步 topics_console.py 的 VALID_TAGS
   f. 执行 python gen_site.py 重新生成站点，然后 git add -A && git commit && git pull --rebase origin main && git push
3. 硬约束：本机用 python 命令（python3 不存在）；state\xyq_access_key.txt 是密钥文件，绝不读取内容、绝不让它进入 git 提交；单个环节失败把错误摘要记入 state\scheduler-log.md 后正常结束，不要无限重试；全程无需人工确认。
4. 结束时向用户呈现：周报核心结论、新增/修订规则清单、选题补给新提名完整清单（id/题目/标签/推荐级/一句话 pitch）并请用户批审、下一周可拍池状况。
```
