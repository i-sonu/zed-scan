import pyzed.sl as sl
import sys

def main():
    cam = sl.Camera()

    init = sl.InitParameters()
    init.camera_resolution = sl.RESOLUTION.HD720
    init.depth_mode = sl.DEPTH_MODE.PERFORMANCE
    init.camera_fps = 30

    err = cam.open(init)
    if err != sl.ERROR_CODE.SUCCESS:
        print(f"Failed to open camera: {err}")
        sys.exit(1)

    info = cam.get_camera_information()
    res = info.camera_configuration.resolution
    print(f"Resolution : {res.width} x {res.height}")
    print(f"Serial     : {info.serial_number}")

    image = sl.Mat()
    depth = sl.Mat()
    runtime = sl.RuntimeParameters()

    # Grab several frames so the depth pipeline warms up and FPS stabilizes
    for i in range(10):
        err = cam.grab(runtime)
        if err != sl.ERROR_CODE.SUCCESS:
            print(f"Failed to grab frame {i}: {err}")
            cam.close()
            sys.exit(1)

    cam.retrieve_image(image, sl.VIEW.LEFT)
    cam.retrieve_measure(depth, sl.MEASURE.DEPTH)

    w, h = res.width, res.height
    cx, cy = w // 2, h // 2

    depth_val = depth.get_value(cx, cy)[1]  # returns (error_code, value)
    print(f"Depth at center ({cx},{cy}): {depth_val:.1f} mm")

    fps = cam.get_current_fps()
    print(f"Current FPS: {fps:.1f}")

    cam.close()
    print("Camera closed cleanly.")

    if 300 <= depth_val <= 5000:
        print("PASS: depth in expected range.")
    else:
        print("WARN: depth out of expected range (300-5000 mm). Point camera at an object 0.5-2m away.")

if __name__ == "__main__":
    main()
