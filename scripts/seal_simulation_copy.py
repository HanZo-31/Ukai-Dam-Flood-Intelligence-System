"""Seal a prepared plain Simulation handoff without deleting or moving any source files."""
import argparse
import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT if (ROOT/'SIMULATION_PACKAGE_ID.txt').is_file() else ROOT.parent/'Ukai_Simulation_Ready'


def digest(p):
    with p.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,help='Exact working copy to seal; never changes another copy.')
    args=parser.parse_args()
    output=(args.root or OUT).resolve()
    if not (output/'SIMULATION_PACKAGE_ID.txt').is_file():
        raise ValueError('Prepared Simulation folder is required.')
    ignored={'__pycache__','.vite','.pytest_cache'}
    files=sorted(p for p in output.rglob('*') if p.is_file() and p.name!='SIMULATION_CHECKSUMS.sha256' and not ignored.intersection(p.parts))
    print(f'Checksumming {len(files)} files...',flush=True)
    hashes=[]
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i,value in enumerate(pool.map(digest,files)):
            hashes.append(value)
            if (i+1)%3000==0:
                print(str(i+1)+' checked',flush=True)
    (output/'SIMULATION_CHECKSUMS.sha256').write_text(''.join(h+'  '+p.relative_to(output).as_posix()+'\n' for p,h in zip(files,hashes)),encoding='utf-8')
    print(f'Sealed: {len(files)} files; {sum(p.stat().st_size for p in files)/1024**3:.2f} GiB.',flush=True)


if __name__=='__main__':
    main()
