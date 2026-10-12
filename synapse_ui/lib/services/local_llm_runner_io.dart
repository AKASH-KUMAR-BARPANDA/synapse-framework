import 'dart:async';
import 'dart:io';
import 'package:http/http.dart' as http;
import 'package:llama_flutter_android/llama_flutter_android.dart' as llama;
import 'package:path_provider/path_provider.dart';

import '../models/message.dart';

/// Progress snapshot emitted during GGUF model download.
class ModelDownloadProgress {
  final int receivedBytes;
  final int totalBytes;
  final double progress;
  final double speedMBps;

  const ModelDownloadProgress({
    required this.receivedBytes,
    required this.totalBytes,
    required this.progress,
    required this.speedMBps,
  });

  int get receivedMB => (receivedBytes / (1024 * 1024)).round();
  int get totalMB => (totalBytes / (1024 * 1024)).round();
}

/// Real on-device GGUF downloader and `llama.cpp` inference runner for Android.
/// Downloads `qwen2.5-0.5b-instruct-q4_k_m.gguf` (~469 MB) from HuggingFace
/// and executes native ARM64 token streaming via `llama_flutter_android`.
class LocalLlmRunner {
  static const String kHuggingFaceGgufUrl =
      'https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf?download=true';
  static const String kModelFileName = 'qwen2.5-0.5b-instruct-q4_k_m.gguf';
  static const int kExpectedModelBytes = 491400032; // ~468.6 MB (469 MB)
  static const int kMinValidModelBytes = 340 * 1024 * 1024; // 340 MB sanity check

  http.Client? _downloadClient;
  bool _cancelRequested = false;

  llama.LlamaController? _controller;
  String? _loadedModelPath;
  Completer<void>? _loadLock;

  Future<File> _getTargetFile() async {
    final dir = await getApplicationSupportDirectory();
    return File('${dir.path}/$kModelFileName');
  }

  Future<File> _getPartFile() async {
    final dir = await getApplicationSupportDirectory();
    return File('${dir.path}/$kModelFileName.part');
  }

  /// Verifies that the actual `.gguf` file exists on disk and is >= 340 MB.
  Future<bool> isModelPresentOnDisk() async {
    if (!Platform.isAndroid) return true;
    try {
      final file = await _getTargetFile();
      if (!await file.exists()) return false;
      final len = await file.length();
      return len >= kMinValidModelBytes;
    } catch (_) {
      return false;
    }
  }

  Future<String?> getModelFilePath() async {
    try {
      final file = await _getTargetFile();
      if (await file.exists() && await file.length() >= kMinValidModelBytes) {
        return file.path;
      }
    } catch (_) {}
    return null;
  }

  /// Streams the real 379 MB GGUF file from HuggingFace to local app storage
  /// with live byte count, Content-Length percentage, and MB/s speed.
  Future<bool> downloadModel({
    required void Function(ModelDownloadProgress progress) onProgress,
  }) async {
    _cancelRequested = false;
    _downloadClient?.close();
    final client = http.Client();
    _downloadClient = client;

    IOSink? sink;
    try {
      final targetFile = await _getTargetFile();
      final partFile = await _getPartFile();

      // Resume support if a partial file exists on disk
      int existingBytes = 0;
      if (await partFile.exists()) {
        existingBytes = await partFile.length();
        if (existingBytes >= kExpectedModelBytes) {
          await partFile.delete();
          existingBytes = 0;
        }
      }

      final request = http.Request('GET', Uri.parse(kHuggingFaceGgufUrl));
      request.headers['User-Agent'] = 'Synapse-Mobile/1.0';
      if (existingBytes > 0) {
        request.headers['Range'] = 'bytes=$existingBytes-';
      }

      final response = await client
          .send(request)
          .timeout(const Duration(seconds: 30));

      if (response.statusCode != 200 && response.statusCode != 206) {
        throw Exception(
          'HuggingFace returned HTTP ${response.statusCode}',
        );
      }

      final isPartial = response.statusCode == 206;
      if (!isPartial && existingBytes > 0) {
        existingBytes = 0;
      }

      final contentLength = response.contentLength ?? kExpectedModelBytes;
      final totalBytes = isPartial
          ? existingBytes + contentLength
          : (contentLength > kMinValidModelBytes
              ? contentLength
              : kExpectedModelBytes);

      final writeSink = partFile.openWrite(
        mode: isPartial ? FileMode.append : FileMode.write,
      );
      sink = writeSink;

      int receivedBytes = existingBytes;
      final stopwatch = Stopwatch()..start();
      int bytesInWindow = 0;
      int lastUiUpdateMs = 0;
      double smoothedSpeedMBps = 0.0;

      onProgress(
        ModelDownloadProgress(
          receivedBytes: receivedBytes,
          totalBytes: totalBytes,
          progress: (receivedBytes / totalBytes).clamp(0.0, 0.99),
          speedMBps: 0.0,
        ),
      );

      await for (final chunk in response.stream) {
        if (_cancelRequested) {
          await writeSink.close();
          sink = null;
          return false;
        }

        writeSink.add(chunk);
        receivedBytes += chunk.length;
        bytesInWindow += chunk.length;

        final elapsedMs = stopwatch.elapsedMilliseconds;
        if (elapsedMs - lastUiUpdateMs >= 180) {
          final windowSec = (elapsedMs - lastUiUpdateMs) / 1000.0;
          if (windowSec > 0) {
            final instantMBps = (bytesInWindow / (1024 * 1024)) / windowSec;
            smoothedSpeedMBps = smoothedSpeedMBps == 0.0
                ? instantMBps
                : (smoothedSpeedMBps * 0.65 + instantMBps * 0.35);
          }
          bytesInWindow = 0;
          lastUiUpdateMs = elapsedMs;

          onProgress(
            ModelDownloadProgress(
              receivedBytes: receivedBytes,
              totalBytes: totalBytes,
              progress: (receivedBytes / totalBytes).clamp(0.0, 0.99),
              speedMBps: smoothedSpeedMBps,
            ),
          );
        }
      }

      await writeSink.flush();
      await writeSink.close();
      sink = null;

      if (_cancelRequested) {
        return false;
      }

      final finalLen = await partFile.length();
      if (finalLen < kMinValidModelBytes) {
        throw Exception(
          'Downloaded file incomplete (${(finalLen / (1024 * 1024)).toStringAsFixed(1)} MB). Please check your internet connection and retry.',
        );
      }

      if (await targetFile.exists()) {
        await targetFile.delete();
      }
      await partFile.rename(targetFile.path);

      onProgress(
        ModelDownloadProgress(
          receivedBytes: finalLen,
          totalBytes: finalLen,
          progress: 1.0,
          speedMBps: smoothedSpeedMBps,
        ),
      );

      return true;
    } catch (_) {
      try {
        await sink?.close();
      } catch (_) {}
      rethrow;
    } finally {
      if (_downloadClient == client) {
        _downloadClient = null;
      }
      client.close();
    }
  }

  /// Cancels an active download. Keeps the `.part` file on disk so the user
  /// can resume later without losing already downloaded megabytes, or deletes
  /// it if `deletePartial` is true.
  void cancelDownload({bool deletePartial = false}) {
    _cancelRequested = true;
    _downloadClient?.close();
    _downloadClient = null;
    if (deletePartial) {
      _getPartFile().then((f) async {
        if (await f.exists()) await f.delete();
      }).catchError((_) {});
    }
  }

  /// Unloads the model from `llama.cpp` and deletes the `.gguf` file from storage.
  Future<void> deleteModelFromDisk() async {
    cancelDownload(deletePartial: true);
    try {
      if (_controller != null) {
        await _controller!.dispose();
        _controller = null;
        _loadedModelPath = null;
      }
    } catch (_) {}

    try {
      final targetFile = await _getTargetFile();
      if (await targetFile.exists()) {
        await targetFile.delete();
      }
      final partFile = await _getPartFile();
      if (await partFile.exists()) {
        await partFile.delete();
      }
    } catch (_) {}
  }

  Future<void> stopGeneration() async {
    try {
      if (_controller != null && _controller!.isGenerating) {
        await _controller!.stop();
      }
    } catch (_) {}
  }

  /// Streams real tokens from `llama.cpp` on Android using the downloaded Qwen 2.5 GGUF model.
  /// Returns `null` if not running on Android or if the `.gguf` file is not present.
  Stream<String>? streamNativeLlamaTokens({
    required String message,
    required List<ChatMessage> history,
    RetrievedContext? retrievedContext,
  }) {
    if (!Platform.isAndroid) return null;
    return _runAndroidLlamaStream(
      message: message,
      history: history,
      retrievedContext: retrievedContext,
    );
  }

  Stream<String> _runAndroidLlamaStream({
    required String message,
    required List<ChatMessage> history,
    RetrievedContext? retrievedContext,
  }) async* {
    final modelPath = await getModelFilePath();
    if (modelPath == null) {
      throw StateError('Qwen 2.5 GGUF model file not found on device storage.');
    }

    _controller ??= llama.LlamaController();
    final ctrl = _controller!;

    if (ctrl.isGenerating) {
      await ctrl.stop();
      await Future<void>.delayed(const Duration(milliseconds: 100));
    }

    while (_loadLock != null) {
      await _loadLock!.future;
    }

    bool loaded = false;
    try {
      loaded = await ctrl.isModelLoaded();
    } catch (_) {
      loaded = false;
    }

    if (!loaded || _loadedModelPath != modelPath) {
      final lock = Completer<void>();
      _loadLock = lock;
      try {
        await ctrl.loadModel(
          modelPath: modelPath,
          threads: 3,
          contextSize: 2048,
        );
        _loadedModelPath = modelPath;
      } finally {
        _loadLock = null;
        lock.complete();
      }
    } else {
      // Clear KV cache between turns so full RAG context fits cleanly
      try {
        await ctrl.clearContext();
      } catch (_) {}
    }

    // Construct RAG-augmented system prompt
    final sysBuf = StringBuffer();
    sysBuf.writeln(
      'You are Synapse, a helpful, concise personal intelligence assistant running locally on Akash\'s device. '
      'Answer clearly using Markdown formatting. Ground your answers in the personal context provided below when relevant.',
    );

    if (retrievedContext != null &&
        (retrievedContext.chunks.isNotEmpty ||
            retrievedContext.graphTriples.isNotEmpty)) {
      if (retrievedContext.chunks.isNotEmpty) {
        sysBuf.writeln('\n[INDEXED PERSONAL EMAILS & NOTES]:');
        for (final c in retrievedContext.chunks.take(3)) {
          sysBuf.writeln('- ${c.content.replaceAll('\n', ' ')}');
        }
      }
      if (retrievedContext.graphTriples.isNotEmpty) {
        sysBuf.writeln('\n[KNOWLEDGE GRAPH RELATIONS]:');
        for (final t in retrievedContext.graphTriples.take(5)) {
          sysBuf.writeln('- ${t.rawFact}');
        }
      }
    }

    final chatMessages = <llama.ChatMessage>[
      llama.ChatMessage(role: 'system', content: sysBuf.toString()),
    ];

    // Keep last 4 history messages so we stay well within 2048 context window
    final recentHistory = history
        .where((m) => m.content.trim().isNotEmpty && !m.hasError)
        .toList();
    final startIdx = recentHistory.length > 4 ? recentHistory.length - 4 : 0;
    for (int i = startIdx; i < recentHistory.length; i++) {
      final h = recentHistory[i];
      chatMessages.add(
        llama.ChatMessage(
          role: h.isUser ? 'user' : 'assistant',
          content: h.content,
        ),
      );
    }

    chatMessages.add(llama.ChatMessage(role: 'user', content: message));

    final tokenStream = ctrl.generateChat(
      messages: chatMessages,
      template: 'chatml',
      maxTokens: 384,
      temperature: 0.65,
      topP: 0.9,
      repeatPenalty: 1.12,
    );

    await for (final token in tokenStream) {
      yield token;
    }
  }
}
