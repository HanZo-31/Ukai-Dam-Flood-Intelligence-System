"""Synthetic inventory checks; no service/database or physical acceptance claims."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from package_delivery import seal  # noqa: E402 -- bundled Python needs explicit local path
from verify_delivery import safe_file, verify_files  # noqa: E402 -- same bootstrap


def fixture_delivery(tmp_path):
    root = tmp_path / 'synthetic-delivery'
    root.mkdir()
    (root / 'sample.txt').write_text('Synthetic public fixture, no credentials', encoding='utf-8')
    seal(root, {'sample.txt': 'synthetic/sample.txt'})
    return root


def test_inventory_and_hash_roundtrip(tmp_path):
    root = fixture_delivery(tmp_path)
    assert set(verify_files(root)) == {'sample.txt', 'FILE_INVENTORY.csv'}


def test_tampered_file_is_rejected(tmp_path):
    root = fixture_delivery(tmp_path)
    (root / 'sample.txt').write_text('Changed synthetic fixture')
    with pytest.raises(ValueError, match='Checksum mismatch'):
        verify_files(root)


def test_unlisted_file_is_rejected(tmp_path):
    root = fixture_delivery(tmp_path)
    (root / 'unlisted.txt').write_text('Synthetic unexpected fixture')
    with pytest.raises(ValueError, match='Unexpected'):
        verify_files(root)


def test_missing_file_is_rejected(tmp_path):
    root = fixture_delivery(tmp_path)
    (root / 'sample.txt').unlink()
    with pytest.raises(ValueError, match='Missing delivered'):
        verify_files(root)


@pytest.mark.parametrize('name', ['../outside.txt', '/absolute.txt', 'C:/file.txt', 'dir\\file.txt', 'dir//file.txt'])
def test_unsafe_paths_are_rejected(tmp_path, name):
    with pytest.raises(ValueError, match='Unsafe'):
        safe_file(tmp_path, name)


def test_duplicate_inventory_checksum_is_rejected(tmp_path):
    root = fixture_delivery(tmp_path)
    checksums = root / 'CHECKSUMS.sha256'
    text = checksums.read_text()
    checksums.write_text(text + text.splitlines()[0] + '\n')
    with pytest.raises(ValueError, match='duplicate'):
        verify_files(root)


def test_existing_seal_is_never_overwritten(tmp_path):
    root = fixture_delivery(tmp_path)
    old = (root / 'CHECKSUMS.sha256').read_bytes()
    with pytest.raises(ValueError, match='Never reseal'):
        seal(root, {})
    assert (root / 'CHECKSUMS.sha256').read_bytes() == old


def test_evidence_index_rejects_escaping_paths(tmp_path):
    import json
    from verify_delivery import verify_evidence
    work = tmp_path / 'team2_work'
    work.mkdir()
    (work / 'DELIVERY_EVIDENCE.json').write_text(json.dumps({
        'regression': '../outside.json', 'quality': '../outside.json',
        'packaging': '../outside.json', 'contract': '../outside.json'}))
    with pytest.raises(ValueError, match='Unsafe'):
        verify_evidence(tmp_path)


def test_evidence_index_rejects_unknown_roles(tmp_path):
    from verify_delivery import verify_evidence
    work = tmp_path / 'team2_work'
    work.mkdir()
    (work / 'DELIVERY_EVIDENCE.json').write_text('{"unknown":"report.json"}')
    with pytest.raises(ValueError, match='Invalid delivery evidence index'):
        verify_evidence(tmp_path)
