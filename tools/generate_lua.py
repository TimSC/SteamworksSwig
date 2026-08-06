#!/usr/bin/env python3
"""Generate friendly Lua wrappers from the shared Steamworks C ABI model."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from generator_io import load_json, write_generated_text
from steamworks_model import (
    disambiguate_names,
    friendly_name,
    helper_name,
    method_params,
    model_methods,
    raw_c_name,
)
from steamworks_types import python_snake_name


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = ROOT / "generated" / "steamworks_c_api_model.json"
DEFAULT_OUTPUT = ROOT / "lua" / "steamworks.lua"

LUA_KEYWORDS = {
    "and",
    "break",
    "do",
    "else",
    "elseif",
    "end",
    "false",
    "for",
    "function",
    "goto",
    "if",
    "in",
    "local",
    "nil",
    "not",
    "or",
    "repeat",
    "return",
    "then",
    "true",
    "until",
    "while",
}

HAND_WRITTEN_METHODS = {
    "Global/static": {
        "SWS_Steam_ClearHelperState",
        "SWS_Steam_GetHSteamPipe",
        "SWS_Steam_GetHSteamUser",
        "SWS_Steam_GetLastInitError",
        "SWS_Steam_GetLastInitResult",
        "SWS_Steam_Init",
        "SWS_Steam_InitEx",
        "SWS_Steam_IsSteamRunning",
        "SWS_Steam_RunCallbacks",
        "SWS_Steam_Shutdown",
        "SWS_Steam_ShutdownManualDispatch",
    },
}


LUA_CALLBACK_HELPERS = """
local function unescape_callback_payload_value(value)
    if string.find(value, "\\\\", 1, true) == nil then
        return value
    end

    local result = {}
    local escaped = false
    for index = 1, #value do
        local ch = string.sub(value, index, index)
        if escaped then
            if ch == "t" then
                table.insert(result, "\\t")
            elseif ch == "n" then
                table.insert(result, "\\n")
            elseif ch == "r" then
                table.insert(result, "\\r")
            elseif ch == "\\\\" then
                table.insert(result, "\\\\")
            else
                table.insert(result, "\\\\")
                table.insert(result, ch)
            end
            escaped = false
        elseif ch == "\\\\" then
            escaped = true
        else
            table.insert(result, ch)
        end
    end
    if escaped then
        table.insert(result, "\\\\")
    end
    return table.concat(result)
end

function steamworks.parse_callback_payload(data)
    local payload = {}
    if data == nil or data == "" then
        return payload
    end

    for field in string.gmatch(data, "[^\\t]+") do
        local separator = string.find(field, "=", 1, true)
        if separator ~= nil and separator > 1 then
            local key = string.sub(field, 1, separator - 1)
            local value = string.sub(field, separator + 1)
            payload[key] = unescape_callback_payload_value(value)
        end
    end
    return payload
end

local function attach_callback_payload_methods(callback)
    function callback:payload()
        return steamworks.parse_callback_payload(self.data)
    end
    function callback:api_call_result_payload()
        return steamworks.parse_callback_payload(self.api_call_result_data)
    end
    return callback
end

function steamworks.manual_dispatch_init()
    raw.SWS_Steam_ManualDispatch_Init()
end

function steamworks.manual_dispatch_run_frame()
    raw.SWS_Steam_ManualDispatch_RunFrame(raw.SWS_Steam_GetHSteamPipe())
end

function steamworks.callback_dispatch_mode()
    return raw.SWS_Steam_GetCallbackDispatchMode()
end

function steamworks.poll_callback()
    local pipe = raw.SWS_Steam_GetHSteamPipe()
    raw.SWS_Steam_ManualDispatch_RunFrame(pipe)
    if not raw.SWS_Steam_ManualDispatch_GetNextCallback(pipe) then
        return nil
    end

    local callback = {
        steam_user = raw.SWS_Steam_ManualDispatch_GetCallbackSteamUser(),
        id = raw.SWS_Steam_ManualDispatch_GetCallbackID(),
        data = raw.SWS_Steam_ManualDispatch_GetCallbackData(),
        size = raw.SWS_Steam_ManualDispatch_GetCallbackSize(),
        api_call_completed = raw.SWS_Steam_ManualDispatch_CallbackIsAPICallCompleted(),
    }

    if callback.api_call_completed then
        callback.completed_api_call = raw.SWS_Steam_ManualDispatch_GetCompletedAPICall()
        callback.completed_callback_id = raw.SWS_Steam_ManualDispatch_GetCompletedCallbackID()
        callback.completed_callback_size = raw.SWS_Steam_ManualDispatch_GetCompletedCallbackSize()
        if raw.SWS_Steam_ManualDispatch_GetAPICallResult(
            pipe,
            callback.completed_api_call,
            callback.completed_callback_size,
            callback.completed_callback_id
        ) then
            callback.api_call_result_data = raw.SWS_Steam_ManualDispatch_GetAPICallResultData()
            callback.api_call_result_failed = raw.SWS_Steam_ManualDispatch_GetAPICallResultFailed()
        end
    end

    raw.SWS_Steam_ManualDispatch_FreeLastCallback(pipe)
    return attach_callback_payload_methods(callback)
end

function steamworks.poll_callbacks(handler)
    local count = 0
    while true do
        local callback = steamworks.poll_callback()
        if callback == nil then
            return count
        end
        count = count + 1
        if handler ~= nil then
            handler(callback)
        end
    end
end

function steamworks.on_callback_id(callback_id, handler)
    return function(callback)
        if callback.id == callback_id and handler ~= nil then
            handler(callback)
        end
    end
end
"""


def lua_name(value: str, *, drop_get: bool = False) -> str:
    name = python_snake_name(value, drop_get=drop_get)
    if name in LUA_KEYWORDS:
        return name + "_value"
    return name or "value"


def instance_name(interface: str) -> str:
    if interface == "Global/static":
        return ""
    return lua_name(interface)


def grouped_helper_method_name(interface: str, model_helper_name: str, raw_name: str, *, drop_get: bool = True) -> str:
    name = model_helper_name or raw_name.removeprefix("SWS_")
    if name.startswith("Steam_"):
        name = name[len("Steam_"):]
    if interface and interface != "Global/static":
        prefix = interface + "_"
        if name.startswith(prefix):
            name = name[len(prefix):]
    return lua_name(name, drop_get=drop_get)


def method_candidates(model: dict) -> list[tuple[str, str, str, dict]]:
    candidates = []
    for method in model_methods(model):
        interface = method.get("interface")
        c_name = raw_c_name(method)
        if not interface or not c_name:
            continue
        if c_name in HAND_WRITTEN_METHODS.get(interface, set()):
            continue
        if method.get("source") == "sdk":
            method_name = friendly_name(method)
            if not method_name:
                continue
            grouped_name = lua_name(method_name)
        else:
            grouped_name = grouped_helper_method_name(interface, helper_name(method), c_name)
        candidates.append((interface, grouped_name, c_name, method))
    return candidates


def collision_name(candidate: tuple[str, str, str, dict]) -> str:
    interface, _, c_name, method = candidate
    if method.get("source") == "sdk":
        sdk_flat_name = method.get("sdk_flat_name") or c_name
        prefix = f"SteamAPI_ISteam{interface}_"
        return lua_name(sdk_flat_name.removeprefix(prefix), drop_get=False)
    return grouped_helper_method_name(interface, helper_name(method), c_name, drop_get=False)


def param_names_and_args(method: dict) -> tuple[list[str], list[str]]:
    params = []
    args = []
    seen: Counter[str] = Counter()
    raw_params = method_params(method)
    index = 0
    while index < len(raw_params):
        param = raw_params[index]
        name = lua_name(param.get("name", "arg"))
        if (
            param.get("c_type") == "const uint8_t *"
            and index + 1 < len(raw_params)
            and raw_params[index + 1].get("c_type") == "size_t"
            and raw_params[index + 1].get("name") == f'{param.get("name")}Size'
        ):
            seen[name] += 1
            if seen[name] > 1:
                name = f"{name}_{seen[name]}"
            params.append(name)
            args.append(name)
            index += 2
            continue

        seen[name] += 1
        if seen[name] > 1:
            name = f"{name}_{seen[name]}"
        params.append(name)
        args.append(name)
        index += 1
    return params, args


def generate(model: dict) -> str:
    interfaces: dict[str, list[dict]] = {}
    module_functions: list[dict] = []
    candidates = method_candidates(model)
    named_candidates = disambiguate_names(
        candidates,
        key=lambda candidate: candidate[0],
        name=lambda candidate: candidate[1],
        fallback_name=lambda candidate: collision_name(candidate),
    )

    for (interface, _, c_name, method), grouped_name in named_candidates:
        params, args = param_names_and_args(method)
        item = {
            "name": grouped_name,
            "raw_c_name": c_name,
            "params": params,
            "args": args,
        }
        if interface == "Global/static":
            module_functions.append(item)
        else:
            interfaces.setdefault(interface, []).append(item)

    lines = [
        "-- Friendly Lua wrappers for the generated Steamworks module.",
        "-- Code generated by tools/generate_lua.py; DO NOT EDIT.",
        "",
        'local raw = require("steamworks_raw")',
        "",
        "local steamworks = {}",
        "",
        "function steamworks.is_steam_running()",
        "    return raw.SWS_Steam_IsSteamRunning()",
        "end",
        "",
        "function steamworks.init()",
        "    local result = raw.SWS_Steam_InitEx()",
        "    if result == 0 then",
        "        return true",
        "    end",
        "    local message = raw.SWS_Steam_GetLastInitError()",
        "    if message == nil or message == \"\" then",
        "        message = string.format(\"Steam_InitEx failed with result %d\", result)",
        "    end",
        "    return nil, message, result",
        "end",
        "",
        "function steamworks.shutdown()",
        "    raw.SWS_Steam_ClearHelperState()",
        "    raw.SWS_Steam_Shutdown()",
        "end",
        "",
        "function steamworks.shutdown_manual_dispatch()",
        "    raw.SWS_Steam_ShutdownManualDispatch()",
        "end",
        "",
        "function steamworks.run_callbacks()",
        "    raw.SWS_Steam_RunCallbacks()",
        "end",
        "",
        "function steamworks.hsteam_pipe_value()",
        "    return raw.SWS_Steam_GetHSteamPipe()",
        "end",
        "",
        "function steamworks.hsteam_user_value()",
        "    return raw.SWS_Steam_GetHSteamUser()",
        "end",
        "",
        "function steamworks.raw()",
        "    return raw",
        "end",
        "",
    ]

    for interface in sorted(interfaces):
        table_name = instance_name(interface)
        lines.extend([f"steamworks.{table_name} = {{}}", ""])
        for item in sorted(interfaces[interface], key=lambda value: value["name"]):
            params = ", ".join(item["params"])
            args = ", ".join(item["args"])
            call = f'raw.{item["raw_c_name"]}({args})' if args else f'raw.{item["raw_c_name"]}()'
            lines.append(f"function steamworks.{table_name}.{item['name']}({params})")
            lines.append(f"    return {call}")
            lines.append("end")
            lines.append("")

    for item in sorted(module_functions, key=lambda value: value["name"]):
        params = ", ".join(item["params"])
        args = ", ".join(item["args"])
        call = f'raw.{item["raw_c_name"]}({args})' if args else f'raw.{item["raw_c_name"]}()'
        lines.append(f"function steamworks.{item['name']}({params})")
        lines.append(f"    return {call}")
        lines.append("end")
        lines.append("")

    lines.extend(LUA_CALLBACK_HELPERS.strip().splitlines())
    lines.append("")
    lines.append("return steamworks")
    lines.append("")
    return "\n".join(lines)


def write_lua_wrappers(model_path: Path, output_path: Path) -> None:
    write_generated_text(output_path, generate(load_json(model_path)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=str(DEFAULT_MODEL), help="Path to steamworks_c_api_model.json")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="Lua wrapper output path")
    args = parser.parse_args()

    write_lua_wrappers(Path(args.model), Path(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
