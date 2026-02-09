"""Camera discovery utility."""

from __future__ import annotations


def discover_cameras() -> list[dict[str, str]]:
    """Discover available Spinnaker cameras."""
    try:
        import PySpin
    except ImportError:
        print("Spinnaker SDK not installed")
        return []

    system = PySpin.System.GetInstance()
    cam_list = system.GetCameras()

    cameras = []
    for i in range(cam_list.GetSize()):
        cam = cam_list.GetByIndex(i)
        cam.Init()

        info = {
            "index": str(i),
            "serial": cam.DeviceSerialNumber.GetValue(),
            "model": cam.DeviceModelName.GetValue(),
            "vendor": cam.DeviceVendorName.GetValue(),
        }
        cameras.append(info)
        cam.DeInit()

    cam_list.Clear()
    system.ReleaseInstance()

    return cameras


def main() -> None:
    """CLI entry point for camera discovery."""
    print("Discovering Spinnaker cameras...\n")

    cameras = discover_cameras()

    if not cameras:
        print("No cameras found.")
        return

    print(f"Found {len(cameras)} camera(s):\n")
    for cam in cameras:
        print(f"  [{cam['index']}] {cam['model']}")
        print(f"      Serial: {cam['serial']}")
        print(f"      Vendor: {cam['vendor']}")
        print()


if __name__ == "__main__":
    main()
