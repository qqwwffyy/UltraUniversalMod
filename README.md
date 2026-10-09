# UltraUniversalMod

UltraUniversalMod is a free, source-available utility mod for Ren'Py games. Version **0.1.0** provides an in-game interface for inspecting game data, reviewing dialogue and choices, managing saves, and adjusting selected presentation options. The mod interface has independent Russian and English translations.

## Installation

1. Download `UltraUniversalMod-v0.1.0.zip` from the [GitHub releases page](https://github.com/qqwwffyy/UltraUniversalMod/releases).
2. Extract the archive into the game's `game/` directory. The resulting path must be `game/UltraUniversalMod/`.
3. Start the game and press **F5** to open or close UltraUniversalMod. **Esc** also closes its open interface.

The archive contains source `.rpy` files. Ren'Py compiles them when the game starts; no manual compilation is required. Back up your game saves before using any save-management or rollback tools.

## Interface

| Tab | Available tools |
| --- | --- |
| Home | Feature overview, version, and a persistent **RU / EN** switch for the mod interface. |
| Search | Search supported game variables, values, and labels; inspect and edit supported values. |
| Dialogues | Browse and search recorded dialogue, filter speakers, and export selected character lines. |
| Saves | Browse slots and screenshots, name saves and pages, and copy, move, load, or delete saves. |
| Timeline | Review recorded choices and available alternatives; use checkpoints and a return point when available. |
| Gallery | Inspect gallery availability and select an unlock mode. Availability depends on the host game. |
| Settings | Configure hints, quick menu, rollback, dialogue presentation, font, and text size. |
| Updates | Version, author, and official project/community links. |

The language switch changes only UltraUniversalMod's interface. It does not change the game's language or translate game content. During gameplay, **Alt+C** shows available choices and **Alt+A** shows conditions for the next branch when that information is available.

## Compatibility

Version 0.1.0 was tested with **Ren'Py 8.5.2** in **The Beach House 0.2** on Windows. Game-specific scripts, custom save systems, gallery implementations, and older or newer Ren'Py versions can behave differently; compatibility with those environments has not been verified. The mod uses the game's normal Ren'Py save location for its settings and features.

## Project and communities

- [Source code, releases, and updates](https://github.com/qqwwffyy/UltraUniversalMod)
- [International Discord community](https://discord.gg/BSzJebe8M)
- [Russian Telegram community](https://t.me/+kd6BEw6gD-o5Y2Nk)

## License and fonts

Author: **qqwwffyy**. Copyright © 2026 qqwwffyy. All rights reserved. UltraUniversalMod's terms are in [LICENSE](LICENSE). The bundled fonts have separate licenses and notices in [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md); the full font license texts are distributed with the mod under `UltraUniversalMod/licenses/`.
