"""Create a verified, private test baseline INSIDE V05; never write another project."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
CHECK = ROOT / '_layout_recheck'
SOURCE = CHECK / 'baseline-source'
PUBLIC = ROOT / 'layout_cleanup_evidence'


def sha(path):
    with path.open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def main():
    assert ROOT.name == 'UKAI_COMBINED_V05' and CHECK.is_relative_to(ROOT)
    # Create/canonicalize the dedicated target before parallel path resolution.
    # Windows may resolve nonexistent descendants through a redirected alias.
    SOURCE.mkdir(parents=True, exist_ok=True)
    assert SOURCE.resolve().is_relative_to(ROOT.resolve())
    expected = '2d41129336506cbf02261f537f423a247551bcf719fb38a370dbc3e18dc49726'
    assert sha(ROOT / 'SSD_CHECKSUMS.sha256') == expected
    PUBLIC.mkdir(exist_ok=True)
    entries = [line.split('  ', 1) for line in (ROOT / 'SSD_CHECKSUMS.sha256').read_text().splitlines()]

    def copy(entry):
        digest, relative = entry
        key = Path(relative)
        assert not key.is_absolute() and '..' not in key.parts
        source, dest = ROOT / key, SOURCE / key
        # Explicit extended paths avoid MAX_PATH normalization for deeply
        # nested bundled npm files. The resolved root was checked above.
        source = Path('\\\\?\\' + str(source))
        dest = Path('\\\\?\\' + str(dest))
        assert sha(source) == digest, 'Pre-change V05 mismatch: ' + relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            assert sha(dest) == digest, 'Unexpected existing snapshot bytes: ' + relative
        else:
            shutil.copy2(source, dest)
        assert sha(dest) == digest

    with ThreadPoolExecutor(max_workers=8) as pool:
        for i, _ in enumerate(pool.map(copy, entries), 1):
            if i % 3000 == 0:
                print(f'{i} original V05 files verified/copied', flush=True)
    shutil.copy2(ROOT / 'SSD_CHECKSUMS.sha256', SOURCE / 'SSD_CHECKSUMS.sha256')
    report = {'checked_at': datetime.now().astimezone().isoformat(), 'passed': True,
              'before_change_manifest_sha256': expected, 'entries': len(entries),
              'scope': 'All writes contained in V05; private snapshot only, excluded from handoff.'}
    (PUBLIC / 'BEFORE_CHANGE.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
