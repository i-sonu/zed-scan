import pyzed.sl as sl
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SVO_PATH = os.path.join(ROOT, "scan.svo2")
OUTPUT_OBJ = os.path.join(ROOT, "room.obj")

# Tunables — re-run with these changed; no need to re-record the SVO.
RESOLUTION_METER = 0.02   # 0.02 = doc-recommended room scale; 0.01 = max detail (heavier)
MAX_MEMORY_MB = 4096      # capped by 15 GB system RAM — 8192+ OOM-kills at init


def main():
    if not os.path.exists(SVO_PATH):
        print(f"ERROR: {SVO_PATH} not found. Run record.py first.")
        sys.exit(1)

    cam = sl.Camera()

    # Reopen the SVO offline. svo_real_time_mode=False processes every frame
    # regardless of wall-clock speed.
    init = sl.InitParameters()
    init.set_from_svo_file(SVO_PATH)
    init.svo_real_time_mode = False
    init.depth_mode = sl.DEPTH_MODE.NEURAL_PLUS   # highest quality; offline budget affords it
    init.coordinate_units = sl.UNIT.METER
    init.coordinate_system = sl.COORDINATE_SYSTEM.RIGHT_HANDED_Y_UP
    init.depth_minimum_distance = 0.3
    init.depth_maximum_distance = 8.0

    err = cam.open(init)
    if err != sl.ERROR_CODE.SUCCESS:
        print(f"Failed to open SVO: {err}")
        sys.exit(1)

    # GEN_3 positional tracking — full loop closure for a handheld orbit.
    ptp = sl.PositionalTrackingParameters()
    ptp.mode = sl.POSITIONAL_TRACKING_MODE.GEN_3
    ptp.enable_area_memory = True
    ptp.enable_imu_fusion = True
    ptp.set_gravity_as_origin = True
    err = cam.enable_positional_tracking(ptp)
    if err != sl.ERROR_CODE.SUCCESS:
        print(f"Failed to enable positional tracking: {err}")
        cam.close()
        sys.exit(1)

    # MESH map so it can be textured. resolution_meter set directly for fine control.
    smp = sl.SpatialMappingParameters()
    smp.map_type = sl.SPATIAL_MAP_TYPE.MESH
    smp.resolution_meter = RESOLUTION_METER
    smp.save_texture = True            # must be True before enable for a textured OBJ
    smp.use_chunk_only = False         # full consolidated mesh at finalize
    smp.max_memory_usage = MAX_MEMORY_MB
    err = cam.enable_spatial_mapping(smp)
    if err != sl.ERROR_CODE.SUCCESS:
        print(f"Failed to enable spatial mapping: {err}")
        cam.disable_positional_tracking()
        cam.close()
        sys.exit(1)

    runtime = sl.RuntimeParameters()
    runtime.confidence_threshold = 50
    total = cam.get_svo_number_of_frames()
    print(f"Processing {total} SVO frames at {RESOLUTION_METER * 1000:.0f}mm resolution...\n")

    mesh = sl.Mesh()
    processed = 0
    bad_odom = 0
    last_odom = None
    try:
        while True:
            err = cam.grab(runtime)
            if err == sl.ERROR_CODE.SUCCESS:
                processed += 1
                # Tracking health — a melted mesh means the pose drifted somewhere
                # in here. odometry_status leaving OK is the canonical bad signal.
                ts = cam.get_positional_tracking_status()
                odom = ts.odometry_status
                if odom != sl.ODOMETRY_STATUS.OK:
                    bad_odom += 1
                if odom != last_odom:
                    print(f"\n  [frame {processed}] odometry: {last_odom} -> {odom}")
                    last_odom = odom
                if processed % 120 == 0:
                    state = cam.get_spatial_mapping_state()
                    print(f"\r  frame {processed}/{total}  mapping={state}", end="", flush=True)
            elif err == sl.ERROR_CODE.END_OF_SVOFILE_REACHED:
                print(f"\n  end of SVO ({processed} frames processed)")
                print(f"  frames with degraded odometry: {bad_odom}/{processed}")
                break
            else:
                continue   # transient error, keep going

        print("\nExtracting mesh...")
        cam.extract_whole_spatial_map(mesh)

        # LOW filter = hole-fill + outlier removal only, no decimation (keeps it dense).
        filt = sl.MeshFilterParameters()
        filt.set(sl.MESH_FILTER.LOW)
        mesh.filter(filt, True)

        n_verts = len(mesh.vertices)
        n_tris = len(mesh.triangles)
        print(f"Mesh: {n_verts} vertices, {n_tris} triangles")

        if n_verts == 0:
            print("ERROR: empty mesh. Tracking likely never locked — check the scan.")
            sys.exit(1)

        print("Applying texture...")
        mesh.apply_texture(sl.MESH_TEXTURE_FORMAT.RGBA)

        ok = mesh.save(OUTPUT_OBJ)
        if ok:
            print(f"\nSaved: {OUTPUT_OBJ} (+ .mtl + texture png)")
        else:
            print(f"\nERROR: mesh.save returned False")
    finally:
        cam.disable_spatial_mapping()
        cam.disable_positional_tracking()
        cam.close()


if __name__ == "__main__":
    main()
