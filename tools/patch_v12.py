#!/usr/bin/env python3
"""V12 layered render: original 20x20 frog, palette-swap body, one hat-only overlay."""
from pathlib import Path
import re,sys
root=Path(sys.argv[1])
files=list(root.rglob("*.ino"))
assert len(files)==1,files
p=files[0]; s=p.read_text()
m=re.search(r'void\s+drawFrogSpriteStyled\s*\(([^)]*)\)\s*\{',s)
if not m: raise RuntimeError("drawFrogSpriteStyled definition missing")
args=m.group(1)
names=[re.search(r'([A-Za-z_]\w*)\s*$',v.strip()).group(1) for v in args.split(',')]
if len(names)!=6: raise RuntimeError("Expected 6 styled-sprite arguments: "+args)
frame,x,y,scale,color,hat=names
br=m.end()-1; depth=0
for j in range(br,len(s)):
    if s[j]=='{':depth+=1
    elif s[j]=='}':
        depth-=1
        if depth==0:break
else:raise RuntimeError("Unbalanced drawFrogSpriteStyled")
body="""{
  if (FRAME < 0 || FRAME >= FROG_FRAME_COUNT) return;
  // Only palette slots 1,3,4 are green frog body shades. Do not recolor eyes,
  // black outlines, mouth, or accessory colors.
  static const uint16_t kBodyShades[5][3] = {
    {0x02C0,0x45E8,0x0160}, // original green
    {0x8015,0xB2FA,0x500C}, // purple
    {0x02AE,0x5D7F,0x0148}, // blue
    {0x8203,0xC368,0x48C2}, // brown
    {0x6B4D,0xCE79,0x4208}  // grayscale
  };
  uint8_t shade = COLOR < 5 ? COLOR : 0;
  const uint8_t *pixels = FROG_FRAMES[FRAME];
  for (int yy=0;yy<FROG_H;++yy) {
    int xx=0;
    while(xx<FROG_W) {
      uint8_t c=pgm_read_byte(pixels+yy*FROG_W+xx);
      if (!c) { ++xx; continue; }
      int first=xx++;
      while(xx<FROG_W && pgm_read_byte(pixels+yy*FROG_W+xx)==c) ++xx;
      uint16_t rgb = c==1?kBodyShades[shade][0]:
                     c==3?kBodyShades[shade][1]:
                     c==4?kBodyShades[shade][2]:pgm_read_word(FROG_PALETTE+c);
      gfx->fillRect(X+first*SCALE,Y+yy*SCALE,(xx-first)*SCALE,SCALE,rgb);
    }
  }
  // One overlay only. Hat origin follows the rendered sprite's anchor,
  // not a fixed screen coordinate. The same logic handles animated poses.
  if(HAT>0 && HAT<=FROG_HAT_COUNT)
    drawFrogHat(HAT, X+(FROG_W*SCALE)/2, Y+2*SCALE, SCALE);
}"""
for source,dest in {'FRAME':frame,'X':x,'Y':y,'SCALE':scale,'COLOR':color,'HAT':hat}.items():
    body=re.sub(r'\b'+source+r'\b',dest,body)
s=s[:br]+body+s[j+1:]
# Eliminate V11's second, hard-coded home overlay: the renderer above handles it.
old="""  // The selected hat must be rendered on the HOME frog after its body.
  // Do not rely on the customization preview's draw path.
  if(selectedFrogHat>0 && selectedFrogHat<=FROG_HAT_COUNT){
    drawFrogHat(selectedFrogHat,233,184,5);
  }
"""
if s.count(old)!=1:raise RuntimeError("V11 duplicate overlay not found")
s=s.replace(old,"",1)
# Explicitly display both COLOR and HAT indexes for verifying previews.
marker='gfx->printf("HAT %u / SAVED %u", (unsigned)previewFrogHat,(unsigned)selectedFrogHat);'
if marker not in s:raise RuntimeError("V11 debug labels missing")
s=s.replace(marker,'gfx->printf("HAT %u / SAVED %u  COLOR %u", (unsigned)previewFrogHat,(unsigned)selectedFrogHat,(unsigned)previewFrogColor);',1)
assert s.count('kBodyShades')>=2
assert 'prefs.getUChar("frogHat",255)' in s
p.write_text(s)
print("V12 layered frog palette + hat overlay; removed double-rendered home hat")
