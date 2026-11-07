# ============================================================================
# services/base.py — Shared runtime helpers, CUDA setup, & abstract contracts.
# ============================================================================
import os
import shutil
import sys
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

IS_WINDOWS = os.name == 'nt'
_CACHE_DIR_NAME = 'cache'

STANDARD_CACHE_SUBDIRS = {
    'tmp': 'Temporary archive extraction & document conversion scratchpad',
    'pycache': 'Centralized Python bytecode (.pyc) compilation cache',
    'cuda': 'NVIDIA CUDA runtime & PTX JIT compilation kernel cache',
    'build': 'Compilation binaries, C++/CUDA build test artifacts',
    'models': 'AI runtime models, HuggingFace & Torch cache',
    'pip': 'Pip wheel downloads & package build cache',
    'ocr': 'OCR image preprocessing and vision intermediate cache',
}


class ConversionError(RuntimeError):
    """Converter ran but produced nothing usable."""


class BackendUnavailable(RuntimeError):
    """Backend's runtime (model/library) is not available."""


def repo_root() -> Path:
    """Project root (two levels up from services/base.py)."""
    return Path(__file__).resolve().parents[1]


def get_cache_dir(*parts: str) -> Path:
    """Project-local cache: <root>/cache/<parts...>. Parents auto-created."""
    d = repo_root() / _CACHE_DIR_NAME
    for p in parts:
        d = d / p
    d.mkdir(parents=True, exist_ok=True)
    return d


def init_cache_system() -> dict[str, Path]:
    """Initialize structured cache directory hierarchy and route all subsystems to it.

    1. Creates standard subdirectories under <repo_root>/cache:
       - tmp/      : extraction / converter temp files (purged if >24h)
       - pycache/  : centralized Python bytecode (.pyc)
       - cuda/     : NVIDIA CUDA JIT / PTX cache
       - build/    : compiled binaries, test runners
       - models/   : HuggingFace & Torch model caches
       - pip/      : pip wheel download cache
       - ocr/      : OCR image preprocessing / vision cache
    2. Routes Python bytecode to cache/pycache (enabling compilation for speed while
       keeping source tree clean).
    3. Routes Python standard tempfile and OS temp variables (TEMP/TMP) to cache/tmp.
    4. Routes CUDA, HuggingFace, Torch, and Pip cache paths via environment variables.
    5. Migrates any loose files in cache/ root to cache/build/.
    """
    cache_root = repo_root() / _CACHE_DIR_NAME
    paths: dict[str, Path] = {}

    # 1. Create standard directory structure
    for sub in STANDARD_CACHE_SUBDIRS:
        p = cache_root / sub
        try:
            p.mkdir(parents=True, exist_ok=True)
        except OSError:
            pass
        paths[sub] = p

    try:
        (cache_root / 'models' / 'huggingface').mkdir(parents=True, exist_ok=True)
        (cache_root / 'models' / 'torch').mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    # 2. Python bytecode caching (keep source clean, preserve compilation for speed)
    sys.pycache_prefix = str(paths['pycache'])
    sys.dont_write_bytecode = False
    os.environ['PYTHONPYCACHEPREFIX'] = str(paths['pycache'])

    # 3. Standard tempfile & OS environment
    import tempfile
    tempfile.tempdir = str(paths['tmp'])
    os.environ['TEMP'] = str(paths['tmp'])
    os.environ['TMP'] = str(paths['tmp'])

    # 4. Third-party frameworks & toolchain caches
    os.environ['CUDA_CACHE_PATH'] = str(paths['cuda'])
    os.environ['HF_HOME'] = str(paths['models'] / 'huggingface')
    os.environ['HUGGINGFACE_HUB_CACHE'] = str(paths['models'] / 'huggingface' / 'hub')
    os.environ['TRANSFORMERS_CACHE'] = str(paths['models'] / 'huggingface')
    os.environ['TORCH_HOME'] = str(paths['models'] / 'torch')
    os.environ['PIP_CACHE_DIR'] = str(paths['pip'])

    # 5. Move any loose test/build files from cache root to cache/build
    try:
        for item in cache_root.iterdir():
            if item.is_file() and item.name not in ('README.md', '.gitignore'):
                dest = paths['build'] / item.name
                if dest.exists():
                    dest.unlink()
                shutil.move(str(item), str(dest))
    except Exception:
        pass

    return paths


def get_cache_stats() -> dict[str, dict]:
    """Return size and file count breakdown for each cache subfolder."""
    cache_root = repo_root() / _CACHE_DIR_NAME
    stats: dict[str, dict] = {}
    for sub, desc in STANDARD_CACHE_SUBDIRS.items():
        sub_path = cache_root / sub
        total_size = 0
        file_count = 0
        if sub_path.exists():
            for p in sub_path.rglob('*'):
                if p.is_file() and p.name not in ('.gitkeep', 'README.md'):
                    file_count += 1
                    try:
                        total_size += p.stat().st_size
                    except OSError:
                        pass
        stats[sub] = {
            'path': sub_path,
            'description': desc,
            'file_count': file_count,
            'size_bytes': total_size,
        }
    return stats


def purge_stale_cache(max_age_seconds: float = 24 * 3600) -> int:
    """Delete old files/dirs strictly under cache/tmp.

    Compilation caches (pycache, cuda, build, pip, models) are explicitly
    preserved to maximize runtime performance and avoid re-compilation.
    Returns count of removed items.
    """
    tmp_root = repo_root() / _CACHE_DIR_NAME / 'tmp'
    if not tmp_root.exists():
        return 0
    removed = 0
    now = time.time()
    for entry in tmp_root.iterdir():
        if entry.name in ('.gitkeep', 'README.md'):
            continue
        try:
            if now - entry.stat().st_mtime > max_age_seconds:
                if entry.is_dir():
                    shutil.rmtree(entry, ignore_errors=True)
                else:
                    entry.unlink()
                removed += 1
        except OSError:
            pass
    return removed


def setup_cuda_dlls() -> bool:
    """Configure Windows DLL search paths for NVIDIA CUDA runtime & llama_cpp.

    Resolves cudart64, cublas64, and llama/ggml libraries so GPU offload works
    flawlessly on NVIDIA hardware (e.g. GTX 1650, RTX series).
    """
    if not IS_WINDOWS:
        return True

    import ctypes

    # Candidate directories containing CUDA runtime DLLs
    candidates: list[str] = []

    # 1. Site-packages from the active python environment
    exe_dir = Path(sys.executable).resolve().parent
    site_packages = (exe_dir / '..' / 'Lib' / 'site-packages').resolve()
    if site_packages.exists():
        candidates.extend([
            str(site_packages / 'nvidia' / 'cuda_runtime' / 'bin'),
            str(site_packages / 'nvidia' / 'cublas' / 'bin'),
            str(site_packages / 'nvidia' / 'cuda_nvrtc' / 'bin'),
            str(site_packages / 'llama_cpp' / 'lib'),
        ])

    # 2. CUDA Toolkit directories if installed (e.g. CUDA 13.5)
    for env_var in ['CUDA_PATH', 'CUDA_PATH_V13_5', 'CUDA_PATH_V12_0']:
        cuda_home = os.environ.get(env_var)
        if cuda_home and os.path.exists(cuda_home):
            candidates.extend([
                os.path.join(cuda_home, 'bin', 'x64'),
                os.path.join(cuda_home, 'bin'),
                os.path.join(cuda_home, 'lib', 'x64'),
            ])

    # Add valid directories to Windows DLL search path and os.environ['PATH']
    for p in candidates:
        if os.path.isdir(p):
            try:
                os.add_dll_directory(p)
            except Exception:
                pass
            if p not in os.environ.get('PATH', ''):
                os.environ['PATH'] = p + os.pathsep + os.environ.get('PATH', '')

    # Preload ggml libraries in dependency order if present in llama_cpp
    llama_lib_dir = site_packages / 'llama_cpp' / 'lib'
    if llama_lib_dir.exists():
        for dll_name in ['ggml-base.dll', 'ggml-cuda.dll', 'ggml.dll']:
            dll_file = llama_lib_dir / dll_name
            if dll_file.exists():
                try:
                    ctypes.CDLL(str(dll_file))
                except Exception:
                    pass

    return True


class DocumentConverter(ABC):
    """A document -> Markdown backend."""
    id: str = ''
    name: str = ''
    extensions: tuple[str, ...] = ()
    priority: int = 0

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def convert(self, file_name: str, data: bytes) -> str: ...


class OcrProvider(ABC):
    """A vision OCR backend (image/pdf bytes -> Markdown)."""
    id: str = ''
    name: str = ''

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def ocr(self, data: bytes, mime: str, file_name: Optional[str] = None,
            prompt: Optional[str] = None) -> str: ...
