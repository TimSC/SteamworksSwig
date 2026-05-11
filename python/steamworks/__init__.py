"""Python bindings for the generated Steamworks SWIG wrapper."""

try:
    from .steamworks import *  # noqa: F401,F403
except ImportError as exc:
    raise ImportError(
        "The generated Steamworks extension is not available. "
        "Install this project with `pip install .` from the repository root."
    ) from exc
