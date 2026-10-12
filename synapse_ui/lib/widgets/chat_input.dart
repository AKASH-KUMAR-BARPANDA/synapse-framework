import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../theme/matte_theme.dart';

/// Bottom sunken input bar (`#121215`) with auto-expanding multiline text box,
/// Hybrid RAG toggle, submit/stop button, and keyboard shortcuts
/// (`Enter` to submit, `Shift + Enter` for new line).
class ChatInput extends StatefulWidget {
  final ValueChanged<String> onSubmit;
  final VoidCallback? onStop;
  final bool isStreaming;
  final bool useRag;
  final ValueChanged<bool> onToggleRag;
  final bool isCompact;

  const ChatInput({
    super.key,
    required this.onSubmit,
    required this.isStreaming,
    required this.useRag,
    required this.onToggleRag,
    this.onStop,
    this.isCompact = false,
  });

  @override
  State<ChatInput> createState() => _ChatInputState();
}

class _ChatInputState extends State<ChatInput> {
  final TextEditingController _controller = TextEditingController();
  late final FocusNode _focusNode;
  bool _isFocused = false;
  bool _hasText = false;

  @override
  void initState() {
    super.initState();
    _focusNode = FocusNode(
      onKeyEvent: (node, event) {
        if (event is KeyDownEvent &&
            event.logicalKey == LogicalKeyboardKey.enter) {
          final isShiftPressed = HardwareKeyboard.instance.isShiftPressed;
          if (!isShiftPressed) {
            _handleSend();
            return KeyEventResult.handled;
          }
        }
        return KeyEventResult.ignored;
      },
    );
    _focusNode.addListener(() {
      if (mounted) {
        setState(() => _isFocused = _focusNode.hasFocus);
      }
    });
    _controller.addListener(() {
      final nonEmpty = _controller.text.trim().isNotEmpty;
      if (nonEmpty != _hasText && mounted) {
        setState(() => _hasText = nonEmpty);
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _handleSend() {
    if (widget.isStreaming) return;
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    _controller.clear();
    setState(() => _hasText = false);
    widget.onSubmit(text);
    _focusNode.requestFocus();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: MatteTheme.insetDecoration(
        isFocused: _isFocused,
        borderRadius: 8,
      ),
      padding: EdgeInsets.fromLTRB(
        12,
        widget.isCompact ? 6 : 8,
        10,
        widget.isCompact ? 6 : 8,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Multiline Auto-Expanding TextField
          TextField(
            controller: _controller,
            focusNode: _focusNode,
            minLines: 1,
            maxLines: 6,
            keyboardType: TextInputType.multiline,
            textInputAction: TextInputAction.newline,
            style: const TextStyle(
              color: MatteColors.textPrimary,
              fontSize: 14,
              height: 1.45,
            ),
            decoration: const InputDecoration(
              hintText:
                  'Ask Synapse anything across your emails & knowledge graph...',
              border: InputBorder.none,
              enabledBorder: InputBorder.none,
              focusedBorder: InputBorder.none,
              filled: false,
              contentPadding: EdgeInsets.symmetric(
                horizontal: 2,
                vertical: 4,
              ),
            ),
          ),

          const SizedBox(height: 6),

          // Bottom Control Strip inside Sunken Input
          Row(
            children: [
              // Hybrid RAG Toggle Chip
              InkWell(
                onTap: () => widget.onToggleRag(!widget.useRag),
                borderRadius: BorderRadius.circular(5),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: widget.useRag
                        ? MatteColors.panelHover
                        : MatteColors.panel,
                    borderRadius: BorderRadius.circular(5),
                    border: Border.all(
                      color: widget.useRag
                          ? MatteColors.borderStrong
                          : MatteColors.borderSubtle,
                      width: 1,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 6,
                        height: 6,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: widget.useRag
                              ? MatteColors.nodeProject
                              : MatteColors.textMuted,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        widget.useRag ? 'Hybrid RAG: ON' : 'Hybrid RAG: OFF',
                        style: TextStyle(
                          color: widget.useRag
                              ? MatteColors.textPrimary
                              : MatteColors.textMuted,
                          fontSize: 11.5,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ),

              const Spacer(),

              if (!widget.isCompact)
                const Padding(
                  padding: EdgeInsets.only(right: 10),
                  child: Text(
                    'Enter to send · Shift+Enter for newline',
                    style: TextStyle(
                      color: MatteColors.textMuted,
                      fontSize: 11,
                    ),
                  ),
                ),

              // Submit or Stop Button
              if (widget.isStreaming)
                InkWell(
                  onTap: widget.onStop,
                  borderRadius: BorderRadius.circular(6),
                  child: Container(
                    height: 30,
                    padding: const EdgeInsets.symmetric(horizontal: 10),
                    decoration: BoxDecoration(
                      color: MatteColors.panelHover,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(
                        color: MatteColors.borderStrong,
                        width: 1,
                      ),
                    ),
                    child: const Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(
                          Icons.stop_rounded,
                          size: 15,
                          color: MatteColors.statusDanger,
                        ),
                        SizedBox(width: 4),
                        Text(
                          'Stop',
                          style: TextStyle(
                            color: MatteColors.textPrimary,
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                )
              else
                InkWell(
                  onTap: _hasText ? _handleSend : null,
                  borderRadius: BorderRadius.circular(6),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 120),
                    width: 32,
                    height: 30,
                    decoration: BoxDecoration(
                      color: _hasText
                          ? MatteColors.textPrimary
                          : MatteColors.panel,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(
                        color: _hasText
                            ? MatteColors.textPrimary
                            : MatteColors.borderSubtle,
                        width: 1,
                      ),
                    ),
                    child: Icon(
                      Icons.arrow_upward_rounded,
                      size: 16,
                      color: _hasText
                          ? MatteColors.canvas
                          : MatteColors.textMuted,
                    ),
                  ),
                ),
            ],
          ),
        ],
      ),
    );
  }
}
