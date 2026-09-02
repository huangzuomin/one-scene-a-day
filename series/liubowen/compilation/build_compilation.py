# -*- coding: utf-8 -*-
"""刘伯温六集合集剪辑：片头字卡(3s) + 六集正片(90s) + 片尾字卡(5s)，全片统一雨夜环境声底。"""
import subprocess, os, sys

ROOT = r"D:\Work\AI 每日短片实验室\series\liubowen"
TMP = os.path.join(ROOT, "compilation", "tmp")
OUT = os.path.join(ROOT, "compilation")
DUR = "15.041787"  # 每集时长
FPS = "24"
FONT_MAIN = r"fontfile='C\:/Windows/Fonts/Dengb.ttf'"
FONT_BODY = r"fontfile='C\:/Windows/Fonts/msyh.ttc'"

def run(args):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("FAIL:", " ".join(args[:6]), "...")
        print(r.stderr[-1800:])
        sys.exit(1)

def enc_args():
    return ["-c:v", "libx264", "-crf", "18", "-preset", "medium", "-r", FPS,
            "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2"]

# 1) 雨夜环境声底：取 EP6 音轨
bed = os.path.join(TMP, "bed.wav")
run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(ROOT, "ep06", "video.mp4"),
     "-vn", "-ac", "2", "-ar", "44100", bed])

# 2) 片头字卡 3s
vf_body = ("drawtext=" + FONT_MAIN + ":text='刘伯温 · 六个决定性瞬间':fontcolor=white:fontsize=58:x=(w-text_w)/2:y=300,"
           + "drawtext=" + FONT_BODY + ":text='公元 1358 — 1375':fontcolor=0xB8B8B8:fontsize=28:x=(w-text_w)/2:y=392,"
           + "fade=t=in:st=0:d=0.5")
run(["ffmpeg", "-y", "-loglevel", "error",
     "-f", "lavfi", "-i", "color=black:s=1280x720:d=3:r=" + FPS,
     "-stream_loop", "30", "-i", bed,
     "-filter_complex", "[0:v]" + vf_body + "[v];[1:a]volume=1.4,afade=t=in:st=0:d=0.4,atrim=0:3[a]",
     "-map", "[v]", "-map", "[a]"] + enc_args() + ["-t", "3", os.path.join(TMP, "card_title.mp4")])

# 3) 六集正片：EP1-4 铺声底，EP5-6 保留原声
for i in range(1, 7):
    src = os.path.join(ROOT, f"ep{i:02d}", "video.mp4")
    dst = os.path.join(TMP, f"ep{i:02d}.mp4")
    if i <= 4:
        run(["ffmpeg", "-y", "-loglevel", "error",
             "-i", src, "-stream_loop", "30", "-i", bed,
             "-filter_complex", "[1:a]volume=1.4,atrim=0:" + DUR + "[a]",
             "-map", "0:v", "-map", "[a]"] + enc_args() + ["-t", DUR, dst])
    else:
        run(["ffmpeg", "-y", "-loglevel", "error",
             "-i", src,
             "-filter_complex", "[0:a]aresample=44100,atrim=0:" + DUR + ",apad[a]",
             "-map", "0:v", "-map", "[a]"] + enc_args() + ["-t", DUR, dst])
    print(f"ep{i:02d} done")

# 4) 片尾字卡 5s（末尾 1.2s 淡出至黑）
end_lines = [
    ("drawtext=" + FONT_MAIN + ":text='「亟上之，毋令后人习也。」':fontcolor=white:fontsize=44:x=(w-text_w)/2:y=262"),
    ("drawtext=" + FONT_BODY + ":text='——《明史 · 刘基传》':fontcolor=0xB8B8B8:fontsize=26:x=(w-text_w)/2:y=330"),
    ("drawtext=" + FONT_BODY + ":text='他为朱元璋算定了天下开局，留给自己的最后一个决定，是松手。':fontcolor=0x9A9A9A:fontsize=23:x=(w-text_w)/2:y=436"),
]
vf_end = "color=black:s=1280x720:d=5:r=" + FPS + "," + ",".join(end_lines) + ",fade=t=out:st=3.8:d=1.2"
run(["ffmpeg", "-y", "-loglevel", "error",
     "-f", "lavfi", "-i", "color=black:s=1280x720:d=5:r=" + FPS,
     "-stream_loop", "30", "-i", bed,
     "-filter_complex", "[0:v]" + ",".join(vf_end.split(",")[1:]) + "[v];[1:a]volume=1.4,afade=t=out:st=3.5:d=1.5,atrim=0:5[a]",
     "-map", "[v]", "-map", "[a]"] + enc_args() + ["-t", "5", os.path.join(TMP, "card_end.mp4")])

# 5) 拼接（参数已归一，流复制）
lst = os.path.join(TMP, "list.txt")
with open(lst, "w", encoding="utf-8") as f:
    for name in ["card_title.mp4"] + [f"ep{i:02d}.mp4" for i in range(1, 7)] + ["card_end.mp4"]:
        f.write("file '" + name + "'\n")
final = os.path.join(OUT, "刘伯温六个决定性瞬间_合集.mp4")
run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", final])

probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration,size", "-of", "csv=p=0", final],
                       capture_output=True, text=True)
print("FINAL:", final)
print("duration,size =", probe.stdout.strip())
