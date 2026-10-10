import pytest
from pydantic import ValidationError

from services.api.app.schemas import InputAssetManifest
from services.api.app.storage import LocalObjectStore


def test_immutable_objects_and_checksums(tmp_path):
    store = LocalObjectStore(tmp_path)
    uri, checksum = store.put("reference/v1/input.csv", b"demo\n")
    store.verify(uri, checksum)
    assert store.put("reference/v1/input.csv", b"demo\n") == (uri, checksum)
    with pytest.raises(ValueError, match="different content"):
        store.put("reference/v1/input.csv", b"changed\n")
    with pytest.raises(ValueError, match="mismatch"):
        store.verify(uri, "sha256:" + "0" * 64)
    with pytest.raises(ValueError, match="does not exist"):
        store.verify((tmp_path / "missing").as_uri(), checksum)


@pytest.mark.parametrize("key", ["../outside", "/absolute", "a/../b", "a\\b", "C:/drive"])
def test_object_keys_cannot_escape_storage(tmp_path, key):
    with pytest.raises(ValueError):
        LocalObjectStore(tmp_path).put(key, b"bad")


@pytest.mark.parametrize("uri", ["s3://bucket", "s3:///file", "file://server/share", "file:///tmp/../secret", "s3://bucket/key?token=secret"])
def test_malformed_object_uris_are_rejected(uri):
    with pytest.raises(ValidationError):
        InputAssetManifest(input_type="rainfall", storage_uri=uri, checksum="sha256:" + "0" * 64, dataset_version="v1")
