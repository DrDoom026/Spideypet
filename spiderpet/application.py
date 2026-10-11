"""SpiderPet: lightweight, draggable GTK3 sprite pet for Omarchy/Hyprland."""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SPRITES_DIR = BASE_DIR / "assets" / "sprites"
IDLE_DIR = SPRITES_DIR / "head_turn"
HANGING_DIR = SPRITES_DIR / "hanging"


def main() -> int:
    try:
        import cairo
        import gi
        gi.require_version("Gtk", "3.0")
        gi.require_version("Gdk", "3.0")
        gi.require_version("GdkPixbuf", "2.0")
        gi.require_version("GtkLayerShell", "0.1")
        from gi.repository import Gtk, Gdk, GdkPixbuf, GtkLayerShell, GLib
    except (ImportError, ValueError) as exc:
        print(
            "SpiderPet needs the existing GTK3, PyGObject, GdkPixbuf, "
            "GtkLayerShell, and Cairo bindings available in the Omarchy environment.\n"
            f"Import detail: {exc}", file=sys.stderr,
        )
        return 2

    def frame_paths(folder: Path) -> list[Path]:
        return sorted(folder.glob("frame_*.png"))

    idle_paths = frame_paths(IDLE_DIR)
    hanging_paths = frame_paths(HANGING_DIR)
    if not idle_paths or not hanging_paths:
        print("SpiderPet sprite frames are missing. Check assets/sprites/.", file=sys.stderr)
        return 2

    # Fractional nearest-neighbour scaling keeps the sprite slightly smaller
    # than the previous 2x size without softening the pixel art.
    try:
        scale = max(1.0, min(float(os.environ.get("SPIDERPET_SCALE", "1.75")), 5.0))
        idle_fps = max(1, min(int(os.environ.get("SPIDERPET_IDLE_FPS", "12")), 24))
        hanging_fps = max(1, min(int(os.environ.get("SPIDERPET_HANGING_FPS", "24")), 30))
    except ValueError:
        print("Invalid SpiderPet scale/FPS environment value.", file=sys.stderr)
        return 2

    def load_frames(paths: list[Path]) -> list[object]:
        loaded = []
        for path in paths:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(str(path))
            width = max(1, round(pixbuf.get_width() * scale))
            height = max(1, round(pixbuf.get_height() * scale))
            loaded.append(pixbuf.scale_simple(width, height, GdkPixbuf.InterpType.NEAREST))
        return loaded

    idle_frames = load_frames(idle_paths)
    hanging_frames = load_frames(hanging_paths)
    canvas_w = max(frame.get_width() for frame in idle_frames + hanging_frames)
    canvas_h = max(frame.get_height() for frame in idle_frames + hanging_frames)

    window = Gtk.Window(type=Gtk.WindowType.TOPLEVEL)
    window.set_title("SpiderPet")
    window.set_decorated(False)
    window.set_resizable(False)
    window.set_skip_taskbar_hint(True)
    window.set_skip_pager_hint(True)
    window.set_keep_above(True)
    window.set_type_hint(Gdk.WindowTypeHint.DOCK)
    window.set_app_paintable(True)

    screen = window.get_screen()
    visual = screen.get_rgba_visual()
    if visual is not None:
        window.set_visual(visual)
    css = Gtk.CssProvider()
    css.load_from_data(
        b"window, drawingarea { background: transparent; background-color: rgba(0,0,0,0); "
        b"border: none; padding: 0; margin: 0; }"
    )
    Gtk.StyleContext.add_provider_for_screen(
        screen, css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    area = Gtk.DrawingArea()
    area.add_events(
        Gdk.EventMask.BUTTON_PRESS_MASK
        | Gdk.EventMask.BUTTON_RELEASE_MASK
        | Gdk.EventMask.BUTTON1_MOTION_MASK
        | Gdk.EventMask.POINTER_MOTION_MASK
    )
    window.add_events(
        Gdk.EventMask.BUTTON_PRESS_MASK
        | Gdk.EventMask.BUTTON_RELEASE_MASK
        | Gdk.EventMask.BUTTON1_MOTION_MASK
        | Gdk.EventMask.POINTER_MOTION_MASK
    )
    window.add(area)

    def get_output_size() -> tuple[int, int]:
        alloc = area.get_allocation()
        if alloc.width > 1 and alloc.height > 1:
            return alloc.width, alloc.height
        display = Gdk.Display.get_default()
        if display is not None:
            mon = display.get_primary_monitor() or (
                display.get_monitor(0) if display.get_n_monitors() > 0 else None
            )
            if mon is not None:
                geom = mon.get_geometry()
                return geom.width, geom.height
        screen = window.get_screen()
        return screen.get_width(), screen.get_height()

    init_w, init_h = get_output_size()
    window.set_default_size(init_w, init_h)

    state = {
        "mode": "idle",
        "index": 0,
        "press_x": 0.0,
        "press_y": 0.0,
        "offset_x": 0.0,
        "offset_y": 0.0,
        "dragging": False,
        "initialized": False,
        "x": max(0, init_w - canvas_w - 12),
        "y": 8,
        "web_top_y": 8.0,
        "shoot_start_time": 0.0,
        "shoot_duration": 0.0,
        "descent_start_time": 0.0,
        "descent_duration": 0.0,
        "descent_start_y": 8,
        "descent_target_y": 8,
        "ascent_start_time": 0.0,
        "ascent_duration": 0.0,
        "ascent_start_y": 8,
        "ascent_target_y": 8,
    }

    def current_frames() -> list[object]:
        return hanging_frames if state["mode"] in ("descending", "hanging", "ascending") else idle_frames

    def update_input_region() -> None:
        rect = cairo.RectangleInt(
            int(round(state["x"])),
            int(round(state["y"])),
            int(canvas_w),
            int(canvas_h),
        )
        region = cairo.Region(rect)
        window.input_shape_combine_region(region)
        gdk_win = window.get_window()
        if gdk_win is not None:
            gdk_win.input_shape_combine_region(region, 0, 0)

    def draw_web(cr: cairo.Context, x: float, y_top: float, y_bottom: float) -> None:
        if y_bottom <= y_top:
            return
        line_x = round(x) + 0.5
        # Subtle dark halo for visibility against light backgrounds
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.35)
        cr.set_line_width(2.5)
        cr.move_to(line_x, y_top)
        cr.line_to(line_x, y_bottom)
        cr.stroke()

        # Restrained soft-white web core
        cr.set_source_rgba(0.95, 0.96, 1.0, 0.95)
        cr.set_line_width(1.2)
        cr.move_to(line_x, y_top)
        cr.line_to(line_x, y_bottom)
        cr.stroke()

    def on_draw(_widget: object, cr: cairo.Context) -> bool:
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        frames = current_frames()
        pixbuf = frames[state["index"] % len(frames)]
        x = state["x"] + (canvas_w - pixbuf.get_width()) // 2
        y = state["y"] + (canvas_h - pixbuf.get_height()) // 2

        attach_x = state["x"] + canvas_w / 2.0
        attach_y = float(y + 2)

        if state["mode"] == "web_shooting":
            web_top_y = state.get("web_top_y", attach_y)
            draw_web(cr, attach_x, web_top_y, attach_y)
        elif state["mode"] in ("descending", "hanging", "ascending"):
            draw_web(cr, attach_x, 0.0, attach_y)

        Gdk.cairo_set_source_pixbuf(cr, pixbuf, x, y)
        cr.paint()
        return False

    area.connect("draw", on_draw)

    GtkLayerShell.init_for_window(window)
    GtkLayerShell.set_layer(window, GtkLayerShell.Layer.TOP)
    GtkLayerShell.set_namespace(window, "spiderpet")
    GtkLayerShell.set_anchor(window, GtkLayerShell.Edge.TOP, True)
    GtkLayerShell.set_anchor(window, GtkLayerShell.Edge.BOTTOM, True)
    GtkLayerShell.set_anchor(window, GtkLayerShell.Edge.LEFT, True)
    GtkLayerShell.set_anchor(window, GtkLayerShell.Edge.RIGHT, True)
    GtkLayerShell.set_margin(window, GtkLayerShell.Edge.TOP, 0)
    GtkLayerShell.set_margin(window, GtkLayerShell.Edge.BOTTOM, 0)
    GtkLayerShell.set_margin(window, GtkLayerShell.Edge.LEFT, 0)
    GtkLayerShell.set_margin(window, GtkLayerShell.Edge.RIGHT, 0)
    GtkLayerShell.set_exclusive_zone(window, -1)
    GtkLayerShell.set_keyboard_mode(window, GtkLayerShell.KeyboardMode.NONE)

    timer_id = {"id": 0}

    def set_timer(fps: int) -> None:
        if timer_id["id"]:
            try:
                GLib.source_remove(timer_id["id"])
            except Exception:
                pass
        timer_id["id"] = GLib.timeout_add(max(16, round(1000 / fps)), animation_tick)

    def ease_out_cubic(t: float) -> float:
        return 1.0 - (1.0 - t) ** 3

    def start_web_shoot() -> None:
        if state["mode"] != "idle":
            return
        state["mode"] = "web_shooting"
        state["shoot_start_time"] = time.monotonic()
        pixbuf = idle_frames[state["index"] % len(idle_frames)]
        attach_y = float(state["y"] + (canvas_h - pixbuf.get_height()) // 2 + 2)
        state["web_top_y"] = attach_y
        dist = max(1.0, attach_y)
        # Fast, snappy shot upward: ~1500 px/s, bounded [0.08, 0.30] seconds
        state["shoot_duration"] = max(0.08, min(0.30, dist / 1500.0))
        set_timer(60)

    def start_descent() -> None:
        state["mode"] = "descending"
        state["index"] = 0
        state["descent_start_time"] = time.monotonic()
        state["descent_start_y"] = state["y"]

        _screen_w, screen_h = get_output_size()
        target_y = round((screen_h - canvas_h) * 0.5)
        if target_y <= state["y"]:
            start_hanging()
            return

        state["descent_target_y"] = target_y
        dist = float(target_y - state["y"])
        # Smooth descent speed: ~350 px/s, bounded [0.6, 2.0] seconds
        state["descent_duration"] = max(0.6, min(2.0, dist / 350.0))
        set_timer(60)

    def start_hanging() -> None:
        state["mode"] = "hanging"
        set_timer(hanging_fps)
        area.queue_draw()

    def start_ascent() -> None:
        if state["mode"] != "hanging":
            return
        state["mode"] = "ascending"
        state["ascent_start_time"] = time.monotonic()
        state["ascent_start_y"] = state["y"]
        target_y = state.get("descent_start_y", 8)
        state["ascent_target_y"] = target_y
        dist = float(state["y"] - target_y)
        if dist <= 0:
            state["mode"] = "idle"
            state["index"] = 0
            update_input_region()
            set_timer(idle_fps)
            area.queue_draw()
            return
        # Swift ascent back up the web: ~700 px/s, bounded [0.4, 1.0] seconds
        state["ascent_duration"] = max(0.4, min(1.0, dist / 700.0))
        set_timer(60)

    def animation_tick() -> bool:
        mode = state["mode"]
        if mode == "idle":
            state["index"] = (state["index"] + 1) % len(idle_frames)
            area.queue_draw_area(
                max(0, int(state["x"])),
                max(0, int(state["y"])),
                canvas_w,
                canvas_h,
            )
            return True

        if mode == "web_shooting":
            now = time.monotonic()
            elapsed = now - state["shoot_start_time"]
            duration = state["shoot_duration"]
            p = min(1.0, elapsed / duration) if duration > 0 else 1.0

            pixbuf = idle_frames[state["index"] % len(idle_frames)]
            attach_y = float(state["y"] + (canvas_h - pixbuf.get_height()) // 2 + 2)
            state["web_top_y"] = max(0.0, attach_y - attach_y * p)
            area.queue_draw()

            if p >= 1.0:
                state["web_top_y"] = 0.0
                start_descent()
            return True

        if mode == "descending":
            now = time.monotonic()
            elapsed = now - state["descent_start_time"]
            duration = state["descent_duration"]
            p = min(1.0, elapsed / duration) if duration > 0 else 1.0

            ease_p = ease_out_cubic(p)
            new_y = round(state["descent_start_y"] + (state["descent_target_y"] - state["descent_start_y"]) * ease_p)
            state["y"] = int(new_y)

            # Advance hanging frames smoothly based on elapsed time
            state["index"] = int(elapsed * hanging_fps) % len(hanging_frames)
            update_input_region()
            area.queue_draw()

            if p >= 1.0:
                state["y"] = state["descent_target_y"]
                update_input_region()
                start_hanging()
            return True

        if mode == "hanging":
            state["index"] = (state["index"] + 1) % len(hanging_frames)
            area.queue_draw()
            return True

        if mode == "ascending":
            now = time.monotonic()
            elapsed = now - state["ascent_start_time"]
            duration = state["ascent_duration"]
            p = min(1.0, elapsed / duration) if duration > 0 else 1.0

            ease_p = ease_out_cubic(p)
            new_y = round(state["ascent_start_y"] + (state["ascent_target_y"] - state["ascent_start_y"]) * ease_p)
            state["y"] = int(new_y)

            state["index"] = int(elapsed * hanging_fps) % len(hanging_frames)
            update_input_region()
            area.queue_draw()

            if p >= 1.0:
                state["y"] = state["ascent_target_y"]
                state["mode"] = "idle"
                state["index"] = 0
                update_input_region()
                set_timer(idle_fps)
                area.queue_draw()
            return True

        return True

    def on_button_press(_widget: object, event: object) -> bool:
        if event.button != 1:
            return False
        if state["mode"] in ("web_shooting", "descending", "ascending"):
            return True
        state["press_x"] = event.x
        state["press_y"] = event.y
        state["offset_x"] = event.x - state["x"]
        state["offset_y"] = event.y - state["y"]
        state["dragging"] = False
        return True

    def on_motion(_widget: object, event: object) -> bool:
        if not (event.state & Gdk.ModifierType.BUTTON1_MASK):
            return False
        if state["mode"] in ("web_shooting", "descending", "ascending"):
            return True
        dx = event.x - state["press_x"]
        dy = event.y - state["press_y"]
        if not state["dragging"]:
            if abs(dx) + abs(dy) < 4:
                return True
            state["dragging"] = True

        new_x = event.x - state["offset_x"]
        new_y = event.y - state["offset_y"]

        screen_w, screen_h = get_output_size()
        clamped_x = max(0, min(screen_w - canvas_w, int(round(new_x))))
        clamped_y = max(0, min(screen_h - canvas_h, int(round(new_y))))

        if clamped_x != state["x"] or clamped_y != state["y"]:
            state["x"] = clamped_x
            state["y"] = clamped_y
            update_input_region()
            area.queue_draw()
        return True

    def on_button_release(_widget: object, event: object) -> bool:
        if event.button != 1:
            return False
        if state["mode"] in ("web_shooting", "descending", "ascending"):
            return True
        if not state["dragging"]:
            if state["mode"] == "idle":
                start_web_shoot()
            elif state["mode"] == "hanging":
                start_ascent()
        state["dragging"] = False
        return True

    area.connect("button-press-event", on_button_press)
    area.connect("motion-notify-event", on_motion)
    area.connect("button-release-event", on_button_release)

    def on_size_allocate(_widget: object, alloc: Gdk.Rectangle) -> None:
        if alloc.width <= 1 or alloc.height <= 1:
            return
        if not state["initialized"]:
            state["initialized"] = True
            state["x"] = max(0, alloc.width - canvas_w - 12)
            state["y"] = 8
            update_input_region()
            area.queue_draw()
        elif state["mode"] == "descending":
            state["descent_target_y"] = round((alloc.height - canvas_h) * 0.5)
        elif state["mode"] == "ascending":
            pass
        else:
            new_x = max(0, min(alloc.width - canvas_w, state["x"]))
            new_y = max(0, min(alloc.height - canvas_h, state["y"]))
            if new_x != state["x"] or new_y != state["y"]:
                state["x"] = new_x
                state["y"] = new_y
                update_input_region()
                area.queue_draw()

    area.connect("size-allocate", on_size_allocate)
    window.connect("realize", lambda *_args: update_input_region())

    window.connect("destroy", lambda *_args: Gtk.main_quit())
    window.show_all()
    update_input_region()
    set_timer(idle_fps)
    try:
        Gtk.main()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
