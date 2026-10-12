/// Represents a single vector document chunk retrieved from ChromaDB.
class RagChunk {
  final String content;
  final String source;
  final String subject;
  final String chunkId;
  final Map<String, dynamic> metadata;

  const RagChunk({
    required this.content,
    this.source = 'memory',
    this.subject = '',
    this.chunkId = '',
    this.metadata = const {},
  });

  factory RagChunk.fromDynamic(dynamic raw) {
    if (raw is String) {
      return RagChunk(content: raw);
    }
    if (raw is Map) {
      final map = Map<String, dynamic>.from(raw);
      final meta = map['metadata'] is Map
          ? Map<String, dynamic>.from(map['metadata'] as Map)
          : <String, dynamic>{};

      final content = (map['page_content'] ??
              map['content'] ??
              map['text'] ??
              map['snippet'] ??
              '')
          .toString();

      final source =
          (map['source'] ?? meta['source'] ?? 'chroma_db').toString();
      final subject = (map['subject'] ?? meta['subject'] ?? '').toString();
      final chunkId = (map['chunk_id'] ?? meta['chunk_id'] ?? '').toString();

      return RagChunk(
        content: content,
        source: source,
        subject: subject,
        chunkId: chunkId,
        metadata: meta.isNotEmpty ? meta : map,
      );
    }
    return RagChunk(content: raw.toString());
  }

  Map<String, dynamic> toJson() => {
        'page_content': content,
        'source': source,
        'subject': subject,
        'chunk_id': chunkId,
        'metadata': metadata,
      };
}

/// Represents a relational triple retrieved from the NetworkX knowledge graph.
class GraphTriple {
  final String source;
  final String relation;
  final String target;
  final String rawFact;

  const GraphTriple({
    required this.source,
    required this.relation,
    required this.target,
    required this.rawFact,
  });

  factory GraphTriple.fromDynamic(dynamic raw) {
    if (raw is String) {
      // Parse "Entity A -> RELATION -> Entity B" format from PersistentGraphStore.find_relation_for
      final parts = raw.split('->').map((s) => s.trim()).toList();
      if (parts.length >= 3) {
        return GraphTriple(
          source: parts[0],
          relation: parts[1],
          target: parts.sublist(2).join(' -> '),
          rawFact: raw,
        );
      }
      return GraphTriple(
        source: raw,
        relation: 'RELATED',
        target: '',
        rawFact: raw,
      );
    }
    if (raw is Map) {
      final map = Map<String, dynamic>.from(raw);
      final src = (map['source'] ?? map['head'] ?? '').toString();
      final rel = (map['relation'] ?? map['predicate'] ?? 'RELATED').toString();
      final tgt = (map['target'] ?? map['tail'] ?? '').toString();
      return GraphTriple(
        source: src,
        relation: rel,
        target: tgt,
        rawFact: '$src -> $rel -> $tgt',
      );
    }
    final str = raw.toString();
    return GraphTriple(
      source: str,
      relation: 'RELATED',
      target: '',
      rawFact: str,
    );
  }

  Map<String, dynamic> toJson() => {
        'source': source,
        'relation': relation,
        'target': target,
        'rawFact': rawFact,
      };
}

/// Aggregates retrieved ChromaDB chunks and NetworkX graph triples for the Context Inspector.
class RetrievedContext {
  final List<RagChunk> chunks;
  final List<GraphTriple> graphTriples;
  final List<String> entitiesDetected;

  const RetrievedContext({
    this.chunks = const [],
    this.graphTriples = const [],
    this.entitiesDetected = const [],
  });

  bool get isEmpty => chunks.isEmpty && graphTriples.isEmpty;
  bool get isNotEmpty => !isEmpty;
  int get totalItems => chunks.length + graphTriples.length;

  factory RetrievedContext.fromJson(Map<String, dynamic> json) {
    // Support both `chunks` and `vector_documents` keys
    final rawChunks =
        (json['chunks'] ?? json['vector_documents'] ?? []) as List<dynamic>;
    // Support both `graph_triples` and `graph_facts` keys
    final rawTriples =
        (json['graph_triples'] ?? json['graph_facts'] ?? []) as List<dynamic>;
    final rawEntities = (json['entities_detected'] ?? []) as List<dynamic>;

    return RetrievedContext(
      chunks: rawChunks.map(RagChunk.fromDynamic).toList(),
      graphTriples: rawTriples.map(GraphTriple.fromDynamic).toList(),
      entitiesDetected: rawEntities.map((e) => e.toString()).toList(),
    );
  }

  Map<String, dynamic> toJson() => {
        'chunks': chunks.map((c) => c.toJson()).toList(),
        'graph_triples': graphTriples.map((t) => t.toJson()).toList(),
        'entities_detected': entitiesDetected,
      };
}

/// Represents a single message turn in a conversation.
class ChatMessage {
  final String id;
  final String role; // 'user' or 'assistant'
  final String content;
  final DateTime timestamp;
  final bool isStreaming;
  final bool useRag;
  final bool contextReceived;
  final RetrievedContext? retrievedContext;
  final String? errorMessage;
  final String? errorStage;

  const ChatMessage({
    required this.id,
    required this.role,
    required this.content,
    required this.timestamp,
    this.isStreaming = false,
    this.useRag = true,
    this.contextReceived = false,
    this.retrievedContext,
    this.errorMessage,
    this.errorStage,
  });

  bool get isUser => role == 'user';
  bool get isAssistant => role == 'assistant';
  bool get hasError => errorMessage != null && errorMessage!.isNotEmpty;

  ChatMessage copyWith({
    String? id,
    String? role,
    String? content,
    DateTime? timestamp,
    bool? isStreaming,
    bool? useRag,
    bool? contextReceived,
    RetrievedContext? retrievedContext,
    String? errorMessage,
    String? errorStage,
    bool clearError = false,
  }) {
    return ChatMessage(
      id: id ?? this.id,
      role: role ?? this.role,
      content: content ?? this.content,
      timestamp: timestamp ?? this.timestamp,
      isStreaming: isStreaming ?? this.isStreaming,
      useRag: useRag ?? this.useRag,
      contextReceived: contextReceived ?? this.contextReceived,
      retrievedContext: retrievedContext ?? this.retrievedContext,
      errorMessage: clearError ? null : (errorMessage ?? this.errorMessage),
      errorStage: clearError ? null : (errorStage ?? this.errorStage),
    );
  }

  /// Payload format expected by FastAPI `ChatRequest.history`: `{"role": str, "content": str}`
  Map<String, String> toApiHistoryMap() => {
        'role': role,
        'content': content,
      };

  Map<String, dynamic> toJson() => {
        'id': id,
        'role': role,
        'content': content,
        'timestamp': timestamp.toIso8601String(),
        'useRag': useRag,
        'contextReceived': contextReceived,
        'retrievedContext': retrievedContext?.toJson(),
        'errorMessage': errorMessage,
        'errorStage': errorStage,
      };

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: (json['id'] ?? DateTime.now().microsecondsSinceEpoch.toString())
          .toString(),
      role: (json['role'] ?? 'user').toString(),
      content: (json['content'] ?? '').toString(),
      timestamp: DateTime.tryParse((json['timestamp'] ?? '').toString()) ??
          DateTime.now(),
      isStreaming: false,
      useRag: json['useRag'] as bool? ?? true,
      contextReceived: json['contextReceived'] as bool? ?? false,
      retrievedContext: json['retrievedContext'] is Map
          ? RetrievedContext.fromJson(
              Map<String, dynamic>.from(json['retrievedContext'] as Map),
            )
          : null,
      errorMessage: json['errorMessage'] as String?,
      errorStage: json['errorStage'] as String?,
    );
  }
}

/// Represents a persisted conversation session displayed in the Sidebar's Recent Chats.
class ChatSession {
  final String id;
  final String title;
  final DateTime createdAt;
  final DateTime updatedAt;
  final List<ChatMessage> messages;

  const ChatSession({
    required this.id,
    required this.title,
    required this.createdAt,
    required this.updatedAt,
    this.messages = const [],
  });

  ChatSession copyWith({
    String? id,
    String? title,
    DateTime? createdAt,
    DateTime? updatedAt,
    List<ChatMessage>? messages,
  }) {
    return ChatSession(
      id: id ?? this.id,
      title: title ?? this.title,
      createdAt: createdAt ?? this.createdAt,
      updatedAt: updatedAt ?? this.updatedAt,
      messages: messages ?? this.messages,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'createdAt': createdAt.toIso8601String(),
        'updatedAt': updatedAt.toIso8601String(),
        'messages': messages.map((m) => m.toJson()).toList(),
      };

  factory ChatSession.fromJson(Map<String, dynamic> json) {
    final rawMessages = (json['messages'] ?? []) as List<dynamic>;
    return ChatSession(
      id: (json['id'] ?? '').toString(),
      title: (json['title'] ?? 'New Chat').toString(),
      createdAt: DateTime.tryParse((json['createdAt'] ?? '').toString()) ??
          DateTime.now(),
      updatedAt: DateTime.tryParse((json['updatedAt'] ?? '').toString()) ??
          DateTime.now(),
      messages: rawMessages
          .whereType<Map>()
          .map((m) => ChatMessage.fromJson(Map<String, dynamic>.from(m)))
          .toList(),
    );
  }
}
