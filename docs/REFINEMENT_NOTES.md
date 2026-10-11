# SpiderPet refinement notes

This update responds to the first live desktop test.

- Default scale reduced from 2x to 1.75x; nearest-neighbour scaling remains in-memory only.
- Idle/head-turn rate defaults to 12 FPS.
- Hanging sequence defaults to 24 FPS.
- Left-click and release (without meaningful movement) triggers hanging.
- Left-button drag moves the pet by updating GtkLayerShell top/left margins.
- The original sprite sheets and extracted frame files are not modified.
- No walking, sitting, stats, menus, package installs, sudo, system config changes, or Git operations were added.

Test on the user's Omarchy/Hyprland session. If Wayland compositor policy prevents runtime layer-shell margin repositioning, keep the original artwork intact and diagnose that behavior before changing the windowing approach.
