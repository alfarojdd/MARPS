#!/usr/bin/env python3
"""Build the README screenshot walkthroughs with FFmpeg (no running app needed)."""

import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
SHOTS = ROOT / "screenshots"
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")

# Original filenames supplied with the documentation request. WebP is lossless:
# screenshots retain their original dimensions, text, figures and attribution.
IMPORTS = {
    "mainpage.png": "jezero-map.webp",
    "textBox.png": "bellona-mission.webp",
    "scanningBellona.png": "bellona-scanning.webp",
    "scannigmarps.png": "manual-endpoints.webp",
    "normalMode.png": "route-2d.webp",
    "missionLog.png": "route-briefing.webp",
    "firstRoute.png": "route-solar-recharge.webp",
    "secondRoute.png": "route-gentle-terrain.webp",
    "thirdRoute.png": "science-mission-3d.webp",
    "3dmodelSelect.png": "surface-marker.webp",
    "3dmodel1.png": "cheyava-on-foot.webp",
    "3dmodel.png": "rochette-rock.webp",
}

# Each frame uses a complete screenshot, fitted inside a separate caption frame.
# The route examples have different starting battery states; they are separate
# scenarios, not successive states of a single run.
WALKTHROUGHS = {
    "mission-walkthrough": (6, [
        ("jezero-map.webp", "01 / Explore Jezero crater",
         "Start with the orbital map, departure time, battery and surface markers."),
        ("bellona-mission.webp", "02 / Describe the mission to Bellona",
         "Two astronauts. Low battery. Ask for an energy-saving route and a sunlit charging stop."),
        ("bellona-scanning.webp", "03 / Request a route",
         "Bellona interprets the mission while the deterministic planner evaluates the terrain."),
        ("route-2d.webp", "04 / Inspect the route in 2D",
         "Compare the planned path with the dashed shortest-path baseline."),
        ("route-solar-recharge.webp", "05 / Inspect the low-battery result in 3D",
         "12.2 km | 5.1 h | 20% battery on arrival | includes a sunlit charging stop."),
        ("route-briefing.webp", "06 / Read the route briefing",
         "Review distance, time, elevation, slope, battery and the charging-stop instructions."),
        ("route-gentle-terrain.webp", "07 / Compare a different mission scenario",
         "Gentle terrain: 14.0 km | 10.3 degree maximum slope | starts with 75% battery."),
    ]),
    "surface-exploration": (5, [
        ("science-mission-3d.webp", "01 / Explore the relief in 3D",
         "Describe science goals, inspect the delta and locate surface reconstructions."),
        ("surface-marker.webp", "02 / Choose a surface marker",
         "Select a 3D marker: Cheyava Falls, Neretva Vallis, sol 1195."),
        ("cheyava-on-foot.webp", "03 / Enter the surface reconstruction",
         "Drag to look around. Use WASD or arrow keys to walk. Switch to Orbit view to inspect."),
        ("rochette-rock.webp", "04 / Inspect a rock detail",
         "Rochette, sol 180: an external Mastcam-Z reconstruction with its original attribution."),
    ]),
}


def run(*args):
    subprocess.run([str(arg) for arg in args], check=True)


def ffmpeg(*args):
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-filter_threads", "2", *args)


def build_video(name, seconds, slides, font_dir, temp):
    regular = font_dir / "DejaVuSans.ttf"
    bold = font_dir / "DejaVuSans-Bold.ttf"
    clips = []
    for index, (shot, title, caption) in enumerate(slides):
        title_file = temp / f"{name}-{index}-title.txt"
        caption_file = temp / f"{name}-{index}-caption.txt"
        title_file.write_text(title, encoding="utf-8")
        caption_file.write_text(caption, encoding="utf-8")
        clip = temp / f"{name}-{index}.mp4"
        # 1600 x 1000, with the screenshot in a 1568 x 768 viewport.
        # Captions never cover the application UI or third-party credits.
        filters = ",".join([
            "scale=1568:768:force_original_aspect_ratio=decrease:flags=lanczos",
            "pad=1600:1000:(ow-iw)/2:96+(768-ih)/2:color=0x151310",
            "setsar=1",
            "drawbox=x=0:y=0:w=6:h=82:color=0xff743b:t=fill",
            f"drawtext=fontfile='{bold}':text='MARPS / BELLONA':x=28:y=14:fontsize=15:fontcolor=0xffab83",
            f"drawtext=fontfile='{bold}':textfile='{title_file}':expansion=none:x=28:y=39:fontsize=28:fontcolor=0xf6f0e8",
            f"drawtext=fontfile='{regular}':textfile='{caption_file}':expansion=none:x=28:y=894:fontsize=24:fontcolor=0xf6f0e8",
            f"drawtext=fontfile='{regular}':text='Screenshot walkthrough / No audio / Separate mission examples':x=28:y=948:fontsize=16:fontcolor=0xbeb3a6",
            f"drawtext=fontfile='{bold}':text='{index + 1} / {len(slides)}':x=1490:y=948:fontsize=16:fontcolor=0xffab83",
            f"drawbox=x=0:y=996:w={1600 * (index + 1) // len(slides)}:h=4:color=0xff743b:t=fill",
            f"fade=t=in:st=0:d=0.2,fade=t=out:st={seconds - 0.2}:d=0.2",
            "format=yuv420p",
        ])
        ffmpeg("-loop", "1", "-framerate", "24", "-i", SHOTS / shot,
               "-vf", filters, "-t", str(seconds), "-an", "-c:v", "libx264",
               "-threads", "2", "-preset", "medium", "-tune", "stillimage",
               "-crf", "20", "-pix_fmt", "yuv420p", clip)
        clips.append(clip)
    concat = temp / f"{name}-concat.txt"
    concat.write_text("".join(f"file '{clip}'\n" for clip in clips), encoding="utf-8")
    ffmpeg("-f", "concat", "-safe", "0", "-i", concat, "-c", "copy",
           "-movflags", "+faststart", ROOT / f"{name}.mp4")
    # Captions are also available as text, independent of the baked-in video UI.
    transcript = [f"# {name.replace('-', ' ').title()}", "",
                  "A silent walkthrough assembled from supplied application screenshots.",
                  "Each numbered item corresponds to one captioned video slide.", ""]
    for index, (_, title, caption) in enumerate(slides):
        start, end = index * seconds, (index + 1) * seconds
        transcript.extend([f"- **{start:02d}–{end:02d} s · {title[5:]}** {caption}"])
    (ROOT / f"{name}.md").write_text("\n".join(transcript) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--import-from", type=Path, help="Folder containing the 12 original PNGs")
    parser.add_argument("--font-dir", type=Path, default=FONT_DIR,
                        help="Folder containing DejaVuSans.ttf and DejaVuSans-Bold.ttf")
    args = parser.parse_args()
    if not shutil.which("ffmpeg"):
        parser.error("FFmpeg is required (libx264, libwebp and drawtext support).")
    for font in ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"):
        if not (args.font_dir / font).is_file():
            parser.error(f"Missing {font}; set --font-dir to the DejaVu font directory.")
    if args.import_from:
        for original in IMPORTS:
            if not (args.import_from / original).is_file():
                parser.error(f"Missing original screenshot: {original}")
        SHOTS.mkdir(parents=True, exist_ok=True)
        for original, output in IMPORTS.items():
            ffmpeg("-i", args.import_from / original, "-frames:v", "1",
                   "-c:v", "libwebp", "-lossless", "1", "-compression_level", "6",
                   SHOTS / output)
    for shot in IMPORTS.values():
        if not (SHOTS / shot).is_file():
            parser.error(f"Missing {shot}; use --import-from to import the original PNGs.")
    with tempfile.TemporaryDirectory(prefix="marps-media-") as temp_dir:
        temp = Path(temp_dir)
        for name, (seconds, slides) in WALKTHROUGHS.items():
            print(f"Building {name}...", flush=True)
            build_video(name, seconds, slides, args.font_dir.resolve(), temp)
        # One representative frame per slide keeps the README animation small.
        print("Building README preview...", flush=True)
        ffmpeg("-i", ROOT / "mission-walkthrough.mp4", "-filter_complex_threads", "2",
               "-filter_complex",
               "fps=1/6,scale=960:-1:flags=lanczos,split[a][b];"
               "[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3",
               "-loop", "0", ROOT / "mission-preview.gif")
    print("Done. See docs/media/README.md for the asset map and transcripts.")


if __name__ == "__main__":
    main()
