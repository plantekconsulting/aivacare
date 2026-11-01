"""Builds the walkthrough video from slides, recorded clips and narration. Run: python assemble.py"""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path("C:/dev/video")
OUT = ROOT / "out"
W, H, FPS = 1920, 1080, 30
TAIL = 0.7          # silence after each narration
LEAD = 0.2          # silence before each narration
FAST_MIN = 1.6      # shortest a sped-up wait may become (seconds)
FONT = "C\\:/Windows/Fonts/segoeui.ttf"
FONT_B = "C\\:/Windows/Fonts/segoeuib.ttf"

SLIDES = {"01-title": "s01", "02-problem": "s02", "03-built": "s03", "04-hood": "s04", "15-close": "s15"}
PARTS = {  # scene -> [(clip id, phone layout?)]
    "05-home": [("05-home", False)],
    "06-assistant": [("06-assistant", False)],
    "07-upload": [("07-upload", False)],
    "08-alert": [("08-alert", False)],
    "09-coordinator": [("09-coordinator", False)],
    "10-physician": [("10-physician", False)],
    "11-approve": [("11-approve", False)],
    "12-followup": [("12-followup", True)],
    "13-redflag": [("13-redflag", True), ("13b-redflag-queue", False)],
    "14-governance": [("14-governance", False)],
}
LABELS = {  # small persona label shown top-left on recorded scenes
    "05-home": "Patient - John Miller (web portal)", "06-assistant": "Patient - John Miller (web portal)",
    "07-upload": "Patient - John Miller (web portal)", "08-alert": "Hepatologist - Dr. Anika Patel",
    "09-coordinator": "Care coordinator - Sam Lee, RN", "10-physician": "Hepatologist - Dr. Anika Patel",
    "11-approve": "Hepatologist - Dr. Anika Patel", "12-followup": "Patient - John Miller (phone)",
    "13-redflag": "Patient - John Miller (phone) → care team", "14-governance": "Hepatologist - Dr. Anika Patel",
}


def run(args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def esc(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\u2019").replace(",", "\\,")


def label_filter(text: str) -> str:
    return (f"drawtext=fontfile='{FONT_B}':text='{esc(text)}':x=28:y=H-th-28:fontsize=26:fontcolor=white:"
            f"box=1:boxcolor=0x0f766e@0.88:boxborderw=12")


def audio_args(scene: str, length: float):
    wav = ROOT / "audio" / f"{scene}.wav"
    ms = int(LEAD * 1000)
    return ["-i", str(wav)], f"adelay={ms}|{ms},apad,atrim=0:{length:.3f},aformat=sample_rates=48000:channel_layouts=stereo"


def render_slide(scene: str, length: float, out: Path):
    png = ROOT / "slides" / f"{SLIDES[scene]}.png"
    a_in, a_f = audio_args(scene, length)
    run(["ffmpeg", "-y", "-loop", "1", "-framerate", str(FPS), "-i", str(png), *a_in,
         "-filter_complex", f"[0:v]scale={W}:{H},format=yuv420p,trim=0:{length:.3f}[v];[1:a]{a_f}[a]",
         "-map", "[v]", "-map", "[a]", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-c:a", "aac", "-b:a", "160k", "-t", f"{length:.3f}", str(out)])


def render_browser(scene: str, length: float, out: Path):
    parts = PARTS[scene]
    pieces = []  # (input index, a, b, is_fast)
    for i, (clip, _) in enumerate(parts):
        m = json.loads((ROOT / "clips" / f"{clip}.json").read_text())
        t = m["start"]
        for a, b in m["fast"]:
            if a > t:
                pieces.append((i, t, a, False))
            pieces.append((i, a, b, True))
            t = b
        pieces.append((i, t, m["end"], False))

    normal = sum(b - a for _, a, b, f in pieces if not f)
    fast_real = [b - a for _, a, b, f in pieces if f]
    if normal + FAST_MIN * len(fast_real) >= length:
        fast_alloc = [min(FAST_MIN, r) for r in fast_real]
        g = (normal + sum(fast_alloc)) / length          # global speed-up to fit
    else:
        extra = length - normal
        total_fast = sum(fast_real) or 1
        fast_alloc = [min(r, max(FAST_MIN, extra * r / total_fast)) for r in fast_real]
        g = 1.0
    produced = (normal + sum(fast_alloc)) / g
    pad = max(0.0, length - produced)

    inputs, chains, labels = [], [], []
    for i, (clip, phone) in enumerate(parts):
        inputs += ["-i", str(ROOT / "clips" / f"{clip}.webm")]
        n = sum(1 for p in pieces if p[0] == i)
        if phone:
            ph = 1000
            pw = round(390 * ph / 844 / 2) * 2
            chains.append(
                f"color=c=0xe6f4f1:s={W}x{H}:r={FPS}[bg{i}];"
                f"[{i}:v]fps={FPS},scale={pw}:{ph}:flags=lanczos,pad={pw + 28}:{ph + 28}:14:14:color=0x1c1917[ph{i}];"
                f"[bg{i}][ph{i}]overlay=x=(W-w)/2:y=(H-h)/2:shortest=1,split={n}" + "".join(f"[s{i}_{k}]" for k in range(n)))
        else:
            chains.append(f"[{i}:v]fps={FPS},scale={W}:{H}:flags=lanczos,split={n}" + "".join(f"[s{i}_{k}]" for k in range(n)))

    counters = {}
    fi = 0
    for idx, (i, a, b, is_fast) in enumerate(pieces):
        k = counters.get(i, 0)
        counters[i] = k + 1
        speed = g
        extra = ""
        if is_fast:
            speed = g * (b - a) / fast_alloc[fi]
            fi += 1
            extra = (f",drawtext=fontfile='{FONT_B}':text='» sped up':x=W-tw-30:y=84:fontsize=28:fontcolor=white:"
                     f"box=1:boxcolor=0x1c1917@0.75:boxborderw=10")
        chains.append(f"[s{i}_{k}]trim={a:.3f}:{b:.3f},setpts=(PTS-STARTPTS)/{speed:.5f}{extra}[p{idx}]")
        labels.append(f"[p{idx}]")
    chains.append("".join(labels) + f"concat=n={len(labels)}:v=1:a=0[cat]")
    chains.append(f"[cat]tpad=stop_mode=clone:stop_duration={pad + 0.5:.3f},trim=0:{length:.3f},setpts=PTS-STARTPTS,"
                  f"{label_filter(LABELS[scene])},format=yuv420p[v]")

    a_in, a_f = audio_args(scene, length)
    ai = len(parts)
    chains.append(f"[{ai}:a]{a_f}[a]")
    run(["ffmpeg", "-y", *inputs, *a_in, "-filter_complex", ";".join(chains), "-map", "[v]", "-map", "[a]",
         "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "160k",
         "-t", f"{length:.3f}", str(out)])
    print(f"  {scene}: speed x{g:.2f}, fast {[round(x, 1) for x in fast_real]} -> {[round(x, 1) for x in fast_alloc]}, pad {pad:.1f}s")


def srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}"


def chunks(text: str) -> list[str]:
    out = []
    for s in re.split(r"(?<=[.?!])\s+", text.strip()):
        while len(s) > 95:
            cut = max(s.rfind(", ", 0, 90), s.rfind(": ", 0, 90))
            if cut < 30:
                break
            out.append(s[: cut + 1])
            s = s[cut + 2:]
        out.append(s)
    return out


def main():
    scenes = json.loads((ROOT / "scenes.json").read_text(encoding="utf-8"))
    seg_dir = OUT / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    concat_lines, srt, t, n = [], [], 0.0, 1
    for sc in scenes:
        sid = sc["id"]
        speech = duration(ROOT / "audio" / f"{sid}.wav")
        length = round(LEAD + speech + TAIL, 3)
        seg = seg_dir / f"{sid}.mp4"
        print("render", sid, f"{length:.1f}s")
        (render_slide if sid in SLIDES else render_browser)(sid, length, seg)
        concat_lines.append(f"file '{seg.as_posix()}'")
        parts = chunks(sc["text"])
        total_chars = sum(len(p) for p in parts)
        cur = t + LEAD
        for p in parts:
            d = speech * len(p) / total_chars
            srt.append(f"{n}\n{srt_time(cur)} --> {srt_time(cur + d - 0.05)}\n{p}\n")
            n += 1
            cur += d
        t += length
    (OUT / "concat.txt").write_text("\n".join(concat_lines), encoding="utf-8")
    (OUT / "AivaCare-Walkthrough.srt").write_text("\n".join(srt), encoding="utf-8")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(OUT / "concat.txt"), "-c", "copy", str(OUT / "joined.mp4")])
    total = duration(OUT / "joined.mp4")
    style = ("FontName=Segoe UI,FontSize=11,PrimaryColour=&H00FFFFFF,BackColour=&H99000000,"
             "BorderStyle=4,Outline=0,Shadow=0,MarginV=24,MarginL=40,MarginR=40")
    srt_path = (OUT / "AivaCare-Walkthrough.srt").as_posix().replace(":", "\\:")
    run(["ffmpeg", "-y", "-i", str(OUT / "joined.mp4"), "-vf",
         f"subtitles='{srt_path}':force_style='{style}',fade=t=in:st=0:d=0.6,fade=t=out:st={total - 0.8:.2f}:d=0.8",
         "-af", f"afade=t=in:st=0:d=0.3,afade=t=out:st={total - 0.8:.2f}:d=0.8",
         "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
         "-movflags", "+faststart", str(OUT / "AivaCare-Walkthrough.mp4")])
    print(f"done: {total:.1f}s")


if __name__ == "__main__":
    main()
