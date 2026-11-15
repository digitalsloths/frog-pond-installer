#!/usr/bin/env python3
"""V13: fix magenta keying and expose touch coordinates for device diagnosis."""
from pathlib import Path
import sys
root=Path(sys.argv[1]); p=next(root.rglob("*.ino"));s=p.read_text()
def function(sig,new):
 global s
 a=s.find(sig)
 if a<0:raise RuntimeError("missing "+sig)
 b=s.index("{",a);depth=0
 for i in range(b,len(s)):
  if s[i]=="{":depth+=1
  elif s[i]=="}":
   depth-=1
   if depth==0:
    s=s[:a]+new+s[i+1:];return
 raise RuntimeError("unbalanced "+sig)
# Only exact magenta/chroma-key hues; do not erase shadows or dark accessory features.
function('void drawFrogHat(uint8_t hat, int frogX, int frogY, int scale) {',"""
void drawFrogHat(uint8_t hat, int frogX, int frogY, int scale) {
  if(hat==0 || hat>FROG_HAT_COUNT)return;
  const uint16_t *px=FROG_HAT_RGB565[hat-1];
  const int left=frogX-8*scale,top=frogY-4*scale;
  for(int yy=0;yy<FROG_HAT_H;++yy) {
    for(int xx=0;xx<FROG_HAT_W;++xx) {
      uint16_t c=pgm_read_word(px+yy*FROG_HAT_W+xx);
      // Asset chroma-key and transparency values must never be painted.
      uint16_t r=(c>>11)&31,g=(c>>5)&63,b=c&31;
      if(c==FROG_HAT_TRANSPARENT || (r>=23 && b>=22 && g<=15))continue;
      gfx->fillRect(left+xx*scale,top+yy*scale,scale,scale,c);
    }
  }
}""")
# If touch controller orientation differs from display, show the raw hit
# location on the actual personalisation screen for direct diagnosis.
anchor='uint32_t frogStyleSaveErrorUntil = 0;'
if s.count(anchor)!=1:raise RuntimeError("touch state anchor")
s=s.replace(anchor,anchor+'''
int personalTouchX=-1,personalTouchY=-1;
uint32_t personalTouchAt=0;
''',1)
needle='  const bool down=readTouch(x,y);'
if s.count(needle)!=1:raise RuntimeError("touch sample anchor")
s=s.replace(needle,needle+'''
  if(down && screen==PERSONALIZE) {
    personalTouchX=x; personalTouchY=y; personalTouchAt=now;
    personalizeDirty=true;
    Serial.printf("PERSONALIZE RAW TOUCH x=%d y=%d\\n",x,y);
  }
''',1)
signature='void drawPersonalize() {'
a=s.find(signature)
if a<0:raise RuntimeError("drawPersonalize")
b=s.index("{",a);depth=0
for i in range(b,len(s)):
 if s[i]=="{":depth+=1
 elif s[i]=="}":
  depth-=1
  if depth==0:break
face=s[a:i]
face+='''  // Debug marker: should appear directly beneath the finger on touch.
  if(personalTouchAt && (uint32_t)(millis()-personalTouchAt)<4200){
    gfx->fillRoundRect(150,430,170,20,4,0x0000);
    gfx->setTextColor(WHITE); gfx->setTextSize(1);
    gfx->setCursor(161,435);
    gfx->printf("TOUCH %d,%d",personalTouchX,personalTouchY);
    gfx->drawCircle(personalTouchX,personalTouchY,7,0xFFE0);
    gfx->drawFastHLine(personalTouchX-10,personalTouchY,21,0xFFE0);
    gfx->drawFastVLine(personalTouchX,personalTouchY-10,21,0xFFE0);
  }
'''
s=s[:a]+face+s[i:]
p.write_text(s)
print("V13: hat chromakey and live touch marker applied",p)
