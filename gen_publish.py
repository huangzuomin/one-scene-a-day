#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_publish.py — 为每晚成片生成视频号「发布包」。

视频号没有公开的内容发布 API，官方通道是人工操作的视频号助手
（channels.weixin.qq.com）。本脚本把能自动化的部分全部自动化：
每晚产出 publish/channels/<日期>/ 自足发布包——

    第NN夜·<题目>.mp4   成片副本
    cover.jpg           封面（末帧 payoff）
    post.txt            可直接粘贴的视频号文案
    README.txt          夜次信息与发布建议

目录已在 .gitignore，不进仓库。已存在的包跳过（幂等）。
用法：python gen_publish.py [--force]
"""

import shutil
import sys
from pathlib import Path

from gen_site import load_films, parse_topic_pool

ROOT = Path(__file__).resolve().parent
PUBLISH = ROOT / "publish" / "channels"

SERIES_LINE = "「一日一幕」：一台 AI 每晚 21:00 自主拍下一部 15 秒历史短片，选题、考据、分镜、生成、自评全程无人值守。"


def build_post(f):
    tags = ["一日一幕", "AI短片", "AI"]
    if f["tag"]:
        tags.append(f["tag"])
    tag_line = " ".join("#" + t for t in tags)
    lines = [f"第 {f['day_no']:02d} 夜 ·《{f['title']}》"]
    if f["logline"]:
        line = f["logline"].strip()
        lines.append(line if line.endswith(("。", "！", "？", "…")) else line + "。")
    lines.append(SERIES_LINE)
    return "\n\n".join(lines[:3]) + "\n\n" + tag_line + "\n"


def build_readme(f):
    from gen_site import CHIP
    status_cn = CHIP.get(f["status"], ("", f["status"]))[1]
    return (
        f"夜次：第 {f['day_no']:02d} 夜（{f['date']}）· {f['tid']} · {status_cn}\n"
        f"评审：均分 {f['avg']}｜{f['ai_sign']}｜{f['human_sign']}\n"
        f"来源：projects/{f['pdir'].name}\n"
        f"\n"
        f"发布建议：视频号流量高峰在早晚通勤时段，可用助手的定时发表约到次日 07:30-08:30。\n"
        f"封面：cover.jpg 为末帧 payoff；如需竖版封面可在助手内裁剪。\n"
    )


def main():
    force = "--force" in sys.argv
    pool, _used = parse_topic_pool()
    films = load_films(pool)
    made = skipped = 0
    for f in films:
        video = f["pdir"] / "video.mp4"
        if not video.exists():
            continue
        pkg = PUBLISH / f["date"]
        if pkg.exists() and not force:
            skipped += 1
            continue
        pkg.mkdir(parents=True, exist_ok=True)
        safe_title = f["title"].replace(":", "：").replace("/", "／")
        shutil.copy2(video, pkg / f"第{f['day_no']:02d}夜·{safe_title}.mp4")
        cover_src = f["pdir"] / "frames" / f'{f["frames"][-1]}.jpg'
        if cover_src.exists():
            shutil.copy2(cover_src, pkg / "cover.jpg")
        (pkg / "post.txt").write_text(build_post(f), encoding="utf-8", newline="\n")
        (pkg / "README.txt").write_text(build_readme(f), encoding="utf-8", newline="\n")
        made += 1
        print(f"打包：{pkg.name} → 第 {f['day_no']:02d} 夜《{f['title']}》")
    print(f"OK：新打包 {made} 夜，已有 {skipped} 夜跳过（--force 重打）→ {PUBLISH}")


if __name__ == "__main__":
    main()
