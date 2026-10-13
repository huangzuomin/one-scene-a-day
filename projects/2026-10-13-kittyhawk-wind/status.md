# 状态 · 2026-10-13 第27夜《杀魔丘上的风：飞行前的一分钟》(T028)

- **状态**: prompted → generating（已提交，轮询中）
- **选题**: T028 杀魔丘上的风：飞行前的一分钟（科技标签；七日窗实测：10-06~10-12 仅战争占用，战争锁至 10-19；科技 32 天未用）
- **模板**: B·动作五拍（R-104a；三部验证之第二部，混合型=静止蓄力→离地爆发）
- **通道**: 主链路 seedance2.0_fast_vision（720p/15s，基线夜 90 分）；质量夜触发（rec 高+potential 8）但直连 2.5 仍阻塞→回退，配额不消耗（0/6）
- **提交**: 2026-10-13 21:03（thread skill_c334d103… / run skill_69c0a3a1…）
- **备注**: submit_once.py 首次实战暴露两处本地 bug（REPO_ROOT 少一层 dirname 致密钥路径错→FileNotFoundError；--max-time 传整型 90→TypeError），均在发包前失败、服务端无建单；修复后一次提交成功。tools/xyq 不入库，本地已修。

## 历史
- 21:00 idea：选题 T028，七日窗实测通过；质量夜判定→回退基线
- 21:00 researched：research.md（首飞史实 A 级全，视觉元素 B+，L-009 回避清单）
- 21:00 scripted：concept.json + script.md + storyboard.json + prompt.txt
- 21:01 submit_incident：submit_once 两处 bug 定位与修复（未发包）
- 21:03 prompted → generating：正式提交成功
