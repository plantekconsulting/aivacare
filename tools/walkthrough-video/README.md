# Walkthrough video

Rebuilds the 5-minute narrated walkthrough (`media/AivaCare-Walkthrough.mp4`, not committed).

Needs: Windows (built-in speech voices), Google Chrome, ffmpeg/ffprobe on PATH, Node with `playwright-core`, Python 3.
The scripts work in `C:\dev\video` (outside Google Drive). Copy this folder there and create `audio/`, `slides/`, `clips/`, `out/`.

| Step | Command | Output |
|---|---|---|
| 1. Narration | `powershell -File tts.ps1` | `audio/*.wav` from `scenes.json` |
| 2. Slides | `node shot-slides.mjs` | `slides/*.png` from `slides.html` |
| 3. Screen recording | `CODE=<team access code> node record.mjs` | `clips/*.webm` + timing marks (resets the demo data first, and changes it while recording) |
| 4. Assembly | `python assemble.py` | `out/AivaCare-Walkthrough.mp4` + `.srt` captions |

Reset the demo data afterwards (Demo Admin → Reset). To change what's said, edit `scenes.json` and rerun steps 1 and 4.
