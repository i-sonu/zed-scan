# zed-scan

3D room reconstruction from a handheld **ZED 2i** stereo-camera scan.

The workflow records a raw stereo video once, then reprocesses it offline into
either a textured mesh (ZED spatial mapping) or a set of sharp frames for
photogrammetry.

## Requirements

- ZED SDK + Python API (`pyzed`)
- `opencv-python`, `numpy`

## Pipeline

| Step | Script | What it does |
|------|--------|--------------|
| 0 | `verify_zed.py` | Sanity-check the camera: resolution, serial, center depth, FPS. |
| A | `record.py` | Record a raw `scan.svo2` at HD720/60fps. Depth off (recomputed offline). SPACE to start, Q/ESC to stop. Move slowly and end where you started for loop closure. |
| B1 | `process.py` | Replay the SVO offline with NEURAL_PLUS depth + GEN_3 tracking + spatial mapping; export a textured mesh to `room.obj`. |
| B2 | `extract_frames.py` | Alternative to B1: pull the sharpest frame from each window (Laplacian-variance sharpness) into `frames/` for photogrammetry (e.g. Meshroom). |

## Usage

```bash
python3 verify_zed.py        # confirm the camera works
python3 record.py            # Phase A: record scan.svo2
python3 process.py           # Phase B1: SVO -> textured mesh (room.obj)
# or
python3 extract_frames.py    # Phase B2: SVO -> frames/ for photogrammetry
```

## Notes

- Recordings (`*.svo2`), mesh outputs (`*.obj`/`*.mtl`/texture), and extracted
  `frames/` are git-ignored — they are large and regenerable from the SVO.
- `process.py` tunables (`RESOLUTION_METER`, `MAX_MEMORY_MB`) can be changed and
  re-run without re-recording.
