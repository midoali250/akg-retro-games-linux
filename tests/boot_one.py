"""Boot one ROM in an isolated child; does not simulate a complete game."""
import sys
from libretro_host import LibretroHost
with LibretroHost(sys.argv[1],sys.argv[2]) as core:
    for i in range(30):
        core.buttons={3} if 10<=i<15 else set()
        core.run_frame()
    if not core.frames or not core.last_frame or not core.width or not core.height:
        raise SystemExit('no video frame received')
    print('BOOT_VIDEO_OK',core.width,core.height,core.frames)
