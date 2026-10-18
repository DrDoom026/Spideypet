"""Windows-native SpiderPet implementation using PySide6.

The Linux/Omarchy implementation remains in application.py. This version uses
one mouse-interactive sprite window and a separate mouse-transparent overlay
for the web line, so clicks outside the sprite pass through to other apps.
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent.parent
SPRITES_DIR = BASE_DIR / "assets" / "sprites"
IDLE_DIR = SPRITES_DIR / "head_turn"
HANGING_DIR = SPRITES_DIR / "hanging"


def main() -> int:
    try:
        from PySide6.QtCore import QPointF, Qt, QTimer
        from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
        from PySide6.QtWidgets import QApplication, QWidget
    except ImportError as exc:
        print(
            "SpiderPet on Windows needs PySide6. From the project folder, run:\n"
            "  py -m pip install -r requirements-windows.txt\n"
            f"Import detail: {exc}",
            file=sys.stderr,
        )
        return 2

    try:
        scale = max(1.0, min(float(os.environ.get("SPIDERPET_SCALE", "1.75")), 5.0))
        idle_fps = max(1, min(int(os.environ.get("SPIDERPET_IDLE_FPS", "12")), 24))
        hanging_fps = max(1, min(int(os.environ.get("SPIDERPET_HANGING_FPS", "24")), 30))
    except ValueError:
        print("Invalid SpiderPet scale/FPS environment value.", file=sys.stderr)
        return 2

    def frame_paths(folder: Path) -> list[Path]:
        return sorted(folder.glob("frame_*.png"))

    idle_paths = frame_paths(IDLE_DIR)
    hanging_paths = frame_paths(HANGING_DIR)
    if not idle_paths or not hanging_paths:
        print("SpiderPet sprite frames are missing. Check assets/sprites/.", file=sys.stderr)
        return 2

    # QPixmap requires a QGuiApplication/QApplication to exist before loading.
    app = QApplication(sys.argv[:1])
    app.setApplicationName("SpiderPet")
    app.setQuitOnLastWindowClosed(True)

    def load_frames(paths: list[Path]) -> list[QPixmap]:
        loaded: list[QPixmap] = []
        for path in paths:
            pixmap = QPixmap(str(path))
            if pixmap.isNull():
                raise RuntimeError(f"Could not read sprite frame: {path}")
            width = max(1, round(pixmap.width() * scale))
            height = max(1, round(pixmap.height() * scale))
            # FastTransformation preserves the supplied pixel-art edges.
            loaded.append(
                pixmap.scaled(
                    width,
                    height,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.FastTransformation,
                )
            )
        return loaded

    try:
        idle_frames = load_frames(idle_paths)
        hanging_frames = load_frames(hanging_paths)
    except (OSError, RuntimeError) as exc:
        print(f"Could not load SpiderPet sprite assets: {exc}", file=sys.stderr)
        return 2

    canvas_w = max(frame.width() for frame in idle_frames + hanging_frames)
    canvas_h = max(frame.height() for frame in idle_frames + hanging_frames)

    primary = app.primaryScreen()
    if primary is None:
        print("SpiderPet could not find a Windows display.", file=sys.stderr)
        return 2

    # Use the virtual desktop for the transparent drawing overlay, while
    # positioning the pet initially on the primary monitor.
    desktop = primary.virtualGeometry()
    primary_geometry = primary.geometry()
    primary_left = primary_geometry.x() - desktop.x()
    primary_top = primary_geometry.y() - desktop.y()
    primary_width = primary_geometry.width()
    primary_height = primary_geometry.height()

    state: dict[str, Any] = {
        "mode": "idle",
        "index": 0,
        "press_x": 0.0,
        "press_y": 0.0,
        "offset_x": 0.0,
        "offset_y": 0.0,
        "dragging": False,
        "x": max(0, primary_left + primary_width - canvas_w - 12),
        "y": max(0, primary_top + 8),
        "web_top_y": float(primary_top + 10),
        "shoot_start_time": 0.0,
        "shoot_duration": 0.0,
        "descent_start_time": 0.0,
        "descent_duration": 0.0,
        "descent_start_y": max(0, primary_top + 8),
        "descent_target_y": max(0, primary_top + 8),
        "ascent_start_time": 0.0,
        "ascent_duration": 0.0,
        "ascent_start_y": max(0, primary_top + 8),
        "ascent_target_y": max(0, primary_top + 8),
    }

    def current_frames() -> list[QPixmap]:
        if state["mode"] in ("descending", "hanging", "ascending"):
            return hanging_frames
        return idle_frames

    def attach_y() -> float:
        frames = current_frames()
        frame = frames[state["index"] % len(frames)]
        return float(state["y"] + (canvas_h - frame.height()) // 2 + 2)

    class WebOverlay(QWidget):
        """Narrow, transparent, mouse-pass-through window for the web line."""

        def __init__(self) -> None:
            flags = (
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.WindowDoesNotAcceptFocus
                | Qt.WindowType.Tool
            )
            super().__init__(None, flags)
            self.setWindowTitle("SpiderPet Web Overlay")
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self._line_visible = False
            self.setGeometry(desktop.x(), desktop.y(), 8, 1)
            self.hide()

        def refresh_line(self) -> None:
            mode = state["mode"]
            if mode not in ("web_shooting", "descending", "hanging", "ascending"):
                self._line_visible = False
                self.hide()
                return

            y_bottom = attach_y()
            y_top = float(state["web_top_y"]) if mode == "web_shooting" else 0.0
            if y_bottom <= y_top:
                self._line_visible = False
                self.hide()
                return

            line_x = float(state["x"]) + canvas_w / 2.0
            line_height = max(1, int(round(y_bottom - y_top)))
            self.setGeometry(
                desktop.x() + int(round(line_x)) - 4,
                desktop.y() + int(round(y_top)),
                8,
                line_height,
            )
            if not self._line_visible:
                self.show()
                self._line_visible = True
            self.update()
            # The pet must stay above the web line where the two meet.
            pet.raise_()

        def paintEvent(self, _event: object) -> None:  # noqa: N802 - Qt event name
            painter = QPainter(self)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

            if not self._line_visible:
                painter.end()
                return

            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            line_x = self.width() / 2.0
            line_y = float(self.height())
            painter.setPen(QPen(QColor(0, 0, 0, 89), 2.5))
            painter.drawLine(QPointF(line_x, 0.0), QPointF(line_x, line_y))
            painter.setPen(QPen(QColor(242, 245, 255, 242), 1.2))
            painter.drawLine(QPointF(line_x, 0.0), QPointF(line_x, line_y))
            painter.end()

    class PetWindow(QWidget):
        """Small, transparent and interactive window containing the sprite."""

        def __init__(self) -> None:
            flags = (
                Qt.WindowType.FramelessWindowHint
                | Qt.WindowType.WindowStaysOnTopHint
                | Qt.WindowType.WindowDoesNotAcceptFocus
                | Qt.WindowType.Tool
            )
            super().__init__(None, flags)
            self.setWindowTitle("SpiderPet")
            self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
            self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
            self.setMouseTracking(True)
            self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            self.resize(canvas_w, canvas_h)
            self._move_to_state()

        def _move_to_state(self) -> None:
            self.move(desktop.x() + int(state["x"]), desktop.y() + int(state["y"]))

        def paintEvent(self, _event: object) -> None:  # noqa: N802 - Qt event name
            frames = current_frames()
            pixmap = frames[state["index"] % len(frames)]
            x = (canvas_w - pixmap.width()) // 2
            y = (canvas_h - pixmap.height()) // 2
            painter = QPainter(self)
            # Transparent pixels in the next sprite frame must replace the old
            # frame, rather than being composited over it.
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.drawPixmap(x, y, pixmap)
            painter.end()

        def mousePressEvent(self, event: object) -> None:  # noqa: N802 - Qt event name
            if event.button() != Qt.MouseButton.LeftButton:
                event.ignore()
                return
            if state["mode"] in ("web_shooting", "descending", "ascending"):
                event.accept()
                return
            local = event.position()
            global_pos = event.globalPosition()
            state["press_x"] = float(global_pos.x() - desktop.x())
            state["press_y"] = float(global_pos.y() - desktop.y())
            state["offset_x"] = float(local.x())
            state["offset_y"] = float(local.y())
            state["dragging"] = False
            event.accept()

        def mouseMoveEvent(self, event: object) -> None:  # noqa: N802 - Qt event name
            if not (event.buttons() & Qt.MouseButton.LeftButton):
                event.ignore()
                return
            if state["mode"] in ("web_shooting", "descending", "ascending"):
                event.accept()
                return

            global_pos = event.globalPosition()
            pointer_x = float(global_pos.x() - desktop.x())
            pointer_y = float(global_pos.y() - desktop.y())
            dx = pointer_x - state["press_x"]
            dy = pointer_y - state["press_y"]
            if not state["dragging"]:
                if abs(dx) + abs(dy) < 4:
                    event.accept()
                    return
                state["dragging"] = True

            new_x = pointer_x - state["offset_x"]
            new_y = pointer_y - state["offset_y"]
            clamped_x = max(0, min(desktop.width() - canvas_w, round(new_x)))
            clamped_y = max(0, min(desktop.height() - canvas_h, round(new_y)))
            if clamped_x != state["x"] or clamped_y != state["y"]:
                state["x"] = int(clamped_x)
                state["y"] = int(clamped_y)
                self._move_to_state()
                overlay.update()
            event.accept()

        def mouseReleaseEvent(self, event: object) -> None:  # noqa: N802 - Qt event name
            if event.button() != Qt.MouseButton.LeftButton:
                event.ignore()
                return
            if state["mode"] in ("web_shooting", "descending", "ascending"):
                event.accept()
                return
            if not state["dragging"]:
                if state["mode"] == "idle":
                    start_web_shoot()
                elif state["mode"] == "hanging":
                    start_ascent()
            state["dragging"] = False
            event.accept()

    overlay = WebOverlay()
    pet = PetWindow()
    timer = QTimer()
    timer.setTimerType(Qt.TimerType.PreciseTimer)

    def redraw() -> None:
        pet.update()
        overlay.refresh_line()

    def set_timer(fps: int) -> None:
        timer.stop()
        timer.setInterval(max(16, round(1000 / fps)))
        timer.start()

    def ease_out_cubic(t: float) -> float:
        return 1.0 - (1.0 - t) ** 3

    def start_hanging() -> None:
        state["mode"] = "hanging"
        set_timer(hanging_fps)
        redraw()

    def start_descent() -> None:
        state["mode"] = "descending"
        state["index"] = 0
        state["descent_start_time"] = time.monotonic()
        state["descent_start_y"] = state["y"]
        target_y = round(primary_top + (primary_height - canvas_h) * 0.5)
        if target_y <= state["y"]:
            start_hanging()
            return
        state["descent_target_y"] = target_y
        dist = float(target_y - state["y"])
        state["descent_duration"] = max(0.6, min(2.0, dist / 350.0))
        set_timer(60)

    def start_web_shoot() -> None:
        if state["mode"] != "idle":
            return
        state["mode"] = "web_shooting"
        state["shoot_start_time"] = time.monotonic()
        state["web_top_y"] = attach_y()
        dist = max(1.0, state["web_top_y"])
        state["shoot_duration"] = max(0.08, min(0.30, dist / 1500.0))
        set_timer(60)
        redraw()

    def start_ascent() -> None:
        if state["mode"] != "hanging":
            return
        state["mode"] = "ascending"
        state["ascent_start_time"] = time.monotonic()
        state["ascent_start_y"] = state["y"]
        target_y = state.get("descent_start_y", primary_top + 8)
        state["ascent_target_y"] = target_y
        dist = float(state["y"] - target_y)
        if dist <= 0:
            state["mode"] = "idle"
            state["index"] = 0
            set_timer(idle_fps)
            redraw()
            return
        state["ascent_duration"] = max(0.4, min(1.0, dist / 700.0))
        set_timer(60)
        redraw()

    def animation_tick() -> None:
        mode = state["mode"]
        if mode == "idle":
            state["index"] = (state["index"] + 1) % len(idle_frames)
            pet.update()
            return

        if mode == "web_shooting":
            now = time.monotonic()
            elapsed = now - state["shoot_start_time"]
            duration = state["shoot_duration"]
            p = min(1.0, elapsed / duration) if duration > 0 else 1.0
            state["web_top_y"] = max(0.0, attach_y() - attach_y() * p)
            redraw()
            if p >= 1.0:
                state["web_top_y"] = 0.0
                start_descent()
            return

        if mode == "descending":
            elapsed = time.monotonic() - state["descent_start_time"]
            duration = state["descent_duration"]
            p = min(1.0, elapsed / duration) if duration > 0 else 1.0
            eased = ease_out_cubic(p)
            state["y"] = int(round(
                state["descent_start_y"]
                + (state["descent_target_y"] - state["descent_start_y"]) * eased
            ))
            state["index"] = int(elapsed * hanging_fps) % len(hanging_frames)
            pet._move_to_state()
            redraw()
            if p >= 1.0:
                state["y"] = state["descent_target_y"]
                pet._move_to_state()
                start_hanging()
            return

        if mode == "hanging":
            state["index"] = (state["index"] + 1) % len(hanging_frames)
            redraw()
            return

        if mode == "ascending":
            elapsed = time.monotonic() - state["ascent_start_time"]
            duration = state["ascent_duration"]
            p = min(1.0, elapsed / duration) if duration > 0 else 1.0
            eased = ease_out_cubic(p)
            state["y"] = int(round(
                state["ascent_start_y"]
                + (state["ascent_target_y"] - state["ascent_start_y"]) * eased
            ))
            state["index"] = int(elapsed * hanging_fps) % len(hanging_frames)
            pet._move_to_state()
            redraw()
            if p >= 1.0:
                state["y"] = state["ascent_target_y"]
                state["mode"] = "idle"
                state["index"] = 0
                pet._move_to_state()
                set_timer(idle_fps)
                redraw()

    timer.timeout.connect(animation_tick)

    # The narrow line window remains mouse-transparent. Add the native Windows
    # extended style as well, so OS input reliably reaches windows underneath.
    try:
        import ctypes

        hwnd = ctypes.c_void_p(int(overlay.winId()))
        user32 = ctypes.windll.user32
        get_window_long = user32.GetWindowLongPtrW
        set_window_long = user32.SetWindowLongPtrW
        get_window_long.argtypes = (ctypes.c_void_p, ctypes.c_int)
        get_window_long.restype = ctypes.c_ssize_t
        set_window_long.argtypes = (ctypes.c_void_p, ctypes.c_int, ctypes.c_ssize_t)
        set_window_long.restype = ctypes.c_ssize_t
        set_window_pos = user32.SetWindowPos
        set_window_pos.argtypes = (
            ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int, ctypes.c_int,
            ctypes.c_int, ctypes.c_int, ctypes.c_uint,
        )
        set_window_pos.restype = ctypes.c_int
        exstyle_index = -20  # GWL_EXSTYLE
        exstyle = int(get_window_long(hwnd, exstyle_index))
        # WS_EX_TRANSPARENT | WS_EX_LAYERED | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE
        exstyle |= 0x00000020 | 0x00080000 | 0x00000080 | 0x08000000
        set_window_long(hwnd, exstyle_index, exstyle)
        # Ask Windows to refresh the cached extended styles without moving or
        # resizing the transparent overlay.
        set_window_pos(hwnd, None, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0004 | 0x0010 | 0x0020)
    except (AttributeError, OSError, TypeError, ValueError) as exc:
        print(
            "Warning: could not apply the native Windows mouse-pass-through "
            f"style to the web overlay: {exc}",
            file=sys.stderr,
        )

    pet.show()
    pet.raise_()
    set_timer(idle_fps)

    try:
        return app.exec()
    except KeyboardInterrupt:
        return 0
