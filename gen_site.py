#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_site.py — 从 projects/ 数据生成 site/index.html，并同步视频与抽帧资产。

原则：页面由数据驱动。每晚流水线跑完后运行本脚本即可上线，
新夜次不需要改代码；只有编辑性文案（系列宣言、机器步骤、日志摘编等）
以常量形式保存在本文件中。

用法：在仓库根目录执行  python gen_site.py
"""

import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECTS = ROOT / "projects"
SITE = ROOT / "site"
TOPICS_JSON = ROOT / "topics" / "topics.json"

SETTLE_DATE = "2026-09-20"
SEASON_NIGHTS = 30
QUEUE_LEN = 5

# ---------------------------------------------------------------------------
# 编辑性常量（人工/会话维护；其余内容全部来自 projects/ 数据）
# ---------------------------------------------------------------------------

SERIES_STATEMENT = (
    "假设历史上的某个关键时刻，真的留下过一段 15 秒影像，它会是什么样子？"
    "这是一日一幕的第一个系列：不做历史科普，只造一段不存在、"
    "但仿佛真的被摄影机记录下来的画面。第一季 30 夜，全部属于这个系列。"
)

MACHINE_STEPS = [
    ("选题", "只从人工批准的选题池中挑一部，与近七天标签不重复。"),
    ("研究", "核验时代、服饰、建筑与事件，逐条标注史料置信。"),
    ("概念", "一个瞬间、一个动作、一种情绪、一次转折。"),
    ("脚本", "15 秒微故事，禁旁白堆砌，标注声音暗示。"),
    ("分镜", "四拍八字段：景别、角度、焦段、构图、运镜、动作、光线、转场。"),
    ("简报", "织成一段完整的自然语言创作简报，附镜头顺序约束。"),
    ("熔断", "当日生成满两次即停，预算台账落盘。"),
    ("生成", "提交小云雀 Seedance，每 10 秒轮询，超 90 分钟弃取。"),
    ("下载", "成片归档，按每秒一帧抽帧。"),
    ("评审", "亲看分布帧，八维打分，回答 adherence 十问。"),
    ("收尾", "重建审片页，追加运行日志，等待人工评级。"),
]

# 运行日志摘编：夜跑后可在此追加一行摘要，再重新生成页面。
RUNLOG = [
    ("08-22", "首拍验证。密钥过期受阻一次，更新后续跑成功，T001 评 8.4。"),
    ("08-22", "21:00 定时器首次触发：当日已有成片，按「每天一部」规则主动跳过。"),
    ("08-23", "首个全自动夜：T002 从选题到收尾无人值守，评 8.6。当晚人工评级「喜欢」。"),
    ("08-24", "21:00 定时运行中断后自动续跑完成：T003 评 8.6。指定模型 Seedance 2.5 后端暂不可选，自动回退 fast_vision，成片质量无异常。"),
    ("08-24", "人工评级「喜欢」。三夜三片，AI 建议与人工评级全中。"),
    ("08-25", "T005 阿波罗舱门夜评 8.3，人工评级「喜欢 → 精选」。"),
    ("08-26", "T008 庞贝清晨评 8.9 系列最高，视觉质量首次满分。"),
    ("08-26", "人工评级「喜欢」。五夜五片全部精选，AI 建议与人工评级五连中。"),
    ("08-26", "选题池治理上线：AI 提名、人批准、AI 挑拣；存量候选转待审，等首批批审。"),
    ("08-27", "首批人工批审经控制台完成（16 条入可拍池）。当晚 T006 兵马俑点睛评 9.0 系列新高，日常标签首作。"),
    ("08-27", "人工评级「精选」。六夜六片全部精选，AI 建议六连中。"),
    ("08-28", "T030 苏格拉底评 9.2 系列新高，人物一致性首个满分，艺术标签首作。"),
    ("08-28", "人工评级「喜欢」。七夜七片全部精选，AI 建议七连中。"),
    ("08-29", "T004 君士坦丁堡夜：系列首次重拍（圣索菲亚宣礼塔穿帮，负面约束无效，L-009 升级），两版择优 j02 上线评 8.1，AI 建议转「复核」。"),
    ("08-29", "人工评级「精选」——AI 建议复核、人工裁定精选，首例分歧人工为准。八夜八片全部精选。"),
    ("08-30", "2.5 之谜破解：直连通道实测 Seedance_2.5 真实可用（1080p），主链路 agent『暂不可选』系误判，默认通道切换（PIPELINE v1.4）。T031 菩提树晨 9.4 再创新高，思想标签首作。"),
    ("08-30", "人工评级「喜欢」，九夜九片全部精选。用户裁定 2.5/1080p 积分消耗过高，日常回退 2.0/720p（v1.5），直连 2.5 留作特别场合。"),
    ("08-31", "T018 维京入雾 8.4 建议精选，雾墙裂开的『发现』构图为本片灵魂；蛇首船首柱违背约束（L-009 第三实证）。720p 回退确认生效。"),
    ("08-31", "人工评级「喜欢」。十夜十片全部精选。"),
    ("09-01", "T035 金字塔封顶（营造首作）8.8 建议精选。病因确诊：主链路 agent 弹问卷挂起 88 分钟触发熔断（用户 web 端应答续跑）；v1.6 防护句+时长硬约束 L-011 入库。"),
    ("09-01", "人工评级「失败」——系列首个非精选：多镜拆解合成致叙事混乱（L-012），v1.6 预防句追加禁止拆镜拼接。精选率 10/11。"),
    ("09-02", "T025 冰山在前遭平台内容审核两提两拦（泰坦尼克联想，code 12011），当日放弃，选题转 blocked——系列首个 failed 夜。用户裁定放弃该选题。"),
    ("09-03", "T039 卡哈马卡（文明交汇首作，周日 Learning 提名首题兑现）9.0，帘缝三部曲签名帧落地；v1.6 时长硬约束首夜生效（15.04s）。"),
    ("09-03", "人工评级「喜欢」。Learning 提名首题即精选。"),
]

# 学习规则的展示顺序与「为什么」段落（why 也可写在 evaluation.json 的 learned[].why 中，优先取数据）。
LEARNING_ORDER = ["static-turn-anchor", "armor-spec-lock", "model-fallback-chain"]
RULE_WHY = {
    "static-turn-anchor": "敦煌夜的「火苗弯折」、卢比孔夜的「马蹄踏碎倒影」，都发生在动态段，事后抽帧无法确证是否真的发生。",
    "armor-spec-lock": "赤壁夜简报写「布甲外罩皮坎肩」，成片升级为札甲，全片一致但偏离设定。",
    "model-fallback-chain": "指定 Seedance 2.5 不可用时，后端自动回退 fast_vision，成片质量无异常。",
}

# --- 首三夜的遗留对齐（保持与手写首版页面一致；新夜次一律走默认规则） ---

LEGACY_FRAMES = {
    "chibi": ["f01", "f04", "f07", "f11", "f13", "f14"],
    "rubicon": ["f01", "f05", "f09", "f12", "f15"],
    "dunhuang": ["f01", "f04", "f07", "f09", "f12", "f15"],
}
LEGACY_LOGLINE = {
    "chibi": "公元 208 年冬夜，长江。一名东吴水兵在船头察觉风向变了：旗幡猛然转向东南，极远的江面尽头，第一艘火船的火光亮起。",
    "rubicon": "冬夜将尽，凯撒驻马河北岸。跨过这条河就是内战。他沉默，然后策马踏入冰水，马蹄踏碎了自己的倒影。",
    "dunhuang": "深夜，道士王圆箓凿开甬道侧墙的封门墙。封闭千年的气涌吹弯了灯焰，灯光随即照亮从地堆到洞顶的五万卷经书。",
}
LEGACY_VERDICT_NOTE = {
    "chibi": "旗幡被狂风灌满的特写是全片最强画面，转折征兆清晰可读，「寂静中的命运感」达成设计目标。盔甲实际呈札甲，较简报设定精良，但前后一致。",
    "rubicon": "大远景、特写、大远景的钟形镜头曲线完整落地，冰河与火把线的视觉母题贯穿全片，身份锁零漂移。钩子「马蹄踏碎倒影」发生在动态段，静帧未能验证。",
    "dunhuang": "四拍结构全中，人物一致性为系列最佳；末帧经卷墙与尘埃光柱是至今最强的收尾画面。核心转折「火苗弯折」在成片中未能确证，实际以表情骤惊替代。",
}
LEGACY_TAGS = {"T001": "战争", "T002": "政治转折", "T003": "探索发现"}
LEGACY_BADGE = {"rubicon": "首个全自动夜"}
HERO_TITLE_BR = {  # 首屏标题的断行位置；缺省时在逗号处断行
    "T003": ("敦煌藏经洞", "第一次被打开"),
}
HERO_POS = {  # 首屏背景图的构图微调（object-position）；缺省居中
    "T003": "center 62%",
}

SCORE_LABELS = [  # (键候选, 展示名) —— evaluation 新旧 schema 键名兼容
    (("visual_quality",), "视觉质量"),
    (("character_consistency",), "人物一致性"),
    (("era_accuracy", "historical_accuracy"), "时代准确性"),
    (("camera_stability",), "镜头稳定性"),
    (("story_clarity",), "故事可理解性"),
    (("emotional_impact",), "情绪强度"),
    (("creativity",), "创意度"),
    (("publish_potential", "publish_readiness"), "发布潜力"),
]

SHOT_SIZE_CN = [
    ("extreme wide shot", "大远景"), ("wide shot", "远景"), ("full shot", "全景"),
    ("medium shot", "中景"), ("medium close-up", "中近景"), ("close-up", "特写"),
    ("extreme close-up", "大特写"), ("insert", "插入镜头"),
]

CHIP = {  # status.json status → (样式类, 文案)
    "selected": ("chip-selected", "已精选"),
    "evaluated": ("", "待复核"),
    "prompted": ("", "制作中"),
    "rendering": ("", "制作中"),
    "failed": ("chip-failed", "无成片"),
    "skipped": ("", "按规则跳过"),
}


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def space_year(y):
    y = str(y).strip()
    return re.sub(r"^(前|约)", r"\1 ", y)


def space_cjk_digits(t):
    t = re.sub(r"(?<=[\u4e00-\u9fff])(\d)", r" \1", t)
    return re.sub(r"(\d)(?=[\u4e00-\u9fff])", r"\1 ", t)


def read_json(p):
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def slug_of(project_dir):
    """projects/2026-08-24-dunhuang-cave17 → dunhuang"""
    suffix = project_dir.name[11:] if len(project_dir.name) > 11 else project_dir.name
    return suffix.split("-")[0] or suffix


def load_topics():
    """读 topics/topics.json（选题池唯一事实源）：返回 (pool{id:{title,year,tag,potential}}, topics 原始列表)"""
    data = read_json(TOPICS_JSON)
    pool = {}
    for t in data["topics"]:
        pool[t["id"]] = {"title": t.get("title", ""), "year": t.get("year", ""),
                         "tag": t.get("tag", ""), "potential": t.get("potential", 0)}
    return pool, data["topics"]


def parse_facts(research_md):
    """解析 research.md 的 | F1 | 事实 | 置信 | 依据 | 表格"""
    facts = []
    for line in research_md.splitlines():
        if re.match(r"^\|\s*F\d+\s*\|", line):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) >= 3:
                conf = cells[2]
                cls = "conf-a" if conf == "A" else ("conf-b" if conf == "B" else "conf-c")
                facts.append((cells[1].replace("**", ""), conf, cls))
    return facts


def norm_scores(ev):
    scores = ev.get("scores") or ev.get("ai_scores") or {}
    avg = scores.get("average", ev.get("average_score"))
    grid = []
    for keys, label in SCORE_LABELS:
        v = next((scores[k] for k in keys if k in scores), None)
        if v is not None:
            grid.append((v, label))
    return grid, avg


def shot_cn(shot_size):
    """英文景别 → 中文；storyboard 里偶有自由文本（如「over-shoulder medium 收于 interior wide」），匹配不到就返回 None。"""
    low = shot_size.lower()
    for en, cn in SHOT_SIZE_CN:
        if en in low:
            return cn
    return None


def pick_frames(pdir, slug, ev):
    legacy = LEGACY_FRAMES.get(slug)
    if legacy:
        return legacy
    listed = ev.get("frames_reviewed") or ev.get("frames_sampled") or []
    if listed:
        return listed[:6]
    files = sorted(f.stem for f in (pdir / "frames").glob("f*.jpg"))
    n = len(files)
    if n <= 6:
        return files
    idx = sorted({round(i * (n - 1) / 5) for i in range(6)})
    return [files[i] for i in idx]


def ai_sign_text(ev, avg):
    text = " ".join(str(ev.get(k, "")) for k in
                    ("decision_suggestion", "decision", "critic_summary", "verdict"))
    for word in ("建议精选", "建议重拍", "建议跳过", "建议复核"):
        if word in text:
            return f"AI 评审：{word}"
    if avg is not None and avg >= 8:
        return "AI 评审：建议精选"
    return "AI 评审：待定"


def human_parts(ev):
    hr = ev.get("human_rating")
    if isinstance(hr, dict):
        rating, result = hr.get("rating", ""), hr.get("result", "")
    else:
        rating = hr or ev.get("human_comment") or ""
        result = ev.get("human_decision", "")
    if not rating and not result:
        return "待人工评级"
    verdict_word = "精选" if result == "selected" else "不精选"
    return f"人说：「{rating}」→ {verdict_word}"


def load_films(pool):
    films = []
    for pdir in sorted(PROJECTS.iterdir()):
        if not (pdir / "status.json").exists():
            continue
        if not (pdir / "video.mp4").exists():
            continue  # 无成片夜（failed/skipped）不进入影片列表，仅计季况统计（手册 Step 12）
        st = read_json(pdir / "status.json")
        con = read_json(pdir / "concept.json")
        sb = read_json(pdir / "storyboard.json")
        ev_raw = (pdir / "evaluation.json")
        ev = read_json(ev_raw) if ev_raw.exists() else {}
        prompt = (pdir / "prompt.txt").read_text(encoding="utf-8").strip()
        research = (pdir / "research.md")
        facts = parse_facts(research.read_text(encoding="utf-8")) if research.exists() else []

        slug = slug_of(pdir)
        topic = con.get("topic", {})
        tid = st.get("topic_id") or topic.get("id", "")
        title = space_cjk_digits(topic.get("title", ev.get("title", "")))
        grid, avg = norm_scores(ev)

        meta_bits = [f"第 {st['day_no']:02d} 夜", st["date"]]
        tag = topic.get("tag") or LEGACY_TAGS.get(tid) or pool.get(tid, {}).get("tag")
        if tag:
            meta_bits.append(tag)
        if topic.get("year"):
            meta_bits.append(space_year(topic["year"]))
        badge = LEGACY_BADGE.get(slug, "")
        if badge:
            meta_bits.append(badge)

        note = LEGACY_VERDICT_NOTE.get(slug)
        if not note:
            note = ev.get("critic_summary") or ""
            if not note and len(ev.get("verdict", "")) > 20:
                note = ev["verdict"]

        logline = LEGACY_LOGLINE.get(slug) or con.get("moment", "")

        beats = []
        for b in sb.get("beats", []):
            beats.append((b.get("time", ""), shot_cn(b.get("shot_size", "")), b.get("action", "").rstrip("。")))
        learned = ev.get("learned") or []

        films.append({
            "slug": slug, "day_no": st["day_no"], "date": st["date"],
            "status": st.get("status", ""), "tid": tid,
            "title": title,
            "logline": logline, "meta_bits": meta_bits,
            "tag": tag or "", "year": topic.get("year", ""), "event": topic.get("event", ""),
            "grid": grid, "avg": avg, "note": note,
            "ai_sign": ai_sign_text(ev, avg), "human_sign": human_parts(ev),
            "frames": pick_frames(pdir, slug, ev),
            "facts": facts,
            "confidence_note": con.get("confidence_note", ""),
            "beats": beats, "prompt": prompt, "learned": learned,
            "pdir": pdir,
        })
    films.sort(key=lambda f: -f["day_no"])
    return films


def chip_html(status):
    cls, word = CHIP.get(status, ("", status))
    cls_attr = f' class="chip {cls}"' if cls else ' class="chip"'
    return f'<span{cls_attr}>{word}</span>'


def hero_title_html(title, tid):
    br = HERO_TITLE_BR.get(tid)
    if br:
        return esc(br[0]) + "<br>" + esc(br[1])
    if "，" in title:
        a, b = title.split("，", 1)
        return esc(a) + "，<br>" + esc(b)
    return esc(title)


def merge_learning(films):
    """合并各夜 learned[]，按 LEARNING_ORDER 排序，来源去重并共享后缀。"""
    rules = {}
    for film in sorted(films, key=lambda f: f["day_no"]):  # 旧→新，先到先得
        for item in film["learned"]:
            rid = item.get("id")
            if not rid:
                continue
            r = rules.setdefault(rid, {"id": rid, "title": item.get("title", ""),
                                       "rule": item.get("rule", ""),
                                       "why": item.get("why", ""),
                                       "sources": [], "days": []})
            if item.get("source") and item["source"] not in r["sources"]:
                r["sources"].append(item["source"])
            if film["day_no"] not in r["days"]:
                r["days"].append(film["day_no"])
    ordered = ([rules[i] for i in LEARNING_ORDER if i in rules]
               + [r for i, r in rules.items() if i not in LEARNING_ORDER])

    out = []
    for n, r in enumerate(ordered, 1):
        srcs = sorted(set(r["sources"]), key=lambda s: re.search(r"\d+", s).group() if re.search(r"\d+", s) else s)
        joined = "、".join(srcs)
        why = r["why"] or RULE_WHY.get(r["id"], "")
        out.append({"no": f"{n:02d}", "title": r["title"], "rule": r["rule"],
                    "why": why, "src": f"来源 · {joined}" if joined else ""})
    return out


def content_version(p):
    """文件内容的短哈希，用作资源 URL 版本号：内容一变 URL 即变，穿透浏览器与 CDN 缓存。"""
    return hashlib.md5(p.read_bytes()).hexdigest()[:8] if p.exists() else ""


def render(films, pool, topics, learning, hero_v, css_v):
    latest = films[0]
    hero_pos = HERO_POS.get(latest["tid"], "center")
    done = len(films)
    selected = sum(1 for f in films if f["status"] == "selected")

    # ---- 统计 ----
    avgs = [f["avg"] for f in films if f["avg"] is not None]
    avg_all = f"{sum(avgs) / len(avgs):.1f}" if avgs else "—"
    agree_n = agree_hit = 0
    for f in films:
        if "待人工评级" in f["human_sign"]:
            continue
        h_sel = "→ 精选" in f["human_sign"]
        ai_sel = "精选" in f["ai_sign"]
        agree_n += 1
        agree_hit += int(h_sel == ai_sel)
    agreement = f"{round(100 * agree_hit / agree_n)}%" if agree_n else "—"

    # ---- 选题池：approved 可拍队列 / candidate 待审 / 冻结与否决 / 标签战绩 ----
    of_status = lambda s: [t for t in topics if t.get("status") == s]
    approved = sorted(of_status("approved"), key=lambda t: -t.get("potential", 0))
    rec_rank = {"高": 0, "中": 1, "低": 2}
    candidates = sorted(of_status("candidate"),
                        key=lambda t: (rec_rank.get(t.get("recommend", "中"), 1), -t.get("potential", 0)))
    frozen = of_status("blocked") + of_status("rejected")

    n_appr, n_cand = len(approved), len(candidates)
    if n_appr == 0:
        pool_state, pool_extra = "empty", " · 池空：今晚按规则跳过，等待人工批准"
    elif n_appr < 3:
        pool_state, pool_extra = "warn", " · 弹药不足三条，请尽快审批"
    else:
        pool_state, pool_extra = "ok", ""

    # 机器区侧栏「待拍清单」：approved 前几条；过渡期为空时给出指引
    side_items = approved[:QUEUE_LEN]
    if side_items:
        queue_html = "\n".join(
            f'        <li><span>{esc(space_cjk_digits(t["title"]))}</span>'
            f'<span class="queue-meta">{esc(space_year(t["year"]))} · {esc(t["tag"])}</span></li>'
            for t in side_items)
    else:
        queue_html = (f'        <li><span>可拍队列为空，待首次人工审批</span>'
                      f'<span class="queue-meta">待审 {n_cand} 条</span></li>')

    appr_html = "\n".join(
        f'        <li><span class="q-no">{i:02d}</span>'
        f'<span class="q-title">{esc(space_cjk_digits(t["title"]))}</span>'
        f'<span class="queue-meta">{esc(space_year(t["year"]))} · {esc(t["tag"])} · 潜力 {t["potential"]}</span></li>'
        for i, t in enumerate(approved, 1)) or '        <li class="pool-none">（空）首批人工批准后进入</li>'

    tag_stats = {}
    for f in films:
        if not f["tag"]:
            continue
        s = tag_stats.setdefault(f["tag"], {"n": 0, "sum": 0.0, "cnt": 0, "sel": 0})
        s["n"] += 1
        if f["avg"] is not None:
            s["sum"] += f["avg"]
            s["cnt"] += 1
        if f["status"] == "selected":
            s["sel"] += 1
    tag_rows_html = "\n".join(
        f'          <tr><td>{esc(tag)}</td><td>{s["n"]}</td>'
        f'<td>{s["sum"] / s["cnt"]:.1f}</td><td>{s["sel"]} / {s["n"]}</td></tr>'
        for tag, s in sorted(tag_stats.items(), key=lambda kv: -kv[1]["n"]))

    REC_CLS = {"高": "rec-high", "中": "rec-mid", "低": "rec-low"}
    REC_WORD = {"高": "优先", "中": "备选", "低": "存疑"}
    cand_html = "\n".join(
        f'''        <li class="cand">
          <p class="cand-title"><b>{esc(t["id"])}</b>{esc(space_cjk_digits(t["title"]))}<span class="badge-rec {REC_CLS.get(t.get("recommend", "中"), "rec-mid")}">{REC_WORD.get(t.get("recommend", "中"), "备选")}</span></p>
          <p class="cand-pitch">{esc(t.get("pitch", ""))}<span class="cand-meta">{esc(space_year(t["year"]))} · {esc(t["tag"])} · 潜力 {t["potential"]}</span></p>
        </li>'''
        for t in candidates) or '        <li class="pool-none">（暂无待审提名）</li>'

    frozen_html = "\n".join(
        f'        <li><span><b>{esc(t["id"])}</b>{esc(t["title"])}</span>'
        f'<span class="queue-meta">{esc(t.get("reason", ""))}</span></li>'
        for t in frozen) or '        <li class="pool-none">（暂无）</li>'

    hero_day_no = latest["day_no"]
    hero_chip = chip_html(latest["status"])

    films_html = []
    for f in films:
        strip = "".join(
            f'<img src="assets/films/{f["slug"]}/{fr}.jpg" alt="">'
            for fr in f["frames"])
        poster = f["frames"][-1]
        meta = " · ".join(esc(b) for b in f["meta_bits"]) + " · " + chip_html(f["status"])
        scores = "".join(
            f'<span class="score"><b>{v}</b>{esc(label)}</span>' for v, label in f["grid"])
        facts = "".join(
            f'\n            <tr><td>{esc(fact)}</td><td class="{cls}">{esc(conf)}</td></tr>'
            for fact, conf, cls in f["facts"])
        note_html = f'\n        <p class="archive-note">置信分级：A 史料确认 / B 合理推断 / C 艺术创作。{esc(f["confidence_note"])}</p>' if f["confidence_note"] else ""
        beats = "".join(
            f'\n            <li><span class="beat-time">{esc(t)}</span>{esc(cn + "：" if cn else "")}{esc(a)}。</li>'
            for t, cn, a in f["beats"])
        films_html.append(f'''  <article class="film" id="film-{f["slug"]}">
    <div class="film-strip" aria-hidden="true">
      {strip}
    </div>
    <header class="film-head">
      <p class="film-meta">{meta}</p>
      <h2 class="film-title">{esc(f["title"])}</h2>
      <p class="film-logline">{esc(f["logline"])}</p>
    </header>
    <video controls preload="metadata" poster="assets/films/{f["slug"]}/{poster}.jpg" src="assets/films/{f["slug"]}/video.mp4"></video>
    <div class="film-verdict">
      <div class="score-grid">
        {scores}
      </div>
      <div class="verdict-block">
        <p class="verdict-avg">{f["avg"]}</p>
        <p class="verdict-note">{esc(f["note"])}</p>
        <p class="verdict-sign"><span class="sign-ai">{esc(f["ai_sign"])}</span><span class="sign-human">{esc(f["human_sign"])}</span></p>
      </div>
    </div>
    <details class="film-archive">
      <summary>创作档案：研究、分镜与提交简报</summary>
      <div class="archive-grid">
        <section class="archive-block">
          <h3>研究事实与置信分级</h3>
          <table>{facts}
          </table>{note_html}
        </section>
        <section class="archive-block">
          <h3>分镜四拍</h3>
          <ol class="beat-list">{beats}
          </ol>
        </section>
      </div>
      <details class="prompt-fold">
        <summary>提交给模型的创作简报原文</summary>
        <pre class="prompt-text">{esc(f["prompt"])}</pre>
      </details>
    </details>
  </article>''')
    films_joined = "\n\n".join(films_html)

    rules_html = []
    for r in learning:
        why = f'\n        <p class="rule-why">{esc(r["why"])}</p>' if r["why"] else ""
        rules_html.append(f'''      <li class="rule">
        <p class="rule-no">规则候选 {r["no"]}</p>
        <h3 class="rule-title">{esc(r["title"])}</h3>{why}
        <p class="rule-candidate">规则候选：{esc(r["rule"])}。</p>
        <p class="rule-src">{esc(r["src"])}</p>
      </li>''')
    rules_joined = "\n".join(rules_html)

    runlog_html = "\n".join(
        f'        <li><span class="log-time">{t}</span>{esc(msg)}</li>' for t, msg in RUNLOG)

    steps_html = "\n".join(
        f'        <li><span class="step-no">{i:02d}</span><div><b>{name}</b>{desc}</div></li>'
        for i, (name, desc) in enumerate(MACHINE_STEPS, 1))

    stat_label = "夜完成 · 全部精选" if selected == done else f"夜完成 · 精选 {selected}"

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>一日一幕 · AI 每日短片实验室</title>
<meta name="description" content="一日一幕：每晚 21:00，一台 AI 自主拍下一部 15 秒短片。第一季 30 夜，全程留档，无人值守。">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%230e0d0b'/%3E%3Crect x='6' y='5' width='20' height='22' fill='none' stroke='%23c98a3d' stroke-width='2'/%3E%3Ccircle cx='16' cy='16' r='4.5' fill='%23c98a3d'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;900&family=JetBrains+Mono:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="css/style.css?v={css_v}">
</head>
<body>

<header class="nav">
  <a class="nav-brand" href="#top">
    <span class="brand-word">一日一幕</span>
    <span class="brand-sub">AI 每日短片实验室</span>
  </a>
  <nav class="nav-links">
    <a href="#films">影片</a>
    <a href="#machine">机器</a>
    <a href="#topics">选题池</a>
    <a href="#learning">学习</a>
    <a href="#about">关于</a>
  </nav>
</header>

<!-- ============ 第一幕 · 首屏 ============ -->
<section class="hero" id="top">
  <img class="hero-bg" src="assets/hero.jpg?v={hero_v}" alt="《{esc(latest["title"])}》末帧画面" style="object-position:{hero_pos}">
  <div class="hero-scrim"></div>
  <div class="hero-content">
    <p class="hero-eyebrow">SERIES 01 · 如果历史有镜头 · 第一季 30 夜</p>
    <p class="hero-day">第 {hero_day_no:02d} 夜 · {latest["date"]} {hero_chip}</p>
    <h1 class="hero-title">{hero_title_html(latest["title"], latest["tid"])}</h1>
    <p class="hero-sub">{esc(latest["logline"])}</p>
    <p class="hero-def">一日一幕：每晚 21:00，一台 AI 自主拍下一部 15 秒短片。第一季 30 夜，全程留档，无人值守。</p>
    <div class="hero-cta">
      <a class="btn btn-solid" href="#film-{latest["slug"]}">播放这一夜</a>
      <a class="btn btn-ghost" href="#machine">这台机器如何运转</a>
    </div>
  </div>
  <p class="hero-caption">首帧画面：《{esc(latest["title"])}》第 15 秒</p>
</section>

<main>

<!-- 季况条 -->
<div class="season-strip">
  <div class="season-inner">
    <p class="season-progress"><b>第一季 · 30 夜</b><span>第 {hero_day_no:02d} 夜已完成</span><span>精选 {selected} / {done}</span></p>
    <p class="season-next">下一次运行 今晚 21:00<span class="sep"> · </span>第 30 夜公开结算 <b>{SETTLE_DATE}</b></p>
  </div>
</div>

<!-- ============ 系列 · 影片 ============ -->
<section class="films" id="films">

  <header class="series-head">
    <p class="kicker">SERIES 01</p>
    <h2 class="section-title">如果历史有镜头</h2>
    <p class="series-statement">{SERIES_STATEMENT}</p>
  </header>

{films_joined}

</section>

<!-- ============ 第三幕 · 机器 ============ -->
<section class="machine" id="machine">
  <div class="machine-cols">
    <div class="pipeline">
      <h2 class="section-title">一台机器的十一步</h2>
      <p class="section-sub">每个深夜 21:00，一个 AI 会话醒来，读自己的操作手册和创作守则，然后走完这条流水线。生成环节之外，没有任何人碰过鼠标。</p>
      <ol class="pipeline-list">
{steps_html}
      </ol>
      <p class="runtime-note">这条流水线是通用的 Runtime。换一个系列，换的只是第 02 步的「研究」规则：历史系列核验史料，古籍系列理解文本，科幻系列构建世界观。系列 Playbook 可插拔，机器不变。</p>
      <p class="pipeline-loop">每晚 21:00 自动运行，周日上午追加学习周报</p>
    </div>
    <div class="machine-side">
      <h3 class="side-title">运行日志</h3>
      <ul class="runlog">
{runlog_html}
      </ul>
      <h3 class="side-title">待拍清单</h3>
      <ul class="queue">
{queue_html}
      </ul>
    </div>
  </div>
</section>

<!-- ============ 选题池 ============ -->
<section class="pool" id="topics">
  <div class="pool-inner">
    <p class="kicker">TOPIC POOL</p>
    <h2 class="section-title">选题池</h2>
    <p class="section-sub">AI 提名，人批准，AI 挑拣。每条片子开拍前，选题必须先经人工批准进入可拍队列；周日的学习会依据标签战绩补充新提名、清理过期候选。</p>
    <p class="pool-status pool-{pool_state}">库存：可拍 {n_appr} 夜 · 待审 {n_cand} 条{pool_extra}</p>
    <div class="pool-cols">
      <div class="pool-col">
        <h3 class="side-title">可拍队列（已批准）</h3>
        <ol class="pool-queue">
{appr_html}
        </ol>
        <h3 class="side-title pool-gap">标签战绩</h3>
        <table class="tag-stats">
          <tr><th>标签</th><th>已拍</th><th>均分</th><th>精选</th></tr>
{tag_rows_html}
        </table>
      </div>
      <div class="pool-col">
        <h3 class="side-title">待审提名（{n_cand} 条）</h3>
        <ul class="cand-list">
{cand_html}
        </ul>
        <details class="frozen-fold">
          <summary>冻结与否决（{len(frozen)}）</summary>
          <ul class="pool-frozen">
{frozen_html}
          </ul>
        </details>
      </div>
    </div>
  </div>
</section>

<!-- ============ 学习 ============ -->
<section class="learning" id="learning">
  <div class="learning-inner">
    <p class="kicker">LEARNING</p>
    <h2 class="section-title">它学到过什么</h2>
    <p class="section-sub">每夜复盘留下的教训，先记为「规则候选」。第 30 夜结算时，只有带样本证据的条目才会写进创作守则。</p>
    <ol class="rule-list">
{rules_joined}
    </ol>
    <div class="settlement">
      <p class="settle-title">第 30 夜 · {SETTLE_DATE} · 公开结算</p>
      <p class="settle-thresholds">运行稳定性 ≥ 90% · 有效成片率 ≥ 70% · 精选率 ≥ 30% · 创作规则 ≥ 10 条</p>
      <p class="settle-now">当前进度：第 {hero_day_no:02d} 夜，精选 {selected} / {done}。样本太小，不作解读。</p>
    </div>
  </div>
</section>

<!-- ============ 第四幕 · 关于 ============ -->
<section class="about" id="about">
  <div class="about-intro">
    <h2 class="section-title">一个无人值守的创作实验</h2>
    <div class="about-def">
      <p>一日一幕是一场公开运行的创作实验：一台 AI 每晚 21:00 醒来，读自己的操作手册与创作守则，完成选题、考据、分镜、生成、自评，全程无人值守。第一季 30 夜，只拍一个系列，第 30 夜公开结算。</p>
      <p>它每晚都拍，但不代表每晚都值得看。精选是人的判断；全部夜次，包括失败和跳过，都留档在案，可在各夜创作档案中查证。</p>
    </div>
    <p class="about-lead">这个实验室想回答一个问题：把创作守则、操作手册和真实的历史题材交给一台 AI，它能否夜复一夜地产出值得看的东西？系统没有界面，没有数据库，全部「源代码」就是两份 markdown 文档；一个 AI 会话读着它们醒来、创作、自我评审、落盘归档，然后在第二天晚上再次醒来。</p>
  </div>

  <div class="method">
    <section class="method-block method-rhythm">
      <h3>十五秒的骨架</h3>
      <p>每条片子按同一条时间轴分配功能，转折必须落在第十一秒附近。</p>
      <div class="rhythm-bar" role="img" aria-label="时间轴：0至2秒钩子，2至6秒展开，6至11秒升级，11至14秒转折，14至15秒收束">
        <span style="width:13.3%">钩子<br>0-2s</span><span style="width:26.7%">展开<br>2-6s</span><span style="width:33.3%">升级<br>6-11s</span><span class="rb-turn" style="width:20%">转折<br>11-14s</span><span style="width:6.7%">收束<br>14-15s</span>
      </div>
    </section>
    <section class="method-block method-flow">
      <h3>七格揭示流</h3>
      <p>历史转折的默认分镜图，实际拍摄时压缩为四到六格。</p>
      <ol class="flow-grid">
        <li>空间孤立</li><li>信号出现</li><li>察觉</li><li>含义揭示</li><li>内在一闪</li><li>定格 payoff</li><li>余韵</li>
      </ol>
    </section>
    <section class="method-block method-qa">
      <h3>生成后的十问</h3>
      <p>每夜成片由 AI 亲自看帧复盘，十问之三：</p>
      <ul>
        <li>主角身份、服装、剪影是否稳定？</li>
        <li>终帧是否落在设计的 payoff？</li>
        <li>画面有没有文字、边框、水印污染？</li>
      </ul>
    </section>
  </div>

  <div class="stats">
    <div class="stat"><b>{done} / {SEASON_NIGHTS}</b><span>{stat_label}</span></div>
    <div class="stat"><b>{agreement}</b><span>AI 建议与人工评级一致</span></div>
    <div class="stat"><b>{avg_all}</b><span>平均评审分</span></div>
    <div class="stat"><b>0</b><span>生成环节人工干预</span></div>
  </div>

  <div class="colophon">
    <p>创作由 ZCode 会话承担，读 <code>PIPELINE.md</code> 与 <code>PLAYBOOK.md</code> 运行；视频由小云雀 Seedance 生成；本站为纯静态 HTML 与 CSS，无框架。</p>
    <p class="disclaimer">所有影片基于真实历史背景的艺术化想象。关键视觉元素经史料置信分级核验，人物细节属创作自由，完整依据见各片创作档案。</p>
  </div>
</section>

</main>

<footer class="site-footer">
  <span>一日一幕 · AI 每日短片实验室</span>
  <span class="footer-dim">第一季 · 第 30 夜公开结算 {SETTLE_DATE}</span>
</footer>

</body>
</html>
'''


def sync_assets(films):
    latest = films[0]
    for f in films:
        dest = SITE / "assets" / "films" / f["slug"]
        dest.mkdir(parents=True, exist_ok=True)
        video = f["pdir"] / "video.mp4"
        if video.exists():
            shutil.copy2(video, dest / "video.mp4")
        for fr in f["frames"]:
            src = f["pdir"] / "frames" / f"{fr}.jpg"
            if src.exists():
                shutil.copy2(src, dest / f"{fr}.jpg")
        poster_src = f["pdir"] / "frames" / f'{f["frames"][-1]}.jpg'
        if f["pdir"] is latest["pdir"] and poster_src.exists():
            shutil.copy2(poster_src, SITE / "assets" / "hero.jpg")


def main():
    pool, topics = load_topics()
    films = load_films(pool)
    if not films:
        raise SystemExit("projects/ 下没有找到任何项目")
    learning = merge_learning(films)
    sync_assets(films)  # 先同步资产，版本号取自同步后的文件内容
    hero_v = content_version(SITE / "assets" / "hero.jpg")
    css_v = content_version(SITE / "css" / "style.css")
    html = render(films, pool, topics, learning, hero_v, css_v)
    (SITE / "index.html").write_text(html, encoding="utf-8", newline="\n")
    print(f"OK: site/index.html 已生成（{len(films)} 个夜次，最新 第 {films[0]['day_no']:02d} 夜 · hero?v={hero_v}）")


if __name__ == "__main__":
    main()
