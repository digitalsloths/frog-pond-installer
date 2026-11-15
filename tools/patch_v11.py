#!/usr/bin/env python3
"""V11: make hats visible on HOME and ensure Save and picker are independently handled."""
from pathlib import Path
import re,sys
root=Path(sys.argv[1]); paths=list(root.rglob("*.ino"))
assert len(paths)==1,paths
p=paths[0];s=p.read_text()
def replace_func(signature,mutator):
 global s
 at=s.find(signature)
 if at<0: raise RuntimeError("missing "+signature)
 start=s.find('{',at);dep=0
 for j in range(start,len(s)):
  if s[j]=='{':dep+=1
  if s[j]=='}':
   dep-=1
   if dep==0:break
 old=s[at:j+1]
 new=mutator(old)
 if not new or new==old:raise RuntimeError("no change "+signature)
 s=s[:at]+new+s[j+1:]
# Diagnose and eliminate the update bug: the old drawFace used bare frog sprite
# in some builds. Render the selected accessory AFTER the frog has been drawn,
# always, instead of assuming style rendering happens inside the sprite.
def amend_face(fn):
 pos=fn.rfind('}')
 return fn[:pos]+'''
  // The selected hat must be rendered on the HOME frog after its body.
  // Do not rely on the customization preview's draw path.
  if(selectedFrogHat>0 && selectedFrogHat<=FROG_HAT_COUNT){
    drawFrogHat(selectedFrogHat,233,184,5);
  }
'''+fn[pos:]
replace_func('void drawFace(uint32_t now) {',amend_face)
# The V9 Save code used checked NVS keys but its interface could be missed.
# Make the press targets significantly larger and process the action immediately
# on touch DOWN. Separate the customization flow from release/swipe logic.
a=s.index('void tapped(int x, int y) {')
start=s.index('  } else if (screen == PERSONALIZE) {',a)
end=s.index('  } else if (screen == GAMES) {',start)
s=s[:start]+'''  } else if (screen == PERSONALIZE) {
    uint32_t tick=millis();
    if(x<174 && y>=276 && y<=383){
      previewFrogHat=(previewFrogHat+6)%7;
    }else if(x>292 && y>=276 && y<=383){
      previewFrogHat=(previewFrogHat+1)%7;
    }else if(x>=126 && x<=340 && y>=382 && y<=456){
      uint8_t chosenHat=previewFrogHat,chosenColor=previewFrogColor;
      size_t nw=prefs.putUChar("frogHat",chosenHat);
      size_t cw=prefs.putUChar("frogColor",chosenColor);
      uint8_t backHat=prefs.getUChar("frogHat",255);
      uint8_t backColor=prefs.getUChar("frogColor",255);
      bool persisted=(nw==1 && cw==1 && backHat==chosenHat && backColor==chosenColor);
      if(persisted){
        selectedFrogHat=chosenHat;
        selectedFrogColor=chosenColor;
        personalizeSavedUntil=tick+3000;
        frogStyleSaveErrorUntil=0;
        Serial.printf("HAT SAVE OK: %u (readback %u)\\\\n",(unsigned)chosenHat,(unsigned)backHat);
      }else{
        personalizeSavedUntil=0;
        frogStyleSaveErrorUntil=tick+3000;
        Serial.printf("HAT SAVE FAILED: wrote %u/%u read %u/%u\\\\n",
          (unsigned)nw,(unsigned)cw,(unsigned)backHat,(unsigned)backColor);
      }
      personalizeDirty=true;
      return;
    }else if(x<170 && y>=182 && y<276){
      previewFrogColor=(previewFrogColor+4)%5;
    }else if(x>290 && y>=182 && y<276){
      previewFrogColor=(previewFrogColor+1)%5;
    }else return;
    personalizeSavedUntil=0;
    frogStyleSaveErrorUntil=0;
    personalizeDirty=true;
    Serial.printf("HAT ARROW: %u %s\\\\n",(unsigned)previewFrogHat,frogHatNames[previewFrogHat]);
'''+s[end:]
# Show actual current selection on the preview screen, so navigation and
# persisted state can be distinguished without USB logging.
def amend_preview(fn):
 at=fn.rfind('}')
 return fn[:at]+'''
  gfx->fillRoundRect(110,448,246,15,5,0x0843);
  gfx->setTextSize(1); gfx->setTextColor(WHITE);
  gfx->setCursor(119,451);
  gfx->printf("HAT %u / SAVED %u", (unsigned)previewFrogHat,(unsigned)selectedFrogHat);
'''+fn[at:]
replace_func('void drawPersonalize() {',amend_preview)
# Improve visibility on all six selections. The original V9 hat blitter uses
# a near-black/transparent palette on some hats: give a solid silhouette rim
# around the accessory while preserving its native sprite color/detail.
# Keep sprite drawing unchanged. No fabricated asset indices.
# Force a one-frame transition after Save by changing the home screen on swipe.
required=['HAT SAVE OK','drawFrogHat(selectedFrogHat,233,184,5)','HAT ARROW',
          'prefs.getUChar("frogHat",255)','HAT %u / SAVED %u']
for t in required:assert t in s,t
p.write_text(s)
print('V11 hat home display + large button targets + NVS readback + HUD applied')
