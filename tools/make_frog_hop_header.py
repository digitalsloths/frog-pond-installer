#!/usr/bin/env python3
"""Build RGB565 indexed 48x56 frames from the user's Frog Hop sprite sheet."""
from pathlib import Path
import sys,zlib,base64
root=Path(sys.argv[1]); W,H,N=32,40,8
colors=[(238,243,250),(185,249,188),(185,216,194),(100,230,105),
(100,229,105),(99,229,104),(94,223,99),(78,203,83),
(65,189,71),(83,178,89),(47,149,52),(10,94,14),
(0,88,4),(5,54,7),(0,46,2),(0,2,1)]
data=zlib.decompress(base64.b64decode(Path('assets/frog_hop_frames.zlib.b64').read_text().strip()))
assert len(data)==W*H*N,(len(data),W*H*N)
def rgb565(c):
 r,g,b=c
 return ((r>>3)<<11)|((g>>2)<<5)|(b>>3)
out=['#pragma once','#include <Arduino.h>',f'#define FROGHOP_W {W}',f'#define FROGHOP_H {H}',f'#define FROGHOP_FRAMES {N}',
'static const uint16_t FROGHOP_PALETTE[16] PROGMEM = {'+','.join(str(rgb565(c)) for c in colors)+'};',
f'static const uint8_t FROGHOP_DATA[{N}][{W*H}] PROGMEM = {{']
for f in range(N):
 arr=bytearray()
 for y in range(H):
  arr.extend(data[y*N*W+f*W:y*N*W+(f+1)*W])
 out.append('{')
 for i in range(0,len(arr),24):out.append(','.join(map(str,arr[i:i+24]))+',')
 out.append('},')
out+=['};','']
target=root/'FrogPond_175_PhysicalSteps_V1'/'froghop_sprites.h'
target.write_text('\n'.join(out));print(target,target.stat().st_size)
