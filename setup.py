from __future__ import annotations

import os
import shutil
import subprocess
import sys
import platform
from pathlib import Path

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext
from setuptools.command.build_py import build_py
from setuptools.command.egg_info import egg_info


ROOT = Path(__file__).parent.resolve()
SDK_DIR = Path(os.environ.get("STEAMWORKS_SDK_DIR", ROOT / "sdk")).expanduser().resolve()
STEAM_INCLUDE = SDK_DIR / "public"
GENERATED_DIR = ROOT / "generated"
GENERATOR = ROOT / "tools" / "generate_core.py"
PYTHON_GENERATOR = ROOT / "tools" / "generate_python.py"
API_JSON = STEAM_INCLUDE / "steam" / "steam_api.json"
SWIG_INTERFACE = GENERATED_DIR / "steamworks.i"
SWIG_PROXY = GENERATED_DIR / "steamworks.py"
SWIG_WRAPPER = GENERATED_DIR / "steamworks_wrap.cpp"
SHIM_SOURCE = GENERATED_DIR / "steamworks_swig_shim.cpp"
C_API_SOURCE = GENERATED_DIR / "steamworks_c_api.cpp"
C_API_MODEL = GENERATED_DIR / "steamworks_c_api_model.json"
PYTHON_GROUPED = ROOT / "python" / "steamworks" / "grouped.py"


def setup_relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def steamworks_platform_config() -> dict[str, object]:
    system = platform.system()
    machine = platform.machine().lower()
    redistributable_dir = SDK_DIR / "redistributable_bin"

    if system == "Linux":
        if machine in {"aarch64", "arm64"}:
            lib_dir = redistributable_dir / "linuxarm64"
        elif machine in {"i386", "i686", "x86"}:
            lib_dir = redistributable_dir / "linux32"
        else:
            lib_dir = redistributable_dir / "linux64"
        return {
            "library_dirs": [str(lib_dir)],
            "libraries": ["steam_api"],
            "runtime_library_dirs": ["$ORIGIN"],
            "runtime_lib": lib_dir / "libsteam_api.so",
            "extra_compile_args": ["-std=c++17"],
            "extra_link_args": [],
        }

    if system == "Darwin":
        lib_dir = redistributable_dir / "osx"
        return {
            "library_dirs": [str(lib_dir)],
            "libraries": ["steam_api"],
            "runtime_library_dirs": ["@loader_path"],
            "runtime_lib": lib_dir / "libsteam_api.dylib",
            "extra_compile_args": ["-std=c++17"],
            "extra_link_args": [],
        }

    if system == "Windows":
        is_64_bit = platform.architecture()[0] == "64bit"
        if is_64_bit:
            lib_dir = redistributable_dir / "win64"
            return {
                "library_dirs": [str(lib_dir)],
                "libraries": ["steam_api64"],
                "runtime_library_dirs": [],
                "runtime_lib": lib_dir / "steam_api64.dll",
                "extra_compile_args": ["/std:c++17"],
                "extra_link_args": [],
            }

        lib_dir = redistributable_dir
        return {
            "library_dirs": [str(lib_dir)],
            "libraries": ["steam_api"],
            "runtime_library_dirs": [],
            "runtime_lib": lib_dir / "steam_api.dll",
            "extra_compile_args": ["/std:c++17"],
            "extra_link_args": [],
        }

    raise RuntimeError(f"Unsupported platform for Steamworks SDK: {system}")


STEAM_CONFIG = steamworks_platform_config()
STEAM_RUNTIME_LIB = Path(STEAM_CONFIG["runtime_lib"])


def require_local_sdk() -> None:
    required = [
        API_JSON,
        STEAM_INCLUDE / "steam" / "steam_api_flat.h",
        STEAM_RUNTIME_LIB,
    ]
    missing = [path for path in required if not path.is_file()]
    if missing:
        missing_lines = "\n".join(f"  - {path}" for path in missing)
        raise RuntimeError(
            "The Steamworks SDK is not distributed with SteamworksSwig.\n"
            "Obtain the SDK directly from Valve, then place or symlink it at "
            f"{SDK_DIR}, or set STEAMWORKS_SDK_DIR to its path.\n"
            "For release artifacts, use tools/build_distributions.py; bare "
            "`python -m build` attempts to build a wheel from the intentionally "
            "SDK-free source archive.\n"
            f"Missing required files:\n{missing_lines}"
        )


def generate_sources() -> None:
    require_local_sdk()
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(
        [
            sys.executable,
            str(GENERATOR),
            "--api-json",
            str(API_JSON),
            "--steam-include",
            str(STEAM_INCLUDE),
            "--output-dir",
            str(GENERATED_DIR),
        ],
        cwd=ROOT,
    )
    subprocess.check_call(
        [
            sys.executable,
            str(PYTHON_GENERATOR),
            "--model",
            str(C_API_MODEL),
            "--output",
            str(PYTHON_GROUPED),
        ],
        cwd=ROOT,
    )
    subprocess.check_call(
        [
            "swig",
            "-c++",
            "-python",
            f"-I{STEAM_INCLUDE}",
            f"-I{GENERATED_DIR}",
            "-o",
            str(SWIG_WRAPPER),
            str(SWIG_INTERFACE),
        ],
        cwd=ROOT,
    )


class SteamworksBuildPy(build_py):
    def run(self) -> None:
        generate_sources()

        package_dir = Path(self.build_lib) / "steamworks"
        if package_dir.exists():
            shutil.rmtree(package_dir)
        super().run()

        package_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SWIG_PROXY, package_dir / "steamworks.py")
        shutil.copy2(STEAM_RUNTIME_LIB, package_dir / STEAM_RUNTIME_LIB.name)


class SteamworksEggInfo(egg_info):
    def run(self) -> None:
        (Path(self.egg_info) / "SOURCES.txt").unlink(missing_ok=True)
        super().run()


class SteamworksBuildExt(build_ext):
    def run(self) -> None:
        generate_sources()
        super().run()

        package_dir = Path(self.build_lib) / "steamworks"
        package_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(STEAM_RUNTIME_LIB, package_dir / STEAM_RUNTIME_LIB.name)


extension = Extension(
    "steamworks._steamworks",
    sources=[
        setup_relative(SWIG_WRAPPER),
        setup_relative(SHIM_SOURCE),
        setup_relative(C_API_SOURCE),
    ],
    include_dirs=[str(STEAM_INCLUDE), str(GENERATED_DIR)],
    library_dirs=STEAM_CONFIG["library_dirs"],
    libraries=STEAM_CONFIG["libraries"],
    runtime_library_dirs=STEAM_CONFIG["runtime_library_dirs"],
    language="c++",
    extra_compile_args=STEAM_CONFIG["extra_compile_args"],
    extra_link_args=STEAM_CONFIG["extra_link_args"],
)


setup(
    packages=["steamworks"],
    package_dir={"steamworks": "python/steamworks"},
    package_data={"steamworks": ["libsteam_api.so", "libsteam_api.dylib", "steam_api.dll", "steam_api64.dll"]},
    ext_modules=[extension],
    cmdclass={
        "build_py": SteamworksBuildPy,
        "build_ext": SteamworksBuildExt,
        "egg_info": SteamworksEggInfo,
    },
)
