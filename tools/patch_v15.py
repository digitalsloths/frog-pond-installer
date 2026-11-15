#!/usr/bin/env python3
"""V15: Fix 180-degree touch coordinate rotation on Waveshare 1.75 AMOLED."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
sources=list(root.rglob("*.ino"))
if len(sources)!=1: raise RuntimeError(f"Expected 1 sketch: {sources}")
path=sources[0]
s=path.read_text()
sig="bool readTouch(int &x, int &y) {"
a=s.find(sig)
if a<0:raise RuntimeError("readTouch signature not found")
b=s.index("{",a)
d=0
for i in range(b,len(s)):
    if s[i]=="{":d+=1
    elif s[i]=="}":
        d-=1
        if d==0:break
else:raise RuntimeError("Unbalanced readTouch function")
fn=s[a:i+1]
needle="  return true;"
if fn.count(needle)!=1:raise RuntimeError("Expected exactly 1 success return in readTouch")
fn=fn.replace(needle,"""  // CST9217 is mounted 180 degrees relative to the visible 466x466 canvas.
  // Photos confirm left arrow reports x~374 (actual x~91), and
  // Save at bottom reports y~38 (actual y~427).
  // Correct centrally so taps, swipes, games, and diagnostic crosshair agree.
  x = (SCREEN_SIZE - 1) - x;
  y = (SCREEN_SIZE - 1) - y;
  return true;""",1)
s=s[:a]+fn+s[i+1:]
assert s.count("x = (SCREEN_SIZE - 1) - x;")==1
assert s.count("y = (SCREEN_SIZE - 1) - y;")==1
for token in ["prefs.getUChar(\"frogHat\",255)","void drawPersonalize() {","HAT SAVE OK"]:
    if token not in s: raise RuntimeError("Prior feature unexpectedly missing: "+token)
path.write_text(s)
print("V15 corrected physical touch axes 180 degrees and preserved NVS Save")
