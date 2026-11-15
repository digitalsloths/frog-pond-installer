#!/usr/bin/env python3
"""Rebuild the test-only 22-frame transparent frog idle strip uploaded by the user."""
from pathlib import Path
import base64,struct,sys,zlib
# 22 transparent 18x21 sprites, left-to-right from Idle Frog.png.
PAYLOAD="eNrtmEsOgCAMRBna6v1vLOVbw9aFxukCkyeiedNAYkqPFYA6YIKcBdCcFYuoiJOBoLM6MS33c0S25ojZRtRupKyvjkwmKC8RLCJiUsq/tl59MEdWloFPR3tGfJl7pTcWzb84CjdQXQ8WohBMolpJR0FzNx/DaeZjFM38FM+eZ8//pMNNNs8dSSdG8zRP8zxhecJ+OQtZU9CzCObbUjRP89xteMLyhKV5mqd57vP0zJ6n+a+rx/avsk6KWbQwTI9aXaybP46FvNJA5wijkLPVCCNt6tNPm57mudtwn6d5mn/e/AU+SDZb"
data=zlib.decompress(base64.b64decode(PAYLOAD))
assert len(data)==22*18*21, len(data)
colors=[(0,0,0),(0,88,4),(0,0,0),(65,189,71),(100,230,105),(0,46,2),(185,249,188),(162,238,165)]
def rgb565(c):
 r,g,b=c; return ((r>>3)<<11)|((g>>2)<<5)|(b>>3)
out=['#pragma once','#include <Arduino.h>','#define POND_IDLE_FRAMES 22','#define POND_IDLE_W 18','#define POND_IDLE_H 21','static const uint16_t POND_IDLE_PALETTE[] PROGMEM = {' + ','.join('0x%04X'%rgb565(c) for c in colors)+'};','static const uint8_t POND_IDLE_PIXELS[22][378] PROGMEM = {']
for f in range(22):
 segment=data[f*378:(f+1)*378]
 assert any(segment)
 out.append('  {')
 for j in range(0,378,42):out.append('    '+','.join(map(str,segment[j:j+42]))+',')
 out.append('  },')
out.append('};')
# Detect the top/head position for every animation frame.  The motion table
# is generated from the exact alpha-masked idle-strip pixels; compare each
# frame's head against frame 0 so the reference hat attachment stays aligned.
headCenters=[]
headTops=[]
for f in range(22):
 frame=data[f*378:(f+1)*378]
 visible=[(xx,yy) for yy in range(21) for xx in range(18) if frame[yy*18+xx]!=0]
 assert visible, f
 top=min(y for x,y in visible)
 head=[x for x,y in visible if y<=top+4]
 headCenters.append(int(round((min(head)+max(head))/2.0)))
 headTops.append(top)
dx=[max(-6,min(6,c-headCenters[0])) for c in headCenters]
dy=[max(-5,min(5,t-headTops[0])) for t in headTops]
out.append('static const int8_t POND_IDLE_HEAD_DX[22] PROGMEM = {'+','.join(map(str,dx))+'};')
out.append('static const int8_t POND_IDLE_HEAD_DY[22] PROGMEM = {'+','.join(map(str,dy))+'};')
root=Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=True)
(root/'pond_idle_test.h').write_text('\n'.join(out)+'\n')
print('Generated 22 exact-order alpha-masked test idle frames, 18x21')
