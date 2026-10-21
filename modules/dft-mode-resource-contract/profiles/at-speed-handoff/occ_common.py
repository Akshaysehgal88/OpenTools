"""Use the parent module's strict local record and path primitives."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from dft_common import canonical,contained,digest,file_hash,known,read_json,require,shape,text
