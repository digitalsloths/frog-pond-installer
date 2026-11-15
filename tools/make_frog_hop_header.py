#!/usr/bin/env python3
"""Build RGB565 indexed 48x56 frames from the user's Frog Hop sprite sheet."""
from pathlib import Path
import sys,zlib,base64
root=Path(sys.argv[1]); W,H,N=48,56,8
colors=[(238,243,250),(183,248,186),(217,228,228),(170,212,178),
(100,230,105),(100,229,105),(99,229,104),(98,228,103),
(89,217,95),(76,200,81),(72,191,78),(65,190,71),
(65,189,71),(142,174,151),(89,172,95),(64,188,70),
(64,172,68),(59,169,63),(91,140,97),(56,138,60),
(30,127,34),(23,100,26),(1,90,5),(18,75,20),
(1,85,4),(0,88,4),(0,81,4),(9,57,11),
(1,47,3),(0,47,2),(0,46,2),(1,3,1)]
data=zlib.decompress(base64.b64decode(Path('assets/frog_hop_frames.zlib.b64').read_text().strip()))
assert len(data)==W*H*N,(len(data),W*H*N)
def rgb565(c):
 r,g,b=c
 return ((r>>3)<<11)|((g>>2)<<5)|(b>>3)
out=['#pragma once','#include <Arduino.h>',f'#define FROGHOP_W {W}',f'#define FROGHOP_H {H}',f'#define FROGHOP_FRAMES {N}',
'static const uint16_t FROGHOP_PALETTE[32] PROGMEM = {'+','.join(str(rgb565(c)) for c in colors)+'};',
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
