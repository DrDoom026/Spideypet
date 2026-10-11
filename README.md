# SpiderPet — Living Sprite Prototype

A minimal transparent GTK3 + GtkLayerShell desktop pet for Omarchy/Hyprland on Wayland. This prototype uses the two sprite sheets exactly as supplied: the first sheet provides the default idle/head-turn animation, and clicking SpiderPet plays the second sheet's hanging animation once before returning to idle.

## Supplied artwork — preserved unchanged

- `assets/sprites/SpiderMan_HeadTurn.png`: original first uploaded sprite sheet, preserved byte-for-byte.
- `assets/sprites/SpiderMan_web.png`: original second uploaded hanging-animation sheet, preserved byte-for-byte.
- `assets/sprites/head_turn/frame_001.png` through `frame_076.png`: extracted transparent frames from the first sheet.
- `assets/sprites/hanging/frame_001.png` through `frame_077.png`: extracted transparent frames from the second sheet.
- `assets/sprites/manifest.json` and `assets/sprites/hanging_manifest.json`: extraction manifests.
- `docs/head_turn_contact_sheet.png`, `docs/hanging_contact_sheet.png`, and `docs/hanging_preview.gif`: inspection previews.

**No original sheet or extracted frame is recolored, redrawn, retouched, or resized on disk.** Runtime scaling creates cached in-memory copies with nearest-neighbour interpolation only.

## Behavior

1. SpiderPet appears beside the top-right area of Waybar.
2. The first sheet's extracted frames loop as the default idle/head-turn animation at 12 FPS.
3. Click/tap the pet to play the second sheet's hanging animation once at 24 FPS. Drag with the left mouse button to reposition it; a small movement threshold distinguishes a drag from a click.
4. When the hanging sequence finishes, SpiderPet returns to the first sheet's idle animation.
5. No walking, sitting, jumping, web shooting, stats, menus, or other features yet.

The first sheet is treated as an animation sequence; a separate blink behavior should only be added later if the supplied frames clearly contain blink/closed-eye poses. Do not synthesize or alter frames to create a blink.

## Run

```bash
python main.py
```

Optional scaling (default 1.75x, slightly smaller than the first build):

```bash
SPIDERPET_SCALE=3 python main.py
```

Optional frame rates:

```bash
SPIDERPET_IDLE_FPS=8 SPIDERPET_HANGING_FPS=15 python main.py
```

Use `Ctrl+C` in the launching terminal to stop it.

## Technical notes

- GTK3 + PyGObject, GdkPixbuf and GtkLayerShell; no new dependencies added.
- Transparent, undecorated overlay initially placed near the top-right. Dragging repositions it across the screen by updating GtkLayerShell margins.
- All frames are loaded and scaled once at startup; GLib timeouts drive animation, with no busy polling or worker threads.
- No package installation, sudo, desktop/system configuration changes, or Git commands.
- If GTK or GtkLayerShell bindings are missing, report the exact error rather than installing anything.

## Next phase

First validate the animation and click interaction. Only after that, consider CPU/RAM indicators and other features. Keep the implementation small and avoid feature creep.
