# SpiderPet implementation notes

- The supplied sprite sheets and extracted transparent frames remain unchanged on disk.
- Runtime scaling uses nearest-neighbour/fast interpolation so the pixel art stays crisp.
- Default scale is 1.75x; the idle animation defaults to 12 FPS and the hanging animation to 24 FPS.
- The Linux branch uses GTK3 + GtkLayerShell for the transparent Wayland overlay.
- The Windows branch uses PySide6 Essentials, with a small transparent sprite window and a narrow mouse-transparent web-line window. Win32 extended styles make the line window pass mouse input through to applications below it.
- Both branches provide a draggable desktop pet, idle/head-turn animation, web shooting, descent, hanging, and ascent after a second click.

Windows runtime behavior still needs smoke testing on a Windows 10/11 desktop. In particular, verify the z-order of the two transparent windows, click-through behavior outside the pet, dragging across monitors, and startup from the batch launcher.
