AVERNO — Food Consequences
Standalone Installer (no CDModManager needed)
==============================================

REQUIREMENTS
------------
Python 3.10 or newer
  Download: https://python.org/downloads

lz4 library (install once):
  Open a terminal and run:
  pip install lz4


USAGE
-----

Interactive mode (recommended for first time):
  python averno_apply.py

Direct apply:
  python averno_apply.py --preset adventure
  python averno_apply.py --preset survival
  python averno_apply.py --preset iron_gut

Restore vanilla:
  python averno_apply.py --restore

Check current state:
  python averno_apply.py --status


PRESETS
-------
Adventure  — Poison DoT + nutritional benefit. Nuanced.
Survival   — Double poison stack. Clearly dangerous.
Iron Gut   — Poison + Drunken. You asked for it.


GAME PATH
---------
The script auto-detects common Steam paths.
If your game is elsewhere, it will ask you the first time.
Your path is saved to config.json for future use.


UNINSTALL
---------
Run:  python averno_apply.py --restore

Or manually: delete the folder
  Crimson Desert/0036/


NOTES
-----
- Close the game before applying
- Compatible with other mods that don't touch skill.pabgb
- Safe to re-run — restores automatically before each apply
- Timestamps are preserved (game validation requirement)


SOURCE
------
https://github.com/claramercury/-cd-food-consequences
https://www.nexusmods.com/crimsondesert/mods/268
