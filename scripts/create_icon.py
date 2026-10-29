"""Original code-drawn ALT-AI icon, no external art dependencies."""
import math
import struct
import zlib
from pathlib import Path

def main():
    size=256
    raw=bytearray()
    for y in range(size):
        raw.append(0)
        for x in range(size):
            inside=(24<=x<=231 or 24<=y<=231 or (x-(24 if x<128 else 231))**2+(y-(24 if y<128 else 231))**2<=24**2)
            if not inside: raw.extend((0,0,0,0));continue
            slash=82<=y<=177 and 100+(177-y)*.34<=x<=128+(177-y)*.34
            border=x<2 or y<2 or x>253 or y>253
            glow=max(0,1-math.hypot(x-128,y-128)/130)
            raw.extend((255,0,87,255) if slash else (65,27,54,255) if border else (int(10+13*glow),int(10+2*glow),int(17+7*glow),255))
    def chunk(kind,data): return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',size,size,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(raw),9))+chunk(b'IEND',b'')
    folder=Path(__file__).resolve().parents[1]/'assets';folder.mkdir(exist_ok=True)
    (folder/'icon.png').write_bytes(png)
    (folder/'icon.ico').write_bytes(struct.pack('<HHH',0,1,1)+struct.pack('<BBBBHHII',0,0,0,0,1,32,len(png),22)+png)

if __name__=='__main__':main()
