import 'dart:async';
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

/// Web stub for [LocalLlmRunner]. On macOS Desktop (which runs via WebKit + local
/// Ollama server), model weights are managed by the local Ollama daemon.
class LocalLlmRunner {
  static const int kExpectedModelBytes = 491400032; // ~468.6 MB (469 MB)

  Future<bool> isModelPresentOnDisk() async => true;

  Future<String?> getModelFilePath() async => null;

  Future<bool> downloadModel({
    required void Function(ModelDownloadProgress progress) onProgress,
  }) async {
    const total = kExpectedModelBytes;
    const steps = 20;
    for (int i = 1; i <= steps; i++) {
      await Future<void>.delayed(const Duration(milliseconds: 120));
      final recv = ((total * i) / steps).round();
      onProgress(
        ModelDownloadProgress(
          receivedBytes: recv,
          totalBytes: total,
          progress: i / steps,
          speedMBps: 18.4,
        ),
      );
    }
    return true;
  }

  void cancelDownload() {}

  Future<void> deleteModelFromDisk() async {}

  Future<void> stopGeneration() async {}

  Stream<String>? streamNativeLlamaTokens({
    required String message,
    required List<ChatMessage> history,
    RetrievedContext? retrievedContext,
  }) {
    return null;
  }
}
