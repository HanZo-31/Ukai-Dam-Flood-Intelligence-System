import os
import pytest
from services.api.app.storage import LocalObjectStore
from services.api.app.receiving_db import immutable_copy
from services.api.app.receiving import raw_hash


@pytest.mark.skipif(os.name != 'nt', reason='Windows rename no-overwrite semantics')
def test_permission_denied_hardlink_uses_atomic_copy_and_retains_immutability(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        raise PermissionError('hard links unavailable')
    monkeypatch.setattr(os, 'link', denied)
    store = LocalObjectStore(tmp_path/'objects')
    uri, checksum = store.put('result.bin', b'original')
    store.verify(uri, checksum)
    assert store.put('result.bin', b'original') == (uri, checksum)
    with pytest.raises(ValueError):
        store.put('result.bin', b'changed')
    source = tmp_path/'source.bin'
    source.write_bytes(b'evidence')
    target = tmp_path/'received/result.bin'
    immutable_copy(source, target, raw_hash(source))
    assert target.read_bytes() == b'evidence'
    source.write_bytes(b'different')
    with pytest.raises(ValueError):
        immutable_copy(source, target, raw_hash(source))
    assert target.read_bytes() == b'evidence'
