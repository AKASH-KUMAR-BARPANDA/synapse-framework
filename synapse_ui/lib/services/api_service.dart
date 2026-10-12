import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import '../models/connector.dart';
import '../models/graph_data.dart';
import '../models/message.dart';
import 'backend_launcher.dart';
import 'embedded_engine.dart';

/// Build-time edition flag passed via `--dart-define=SYNAPSE_EDITION=...`
/// Values:
/// - `'standalone'`: 100% on-device standalone mobile APK (no external server needed)
/// - `'auto'` (default): macOS Desktop auto-spawns local FastAPI + Ollama server
const String kSynapseEdition = String.fromEnvironment(
  'SYNAPSE_EDITION',
  defaultValue: 'auto',
);

/// Represents backend service health returned by `GET /health` or Embedded Engine.
class HealthStatus {
  final bool isOnline;
  final bool isEmbeddedMode;
  final String ollama;
  final String chromaDb;
  final String gmailConnector;

  const HealthStatus({
    this.isOnline = false,
    this.isEmbeddedMode = false,
    this.ollama = 'unreachable',
    this.chromaDb = 'uninitialized',
    this.gmailConnector = 'disconnected',
  });

  bool get isOllamaReady => ollama == 'ready' || ollama == 'embedded';
  bool get isChromaReady => chromaDb == 'ready' || chromaDb == 'embedded';
  bool get isGmailConnected => gmailConnector == 'connected';

  factory HealthStatus.fromJson(Map<String, dynamic> json) {
    final services = json['services'] is Map
        ? Map<String, dynamic>.from(json['services'] as Map)
        : <String, dynamic>{};
    return HealthStatus(
      isOnline: json['status'] == 'online',
      isEmbeddedMode: false,
      ollama: (services['ollama'] ?? 'unreachable').toString(),
      chromaDb: (services['chroma_db'] ?? 'uninitialized').toString(),
      gmailConnector: (services['gmail_connector'] ?? 'disconnected').toString(),
    );
  }
}

/// Central API & Configuration Service for the Synapse Flutter frontend.
/// Supports:
/// 1. macOS Desktop Mode: Auto-spawns `ollama serve` & FastAPI server on launch.
/// 2. Android Standalone Mode (`SYNAPSE_EDITION=standalone`): Runs 100% on-device.
class ApiService extends ChangeNotifier {
  static const String _prefBackendUrl = 'synapse_backend_url';
  static const String _prefOllamaUrl = 'synapse_ollama_url';
  static const String _prefModelName = 'synapse_model_name';
  static const String _prefDefaultUseRag = 'synapse_default_use_rag';
  static const String _prefGraphPalette = 'synapse_graph_palette';
  static const String _prefChatSessions = 'synapse_chat_sessions_v1';
  static const String _prefQwenDownloaded = 'synapse_qwen_downloaded_v2_real';
  static const String _prefUseQwenModel = 'synapse_use_qwen_model_v2_real';
  static const String _prefSeenModelPrompt = 'synapse_seen_model_prompt_v2_real';

  static const int kQwenTotalSizeMB = 469;

  final EmbeddedEngine embeddedEngine = EmbeddedEngine();

  String _backendUrl = defaultPlatformBaseUrl;
  String _ollamaEndpoint = 'http://localhost:11434';
  String _modelName = 'qwen2.5:0.5b';
  bool _defaultUseRag = true;
  String _graphPalette = 'zinc';

  bool _isQwenDownloaded = false;
  bool _useQwenModel = false;
  bool _hasSeenFirstChatModelPrompt = false;
  bool _isDownloadingQwen = false;
  double _qwenDownloadProgress = 0.0;
  int _qwenDownloadedMB = 0;
  int _qwenTotalMB = kQwenTotalSizeMB;
  double _qwenDownloadSpeedMBps = 0.0;
  String? _qwenDownloadError;

  bool get isStandaloneEdition =>
      kSynapseEdition == 'standalone' ||
      (!kIsWeb && defaultTargetPlatform == TargetPlatform.android);

  late HealthStatus _healthStatus = isStandaloneEdition
      ? const HealthStatus(
          isOnline: true,
          isEmbeddedMode: true,
          ollama: 'ready',
          chromaDb: 'ready',
          gmailConnector: 'connected',
        )
      : const HealthStatus(isOnline: false, isEmbeddedMode: false);

  late List<ConnectorModel> _connectors =
      ConnectorModel.fromAuthStatusResponse(embeddedEngine.getAuthStatusJson());
  late SyncStateModel _syncState = embeddedEngine.getSyncState();
  late GraphStats _graphStats = embeddedEngine.getGraphData().stats;

  List<ChatSession> _sessions = [];
  String? _activeSessionId;

  static Map<String, String> get defaultHeaders => const {
        'Accept': 'application/json',
      };

  static String get defaultPlatformBaseUrl {
    if (kIsWeb) {
      final host = Uri.base.host;
      if (host.isNotEmpty && host != 'localhost') {
        return 'http://$host:8000';
      }
    }
    return 'http://127.0.0.1:8000';
  }

  String get backendUrl => _backendUrl;
  String get ollamaEndpoint => _ollamaEndpoint;
  String get modelName => _modelName;
  bool get defaultUseRag => _defaultUseRag;
  String get graphPalette => _graphPalette;

  bool get isQwenDownloaded => _isQwenDownloaded;
  bool get useQwenModel => _useQwenModel && _isQwenDownloaded;
  bool get isRuleBasedActive => !useQwenModel;
  bool get hasSeenFirstChatModelPrompt => _hasSeenFirstChatModelPrompt;
  bool get isDownloadingQwen => _isDownloadingQwen;
  double get qwenDownloadProgress => _qwenDownloadProgress;
  int get qwenDownloadedMB => _qwenDownloadedMB;
  int get qwenTotalMB => _qwenTotalMB;
  double get qwenDownloadSpeedMBps => _qwenDownloadSpeedMBps;
  String? get qwenDownloadError => _qwenDownloadError;

  /// Active badge string shown in the top header bar and Settings.
  String get activeEngineBadge =>
      useQwenModel ? _modelName : 'Rule-Based Engine';

  HealthStatus get healthStatus => _healthStatus;
  List<ConnectorModel> get connectors => _connectors;
  SyncStateModel get syncState => _syncState;
  GraphStats get graphStats => _graphStats;

  List<ChatSession> get sessions => List.unmodifiable(_sessions);
  String? get activeSessionId => _activeSessionId;

  ChatSession? get activeSession {
    if (_activeSessionId == null) return null;
    for (final s in _sessions) {
      if (s.id == _activeSessionId) return s;
    }
    return _sessions.isNotEmpty ? _sessions.first : null;
  }

  ConnectorModel get gmailConnector {
    for (final c in _connectors) {
      if (c.id == 'gmail') return c;
    }
    return ConnectorModel.fromAuthStatusResponse(
      embeddedEngine.getAuthStatusJson(),
    ).first;
  }

  /// Initializes persisted preferences, verifies whether the real GGUF file is
  /// present on disk (on Android), auto-starts the local backend on Desktop,
  /// and refreshes health/connectors/graph status.
  Future<void> initialize() async {
    final prefs = await SharedPreferences.getInstance();
    _backendUrl = prefs.getString(_prefBackendUrl) ?? defaultPlatformBaseUrl;
    _ollamaEndpoint =
        prefs.getString(_prefOllamaUrl) ?? 'http://localhost:11434';
    _modelName = prefs.getString(_prefModelName) ?? 'qwen2.5:0.5b';
    _defaultUseRag = prefs.getBool(_prefDefaultUseRag) ?? true;
    _graphPalette = prefs.getString(_prefGraphPalette) ?? 'zinc';

    if (isStandaloneEdition) {
      final fileOnDisk =
          await embeddedEngine.localLlmRunner.isModelPresentOnDisk();
      _isQwenDownloaded =
          fileOnDisk && (prefs.getBool(_prefQwenDownloaded) ?? false);
      if (fileOnDisk && !_isQwenDownloaded) {
        _isQwenDownloaded = true;
        await prefs.setBool(_prefQwenDownloaded, true);
      } else if (!fileOnDisk && _isQwenDownloaded) {
        _isQwenDownloaded = false;
        await prefs.setBool(_prefQwenDownloaded, false);
      }
      _useQwenModel =
          _isQwenDownloaded && (prefs.getBool(_prefUseQwenModel) ?? true);
      _hasSeenFirstChatModelPrompt =
          prefs.getBool(_prefSeenModelPrompt) ?? false;
    } else {
      _isQwenDownloaded = prefs.getBool(_prefQwenDownloaded) ?? true;
      _useQwenModel = prefs.getBool(_prefUseQwenModel) ?? true;
      _hasSeenFirstChatModelPrompt =
          prefs.getBool(_prefSeenModelPrompt) ?? true;
    }

    final rawSessions = prefs.getString(_prefChatSessions);
    if (rawSessions != null && rawSessions.isNotEmpty) {
      try {
        final decoded = jsonDecode(rawSessions) as List<dynamic>;
        _sessions = decoded
            .whereType<Map>()
            .map((e) => ChatSession.fromJson(Map<String, dynamic>.from(e)))
            .toList();
      } catch (_) {
        _sessions = [];
      }
    }

    if (_sessions.isEmpty) {
      createNewSession(notify: false);
    } else {
      _activeSessionId = _sessions.first.id;
    }

    notifyListeners();

    if (!isStandaloneEdition) {
      // Auto-start the local Python FastAPI & Ollama servers on macOS/Desktop
      await BackendLauncher.ensureLocalBackendRunning();
    }
    await refreshSystemStatus();
  }

  /// Refreshes `/health`, `/auth/status`, and `/sync/status` concurrently.
  Future<void> refreshSystemStatus() async {
    await checkHealth();
    await Future.wait([
      fetchAuthStatus(),
      fetchSyncStatus(),
      _refreshGraphCount(),
    ]);
  }

  Future<void> _refreshGraphCount() async {
    try {
      await fetchGraphData();
    } catch (_) {}
  }

  /// Streams the real `qwen2.5-0.5b-instruct-q4_k_m.gguf` (379 MB) model from
  /// HuggingFace to device storage and activates `llama.cpp` neural inference.
  Future<bool> downloadQwenModel() async {
    if (_isDownloadingQwen) return false;
    if (_isQwenDownloaded) return true;

    _isDownloadingQwen = true;
    _qwenDownloadError = null;
    _qwenDownloadProgress = 0.0;
    _qwenDownloadedMB = 0;
    _qwenTotalMB = kQwenTotalSizeMB;
    _qwenDownloadSpeedMBps = 0.0;
    notifyListeners();

    try {
      final completed = await embeddedEngine.localLlmRunner.downloadModel(
        onProgress: (p) {
          _qwenDownloadProgress = p.progress;
          _qwenDownloadedMB = p.receivedMB;
          _qwenTotalMB = p.totalMB > 0 ? p.totalMB : kQwenTotalSizeMB;
          _qwenDownloadSpeedMBps = p.speedMBps;
          notifyListeners();
        },
      );

      if (!completed) {
        _isDownloadingQwen = false;
        notifyListeners();
        return false;
      }

      _isDownloadingQwen = false;
      _isQwenDownloaded = true;
      _useQwenModel = true;
      _hasSeenFirstChatModelPrompt = true;
      _qwenDownloadError = null;

      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(_prefQwenDownloaded, true);
      await prefs.setBool(_prefUseQwenModel, true);
      await prefs.setBool(_prefSeenModelPrompt, true);
      notifyListeners();
      return true;
    } catch (e) {
      _isDownloadingQwen = false;
      _qwenDownloadError = e.toString().replaceFirst('Exception: ', '');
      notifyListeners();
      return false;
    }
  }

  void cancelQwenDownload() {
    if (!_isDownloadingQwen) return;
    embeddedEngine.localLlmRunner.cancelDownload();
    _isDownloadingQwen = false;
    _qwenDownloadSpeedMBps = 0.0;
    notifyListeners();
  }

  /// Removes the downloaded `qwen2.5:0.5b` GGUF weights from device storage
  /// and reverts to the Rule-Based Engine.
  Future<void> deleteQwenModel() async {
    _isDownloadingQwen = false;
    await embeddedEngine.localLlmRunner.deleteModelFromDisk();
    _isQwenDownloaded = false;
    _useQwenModel = false;
    _qwenDownloadProgress = 0.0;
    _qwenDownloadedMB = 0;
    _qwenDownloadSpeedMBps = 0.0;
    _qwenDownloadError = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_prefQwenDownloaded, false);
    await prefs.setBool(_prefUseQwenModel, false);
    notifyListeners();
  }

  /// Switches between `qwen2.5:0.5b` Neural Model (`useQwen: true`)
  /// and the built-in `Rule-Based Engine` (`useQwen: false`).
  Future<void> setEngineMode({required bool useQwen}) async {
    if (useQwen && !_isQwenDownloaded) {
      await downloadQwenModel();
      return;
    }
    _useQwenModel = useQwen;
    _hasSeenFirstChatModelPrompt = true;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_prefUseQwenModel, _useQwenModel);
    await prefs.setBool(_prefSeenModelPrompt, true);
    notifyListeners();
  }

  Future<void> dismissFirstChatModelPrompt() async {
    _hasSeenFirstChatModelPrompt = true;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_prefSeenModelPrompt, true);
    notifyListeners();
  }

  /// Updates configurable settings and persists them.
  Future<void> updateSettings({
    String? backendUrl,
    String? ollamaEndpoint,
    String? modelName,
    bool? defaultUseRag,
    String? graphPalette,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    if (backendUrl != null && backendUrl.trim().isNotEmpty) {
      var clean = backendUrl.trim();
      if (clean.endsWith('/')) {
        clean = clean.substring(0, clean.length - 1);
      }
      _backendUrl = clean;
      await prefs.setString(_prefBackendUrl, _backendUrl);
    }
    if (ollamaEndpoint != null && ollamaEndpoint.trim().isNotEmpty) {
      _ollamaEndpoint = ollamaEndpoint.trim();
      await prefs.setString(_prefOllamaUrl, _ollamaEndpoint);
    }
    if (modelName != null && modelName.trim().isNotEmpty) {
      _modelName = modelName.trim();
      await prefs.setString(_prefModelName, _modelName);
    }
    if (defaultUseRag != null) {
      _defaultUseRag = defaultUseRag;
      await prefs.setBool(_prefDefaultUseRag, _defaultUseRag);
    }
    if (graphPalette != null) {
      _graphPalette = graphPalette;
      await prefs.setString(_prefGraphPalette, _graphPalette);
    }
    notifyListeners();
    await refreshSystemStatus();
  }

  // ===========================================================================
  // Chat Session Management
  // ===========================================================================

  ChatSession createNewSession({bool notify = true}) {
    if (_sessions.isNotEmpty && _sessions.first.messages.isEmpty) {
      _activeSessionId = _sessions.first.id;
      if (notify) notifyListeners();
      return _sessions.first;
    }

    final now = DateTime.now();
    final session = ChatSession(
      id: 'chat_${now.microsecondsSinceEpoch}',
      title: 'New Chat',
      createdAt: now,
      updatedAt: now,
      messages: const [],
    );
    _sessions.insert(0, session);
    _activeSessionId = session.id;
    _persistSessions();
    if (notify) notifyListeners();
    return session;
  }

  void selectSession(String sessionId) {
    _activeSessionId = sessionId;
    notifyListeners();
  }

  void renameSession(String sessionId, String newTitle) {
    final trimmed = newTitle.trim();
    if (trimmed.isEmpty) return;
    final idx = _sessions.indexWhere((s) => s.id == sessionId);
    if (idx == -1) return;
    _sessions[idx] = _sessions[idx].copyWith(
      title: trimmed,
      updatedAt: DateTime.now(),
    );
    _persistSessions();
    notifyListeners();
  }

  void deleteSession(String sessionId) {
    _sessions.removeWhere((s) => s.id == sessionId);
    if (_sessions.isEmpty) {
      createNewSession(notify: false);
    } else if (_activeSessionId == sessionId) {
      _activeSessionId = _sessions.first.id;
    }
    _persistSessions();
    notifyListeners();
  }

  Future<void> clearAllSessions() async {
    _sessions.clear();
    createNewSession(notify: false);
    await _persistSessions();
    notifyListeners();
  }

  void updateSessionMessages(
    String sessionId,
    List<ChatMessage> messages, {
    String? autoTitle,
  }) {
    final idx = _sessions.indexWhere((s) => s.id == sessionId);
    if (idx == -1) return;
    final current = _sessions[idx];
    String title = current.title;
    if ((title == 'New Chat' || title.isEmpty) &&
        autoTitle != null &&
        autoTitle.trim().isNotEmpty) {
      final clean = autoTitle.trim().replaceAll('\n', ' ');
      title = clean.length > 38 ? '${clean.substring(0, 38)}...' : clean;
    }
    _sessions[idx] = current.copyWith(
      title: title,
      updatedAt: DateTime.now(),
      messages: messages,
    );
    _persistSessions();
    notifyListeners();
  }

  Future<void> _persistSessions() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final encoded = jsonEncode(_sessions.map((s) => s.toJson()).toList());
      await prefs.setString(_prefChatSessions, encoded);
    } catch (_) {}
  }

  // ===========================================================================
  // Backend HTTP Endpoints
  // ===========================================================================

  Uri buildUri(String path) => Uri.parse('$_backendUrl$path');

  /// `GET /health`
  Future<HealthStatus> checkHealth() async {
    // 1. Standalone APK always uses the built-in Embedded Engine
    if (isStandaloneEdition) {
      final embeddedAuth = embeddedEngine.getAuthStatusJson();
      final gmailStatus =
          (embeddedAuth['gmail'] as Map)['status']?.toString() ?? 'connected';
      _healthStatus = HealthStatus(
        isOnline: true,
        isEmbeddedMode: true,
        ollama: 'ready',
        chromaDb: 'ready',
        gmailConnector: gmailStatus,
      );
      notifyListeners();
      return _healthStatus;
    }

    // 2. macOS Desktop: probe local FastAPI server
    try {
      final response = await http
          .get(Uri.parse('$_backendUrl/health'), headers: defaultHeaders)
          .timeout(const Duration(seconds: 4));
      if (response.statusCode == 200) {
        final decoded = jsonDecode(response.body) as Map<String, dynamic>;
        _healthStatus = HealthStatus.fromJson(decoded);
        notifyListeners();
        return _healthStatus;
      }
    } catch (_) {}

    // 3. Fallback gracefully to Embedded Engine if local server isn't up
    final embeddedAuth = embeddedEngine.getAuthStatusJson();
    final gmailStatus =
        (embeddedAuth['gmail'] as Map)['status']?.toString() ?? 'connected';
    _healthStatus = HealthStatus(
      isOnline: true,
      isEmbeddedMode: true,
      ollama: 'ready',
      chromaDb: 'ready',
      gmailConnector: gmailStatus,
    );
    notifyListeners();
    return _healthStatus;
  }

  /// `GET /auth/status`
  Future<List<ConnectorModel>> fetchAuthStatus() async {
    if (!_healthStatus.isEmbeddedMode) {
      try {
        final response = await http
            .get(buildUri('/auth/status'), headers: defaultHeaders)
            .timeout(const Duration(seconds: 6));
        if (response.statusCode == 200) {
          final decoded = jsonDecode(response.body) as Map<String, dynamic>;
          _connectors = ConnectorModel.fromAuthStatusResponse(decoded);
          notifyListeners();
          return _connectors;
        }
      } catch (_) {}
    }

    _connectors = ConnectorModel.fromAuthStatusResponse(
      embeddedEngine.getAuthStatusJson(),
    );
    notifyListeners();
    return _connectors;
  }

  /// `POST /auth/gmail/upload-credentials`
  Future<Map<String, dynamic>> uploadGmailCredentials({
    String? filePath,
    Uint8List? bytes,
    String fileName = 'credentials.json',
  }) async {
    if (!_healthStatus.isEmbeddedMode) {
      final request = http.MultipartRequest(
        'POST',
        buildUri('/auth/gmail/upload-credentials'),
      );
      request.headers.addAll(defaultHeaders);

      if (bytes != null) {
        request.files.add(
          http.MultipartFile.fromBytes('file', bytes, filename: fileName),
        );
      } else if (filePath != null && filePath.isNotEmpty) {
        request.files.add(
          await http.MultipartFile.fromPath(
            'file',
            filePath,
            filename: fileName,
          ),
        );
      }

      final streamed =
          await request.send().timeout(const Duration(seconds: 15));
      final response = await http.Response.fromStream(streamed);
      final decoded = _decodeJsonSafely(response.body);

      if (response.statusCode >= 200 && response.statusCode < 300) {
        await fetchAuthStatus();
        await checkHealth();
        return decoded;
      } else {
        throw Exception(
          decoded['detail'] ??
              'Failed to upload credentials (${response.statusCode})',
        );
      }
    }

    embeddedEngine.markCredentialsUploaded();
    await fetchAuthStatus();
    await checkHealth();
    return {'status': 'saved', 'path': 'embedded/credentials.json'};
  }

  /// `POST /auth/gmail/login`
  Future<Map<String, dynamic>> loginGmail() async {
    if (!_healthStatus.isEmbeddedMode) {
      final response = await http
          .post(buildUri('/auth/gmail/login'), headers: defaultHeaders)
          .timeout(const Duration(seconds: 120));
      final decoded = _decodeJsonSafely(response.body);

      if (response.statusCode >= 200 && response.statusCode < 300) {
        await fetchAuthStatus();
        await checkHealth();
        return decoded;
      } else {
        throw Exception(
          decoded['detail'] ??
              'Google OAuth Login failed (${response.statusCode})',
        );
      }
    }

    embeddedEngine.markGmailLoggedIn();
    await fetchAuthStatus();
    await checkHealth();
    return {'status': 'success', 'authenticated': true};
  }

  /// `POST /auth/gmail/disconnect`
  Future<Map<String, dynamic>> disconnectGmail() async {
    if (!_healthStatus.isEmbeddedMode) {
      final response = await http
          .post(buildUri('/auth/gmail/disconnect'), headers: defaultHeaders)
          .timeout(const Duration(seconds: 10));
      final decoded = _decodeJsonSafely(response.body);

      if (response.statusCode >= 200 && response.statusCode < 300) {
        await fetchAuthStatus();
        await checkHealth();
        return decoded;
      } else {
        throw Exception(
          decoded['detail'] ??
              'Failed to disconnect Gmail (${response.statusCode})',
        );
      }
    }

    embeddedEngine.markGmailDisconnected();
    await fetchAuthStatus();
    await checkHealth();
    return {'status': 'disconnected'};
  }

  /// `POST /sync/gmail`
  Future<Map<String, dynamic>> triggerGmailSync({
    String query = 'label:INBOX',
    int maxResults = 5,
    bool extractGraph = true,
  }) async {
    if (!_healthStatus.isEmbeddedMode) {
      final response = await http
          .post(
            buildUri('/sync/gmail'),
            headers: {
              ...defaultHeaders,
              'Content-Type': 'application/json',
            },
            body: jsonEncode({
              'query': query,
              'max_results': maxResults,
              'extract_graph': extractGraph,
            }),
          )
          .timeout(const Duration(seconds: 15));
      final decoded = _decodeJsonSafely(response.body);

      if (response.statusCode >= 200 && response.statusCode < 300) {
        await fetchSyncStatus();
        return decoded;
      } else {
        throw Exception(
          decoded['detail'] ??
              'Failed to start Gmail sync (${response.statusCode})',
        );
      }
    }

    final res = await embeddedEngine.triggerEmbeddedSync(
      maxResults: maxResults,
      onUpdate: () {
        _syncState = embeddedEngine.getSyncState();
        notifyListeners();
      },
    );
    _syncState = embeddedEngine.getSyncState();
    notifyListeners();
    return res;
  }

  /// `GET /sync/status`
  Future<SyncStateModel> fetchSyncStatus() async {
    if (!_healthStatus.isEmbeddedMode) {
      try {
        final response = await http
            .get(buildUri('/sync/status'), headers: defaultHeaders)
            .timeout(const Duration(seconds: 6));
        if (response.statusCode == 200) {
          final decoded = jsonDecode(response.body) as Map<String, dynamic>;
          _syncState = SyncStateModel.fromJson(decoded);
          notifyListeners();
          return _syncState;
        }
      } catch (_) {}
    }

    _syncState = embeddedEngine.getSyncState();
    notifyListeners();
    return _syncState;
  }

  /// `GET /graph/data`
  Future<GraphData> fetchGraphData() async {
    if (!_healthStatus.isEmbeddedMode) {
      try {
        final response = await http
            .get(buildUri('/graph/data'), headers: defaultHeaders)
            .timeout(const Duration(seconds: 10));
        if (response.statusCode == 200) {
          final decoded = jsonDecode(response.body) as Map<String, dynamic>;
          final data = GraphData.fromJson(decoded);
          _graphStats = data.stats;
          notifyListeners();
          return data;
        }
      } catch (_) {}
    }

    final fallbackData = embeddedEngine.getGraphData();
    _graphStats = fallbackData.stats;
    notifyListeners();
    return fallbackData;
  }

  Map<String, dynamic> _decodeJsonSafely(String body) {
    try {
      final parsed = jsonDecode(body);
      if (parsed is Map) {
        return Map<String, dynamic>.from(parsed);
      }
      return {'data': parsed};
    } catch (_) {
      return {'detail': body};
    }
  }
}
