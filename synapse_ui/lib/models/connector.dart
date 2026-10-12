/// Status states for MCP and external service connectors.
enum ConnectorStatus {
  connected,
  needsLogin,
  unconfigured,
  apiKeySetup,
  comingSoon;

  String get label {
    switch (this) {
      case ConnectorStatus.connected:
        return 'Connected';
      case ConnectorStatus.needsLogin:
        return 'Needs Login';
      case ConnectorStatus.unconfigured:
        return 'Unconfigured';
      case ConnectorStatus.apiKeySetup:
        return 'API Key Setup';
      case ConnectorStatus.comingSoon:
        return 'Coming Soon';
    }
  }

  static ConnectorStatus fromBackendString(
    String? raw, {
    bool isPlaceholder = false,
  }) {
    switch (raw?.toLowerCase()) {
      case 'connected':
        return ConnectorStatus.connected;
      case 'needs_login':
        return ConnectorStatus.needsLogin;
      case 'unconfigured':
        return isPlaceholder
            ? ConnectorStatus.apiKeySetup
            : ConnectorStatus.unconfigured;
      default:
        return isPlaceholder
            ? ConnectorStatus.comingSoon
            : ConnectorStatus.unconfigured;
    }
  }
}

/// Extensible model representing an MCP or external data source connector.
class ConnectorModel {
  final String id;
  final String name;
  final String protocolBadge;
  final String description;
  final ConnectorStatus status;
  final bool hasCredentials;
  final bool isAuthenticated;
  final bool isPlaceholder;
  final List<String> capabilities;

  const ConnectorModel({
    required this.id,
    required this.name,
    required this.protocolBadge,
    required this.description,
    required this.status,
    this.hasCredentials = false,
    this.isAuthenticated = false,
    this.isPlaceholder = false,
    this.capabilities = const [],
  });

  ConnectorModel copyWith({
    ConnectorStatus? status,
    bool? hasCredentials,
    bool? isAuthenticated,
  }) {
    return ConnectorModel(
      id: id,
      name: name,
      protocolBadge: protocolBadge,
      description: description,
      status: status ?? this.status,
      hasCredentials: hasCredentials ?? this.hasCredentials,
      isAuthenticated: isAuthenticated ?? this.isAuthenticated,
      isPlaceholder: isPlaceholder,
      capabilities: capabilities,
    );
  }

  /// Parses `GET /auth/status` response into the extensible list of Synapse connectors.
  static List<ConnectorModel> fromAuthStatusResponse(
    Map<String, dynamic> json,
  ) {
    final gmailMap = json['gmail'] is Map
        ? Map<String, dynamic>.from(json['gmail'] as Map)
        : <String, dynamic>{};
    final notionMap = json['notion'] is Map
        ? Map<String, dynamic>.from(json['notion'] as Map)
        : <String, dynamic>{};

    final gmailHasCreds = gmailMap['has_credentials'] as bool? ?? false;
    final gmailIsAuth = gmailMap['is_authenticated'] as bool? ?? false;
    final gmailStatusStr = gmailMap['status']?.toString();

    final notionIsAuth = notionMap['is_authenticated'] as bool? ?? false;

    return [
      ConnectorModel(
        id: 'gmail',
        name: 'Gmail',
        protocolBadge: 'Local MCP · stdio',
        description:
            'Indexes inbox threads into ChromaDB vector chunks and extracts entity-relation triples into the NetworkX knowledge graph via local Ollama.',
        status: ConnectorStatus.fromBackendString(gmailStatusStr),
        hasCredentials: gmailHasCreds,
        isAuthenticated: gmailIsAuth,
        isPlaceholder: false,
        capabilities: const [
          'search_emails',
          'ChromaDB Vector Indexing',
          'NetworkX Triple Extraction',
        ],
      ),
      ConnectorModel(
        id: 'notion',
        name: 'Notion Workspace',
        protocolBadge: 'MCP Server · REST API',
        description:
            'Synchronize workspace pages, databases, and engineering docs into local hybrid RAG memory via NOTION_API_KEY.',
        status: notionIsAuth
            ? ConnectorStatus.connected
            : ConnectorStatus.apiKeySetup,
        hasCredentials: notionIsAuth,
        isAuthenticated: notionIsAuth,
        isPlaceholder: true,
        capabilities: const [
          'Pages & Databases',
          'Markdown Block Chunker',
          'Cross-Doc Graph Links',
        ],
      ),
      const ConnectorModel(
        id: 'google_photos_calendar',
        name: 'Google Photos & Calendar',
        protocolBadge: 'Local MCP · OAuth 2.0',
        description:
            'Ingest calendar events, meeting attendees, and photo metadata to enrich temporal and person entities in your personal graph.',
        status: ConnectorStatus.comingSoon,
        hasCredentials: false,
        isAuthenticated: false,
        isPlaceholder: true,
        capabilities: [
          'Event Timeline Graph',
          'Attendee Resolution',
          'EXIF & Caption Indexing',
        ],
      ),
    ];
  }
}

/// Represents background synchronization progress returned by `GET /sync/status`.
class SyncStateModel {
  final bool isSyncing;
  final String? source;
  final String progress;
  final int itemsSynced;
  final String? lastSyncedAt;
  final String? error;

  const SyncStateModel({
    this.isSyncing = false,
    this.source,
    this.progress = '',
    this.itemsSynced = 0,
    this.lastSyncedAt,
    this.error,
  });

  bool get hasError => error != null && error!.isNotEmpty;

  factory SyncStateModel.fromJson(Map<String, dynamic> json) {
    return SyncStateModel(
      isSyncing: json['is_syncing'] as bool? ?? false,
      source: json['source']?.toString(),
      progress: (json['progress'] ?? '').toString(),
      itemsSynced: (json['items_synced'] as num?)?.toInt() ?? 0,
      lastSyncedAt: json['last_synced_at']?.toString(),
      error: json['error']?.toString(),
    );
  }
}
