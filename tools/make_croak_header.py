#!/usr/bin/env python3
"""Convert the supplied 16-kHz mono croak asset to stereo 16-bit I2S PCM in flash."""
from pathlib import Path
import base64,zlib,sys
root=Path(sys.argv[1])
encoded=Path('assets/croak_u8_16khz_zlib.b64').read_text().strip()
samples=zlib.decompress(base64.b64decode(encoded,validate=True))
if not 3000<len(samples)<16000:raise ValueError('Unexpected croak length')
# Keep the sound below clipping while accounting for original U8 center of 128.
values=[(int(v)-128)*140 for v in samples]
stereo=[value for sample in values for value in (sample,sample)]
header=['// User-provided croak; 16kHz, signed 16-bit, stereo, ES8311 I2S.','#pragma once','#include <Arduino.h>','static const int16_t FROG_CROAK_PCM[] PROGMEM = {']
for i in range(0,len(stereo),20):header.append('  '+','.join(str(x) for x in stereo[i:i+20])+',')
header.extend(['};','#define FROG_CROAK_PCM_BYTES sizeof(FROG_CROAK_PCM)',''])
out=root/'FrogPond_175_PhysicalSteps_V1'/'frog_croak_audio.h'
out.write_text('\n'.join(header))
print('Generated',out,len(samples),'audio samples',len(stereo),'stereo values')