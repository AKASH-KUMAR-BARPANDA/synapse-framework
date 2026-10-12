import 'dart:async';
import 'dart:io';
import 'package:http/http.dart' as http;

/// Automatically starts the local Ollama daemon and Python FastAPI server
/// in the background when the Desktop app is opened, so the user never has
/// to manually start any terminal servers.
class BackendLauncher {
  BackendLauncher._();

  static Process? _backendProcess;
  static Process? _ollamaProcess;
  static bool _isStarting = false;

  /// Ensures `http://127.0.0.1:8000/health` is running on macOS/Windows/Linux.
  static Future<bool> ensureLocalBackendRunning() async {
    if (!Platform.isMacOS && !Platform.isWindows && !Platform.isLinux) {
      return false;
    }

    if (await _isPortHealthy('http://127.0.0.1:8000/health')) {
      return true;
    }

    if (_isStarting) {
      return _waitForHealth(maxAttempts: 12);
    }

    _isStarting = true;
    try {
      // 1. Ensure Ollama is running on port 11434 if installed
      await _ensureOllamaRunning();

      // 2. Locate the Synapse project root containing `app/api/server.py`
      final projectRoot = _resolveProjectRoot();
      if (projectRoot == null) {
        return false;
      }

      // 3. Find the Python / uvicorn executable inside `.venv` or `uv`
      final venvPython = File('$projectRoot/.venv/bin/python');
      final uvBinary = _findExecutable([
        '/Library/Frameworks/Python.framework/Versions/3.14/bin/uv',
        '/opt/homebrew/bin/uv',
        '/usr/local/bin/uv',
        '${Platform.environment['HOME'] ?? ''}/.local/bin/uv',
        '${Platform.environment['HOME'] ?? ''}/.cargo/bin/uv',
      ]);

      final env = Map<String, String>.from(Platform.environment);
      env['PYTHONPATH'] = projectRoot;

      if (venvPython.existsSync()) {
        _backendProcess = await Process.start(
          venvPython.path,
          [
            '-m',
            'uvicorn',
            'app.api.server:app',
            '--host',
            '0.0.0.0',
            '--port',
            '8000',
          ],
          workingDirectory: projectRoot,
          environment: env,
          mode: ProcessStartMode.detachedWithStdio,
        );
      } else if (uvBinary != null) {
        _backendProcess = await Process.start(
          uvBinary,
          [
            'run',
            'uvicorn',
            'app.api.server:app',
            '--host',
            '0.0.0.0',
            '--port',
            '8000',
          ],
          workingDirectory: projectRoot,
          environment: env,
          mode: ProcessStartMode.detachedWithStdio,
        );
      } else {
        return false;
      }

      // Drain stdout/stderr so pipes never block
      _backendProcess?.stdout.drain<void>();
      _backendProcess?.stderr.drain<void>();

      return await _waitForHealth(maxAttempts: 16);
    } catch (_) {
      return false;
    } finally {
      _isStarting = false;
    }
  }

  static Future<void> _ensureOllamaRunning() async {
    try {
      final res = await http
          .get(Uri.parse('http://127.0.0.1:11434/api/tags'))
          .timeout(const Duration(milliseconds: 900));
      if (res.statusCode == 200) return;
    } catch (_) {}

    final ollamaBin = _findExecutable([
      '/opt/homebrew/bin/ollama',
      '/usr/local/bin/ollama',
      '/usr/bin/ollama',
    ]);
    if (ollamaBin == null) return;

    try {
      _ollamaProcess = await Process.start(
        ollamaBin,
        ['serve'],
        mode: ProcessStartMode.detachedWithStdio,
      );
      _ollamaProcess?.stdout.drain<void>();
      _ollamaProcess?.stderr.drain<void>();
    } catch (_) {}
  }

  static String? _resolveProjectRoot() {
    final candidates = <String>[
      '/Users/akash/Documents/projects/Synapse',
      Directory.current.path,
      Directory.current.parent.path,
    ];

    // Also inspect relative to the macOS .app bundle path if packaged inside project
    try {
      var dir = File(Platform.resolvedExecutable).parent;
      for (int i = 0; i < 8; i++) {
        candidates.add(dir.path);
        dir = dir.parent;
      }
    } catch (_) {}

    for (final path in candidates) {
      if (File('$path/app/api/server.py').existsSync()) {
        return path;
      }
    }
    return null;
  }

  static String? _findExecutable(List<String> paths) {
    for (final p in paths) {
      if (p.isNotEmpty && File(p).existsSync()) {
        return p;
      }
    }
    return null;
  }

  static Future<bool> _isPortHealthy(String url) async {
    try {
      final response = await http
          .get(Uri.parse(url))
          .timeout(const Duration(milliseconds: 1200));
      return response.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  static Future<bool> _waitForHealth({int maxAttempts = 14}) async {
    for (int i = 0; i < maxAttempts; i++) {
      if (await _isPortHealthy('http://127.0.0.1:8000/health')) {
        return true;
      }
      await Future<void>.delayed(const Duration(milliseconds: 500));
    }
    return false;
  }
}
