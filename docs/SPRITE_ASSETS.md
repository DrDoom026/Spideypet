# Sprite asset inventory

- Head-turn sheet: 2048×43 RGBA; 76 extracted frames on 27×43 transparent canvases.
- Hanging sheet: 2048×40 RGBA; 77 extracted frames on 27×40 transparent canvases.
- Source sheets are preserved unchanged. The extraction code used non-transparent horizontal runs separated by fully transparent vertical gutters.
- Contact sheets: `head_turn_contact_sheet.png`, `hanging_contact_sheet.png`; animated preview: `hanging_preview.gif`.

Frame boundaries are inferred from transparency gutters. Inspect the contact sheet before changing frame timing or selecting blink frames.
