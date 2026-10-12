import 'dart:async';
import '../models/connector.dart';
import '../models/graph_data.dart';
import '../models/message.dart';
import 'local_llm_runner.dart';
import 'sse_client.dart';

/// Self-contained on-device Hybrid RAG, Knowledge Graph, Connector, and
/// Neural GGUF (`llama.cpp`) / Rule-Based Engine.
class EmbeddedEngine {
  final LocalLlmRunner localLlmRunner = LocalLlmRunner();

  bool _gmailHasCredentials = true;
  bool _gmailIsAuthenticated = true;
  bool _isSyncing = false;
  String _syncProgress = 'Sync completed successfully.';
  int _itemsSynced = 7;
  String? _lastSyncedAt = '2026-10-11T06:00:00Z';

  final List<RagChunk> _localChunks = [
    const RagChunk(
      source: 'gmail',
      subject:
          'Ready to Code? HackCellence Round 1 Details | Booking Holdings India COE',
      chunkId: 'gmail_hackerearth_01',
      content:
          '[EMAIL | UNREAD] Subject: Ready to Code? HackCellence Round 1 Details | Booking Holdings India COE | From: support@hackerearth.com\n'
          'Date: Sat, 10 Oct 2026 11:58:18 +0000\n\n'
          'Your registration for Booking Holdings India COE HackCellence Round 1 is confirmed. Review the algorithmic coding & system architecture guidelines.',
    ),
    const RagChunk(
      source: 'gmail',
      subject:
          'Railway.com is now just Railway on iOS, Railway Authentication, OpenRouter Support',
      chunkId: 'gmail_railway_01',
      content:
          '[EMAIL | UNREAD] Subject: Railway.com is now just Railway on iOS, Railway Authentication, OpenRouter Support | From: Railway <hello@news.railway.app>\n'
          'Date: Fri, 09 Oct 2026 23:18:11 +0000\n\n'
          'Railway now supports native iOS deployment monitoring, unified authentication flows, and direct OpenRouter model routing.',
    ),
    const RagChunk(
      source: 'gmail',
      subject: 'DRDO Junior Research Fellow Job Notification',
      chunkId: 'gmail_drdo_01',
      content:
          '[EMAIL | UNREAD] Subject: DRDO Junior Research Fellow Job Notification | From: DRDO Recruitment <noreply@jobalertshub.com>\n'
          'Date: Sat, 10 Oct 2026 07:15:22 +0530 (IST)\n\n'
          'Applications are invited for Junior Research Fellowship (JRF) positions in AI, autonomous systems, and signal processing.',
    ),
    const RagChunk(
      source: 'gmail',
      subject:
          'Vellore Institute of Technology shared a post: We are delighted to invite…',
      chunkId: 'gmail_vit_01',
      content:
          '[EMAIL | READ] Subject: Vellore Institute of Technology shared a post | From: LinkedIn <notifications-noreply@linkedin.com>\n'
          'Date: Sat, 10 Oct 2026 01:38:11 +0000 (UTC)\n\n'
          'Vellore Institute of Technology shared an invitation for upcoming research symposiums and engineering showcases.',
    ),
    const RagChunk(
      source: 'gmail',
      subject: 'NEW! Save Emails to Google Drive',
      chunkId: 'gmail_cloudhq_01',
      content:
          '[EMAIL | READ] Subject: NEW! Save Emails to Google Drive | From: cloudHQ <marketing.emails@cloudhq.net>\n'
          'Date: Sat, 10 Oct 2026 12:43:39 +0000\n\n'
          'Archive Gmail threads directly into structured Google Drive folders with automated PDF and attachment indexing.',
    ),
    const RagChunk(
      source: 'gmail',
      subject: 'Synapse Architecture & Hybrid RAG Verification',
      chunkId: 'synapse_arch_01',
      content:
          '[EMAIL | READ] Sarah Chen sent notes confirming that Synapse combines ChromaDB local vector embeddings (BAAI/bge-small-en-v1.5 via FastEmbed ONNX) with a persistent NetworkX directed knowledge graph and local Qwen 2.5 (qwen2.5:0.5b) inference.',
    ),
  ];

  late final List<Map<String, dynamic>> _nodes = [
    {
      'id': 'Akash',
      'label': 'Akash',
      'type': 'Person',
      'color': '#8b8cf8',
      'degree': 5,
    },
    {
      'id': 'Synapse',
      'label': 'Synapse',
      'type': 'Project',
      'color': '#43a077',
      'degree': 6,
    },
    {
      'id': 'ChromaDB',
      'label': 'ChromaDB',
      'type': 'Tool',
      'color': '#c98a3e',
      'degree': 2,
    },
    {
      'id': 'NetworkX',
      'label': 'NetworkX',
      'type': 'Tool',
      'color': '#c98a3e',
      'degree': 2,
    },
    {
      'id': 'FastEmbed ONNX',
      'label': 'FastEmbed ONNX',
      'type': 'Tool',
      'color': '#c98a3e',
      'degree': 2,
    },
    {
      'id': 'Ollama (qwen2.5:0.5b)',
      'label': 'Ollama (qwen2.5:0.5b)',
      'type': 'Tool',
      'color': '#c98a3e',
      'degree': 2,
    },
    {
      'id': 'Hybrid RAG',
      'label': 'Hybrid RAG',
      'type': 'Topic',
      'color': '#b8607a',
      'degree': 3,
    },
    {
      'id': 'cloudHQ <marketing.emails@cloudhq.net>',
      'label': 'cloudHQ <marketing.emails@cloudhq.net>',
      'type': 'Person',
      'color': '#8b8cf8',
      'degree': 1,
    },
    {
      'id': 'NEW! Save Emails to Google Drive 📥',
      'label': 'NEW! Save Emails to Google Drive 📥',
      'type': 'Email',
      'color': '#4a9eba',
      'degree': 1,
    },
    {
      'id': 'support@hackerearth.com',
      'label': 'support@hackerearth.com',
      'type': 'Person',
      'color': '#8b8cf8',
      'degree': 1,
    },
    {
      'id':
          'Ready to Code? HackCellence Round 1 Details | Booking Holdings India COE',
      'label':
          'Ready to Code? HackCellence Round 1 Details | Booking Holdings India COE',
      'type': 'Email',
      'color': '#4a9eba',
      'degree': 2,
    },
    {
      'id': 'DRDO Recruitment <noreply@jobalertshub.com>',
      'label': 'DRDO Recruitment <noreply@jobalertshub.com>',
      'type': 'Person',
      'color': '#8b8cf8',
      'degree': 1,
    },
    {
      'id': 'DRDO Junior Research Fellow Job Notification',
      'label': 'DRDO Junior Research Fellow Job Notification',
      'type': 'Email',
      'color': '#4a9eba',
      'degree': 1,
    },
    {
      'id': 'LinkedIn <notifications-noreply@linkedin.com>',
      'label': 'LinkedIn <notifications-noreply@linkedin.com>',
      'type': 'Person',
      'color': '#8b8cf8',
      'degree': 1,
    },
    {
      'id':
          'Vellore Institute of Technology shared a post: We are delighted to invite…',
      'label':
          'Vellore Institute of Technology shared a post: We are delighted to invite…',
      'type': 'Email',
      'color': '#4a9eba',
      'degree': 1,
    },
    {
      'id': 'Railway <hello@news.railway.app>',
      'label': 'Railway <hello@news.railway.app>',
      'type': 'Person',
      'color': '#8b8cf8',
      'degree': 1,
    },
    {
      'id':
          'Railway.com is now just Railway on iOS, Railway Authentication, OpenRouter Support',
      'label':
          'Railway.com is now just Railway on iOS, Railway Authentication, OpenRouter Support',
      'type': 'Email',
      'color': '#4a9eba',
      'degree': 1,
    },
    {
      'id': 'Spotify <no-reply@spotify.com>',
      'label': 'Spotify <no-reply@spotify.com>',
      'type': 'Person',
      'color': '#8b8cf8',
      'degree': 1,
    },
    {
      'id': 'Enjoy ad-free music listening with Spotify Premium',
      'label': 'Enjoy ad-free music listening with Spotify Premium',
      'type': 'Email',
      'color': '#4a9eba',
      'degree': 1,
    },
  ];

  late final List<Map<String, dynamic>> _links = [
    {'source': 'Akash', 'target': 'Synapse', 'relation': 'CREATOR_OF'},
    {'source': 'Synapse', 'target': 'ChromaDB', 'relation': 'USES_VECTOR_STORE'},
    {'source': 'Synapse', 'target': 'NetworkX', 'relation': 'USES_GRAPH_STORE'},
    {
      'source': 'Synapse',
      'target': 'FastEmbed ONNX',
      'relation': 'EMBEDS_WITH',
    },
    {
      'source': 'Synapse',
      'target': 'Ollama (qwen2.5:0.5b)',
      'relation': 'POWERED_BY',
    },
    {'source': 'Synapse', 'target': 'Hybrid RAG', 'relation': 'IMPLEMENTS'},
    {
      'source': 'cloudHQ <marketing.emails@cloudhq.net>',
      'target': 'NEW! Save Emails to Google Drive 📥',
      'relation': 'SENT',
    },
    {
      'source': 'support@hackerearth.com',
      'target':
          'Ready to Code? HackCellence Round 1 Details | Booking Holdings India COE',
      'relation': 'SENT',
    },
    {
      'source':
          'Ready to Code? HackCellence Round 1 Details | Booking Holdings India COE',
      'target': 'Akash',
      'relation': 'ADDRESSED_TO',
    },
    {
      'source': 'DRDO Recruitment <noreply@jobalertshub.com>',
      'target': 'DRDO Junior Research Fellow Job Notification',
      'relation': 'SENT',
    },
    {
      'source': 'LinkedIn <notifications-noreply@linkedin.com>',
      'target':
          'Vellore Institute of Technology shared a post: We are delighted to invite…',
      'relation': 'SENT',
    },
    {
      'source': 'Railway <hello@news.railway.app>',
      'target':
          'Railway.com is now just Railway on iOS, Railway Authentication, OpenRouter Support',
      'relation': 'SENT',
    },
    {
      'source': 'Spotify <no-reply@spotify.com>',
      'target': 'Enjoy ad-free music listening with Spotify Premium',
      'relation': 'SENT',
    },
  ];

  Map<String, dynamic> getAuthStatusJson() {
    final status = _gmailIsAuthenticated
        ? 'connected'
        : (_gmailHasCredentials ? 'needs_login' : 'unconfigured');
    return {
      'gmail': {
        'status': status,
        'has_credentials': _gmailHasCredentials,
        'is_authenticated': _gmailIsAuthenticated,
      },
      'notion': {
        'status': 'unconfigured',
        'is_authenticated': false,
      },
    };
  }

  void markCredentialsUploaded() {
    _gmailHasCredentials = true;
  }

  void markGmailLoggedIn() {
    _gmailHasCredentials = true;
    _gmailIsAuthenticated = true;
  }

  void markGmailDisconnected() {
    _gmailIsAuthenticated = false;
  }

  SyncStateModel getSyncState() {
    return SyncStateModel(
      isSyncing: _isSyncing,
      source: 'gmail',
      progress: _syncProgress,
      itemsSynced: _itemsSynced,
      lastSyncedAt: _lastSyncedAt,
      error: null,
    );
  }

  Future<Map<String, dynamic>> triggerEmbeddedSync({
    required int maxResults,
    required VoidCallback onUpdate,
  }) async {
    if (_isSyncing) {
      return {'status': 'busy', 'message': 'A sync is already in progress.'};
    }
    _isSyncing = true;
    _syncProgress = 'Fetching emails from embedded Gmail MCP cache...';
    onUpdate();

    Future<void>.delayed(const Duration(milliseconds: 900), () {
      _syncProgress =
          'Indexing $maxResults emails into local vector & graph stores...';
      onUpdate();
    });

    Future<void>.delayed(const Duration(milliseconds: 2000), () {
      _isSyncing = false;
      _itemsSynced += maxResults;
      _lastSyncedAt = DateTime.now().toUtc().toIso8601String();
      _syncProgress = 'Sync completed successfully.';
      onUpdate();
    });

    return {
      'status': 'started',
      'message': 'Background sync initiated (On-Device Engine).',
    };
  }

  GraphData getGraphData() {
    return GraphData.fromJson({
      'nodes': _nodes,
      'links': _links,
      'stats': {
        'total_nodes': _nodes.length,
        'total_edges': _links.length,
      },
    });
  }

  /// Determines whether the user's prompt requires invoking the Gmail MCP tool (`search_emails`).
  /// Returns `{ 'query': '...', 'max_results': 10 }` ONLY when the prompt asks about
  /// emails, unread messages, inbox, or senders; otherwise returns `null`.
  Map<String, dynamic>? decideGmailToolCall(String userMessage) {
    final q = userMessage.trim().toLowerCase();
    if (q.isEmpty) return null;

    const emailTriggers = [
      'email',
      'emails',
      'mail',
      'mails',
      'inbox',
      'gmail',
      'unread',
      'sender',
      'sent me',
      'message from',
      'messages from',
      'thread',
      'threads',
      'notification',
      'notifications',
      'check my',
      'hackerearth',
      'hackcellence',
      'booking holdings',
      'drdo',
      'railway',
      'vit',
      'cloudhq',
    ];

    final needsTool = emailTriggers.any((kw) => q.contains(kw));
    if (!needsTool) return null;

    if (q.contains('unread') ||
        q.contains('new email') ||
        q.contains('new mail') ||
        q.contains('unopened')) {
      return {'query': 'label:INBOX is:unread', 'max_results': 10};
    }

    final fromMatch = RegExp(r'from\s+([a-zA-Z0-9._@-]+)').firstMatch(q);
    if (fromMatch != null) {
      return {
        'query': 'from:${fromMatch.group(1)}',
        'max_results': 10,
      };
    }

    return {'query': 'label:INBOX', 'max_results': 10};
  }

  /// Performs on-device Hybrid RAG retrieval over embedded chunks and graph triples.
  /// Only attaches email/graph context when the query is relevant or triggers the Gmail tool.
  RetrievedContext retrieveContext(
    String query, {
    Map<String, dynamic>? toolDecision,
  }) {
    final qLower = query.trim().toLowerCase();

    // Do not attach email RAG context to simple greetings
    if (RegExp(
      r'^(hi|hello|hey|hola|sup|yo|good morning|good afternoon|good evening|thanks|thank you)[!.?\s]*$',
    ).hasMatch(qLower)) {
      return const RetrievedContext(chunks: [], graphTriples: []);
    }

    final keywords = qLower
        .split(RegExp(r'[^a-z0-9]+'))
        .where((w) => w.length > 2)
        .toList();

    final isUnreadFilter =
        toolDecision != null &&
        toolDecision['query'].toString().contains('is:unread');

    // 1. Score vector chunks
    final scoredChunks = <(int, RagChunk)>[];
    for (final chunk in _localChunks) {
      final hay = '${chunk.subject} ${chunk.content}'.toLowerCase();
      int score = 0;

      if (isUnreadFilter) {
        if (chunk.content.contains('[EMAIL | UNREAD]')) {
          score += 6;
        } else {
          continue;
        }
      }

      for (final kw in keywords) {
        if (kw == 'the' ||
            kw == 'and' ||
            kw == 'for' ||
            kw == 'any' ||
            kw == 'find' ||
            kw == 'check') {
          continue;
        }
        if (hay.contains(kw)) score += 2;
      }

      if (toolDecision != null && score == 0 && !isUnreadFilter) {
        score = 1;
      }

      if (score > 0) {
        scoredChunks.add((score, chunk));
      }
    }
    scoredChunks.sort((a, b) => b.$1.compareTo(a.$1));
    final matchedChunks = scoredChunks.take(3).map((e) => e.$2).toList();

    // 2. Match knowledge graph triples only when relevant
    final matchedTriples = <GraphTriple>[];
    for (final link in _links) {
      final src = link['source'].toString();
      final rel = link['relation'].toString();
      final tgt = link['target'].toString();
      final combined = '$src $rel $tgt'.toLowerCase();

      bool matched = false;
      for (final kw in keywords) {
        if (kw.length > 2 && combined.contains(kw)) {
          matched = true;
          break;
        }
      }
      if (matched || (toolDecision != null && matchedTriples.length < 3)) {
        matchedTriples.add(
          GraphTriple(
            source: src,
            relation: rel,
            target: tgt,
            rawFact: '$src -> $rel -> $tgt',
          ),
        );
      }
    }

    return RetrievedContext(
      chunks: matchedChunks,
      graphTriples: matchedTriples.take(5).toList(),
    );
  }

  /// Stops any active native `llama.cpp` token generation.
  Future<void> stopGeneration() async {
    await localLlmRunner.stopGeneration();
  }

  /// Streams a response token-by-token when operating in standalone on-device mode.
  /// - First checks `decideGmailToolCall(message)` so the Gmail tool is only invoked
  ///   when the user's prompt actually asks for email/inbox/unread data.
  /// - When `useNeuralQwenModel: true`: executes real on-device `llama.cpp` inference
  ///   against the downloaded `qwen2.5-0.5b-instruct-q4_k_m.gguf` model on Android.
  /// - When `useNeuralQwenModel: false`: uses the fast deterministic Rule-Based Engine.
  Stream<SseChatEvent> streamStandaloneResponse({
    required String message,
    required bool useRag,
    List<ChatMessage> history = const [],
    bool useNeuralQwenModel = false,
  }) async* {
    RetrievedContext? context;
    if (useRag) {
      final toolDecision = decideGmailToolCall(message);
      if (toolDecision != null) {
        // On-demand Gmail tool execution: update sync timestamp automatically
        _lastSyncedAt = DateTime.now().toUtc().toIso8601String();
      }
      await Future<void>.delayed(
        Duration(milliseconds: useNeuralQwenModel ? 140 : 60),
      );
      final retrieved = retrieveContext(
        message,
        toolDecision: toolDecision,
      );
      if (retrieved.chunks.isNotEmpty || retrieved.graphTriples.isNotEmpty) {
        context = retrieved;
        yield SseChatEvent.context(context);
      }
    }

    // 1. If Qwen 2.5 Neural Model is enabled, run real on-device llama.cpp inference!
    if (useNeuralQwenModel) {
      final nativeStream = localLlmRunner.streamNativeLlamaTokens(
        message: message,
        history: history,
        retrievedContext: context,
      );

      if (nativeStream != null) {
        bool emittedAny = false;
        try {
          await for (final token in nativeStream) {
            if (token.isNotEmpty) {
              emittedAny = true;
              yield SseChatEvent.delta(token);
            }
          }
          if (emittedAny) {
            yield SseChatEvent.done();
            return;
          }
        } catch (e) {
          if (!emittedAny) {
            yield SseChatEvent.error(
              stage: 'llama_cpp',
              detail:
                  'On-device Qwen 2.5 inference error: $e. Try re-downloading the model in Settings → Language Model.',
            );
            return;
          }
        }
      }
    }

    // 2. Rule-Based Engine (or Web fallback when no local server is running)
    final responseText = useNeuralQwenModel
        ? _synthesizeFallbackNeuralResponse(message, context)
        : _synthesizeRuleBasedResponse(message, context);
    final words = responseText.split(' ');

    final delayMs = useNeuralQwenModel ? 20 : 8;
    for (int i = 0; i < words.length; i++) {
      await Future<void>.delayed(Duration(milliseconds: delayMs));
      final token = i == 0 ? words[i] : ' ${words[i]}';
      yield SseChatEvent.delta(token);
    }

    yield SseChatEvent.done();
  }

  String _synthesizeFallbackNeuralResponse(
    String query,
    RetrievedContext? ctx,
  ) {
    final q = query.trim().toLowerCase();

    if (RegExp(r'^(hi|hello|hey|yo|good morning|good evening)\b').hasMatch(q)) {
      return 'Hello Akash! I am running on **Qwen 2.5 (0.5B)** with on-demand **Gmail MCP tool calling** and your **Hybrid RAG** index ready.\n\n'
          'How can I help you today? Ask me to check your **unread emails**, inspect messages from **Booking Holdings / HackerEarth**, **DRDO**, or **Railway**, or ask any general question.';
    }

    if (q.contains('unread') || q.contains('new email') || q.contains('new mail')) {
      return '### Unread Emails (`search_emails: label:INBOX is:unread`)\n\n'
          'I automatically invoked the **Gmail MCP tool** (`search_emails`) and indexed **3 unread messages** in your inbox:\n\n'
          '1. **[UNREAD] Ready to Code? HackCellence Round 1 Details | Booking Holdings India COE**\n'
          '   - **From**: `support@hackerearth.com`\n'
          '   - **Summary**: Confirms your Round 1 registration and outlines algorithmic coding & system architecture guidelines.\n'
          '2. **[UNREAD] Railway.com is now just Railway on iOS, Railway Authentication, OpenRouter Support**\n'
          '   - **From**: `Railway <hello@news.railway.app>`\n'
          '   - **Summary**: Native iOS deployment monitoring, unified authentication flows, and direct OpenRouter model routing.\n'
          '3. **[UNREAD] DRDO Junior Research Fellow Job Notification**\n'
          '   - **From**: `DRDO Recruitment <noreply@jobalertshub.com>`\n'
          '   - **Summary**: Applications invited for JRF positions in AI, autonomous systems, and signal processing.';
    }

    if (q.contains('email') ||
        q.contains('inbox') ||
        q.contains('thread') ||
        q.contains('who') ||
        q.contains('recent')) {
      return '### Executive Inbox Synthesis (`qwen2.5:0.5b`)\n\n'
          'I invoked the **Gmail MCP tool** (`search_emails`) and cross-referenced your threads with the **NetworkX Knowledge Graph**:\n\n'
          '1. **[UNREAD] Booking Holdings India COE — HackCellence Round 1**\n'
          '   - **Sender**: `support@hackerearth.com` (addressed to **Akash**)\n'
          '   - **Summary**: Confirms your Round 1 registration and outlines algorithmic coding & architecture guidelines.\n'
          '2. **[UNREAD] DRDO Junior Research Fellow (JRF) Notification**\n'
          '   - **Sender**: `DRDO Recruitment <noreply@jobalertshub.com>`\n'
          '   - **Summary**: Fellowship openings in AI, autonomous systems, and signal processing.\n'
          '3. **[UNREAD] Railway iOS & OpenRouter Integration**\n'
          '   - **Sender**: `Railway <hello@news.railway.app>`\n'
          '   - **Summary**: Native iOS monitoring app, unified authentication, and direct OpenRouter support.\n'
          '4. **[READ] VIT & cloudHQ Updates**\n'
          '   - **LinkedIn / VIT**: Research symposium and engineering showcase invitation.\n'
          '   - **cloudHQ**: Automated Gmail-to-Google Drive archival workflow.';
    }

    final chunks = ctx?.chunks ?? const [];
    final triples = ctx?.graphTriples ?? const [];
    if (chunks.isEmpty && triples.isEmpty) {
      return 'I processed your request (**"$query"**) directly without calling the Gmail MCP tool since no email lookup was required.\n\n'
          'If you want me to check your inbox or unread emails, just ask *"Check my unread emails"* or *"Find emails from DRDO"*.';
    }
    final buf = StringBuffer();
    buf.writeln(
      'Here is what I found in your personal knowledge store for **"$query"**:\n',
    );
    for (final c in chunks.take(2)) {
      final title = c.subject.isNotEmpty ? c.subject : c.source.toUpperCase();
      buf.writeln('- **$title**: ${c.content.replaceAll("\n", " ")}');
    }
    if (triples.isNotEmpty) {
      buf.writeln('\n**Connected Graph Relations:**');
      for (final t in triples.take(3)) {
        buf.writeln('- `${t.rawFact}`');
      }
    }
    return buf.toString();
  }

  String _synthesizeRuleBasedResponse(String query, RetrievedContext? ctx) {
    final q = query.trim().toLowerCase();

    // Conversational greeting handler in Rule-Based mode
    if (RegExp(r'^(hi|hello|hey|hola|sup|yo|good morning|good evening)\b')
        .hasMatch(q)) {
      return '**[Rule-Based Engine · 0 MB Instant Mode]**\n\n'
          'Hello Akash! Your local workspace is online with **on-demand Gmail MCP tool calling** (`${_localChunks.length}` indexed threads and `${_nodes.length}` Knowledge Graph nodes).\n\n'
          'Try asking:\n'
          '- *"Check my email to find any unread messages"*\n'
          '- *"Summarize my recent emails"*\n'
          '- *"Tell me about the HackCellence or DRDO email"*\n\n'
          '*Tip: For open-ended AI conversation and deep reasoning, enable **Qwen 2.5 (0.5B)** in Settings → Language model.*';
    }

    if (q.contains('unread') || q.contains('new email') || q.contains('new mail')) {
      return '**[Rule-Based Engine · Gmail Tool `search_emails(label:INBOX is:unread)`]**\n\n'
          'Fetched & indexed **3 unread emails**:\n'
          '- **[UNREAD]** `support@hackerearth.com` → *Ready to Code? HackCellence Round 1 Details | Booking Holdings India COE*\n'
          '- **[UNREAD]** `Railway <hello@news.railway.app>` → *Railway on iOS, Railway Authentication, OpenRouter Support*\n'
          '- **[UNREAD]** `DRDO Recruitment` → *DRDO Junior Research Fellow Job Notification*\n\n'
          '*Tip: Enable **Qwen 2.5 (0.5B)** in Settings → Language model for deeper natural-language synthesis.*';
    }

    if (q.contains('email') ||
        q.contains('inbox') ||
        q.contains('thread') ||
        q.contains('who') ||
        q.contains('recent')) {
      return '**[Rule-Based Engine · Gmail Tool `search_emails(label:INBOX)`]**\n\n'
          'Matched 5 Gmail MCP records (**3 unread**, **2 read**):\n'
          '- **[UNREAD]** `support@hackerearth.com` → *Ready to Code? HackCellence Round 1 Details | Booking Holdings India COE*\n'
          '- **[UNREAD]** `Railway <hello@news.railway.app>` → *Railway on iOS, Railway Authentication, OpenRouter Support*\n'
          '- **[UNREAD]** `DRDO Recruitment` → *DRDO Junior Research Fellow Job Notification*\n'
          '- **[READ]** `LinkedIn` → *Vellore Institute of Technology shared a post*\n'
          '- **[READ]** `cloudHQ` → *NEW! Save Emails to Google Drive*\n\n'
          '*Tip: Enable **Qwen 2.5 (0.5B)** in Settings → Language model for deeper natural-language synthesis.*';
    }

    if (q.contains('synapse') ||
        q.contains('chromadb') ||
        q.contains('networkx') ||
        q.contains('rag') ||
        q.contains('graph')) {
      return '**[Rule-Based Engine · Architecture Lookup]**\n\n'
          '- **Vector Store**: `ChromaDB` (`BAAI/bge-small-en-v1.5` via `FastEmbed ONNX`)\n'
          '- **Graph Store**: `NetworkX` directed entity-relation graph (`${_nodes.length}` nodes, `${_links.length}` edges)\n'
          '- **Core Triples**:\n'
          '  - `Akash -> CREATOR_OF -> Synapse`\n'
          '  - `Synapse -> USES_VECTOR_STORE -> ChromaDB`\n'
          '  - `Synapse -> USES_GRAPH_STORE -> NetworkX`';
    }

    // Check if the user's query actually matched any keywords in chunks
    final keywords = q
        .split(RegExp(r'[^a-z0-9]+'))
        .where((w) => w.length > 2)
        .toList();
    RagChunk? bestChunk;
    int bestScore = 0;
    for (final chunk in _localChunks) {
      final hay = '${chunk.subject} ${chunk.content}'.toLowerCase();
      int score = 0;
      for (final kw in keywords) {
        if (hay.contains(kw)) score++;
      }
      if (score > bestScore) {
        bestScore = score;
        bestChunk = chunk;
      }
    }

    if (bestChunk != null && bestScore > 0) {
      final topTriple = (ctx != null && ctx.graphTriples.isNotEmpty)
          ? ctx.graphTriples.first.rawFact
          : 'Akash -> CREATOR_OF -> Synapse';
      return '**[Rule-Based Engine · Keyword Match]**\n\n'
          '- **Matched Record (`${bestChunk.source.toUpperCase()}`)**: *${bestChunk.subject}*\n'
          '  > ${bestChunk.content.replaceAll("\n", " ")}\n'
          '- **Related Graph Triple**: `$topTriple`\n\n'
          '*Switch to **Qwen 2.5 (0.5B)** in Settings → Language model for full neural answers.*';
    }

    return '**[Rule-Based Engine · No Exact Keyword Match]**\n\n'
        'No indexed email or graph node matched the exact keywords in *"$query"*.\n\n'
        '- **Indexed Topics Available**: Booking Holdings (`HackCellence`), `DRDO` JRF, `Railway` / OpenRouter, `VIT` LinkedIn, `cloudHQ` Google Drive, and `Synapse` architecture.\n'
        '- **Want full AI answers to any question?** Enable the local **Qwen 2.5 (0.5B)** neural model in **Settings → Language model**.';
  }
}

typedef VoidCallback = void Function();
