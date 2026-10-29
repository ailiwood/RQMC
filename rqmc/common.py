from __future__ import annotations
import hashlib, json, os, stat, sys, platform
from pathlib import Path
from importlib import metadata

def root() -> Path:
    p = Path(__file__).resolve().parents[1]
    if (p / '.project-root').read_text(encoding='utf-8').strip() != 'RQMC_9950X_20261027':
        raise RuntimeError('Project marker missing or mismatched')
    return p

def digest(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()

def sha_file(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    os.replace(tmp,path)

def load_config():
    return json.loads((root()/'config/experiment.json').read_text(encoding='utf-8'))

def source_hashes():
    r=root()
    ps=[*r.glob('rqmc/*.py'),*r.glob('scripts/*.py'),*r.glob('tests/*.py'),r/'requirements.txt',r/'requirements-fast.txt']
    if (r/'requirements-lock.txt').exists():ps.append(r/'requirements-lock.txt')
    return {p.relative_to(r).as_posix():sha_file(p) for p in sorted(ps)}

def environment():
    packages={}
    for p in ['numpy','scipy','pandas','qmcpy','qmctoolscl','psutil','pytest','matplotlib']:
        try: packages[p]=metadata.version(p)
        except metadata.PackageNotFoundError: packages[p]=None
    installed={d.metadata['Name'].lower():d.version for d in metadata.distributions() if d.metadata['Name']}
    return {'python':platform.python_version(),'platform':platform.platform(),'packages':packages,
            'installed':dict(sorted(installed.items()))}

def seed_words(master: int, *labels) -> list[int]:
    """Stable SeedSequence entropy; not Python's process-dependent hash()."""
    b=hashlib.sha256(json.dumps([master,*labels],sort_keys=True,separators=(',',':')).encode()).digest()
    return [int.from_bytes(b[i:i+4],'little') for i in range(0,32,4)]

def safe_relative(r: Path, relative: str) -> Path:
    """Reject traversal, Windows absolute paths, symlinks and reparse points."""
    from pathlib import PurePosixPath, PureWindowsPath
    if not relative or '\\' in relative or PureWindowsPath(relative).is_absolute():
        raise ValueError('Unsafe path syntax')
    q=PurePosixPath(relative)
    if q.is_absolute() or any(x in ('..','.') for x in q.parts):
        raise ValueError('Unsafe traversal')
    current=r
    for part in q.parts:
        current=current/part
        if current.exists() or current.is_symlink():
            st=current.lstat()
            if current.is_symlink() or getattr(st,'st_file_attributes',0)&getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024):
                raise ValueError('Links/reparse points are forbidden')
    if not current.resolve().is_relative_to(r.resolve()):
        raise ValueError('Path outside root')
    return current
