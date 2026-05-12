from __future__ import annotations

import shutil
import subprocess
import sys
import platform
from pathlib import Path

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext
from setuptools.command.build_py import build_py


ROOT = Path(__file__).parent.resolve()
SDK_DIR = ROOT / "sdk"
STEAM_INCLUDE = SDK_DIR / "public"
GENERATED_DIR = ROOT / "generated"
GENERATOR = ROOT / "tools" / "generate_swig_shim.py"
API_JSON = STEAM_INCLUDE / "steam" / "steam_api.json"
SWIG_INTERFACE = GENERATED_DIR / "steamworks.i"
SWIG_PROXY = GENERATED_DIR / "steamworks.py"
SWIG_WRAPPER = GENERATED_DIR / "steamworks_wrap.cpp"
SHIM_SOURCE = GENERATED_DIR / "steamworks_swig_shim.cpp"


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


def generate_sources() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(
        [
            sys.executable,
            str(GENERATOR),
            "--api-json",
            str(API_JSON),
            "--output-dir",
            str(GENERATED_DIR),
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
        super().run()

        package_dir = Path(self.build_lib) / "steamworks"
        package_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SWIG_PROXY, package_dir / "steamworks.py")
        shutil.copy2(STEAM_RUNTIME_LIB, package_dir / STEAM_RUNTIME_LIB.name)


class SteamworksBuildExt(build_ext):
    def run(self) -> None:
        generate_sources()
        super().run()

        package_dir = Path(self.build_lib) / "steamworks"
        package_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(STEAM_RUNTIME_LIB, package_dir / STEAM_RUNTIME_LIB.name)


extension = Extension(
    "steamworks._steamworks",
    sources=[str(SWIG_WRAPPER), str(SHIM_SOURCE)],
    include_dirs=[str(STEAM_INCLUDE), str(GENERATED_DIR)],
    library_dirs=STEAM_CONFIG["library_dirs"],
    libraries=STEAM_CONFIG["libraries"],
    runtime_library_dirs=STEAM_CONFIG["runtime_library_dirs"],
    language="c++",
    extra_compile_args=STEAM_CONFIG["extra_compile_args"],
    extra_link_args=STEAM_CONFIG["extra_link_args"],
)


setup(
    name="steamworks-swig",
    version="0.1.0",
    description="Generated Python bindings for the Steamworks SDK flat API",
    license="BSD-3-Clause",
    license_files=["LICENSE"],
    classifiers=[
        "License :: OSI Approved :: BSD License",
    ],
    packages=["steamworks"],
    package_dir={"steamworks": "python/steamworks"},
    package_data={"steamworks": ["libsteam_api.so", "libsteam_api.dylib", "steam_api.dll", "steam_api64.dll"]},
    ext_modules=[extension],
    cmdclass={
        "build_py": SteamworksBuildPy,
        "build_ext": SteamworksBuildExt,
    },
    python_requires=">=3.9",
)
