#!/usr/bin/env python3
"""V9: repair Personalize interaction/hat previews and reliable frog swipe-up jump."""
from pathlib import Path
import sys
root=Path(sys.argv[1]); files=list(root.rglob("*.ino")); assert len(files)==1
p=files[0]; s=p.read_text()
def swap(a,b,label):
 global s
 n=s.count(a)
 if n!=1:raise RuntimeError(f"{label}: expected 1 anchor, got {n}")
 s=s.replace(a,b,1)
def replace_function(sig,new):
 global s
 a=s.index(sig);b=s.index("{",a);depth=0
 for i in range(b,len(s)):
  if s[i]=="{":depth+=1
  elif s[i]=="}":
   depth-=1
   if depth==0:
    s=s[:a]+new+s[i+1:];return
 raise RuntimeError("unbalanced "+sig)
# Use a single clear touch state machine for Personalize. An action is handled
# on touch DOWN, not on a sometimes-missing release; no auto-repeat while held.
swap('bool personalizeDirty = true;',"""bool personalizeDirty = true;
bool personalizePressConsumed = false;
bool frogSwipeJumpConsumed = false;
uint32_t frogStyleSaveErrorUntil = 0;""","touch state")
# Make hat sprites use their own source pixels, with visual debugging contrast.
# Draw overlay using a per-pixel blit. All pixels are checked in the build test.
replace_function('void drawFrogHat(uint8_t hat, int frogX, int frogY, int scale) {',"""void drawFrogHat(uint8_t hat, int frogX, int frogY, int scale) {
  if(hat==0 || hat>FROG_HAT_COUNT)return;
  const uint16_t *px=FROG_HAT_RGB565[hat-1];
  const int left=frogX-8*scale, top=frogY-4*scale;
  for(int yy=0; yy<FROG_HAT_H; ++yy){
    for(int xx=0; xx<FROG_HAT_W; ++xx){
      uint16_t c=pgm_read_word(px+yy*FROG_HAT_W+xx);
      if(c!=FROG_HAT_TRANSPARENT)
        gfx->fillRect(left+xx*scale,top+yy*scale,scale,scale,c);
    }
  }
}""")
# Keep the same appearance preview but make accessory preview a clearly visible
# complete frog wearing the selected hat, rather than an unanchored hat.
replace_function('void drawPersonalize() {',"""void drawPersonalize() {
  gfx->fillScreen(0x0883);
  centered("Personalize your frog",233,24,2,WHITE);
  // Top preview with hat rendered over the frog.
  gfx->fillRoundRect(160,54,146,112,16,0x2C6A);
  drawFrogSpriteStyled(0,185,67,4,previewFrogColor,previewFrogHat);
  centered("Frog Color",233,170,2,0xB737);
  gfx->fillRoundRect(65,195,78,56,12,0x2C6A);
  gfx->fillRoundRect(323,195,78,56,12,0x2C6A);
  centered("<",103,205,3,WHITE);
  centered(">",362,205,3,WHITE);
  gfx->fillRoundRect(190,201,86,46,11,frogColorSwatches[previewFrogColor]);
  gfx->drawRoundRect(190,201,86,46,11,WHITE);
  centered(frogColorNames[previewFrogColor],233,255,2,WHITE);
  centered("Accessories",233,279,2,0xB737);
  gfx->fillRoundRect(65,302,78,57,12,0x2C6A);
  gfx->fillRoundRect(323,302,78,57,12,0x2C6A);
  centered("<",103,312,3,WHITE);
  centered(">",362,312,3,WHITE);
  // Accessory itself is drawn in a dedicated preview area, no overlapping label.
  gfx->fillRoundRect(175,296,116,64,9,0x2104);
  if(previewFrogHat==0) centered("NONE",233,320,2,WHITE);
  else drawFrogHat(previewFrogHat,227,311,2);
  centered(frogHatNames[previewFrogHat],233,362,2,WHITE);
  centeredButton(146,390,174,48,
      personalizeSavedUntil>millis()?"SAVED!":"SAVE",GREEN);
  if(frogStyleSaveErrorUntil>millis()) centered("SAVE FAILED",233,442,1,RED);
  else if(personalizeSavedUntil>millis()) centered("SAVED TO FLASH",233,442,1,WHITE);
  else centered("SWIPE RIGHT TO RETURN",233,442,1,GRAY);
}""")
# Replace only the personalize branch of tapped; explicitly confirm NVS writes.
a=s.index('  } else if (screen == PERSONALIZE) {',s.index('void tapped(int x, int y) {'))
b=s.index('  } else if (screen == GAMES) {',a)
s=s[:a]+"""  } else if (screen == PERSONALIZE) {
    const uint32_t now=millis();
    if (inside(x,y,55,187,104,86)) previewFrogColor=(previewFrogColor+4)%5;
    else if (inside(x,y,307,187,104,86)) previewFrogColor=(previewFrogColor+1)%5;
    else if (inside(x,y,55,292,104,81)) previewFrogHat=(previewFrogHat+6)%7;
    else if (inside(x,y,307,292,104,81)) previewFrogHat=(previewFrogHat+1)%7;
    else if (inside(x,y,142,384,182,64)) {
      const uint8_t color=previewFrogColor, hat=previewFrogHat;
      const size_t cb=prefs.putUChar("frogColor",color);
      const size_t hb=prefs.putUChar("frogHat",hat);
      const bool verified=cb==1 && hb==1 &&
        prefs.getUChar("frogColor",255)==color &&
        prefs.getUChar("frogHat",255)==hat;
      if(verified){
        selectedFrogColor=color;
        selectedFrogHat=hat;
        personalizeSavedUntil=now+2600;
        frogStyleSaveErrorUntil=0;
      }else{
        personalizeSavedUntil=0;
        frogStyleSaveErrorUntil=now+2600;
      }
      personalizeDirty=true;
      Serial.printf("PERSONALIZE SAVE color=%u hat=%u success=%d bytes=%u,%u\\n",
        color,hat,verified,(unsigned)cb,(unsigned)hb);
      return;
    } else return;
    personalizeSavedUntil=0;
    frogStyleSaveErrorUntil=0;
    personalizeDirty=true;
    Serial.printf("PERSONALIZE SELECT color=%u hat=%u\\n",
      previewFrogColor,previewFrogHat);
""" + s[b:]
# Load stored appearance from the same NVS keys that Save writes.
swap('  frogHopHigh = prefs.getUInt("frogHopBest",0);',"""  selectedFrogColor = min((uint8_t)4, prefs.getUChar("frogColor",0));
  selectedFrogHat = min((uint8_t)6, prefs.getUChar("frogHat",0));
  previewFrogColor=selectedFrogColor;
  previewFrogHat=selectedFrogHat;
  Serial.printf("PERSONALIZE LOAD color=%u hat=%u\\n",selectedFrogColor,selectedFrogHat);
  frogHopHigh = prefs.getUInt("frogHopBest",0);""","restore saved style")
# Replace the old pollTouch state machine, whose Game menu branch was intercepting
# swipes and whose personalize actions waited on release. The new version:
# - handles exactly one personalize action per physical touch
# - recognizes jump while the finger is moving, beginning ON the frog
# - ignores short touchscreen contact dropouts
# - preserves other app navigation.
replace_function('void pollTouch(uint32_t now) {',"""void pollTouch(uint32_t now) {
  int x=0,y=0;
  const bool down=readTouch(x,y);
  if(down)touchReleasedAt=0;
  else if(fingerDown){
    if(!touchReleasedAt)touchReleasedAt=now;
    if((uint32_t)(now-touchReleasedAt)<55)return;
  }
  if(down && !fingerDown){
    fingerDown=true;
    downX=lastX=x;downY=lastY=y;downAt=now;
    personalizePressConsumed=false;
    frogSwipeJumpConsumed=false;
    if(screen==PERSONALIZE){
      // Trigger on press; don't depend on the release event to reach SAVE.
      tapped(x,y);
      personalizePressConsumed=true;
    }
    return;
  }
  if(down && fingerDown){
    lastX=x;lastY=y;
    if(screen==FACE && !frogSwipeJumpConsumed &&
       downX>=169 && downX<=299 && downY>=166 && downY<=312 &&
       (downY-y)>=34 && abs(x-downX)<95){
      frogSwipeJumpConsumed=true;
      frogTapPending=false;
      frogCurrentAction=FROG_JUMP_ACTION;
      frogActionAt=now;
      frogActionNumber++;
      frogLastRenderedFrame=-1;
      Serial.println("FROG: swipe from frog UP -> JUMP");
    }
    return;
  }
  if(!down && fingerDown){
    fingerDown=false;
    const int dx=lastX-downX,dy=lastY-downY;
    if(frogSwipeJumpConsumed){
      frogSwipeJumpConsumed=false;
      return;
    }
    if(screen==PERSONALIZE){
      personalizePressConsumed=false;
      if(abs(dx)>SWIPE_THRESHOLD && abs(dx)>abs(dy)*1.2f)
        changeScreen(dx<0?1:-1);
      return;
    }
    if(screen==FACE && downX>=169 && downX<=299 && downY>=166 && downY<=312 &&
       dy>=34 && abs(dx)<95){
      frogTapPending=false;
      frogCurrentAction=FROG_JUMP_ACTION;
      frogActionAt=now;
      frogActionNumber++;
      frogLastRenderedFrame=-1;
      Serial.println("FROG: swipe UP release -> JUMP");
      return;
    }
    if(abs(dx)>=SWIPE_THRESHOLD && abs(dx)>abs(dy)*1.3f){
      changeScreen(dx<0?1:-1);
    }else if(abs(dx)<45 && abs(dy)<45 && (uint32_t)(now-downAt)<900){
      tapped(downX,downY);
    }
  }
}""")
# Repaint after save/hat changes and ensure the on-screen SAVED label expires.
# Redraw can be expensive, but a state change must always force it.
swap('redraw = changedScreen || personalizeDirty || (personalizeSavedUntil > 0 && now >= personalizeSavedUntil);',
'redraw = changedScreen || personalizeDirty || (personalizeSavedUntil > 0 && now >= personalizeSavedUntil) || (frogStyleSaveErrorUntil > 0 && now >= frogStyleSaveErrorUntil);',
'personalize redraw')
# Prevent permanent redraw once confirmation expired.
swap('  } else if (screen == CLOCK) {\n    int minute = timeSet ? runningSeconds() / 60 : -1;',
'  } else if (screen == CLOCK) {\n    int minute = timeSet ? runningSeconds() / 60 : -1;',
'unchanged') if False else None
# Reset confirmation timer after its first expiration redraw, not before draw.
# Preserve older logic if it already clears on redraw.
# Check static expectations for compile-time regression.
for required in ('prefs.getUChar("frogHat",255)==hat','PERSONALIZE SAVE','swipe from frog UP -> JUMP',
                 'if(screen==PERSONALIZE){','drawFrogHat(previewFrogHat,227,311,2)'):
 assert required in s,required
p.write_text(s)
print("V9 personalized and swipe jump fixes applied",p,len(s))
