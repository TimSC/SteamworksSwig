#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SDK_DIR="${STEAMWORKS_SDK_DIR:-"$ROOT_DIR/sdk"}"
CONTAINER_ENGINE="${CONTAINER_ENGINE:-docker}"
MANYLINUX_IMAGE="${MANYLINUX_IMAGE:-quay.io/pypa/manylinux2014_x86_64}"
PYTHON_TAGS="${PYTHON_TAGS:-cp39-cp39 cp310-cp310 cp311-cp311 cp312-cp312 cp313-cp313 cp314-cp314 cp315-cp315}"
WHEELHOUSE="${WHEELHOUSE:-"$ROOT_DIR/wheelhouse"}"

usage() {
    cat <<'EOF'
Build and repair manylinux wheels for SteamworksSwig.

Usage:
  tools/build_manylinux_wheels.sh [options]

Options:
  --sdk-dir PATH       Steamworks SDK path (default: $STEAMWORKS_SDK_DIR or ./sdk)
  --python-tags TAGS   Space-separated /opt/python tags
  --wheelhouse PATH    Output directory (default: ./wheelhouse)
  --image IMAGE        manylinux image
  --engine COMMAND     Container engine: docker or podman
  -h, --help           Show this help

Environment variables provide the same configuration:
  STEAMWORKS_SDK_DIR, PYTHON_TAGS, WHEELHOUSE,
  MANYLINUX_IMAGE, CONTAINER_ENGINE

Example:
  tools/build_manylinux_wheels.sh \
    --sdk-dir sdk_158a \
    --python-tags "cp311-cp311 cp312-cp312"
EOF
}

while (($#)); do
    case "$1" in
        --sdk-dir)
            SDK_DIR="$2"
            shift 2
            ;;
        --python-tags)
            PYTHON_TAGS="$2"
            shift 2
            ;;
        --wheelhouse)
            WHEELHOUSE="$2"
            shift 2
            ;;
        --image)
            MANYLINUX_IMAGE="$2"
            shift 2
            ;;
        --engine)
            CONTAINER_ENGINE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if ! command -v "$CONTAINER_ENGINE" >/dev/null 2>&1; then
    echo "Container engine not found: $CONTAINER_ENGINE" >&2
    exit 1
fi

SDK_DIR="$(realpath "$SDK_DIR")"
WHEELHOUSE="$(realpath -m "$WHEELHOUSE")"

if [[ ! -f "$SDK_DIR/public/steam/steam_api.json" ]]; then
    echo "Steamworks SDK not found at: $SDK_DIR" >&2
    echo "Expected: $SDK_DIR/public/steam/steam_api.json" >&2
    exit 1
fi

mkdir -p "$WHEELHOUSE"

"$CONTAINER_ENGINE" run --rm \
    -e "PYTHON_TAGS=$PYTHON_TAGS" \
    -v "$ROOT_DIR:/project" \
    -v "$SDK_DIR:/steamworks-sdk:ro" \
    -v "$WHEELHOUSE:/wheelhouse" \
    -w /project \
    "$MANYLINUX_IMAGE" \
    bash -lc '
        set -euo pipefail

        rm -rf /tmp/steamworks-raw-wheels
        mkdir -p /tmp/steamworks-raw-wheels
        rm -f /wheelhouse/*.whl

        for tag in $PYTHON_TAGS; do
            python="/opt/python/$tag/bin/python"
            if [[ ! -x "$python" ]]; then
                echo "Python interpreter not available in image: $python" >&2
                exit 1
            fi

            raw_dir="/tmp/steamworks-raw-wheels/$tag"
            mkdir -p "$raw_dir"

            "$python" -m pip install --upgrade \
                "setuptools>=77" \
                wheel \
                build

            STEAMWORKS_SDK_DIR=/steamworks-sdk \
                "$python" -m build \
                --wheel \
                --no-isolation \
                --skip-dependency-check \
                --outdir "$raw_dir"

            auditwheel show "$raw_dir"/*.whl
            auditwheel repair "$raw_dir"/*.whl --wheel-dir /wheelhouse
        done
    '

echo "Built manylinux wheels:"
find "$WHEELHOUSE" -maxdepth 1 -type f -name '*.whl' -print | sort
