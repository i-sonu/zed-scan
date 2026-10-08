import pyzed.sl as sl
import cv2
import os
import sys

SVO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scan.svo2")


def start_recording(cam):
    """Try H265_LOSSLESS (NVENC, ~25% raw), fall back to LOSSLESS (CPU, ~42% raw)."""
    for mode in (sl.SVO_COMPRESSION_MODE.H265_LOSSLESS, sl.SVO_COMPRESSION_MODE.LOSSLESS):
        rec = sl.RecordingParameters()
        rec.video_filename = SVO_PATH
        rec.compression_mode = mode
        err = cam.enable_recording(rec)
        if err == sl.ERROR_CODE.SUCCESS:
            print(f"Recording started: {SVO_PATH}  (compression={mode})")
            return True
        print(f"  enable_recording failed with {mode}: {err}")
    return False


def main():
    print("=" * 60)
    print("  ZED 2i Room Scan — SVO Recording (Phase A)")
    print("=" * 60)
    print("  - HD720 @ 60fps for robust tracking.")
    print("  - Press SPACE to start recording.")
    print("  - Move SLOWLY, steady, ~0.2-0.5 m/s. Keep good overlap.")
    print("  - End where you started so loop closure can correct drift.")
    print("  - Press Q or ESC to stop.")
    print("=" * 60 + "\n")

    cam = sl.Camera()

    init = sl.InitParameters()
    init.camera_resolution = sl.RESOLUTION.HD720
    init.camera_fps = 60
    init.depth_mode = sl.DEPTH_MODE.NONE   # depth is recomputed offline in process.py
    init.coordinate_units = sl.UNIT.METER

    err = cam.open(init)
    if err != sl.ERROR_CODE.SUCCESS:
        print(f"Failed to open camera: {err}")
        sys.exit(1)

    image = sl.Mat()
    runtime = sl.RuntimeParameters()
    recording = False
    frames = 0
    loop_i = 0

    cv2.namedWindow("ZED Recording", cv2.WINDOW_NORMAL)
    print("Preview active. Press SPACE to start recording.\n")

    try:
        while True:
            err = cam.grab(runtime)
            if err != sl.ERROR_CODE.SUCCESS:
                print(f"Grab failed: {err}")
                break

            # Every successful grab is auto-written to the SVO once recording is on.
            if recording:
                frames += 1
            loop_i += 1

            # grab() runs every iteration (all 60fps get recorded), but rendering
            # the preview every frame starves the 16.7ms loop budget and drops
            # frames. Throttle the display to ~20fps.
            if loop_i % 3 != 0:
                continue

            cam.retrieve_image(image, sl.VIEW.LEFT)
            preview = cv2.cvtColor(image.get_data(), cv2.COLOR_BGRA2BGR)

            label = f"RECORDING  frames: {frames}" if recording else "Press SPACE to record"
            color = (0, 0, 255) if recording else (0, 200, 0)
            cv2.putText(preview, label, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)

            cv2.imshow("ZED Recording", preview)
            key = cv2.waitKey(1) & 0xFF

            if key == ord(' ') and not recording:
                if not start_recording(cam):
                    print("Could not start recording. Aborting.")
                    break
                recording = True
            elif key in (ord('q'), ord('Q'), 27):
                print("Stopping...")
                break
    finally:
        cv2.destroyAllWindows()
        if recording:
            dropped = cam.get_frame_dropped_count()
            cam.disable_recording()
            print(f"\nRecorded {frames} frames to {SVO_PATH}")
            print(f"Frames dropped during recording: {dropped}")
        cam.close()

    if recording and frames > 0:
        print("Done. Proceed to process.py.")
    else:
        print("No frames recorded.")


if __name__ == "__main__":
    main()
