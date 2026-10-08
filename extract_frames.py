import pyzed.sl as sl
import cv2
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SVO_PATH = os.path.join(ROOT, "scan.svo2")
OUT_DIR = os.path.join(ROOT, "frames")

TARGET_COUNT = 250   # how many images to feed photogrammetry


def main():
    if not os.path.exists(SVO_PATH):
        print(f"ERROR: {SVO_PATH} not found.")
        sys.exit(1)

    os.makedirs(OUT_DIR, exist_ok=True)

    cam = sl.Camera()
    init = sl.InitParameters()
    init.set_from_svo_file(SVO_PATH)
    init.svo_real_time_mode = False
    init.depth_mode = sl.DEPTH_MODE.NONE   # photogrammetry needs the images only

    err = cam.open(init)
    if err != sl.ERROR_CODE.SUCCESS:
        print(f"Failed to open SVO: {err}")
        sys.exit(1)

    total = cam.get_svo_number_of_frames()
    window = max(1, total // TARGET_COUNT)
    print(f"{total} frames in SVO. Keeping the sharpest of every {window} "
          f"-> ~{total // window} images.\n")

    image = sl.Mat()
    runtime = sl.RuntimeParameters()

    best_score = -1.0
    best_img = None
    pos = 0
    saved = 0
    scores = []

    while True:
        err = cam.grab(runtime)
        if err == sl.ERROR_CODE.END_OF_SVOFILE_REACHED:
            break
        if err != sl.ERROR_CODE.SUCCESS:
            continue

        cam.retrieve_image(image, sl.VIEW.LEFT)
        bgr = cv2.cvtColor(image.get_data(), cv2.COLOR_BGRA2BGR)
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        # Laplacian variance = sharpness. Higher = sharper; low = motion blur.
        score = cv2.Laplacian(gray, cv2.CV_64F).var()

        if score > best_score:
            best_score = score
            best_img = bgr

        pos += 1
        if pos % window == 0 and best_img is not None:
            cv2.imwrite(os.path.join(OUT_DIR, f"{saved:04d}.jpg"), best_img,
                        [cv2.IMWRITE_JPEG_QUALITY, 95])
            scores.append(best_score)
            saved += 1
            best_score = -1.0
            best_img = None

    if best_img is not None:
        cv2.imwrite(os.path.join(OUT_DIR, f"{saved:04d}.jpg"), best_img,
                    [cv2.IMWRITE_JPEG_QUALITY, 95])
        scores.append(best_score)
        saved += 1

    cam.close()
    print(f"Saved {saved} images to {OUT_DIR}/")
    if scores:
        scores.sort()
        print(f"Sharpness (Laplacian var): min={scores[0]:.0f}  "
              f"median={scores[len(scores)//2]:.0f}  max={scores[-1]:.0f}")
        print("Low numbers across the board = footage is motion-blurred.")


if __name__ == "__main__":
    main()
