#!/usr/bin/env python3
"""V18: after successful Personalize SAVE, return to Games/Apps/Settings main menu."""
from pathlib import Path
import sys
p=next(Path(sys.argv[1]).rglob("*.ino"))
s=p.read_text()
old="openScreen(FACE); // Save returns directly to the pond."
new="openScreen(APPS); // Save returns to the main Games / Apps / Settings menu."
if s.count(old)!=1:raise RuntimeError(f"Expected exactly one successful SAVE navigation; got {s.count(old)}")
s=s.replace(old,new)
if 'const char* labels[] = {"GAMES","APPS","SETTINGS"};' not in s:raise RuntimeError("Main menu order changed unexpectedly")
if 'prefs.getUChar("frogHat",255)' not in s:raise RuntimeError("Saved hat readback check missing")
p.write_text(s)
print("V18 verified Personalize SAVE navigates to Games / Apps / Settings only after successful NVS write.")
