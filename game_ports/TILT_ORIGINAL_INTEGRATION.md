# Original Tilt-a-Tron game integration into Frog Pond

Upstream repository: https://github.com/PartiallyFrozen/tilt-a-tron
Pinned upstream commit: e859d481604b86eeb40def6be552b4338ed0f21e
License: MIT. Copyright (c) 2026 PartiallyFrozen; retain attribution.

## Imported original code
Original eleven game C sources: upstream/tilt-a-tron/games/
Original rendering/runtime components: upstream/tilt-a-tron/components/
Original API contract: upstream/tilt-a-tron/components/tat_api/include/tat/tat_api.h

The compatibility-audit workflow verifies that the eleven imported game C sources
match the pinned upstream byte for byte, host-compiles them, and cross-compiles
all eleven into original Xtensa .tat game packages with their full PNG/icon assets.

IMPORTANT: .tat packages are NOT executable by Frog Pond V21. Do not offer them
as a Frog Pond flash release. The current V21 Arduino game shell does not contain
Tilt-a-Tron's game loader or compatible tat_api_t host implementation.

## Required runtime integration
- Graphics: original Canvas/Presenter indexed 233x233 and 155x155 RGB565 drawing;
  preserve palette, alpha, round-screen clipping, original fonts and sprite scale.
- Sprite assets: original lodepng PNG loader and per-frame positioning.
- Rotation: original polar tables and rotated-canvas presentation on PSRAM.
- Motion: corrected QMI8658 gravity/gyro and CST9217 touchscreen coordinates.
- Audio: original SQUARE, TRIANGLE and NOISE tones via existing ES8311 codec.
- Persistence: per-game save keys scoped in NVS, separate from Frog Pond state.
- Lifecycle: original tat_game_t begin/update/draw/leave/unload/redraw callbacks.
- Loader: a validated ESP-IDF TAT package loader port or a static native registry
  with distinct symbols for each game's tat_game_t descriptor.
- Pause: top-edge swipe -> Resume / Restart / Exit to Games, preserving menu page.
- Retain Frog Pond home, hats, steps, SD backgrounds, Time/Date and Pocket Watch.

## Exact requested menu order
1 Echo (echo); 2 Starfall (starfall); 3 Radar (radar);
4 Marble Maze (maze); 5 Grand Prix (racer); 6 Tilt-a-Tris (tiltatris);
7 Sleepy Star (star); 8 Pin Drop (pindrop); 9 Breakout (breakout);
10 Skater Girlz (skatergirlz); 11 Sky Jump (jump).
Four entries per page across three pages, with navigation and page indicator.

## Release gate
All eleven must launch with their original graphics, touch/tilt controls,
correct sprite/PNG assets, audio and saved scores, and exit via the shared menu.
Build and physical testing must preserve all existing Frog Pond features.

Current status: original sources, graphics modules, host compilation, and
Xtensa TAT packages imported and validated. A native Arduino TAT API 1.3
compatibility host now links all eleven original C game modules into one
experimental Frog Pond firmware using static game descriptors.

Implemented in the experimental branch:
- Original indexed canvases (233x233 and 155x155), RGB565 presentation and rotation
- Sprite PNG decoding, transparent sprites and original 5x7 font
- Original game update/draw/enter/leave/unload lifecycle and game-scoped NVS saves
- QMI8658 accelerometer/gyroscope samples and corrected CST9217 touch events
- ES8311 stereo 16-kHz square/triangle/noise synthesis via a shared queued I2S task
- Pause/restart/exit controls, original menu ordering and per-game assets
- Game TAT API entry points for polar tables, sheets, banners and drawing

Caveats: on-hardware playability and visual parity are NOT YET VERIFIED.
Original in-game menu row rendering is replaced by Frog Pond's universal
pause overlay; its menu functions are compatibility shims, not a complete
replica of upstream console settings. The gyro orientation and precise
touch/pause ergonomics need hardware testing. Production browser firmware
remains V21; this branch intentionally does not deploy a public flasher.