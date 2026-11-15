#!/usr/bin/env python3
"""V10 beta patch on top of the existing V9 firmware. Strict and reversible."""
from pathlib import Path
import sys
root=Path(sys.argv[1])
files=list(root.rglob("*.ino"))
assert len(files)==1, files
p=files[0]; s=p.read_text()
def once(old,new,label):
 global s
 if s.count(old)!=1: raise RuntimeError(f"{label}: expected 1 match, found {s.count(old)}")
 s=s.replace(old,new,1)
# Keep NVS verified Save/hat cycling from V9, and preserve all V9 games, sound and power behavior.
# Eliminate the ill-fitting trailing sprite frames from the home hop sequence.
s=s.replace('static const uint8_t FROG_HOP_SEQUENCE[] = {0, 9, 13, 17, 17, 13, 9, 14, 18, 0};',
            'static const uint8_t FROG_HOP_SEQUENCE[] = {0, 9, 13, 17, 17, 13, 9, 0, 0, 0};')
particle_code="""
// Deterministic pollen / fireflies, rendered between background and frog.
void drawPondParticles(uint32_t now) {
  const uint32_t tick=now/100;
  for(int i=0;i<28;++i) {
    uint32_t seed=(uint32_t)(i+17)*2654435761UL;
    int x=43+(int)((seed>>11)%382);
    int y=118+(int)((seed>>19)%270);
    x+=int((tick/(3+(i%5))+(seed>>8))%32)-16;
    y-=int((tick/(4+(i%4)))%60);
    if(y<110)y+=280;
    const uint16_t c=(i%6==0)?0xFFE0:((i%3==0)?0xF7BD:0xB7B5);
    if(i%7==0) {
      gfx->drawFastHLine(x-2,y,5,c);
      gfx->drawFastVLine(x,y-2,5,c);
    }else gfx->fillRect(x,y,(i%4==0)?3:2,(i%4==0)?3:2,c);
  }
}
"""
once('void drawFace(uint32_t now) {',particle_code+'\nvoid drawFace(uint32_t now) {','particle helper')
# Insert into drawFace only, after the freshly drawn background, before the frog.
start=s.index('void drawFace(uint32_t now) {')
opening=s.index('{',start);depth=0;end=None
for i in range(opening,len(s)):
 if s[i]=='{': depth+=1
 elif s[i]=='}':
  depth-=1
  if depth==0: end=i;break
assert end is not None
face=s[start:end]
needle='else gfx->fillScreen(0x056A);'
if needle not in face: raise RuntimeError('pond background anchor missing')
face=face.replace(needle,needle+'\n  drawPondParticles(now);',1)
# Restore a readable counter to the circular home screen, avoiding the frog.
hud="""
  gfx->fillRoundRect(129,57,208,61,15,0x0843);
  gfx->drawRoundRect(129,57,208,61,15,0xA653);
  gfx->setTextSize(2); gfx->setTextColor(WHITE);
  gfx->setCursor(151,78); gfx->print("STEPS: "); gfx->print(frogSteps);
"""
face+=hud
s=s[:start]+face+s[end:]
# Ensure the particle field animates even when the frog has not changed pose.
a=s.index('  if (screen == FACE) {',s.index('void loop() {'))
b=s.find('  } else if (screen ==',a)
if b<0: raise RuntimeError('FACE redraw section missing')
seg=s[a:b]
if 'redraw = changedScreen ||' in seg:
 seg=seg.replace('redraw = changedScreen ||','redraw = changedScreen || (now-prevFrameAt>=240) ||',1)
else: raise RuntimeError('face redraw expression missing')
s=s[:a]+seg+s[b:]
for required in ('prefs.getUChar("frogHat",255)==hat','void drawPondParticles','STEPS: '):
 if required not in s: raise RuntimeError('missing '+required)
p.write_text(s)
print('V10 beta patch: particles, home steps, frog pose ordering + verified V9 Save',p)
