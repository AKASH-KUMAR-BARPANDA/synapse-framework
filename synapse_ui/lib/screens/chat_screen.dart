import 'dart:async';
import 'package:flutter/material.dart';

import '../models/message.dart';
import '../services/api_service.dart';
import '../services/sse_client.dart';
import '../theme/matte_theme.dart';
import '../widgets/chat_bubble.dart';
import '../widgets/chat_input.dart';

/// Conversational AI screen streaming tokens from `POST /chat` or on-device `llama.cpp`.
class ChatScreen extends StatefulWidget {
  final ApiService apiService;
  final VoidCallback? onOpenConnectors;
  final VoidCallback? onOpenGraph;

  const ChatScreen({
    super.key,
    required this.apiService,
    this.onOpenConnectors,
    this.onOpenGraph,
  });

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final SseClient _sseClient = SseClient();
  final ScrollController _scrollController = ScrollController();

  StreamSubscription<SseChatEvent>? _streamSubscription;
  bool _isStreaming = false;
  bool _isModelPromptOpen = false;
  late bool _useRag;

  @override
  void initState() {
    super.initState();
    _useRag = widget.apiService.defaultUseRag;
  }

  @override
  void dispose() {
    _streamSubscription?.cancel();
    _sseClient.cancel();
    _scrollController.dispose();
    super.dispose();
  }

  void _scrollToBottom({bool animated = true}) {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_scrollController.hasClients) return;
      final target = _scrollController.position.maxScrollExtent;
      if (animated) {
        _scrollController.animateTo(
          target,
          duration: const Duration(milliseconds: 180),
          curve: Curves.easeOut,
        );
      } else {
        _scrollController.jumpTo(target);
      }
    });
  }

  /// Intercepts the user's very first message send when Qwen 2.5 is not yet
  /// downloaded, prompting them to either download Qwen 2.5 (469 MB) for better
  /// neural output or send immediately with the 0 MB Rule-Based Engine.
  Future<void> _handleUserSubmit(String text) async {
    final shouldPrompt = !widget.apiService.isQwenDownloaded &&
        !widget.apiService.hasSeenFirstChatModelPrompt;

    if (shouldPrompt && mounted) {
      final proceedToSend = await _showFirstMessageModelPromptModal(text);
      if (!proceedToSend || !mounted) return;
    }

    await _sendMessage(text);
  }

  Future<bool> _showFirstMessageModelPromptModal(String queuedMessage) async {
    setState(() => _isModelPromptOpen = true);
    try {
      final result = await showDialog<bool>(
        context: context,
        barrierDismissible: false,
        builder: (ctx) {
          return _FirstMessageModelPromptDialog(
            apiService: widget.apiService,
            queuedMessage: queuedMessage,
          );
        },
      );
      return result ?? false;
    } finally {
      if (mounted) {
        setState(() => _isModelPromptOpen = false);
      }
    }
  }

  Future<void> _sendMessage(
    String text, {
    List<ChatMessage>? customHistory,
  }) async {
    final session =
        widget.apiService.activeSession ?? widget.apiService.createNewSession();
    final sessionId = session.id;

    final existingMessages =
        customHistory ?? List<ChatMessage>.from(session.messages);
    final historyForRequest = List<ChatMessage>.from(existingMessages);

    final now = DateTime.now();
    final userMsg = ChatMessage(
      id: 'user_${now.microsecondsSinceEpoch}',
      role: 'user',
      content: text,
      timestamp: now,
      useRag: _useRag,
    );

    final assistantId = 'asst_${now.microsecondsSinceEpoch + 1}';
    var assistantMsg = ChatMessage(
      id: assistantId,
      role: 'assistant',
      content: '',
      timestamp: now,
      isStreaming: true,
      useRag: _useRag,
      contextReceived: false,
    );

    final updatedList = [...existingMessages, userMsg, assistantMsg];
    widget.apiService.updateSessionMessages(
      sessionId,
      updatedList,
      autoTitle: text,
    );

    setState(() => _isStreaming = true);
    _scrollToBottom();

    await _streamSubscription?.cancel();
    final stream = _sseClient.streamChat(
      endpoint: widget.apiService.buildUri('/chat'),
      message: text,
      history: historyForRequest,
      useRag: _useRag,
      embeddedEngine: widget.apiService.embeddedEngine,
      forceEmbedded: widget.apiService.healthStatus.isEmbeddedMode,
      useNeuralQwenModel: widget.apiService.useQwenModel,
    );

    _streamSubscription = stream.listen(
      (event) {
        if (!mounted) return;
        switch (event.type) {
          case SseEventType.context:
            assistantMsg = assistantMsg.copyWith(
              retrievedContext: event.context,
              contextReceived: true,
            );
            _replaceAssistantMessage(sessionId, assistantId, assistantMsg);
            _scrollToBottom(animated: false);
            break;

          case SseEventType.delta:
            final delta = event.tokenDelta ?? '';
            assistantMsg = assistantMsg.copyWith(
              content: assistantMsg.content + delta,
            );
            _replaceAssistantMessage(sessionId, assistantId, assistantMsg);
            _scrollToBottom(animated: false);
            break;

          case SseEventType.error:
            assistantMsg = assistantMsg.copyWith(
              isStreaming: false,
              errorStage: event.errorStage ?? 'error',
              errorMessage: event.errorDetail ?? 'Stream error occurred.',
            );
            _replaceAssistantMessage(sessionId, assistantId, assistantMsg);
            setState(() => _isStreaming = false);
            _scrollToBottom();
            break;

          case SseEventType.done:
            assistantMsg = assistantMsg.copyWith(
              isStreaming: false,
              contextReceived: true,
            );
            _replaceAssistantMessage(sessionId, assistantId, assistantMsg);
            setState(() => _isStreaming = false);
            _scrollToBottom();
            break;
        }
      },
      onError: (Object err) {
        if (!mounted) return;
        assistantMsg = assistantMsg.copyWith(
          isStreaming: false,
          errorStage: 'stream',
          errorMessage: err.toString(),
        );
        _replaceAssistantMessage(sessionId, assistantId, assistantMsg);
        setState(() => _isStreaming = false);
      },
      onDone: () {
        if (!mounted) return;
        if (assistantMsg.isStreaming) {
          assistantMsg = assistantMsg.copyWith(
            isStreaming: false,
            contextReceived: true,
          );
          _replaceAssistantMessage(sessionId, assistantId, assistantMsg);
        }
        setState(() => _isStreaming = false);
      },
    );
  }

  void _replaceAssistantMessage(
    String sessionId,
    String assistantId,
    ChatMessage updatedAssistant,
  ) {
    final session = widget.apiService.activeSession;
    if (session == null || session.id != sessionId) return;
    final list = List<ChatMessage>.from(session.messages);
    final idx = list.indexWhere((m) => m.id == assistantId);
    if (idx != -1) {
      list[idx] = updatedAssistant;
      widget.apiService.updateSessionMessages(sessionId, list);
    }
  }

  void _stopStreaming() {
    _streamSubscription?.cancel();
    _sseClient.cancel();
    final session = widget.apiService.activeSession;
    if (session != null && session.messages.isNotEmpty) {
      final list = List<ChatMessage>.from(session.messages);
      final last = list.last;
      if (last.isStreaming) {
        list[list.length - 1] = last.copyWith(
          isStreaming: false,
          contextReceived: true,
        );
        widget.apiService.updateSessionMessages(session.id, list);
      }
    }
    setState(() => _isStreaming = false);
  }

  void _retryFailedTurn(int assistantIndex, List<ChatMessage> messages) {
    if (_isStreaming) return;
    int userIdx = -1;
    for (int i = assistantIndex - 1; i >= 0; i--) {
      if (messages[i].isUser) {
        userIdx = i;
        break;
      }
    }
    if (userIdx == -1) return;

    final promptText = messages[userIdx].content;
    final historyBeforeTurn = messages.sublist(0, userIdx);
    _sendMessage(promptText, customHistory: historyBeforeTurn);
  }

  @override
  Widget build(BuildContext context) {
    final isMobile = MatteBreakpoints.isMobile(context);
    final session = widget.apiService.activeSession;
    final messages = session?.messages ?? const [];

    return Container(
      color: MatteColors.canvas,
      child: Column(
        children: [
          // Background Download Progress Strip (if downloading while chatting)
          if (widget.apiService.isDownloadingQwen && !_isModelPromptOpen)
            _BackgroundDownloadStrip(apiService: widget.apiService),

          // Main Conversational Stream Area
          Expanded(
            child: messages.isEmpty
                ? _buildEmptyState(context, isMobile)
                : ListView.builder(
                    controller: _scrollController,
                    padding: EdgeInsets.symmetric(
                      horizontal: isMobile ? 14 : 28,
                      vertical: 18,
                    ),
                    itemCount: messages.length,
                    itemBuilder: (context, index) {
                      final msg = messages[index];
                      return Center(
                        child: ConstrainedBox(
                          constraints: const BoxConstraints(
                            maxWidth: MatteBreakpoints.chatMaxWidth,
                          ),
                          child: ChatBubble(
                            message: msg,
                            onRetry: msg.hasError
                                ? () => _retryFailedTurn(index, messages)
                                : null,
                          ),
                        ),
                      );
                    },
                  ),
          ),

          // Bottom Sunken / Floating Input Container
          Container(
            padding: EdgeInsets.fromLTRB(
              isMobile ? 12 : 28,
              6,
              isMobile ? 12 : 28,
              isMobile ? 12 : 18,
            ),
            decoration: const BoxDecoration(
              color: MatteColors.canvas,
            ),
            child: Center(
              child: ConstrainedBox(
                constraints: const BoxConstraints(
                  maxWidth: MatteBreakpoints.chatMaxWidth,
                ),
                child: ChatInput(
                  isStreaming: _isStreaming,
                  useRag: _useRag,
                  isCompact: isMobile,
                  onToggleRag: (val) => setState(() => _useRag = val),
                  onSubmit: _handleUserSubmit,
                  onStop: _stopStreaming,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmptyState(BuildContext context, bool isMobile) {
    final health = widget.apiService.healthStatus;
    final gmail = widget.apiService.gmailConnector;

    const starterPrompts = [
      (
        title: 'Summarize recent inbox threads',
        prompt:
            'What are the key updates and action items from my recent emails?',
        icon: Icons.mark_email_unread_outlined,
      ),
      (
        title: 'Query Knowledge Graph entities',
        prompt:
            'Who has sent me emails recently and what topics or projects are they connected to?',
        icon: Icons.hub_outlined,
      ),
      (
        title: 'Inspect technical architecture notes',
        prompt:
            'What tools, libraries, or deadlines were mentioned in my messages?',
        icon: Icons.terminal_rounded,
      ),
      (
        title: 'Direct local LLM reasoning',
        prompt:
            'Explain how Synapse combines ChromaDB vector search with NetworkX graph triples.',
        icon: Icons.psychology_outlined,
      ),
    ];

    return SingleChildScrollView(
      padding: EdgeInsets.symmetric(
        horizontal: isMobile ? 16 : 32,
        vertical: 24,
      ),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 680),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              // Matte Emblem
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: MatteColors.panel,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: MatteColors.borderStrong,
                    width: 1,
                  ),
                ),
                child: const Icon(
                  Icons.hub_outlined,
                  size: 22,
                  color: MatteColors.nodePerson,
                ),
              ),
              const SizedBox(height: 14),
              const Text(
                'Synapse Personal Intelligence',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: MatteColors.textPrimary,
                  fontSize: 20,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.4,
                ),
              ),
              const SizedBox(height: 6),
              const Text(
                'Private, local-first hybrid RAG powered by ChromaDB vectors, NetworkX knowledge graphs, and on-device inference.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: MatteColors.textSecondary,
                  fontSize: 13.5,
                  height: 1.45,
                ),
              ),
              const SizedBox(height: 16),

              // Live Service Status Pills
              Wrap(
                spacing: 8,
                runSpacing: 8,
                alignment: WrapAlignment.center,
                children: [
                  _StatusPill(
                    label: 'Engine',
                    value: widget.apiService.useQwenModel
                        ? '${widget.apiService.modelName} (Neural)'
                        : 'Rule-Based (0 MB)',
                    isOk: true,
                  ),
                  _StatusPill(
                    label: 'ChromaDB',
                    value: health.chromaDb,
                    isOk: health.isChromaReady,
                  ),
                  GestureDetector(
                    onTap: widget.onOpenConnectors,
                    child: _StatusPill(
                      label: 'Gmail MCP',
                      value: gmail.status.label,
                      isOk: gmail.isAuthenticated,
                    ),
                  ),
                ],
              ),

              const SizedBox(height: 28),

              // Starter Prompt Grid
              LayoutBuilder(
                builder: (context, constraints) {
                  final crossAxisCount = constraints.maxWidth > 500 ? 2 : 1;
                  return GridView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: starterPrompts.length,
                    gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                      crossAxisCount: crossAxisCount,
                      crossAxisSpacing: 10,
                      mainAxisSpacing: 10,
                      mainAxisExtent: 82,
                    ),
                    itemBuilder: (context, index) {
                      final item = starterPrompts[index];
                      return _StarterPromptCard(
                        title: item.title,
                        subtitle: item.prompt,
                        icon: item.icon,
                        onTap: () => _handleUserSubmit(item.prompt),
                      );
                    },
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Compact top progress strip shown if the user continues chatting while Qwen 2.5 downloads.
class _BackgroundDownloadStrip extends StatelessWidget {
  final ApiService apiService;

  const _BackgroundDownloadStrip({required this.apiService});

  @override
  Widget build(BuildContext context) {
    final progress = apiService.qwenDownloadProgress;
    final recv = apiService.qwenDownloadedMB;
    final total = apiService.qwenTotalMB;
    final speed = apiService.qwenDownloadSpeedMBps;
    final speedText =
        speed > 0.05 ? ' · ${speed.toStringAsFixed(1)} MB/s' : '';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
      decoration: const BoxDecoration(
        color: MatteColors.panel,
        border: Border(
          bottom: BorderSide(color: MatteColors.borderSubtle, width: 1),
        ),
      ),
      child: Row(
        children: [
          const SizedBox(
            width: 14,
            height: 14,
            child: CircularProgressIndicator(
              strokeWidth: 2,
              color: MatteColors.nodeProject,
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'Downloading Qwen 2.5 GGUF: $recv / $total MB (${(progress * 100).round()}%)$speedText',
              style: const TextStyle(
                color: MatteColors.textPrimary,
                fontSize: 12,
                fontFamily: 'monospace',
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          InkWell(
            onTap: apiService.cancelQwenDownload,
            child: const Padding(
              padding: EdgeInsets.symmetric(horizontal: 6, vertical: 2),
              child: Text(
                'Cancel',
                style: TextStyle(
                  color: MatteColors.textSecondary,
                  fontSize: 11.5,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Modal dialog triggered when the user writes their first message and presses Send.
/// Lets the user either download & enable the real 379 MB Qwen 2.5 GGUF model
/// (and auto-sends once complete) or send immediately with the 0 MB Rule-Based Engine.
class _FirstMessageModelPromptDialog extends StatelessWidget {
  final ApiService apiService;
  final String queuedMessage;

  const _FirstMessageModelPromptDialog({
    required this.apiService,
    required this.queuedMessage,
  });

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: apiService,
      builder: (context, _) {
        final isDownloading = apiService.isDownloadingQwen;
        final progress = apiService.qwenDownloadProgress;
        final downloadedMB = apiService.qwenDownloadedMB;
        final totalMB = apiService.qwenTotalMB;
        final speed = apiService.qwenDownloadSpeedMBps;
        final error = apiService.qwenDownloadError;

        return Dialog(
          backgroundColor: MatteColors.panel,
          insetPadding:
              const EdgeInsets.symmetric(horizontal: 18, vertical: 24),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(18),
            side: const BorderSide(color: MatteColors.borderStrong, width: 1),
          ),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 460),
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(20),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  // Header
                  Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(9),
                        decoration: BoxDecoration(
                          color: MatteColors.inset,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(
                            color: MatteColors.borderStrong,
                            width: 1,
                          ),
                        ),
                        child: const Icon(
                          Icons.auto_awesome_outlined,
                          size: 20,
                          color: MatteColors.nodePerson,
                        ),
                      ),
                      const SizedBox(width: 12),
                      const Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Choose Your AI Engine',
                              style: TextStyle(
                                color: MatteColors.textPrimary,
                                fontSize: 17,
                                fontWeight: FontWeight.w600,
                                letterSpacing: -0.2,
                              ),
                            ),
                            SizedBox(height: 3),
                            Text(
                              'Before sending your first message, choose whether to download Qwen 2.5 for full neural answers.',
                              style: TextStyle(
                                color: MatteColors.textSecondary,
                                fontSize: 12.5,
                                height: 1.35,
                              ),
                            ),
                          ],
                        ),
                      ),
                      if (!isDownloading)
                        IconButton(
                          onPressed: () => Navigator.of(context).pop(false),
                          icon: const Icon(
                            Icons.close_rounded,
                            size: 18,
                            color: MatteColors.textMuted,
                          ),
                          visualDensity: VisualDensity.compact,
                        ),
                    ],
                  ),

                  const SizedBox(height: 14),

                  // Option 1 Card: Qwen 2.5 0.5B Neural Model
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: MatteColors.inset,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: MatteColors.nodePerson.withValues(alpha: 0.65),
                        width: 1,
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Expanded(
                              child: Text(
                                'Qwen 2.5 0.5B Instruct (Recommended)',
                                style: TextStyle(
                                  color: MatteColors.textPrimary,
                                  fontSize: 13.5,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 7,
                                vertical: 2,
                              ),
                              decoration: BoxDecoration(
                                color: MatteColors.panel,
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(
                                  color: MatteColors.borderSubtle,
                                  width: 1,
                                ),
                              ),
                              child: const Text(
                                '469 MB GGUF',
                                style: TextStyle(
                                  color: MatteColors.nodePerson,
                                  fontSize: 10.5,
                                  fontFamily: 'monospace',
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          '• True on-device neural LLM via llama.cpp\n'
                          '• Natural conversation & deep multi-email synthesis\n'
                          '• 100% offline privacy after one-time download',
                          style: TextStyle(
                            color: MatteColors.textSecondary,
                            fontSize: 12,
                            height: 1.42,
                          ),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 10),

                  // Option 2 Card: Rule-Based Engine
                  Container(
                    padding: const EdgeInsets.all(14),
                    decoration: BoxDecoration(
                      color: MatteColors.inset,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: MatteColors.borderSubtle,
                        width: 1,
                      ),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Expanded(
                              child: Text(
                                'Rule-Based Engine',
                                style: TextStyle(
                                  color: MatteColors.textPrimary,
                                  fontSize: 13.5,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 7,
                                vertical: 2,
                              ),
                              decoration: BoxDecoration(
                                color: MatteColors.panel,
                                borderRadius: BorderRadius.circular(6),
                                border: Border.all(
                                  color: MatteColors.borderSubtle,
                                  width: 1,
                                ),
                              ),
                              child: const Text(
                                '0 MB · Instant',
                                style: TextStyle(
                                  color: MatteColors.nodeProject,
                                  fontSize: 10.5,
                                  fontFamily: 'monospace',
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          '• Deterministic keyword & Knowledge Graph lookup\n'
                          '• Zero storage or RAM overhead (switch anytime in Settings)',
                          style: TextStyle(
                            color: MatteColors.textSecondary,
                            fontSize: 12,
                            height: 1.42,
                          ),
                        ),
                      ],
                    ),
                  ),

                  if (error != null && !isDownloading) ...[
                    const SizedBox(height: 12),
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: MatteColors.inset,
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(
                          color: MatteColors.statusDanger,
                          width: 1,
                        ),
                      ),
                      child: Text(
                        'Download failed: $error',
                        style: const TextStyle(
                          color: MatteColors.statusDanger,
                          fontSize: 12,
                        ),
                      ),
                    ),
                  ],

                  const SizedBox(height: 16),

                  // Action Buttons or Live Download Progress
                  if (isDownloading) ...[
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Expanded(
                          child: Text(
                            '$downloadedMB MB / $totalMB MB'
                            '${speed > 0.05 ? " · ${speed.toStringAsFixed(1)} MB/s" : " · Connecting..."}',
                            style: const TextStyle(
                              color: MatteColors.textPrimary,
                              fontSize: 12,
                              fontFamily: 'monospace',
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        Text(
                          '${(progress * 100).round()}%',
                          style: const TextStyle(
                            color: MatteColors.nodeProject,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(5),
                      child: LinearProgressIndicator(
                        value: progress > 0.01 ? progress : null,
                        minHeight: 7,
                        backgroundColor: MatteColors.inset,
                        valueColor: const AlwaysStoppedAnimation<Color>(
                          MatteColors.nodeProject,
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),
                    // Full-width button: Send Now (Download in background)
                    InkWell(
                      onTap: () async {
                        await apiService.dismissFirstChatModelPrompt();
                        if (context.mounted) {
                          Navigator.of(context).pop(true);
                        }
                      },
                      borderRadius: BorderRadius.circular(24),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 11,
                        ),
                        decoration: BoxDecoration(
                          color: MatteColors.inset,
                          borderRadius: BorderRadius.circular(24),
                          border: Border.all(
                            color: MatteColors.nodePerson.withValues(alpha: 0.7),
                            width: 1,
                          ),
                        ),
                        child: const Center(
                          child: Text(
                            'Send Now (Download in background)',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              color: MatteColors.nodePerson,
                              fontSize: 12.5,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    // Full-width button: Pause / Cancel
                    InkWell(
                      onTap: apiService.cancelQwenDownload,
                      borderRadius: BorderRadius.circular(24),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 9,
                        ),
                        child: const Center(
                          child: Text(
                            'Pause / Cancel Download',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              color: MatteColors.textSecondary,
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ] else ...[
                    // Primary CTA: Download & Send with Qwen 2.5
                    InkWell(
                      onTap: () async {
                        final ok = await apiService.downloadQwenModel();
                        if (ok && context.mounted) {
                          Navigator.of(context).pop(true);
                        }
                      },
                      borderRadius: BorderRadius.circular(24),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 18,
                          vertical: 12,
                        ),
                        decoration: BoxDecoration(
                          color: MatteColors.textPrimary,
                          borderRadius: BorderRadius.circular(24),
                        ),
                        child: const Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.download_rounded,
                              size: 17,
                              color: MatteColors.canvas,
                            ),
                            SizedBox(width: 8),
                            Flexible(
                              child: Text(
                                'Download Qwen 2.5 (469 MB) & Send',
                                style: TextStyle(
                                  color: MatteColors.canvas,
                                  fontSize: 13.5,
                                  fontWeight: FontWeight.w600,
                                ),
                                overflow: TextOverflow.ellipsis,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 10),
                    // Secondary CTA: Send with Rule-Based Engine
                    InkWell(
                      onTap: () async {
                        await apiService.dismissFirstChatModelPrompt();
                        if (context.mounted) {
                          Navigator.of(context).pop(true);
                        }
                      },
                      borderRadius: BorderRadius.circular(24),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 18,
                          vertical: 11,
                        ),
                        decoration: BoxDecoration(
                          color: MatteColors.inset,
                          borderRadius: BorderRadius.circular(24),
                          border: Border.all(
                            color: MatteColors.borderStrong,
                            width: 1,
                          ),
                        ),
                        child: const Center(
                          child: Text(
                            'Send with Rule-Based Engine (0 MB)',
                            style: TextStyle(
                              color: MatteColors.textPrimary,
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

class _StatusPill extends StatelessWidget {
  final String label;
  final String value;
  final bool isOk;

  const _StatusPill({
    required this.label,
    required this.value,
    required this.isOk,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: MatteColors.panel,
        borderRadius: BorderRadius.circular(5),
        border: Border.all(color: MatteColors.borderSubtle, width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: isOk
                  ? MatteColors.statusConnected
                  : MatteColors.statusWarning,
            ),
          ),
          const SizedBox(width: 7),
          Text(
            '$label: ',
            style: const TextStyle(
              color: MatteColors.textMuted,
              fontSize: 11.5,
            ),
          ),
          Text(
            value,
            style: const TextStyle(
              color: MatteColors.textPrimary,
              fontSize: 11.5,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

class _StarterPromptCard extends StatefulWidget {
  final String title;
  final String subtitle;
  final IconData icon;
  final VoidCallback onTap;

  const _StarterPromptCard({
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.onTap,
  });

  @override
  State<_StarterPromptCard> createState() => _StarterPromptCardState();
}

class _StarterPromptCardState extends State<_StarterPromptCard> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 120),
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: _hovered ? MatteColors.panelHover : MatteColors.panel,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(
              color:
                  _hovered ? MatteColors.borderStrong : MatteColors.borderSubtle,
              width: 1,
            ),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                widget.icon,
                size: 16,
                color: MatteColors.nodePerson,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      widget.title,
                      style: const TextStyle(
                        color: MatteColors.textPrimary,
                        fontSize: 12.5,
                        fontWeight: FontWeight.w500,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                    const SizedBox(height: 3),
                    Text(
                      widget.subtitle,
                      style: const TextStyle(
                        color: MatteColors.textMuted,
                        fontSize: 11.5,
                        height: 1.3,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
