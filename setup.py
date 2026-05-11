from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext
from setuptools.command.build_py import build_py


ROOT = Path(__file__).parent.resolve()
SDK_DIR = ROOT / "sdk"
STEAM_INCLUDE = SDK_DIR / "public"
STEAM_LIB_DIR = SDK_DIR / "redistributable_bin" / "linux64"
STEAM_RUNTIME_LIB = STEAM_LIB_DIR / "libsteam_api.so"
GENERATED_DIR = ROOT / "generated"
GENERATOR = ROOT / "tools" / "generate_swig_shim.py"
API_JSON = STEAM_INCLUDE / "steam" / "steam_api.json"
SWIG_INTERFACE = GENERATED_DIR / "steamworks.i"
SWIG_PROXY = GENERATED_DIR / "steamworks.py"
SWIG_WRAPPER = GENERATED_DIR / "steamworks_wrap.cpp"
SHIM_SOURCE = GENERATED_DIR / "steamworks_swig_shim.cpp"


def generate_sources() -> None:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(
        [
            "python3",
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
        shutil.copy2(STEAM_RUNTIME_LIB, package_dir / "libsteam_api.so")


class SteamworksBuildExt(build_ext):
    def run(self) -> None:
        generate_sources()
        super().run()

        package_dir = Path(self.build_lib) / "steamworks"
        package_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(STEAM_RUNTIME_LIB, package_dir / "libsteam_api.so")


extension = Extension(
    "steamworks._steamworks",
    sources=[str(SWIG_WRAPPER), str(SHIM_SOURCE)],
    include_dirs=[str(STEAM_INCLUDE), str(GENERATED_DIR)],
    library_dirs=[str(STEAM_LIB_DIR)],
    libraries=["steam_api"],
    runtime_library_dirs=["$ORIGIN"],
    language="c++",
    extra_compile_args=["-std=c++17"],
)


setup(
    name="steamworks-swig",
    version="0.1.0",
    description="Generated Python bindings for the Steamworks SDK flat API",
    packages=["steamworks"],
    package_dir={"steamworks": "python/steamworks"},
    package_data={"steamworks": ["libsteam_api.so"]},
    ext_modules=[extension],
    cmdclass={
        "build_py": SteamworksBuildPy,
        "build_ext": SteamworksBuildExt,
    },
    python_requires=">=3.9",
)
