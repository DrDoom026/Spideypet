#!/usr/bin/env python3
"""SpiderPet entry point: Windows uses Qt; Linux/Omarchy uses GTK + GtkLayerShell."""
import sys

if sys.platform == "win32":
    from spiderpet.windows_app import main
else:
    from spiderpet.application import main

if __name__ == "__main__":
    raise SystemExit(main())
