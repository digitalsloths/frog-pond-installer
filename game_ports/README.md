# Frog Pond game ports

The Frog Pond 1.75-inch Arduino firmware runs a different game runtime from
[PartiallyFrozen/tilt-a-tron](https://github.com/PartiallyFrozen/tilt-a-tron).

Frog Pond V21 includes a first native Arduino **Echo adaptation** built around
the upstream game's sequence-memory mechanic. The remaining ten titles appear
in the 4-per-page catalog but are intentionally marked unported.

The shared `frogpond_pause.h` gesture controller supports:
- A downward swipe starting in the top 36px of the active game
- Resume, restart, and Exit to Games actions
- Returning to the same catalog page

Upstream source: https://github.com/PartiallyFrozen/tilt-a-tron/tree/master/games/echo
Upstream copyright (c) 2026 PartiallyFrozen.
License: MIT (https://github.com/PartiallyFrozen/tilt-a-tron/blob/master/LICENSE).

The Echo adaptation is not a binary transplant of the Tilt-a-Tron game, and
does not yet reproduce its full graphics or sound. Do not label other titles
as playable until their own input, physics, drawing and save state are ported.
