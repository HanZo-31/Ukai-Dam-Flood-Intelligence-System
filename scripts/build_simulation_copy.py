"""Prepare a plain self-contained Windows x64 transfer; preserve the working source."""
import hashlib
import json
import shutil
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'Ukai_Simulation_Ready'
PYTHON=Path(sys.base_prefix)
NODE=Path(r'C:\Program Files\nodejs')
SKIP={'__pycache__','.pytest_cache','.vite','.git','.venv','.quality'}


def digest(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def copy(source,destination,skip=SKIP):
    if source.is_dir():
        shutil.copytree(source,destination,ignore=lambda path,names:[n for n in names if n in skip])
    else:
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(source,destination)


def main():
    if OUT.exists():
        raise ValueError('Simulation preparation folder already exists; do not overwrite an existing handoff.')
    if not (ROOT/'frontend/dist/index.html').is_file():
        raise ValueError('Build the current frontend before packaging.')
    OUT.mkdir()
    print('Preparing plain folder: '+str(OUT),flush=True)
    for name in ('database','docs','scripts','services','tests','part_a','receipts','frontend','evidence'):
        print('Copying '+name,flush=True)
        copy(ROOT/name,OUT/name)
    for p in ROOT.iterdir():
        if p.is_file() and (p.suffix in {'.md','.txt','.ini','.yaml','.cmd'} or p.name=='.env.example') and p.name not in {'.env'}:
            copy(p,OUT/p.name)
    print('Bundling PostgreSQL/PostGIS...',flush=True)
    copy(ROOT/'runtime/pgsql',OUT/'runtime/pgsql')
    # PostgreSQL is a separate executable; it cannot use Python's adjacent DLLs.
    for name in ('vcruntime140.dll','vcruntime140_1.dll','msvcp140.dll'):
        copy(Path(r'C:\Windows\System32')/name,OUT/'runtime/pgsql/bin'/name)
    print('Bundling Python and verified backend packages...',flush=True)
    runtime=OUT/'runtime/python'
    runtime.mkdir(parents=True)
    for name in ('python.exe','python3.dll','python312.dll','vcruntime140.dll','vcruntime140_1.dll','LICENSE.txt'):
        copy(PYTHON/name,runtime/name)
    copy(PYTHON/'DLLs',runtime/'DLLs')
    copy(PYTHON/'Lib',runtime/'Lib',SKIP|{'site-packages','test','idlelib','turtledemo'})
    copy(ROOT/'.venv/Lib/site-packages',runtime/'Lib/site-packages')
    (runtime/'python312._pth').write_text('.\nDLLs\nLib\nLib/site-packages\n..\\..\nimport site\n',encoding='ascii')
    print('Bundling separate quality tools...',flush=True)
    quality=OUT/'runtime/quality'
    quality.mkdir(parents=True)
    for name in ('python.exe','python3.dll','python312.dll','vcruntime140.dll','vcruntime140_1.dll','LICENSE.txt'):
        copy(PYTHON/name,quality/name)
    copy(ROOT/'.quality/Lib/site-packages',quality/'Lib/site-packages')
    copy(ROOT/'.quality/Scripts/ruff.exe',quality/'Scripts/ruff.exe')
    (quality/'python312._pth').write_text('.\n..\\python\\DLLs\n..\\python\\Lib\nLib/site-packages\n..\\..\nimport site\n',encoding='ascii')
    print('Bundling Node and npm...',flush=True)
    node=OUT/'runtime/node'
    node.mkdir(parents=True)
    for name in ('node.exe','npm.cmd','npx.cmd','node_modules'):
        if (NODE/name).exists():
            copy(NODE/name,node/name)
    for name in ('LICENSE','LICENSE.txt'):
        if (NODE/name).exists():
            copy(NODE/name,node/name)
    identifier=uuid.uuid4().hex
    (OUT/'SIMULATION_PACKAGE_ID.txt').write_text(identifier+'\n',encoding='ascii')
    start='@echo off\nsetlocal\ntitle Ukai Simulation\ncd /d "%~dp0"\n"runtime\\python\\python.exe" -B scripts\\simulation_runtime.py\npause\n'
    (OUT/'START_SIMULATION.cmd').write_text(start,encoding='ascii')
    for name in ('START_UKAI.cmd','START_FRONTEND.cmd','START_FRONTEND_PREVIEW.cmd'):
        (OUT/name).write_text('@echo off\ncall "%~dp0START_SIMULATION.cmd"\n',encoding='ascii')
    (OUT/'STOP_SIMULATION.cmd').write_text('@echo off\ncd /d "%~dp0"\n"runtime\\python\\python.exe" -B scripts\\simulation_runtime.py --stop\npause\n',encoding='ascii')
    (OUT/'STOP_DATABASE.cmd').write_text('@echo off\ncall "%~dp0STOP_SIMULATION.cmd"\n',encoding='ascii')
    (OUT/'VERIFY_COPY.cmd').write_text('@echo off\ncd /d "%~dp0"\n"runtime\\python\\python.exe" -B scripts\\simulation_runtime.py --verify-copy\nif errorlevel 1 (echo COPY VERIFICATION FAILED.) else (echo COPY VERIFIED.)\npause\n',encoding='ascii')
    (OUT/'CHECK_SIMULATION.cmd').write_text('@echo off\ncd /d "%~dp0"\n"runtime\\python\\python.exe" -B scripts\\simulation_runtime.py --check-only --no-browser\npause\n',encoding='ascii')
    (OUT/'DEV_FRONTEND.cmd').write_text('@echo off\nsetlocal\nset "PATH=%~dp0runtime\\node;%PATH%"\ncd /d "%~dp0frontend"\necho Start START_SIMULATION.cmd first. Development opens at http://127.0.0.1:5175.\ncall npm run dev\npause\n',encoding='ascii')
    vite=OUT/'frontend/vite.config.ts'
    vite.write_text(vite.read_text(encoding='utf-8').replace('127.0.0.1:8765','127.0.0.1:8766').replace('port: 5173','port: 5175'),encoding='utf-8')
    (OUT/'REBUILD_FRONTEND.cmd').write_text('@echo off\nsetlocal\nset "PATH=%~dp0runtime\\node;%PATH%"\ncd /d "%~dp0frontend"\ncall npm run build\nif errorlevel 1 goto failed\ncall npm test\nif errorlevel 1 goto failed\necho Build and frontend tests passed. Restart START_SIMULATION.cmd to use the new build.\npause\nexit /b 0\n:failed\necho Build or tests failed. Check the messages above before handing off this copy.\npause\nexit /b 1\n',encoding='ascii')
    (OUT/'SEAL_WORKING_COPY.cmd').write_text('@echo off\ncd /d "%~dp0"\necho This updates the checksum inventory of THIS folder after intentional edits.\necho It records file contents; it does not prove the edited software works.\n"runtime\\python\\python.exe" -B scripts\\seal_simulation_copy.py --root "%~dp0."\nif errorlevel 1 (echo SEAL FAILED.) else (echo SEALED. Now run VERIFY_COPY.cmd.)\npause\n',encoding='ascii')
    (OUT/'START_HERE_SIMULATION.md').write_text('''# Ukai SSD copy - another Windows laptop

This is the runnable combined application, with frontend/backend source, production frontend, dependencies, all four verified scenario receipts, native PostgreSQL/PostGIS, Python and Node. No ZIP, installer, Git, account or internet connection is needed for ordinary use. Target: Windows x64 with a current browser.

## Copy and run

1. Copy this **entire Ukai_Simulation_Ready folder** onto the SSD. Copy it; do not remove the working laptop's original folders.
2. Safely eject, connect the SSD to the other laptop, and open its Ukai_Simulation_Ready folder in Windows File Explorer.
3. Double-click **VERIFY_COPY.cmd**. Wait for COPY VERIFIED. This checks contents, not just file count.
4. Double-click **START_SIMULATION.cmd**. The first run verifies files and creates/imports a local database; allow several minutes.
5. Wait for **READY: 4 scenarios verified**. The normal browser opens **http://127.0.0.1:5174** automatically.
6. Keep the server window open. Do not launch three separate windows; the SSD launcher starts frontend, API and database together.

Ports are separate from the working laptop's original app: frontend 5174, API 8766, PostgreSQL 55433. Everything binds to 127.0.0.1. No remote map/font/script service is required.

## What lives where

The SSD holds the app, code, runtimes and checksum-protected scenario deliveries. The receiving laptop keeps its own writable database, imported objects, credentials and logs under `%LOCALAPPDATA%\\UkaiSSD\\<instance>`. Its exact location is printed at startup. A local NTFS database avoids putting a live database on a removable/exFAT drive.

The receiver recreates the four stored scenarios from verified receipts. It does not execute HEC-RAS, change source rasters, infer missing provenance, or copy this laptop's active database. Numeric database row IDs and import timestamps may be new; scenario/run IDs, output bytes and manifest identities are retained.

The instance is derived from this package and its current path. Another laptop or SSD drive letter gets a separate local database without corrupting the old instance. Keeping the same drive letter avoids a repeated first-run import. The original laptop's database and ports are untouched.

## Recheck after transfer

Close the running SSD server first, then double-click **CHECK_SIMULATION.cmd**. It verifies all four scenarios and downloads through the frontend proxy, records `SSD_SMOKE_RESULT.json` in the printed local state folder, and stops cleanly. Real browser rendering should also be checked on the receiving laptop, especially its WebGL maps.

## Stop and safely eject

Press **Ctrl+C in the SSD server window**, or run **STOP_SIMULATION.cmd**, and wait for **Stopped**. Close the server window, then use Windows safely-remove/eject. Each laptop has its own local database; the SSD may be transferred after shutdown.

## Troubleshooting

- Port in use: stop another copy using these SSD ports. The launcher will not stop unrelated services.
- First-run error: inspect `setup.log`, `api.log`, `frontend.log` in the local-state folder printed at startup. Do not delete the source packages.
- Map/WebGL issue: inspect the receiving browser's hardware acceleration and the map error text. The data and raster renderings still need that device's browser check.
- Editing code: frontend source, lockfile and Windows node_modules are included. Node/npm are bundled under `runtime/node`. Original developer scripts referring to `.venv`/`.quality` should use `runtime/python/python.exe`/`runtime/quality/python.exe` instead; ordinary launch needs only START_SIMULATION.cmd.

## Scope and remaining records

This transfers **Ukai_Combined**, not the large original scientific workspace outside it. For a full scientific archive, separately copy the original `C:\\Ukai` folders, including large HEC-RAS result/terrain files and fast-solver work. Those external files are not needed to run the combined app.

The models remain simulated, uncalibrated and not scientifically validated. Missing licences/timezones/exposure data stay explicitly unknown. Original audit history is retained; older launch URLs in those records describe the working laptop. Follow this SSD guide for the portable copy.
''',encoding='utf-8')
    for name in ('README.md','START_HERE.md','frontend/FRONTEND_START_HERE.md'):
        guide=OUT/name
        link='../START_HERE_SIMULATION.md' if name.startswith('frontend/') else 'START_HERE_SIMULATION.md'
        guide.write_text('# Portable SSD copy\n\nUse ['+link+']('+link+'). '
            'Start with START_SIMULATION.cmd; this copy uses http://127.0.0.1:5174. '
            'The notes below are retained as original development history.\n\n---\n\n'
            +guide.read_text(encoding='utf-8'),encoding='utf-8')
    (OUT/'RUN_FULL_RECHECK.cmd').write_text('@echo off\ncall "%~dp0CHECK_SIMULATION.cmd"\n',encoding='ascii')
    report={'package_id':identifier,'source':str(ROOT),'prepared_folder':str(OUT),
            'database_strategy':'recreate four immutable receipts in receiving-local state',
            'copied_live_database':False,'portable_smoke_test_performed':False}
    (OUT/'SIMULATION_PACKAGE_REPORT.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    files=sorted(p for p in OUT.rglob('*') if p.is_file() and p.name!='SIMULATION_CHECKSUMS.sha256')
    print(f'Checksumming {len(files)} files...',flush=True)
    with ThreadPoolExecutor(max_workers=8) as pool:
        hashes=list(pool.map(digest,files))
    (OUT/'SIMULATION_CHECKSUMS.sha256').write_text(''.join(h+'  '+p.relative_to(OUT).as_posix()+'\n' for p,h in zip(files,hashes)),encoding='utf-8')
    total=sum(p.stat().st_size for p in files)
    print(f'Prepared {len(files)} checksummed files; {total/1024**3:.2f} GiB. Ready for independent smoke test.',flush=True)


if __name__=='__main__':
    main()
