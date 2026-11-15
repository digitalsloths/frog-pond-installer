#!/usr/bin/env python3
"""V20: position-aligned idle hats, compact Personalize, back arrows, no menu step count."""
from pathlib import Path
import sys
files=list(Path(sys.argv[1]).rglob("*.ino"))
assert len(files)==1,files
p=files[0];s=p.read_text()
def swap(a,b,reason):
 global s
 n=s.count(a)
 if n!=1:raise RuntimeError(f"{reason}: expected one instance, found {n}")
 s=s.replace(a,b,1)
def span(signature):
 a=s.find(signature)
 if a<0:raise RuntimeError("Missing "+signature)
 b=s.index("{",a);depth=0
 for j in range(b,len(s)):
  if s[j]=="{":depth+=1
  elif s[j]=="}":
   depth-=1
   if depth==0:return a,j+1
 raise RuntimeError("Unbalanced "+signature)
def fn(sig,new):
 global s
 a,b=span(sig)
 s=s[:a]+new+s[b:]
def add_before_close(sig,code):
 global s
 a,b=span(sig)
 s=s[:b-1]+code+"\n"+s[b-1:]
# Follow the head's frame-dependent movement using metadata extracted from
# the uploaded transparent 22-frame idle sprite (relative to reference frame 0).
swap('if(hat>0)drawIsolatedHatFrame(hat,0,x,y,scale);',
'''if(hat>0) {
    int dx=(int8_t)pgm_read_byte(&POND_IDLE_HEAD_DX[frame]);
    int dy=(int8_t)pgm_read_byte(&POND_IDLE_HEAD_DY[frame]);
    drawIsolatedHatFrame(hat,0,x+dx*scale,y+dy*scale,scale);
  }''',"idle hat follows head")
# Rebuild preview rather than shifting text calls independently. Remove old
# bottom debug/saved/swipe text and increase centered hat icon scale.
fn('void drawPersonalize() {',r'''void drawPersonalize() {
  gfx->fillScreen(0x0883);
  centered("Personalize",233,25,2,WHITE);
  drawFrogSpriteStyled(0,185,50,4,previewFrogColor,previewFrogHat);
  centered("Frog Color",233,140,2,0xB737);
  gfx->fillRoundRect(65,165,78,53,12,0x2C6A);
  gfx->fillRoundRect(323,165,78,53,12,0x2C6A);
  centered("<",103,175,3,WHITE);
  centered(">",362,175,3,WHITE);
  gfx->fillRoundRect(190,168,86,45,11,frogColorSwatches[previewFrogColor]);
  gfx->drawRoundRect(190,168,86,45,11,WHITE);
  centered(frogColorNames[previewFrogColor],233,222,2,WHITE);
  centered("Accessories",233,250,2,0xB737);
  gfx->fillRoundRect(65,280,78,55,12,0x2C6A);
  gfx->fillRoundRect(323,280,78,55,12,0x2C6A);
  centered("<",103,292,3,WHITE);
  centered(">",362,292,3,WHITE);
  if(previewFrogHat==0)centered("NONE",233,301,2,WHITE);
  else drawFrogHat(previewFrogHat,233,306,4);
  centered(frogHatNames[previewFrogHat],233,344,2,WHITE);
  centeredButton(146,374,174,53,"SAVE",GREEN);
  // No debug coordinates, saved counters or footer text on this page.
}''')
# Visible buttons and touch regions must match; SAVE remains verified in V11.
needle='  } else if (screen == PERSONALIZE) {'
start=s.index(needle,s.index('void tapped(int x, int y) {'))
end=s.index('  } else if (screen == GAMES) {',start)
portion=s[start:end]
for old,new in [
 ('x<174 && y>=276 && y<=383','x<=159 && y>=266 && y<=348'),
 ('x>292 && y>=276 && y<=383','x>=307 && y>=266 && y<=348'),
 ('x>=126 && x<=340 && y>=382 && y<=456','x>=140 && x<=325 && y>=366 && y<=433'),
 ('x<170 && y>=182 && y<276','x<=159 && y>=159 && y<246'),
 ('x>290 && y>=182 && y<276','x>=307 && y>=159 && y<246')
]:
 if portion.count(old)!=1:raise RuntimeError("Personalize touch anchor missing: "+old)
 portion=portion.replace(old,new)
s=s[:start]+portion+s[end:]
# Back arrow is left-centered in the round display and doesn't overlap the
# settings sliders or editable Time/Date fields.
back=r'''
void drawPageBackArrow(){
  gfx->fillRoundRect(23,216,70,47,11,0x2467);
  gfx->drawRoundRect(23,216,70,47,11,0xAD97);
  centered("<",58,223,3,WHITE);
}
'''
swap('void drawAppMenu() {',back+'\nvoid drawAppMenu() {',"back arrow helper")
# Remove Steps from Games / Apps / Settings selector, but NOT the home HUD.
for needle in ['  centered("STEPS",233,78,1,WHITE);',
               '  centered(String(frogSteps),233,105,3,0xCFFF);']:
 if needle not in s:raise RuntimeError("Main menu steps missing: "+needle)
 s=s.replace(needle,'',1)
# Add back arrow to main selector, Games, Apps hub and settings.
for sig in ['void drawAppMenu() {','void drawEmptyGames() {',
            'void drawAppsHub() {','void pondDrawSettings(){']:
 add_before_close(sig,'  drawPageBackArrow();')
# Time editor has a separate top left arrow in V19; replace with the same
# middle-left arrow. Its hit target lives in pondTimeTap (not tapped()).
swap(' gfx->fillRoundRect(55,68,61,43,10,0x2467);\n centered("<",85,75,2,WHITE);\n','',"remove old top-left Time arrow")
add_before_close('void pondDrawTime(){','  drawPageBackArrow();')
swap('if(y>=63 && y<=114 && x<122){openScreen(SETTINGS);return;}',
     'if(x>=15 && x<=100 && y>=210 && y<=270){openScreen(SETTINGS);return;}',
     "Time back button hitbox")
# Route menu back to FACE, and secondary pages back to main menu.
swap('void tapped(int x, int y) {',r'''void tapped(int x, int y) {
  if ((screen==APPS || screen==GAMES || screen==APPS_HUB || screen==SETTINGS)
      && inside(x,y,15,210,88,60)) {
    openScreen(screen==APPS?FACE:APPS);
    return;
  }
''',"menu back taps")
for required in ('POND_IDLE_HEAD_DX[frame]','POND_IDLE_HEAD_DY[frame]',
                 'drawPageBackArrow();','openScreen(screen==APPS?FACE:APPS)',
                 'drawIsolatedHatFrame(hat,0,x+dx*scale',
                 'prefs.getUChar("frogHat",255)'):
 if required not in s:raise RuntimeError("Missing feature: "+required)
p.write_text(s)
print("V20: idle hat alignment, raised Personalize, larger hat preview, clean footer, back arrows, no menu steps.")
