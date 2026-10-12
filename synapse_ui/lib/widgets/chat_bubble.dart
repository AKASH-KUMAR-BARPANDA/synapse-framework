import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';

import '../models/message.dart';
import '../theme/matte_theme.dart';
import 'context_inspector.dart';

/// Conversational message widget supporting user bubbles, assistant markdown
/// streams, `ContextInspector` accordion cards, and inline retry error banners.
class ChatBubble extends StatelessWidget {
  final ChatMessage message;
  final VoidCallback? onRetry;

  const ChatBubble({
    super.key,
    required this.message,
    this.onRetry,
  });

  @override
  Widget build(BuildContext context) {
    if (message.isUser) {
      return _buildUserBubble(context);
    }
    return _buildAssistantTurn(context);
  }

  Widget _buildUserBubble(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 10),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.end,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(width: 48),
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
              decoration: BoxDecoration(
                color: MatteColors.panel,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: MatteColors.borderSubtle, width: 1),
              ),
              child: SelectableText(
                message.content,
                style: const TextStyle(
                  color: MatteColors.textPrimary,
                  fontSize: 14,
                  height: 1.5,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAssistantTurn(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Assistant Matte Avatar
          Container(
            width: 28,
            height: 28,
            margin: const EdgeInsets.only(top: 2, right: 12),
            decoration: BoxDecoration(
              color: MatteColors.panel,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: MatteColors.borderSubtle, width: 1),
            ),
            child: const Icon(
              Icons.auto_awesome_mosaic_outlined,
              size: 14,
              color: MatteColors.nodePerson,
            ),
          ),

          // Main Content Column
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // 1. Retrieved Context Inspector Accordion when `use_rag: true`
                if (message.useRag)
                  ContextInspector(
                    contextData: message.retrievedContext,
                    isStreaming: message.isStreaming,
                    contextReceived: message.contextReceived,
                  ),

                // 2. Markdown Body or Streaming Placeholder
                if (message.content.isNotEmpty)
                  MarkdownBody(
                    data: message.isStreaming
                        ? '${message.content} ▍'
                        : message.content,
                    selectable: true,
                    styleSheet: _matteMarkdownStyle(context),
                  )
                else if (message.isStreaming)
                  const Padding(
                    padding: EdgeInsets.symmetric(vertical: 6),
                    child: Row(
                      children: [
                        SizedBox(
                          width: 12,
                          height: 12,
                          child: CircularProgressIndicator(
                            strokeWidth: 1.6,
                            color: MatteColors.textSecondary,
                          ),
                        ),
                        SizedBox(width: 8),
                        Text(
                          'Synthesizing response...',
                          style: TextStyle(
                            color: MatteColors.textMuted,
                            fontSize: 12.5,
                          ),
                        ),
                      ],
                    ),
                  ),

                // 3. Inline Warning Banner on `event: error` with Retry option
                if (message.hasError) ...[
                  const SizedBox(height: 10),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 10,
                    ),
                    decoration: BoxDecoration(
                      color: MatteColors.inset,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(
                        color: MatteColors.statusWarning,
                        width: 1,
                      ),
                    ),
                    child: Row(
                      children: [
                        const Icon(
                          Icons.warning_amber_rounded,
                          size: 16,
                          color: MatteColors.statusWarning,
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                'Stream Interrupted (${message.errorStage ?? 'error'})',
                                style: const TextStyle(
                                  color: MatteColors.textPrimary,
                                  fontSize: 12,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                message.errorMessage ?? 'Unknown error',
                                style: const TextStyle(
                                  color: MatteColors.textSecondary,
                                  fontSize: 12,
                                ),
                              ),
                            ],
                          ),
                        ),
                        if (onRetry != null) ...[
                          const SizedBox(width: 8),
                          InkWell(
                            onTap: onRetry,
                            borderRadius: BorderRadius.circular(5),
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 10,
                                vertical: 6,
                              ),
                              decoration: BoxDecoration(
                                color: MatteColors.panel,
                                borderRadius: BorderRadius.circular(5),
                                border: Border.all(
                                  color: MatteColors.borderStrong,
                                  width: 1,
                                ),
                              ),
                              child: const Row(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    Icons.refresh_rounded,
                                    size: 13,
                                    color: MatteColors.textPrimary,
                                  ),
                                  SizedBox(width: 5),
                                  Text(
                                    'Retry',
                                    style: TextStyle(
                                      color: MatteColors.textPrimary,
                                      fontSize: 12,
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                  ),
                ],

                // 4. Subtle Action Bar (Copy response)
                if (!message.isStreaming && message.content.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 6),
                    child: Row(
                      children: [
                        InkWell(
                          onTap: () {
                            Clipboard.setData(
                              ClipboardData(text: message.content),
                            );
                            ScaffoldMessenger.of(context).showSnackBar(
                              const SnackBar(
                                content: Text('Copied response to clipboard'),
                                duration: Duration(seconds: 2),
                              ),
                            );
                          },
                          borderRadius: BorderRadius.circular(4),
                          child: const Padding(
                            padding: EdgeInsets.symmetric(
                              horizontal: 6,
                              vertical: 4,
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  Icons.copy_rounded,
                                  size: 12,
                                  color: MatteColors.textMuted,
                                ),
                                SizedBox(width: 4),
                                Text(
                                  'Copy',
                                  style: TextStyle(
                                    color: MatteColors.textMuted,
                                    fontSize: 11,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  MarkdownStyleSheet _matteMarkdownStyle(BuildContext context) {
    return MarkdownStyleSheet(
      p: const TextStyle(
        color: MatteColors.textPrimary,
        fontSize: 14,
        height: 1.58,
      ),
      h1: const TextStyle(
        color: MatteColors.textPrimary,
        fontSize: 20,
        fontWeight: FontWeight.w600,
        height: 1.4,
      ),
      h2: const TextStyle(
        color: MatteColors.textPrimary,
        fontSize: 17,
        fontWeight: FontWeight.w600,
        height: 1.4,
      ),
      h3: const TextStyle(
        color: MatteColors.textPrimary,
        fontSize: 15,
        fontWeight: FontWeight.w600,
        height: 1.4,
      ),
      listBullet: const TextStyle(
        color: MatteColors.textSecondary,
        fontSize: 14,
      ),
      strong: const TextStyle(
        color: MatteColors.textPrimary,
        fontWeight: FontWeight.w600,
      ),
      em: const TextStyle(
        color: MatteColors.textSecondary,
        fontStyle: FontStyle.italic,
      ),
      blockquote: const TextStyle(
        color: MatteColors.textSecondary,
        fontSize: 13.5,
      ),
      blockquoteDecoration: const BoxDecoration(
        color: MatteColors.inset,
        border: Border(
          left: BorderSide(color: MatteColors.borderStrong, width: 3),
        ),
      ),
      code: const TextStyle(
        color: MatteColors.nodePerson,
        backgroundColor: MatteColors.inset,
        fontFamily: 'monospace',
        fontSize: 12.5,
      ),
      codeblockPadding: const EdgeInsets.all(12),
      codeblockDecoration: BoxDecoration(
        color: MatteColors.inset,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: MatteColors.borderSubtle, width: 1),
      ),
      horizontalRuleDecoration: const BoxDecoration(
        border: Border(
          top: BorderSide(color: MatteColors.borderSubtle, width: 1),
        ),
      ),
    );
  }
}
