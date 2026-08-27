#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
topics_console.py — 选题池控制台（审核 Web UI + 治理 CLI）

用法：
  python topics_console.py serve [--port 8787] [--file PATH]   启动本地审核控制台
  python topics_console.py check [--file PATH]                  全量体检
  python topics_console.py dedup [--file PATH]                  近重复事件检测
  python topics_console.py stale [--apply] [--file PATH]        超期候选冷藏（默认 dry-run）
  python topics_console.py stats [--file PATH]                  覆盖矩阵（markdown）
  python topics_console.py next [--file PATH]                   dry-run 挑选模拟
  python topics_console.py approve T006 [T014 ...] [--file PATH]
  python topics_console.py reject T013 --reason "..." [--file PATH]
  python topics_console.py block T004 --reason "..." [--file PATH]
  python topics_console.py add --title "..." --event "..." --year "..." \
      --tag "..." --potential 8 --pitch "..." [--recommend 中] [--file PATH]

数据文件默认 topics/topics.json，--file 可指定替代文件（开发自测用）。
仅绑定 127.0.0.1，无鉴权，单用户本机工具。
"""

import argparse
import hashlib
import http.server
import json
import os
import re
import shutil
import sys
import urllib.parse
from datetime import date, datetime, timedelta
from pathlib import Path

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent
DEFAULT_TOPICS = ROOT / "topics" / "topics.json"
PROJECTS_DIR = ROOT / "projects"

VALID_STATUS = {"candidate", "approved", "used", "rejected", "blocked"}
VALID_TAGS = {"战争", "政治转折", "探索发现", "日常", "科技", "艺术", "灾难", "文明交汇"}
VALID_SOURCES = {"seed", "ai_weekly", "user"}
VALID_RECOMMEND = {"高", "中", "低"}

# 状态机：允许的转换
ALLOWED_TRANSITIONS = {
    "candidate": {"approved", "rejected", "blocked"},
    "approved": {"candidate"},            # 撤销批准
    "rejected": {"candidate"},            # 捞回
    "blocked": {"candidate"},             # 捞回
    "used": set(),                        # 终态
}

REC_RANK = {"高": 0, "中": 1, "低": 2}
REC_WORD = {"高": "优先", "中": "备选", "低": "存疑"}
REC_CLS = {"高": "rec-high", "中": "rec-mid", "低": "rec-low"}

# 年代分段
ERA_BUCKETS = ["先秦秦汉", "魏晋南北朝", "隋唐", "宋", "元", "明", "清", "近现代", "未分类"]
DYNASTY_MAP = {
    "夏": "先秦秦汉", "商": "先秦秦汉", "周": "先秦秦汉", "春秋": "先秦秦汉",
    "战国": "先秦秦汉", "秦": "先秦秦汉", "汉": "先秦秦汉", "先秦": "先秦秦汉",
    "新": "先秦秦汉",
    "三国": "魏晋南北朝", "魏": "魏晋南北朝", "晋": "魏晋南北朝",
    "南北朝": "魏晋南北朝", "北魏": "魏晋南北朝", "北齐": "魏晋南北朝", "北周": "魏晋南北朝",
    "隋": "隋唐", "唐": "隋唐", "五代": "隋唐",
    "宋": "宋", "北宋": "宋", "南宋": "宋", "辽": "宋", "金": "宋", "西夏": "宋",
    "元": "元",
    "明": "明",
    "清": "清",
}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ID_RE = re.compile(r"^T\d{3,}$")


# ---------------------------------------------------------------------------
# 数据层
# ---------------------------------------------------------------------------

def load_topics(path):
    """读 topics.json，返回完整 dict。"""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_topics(path, data):
    """原子写 + 备份轮转。调用前应已完成 validate。"""
    path = Path(path)
    backup(path)
    data["updated"] = date.today().isoformat()
    tmp = path.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def backup(path):
    """轮转备份：.bak3 ← .bak2 ← .bak ← 当前文件。"""
    path = Path(path)
    bak = path.with_suffix(".json.bak")
    bak2 = path.with_suffix(".json.bak2")
    bak3 = path.with_suffix(".json.bak3")
    if bak3.exists():
        bak3.unlink()
    if bak2.exists():
        bak2.rename(bak3)
    if bak.exists():
        bak.rename(bak2)
    if path.exists():
        shutil.copy2(path, bak)


def file_version(path):
    """文件内容的 md5，用作乐观锁版本 token。"""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def next_id(topics):
    """计算下一个 T0NN 编号。"""
    max_n = 0
    for t in topics:
        m = re.match(r"^T(\d+)$", t.get("id", ""))
        if m:
            max_n = max(max_n, int(m.group(1)))
    return f"T{max_n + 1:03d}"


def validate_topic(t):
    """校验单条，返回错误字符串列表（空=通过）。"""
    errs = []
    tid = t.get("id", "?")

    def req(field):
        v = t.get(field)
        if v is None or (isinstance(v, str) and not v.strip()):
            errs.append(f"{tid}: 必填字段 '{field}' 缺失或为空")

    for f in ("id", "title", "event", "year", "tag", "potential", "status", "source", "proposed_date"):
        req(f)

    if not ID_RE.match(str(t.get("id", ""))):
        errs.append(f"{tid}: id 格式应为 T0NN（实际 {t.get('id')!r}）")

    if t.get("status") not in VALID_STATUS:
        errs.append(f"{tid}: status 非法 {t.get('status')!r}，允许 {sorted(VALID_STATUS)}")

    if t.get("tag") not in VALID_TAGS:
        errs.append(f"{tid}: tag 非法 {t.get('tag')!r}，允许 {sorted(VALID_TAGS)}")

    if t.get("source") not in VALID_SOURCES:
        errs.append(f"{tid}: source 非法 {t.get('source')!r}，允许 {sorted(VALID_SOURCES)}")

    pot = t.get("potential")
    if not isinstance(pot, int) or not (1 <= pot <= 9):
        errs.append(f"{tid}: potential 应为 1-9 整数（实际 {pot!r}）")

    pd = t.get("proposed_date", "")
    if not DATE_RE.match(str(pd)):
        errs.append(f"{tid}: proposed_date 格式应为 YYYY-MM-DD（实际 {pd!r}）")
    else:
        try:
            datetime.strptime(pd, "%Y-%m-%d")
        except ValueError:
            errs.append(f"{tid}: proposed_date 不是合法日期 {pd!r}")

    if t.get("recommend") is not None and t.get("recommend") not in VALID_RECOMMEND:
        errs.append(f"{tid}: recommend 非法 {t.get('recommend')!r}，允许 高/中/低")

    st = t.get("status")
    if st == "used":
        if not t.get("used_date"):
            errs.append(f"{tid}: used 条目必须有 used_date")
        elif not DATE_RE.match(str(t.get("used_date", ""))):
            errs.append(f"{tid}: used_date 格式应为 YYYY-MM-DD")
        if not t.get("project"):
            errs.append(f"{tid}: used 条目必须有 project 文件夹名")
    if st in ("rejected", "blocked"):
        if not t.get("reason"):
            errs.append(f"{tid}: {st} 条目必须有 reason")

    return errs


def validate_all(data, projects_dir=PROJECTS_DIR):
    """全量校验，返回错误列表。"""
    errs = []
    if not isinstance(data, dict):
        return ["顶层结构应为 JSON object"]
    if data.get("schema") != "topics/1":
        errs.append(f"schema 应为 'topics/1'（实际 {data.get('schema')!r}）")
    topics = data.get("topics")
    if not isinstance(topics, list):
        errs.append("topics 应为数组")
        return errs

    seen_ids = set()
    for t in topics:
        errs.extend(validate_topic(t))
        tid = t.get("id")
        if tid in seen_ids:
            errs.append(f"{tid}: id 重复")
        seen_ids.add(tid)

    # used 条目引用的 project 文件夹是否存在
    for t in topics:
        if t.get("status") == "used":
            proj = t.get("project", "")
            if proj and projects_dir and not (projects_dir / proj).exists():
                errs.append(f"{t['id']}: project 文件夹不存在 projects/{proj}")

    return errs


# ---------------------------------------------------------------------------
# 业务层（纯函数）
# ---------------------------------------------------------------------------

def can_transition(old, new):
    return new in ALLOWED_TRANSITIONS.get(old, set())


def stock_state(topics):
    """返回 (level, count, message)；level ∈ red/yellow/green。"""
    n = sum(1 for t in topics if t.get("status") == "approved")
    if n == 0:
        return "red", n, "池空：今晚按规则跳过，等待人工批准"
    if n < 3:
        return "yellow", n, "弹药不足三条，请尽快审批"
    return "green", n, f"可拍 {n} 夜"


def cooldown_map(topics, today=None):
    """7 天标签冷却：返回 {tag: date_available}。"""
    if today is None:
        today = date.today()
    cooled = {}
    for t in topics:
        if t.get("status") != "used":
            continue
        ud = t.get("used_date", "")
        if not ud:
            continue
        try:
            d = datetime.strptime(ud, "%Y-%m-%d").date()
        except ValueError:
            continue
        delta = (today - d).days
        if 0 <= delta < 7:
            avail = d + timedelta(days=7)
            tag = t.get("tag", "")
            if tag and (tag not in cooled or avail < cooled[tag]):
                cooled[tag] = avail
    return cooled


def next_pick(topics, today=None):
    """按 PIPELINE Step 1 模拟挑选：approved 中 potential 最高 + 过 7 天标签窗。
    返回 (picked_topic_or_None, exclude_reasons: [(id, title, reason)])。"""
    if today is None:
        today = date.today()
    cooled = cooldown_map(topics, today)
    approved = [t for t in topics if t.get("status") == "approved"]

    candidates = []
    excluded = []
    for t in approved:
        tag = t.get("tag", "")
        if tag in cooled:
            excluded.append((t["id"], t.get("title", ""),
                             f"标签「{tag}」冷却中至 {cooled[tag].strftime('%m-%d')}"))
        else:
            candidates.append(t)

    if not candidates:
        return None, excluded

    candidates.sort(key=lambda t: -t.get("potential", 0))
    pick = candidates[0]
    best_pot = pick.get("potential", 0)
    for t in candidates[1:]:
        excluded.append((t["id"], t.get("title", ""),
                         f"潜力 {t.get('potential', 0)} < {best_pot}"))
    return pick, excluded


def _bigrams(s):
    s = re.sub(r"\s+", "", str(s))
    return set(s[i:i + 2] for i in range(len(s) - 1)) if len(s) >= 2 else set()


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def find_duplicates(topics, threshold=0.3):
    """近重复检测：event 是查重关键字段，分别对 event 和 title 做 bigram Jaccard，
    取最大值。返回 [(id_a, id_b, text_a, text_b, score)]，score >= threshold。
    宁多报不漏报。"""
    items = [(t["id"], t.get("title", ""), t.get("event", ""))
             for t in topics if t.get("status") in ("candidate", "used", "rejected", "blocked")]
    grams = []
    for tid, title, ev in items:
        grams.append((tid, _bigrams(ev), _bigrams(f"{ev}{title}")))
    results = []
    for i in range(len(grams)):
        for j in range(i + 1, len(grams)):
            # event 单独比 + event+title 联合比，取最大
            score_ev = _jaccard(grams[i][1], grams[j][1])
            score_all = _jaccard(grams[i][2], grams[j][2])
            score = max(score_ev, score_all)
            if score >= threshold:
                a = next(x for x in items if x[0] == grams[i][0])
                b = next(x for x in items if x[0] == grams[j][0])
                results.append((a[0], b[0], f"{a[2]}｜{a[1]}", f"{b[2]}｜{b[1]}", round(score, 2)))
    results.sort(key=lambda r: -r[4])
    return results


def find_stale(topics, today=None, weeks=4):
    """proposed_date 超 N 周仍是 candidate → 应移入 blocked。"""
    if today is None:
        today = date.today()
    cutoff = today - timedelta(weeks=weeks)
    stale = []
    for t in topics:
        if t.get("status") != "candidate":
            continue
        pd = t.get("proposed_date", "")
        try:
            d = datetime.strptime(pd, "%Y-%m-%d").date()
        except ValueError:
            continue
        if d < cutoff:
            stale.append(t)
    return stale


def classify_era(year):
    """自由文本年代 → 时代分段。"""
    y = str(year).strip()
    if not y:
        return "未分类"

    # 含"前" → 先秦秦汉（公元前）
    if "前" in y:
        return "先秦秦汉"

    # 朝代关键词匹配（长词优先）
    for dynasty in sorted(DYNASTY_MAP, key=len, reverse=True):
        if dynasty in y:
            return DYNASTY_MAP[dynasty]

    # 提取纯数字
    m = re.search(r"(\d+)", y)
    if m:
        n = int(m.group(1))
        if n <= 220:
            return "先秦秦汉"
        if n <= 589:
            return "魏晋南北朝"
        if n <= 907:
            return "隋唐"
        if n <= 1279:
            return "宋"
        if n <= 1368:
            return "元"
        if n <= 1644:
            return "明"
        if n <= 1912:
            return "清"
        return "近现代"

    return "未分类"


def coverage_matrix(topics):
    """覆盖矩阵：行=标签，列=时代分段。返回 (tags, matrix dict{tag:{era:count}})。"""
    tags = sorted(VALID_TAGS)
    matrix = {tag: {era: 0 for era in ERA_BUCKETS} for tag in tags}
    for t in topics:
        tag = t.get("tag", "")
        if tag not in matrix:
            continue
        era = classify_era(t.get("year", ""))
        matrix[tag][era] += 1
    return tags, matrix


def tag_stats(projects_dir=PROJECTS_DIR):
    """扫描 projects/ 统计标签战绩：{tag: {n, sum, cnt, sel}}。"""
    stats = {}
    if not projects_dir.exists():
        return stats
    for pdir in sorted(projects_dir.iterdir()):
        if not pdir.is_dir() or not (pdir / "status.json").exists():
            continue
        try:
            with open(pdir / "status.json", encoding="utf-8") as f:
                st = json.load(f)
            con = {}
            if (pdir / "concept.json").exists():
                with open(pdir / "concept.json", encoding="utf-8") as f:
                    con = json.load(f)
            ev = {}
            if (pdir / "evaluation.json").exists():
                with open(pdir / "evaluation.json", encoding="utf-8") as f:
                    ev = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        tag = (con.get("topic") or {}).get("tag", "")
        if not tag:
            continue
        s = stats.setdefault(tag, {"n": 0, "sum": 0.0, "cnt": 0, "sel": 0})
        s["n"] += 1
        scores = ev.get("ai_scores") or {}
        avg = scores.get("average")
        if avg is not None:
            s["sum"] += avg
            s["cnt"] += 1
        if st.get("status") == "selected":
            s["sel"] += 1
    return stats


# ---------------------------------------------------------------------------
# 变更操作（CLI 与 Web 共用）
# ---------------------------------------------------------------------------

class ChangeError(Exception):
    pass


def apply_status_change(data, tid, new_status, reason=None):
    """对内存数据应用状态变更，返回变更描述。校验失败抛 ChangeError。"""
    topic = None
    for t in data["topics"]:
        if t.get("id") == tid:
            topic = t
            break
    if topic is None:
        raise ChangeError(f"{tid}: 未找到")

    old = topic.get("status")
    if old == new_status:
        raise ChangeError(f"{tid}: 已经是 {new_status}")
    if not can_transition(old, new_status):
        raise ChangeError(f"{tid}: 不允许 {old}→{new_status}（used 为终态）")

    if new_status in ("rejected", "blocked"):
        if not reason or not reason.strip():
            raise ChangeError(f"{tid}: {new_status} 必须填写理由")
        topic["reason"] = reason.strip()
    else:
        # 离开 rejected/blocked 时清除 reason
        topic.pop("reason", None)

    topic["status"] = new_status
    return f"{tid} {old}→{new_status}"


def apply_add(data, title, event, year, tag, potential, pitch, recommend="中"):
    """新增 user 投喂的 candidate。"""
    if tag not in VALID_TAGS:
        raise ChangeError(f"tag 非法 {tag!r}")
    pot = int(potential)
    if not (1 <= pot <= 9):
        raise ChangeError("potential 应为 1-9 整数")
    tid = next_id(data["topics"])
    topic = {
        "id": tid,
        "title": title.strip(),
        "event": event.strip(),
        "year": year.strip(),
        "tag": tag,
        "potential": pot,
        "status": "candidate",
        "source": "user",
        "proposed_date": date.today().isoformat(),
        "recommend": recommend if recommend in VALID_RECOMMEND else "中",
        "pitch": pitch.strip(),
    }
    data["topics"].append(topic)
    return tid


# ---------------------------------------------------------------------------
# CLI 命令
# ---------------------------------------------------------------------------

def cmd_check(args):
    data = load_topics(args.file)
    errs = validate_all(data)
    if errs:
        for e in errs:
            print(f"ERROR {e}")
        print(f"\n共 {len(errs)} 个问题")
        return 1
    print("OK 全量校验通过，无错误")
    return 0


def cmd_dedup(args):
    data = load_topics(args.file)
    dups = find_duplicates(data["topics"])
    if not dups:
        print("OK 未发现近重复事件对")
        return 0
    for a, b, ta, tb, score in dups:
        print(f"DUP {a} ↔ {b}  相似度 {score}")
        print(f"    {ta}")
        print(f"    {tb}")
    print(f"\n共 {len(dups)} 对疑似重复（宁多报不漏报，请人工判断）")
    return 0


def cmd_stale(args):
    data = load_topics(args.file)
    stale = find_stale(data["topics"])
    if not stale:
        print("OK 无超期候选")
        return 0
    for t in stale:
        print(f"STALE {t['id']} {t.get('title','')}（proposed {t.get('proposed_date')}）")
    if not args.apply:
        print(f"\n[dry-run] 共 {len(stale)} 条超期候选，加 --apply 执行移入 blocked")
        return 0
    for t in stale:
        t["status"] = "blocked"
        t["reason"] = "stale"
    save_topics(args.file, data)
    print(f"\nAPPLIED 已将 {len(stale)} 条移入 blocked（reason=stale）")
    return 0


def cmd_stats(args):
    data = load_topics(args.file)
    tags, matrix = coverage_matrix(data["topics"])
    # 表头
    lines = []
    header = "| 标签 | " + " | ".join(ERA_BUCKETS) + " | 合计 |"
    sep = "|" + "---|" * (len(ERA_BUCKETS) + 2)
    lines.append(header)
    lines.append(sep)
    for tag in tags:
        row = matrix[tag]
        vals = [str(row[era]) for era in ERA_BUCKETS]
        total = sum(row.values())
        lines.append(f"| {tag} | " + " | ".join(vals) + f" | {total} |")
    # 列合计
    col_totals = [sum(matrix[tag][era] for tag in tags) for era in ERA_BUCKETS]
    lines.append("| **合计** | " + " | ".join(str(c) for c in col_totals)
                 + f" | {sum(col_totals)} |")
    print("\n".join(lines))
    return 0


def cmd_next(args):
    data = load_topics(args.file)
    pick, excluded = next_pick(data["topics"])
    if pick is None:
        n_appr = sum(1 for t in data["topics"] if t.get("status") == "approved")
        if n_appr == 0:
            print("PICK_NONE approved=0 池空，今晚按规则跳过")
        else:
            print("PICK_NONE 所有 approved 条目均在冷却中")
            for tid, title, reason in excluded:
                print(f"EXCLUDE {tid} {reason}")
        return 0
    print(f"PICK {pick['id']} {pick.get('title','')}（潜力 {pick.get('potential')}，标签 {pick.get('tag')}）")
    for tid, title, reason in excluded:
        print(f"EXCLUDE {tid} {reason}")
    return 0


def _load_and_lock(args):
    """读数据 + 全量校验，返回 data；校验失败抛 SystemExit(1)。"""
    data = load_topics(args.file)
    errs = validate_all(data)
    if errs:
        for e in errs:
            print(f"ERROR {e}")
        raise SystemExit(1)
    return data


def cmd_approve(args):
    data = _load_and_lock(args)
    results = []
    for tid in args.ids:
        try:
            desc = apply_status_change(data, tid, "approved")
            results.append(("OK", desc))
        except ChangeError as e:
            results.append(("ERROR", str(e)))
    if any(r[0] == "OK" for r in results):
        save_topics(args.file, data)
    for status, desc in results:
        print(f"{status} {desc}")
    return 0 if all(r[0] == "OK" for r in results) else 1


def cmd_reject(args):
    data = _load_and_lock(args)
    try:
        desc = apply_status_change(data, args.id, "rejected", reason=args.reason)
        save_topics(args.file, data)
        print(f"OK {desc}")
        return 0
    except ChangeError as e:
        print(f"ERROR {e}")
        return 1


def cmd_block(args):
    data = _load_and_lock(args)
    try:
        desc = apply_status_change(data, args.id, "blocked", reason=args.reason)
        save_topics(args.file, data)
        print(f"OK {desc}")
        return 0
    except ChangeError as e:
        print(f"ERROR {e}")
        return 1


def cmd_add(args):
    data = _load_and_lock(args)
    try:
        tid = apply_add(data, args.title, args.event, args.year, args.tag,
                        args.potential, args.pitch, args.recommend)
        errs = validate_all(data)
        if errs:
            for e in errs:
                print(f"ERROR {e}")
            return 1
        save_topics(args.file, data)
        print(f"OK {tid} added candidate")
        return 0
    except ChangeError as e:
        print(f"ERROR {e}")
        return 1


# ---------------------------------------------------------------------------
# Web UI
# ---------------------------------------------------------------------------

def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def space_year(y):
    return re.sub(r"^(前|约)", r"\1 ", str(y).strip())


def space_cjk_digits(t):
    t = re.sub(r"(?<=[\u4e00-\u9fff])(\d)", r" \1", str(t))
    return re.sub(r"(\d)(?=[\u4e00-\u9fff])", r"\1 ", t)


CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{background:#141311;color:#e8e4de;font-family:"Noto Serif SC",-apple-system,"Microsoft YaHei",sans-serif;line-height:1.6;padding:20px;max-width:1200px;margin:0 auto}
h1{font-size:1.4em;color:#c98a3d;margin-bottom:4px}
h2{font-size:1.15em;margin:16px 0 8px}
.subtitle{color:#9a948a;font-size:.85em;margin-bottom:16px}
a{color:#c98a3d;text-decoration:none}
a:hover{text-decoration:underline}

/* 库存状态条 */
.stock-bar{padding:12px 16px;border-radius:6px;margin-bottom:16px;font-weight:600;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.stock-red{background:#3a1a14;border:1px solid #c45a3d;color:#e89880}
.stock-yellow{background:#3a3014;border:1px solid #c9a23d;color:#e8c870}
.stock-green{background:#1a2e14;border:1px solid #6a9a5a;color:#90c078}
.stock-bar .count{font-size:1.3em}
.stock-bar .msg{font-weight:400;font-size:.9em;opacity:.85}

/* Tabs */
.tabs{display:flex;gap:4px;border-bottom:1px solid #2d2a26;margin-bottom:16px;flex-wrap:wrap}
.tabs a{padding:8px 16px;color:#9a948a;border-bottom:2px solid transparent;font-size:.9em}
.tabs a.active{color:#c98a3d;border-bottom-color:#c98a3d}
.tabs a:hover{color:#e8e4de;text-decoration:none}

/* 筛选栏 */
.filters{display:flex;gap:8px;align-items:center;margin-bottom:12px;flex-wrap:wrap;font-size:.85em}
.filters select,.filters button{background:#1e1c19;border:1px solid #3d3a36;color:#e8e4de;padding:4px 10px;border-radius:4px;cursor:pointer;font-size:.85em}
.filters label{color:#9a948a}

/* 批量操作栏 */
.batch-bar{background:#1e1c19;border:1px solid #3d3a36;border-radius:6px;padding:10px 14px;margin-bottom:12px;display:none;align-items:center;gap:10px;font-size:.9em}
.batch-bar.show{display:flex}
.batch-bar button{padding:5px 14px;border-radius:4px;border:none;cursor:pointer;font-size:.85em}
.btn-approve{background:#6a9a5a;color:#141311;font-weight:600}
.btn-reject{background:#c45a3d;color:#fff}
.btn-neutral{background:#3d3a36;color:#e8e4de}

/* 选题卡片 */
.card{background:#1e1c19;border:1px solid #2d2a26;border-radius:6px;padding:14px 16px;margin-bottom:10px}
.card:hover{border-color:#3d3a36}
.card-head{display:flex;align-items:flex-start;gap:10px;margin-bottom:6px}
.card-check{margin-top:4px}
.card-id{color:#9a948a;font-family:monospace;font-size:.85em;white-space:nowrap}
.card-title{font-weight:600;font-size:1em;flex:1}
.card-pitch{color:#c8c2b8;font-size:.88em;margin:4px 0 8px;padding-left:24px}
.card-meta{display:flex;gap:10px;flex-wrap:wrap;font-size:.8em;color:#9a948a;padding-left:24px;align-items:center}
.card-actions{padding-left:24px;margin-top:8px;display:flex;gap:8px}
.card-actions button{padding:3px 12px;border-radius:4px;border:1px solid #3d3a36;background:#252320;color:#e8e4de;cursor:pointer;font-size:.82em}
.card-actions button:hover{border-color:#c98a3d}
.card-actions .btn-ap{border-color:#6a9a5a;color:#90c078}
.card-actions .btn-rj{border-color:#c45a3d;color:#e89880}
.card-actions .bk{border-color:#c9a23d;color:#e8c870}

/* 徽章 */
.badge{display:inline-block;padding:1px 8px;border-radius:3px;font-size:.75em;font-weight:600}
.rec-high{border:1px solid #c98a3d;color:#c98a3d}
.rec-mid{border:1px solid #5a5650;color:#9a948a}
.rec-low{border:1px solid #7a4a3a;color:#a07060}
.badge-cool{background:#3a3014;color:#e8c870;padding:1px 6px;border-radius:3px;font-size:.75em}
.badge-ok{background:#1a2e14;color:#90c078;padding:1px 6px;border-radius:3px;font-size:.75em}
.tag-chip{background:#252320;padding:1px 8px;border-radius:3px;font-size:.8em}

/* 否决理由内联输入 */
.reject-row{display:none;padding-left:24px;margin-top:8px;gap:8px;align-items:center}
.reject-row.show{display:flex}
.reject-row input{flex:1;background:#141311;border:1px solid #3d3a36;color:#e8e4de;padding:5px 10px;border-radius:4px;font-size:.85em}
.reject-row button{padding:4px 12px;border-radius:4px;border:none;cursor:pointer;font-size:.82em}

/* 表单 */
.form-add{background:#1e1c19;border:1px solid #2d2a26;border-radius:6px;padding:16px;margin-bottom:16px}
.form-add summary{cursor:pointer;color:#c98a3d;font-weight:600;font-size:.95em;margin-bottom:8px}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
.form-grid .full{grid-column:1/-1}
.form-grid label{display:block;font-size:.82em;color:#9a948a;margin-bottom:2px}
.form-grid input,.form-grid select,.form-grid textarea{width:100%;background:#141311;border:1px solid #3d3a36;color:#e8e4de;padding:6px 10px;border-radius:4px;font-size:.88em;font-family:inherit}
.form-grid textarea{resize:vertical;min-height:50px}
.form-grid button{grid-column:1/-1;padding:8px;background:#6a9a5a;color:#141311;border:none;border-radius:4px;cursor:pointer;font-weight:600;font-size:.9em}

/* 表格 */
table{width:100%;border-collapse:collapse;font-size:.85em;margin:8px 0}
th,td{padding:6px 10px;text-align:left;border-bottom:1px solid #2d2a26}
th{color:#9a948a;font-weight:600}
.matrix td.num{text-align:center;font-family:monospace}
.matrix tr:hover{background:#1e1c19}

/* 消息 */
.msg-ok{background:#1a2e14;border:1px solid #6a9a5a;color:#90c078;padding:10px 14px;border-radius:6px;margin-bottom:12px}
.msg-err{background:#3a1a14;border:1px solid #c45a3d;color:#e89880;padding:10px 14px;border-radius:6px;margin-bottom:12px}

.frozen-list .card{opacity:.8}
.empty{color:#6a6560;text-align:center;padding:30px;font-size:.9em}
"""


def render_card(t, version, show_check=True, for_tab="candidate"):
    """渲染单条选题卡片。"""
    tid = esc(t["id"])
    title = esc(space_cjk_digits(t.get("title", "")))
    pitch = esc(t.get("pitch", ""))
    year = esc(space_year(t.get("year", "")))
    tag = esc(t.get("tag", ""))
    pot = t.get("potential", 0)
    rec = t.get("recommend", "中")
    source = esc(t.get("source", ""))
    pd = esc(t.get("proposed_date", ""))

    badge = ""
    if for_tab == "candidate" and rec:
        badge = f'<span class="badge {REC_CLS.get(rec, "rec-mid")}">{REC_WORD.get(rec, "备选")}</span>'

    # 冷却徽章（approved 区）：冷却信息由 render_page 预计算后注入 t["_cool"]
    cool_badge = ""
    if for_tab == "approved":
        if t.get("_cool"):
            cool_badge = f'<span class="badge-cool">冷却中 → {t["_cool"]}</span>'
        else:
            cool_badge = '<span class="badge-ok">今夜可拍</span>'

    check = f'<input type="checkbox" class="card-check" name="ids" value="{tid}" data-rec="{esc(rec)}">' if show_check else ""

    actions = ""
    if for_tab == "candidate":
        actions = f'''
        <div class="card-actions">
          <button type="submit" formaction="/single" name="action" value="approve" class="btn-ap">批准</button>
          <button type="button" class="btn-rj" onclick="toggleReject('{tid}')">否决</button>
          <button type="submit" formaction="/single" name="action" value="block" class="bk">冻结</button>
        </div>
        <div class="reject-row" id="rj-{tid}">
          <input type="text" name="reason_{tid}" placeholder="否决理由（必填）" maxlength="200">
          <button type="submit" formaction="/single" name="action" value="reject" class="btn-reject">确认否决</button>
          <button type="button" class="btn-neutral" onclick="toggleReject('{tid}')">取消</button>
        </div>'''
    elif for_tab == "approved":
        actions = f'''
        <div class="card-actions">
          <button type="submit" formaction="/single" name="action" value="revoke" class="btn-neutral">撤销批准</button>
        </div>'''
    elif for_tab in ("rejected", "blocked"):
        reason = esc(t.get("reason", ""))
        actions = f'''
        <div class="card-actions">
          <button type="submit" formaction="/single" name="action" value="revive" class="btn-ap">捞回待审</button>
        </div>
        <div class="card-meta" style="margin-top:4px">理由：{reason}</div>'''

    pitch_html = f'<p class="card-pitch">{pitch}</p>' if pitch else ""

    return f'''
    <div class="card">
      <input type="hidden" name="single_id" value="{tid}">
      <div class="card-head">
        {check}
        <span class="card-id">{tid}</span>
        <span class="card-title">{title}</span>
        {badge}{cool_badge}
      </div>
      {pitch_html}
      <div class="card-meta">
        <span class="tag-chip">{tag}</span>
        <span>{year}</span>
        <span>潜力 {pot}</span>
        <span>{source} · {pd}</span>
      </div>
      {actions}
    </div>'''


def render_tag_stats_html(stats):
    if not stats:
        return '<p class="empty">暂无已拍项目</p>'
    rows = []
    for tag, s in sorted(stats.items(), key=lambda kv: -kv[1]["n"]):
        avg = f'{s["sum"] / s["cnt"]:.1f}' if s["cnt"] else "—"
        rows.append(f"<tr><td>{esc(tag)}</td><td>{s['n']}</td><td>{avg}</td>"
                    f"<td>{s['sel']} / {s['n']}</td></tr>")
    return f'''<table>
      <tr><th>标签</th><th>已拍</th><th>均分</th><th>精选</th></tr>
      {"".join(rows)}
    </table>'''


def render_matrix_html(topics):
    tags, matrix = coverage_matrix(topics)
    header = "".join(f"<th>{era}</th>" for era in ERA_BUCKETS)
    rows = []
    for tag in tags:
        cells = "".join(f'<td class="num">{matrix[tag][era] or ""}</td>' for era in ERA_BUCKETS)
        total = sum(matrix[tag].values())
        rows.append(f"<tr><td>{esc(tag)}</td>{cells}<td class='num'><b>{total or ''}</b></td></tr>")
    col_totals = [sum(matrix[tag][era] for tag in tags) for era in ERA_BUCKETS]
    total_cells = "".join(f'<td class="num">{c or ""}</td>' for c in col_totals)
    return f'''<table class="matrix">
      <tr><th>标签</th>{header}<th>合计</th></tr>
      {"".join(rows)}
      <tr><td><b>合计</b></td>{total_cells}<td class="num"><b>{sum(col_totals)}</b></td></tr>
    </table>'''


def render_page(data, version, tab="candidate", message="", msg_type="ok",
                filter_rec="", filter_tag="", sort_by="potential"):
    topics = data["topics"]
    level, n_appr, stock_msg = stock_state(topics)
    n_cand = sum(1 for t in topics if t.get("status") == "candidate")
    n_used = sum(1 for t in topics if t.get("status") == "used")
    n_frozen = sum(1 for t in topics if t.get("status") in ("rejected", "blocked"))

    cooled = cooldown_map(topics)
    # 给 approved 条目注入冷却信息
    for t in topics:
        if t.get("status") == "approved":
            avail = cooled.get(t.get("tag", ""))
            t["_cool"] = avail.strftime("%m-%d") if avail else ""

    def by_status(s):
        return [t for t in topics if t.get("status") == s]

    candidates = by_status("candidate")
    approved = sorted(by_status("approved"), key=lambda t: -t.get("potential", 0))
    used = sorted(by_status("used"), key=lambda t: t.get("used_date", ""), reverse=True)
    rejected = by_status("rejected")
    blocked = by_status("blocked")

    # 筛选 + 排序
    if filter_rec:
        candidates = [t for t in candidates if t.get("recommend") == filter_rec]
    if filter_tag:
        candidates = [t for t in candidates if t.get("tag") == filter_tag]
    if sort_by == "potential":
        candidates.sort(key=lambda t: (REC_RANK.get(t.get("recommend", "中"), 1), -t.get("potential", 0)))
    else:
        candidates.sort(key=lambda t: t.get("proposed_date", ""), reverse=True)

    # Tabs
    tabs = [
        ("candidate", f"待审 ({n_cand})"),
        ("approved", f"可拍 ({n_appr})"),
        ("used", f"已拍 ({n_used})"),
        ("frozen", f"冻结与否决 ({n_frozen})"),
        ("stats", "标签战绩"),
    ]
    tabs_html = "".join(
        f'<a href="?tab={t}" class="{"active" if t == tab else ""}">{label}</a>'
        for t, label in tabs
    )

    # 消息
    msg_html = ""
    if message:
        cls = "msg-ok" if msg_type == "ok" else "msg-err"
        msg_html = f'<div class="{cls}">{esc(message)}</div>'

    # 筛选栏（仅待审 tab）
    filters_html = ""
    if tab == "candidate":
        tag_opts = "".join(f'<option value="{t}" {"selected" if t==filter_tag else ""}>{t}</option>'
                           for t in sorted(VALID_TAGS))
        filters_html = f'''
        <div class="filters">
          <label>推荐级</label>
          <select onchange="applyFilter()" id="f-rec">
            <option value="">全部</option>
            <option value="高" {"selected" if filter_rec=="高" else ""}>优先</option>
            <option value="中" {"selected" if filter_rec=="中" else ""}>备选</option>
            <option value="低" {"selected" if filter_rec=="低" else ""}>存疑</option>
          </select>
          <label>标签</label>
          <select onchange="applyFilter()" id="f-tag">
            <option value="">全部</option>{tag_opts}
          </select>
          <label>排序</label>
          <select onchange="applyFilter()" id="f-sort">
            <option value="potential" {"selected" if sort_by=="potential" else ""}>推荐级+潜力</option>
            <option value="date" {"selected" if sort_by=="date" else ""}>提名日期</option>
          </select>
        </div>'''

    # 批量操作栏
    batch_html = ""
    if tab == "candidate":
        batch_html = '''
        <div class="batch-bar" id="batch-bar">
          <span id="batch-count">已选 0 条</span>
          <button type="submit" name="action" value="approve" class="btn-approve" onclick="return confirmBatch()">批量批准</button>
          <button type="button" class="btn-reject" onclick="showBatchReject()">批量否决</button>
        </div>'''

    # 投喂表单
    add_form = ""
    if tab == "candidate":
        tag_opts = "".join(f'<option value="{t}">{t}</option>' for t in sorted(VALID_TAGS))
        add_form = f'''
        <details class="form-add" {"open" if False else ""}>
          <summary>+ 投喂新选题</summary>
          <form method="POST" action="/add">
            <input type="hidden" name="version" value="{version}">
            <div class="form-grid">
              <div><label>题目 *</label><input name="title" required></div>
              <div><label>历史事件 *</label><input name="event" required></div>
              <div><label>年代 *</label><input name="year" placeholder="如 208 / 前49 / 唐" required></div>
              <div><label>标签 *</label><select name="tag">{tag_opts}</select></div>
              <div><label>视觉潜力 (1-9) *</label><input name="potential" type="number" min="1" max="9" value="7" required></div>
              <div><label>推荐分级</label><select name="recommend"><option value="高">优先</option><option value="中" selected>备选</option><option value="低">存疑</option></select></div>
              <div class="full"><label>一句话提名理由（视觉钩子）*</label><textarea name="pitch" required></textarea></div>
              <button type="submit">投喂到待审区</button>
            </div>
          </form>
        </details>'''

    # 内容区
    content = ""
    if tab == "candidate":
        cards = "".join(render_card(t, version, for_tab="candidate") for t in candidates)
        content = f'''
        <form method="POST" action="/bulk" id="bulk-form">
          <input type="hidden" name="version" value="{version}">
          <input type="hidden" name="tab" value="{tab}">
          <input type="hidden" name="filter_rec" value="{esc(filter_rec)}">
          <input type="hidden" name="filter_tag" value="{esc(filter_tag)}">
          <input type="hidden" name="sort_by" value="{esc(sort_by)}">
          {batch_html}
          {cards or '<p class="empty">（暂无待审提名）</p>'}
        </form>
        {add_form}'''
    elif tab == "approved":
        cards = "".join(render_card(t, version, show_check=False, for_tab="approved") for t in approved)
        # 每条 approved 单独一个 form（撤销操作）
        content = f'''
        {"".join(_wrap_card_form(t, version, tab, filter_rec, filter_tag, sort_by) for t in approved) or '<p class="empty">（可拍队列为空）</p>'}'''
    elif tab == "used":
        rows = []
        for t in used:
            result = esc(t.get("result", ""))
            rows.append(f'''<div class="card">
              <div class="card-head">
                <span class="card-id">{esc(t["id"])}</span>
                <span class="card-title">{esc(space_cjk_digits(t.get("title","")))}</span>
              </div>
              <div class="card-meta">
                <span class="tag-chip">{esc(t.get("tag",""))}</span>
                <span>{esc(space_year(t.get("year","")))}</span>
                <span>潜力 {t.get("potential",0)}</span>
                <span>拍摄于 {esc(t.get("used_date",""))}</span>
              </div>
              {f'<div class="card-meta" style="margin-top:4px">{result}</div>' if result else ""}
            </div>''')
        content = "".join(rows) or '<p class="empty">（暂无已拍）</p>'
    elif tab == "frozen":
        parts = []
        for label, items in (("否决", rejected), ("冻结", blocked)):
            if items:
                parts.append(f'<h2>{label}（{len(items)}）</h2>')
                parts.append("".join(_wrap_card_form(t, version, tab, filter_rec, filter_tag, sort_by,
                                                     for_tab="rejected" if label=="否决" else "blocked")
                                   for t in items))
        content = "".join(parts) or '<p class="empty">（暂无冻结与否决）</p>'
    elif tab == "stats":
        stats = tag_stats()
        content = f'''
        <h2>标签战绩（来自 projects/ 已拍项目）</h2>
        {render_tag_stats_html(stats)}
        <h2>覆盖矩阵（标签 × 时代）</h2>
        {render_matrix_html(topics)}'''

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>选题池控制台</title>
<style>{CSS}</style>
</head>
<body>
<h1>选题池控制台</h1>
<p class="subtitle">topics/topics.json · 人管池子，AI 管挑拣 · 仅本地访问</p>

<div class="stock-bar stock-{level}">
  <span class="count">可拍 {n_appr} 夜</span>
  <span class="msg">{esc(stock_msg)}</span>
  <span class="msg" style="margin-left:auto">待审 {n_cand} · 已拍 {n_used} · 冻结/否决 {n_frozen}</span>
</div>

{msg_html}

<div class="tabs">{tabs_html}</div>

{filters_html}

{content}

<script>
function toggleReject(id) {{
  var row = document.getElementById('rj-' + id);
  row.classList.toggle('show');
  if (row.classList.contains('show')) row.querySelector('input').focus();
}}
function applyFilter() {{
  var r = document.getElementById('f-rec').value;
  var t = document.getElementById('f-tag').value;
  var s = document.getElementById('f-sort').value;
  window.location.href = '?tab=candidate&rec=' + encodeURIComponent(r) + '&tag=' + encodeURIComponent(t) + '&sort=' + s;
}}
document.querySelectorAll('.card-check').forEach(function(cb) {{
  cb.addEventListener('change', updateBatch);
}});
function updateBatch() {{
  var n = document.querySelectorAll('.card-check:checked').length;
  var bar = document.getElementById('batch-bar');
  document.getElementById('batch-count').textContent = '已选 ' + n + ' 条';
  bar.classList.toggle('show', n > 0);
}}
function confirmBatch() {{
  var n = document.querySelectorAll('.card-check:checked').length;
  if (n > 5) return confirm('即将批量批准 ' + n + ' 条选题，确认？');
  return true;
}}
function showBatchReject() {{
  var n = document.querySelectorAll('.card-check:checked').length;
  if (n === 0) return;
  var reason = prompt('批量否决理由（必填，将应用于所有选中条目）：');
  if (reason && reason.trim()) {{
    var form = document.getElementById('bulk-form');
    var btnApprove = form.querySelector('.btn-approve');
    if (btnApprove) btnApprove.disabled = true;
    var inp = document.createElement('input');
    inp.type = 'hidden'; inp.name = 'bulk_reason'; inp.value = reason.trim();
    form.appendChild(inp);
    var act = document.createElement('input');
    act.type = 'hidden'; act.name = 'action'; act.value = 'reject';
    form.appendChild(act);
    form.submit();
  }}
}}
</script>
</body>
</html>'''


def _wrap_card_form(t, version, tab, filter_rec, filter_tag, sort_by, for_tab=None):
    """把单条卡片包在独立 form 里（用于 approved/frozen 的单条操作）。"""
    ft = for_tab or tab
    card = render_card(t, version, show_check=False, for_tab=ft)
    rec = urllib.parse.urlencode({"tab": tab, "rec": filter_rec, "tag": filter_tag, "sort": sort_by})
    return f'''
    <form method="POST" action="/single" style="margin-bottom:0">
      <input type="hidden" name="version" value="{version}">
      <input type="hidden" name="tab" value="{esc(tab)}">
      <input type="hidden" name="redirect" value="{rec}">
      {card}
    </form>'''


class ConsoleHandler(http.server.BaseHTTPRequestHandler):
    topics_file = DEFAULT_TOPICS

    def log_message(self, fmt, *args):
        pass  # 静默日志

    def _send(self, code, body, content_type="text/html; charset=utf-8", redirect=None):
        if redirect:
            self.send_response(303)
            self.send_header("Location", redirect)
            self.end_headers()
            return
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _load(self):
        return load_topics(self.topics_file)

    def _check_version(self, data, form_version):
        """写前重读：比较磁盘版本与表单版本。"""
        current = file_version(self.topics_file)
        if current != form_version:
            return False
        return True

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if parsed.path != "/":
            self._send(404, "Not Found")
            return
        tab = params.get("tab", ["candidate"])[0]
        if tab not in ("candidate", "approved", "used", "frozen", "stats"):
            tab = "candidate"
        data = self._load()
        version = file_version(self.topics_file)
        html = render_page(
            data, version, tab=tab,
            filter_rec=params.get("rec", [""])[0],
            filter_tag=params.get("tag", [""])[0],
            sort_by=params.get("sort", ["potential"])[0],
        )
        self._send(200, html)

    def _read_form(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8")
        return urllib.parse.parse_qs(raw, keep_blank_values=True)

    def _redirect_to(self, tab, **kwargs):
        params = {"tab": tab}
        params.update(kwargs)
        return "/?" + urllib.parse.urlencode(params)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        form = self._read_form()
        version = form.get("version", [""])[0]
        action = form.get("action", [""])[0]
        tab = form.get("tab", ["candidate"])[0]
        filter_rec = form.get("filter_rec", [""])[0]
        filter_tag = form.get("filter_tag", [""])[0]
        sort_by = form.get("sort_by", ["potential"])[0]

        try:
            data = self._load()
            if not self._check_version(data, version):
                html = render_page(data, file_version(self.topics_file), tab=tab,
                                   message="数据已被其他进程修改（可能是 21:00 流水线），请刷新后重试",
                                   msg_type="err", filter_rec=filter_rec,
                                   filter_tag=filter_tag, sort_by=sort_by)
                self._send(409, html)
                return

            if parsed.path == "/bulk":
                ids = form.get("ids", [])
                if not ids:
                    raise ChangeError("未选择任何条目")
                if action == "approve":
                    for tid in ids:
                        apply_status_change(data, tid, "approved")
                elif action == "reject":
                    reason = form.get("bulk_reason", [""])[0]
                    if not reason.strip():
                        raise ChangeError("批量否决必须填写理由")
                    for tid in ids:
                        apply_status_change(data, tid, "rejected", reason=reason)
                else:
                    raise ChangeError(f"未知操作 {action}")

            elif parsed.path == "/single":
                tid = form.get("single_id", [""])[0]
                if not tid:
                    raise ChangeError("缺少条目 id")
                if action == "approve":
                    apply_status_change(data, tid, "approved")
                elif action == "reject":
                    reason = form.get(f"reason_{tid}", [""])[0]
                    apply_status_change(data, tid, "rejected", reason=reason)
                elif action == "block":
                    reason = form.get(f"reason_{tid}", [""])[0] or "人工冻结"
                    apply_status_change(data, tid, "blocked", reason=reason)
                elif action in ("revoke", "revive"):
                    apply_status_change(data, tid, "candidate")
                else:
                    raise ChangeError(f"未知操作 {action}")

            elif parsed.path == "/add":
                tid = apply_add(
                    data,
                    title=form.get("title", [""])[0],
                    event=form.get("event", [""])[0],
                    year=form.get("year", [""])[0],
                    tag=form.get("tag", [""])[0],
                    potential=int(form.get("potential", ["7"])[0]),
                    pitch=form.get("pitch", [""])[0],
                    recommend=form.get("recommend", ["中"])[0],
                )
                tab = "candidate"

            else:
                self._send(404, "Not Found")
                return

            # 校验 + 写入
            errs = validate_all(data)
            if errs:
                raise ChangeError("写入前校验失败：" + "；".join(errs[:5]))
            save_topics(self.topics_file, data)

            # 重定向回列表
            if parsed.path == "/add":
                redirect = self._redirect_to("candidate", msg=f"已投喂 {tid}")
            else:
                redirect = self._redirect_to(tab, rec=filter_rec, tag=filter_tag, sort=sort_by)
            self._send(303, "", redirect=redirect)

        except ChangeError as e:
            data = self._load()
            html = render_page(data, file_version(self.topics_file), tab=tab,
                               message=str(e), msg_type="err",
                               filter_rec=filter_rec, filter_tag=filter_tag, sort_by=sort_by)
            self._send(400, html)
        except Exception as e:
            self._send(500, f"服务器错误：{esc(str(e))}")


def cmd_serve(args):
    ConsoleHandler.topics_file = Path(args.file)
    port = args.port
    server = http.server.HTTPServer(("127.0.0.1", port), ConsoleHandler)
    print(f"选题池控制台已启动：http://127.0.0.1:{port}")
    print(f"数据文件：{ConsoleHandler.topics_file}")
    print("按 Ctrl+C 停止")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        server.server_close()
    return 0


# ---------------------------------------------------------------------------
# 入口
# ---------------------------------------------------------------------------

def main():
    file_parser = argparse.ArgumentParser(add_help=False)
    file_parser.add_argument("--file", default=str(DEFAULT_TOPICS),
                             help="topics.json 路径（默认 topics/topics.json）")

    parser = argparse.ArgumentParser(
        description="选题池控制台：审核 Web UI + 治理 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[file_parser],
    )
    sub = parser.add_subparsers(dest="command")

    # serve
    p_serve = sub.add_parser("serve", help="启动本地 Web 控制台", parents=[file_parser])
    p_serve.add_argument("--port", type=int, default=8787)

    # check
    sub.add_parser("check", help="全量体检", parents=[file_parser])

    # dedup
    sub.add_parser("dedup", help="近重复事件检测", parents=[file_parser])

    # stale
    p_stale = sub.add_parser("stale", help="超期候选冷藏", parents=[file_parser])
    p_stale.add_argument("--apply", action="store_true", help="执行（默认 dry-run）")

    # stats
    sub.add_parser("stats", help="覆盖矩阵（markdown）", parents=[file_parser])

    # next
    sub.add_parser("next", help="dry-run 挑选模拟", parents=[file_parser])

    # approve
    p_app = sub.add_parser("approve", help="批准选题", parents=[file_parser])
    p_app.add_argument("ids", nargs="+")

    # reject
    p_rej = sub.add_parser("reject", help="否决选题", parents=[file_parser])
    p_rej.add_argument("id")
    p_rej.add_argument("--reason", required=True)

    # block
    p_blk = sub.add_parser("block", help="冻结选题", parents=[file_parser])
    p_blk.add_argument("id")
    p_blk.add_argument("--reason", required=True)

    # add
    p_add = sub.add_parser("add", help="投喂新选题", parents=[file_parser])
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--event", required=True)
    p_add.add_argument("--year", required=True)
    p_add.add_argument("--tag", required=True)
    p_add.add_argument("--potential", type=int, required=True)
    p_add.add_argument("--pitch", required=True)
    p_add.add_argument("--recommend", default="中")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return 1

    args.file = Path(args.file)

    commands = {
        "serve": cmd_serve,
        "check": cmd_check,
        "dedup": cmd_dedup,
        "stale": cmd_stale,
        "stats": cmd_stats,
        "next": cmd_next,
        "approve": cmd_approve,
        "reject": cmd_reject,
        "block": cmd_block,
        "add": cmd_add,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
