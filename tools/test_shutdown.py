#!/usr/bin/env python3
"""Compile actual shutdown helper bodies against a deterministic fake SDK.

Run: python3 -m unittest discover -s tools -p 'test_shutdown.py'
No Steam client or SDK installation is required.
"""
import pathlib
import shutil
import subprocess
import tempfile
import unittest

TEMPLATE = pathlib.Path(__file__).parent / 'templates' / 'steamworks_helpers.cpp.in'


def function(source, signature):
    start = source.index(signature + '\n{')
    end = source.index('{', start)
    depth = 1
    pos = end + 1
    while depth:
        if source[pos] == '{':
            depth += 1
        elif source[pos] == '}':
            depth -= 1
        pos += 1
    return source[start:pos]


class ShutdownTests(unittest.TestCase):
    def test_native_callback_ownership_and_shutdown(self):
        compiler = shutil.which('c++')
        self.assertIsNotNone(compiler, 'a C++ compiler is required')
        source = TEMPLATE.read_text()
        signatures = [
            'void ReleaseManualDispatchCallback( HSteamPipe pipe )',
            'void ResetDispatchModeIfUnused()',
            'void Steam_Shutdown()',
            'void Steam_ShutdownManualDispatch()',
            'void Steam_GameServer_Shutdown()',
            'bool Steam_ManualDispatch_GetNextCallback( HSteamPipe pipe )',
            'void Steam_ManualDispatch_FreeLastCallback( HSteamPipe pipe )',
        ]
        bodies = '\n'.join(function(source, signature) for signature in signatures)
        # Use production global definitions, including the owning pipe.
        globals_start = source.index('std::atomic<int> g_callbackDispatchMode')
        globals_end = source.index('{{ manual_dispatch_serializer_forward_declarations }}')
        program = r'''
#include <atomic>
#include <cassert>
#include <stdexcept>
#include <string>
using HSteamPipe = int;
using SteamErrMsg = char[1024];
using SteamworksBytes = std::string;
struct CallbackMsg_t { int m_hSteamUser=0, m_iCallback=0, m_cubParam=0; unsigned char *m_pubParam=nullptr; };
constexpr int k_CallbackDispatchModeUninitialized=0, k_CallbackDispatchModeAutomatic=1, k_CallbackDispatchModeManual=2;
int client=1, server=0, nativeOwner=0, releases=0, clientStops=0, serverStops=0, clears=0;
bool throwOnClear=false, offerCallback=true;
int SteamAPI_GetHSteamPipe() { return client; }
int SteamGameServer_GetHSteamPipe() { return server; }
void SteamAPI_ManualDispatch_FreeLastCallback(int pipe) {
    assert(pipe == nativeOwner); nativeOwner=0; ++releases;
}
bool SteamAPI_ManualDispatch_GetNextCallback(int pipe, CallbackMsg_t *callback) {
    assert(!nativeOwner);
    if (!offerCallback) return false;
    nativeOwner=pipe; static unsigned char payload[]="event";
    callback->m_pubParam=payload; callback->m_cubParam=5; return true;
}
void Steam_ClearHelperState() {
    assert(client); ++clears;
    if (throwOnClear) throw std::runtime_error("cleanup failed");
}
void SteamAPI_Shutdown() { assert(client && nativeOwner!=client); client=0; ++clientStops; }
void SteamGameServer_Shutdown() { assert(server && nativeOwner!=server); server=0; ++serverStops; }
void RequireCallbackDispatchMode(int, const char *);
''' + source[globals_start:globals_end] + r'''
void RequireCallbackDispatchMode(int mode, const char *) {
    if (g_callbackDispatchMode.load()!=mode) throw std::logic_error("wrong mode");
}
''' + bodies + r'''
int main() {
    g_callbackDispatchMode=2;
    assert(Steam_ManualDispatch_GetNextCallback(1));
    try { Steam_ManualDispatch_GetNextCallback(1); assert(false); } catch(const std::logic_error&) {}
    try { Steam_ManualDispatch_FreeLastCallback(2); assert(false); } catch(const std::logic_error&) {}
    assert(nativeOwner==1 && g_manualDispatchHasCallback);
    // Failed prerequisite cleanup preserves the SDK and callback for retry.
    throwOnClear=true;
    try { Steam_Shutdown(); assert(false); } catch(const std::runtime_error&) {}
    assert(client && clientStops==0 && nativeOwner==1 && g_manualDispatchHasCallback);
    throwOnClear=false;
    Steam_Shutdown();
    assert(clientStops==1 && releases==1 && !g_manualDispatchHasCallback);
    assert(g_manualDispatchCallbackData.empty() && g_manualDispatchCallbackPipe==0);
    assert(g_callbackDispatchMode==0);
    Steam_ShutdownManualDispatch(); assert(clientStops==1);
    // Shutting down one API preserves the other API's mode and callback.
    client=1; server=2; g_callbackDispatchMode=2;
    assert(Steam_ManualDispatch_GetNextCallback(2));
    Steam_Shutdown();
    assert(g_callbackDispatchMode==2 && nativeOwner==2);
    Steam_GameServer_Shutdown();
    assert(serverStops==1 && releases==2 && g_callbackDispatchMode==0);
    Steam_GameServer_Shutdown(); assert(serverStops==1);
    // Reverse shutdown order, retaining the client's callback.
    client=1; server=2; g_callbackDispatchMode=2;
    assert(Steam_ManualDispatch_GetNextCallback(1));
    Steam_GameServer_Shutdown();
    assert(g_callbackDispatchMode==2 && nativeOwner==1);
    Steam_ShutdownManualDispatch(); assert(g_callbackDispatchMode==0 && releases==3);
    // Explicit free is idempotent, and empty fetches retain no ownership.
    client=1; g_callbackDispatchMode=2;
    assert(Steam_ManualDispatch_GetNextCallback(1));
    Steam_ManualDispatch_FreeLastCallback(1);
    Steam_ManualDispatch_FreeLastCallback(1); assert(releases==4);
    offerCallback=false;
    assert(!Steam_ManualDispatch_GetNextCallback(1));
    Steam_Shutdown(); assert(releases==4);
    // Automatic shutdown must not require/pump manual or automatic callbacks.
    client=1; g_callbackDispatchMode=1; Steam_Shutdown();
    assert(g_callbackDispatchMode==0);
}
'''
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory)
            (path / 'shutdown.cpp').write_text(program)
            subprocess.run([compiler, '-std=c++17', '-Wall', '-Wextra', '-Werror',
                            str(path / 'shutdown.cpp'), '-o', str(path / 'shutdown')], check=True)
            subprocess.run([str(path / 'shutdown')], check=True, timeout=10)


if __name__ == '__main__':
    unittest.main()
