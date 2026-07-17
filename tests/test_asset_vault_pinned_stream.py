"""Regression contracts for descriptor-pinned private Asset Vault reads."""

from __future__ import annotations

import hashlib
import os
import stat
from types import SimpleNamespace

import copyfast_assets


def test_verified_descriptor_keeps_the_hashed_blob_when_the_path_is_replaced(tmp_path):
    """Serving must use the verified descriptor, never reopen the pathname."""

    objects = tmp_path / "objects"
    objects.mkdir()
    blob = objects / "pinned.blob"
    trusted = b"the verified private blob"
    blob.write_bytes(trusted)
    stream = copyfast_assets._open_verified_private_file(
        blob,
        expected_bytes=len(trusted),
        expected_digest=hashlib.sha256(trusted).hexdigest(),
    )
    assert stream is not None
    replacement = objects / "replacement.blob"
    replacement.write_bytes(b"a same-size replacement blob")
    try:
        try:
            os.replace(replacement, blob)
        except OSError:
            # Some Windows filesystems deny an atomic replace while a file is
            # open. The descriptor still proves it is independently readable;
            # Railway/Linux also exercises the identity-change assertion.
            pass
        else:
            assert copyfast_assets._pinned_private_file_is_current(stream, blob) is False
        assert stream.read() == trusted
    finally:
        stream.close()


def test_verified_descriptor_rejects_a_final_component_symlink(tmp_path, monkeypatch):
    """A storage blob cannot escape through a symlink after key validation."""

    objects = tmp_path / "objects"
    objects.mkdir()
    target = tmp_path / "outside.blob"
    content = b"outside private content"
    target.write_bytes(content)
    link = objects / "linked.blob"
    try:
        os.symlink(target, link)
    except (AttributeError, NotImplementedError, OSError):
        # Windows developer-mode/ACLs can forbid creating test symlinks. Model
        # only the final lstat result; the helper rejects before os.open.
        link.write_bytes(content)
        real_lstat = copyfast_assets.os.lstat

        def lstat_with_symlink(candidate):
            if os.fspath(candidate) == os.fspath(link):
                return SimpleNamespace(st_mode=stat.S_IFLNK | 0o777)
            return real_lstat(candidate)

        monkeypatch.setattr(copyfast_assets.os, "lstat", lstat_with_symlink)
    stream = copyfast_assets._open_verified_private_file(
        link,
        expected_bytes=len(content),
        expected_digest=hashlib.sha256(content).hexdigest(),
    )
    assert stream is None


def test_verified_descriptor_rejects_a_symlinked_objects_directory(tmp_path, monkeypatch):
    """Pinning must cover the intermediate `objects/` component as well."""

    root = tmp_path / "vault"
    root.mkdir()
    target_directory = tmp_path / "outside-objects"
    target_directory.mkdir()
    content = b"intermediate directory target"
    (target_directory / "blob.blob").write_bytes(content)
    objects = root / "objects"
    path = objects / "blob.blob"
    try:
        os.symlink(target_directory, objects, target_is_directory=True)
    except (AttributeError, NotImplementedError, OSError):
        objects.mkdir()
        path.write_bytes(content)
        real_lstat = copyfast_assets.os.lstat

        def lstat_with_symlinked_objects(candidate):
            if os.fspath(candidate) == os.fspath(objects):
                return SimpleNamespace(st_mode=stat.S_IFLNK | 0o777)
            return real_lstat(candidate)

        monkeypatch.setattr(copyfast_assets.os, "lstat", lstat_with_symlinked_objects)
    stream = copyfast_assets._open_verified_private_file(
        path,
        expected_bytes=len(content),
        expected_digest=hashlib.sha256(content).hexdigest(),
    )
    assert stream is None


def test_private_delivery_uses_an_anonymous_rehashed_sealed_stream(tmp_path):
    """The response source is independent from the mutable Vault pathname."""

    objects = tmp_path / "objects"
    objects.mkdir()
    blob = objects / "sealed.blob"
    content = b"sealed private delivery"
    blob.write_bytes(content)
    source = copyfast_assets._open_verified_private_file(
        blob,
        expected_bytes=len(content),
        expected_digest=hashlib.sha256(content).hexdigest(),
    )
    assert source is not None
    sealed = copyfast_assets.seal_verified_private_file(
        source,
        expected_bytes=len(content),
        expected_digest=hashlib.sha256(content).hexdigest(),
    )
    assert source.closed is True
    assert sealed is not None
    try:
        blob.write_bytes(b"tampered vault object")
        assert sealed.read() == content
    finally:
        sealed.close()
