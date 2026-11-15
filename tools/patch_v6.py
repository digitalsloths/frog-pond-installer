#!/usr/bin/env python3
"""Patch original Frog Pond V5 source. Stops on unexpected source changes."""
import pathlib,sys,zipfile
src=pathlib.Path(sys.argv[1]); dst=pathlib.Path(sys.argv[2])
with zipfile.ZipFile(src) as z:
    files=[n for n in z.namelist() if n.endswith('.ino')]
    assert len(files)==1,files
    for n in z.namelist():
        p=pathlib.PurePosixPath(n)
        if p.is_absolute() or '..' in p.parts: raise ValueError('unsafe ZIP path')
    z.extractall(dst)
sketch=dst/files[0]; s=sketch.read_text()
def fix(old,new,what):
    global s
    if s.count(old)!=1: raise ValueError(f'{what}: expected one match, found {s.count(old)}')
    s=s.replace(old,new,1)
fix('uint32_t downAt = 0, lastActive = 0, lastFrame = 0;','uint32_t downAt = 0, lastActive = 0, lastFrame = 0;\nuint32_t touchReleasedAt = 0;', 'touch state')
a=s.index('void changeScreen(int direction) {'); b=s.index('\nbool inside(',a)
s=s[:a]+'''void changeScreen(int direction) {
  // Left swipe goes to Personalize, right swipe goes to Games / Settings.
  if (screen == FACE) {
    if (direction > 0) openScreen(PERSONALIZE);
    else if (direction < 0) openScreen(APPS);
  } else if (screen == PERSONALIZE) {
    if (direction < 0) openScreen(FACE);
  } else if (screen == APPS) {
    if (direction > 0) openScreen(FACE);
  } else if (screen == SETTINGS) {
    if (direction > 0) openScreen(APPS);
  } else if (screen == CLOCK || screen == COUNTER_APP || screen == TIMER_APP) {
    if (direction > 0) openScreen(SETTINGS);
  } else if (screen == GAMES) {
    if (direction > 0) openScreen(APPS);
  }
}'''+s[b:]
fix('  bool down = readTouch(x, y);\n  if (down && !fingerDown) {','''  bool down = readTouch(x, y);
  // Ignore brief loss of contact to avoid repeated taps on a held arrow.
  if (down) touchReleasedAt = 0;
  else if (fingerDown) {
    if (!touchReleasedAt) touchReleasedAt = now;
    if ((uint32_t)(now - touchReleasedAt) < 65) return;
  }
  if (down && !fingerDown) {''','debounced release')
fix('  centeredButton(165,433,136,29,"BACK",0x45E8);','  centered("SWIPE RIGHT TO RETURN",233,444,1,0xB6B5);','remove back button')
fix('    } else if (inside(x,y,145,426,175,40)) openScreen(FACE);','    }','remove back touch')
fix('  } else if (screen == PERSONALIZE) {\n    if (inside(x,y,65,195,80,65))','''  } else if (screen == PERSONALIZE) {
    // One interaction per tap even if the touchscreen contact is noisy.
    static uint32_t lastPickerTapAt = 0;
    uint32_t t = millis();
    if (lastPickerTapAt && (uint32_t)(t-lastPickerTapAt) < 250) return;
    lastPickerTapAt = t;
    if (inside(x,y,65,195,80,65))''','picker cooldown')
fix('else if (inside(x,y,65,300,80,65))','else if (inside(x,y,50,280,115,100))','hat previous target')
fix('else if (inside(x,y,320,300,85,65))','else if (inside(x,y,300,280,115,100))','hat next target')
fix('      prefs.putUChar("frogColor", selectedFrogColor);\n      prefs.putUChar("frogHat", selectedFrogHat);','''      size_t colorBytes = prefs.putUChar("frogColor", selectedFrogColor);
      size_t hatBytes = prefs.putUChar("frogHat", selectedFrogHat);
      Serial.printf("Saved style to flash: color=%u hat=%u\\n",(unsigned)colorBytes,(unsigned)hatBytes);''','persist selected style')
fix('  centeredButton(160,385,146,41,personalizeSavedUntil > millis() ? "SAVED!" : "SAVE",GREEN);','''  centeredButton(160,385,146,41,personalizeSavedUntil > millis() ? "SAVED!" : "SAVE",GREEN);
  if (personalizeSavedUntil > millis()) centered("STYLE SAVED",233,426,1,WHITE);''','save confirmation')
sketch.write_text(s)
print('V6 patch applied to',sketch)
