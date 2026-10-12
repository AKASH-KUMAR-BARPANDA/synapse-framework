import 'dart:async';
import 'dart:convert';
import 'package:http/http.dart' as http;

import '../models/message.dart';
import 'embedded_engine.dart';

/// Types of Server-Sent Events emitted by `POST /chat`.
enum SseEventType {
  context,
  delta,
  error,
  done,
}

/// Parsed SSE frame from `POST /chat`.
class SseChatEvent {
  final SseEventType type;
  final RetrievedContext? context;
  final String? tokenDelta;
  final String? errorStage;
  final String? errorDetail;

  const SseChatEvent._({
    required this.type,
    this.context,
    this.tokenDelta,
    this.errorStage,
    this.errorDetail,
  });

  factory SseChatEvent.context(RetrievedContext ctx) => SseChatEvent._(
        type: SseEventType.context,
        context: ctx,
      );

  factory SseChatEvent.delta(String token) => SseChatEvent._(
        type: SseEventType.delta,
        tokenDelta: token,
      );

  factory SseChatEvent.error({required String stage, required String detail}) =>
      SseChatEvent._(
        type: SseEventType.error,
        errorStage: stage,
        errorDetail: detail,
      );

  factory SseChatEvent.done() => const SseChatEvent._(
        type: SseEventType.done,
      );
}

/// Client for streaming Server-Sent Events (`text/event-stream`) from `POST /chat`.
/// Automatically falls back to the built-in `EmbeddedEngine` if no external
/// FastAPI server is running, so the app works as a single self-contained package.
class SseClient {
  http.Client? _activeClient;
  bool _isCancelled = false;

  EmbeddedEngine? _activeEmbeddedEngine;

  /// Cancels any active SSE or native llama.cpp stream.
  void cancel() {
    _isCancelled = true;
    _activeClient?.close();
    _activeClient = null;
    _activeEmbeddedEngine?.stopGeneration();
    _activeEmbeddedEngine = null;
  }

  /// Opens an SSE stream to `POST /chat` with body:
  /// `{"message": str, "history": list, "use_rag": bool}`
  /// Falls back to `embeddedEngine.streamStandaloneResponse` when offline.
  Stream<SseChatEvent> streamChat({
    required Uri endpoint,
    required String message,
    required List<ChatMessage> history,
    required bool useRag,
    EmbeddedEngine? embeddedEngine,
    bool forceEmbedded = false,
    bool useNeuralQwenModel = false,
  }) async* {
    cancel();
    _isCancelled = false;
    _activeEmbeddedEngine = embeddedEngine;

    if (forceEmbedded && embeddedEngine != null) {
      await for (final ev in embeddedEngine.streamStandaloneResponse(
        message: message,
        useRag: useRag,
        history: history,
        useNeuralQwenModel: useNeuralQwenModel,
      )) {
        if (_isCancelled) break;
        yield ev;
      }
      return;
    }

    final client = http.Client();
    _activeClient = client;

    try {
      final request = http.Request('POST', endpoint);
      request.headers['Content-Type'] = 'application/json';
      request.headers['Accept'] = 'text/event-stream';
      request.headers['Cache-Control'] = 'no-cache';

      request.body = jsonEncode({
        'message': message,
        'history': history
            .where((m) => m.content.trim().isNotEmpty && !m.hasError)
            .map((m) => m.toApiHistoryMap())
            .toList(),
        'use_rag': useRag,
      });

      final streamedResponse = await client
          .send(request)
          .timeout(const Duration(seconds: 6));

      if (streamedResponse.statusCode < 200 ||
          streamedResponse.statusCode >= 300) {
        if (embeddedEngine != null) {
          await for (final ev in embeddedEngine.streamStandaloneResponse(
            message: message,
            useRag: useRag,
            useNeuralQwenModel: useNeuralQwenModel,
          )) {
            if (_isCancelled) break;
            yield ev;
          }
          return;
        }
        final errorBody = await streamedResponse.stream.bytesToString();
        yield SseChatEvent.error(
          stage: 'http_${streamedResponse.statusCode}',
          detail: errorBody.isNotEmpty
              ? errorBody
              : 'Server returned HTTP ${streamedResponse.statusCode}',
        );
        return;
      }

      String currentEvent = 'message';
      final dataLines = <String>[];
      bool emittedDelta = false;

      final lineStream = streamedResponse.stream
          .transform(utf8.decoder)
          .transform(const LineSplitter());

      await for (final rawLine in lineStream) {
        if (_isCancelled) break;

        final line = rawLine.trimRight();

        if (line.isEmpty) {
          if (dataLines.isNotEmpty) {
            final fullData = dataLines.join('\n');
            dataLines.clear();
            final parsedEvent = _parseFrame(currentEvent, fullData);
            currentEvent = 'message';
            if (parsedEvent != null) {
              if (parsedEvent.type == SseEventType.delta) {
                emittedDelta = true;
              }
              // If local Ollama failed on backend, seamlessly synthesize via EmbeddedEngine
              if (parsedEvent.type == SseEventType.error &&
                  !emittedDelta &&
                  embeddedEngine != null) {
                await for (final ev in embeddedEngine.streamStandaloneResponse(
                  message: message,
                  useRag: false,
                  useNeuralQwenModel: useNeuralQwenModel,
                )) {
                  if (_isCancelled) break;
                  yield ev;
                }
                return;
              }
              yield parsedEvent;
              if (parsedEvent.type == SseEventType.done) {
                break;
              }
            }
          }
          continue;
        }

        if (line.startsWith('event:')) {
          currentEvent = line.substring(6).trim();
        } else if (line.startsWith('data:')) {
          dataLines.add(line.substring(5).trimLeft());
        }
      }

      if (!_isCancelled && dataLines.isNotEmpty) {
        final fullData = dataLines.join('\n');
        dataLines.clear();
        final parsedEvent = _parseFrame(currentEvent, fullData);
        if (parsedEvent != null) {
          yield parsedEvent;
        }
      }
    } catch (e) {
      if (!_isCancelled && embeddedEngine != null) {
        await for (final ev in embeddedEngine.streamStandaloneResponse(
          message: message,
          useRag: useRag,
          useNeuralQwenModel: useNeuralQwenModel,
        )) {
          if (_isCancelled) break;
          yield ev;
        }
        return;
      }
      if (!_isCancelled) {
        yield SseChatEvent.error(
          stage: 'connection',
          detail: 'Unable to reach Synapse backend (${endpoint.origin}): $e',
        );
      }
    } finally {
      if (_activeClient == client) {
        _activeClient = null;
      }
      client.close();
    }
  }

  SseChatEvent? _parseFrame(String eventName, String rawData) {
    switch (eventName) {
      case 'context':
        try {
          final decoded = jsonDecode(rawData);
          if (decoded is Map) {
            return SseChatEvent.context(
              RetrievedContext.fromJson(Map<String, dynamic>.from(decoded)),
            );
          }
        } catch (_) {}
        return SseChatEvent.context(const RetrievedContext());

      case 'delta':
        try {
          final decoded = jsonDecode(rawData);
          if (decoded is Map) {
            final token = (decoded['token'] ?? '').toString();
            if (token.isNotEmpty) {
              return SseChatEvent.delta(token);
            }
            return null;
          }
        } catch (_) {
          if (rawData.isNotEmpty) {
            return SseChatEvent.delta(rawData);
          }
        }
        return null;

      case 'error':
        try {
          final decoded = jsonDecode(rawData);
          if (decoded is Map) {
            return SseChatEvent.error(
              stage: (decoded['stage'] ?? 'backend').toString(),
              detail: (decoded['detail'] ?? 'Unknown backend error').toString(),
            );
          }
        } catch (_) {}
        return SseChatEvent.error(
          stage: 'stream',
          detail: rawData,
        );

      case 'done':
        return SseChatEvent.done();

      default:
        return null;
    }
  }
}
