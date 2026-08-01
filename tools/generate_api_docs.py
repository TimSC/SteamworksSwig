#!/usr/bin/env python3
"""Generate API coverage docs from the shared C ABI model."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "generated" / "steamworks_c_api_model.json"
DEFAULT_OUTPUT = ROOT / "docs" / "API_COVERAGE.md"


def percentage(part: int, total: int) -> str:
    if total == 0:
        return "-"
    return f"{(part / total) * 100:.1f}%"


def source_label(source: str | None) -> str:
    return {
        "sdk": "SDK methods",
        "manual": "Manual lifecycle/global helpers",
        "helper": "Curated C-safe helpers",
        "manual_dispatch": "Manual-dispatch callback helpers",
    }.get(source or "", source or "Unknown")


def generate(model: dict) -> str:
    summary = model.get("summary", {})
    methods = model.get("methods", [])
    skipped = model.get("skipped_methods", [])

    sdk_by_interface: Counter[str] = Counter()
    supported_by_interface: Counter[str] = Counter()
    skipped_by_interface: Counter[str] = Counter()
    helper_by_interface: Counter[str] = Counter()
    skipped_reasons: Counter[str] = Counter()
    by_source: Counter[str] = Counter()

    for method in methods:
        source = method.get("source", "sdk")
        by_source[source] += 1
        interface = method.get("interface") or "Global/static"
        if source == "sdk":
            supported_by_interface[interface] += 1
        elif source in {"manual", "helper", "manual_dispatch"}:
            helper_by_interface[interface] += 1

    for item in skipped:
        interface = item.get("interface") or "Global/static"
        skipped_by_interface[interface] += 1
        skipped_reasons[item.get("reason") or "unknown"] += 1

    for interface in set(supported_by_interface) | set(skipped_by_interface):
        sdk_by_interface[interface] = supported_by_interface[interface] + skipped_by_interface[interface]

    sdk_total = int(summary.get("sdk_methods_total", sum(sdk_by_interface.values())))
    sdk_supported = int(summary.get("sdk_methods_supported", sum(supported_by_interface.values())))
    sdk_skipped = int(summary.get("sdk_methods_skipped", len(skipped)))
    c_total = int(summary.get("c_abi_functions_total", len(methods)))

    lines = [
        "# API Coverage",
        "",
        "This file is generated from `generated/steamworks_c_api_model.json`.",
        "Regenerate it after changing the SDK, C ABI generator, or curated helper list.",
        "",
        "## Summary",
        "",
        f"- SDK interface methods supported by the generated C ABI: {sdk_supported} of {sdk_total} ({percentage(sdk_supported, sdk_total)})",
        f"- SDK interface methods currently skipped: {sdk_skipped}",
        f"- Total C ABI functions, including manual helpers: {c_total}",
        "",
        "## C ABI Function Sources",
        "",
        "| Source | Functions |",
        "| --- | ---: |",
    ]
    for source, count in sorted(by_source.items(), key=lambda item: source_label(item[0])):
        lines.append(f"| {source_label(source)} | {count} |")

    lines.extend(
        [
            "",
            "## Interface Coverage",
            "",
            "| Steamworks group | SDK methods | C ABI methods | Coverage | Curated/helper funcs |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for interface in sorted(sdk_by_interface):
        total = sdk_by_interface[interface]
        supported = supported_by_interface[interface]
        helpers = helper_by_interface[interface]
        lines.append(
            f"| `{interface}` | {total} | {supported} | {percentage(supported, total)} | {helpers} |"
        )

    lines.extend(
        [
            "",
            "## Skipped Reasons",
            "",
            "| Reason | Methods |",
            "| --- | ---: |",
        ]
    )
    for reason, count in sorted(skipped_reasons.items()):
        lines.append(f"| `{reason}` | {count} |")

    examples_by_reason: defaultdict[str, list[dict]] = defaultdict(list)
    for item in skipped:
        reason = item.get("reason") or "unknown"
        if len(examples_by_reason[reason]) < 5:
            examples_by_reason[reason].append(item)

    lines.extend(["", "## Skipped Examples", ""])
    for reason in sorted(examples_by_reason):
        lines.append(f"### `{reason}`")
        lines.append("")
        lines.append("| Interface | Method | Detail |")
        lines.append("| --- | --- | --- |")
        for item in examples_by_reason[reason]:
            interface = item.get("interface") or ""
            method = item.get("methodname") or item.get("flat_name") or ""
            detail = item.get("detail") or item.get("return_type") or ""
            lines.append(f"| `{interface}` | `{method}` | `{detail}` |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="Path to steamworks_c_api_model.json")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Markdown output path")
    args = parser.parse_args()

    model_path = Path(args.model)
    output_path = Path(args.output)
    model = json.loads(model_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generate(model), encoding="utf-8")
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
