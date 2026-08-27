# 选题池控制台 · README

`topics_console.py` — 选题池审核控制台（本地 Web UI）+ 治理 CLI。

人管池子，AI 管挑拣：本工具是 `topics/topics.json` 的人工审核界面与治理规则执行工具，不改变 PIPELINE.md 定义的治理语义。

## 启动 Web 控制台

```bash
python topics_console.py serve
# 浏览器打开 http://127.0.0.1:8787
# 自定义端口：python topics_console.py serve --port 9000
```

仅绑定 127.0.0.1，无鉴权，单用户本机工具。

### 界面功能

- **库存状态条**：顶部常驻，红（池空）/ 黄（<3 条）/ 绿（≥3 条）三态
- **待审列表**：默认视图，展示 pitch、标签、年代、潜力分、推荐分级徽章（优先/备选/存疑）
- **筛选排序**：按推荐级/标签筛选，按推荐级+潜力或提名日期排序
- **单条审批**：批准 / 否决（必填理由）/ 冻结
- **批量审批**：勾选多条一键批准（>5 条弹确认）；批量否决需填理由
- **撤销/捞回**：approved→candidate（撤销）；rejected/blocked→candidate（捞回）
- **投喂表单**：新增 user 来源的 candidate，id 自动顺延
- **可拍队列**：每条 approved 显示「今夜可拍」或「冷却中 → MM-DD」（7 天标签窗提示）
- **标签战绩**：扫描 `projects/*/` 统计每标签已拍数/均分/精选数
- **覆盖矩阵**：标签 × 时代分段分布表

## CLI 命令一览

```bash
python topics_console.py check                  # 全量体检（schema/状态/id唯一/项目引用/日期）
python topics_console.py dedup                  # 近重复事件检测（bigram Jaccard，宁多报）
python topics_console.py stale                  # 超期候选（>4 周 candidate），默认 dry-run
python topics_console.py stale --apply          # 执行移入 blocked（reason=stale）
python topics_console.py stats                  # 覆盖矩阵（markdown 表）
python topics_console.py next                   # dry-run 挑选模拟（复现 PIPELINE Step 1）
python topics_console.py approve T006 [T014]    # 批准（支持多条）
python topics_console.py reject T013 --reason "理由"
python topics_console.py block T004 --reason "理由"
python topics_console.py add --title "..." --event "..." --year "..." \
    --tag "科技" --potential 8 --pitch "..." [--recommend 中]
```

所有命令支持 `--file PATH` 指定替代数据文件（开发自测用）。

### CLI 输出约定

- 每条结果一行：`OK T006 candidate→approved` / `ERROR T099: 未找到`
- exit code 0 = 成功，非 0 = 有错误
- `check` 输出问题清单；`stats` 输出 markdown 表；`next` 输出 `PICK` / `EXCLUDE` 行

## 数据安全

- **原子写**：临时文件 + `os.replace`，不会出现半写状态
- **写前重读**：每次提交前重新加载磁盘文件并比对版本 token（md5），与界面加载版本不一致时拒绝写入（防 21:00 流水线并发覆盖）
- **备份轮转**：每次写入前备份，保留 3 份（`.bak` / `.bak2` / `.bak3`）
- **schema 校验**：写入前校验全部条目，失败拒绝并给出可读错误
- **前向兼容**：未知字段一律保留，不丢弃

## 状态机

```
candidate → approved → used（终态，不可回退）
candidate → rejected（否决，事件永不复提）
candidate → blocked（冻结）
approved → candidate（撤销批准）
rejected → candidate（捞回）
blocked → candidate（捞回）
```

## 自测记录（2026-08-26）

用 `topics.test.json` 副本执行，8 个验收场景全部通过：

| # | 场景 | 结果 |
|---|---|---|
| 1 | 启动 → 23 条待审、推荐徽章正确、库存红条 | ✅ |
| 2 | 批量批准 7 条优先 → 库存变绿「可拍 7 夜」 | ✅ |
| 3 | 否决 T013 填理由 → 出现在冻结区且带理由 | ✅ |
| 4 | 投喂新选题 → id 顺延 T031、source=user | ✅ |
| 5 | 批准 T025（灾难）→ 显示「冷却中 → 09-02」 | ✅ |
| 6 | CLI approve + next（跳过冷却中标签条目） | ✅ |
| 7 | check 对坏数据报出全部错误且 exit≠0 | ✅ |
| 8 | 真实数据 approve T006 → gen_site.py 正常生成、选题池板块反映新状态 → 回滚无残留 | ✅ |

## 环境

- Windows 10/11，Python 3.13，零依赖（纯 stdlib）
- 所有文件 UTF-8 读写
- 不修改 PIPELINE.md / gen_site.py / gen_publish.py / projects/ 任何内容
