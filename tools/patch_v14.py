#!/usr/bin/env python3
"""V14: Personalize title, bare preview, animated particles, footprint step HUD."""
from pathlib import Path
import sys
root=Path(sys.argv[1]); fs=list(root.rglob("*.ino"))
assert len(fs)==1
p=fs[0];s=p.read_text()
def once(old,new,what):
 global s
 n=s.count(old)
 if n!=1:raise RuntimeError(f"{what}: expected 1, got {n}")
 s=s.replace(old,new,1)
def fn(sig,body):
 global s
 a=s.find(sig)
 if a<0:raise RuntimeError("missing "+sig)
 b=s.index("{",a);dep=0
 for j in range(b,len(s)):
  if s[j]=="{":dep+=1
  elif s[j]=="}":
   dep-=1
   if not dep:
    s=s[:a]+body+s[j+1:];return
 raise RuntimeError("unbalanced "+sig)
once('centered("Personalize your frog",233,24,2,WHITE);','centered("Personalize",233,24,2,WHITE);',"title")
once('  gfx->fillRoundRect(160,54,146,112,16,0x2C6A);\n','',"green frame")
icon="""
static const uint32_t stepPixels[24] PROGMEM={
0x000000,0x000000,0x060000,0x0F8000,0x0F8000,0x0FC000,
0x0FC000,0x0FE0E0,0x0FE1F0,0x0FE3F0,0x07E3F0,0x07C7F0,
0x0027F0,0x01F7F0,0x03F7F0,0x03E3E0,0x01E1C0,0x000600,
0x000FC0,0x000FC0,0x000780,0x000300,0x000000,0x000000};
void drawStepIcon(int x,int y,int z,uint16_t color){
 for(int row=0;row<24;++row){
  uint32_t mask=pgm_read_dword(&stepPixels[row]);
  int col=0;
  while(col<24){
   if(!(mask&(1UL<<col))){++col;continue;}
   int st=col++;
   while(col<24&&(mask&(1UL<<col)))++col;
   gfx->fillRect(x+st*z,y+row*z,(col-st)*z,z,color);
  }
 }
}
void drawHomeStepCount(){
 // Transparent footprint + number, black pixel shadows, NO background box.
 drawStepIcon(162,57,2,BLACK);
 drawStepIcon(160,54,2,WHITE);
 gfx->setTextSize(3);gfx->setTextColor(BLACK);
 gfx->setCursor(225,67);gfx->print(frogSteps);
 gfx->setTextColor(WHITE);gfx->setCursor(223,65);gfx->print(frogSteps);
}
"""
once('void drawFace(uint32_t now) {',icon+'\nvoid drawFace(uint32_t now) {',"icon insertion")
box="""  gfx->fillRoundRect(129,57,208,61,15,0x0843);
  gfx->drawRoundRect(129,57,208,61,15,0xA653);
  gfx->setTextSize(2); gfx->setTextColor(WHITE);
  gfx->setCursor(151,78); gfx->print("STEPS: "); gfx->print(frogSteps);"""
once(box,'  drawHomeStepCount();',"boxed HUD")
fn('void drawPondParticles(uint32_t now) {',"""void drawPondParticles(uint32_t now){
 const uint32_t tick=now/70;
 for(int i=0;i<40;++i){
  uint32_t seed=(uint32_t)(i+31)*2654435761UL;
  int x=38+(int)((seed>>12)%391);
  int y=104+(int)((seed>>20)%310);
  x+=int(((tick/(4+(i%6)))+(seed>>8))%38)-19;
  y-=int((tick/(3+(i%5)))%72);
  if(y<100)y+=300;
  int phase=(int)((tick/5+i*7)%12);
  uint16_t c=phase<3?0xFFE0:(phase<8?0xFFFF:0xCF9A);
  if(i%5==0){
   gfx->drawFastHLine(x-3,y,7,c);
   gfx->drawFastVLine(x,y-3,7,c);
   gfx->fillRect(x-1,y-1,3,3,WHITE);
  } else if(i%3==0)gfx->fillRect(x,y,3,3,c);
  else gfx->fillRect(x,y,2,2,c);
 }
}""")
# Bright magenta pixels baked into the frog sheet must not be drawn.
a=s.index('void drawFrogSpriteStyled(')
b=s.index('  // One overlay only.',a)
sub=s[a:b]
anchor='      gfx->fillRect('
if sub.count(anchor)!=1:raise RuntimeError("frog sprite blit anchor")
sub=sub.replace(anchor,'''      uint16_t rr=(rgb>>11)&31, gg=(rgb>>5)&63, bb=rgb&31;
      if(rr>=24 && bb>=23 && gg<=19) continue;
'''+anchor,1)
s=s[:a]+sub+s[b:]
for t in ('drawHomeStepCount();','centered("Personalize",','drawPondParticles(now);','prefs.getUChar("frogHat",255)'):
 if t not in s:raise RuntimeError("Missing "+t)
p.write_text(s)
print("V14 visual changes patched",p,len(s))
