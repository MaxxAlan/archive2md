# ============================================================================
# intake — recursive unpacking of archives and directory trees.
# zip/war/jar (zipfile) · tar/gz/tgz/bz2/xz (tarfile) · 7z (py7zr) · rar (rarfile)
# Yields (inner_path, data, origin_chain) for every leaf file.
# ============================================================================
import io
import os
import tarfile
import zipfile
from pathlib import Path
from typing import Iterator, Optional

from .classify import get_extension

ARCHIVE_EXTS = frozenset({'zip', 'war', 'jar', 'rar', '7z', 'tar', 'gz', 'tgz', 'bz2', 'xz'})
MAX_ENTRY_BYTES = 512 * 1024 * 1024   # 512MB per entry safety cap
MAX_TOTAL_ENTRIES = 50_000            # zip-bomb cap


class IntakeError(RuntimeError):
    pass


def _extract_zip(data: bytes) -> Iterator[tuple[str, bytes]]:
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        count = 0
        for info in zf.infolist():
            if info.is_dir():
                continue
            count += 1
            if count > MAX_TOTAL_ENTRIES:
                raise IntakeError('Qua nhieu entry (nghi van zip-bomb) — dung lai.')
            if info.file_size > MAX_ENTRY_BYTES:
                continue
            yield info.filename, zf.read(info)


def _extract_tar(data: bytes) -> Iterator[tuple[str, bytes]]:
    # tarfile auto-detects gz/bz2/xz compression from the stream.
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:*') as tf:
        count = 0
        for member in tf:
            if not member.isfile():
                continue
            count += 1
            if count > MAX_TOTAL_ENTRIES:
                raise IntakeError('Qua nhieu entry (nghi van tar-bomb) — dung lai.')
            if member.size > MAX_ENTRY_BYTES:
                continue
            fh = tf.extractfile(member)
            if fh is None:
                continue
            yield member.name, fh.read()


def _extract_7z(data: bytes) -> Iterator[tuple[str, bytes]]:
    try:
        import py7zr
    except ImportError as e:
        raise IntakeError(
            'py7zr chua cai — chay setup.ps1 (venv core).'
        ) from e
    # py7zr 1.x removed in-memory readall(); extract to cache/tmp and walk.
    import shutil
    from services.base import get_cache_dir  # local import: avoid cycle at module load
    tmp = Path(shutil.mkdtemp(prefix='7z-', dir=str(get_cache_dir('tmp'))))
    try:
        with py7zr.SevenZipFile(io.BytesIO(data), mode='r') as sz:
            sz.extractall(tmp)
        for dirpath, _dirnames, filenames in os.walk(tmp):
            for fname in filenames:
                full = Path(dirpath) / fname
                yield full.relative_to(tmp).as_posix(), full.read_bytes()
    except py7zr.Bad7zFile as e:
        raise IntakeError(f'7z loi doc file: {e}') from e
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _extract_rar(data: bytes) -> Iterator[tuple[str, bytes]]:
    try:
        import rarfile
    except ImportError as e:
        raise IntakeError(
            'rarfile chua cai — chay: venv python -m pip install rarfile (hoac setup.ps1)'
        ) from e
    # rarfile needs an external helper (unrar/unar/7z/bsdtar) on Windows.
    try:
        with rarfile.RarFile(io.BytesIO(data)) as rf:
            for info in rf.infolist():
                if info.is_dir():
                    continue
                if info.file_size > MAX_ENTRY_BYTES:
                    continue
                yield info.filename, rf.read(info)
    except rarfile.Error as e:
        raise IntakeError(
            f'Khong giai nen duoc RAR (can unrar.exe hoac 7z.exe trong PATH): {e}'
        ) from e


def extract_archive_bytes(ext: str, data: bytes) -> Iterator[tuple[str, bytes]]:
    """Dispatch to the right extractor for one archive payload."""
    if ext in ('zip', 'war', 'jar'):
        yield from _extract_zip(data)
    elif ext in ('tar', 'gz', 'tgz', 'bz2', 'xz'):
        yield from _extract_tar(data)
    elif ext == '7z':
        yield from _extract_7z(data)
    elif ext == 'rar':
        yield from _extract_rar(data)
    else:
        raise IntakeError(f'Khong ho tro dinh dang thay doi: .{ext}')


def iter_archive_files(ext: str, data: bytes, origin: str, depth: int,
                       max_depth: int) -> Iterator[tuple[str, bytes, Optional[str]]]:
    """Recursively unpack; yields (inner_path, data, origin) for leaf files.

    Nested archives recurse with depth+1; origin is the 'a.zip > b.rar' chain.
    """
    if depth > max_depth:
        yield from ()  # silent: depth cap prevents archive bombs
        return
    chain = origin or None
    try:
        entries = list(extract_archive_bytes(ext, data))
    except (IntakeError, zipfile.BadZipFile, tarfile.TarError, OSError, ValueError) as e:
        print(f'[intake] Bo qua khong giai nen duoc {origin}: {e}')
        return
    for name, payload in entries:
        inner_path = f'{chain} > {name}' if chain else name
        norm_path = name.replace('\\', '/').lstrip('/')
        entry_ext = get_extension(norm_path)
        if entry_ext in ARCHIVE_EXTS:
            yield from iter_archive_files(entry_ext, payload, inner_path, depth + 1, max_depth)
        else:
            # Display path nests nested-archive entries under their archive chain:
            # 'Login.zip > src.zip' + 'App.java' → 'Login.zip/src.zip/App.java'
            display = '/'.join([*chain.split(' > '), norm_path]) if chain else norm_path
            yield display, payload, chain


def iter_directory(root: Path, max_depth: int = 5) -> Iterator[tuple[str, bytes, Optional[str]]]:
    """Walk a real directory; yields (relative_path, data, origin)."""
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip common junk dirs at source
        dirnames[:] = [d for d in dirnames if d not in (
            'node_modules', '.git', '.svn', '.hg', '__pycache__', '.idea',
            '.vscode', 'venv', '.venv', 'target')]
        for fname in filenames:
            full = Path(dirpath) / fname
            rel = full.relative_to(root).as_posix()
            entry_ext = get_extension(fname)
            try:
                data = full.read_bytes()
            except OSError as e:
                print(f'[intake] Khong doc duoc {rel}: {e}')
                continue
            if entry_ext in ARCHIVE_EXTS:
                yield from iter_archive_files(entry_ext, data, rel, 1, max_depth)
            else:
                yield rel, data, None


def iter_input(input_path: Path, max_depth: int = 5) -> Iterator[tuple[str, bytes, Optional[str]]]:
    """Main entry: (input file | dir) → stream of (path, data, origin)."""
    if input_path.is_dir():
        yield from iter_directory(input_path)
        return
    if not input_path.is_file():
        raise IntakeError(f'Input khong ton tai: {input_path}')
    data = input_path.read_bytes()
    ext = get_extension(input_path.name)
    if ext in ARCHIVE_EXTS:
        yield from iter_archive_files(ext, data, input_path.name, 0, max_depth)
    else:
        yield input_path.name, data, None
