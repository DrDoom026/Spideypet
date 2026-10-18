# SpiderPet — Desktop Sprite Pet

SpiderPet is a small transparent desktop pet that reuses the supplied sprite assets. It has separate native desktop implementations for **Linux/Omarchy on Wayland** and **Windows 10/11**.

## Artwork

- `assets/sprites/SpiderMan_HeadTurn.png` and `SpiderMan_web.png` are retained unchanged.
- `assets/sprites/head_turn/` contains the 76 extracted idle/head-turn frames.
- `assets/sprites/hanging/` contains the 77 extracted hanging frames.
- The original sprite sheets and extracted PNG frames are not edited on disk. Scaling happens in memory with nearest-neighbour/fast interpolation.

## Current behavior

1. SpiderPet appears near the top-right of the primary display and loops the head-turn sequence as its idle animation.
2. Click the pet to shoot a web and descend toward the center of the primary display.
3. The pet loops the hanging sequence until clicked again, then ascends to its original vertical position and returns to idle.
4. Drag the pet with the left mouse button to reposition it. During the web/descent/ascent phases, mouse interactions are temporarily ignored.

The Windows build uses a transparent, always-on-top Qt sprite window plus a mouse-transparent web overlay, so the web line can be drawn without intentionally capturing clicks outside the pet. The pet is positioned relative to the desktop, not attached to the Windows taskbar.

## Windows 10/11

**Requirements:** 64-bit Python 3.10 or newer and an internet connection for the initial dependency installation.

1. Extract the project ZIP to a normal writable folder.
2. Double-click `setup_windows.bat`. It creates a local `.venv` and installs PySide6 Essentials.
3. Double-click `run_windows.bat` to launch SpiderPet.
4. To stop it, use `Ctrl+C` in the terminal window opened with the launcher, or end `python.exe` from Task Manager.

Manual setup from PowerShell in the project directory:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-windows.txt
.\.venv\Scripts\python.exe main.py
```

Optional scale and FPS settings in PowerShell:

```powershell
$env:SPIDERPET_SCALE = "2"
$env:SPIDERPET_IDLE_FPS = "12"
$env:SPIDERPET_HANGING_FPS = "24"
.\.venv\Scripts\python.exe main.py
```

The defaults are scale `1.75`, idle `12 FPS`, and hanging `24 FPS`. The scale is limited to `1.0`–`5.0`; FPS values are clamped by the application.

### Optional Windows autostart

After verifying the app works, press `Win+R`, enter `shell:startup`, and press Enter. Create a shortcut to `run_windows.bat` in the opened Startup folder. Remove that shortcut to disable autostart.

## Linux / Omarchy / Hyprland

The existing Linux implementation remains in `spiderpet/application.py` and uses GTK3, PyGObject, GdkPixbuf, Cairo and GtkLayerShell. Run it in the configured Omarchy environment with:

```bash
python main.py
```

Optional environment settings:

```bash
SPIDERPET_SCALE=3 SPIDERPET_IDLE_FPS=8 SPIDERPET_HANGING_FPS=15 python main.py
```

Windows uses PySide6 Essentials from `requirements-windows.txt`; Linux dependencies are system-provided by the existing Omarchy setup and are intentionally not replaced by the Windows requirements.

## Troubleshooting

- If Windows setup fails, confirm that 64-bit Python 3.10+ and the Python Launcher (`py`) are installed, then run `setup_windows.bat` again.
- If the pet is missing, make sure the `assets` folder stays next to `main.py` and the entire project ZIP was extracted.
- If the pet appears behind other windows, check Windows compatibility settings or whether another application forces an exclusive full-screen mode.
- The Windows implementation has been statically checked in this package, but it still needs a runtime smoke test on a real Windows desktop; this Linux environment cannot validate Windows window-manager behavior.
