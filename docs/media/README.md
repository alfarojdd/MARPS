# README media

Second media set: 12 application screenshots, two captioned MP4 walkthroughs and a looping GIF preview, edited as slide presentations with no audio. They show the interface and example outputs; they are not recordings of a live session. The [main README](../../README.md) uses the recordings in [product/](product/README.md) instead.

## Watch or read

| Asset | Duration | Contents | Text alternative |
|---|---|---|---|
| [Mission planning](mission-walkthrough.mp4?raw=true) | 42 s | Orbital map → Bellona mission → terrain evaluation → 2D path → 3D low-battery route → briefing → separate gentle-terrain scenario | [Transcript](mission-walkthrough.md) |
| [Surface exploration](surface-exploration.mp4?raw=true) | 20 s | 3D science-mission input → surface marker → Cheyava Falls on foot → Rochette rock detail | [Transcript](surface-exploration.md) |
| [README preview](mission-preview.gif) | 42 s, looping | One frame per mission-planning slide, held for six seconds | [Transcript](mission-walkthrough.md) |

The MP4s use H.264, `yuv420p`, 1600 × 1000 pixels, 24 fps and `faststart` metadata. The README uses ordinary image and file links, so it also works in Markdown viewers that do not embed video. Open an MP4 link to play or download the full-size version. The 960-pixel GIF is the inline preview.

## Screenshot sources

The screenshots are stored as **lossless WebP** at their original dimensions. No interface labels, routes, figures or source credits were changed. Click any screenshot in the main guide to inspect its full-size file.

| Original supplied file | Repository asset | What it shows |
|---|---|---|
| `mainpage.png` | [jezero-map.webp](screenshots/jezero-map.webp) | Initial orbital map, telemetry and Bellona |
| `textBox.png` | [bellona-mission.webp](screenshots/bellona-mission.webp) | Low-battery mission text |
| `scanningBellona.png` | [bellona-scanning.webp](screenshots/bellona-scanning.webp) | Mission submitted; terrain evaluation indicator |
| `scannigmarps.png` | [manual-endpoints.webp](screenshots/manual-endpoints.webp) | Manually selected origin and destination |
| `normalMode.png` | [route-2d.webp](screenshots/route-2d.webp) | 2D route and shortest-path baseline |
| `missionLog.png` | [route-briefing.webp](screenshots/route-briefing.webp) | Low-battery route figures and charging instructions |
| `firstRoute.png` | [route-solar-recharge.webp](screenshots/route-solar-recharge.webp) | Low-battery result in 3D |
| `secondRoute.png` | [route-gentle-terrain.webp](screenshots/route-gentle-terrain.webp) | Gentler route in 3D |
| `thirdRoute.png` | [science-mission-3d.webp](screenshots/science-mission-3d.webp) | Science-mission input over the 3D relief |
| `3dmodelSelect.png` | [surface-marker.webp](screenshots/surface-marker.webp) | Cheyava Falls marker selection |
| `3dmodel1.png` | [cheyava-on-foot.webp](screenshots/cheyava-on-foot.webp) | Local first-person surface viewer |
| `3dmodel.png` | [rochette-rock.webp](screenshots/rochette-rock.webp) | External annotated rock-detail viewer |

The low-battery example starts at **40%** battery, while the gentle-terrain example starts at **75%**. They are separate mission runs, not a controlled comparison that changes only one planner parameter. The science image shows a prompt before submission, not a computed science-route result. Rounded charging times and other values in screenshots are kept as captured.

## Credits

Application UI and screenshot selection: MARPS / project author. Orbital imagery and derived terrain layers: the NASA, ESA and USGS products described in [DATA_SOURCES.md](../DATA_SOURCES.md).

- **Cheyava Falls · Neretva Vallis:** Planetary Scene Studio, built from Perseverance imagery, sols 1195–1210. [Original project](https://github.com/Matusvec/spaceX-Mhacks-Challenge). The source scene's redistribution terms remain unconfirmed, as indicated in the captured UI and [RECONSTRUCTIONS.md](../RECONSTRUCTIONS.md). These documentation assets contain the supplied screenshots, not the downloadable scene geometry.
- **M2020 ZCAM — Rochette pre-abrasion, sol 180:** Mastcam-Z; source credits NASA/JPL/MSSS/ASU/Cornell. The catalogue records **CC Attribution**. [Original model and author terms](https://sketchfab.com/3d-models/c58c8f9cb9374b02b117e87e9748b5a0). The screenshot and video preserve the embedded viewer's author and licence labels. No model files are included in this media folder.

Underlying third-party content retains its original terms; the repository's code licence does not replace those terms. See [NOTICE](../../NOTICE) and [DATA_SOURCES.md](../DATA_SOURCES.md).

## Rebuild

Requirements: Python 3, FFmpeg with `libx264`, `libwebp`, `drawtext`, `palettegen` and `paletteuse`, and the DejaVu Sans regular/bold fonts. No app server, model downloads, Ollama or Python packages are required.

From the repository root, regenerate the videos, preview and text transcripts from the committed screenshots:

```bash
python3 docs/media/build_media.py
```

To import a new copy of the 12 original PNGs and rebuild everything:

```bash
python3 docs/media/build_media.py --import-from /path/to/original-screenshots
```

If the fonts are installed elsewhere, pass `--font-dir /path/to/dejavu`. Run the build before committing updated screenshots so the preview, videos and transcripts stay in sync. Captions, slide order, durations and the original-to-repository filename map live in [build_media.py](build_media.py).
