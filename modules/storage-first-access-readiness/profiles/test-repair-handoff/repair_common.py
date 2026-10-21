"""Shared types for the owned test/repair handoff observation profile."""
import hashlib
import json
import sys
from pathlib import Path

PARENT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PARENT))
from ecc39 import PROFILE, decode, encode
from storage_core import read_json, require

INPUTS = {'clk':1, 'reset':1, 'valid':1, 'cfg':8, 'operation':4,
          'word_address':'aw', 'physical_address':'paw', 'repair_input':12,
          'write_data':32, 'byte_enable':4, 'raw_input':39}
OUTPUTS = {'accepted':1, 'address_valid':1, 'committed':1, 'error':1,
           'internal_read':1, 'correctable':1, 'uncorrectable':1,
           'test_owner':1, 'test_done':1, 'repair_loaded':1, 'repair_active':1,
           'ecc_enabled':1, 'released':1, 'initialized':'words', 'decoded_bad':4,
           'decoded_spare':4, 'canonical_bad':4, 'canonical_spare':4,
           'repair_epoch':16, 'loaded_payload':12, 'actual_physical':'paw',
           'before_codeword':39, 'after_codeword':39, 'read_data':32,
           'old_data':32, 'test_writes':'physical', 'test_reads':'physical'}
STATE = ('test_owner','test_done','repair_loaded','repair_active','ecc_enabled',
         'initialized','released','repair_epoch','loaded_payload','decoded_bad',
         'decoded_spare','canonical_bad','canonical_spare','test_writes','test_reads')
FIELDS = tuple('before_'+k for k in STATE) + tuple(k for k in INPUTS if k not in
         ('clk','reset','valid','cfg')) + tuple(OUTPUTS) + ('checks','failures')
IDENTITY = ('run_ref','scope_ref','design_ref','configuration_ref','memory_ref',
            'init_epoch_ref','transition_ref')
BASIS = ('mapping_basis_ref','macro_view_ref','wrapper_basis_ref','repair_basis_ref',
         'test_basis_ref','initializer_basis_ref','instrumentation_basis_ref','owner_ref')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',',':'),
                         allow_nan=False).encode()).hexdigest()

def uint(value, maximum, label):
    require(type(value) is int and 0 <= value <= maximum, 'Invalid '+label)
    return value

def text(value, label):
    require(isinstance(value,str) and value.strip() and len(value)<=1024,
            'Missing/invalid '+label)
    return value

def save(path, value):
    with Path(path).open('x',encoding='utf-8',newline='\n') as stream:
        stream.write(json.dumps(value,indent=2,allow_nan=False)+'\n')

def contained(root, name, limit=16*1024*1024):
    root=Path(root)
    require(not root.is_symlink(), 'Linked native directory')
    path=root/name
    require(Path(name).name==name and not path.is_symlink() and path.is_file(),
            'Missing/linked native file: '+name)
    require(path.resolve().parent==root.resolve() and path.stat().st_size<=limit,
            'Native file outside bounds: '+name)
    return path

def exit_code(report):
    return 1 if report['findings'] else 2 if report['gaps'] else 0
