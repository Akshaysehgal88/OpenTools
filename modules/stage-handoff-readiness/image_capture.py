#!/usr/bin/env python3
"""Capture identity and PT_LOAD metadata for a static identity-mapped x86-64 ELF."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys
from handoff_core import MAX,require

def capture(path):
    path=Path(path);require(path.stat().st_size<=64*1024*1024,'ELF profile limit is 64 MiB');data=path.read_bytes()
    require(len(data)>=64 and data[:7]==b'\x7fELF\x02\x01\x01','ELF64 little-endian v1 required')
    values=struct.unpack_from('<HHIQQQIHHHHHH',data,16)
    kind,machine,version,entry,phoff,_,_,ehsize,phsize,phnum,_,_,_=values
    require(kind==2 and machine==62 and version==1 and ehsize==64,'Static executable x86-64 ELF profile required')
    require(phsize==56 and 0<phnum<=1024 and phoff>=64 and phoff+phnum*phsize<=len(data),'Invalid/extended program headers')
    segments=[]
    for index in range(phnum):
        ptype,flags,offset,vaddr,paddr,filesz,memsz,align=struct.unpack_from('<IIQQQQQQ',data,phoff+index*phsize)
        require(ptype not in (2,3),'Dynamic/interpreter ELF not qualified')
        if ptype!=1:continue
        require(vaddr==paddr and 0<memsz and filesz<=memsz and offset+filesz<=len(data) and vaddr+memsz<=MAX+1,'Invalid/nonidentity load segment')
        require(align in (0,1) or align&(align-1)==0,'Invalid segment alignment')
        require(flags&~7==0,'Unsupported segment flags')
        require(not any(vaddr<s['start']+s['size'] and s['start']<vaddr+memsz for s in segments),'Overlapping ELF load segments not qualified')
        segments.append({'start':vaddr,'size':memsz,'file_offset':offset,'file_size':filesz,
            'permissions':[name for name,bit in (('R',4),('W',2),('X',1)) if flags&bit],
            'evidence_ref':path.name+':PT_LOAD:'+str(index)})
    require(segments and any('X' in s['permissions'] and s['start']<=entry<s['start']+s['size'] for s in segments),'Entry must lie in an executable load segment')
    return {'format':'opentools.stage.image.v1','machine':'x86_64','sha256':hashlib.sha256(data).hexdigest(),
        'entry':entry,'segments':segments,'evidence_ref':path.name+':ELF64-static-identity'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('image');parser.add_argument('--output');args=parser.parse_args()
    try:
        encoded=json.dumps(capture(args.image),indent=2)+'\n'
        if args.output:
            with Path(args.output).open('x',encoding='utf-8') as stream:stream.write(encoded)
        else:print(encoded,end='')
        return 0
    except (OSError,ValueError,TypeError,struct.error) as error:print(str(error),file=sys.stderr);return 3

if __name__=='__main__':sys.exit(main())
