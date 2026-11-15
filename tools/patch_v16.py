#!/usr/bin/env python3
"""V16: isolated hat overlays and frame-specific positions, original color art,
volume slider, save-to-home, menu order, particle size, and top 20% shade."""
from pathlib import Path
import zipfile,re,sys
root=Path(sys.argv[1]); paths=list(root.rglob("*.ino"))
assert len(paths)==1,paths
p=paths[0];s=p.read_text()
def replace_once(a,b,label):
 global s
 if s.count(a)!=1:raise RuntimeError(f"{label}: expected one anchor, got {s.count(a)}")
 s=s.replace(a,b,1)
def span(src,signature):
 a=src.find(signature)
 if a<0:raise RuntimeError("Missing function "+signature)
 b=src.index("{",a);dep=0
 for i in range(b,len(src)):
  if src[i]=="{":dep+=1
  elif src[i]=="}":
   dep-=1
   if dep==0:return a,i+1
 raise RuntimeError("Unbalanced "+signature)
def function(signature,body):
 global s
 a,b=span(s,signature);s=s[:a]+body+s[b:]
replace_once('#include "frog_custom.h"','#include "frog_custom.h"\n#include "frog_isolated_hats.h"',"hat asset header")
overlay=r'''
// Per-frame positions measured from the user's 32x32 frog/hat reference sheets.
// The 20x20 frog renderer crops the original sprite at (8,12).
// Pixels with 0x0001 are transparent; not magenta chromakey.
void drawIsolatedHatPixels(uint8_t index,int px,int py,int scale) {
  if(index>=6)return;
  const uint16_t *data=ISOLATED_HAT_PIXELS[index];
  const int w=ISOLATED_HAT_W[index], h=ISOLATED_HAT_H[index];
  for(int yy=0;yy<h;++yy) {
    int xx=0;
    while(xx<w) {
      uint16_t c=pgm_read_word(data+yy*w+xx);
      if(c==0x0001){++xx;continue;}
      int first=xx++;
      while(xx<w && pgm_read_word(data+yy*w+xx)==c)++xx;
      gfx->fillRect(px+first*scale,py+yy*scale,(xx-first)*scale,scale,c);
    }
  }
}
void drawIsolatedHatFrame(uint8_t hat,int frame,int x,int y,int scale) {
  if(hat==0 || hat>6)return;
  const uint8_t index=hat-1;
  int f=constrain(frame,0,19);
  const int dx=ISOLATED_HAT_X[index][f]-8;
  const int dy=ISOLATED_HAT_Y[index][f]-12;
  drawIsolatedHatPixels(index,x+dx*scale,y+dy*scale,scale);
}
'''
replace_once('void drawFrogHat(uint8_t hat, int frogX, int frogY, int scale) {',overlay+'\nvoid drawFrogHat(uint8_t hat, int frogX, int frogY, int scale) {',"overlay helpers")
function('void drawFrogHat(uint8_t hat, int frogX, int frogY, int scale) {',r'''void drawFrogHat(uint8_t hat,int frogX,int frogY,int scale) {
  if(hat==0 || hat>6)return;
  int j=hat-1;
  drawIsolatedHatPixels(j,frogX-ISOLATED_HAT_W[j]*scale/2,
                           frogY-ISOLATED_HAT_H[j]*scale/2,scale);
}''')
# Replace the currently palette-swapped V12 renderer with the original
# pre-recolor source, so all existing color options use their original art.
with zipfile.ZipFile('v5.zip') as z:
 original_names=[n for n in z.namelist() if n.endswith('.ino')]
 assert len(original_names)==1
 original=z.read(original_names[0]).decode()
original_sig='void drawFrogSpriteStyled('
old_a,old_b=span(original,original_sig)
original_fn=original[old_a:old_b]
if 'drawFrogHat(' not in original_fn: raise RuntimeError('Original sprite renderer has no hat hook; inspect before replacing')
# Remove the old accessory overlay (which had an incorrect origin).
original_fn=re.sub(r'\b(?:if\s*\([^;{}]*\)\s*)?drawFrogHat\([^;]+\);','',original_fn)
sig=re.search(r'drawFrogSpriteStyled\(([^)]*)\)',original_fn).group(1)
args=[re.search(r'([A-Za-z_]\w*)\s*$',v.strip()).group(1) for v in sig.split(',')]
if len(args)!=6:raise RuntimeError("Expected 6 renderer arguments: "+repr(args))
frame,x,y,scale,color,hat=args
original_fn=original_fn[:-1]+f'\n  drawIsolatedHatFrame({hat},{frame},{x},{y},{scale});\n'+original_fn[-1]
function(original_sig,original_fn)
# Preview: remove pink/green background by retaining the dark canvas under frog.
# The selected hat still has its own dedicated icon, now from the isolated sheet.
# Pressing Save returns to main pond only after NVS readback succeeds.
needle='        frogStyleSaveErrorUntil=0;'
# Only modify the V11 SAVE success branch, not any other reset.
pos=s.index('bool persisted=(nw==1 && cw==1')
section=s[pos:pos+1400]
if needle not in section:raise RuntimeError("Save-success anchor missing")
section=section.replace(needle,needle+'\n        openScreen(FACE); // Save returns directly to the pond.',1)
s=s[:pos]+section+s[pos+1400:]
# Reorder the visible main menu and its corresponding hit targets.
replace_once('const char* labels[] = {"GAMES","SETTINGS","APPS"};',
             'const char* labels[] = {"GAMES","APPS","SETTINGS"};',"menu labels")
replace_once('else if (inside(x,y,105,230,256,73)) openScreen(SETTINGS);',
             'else if (inside(x,y,105,230,256,73)) openScreen(APPS_HUB);',"middle menu action")
replace_once('else if (inside(x,y,105,322,256,73)) openScreen(APPS_HUB);',
             'else if (inside(x,y,105,322,256,73)) openScreen(SETTINGS);',"bottom menu action")
# Bigger but still softly drifting airborne particles.
replace_once('gfx->drawFastHLine(x-3,y,7,c);','gfx->drawFastHLine(x-4,y,9,c);',"particles horizontal")
replace_once('gfx->drawFastVLine(x,y-3,7,c);','gfx->drawFastVLine(x,y-4,9,c);',"particles vertical")
replace_once('gfx->fillRect(x,y,3,3,c);','gfx->fillRect(x,y,5,5,c);',"particle 5px")
replace_once('else gfx->fillRect(x,y,2,2,c);','else gfx->fillRect(x,y,4,4,c);',"particle 4px")
# 10% of 466 px = 47 px. Approx 20% black using ordered dithering: no
# opaque black rectangle, and works with Arduino_Canvas RGB565 framebuffer.
function('void drawHomeStepCount(){',r'''void drawHomeStepCount(){
  for(int yy=0;yy<47;++yy)
    for(int xx=0;xx<466;++xx)
      if(((xx+yy*2)%5)==0) gfx->drawPixel(xx,yy,BLACK);
  drawStepIcon(195,12,1,BLACK);
  drawStepIcon(193,10,1,WHITE);
  gfx->setTextSize(3);gfx->setTextColor(BLACK);
  gfx->setCursor(242,14);gfx->print(frogSteps);
  gfx->setTextColor(WHITE);gfx->setCursor(240,12);gfx->print(frogSteps);
}''')
# One single-touch draggable volume slider on the SETTINGS page, stored in NVS.
replace_once('Screen screen = FACE;', 'volatile uint8_t frogVolumePct = 72;\nuint8_t frogVolumeApplied = 255;\nScreen screen = FACE;', "early volume globals")
replace_once('es8311_voice_volume_set(codec,72,NULL);',
             'es8311_voice_volume_set(codec,frogVolumePct,NULL);',"audio initial volume")
replace_once('while (true) {\n    if (frogCroakRequested) {',
'''while (true) {
    if(frogVolumeApplied!=frogVolumePct){
      frogVolumeApplied=frogVolumePct;
      es8311_voice_volume_set(codec,frogVolumeApplied,NULL);
    }
    if (frogCroakRequested) {''',"audio live volume")
prefs=re.search(r'prefs\.begin\([^;]+;',s)
if not prefs:raise RuntimeError("NVS begin not found")
s=s[:prefs.end()]+'\n  frogVolumePct = min((uint8_t)100,prefs.getUChar("frogVolume",72));'+s[prefs.end():]
function('void drawSettingsMenu() {',r'''void drawSettingsMenu() {
  gfx->fillScreen(0x0863);
  centered("SETTINGS",233,75,3,WHITE);
  centered("VOLUME",233,156,2,WHITE);
  gfx->fillRoundRect(70,222,326,40,13,0x18C6);
  int filled=(int)frogVolumePct*306/100;
  gfx->fillRoundRect(80,229,306,26,9,0x4208);
  if(filled>0)gfx->fillRoundRect(80,229,filled,26,9,0x07E0);
  centered(String((int)frogVolumePct)+"%",233,288,2,WHITE);
  centered("DRAG TO ADJUST",233,330,1,GRAY);
  centered("SWIPE RIGHT TO RETURN",233,418,1,GRAY);
}''')
# Handle slider immediately on touch DOWN and on drag; persist on release.
needle='    if(screen==PERSONALIZE){'
if needle not in s:raise RuntimeError("Touch-down branch missing")
s=s.replace(needle,'''    if(screen==SETTINGS && y>=199 && y<=290) {
      frogVolumePct=(uint8_t)constrain((x-80)*100/306,0,100);
      changedScreen=true;
      return;
    }
'''+needle,1)
# Add an updating drag branch ahead of the FACE swipe special case.
needle='    if(screen==FACE && !frogSwipeJumpConsumed'
if needle not in s:raise RuntimeError("Touch moving branch missing")
s=s.replace(needle,'''    if(screen==SETTINGS && downY>=199 && downY<=290) {
      frogVolumePct=(uint8_t)constrain((x-80)*100/306,0,100);
      changedScreen=true;
      return;
    }
'''+needle,1)
needle='  if(!down && fingerDown){'
if needle not in s:raise RuntimeError("Touch release branch missing")
s=s.replace(needle,'''  if(!down && fingerDown && screen==SETTINGS && downY>=199 && downY<=290){
    fingerDown=false;
    prefs.putUChar("frogVolume",frogVolumePct);
    changedScreen=true;
    Serial.printf("VOLUME SAVED %u%%\\n",(unsigned)frogVolumePct);
    return;
  }
'''+needle,1)
# Screen redraw flag is local to loop(); pollTouch cannot write it.
# Repaint SETTINGS periodically while the slider is being dragged.
s=s.replace('changedScreen=true;', '/* redraw via SETTINGS timer */')
redraw_anchor='redraw = changedScreen || (screen == APPS && frogStepsRendered != frogSteps);'
if redraw_anchor not in s: raise RuntimeError("settings redraw anchor missing")
s=s.replace(redraw_anchor,
            'redraw = changedScreen || (screen == SETTINGS && now-prevFrameAt >= 125) || (screen == APPS && frogStepsRendered != frogSteps);',1)
# Standard taps in settings should also adjust the slider (in addition to drag).
needle='  } else if (screen == SETTINGS) {'
start=s.index('void tapped(int x, int y) {')
pos=s.find(needle,start)
if pos<0:raise RuntimeError("SETTINGS touch branch missing")
# settings block replaced up to next else-if
q=s.find('  } else if (screen ==',pos+len(needle))
if q<0:raise RuntimeError("SETTINGS subsequent branch missing")
s=s[:pos]+'''  } else if (screen == SETTINGS) {
    if(y>=199 && y<=290){
      frogVolumePct=(uint8_t)constrain((x-80)*100/306,0,100);
      prefs.putUChar("frogVolume",frogVolumePct);
      changedScreen=true;
    }
'''+s[q:]
# Remove any loop-local redraw-flag references inserted into callbacks.
s=s.replace('changedScreen=true;', '/* settings refreshes at 125ms intervals */')
for required in ('drawIsolatedHatFrame','frogVolumePct','openScreen(FACE); // Save','const char* labels[] = {"GAMES","APPS","SETTINGS"};',
                 'drawStepIcon(193,10,1,WHITE)','prefs.getUChar("frogHat",255)'):
 if required not in s:raise RuntimeError("Missing expected V16 behavior: "+required)
p.write_text(s)
print("V16: isolated 20-frame overlays, original frog colors, save-to-home, audio volume, menu and HUD")
