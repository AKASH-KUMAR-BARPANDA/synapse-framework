import 'package:flutter/material.dart';

import '../models/connector.dart';
import '../models/message.dart';
import '../services/api_service.dart';
import '../theme/matte_theme.dart';

/// Navigation routes in the Synapse shell.
enum SynapseDestination {
  chat,
  connectors,
  graph,
  settings,
}

/// Collapsible Matte Sidebar used in Desktop/Tablet split view and Mobile Drawer.
class MatteSidebar extends StatelessWidget {
  final ApiService apiService;
  final SynapseDestination activeDestination;
  final ValueChanged<SynapseDestination> onSelectDestination;
  final VoidCallback onNewChat;
  final ValueChanged<String> onSelectSession;
  final VoidCallback? onToggleCollapse;
  final VoidCallback? onOpenSettingsModal;
  final bool isDrawer;

  const MatteSidebar({
    super.key,
    required this.apiService,
    required this.activeDestination,
    required this.onSelectDestination,
    required this.onNewChat,
    required this.onSelectSession,
    this.onToggleCollapse,
    this.onOpenSettingsModal,
    this.isDrawer = false,
  });

  @override
  Widget build(BuildContext context) {
    final gmail = apiService.gmailConnector;
    final health = apiService.healthStatus;
    final sessions = apiService.sessions;
    final activeSessionId = apiService.activeSessionId;

    return Container(
      width: MatteBreakpoints.sidebarExpandedWidth,
      decoration: const BoxDecoration(
        color: MatteColors.panel,
        border: Border(
          right: BorderSide(color: MatteColors.borderSubtle, width: 1),
        ),
      ),
      child: SafeArea(
        right: false,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // 1. Header Brand + Collapse Control
            Padding(
              padding: const EdgeInsets.fromLTRB(14, 14, 10, 10),
              child: Row(
                children: [
                  Container(
                    width: 24,
                    height: 24,
                    decoration: BoxDecoration(
                      color: MatteColors.inset,
                      borderRadius: BorderRadius.circular(5),
                      border: Border.all(
                        color: MatteColors.borderStrong,
                        width: 1,
                      ),
                    ),
                    child: const Icon(
                      Icons.hub_outlined,
                      size: 14,
                      color: MatteColors.nodePerson,
                    ),
                  ),
                  const SizedBox(width: 10),
                  const Expanded(
                    child: Text(
                      'Synapse',
                      style: TextStyle(
                        color: MatteColors.textPrimary,
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                        letterSpacing: -0.3,
                      ),
                    ),
                  ),
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 6,
                      vertical: 2,
                    ),
                    decoration: BoxDecoration(
                      color: MatteColors.inset,
                      borderRadius: BorderRadius.circular(4),
                      border: Border.all(
                        color: MatteColors.borderSubtle,
                        width: 1,
                      ),
                    ),
                    child: Text(
                      'LOCAL',
                      style: TextStyle(
                        color: health.isOnline
                            ? MatteColors.nodeProject
                            : MatteColors.textMuted,
                        fontSize: 9.5,
                        fontWeight: FontWeight.w600,
                        letterSpacing: 0.5,
                      ),
                    ),
                  ),
                  if (onToggleCollapse != null) ...[
                    const SizedBox(width: 4),
                    IconButton(
                      onPressed: onToggleCollapse,
                      icon: Icon(
                        isDrawer
                            ? Icons.close
                            : Icons.view_sidebar_outlined,
                        size: 17,
                        color: MatteColors.textSecondary,
                      ),
                      tooltip: isDrawer ? 'Close menu' : 'Collapse sidebar',
                      visualDensity: VisualDensity.compact,
                      splashRadius: 16,
                    ),
                  ],
                ],
              ),
            ),

            // 2. "+ New Chat" Button with clean matte border
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
              child: _NewChatButton(onPressed: onNewChat),
            ),

            const SizedBox(height: 8),

            // 3. Primary Navigation Entries (Connectors & Knowledge Graph)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Column(
                children: [
                  _SidebarNavTile(
                    icon: Icons.chat_bubble_outline_rounded,
                    label: 'Assistant Chat',
                    isSelected: activeDestination == SynapseDestination.chat,
                    onTap: () => onSelectDestination(SynapseDestination.chat),
                  ),
                  const SizedBox(height: 2),
                  _SidebarNavTile(
                    icon: Icons.cable_outlined,
                    label: 'Connectors',
                    isSelected:
                        activeDestination == SynapseDestination.connectors,
                    onTap: () =>
                        onSelectDestination(SynapseDestination.connectors),
                    trailing: _ConnectorStatusBadge(status: gmail.status),
                  ),
                  const SizedBox(height: 2),
                  _SidebarNavTile(
                    icon: Icons.grain_rounded,
                    label: 'Knowledge Graph',
                    isSelected: activeDestination == SynapseDestination.graph,
                    onTap: () => onSelectDestination(SynapseDestination.graph),
                    trailing: _GraphCountBadge(
                      nodeCount: apiService.graphStats.totalNodes,
                    ),
                  ),
                ],
              ),
            ),

            const SizedBox(height: 12),
            const Divider(height: 1, color: MatteColors.borderSubtle),

            // 4. Middle Section: Recent Chats Scrollable List
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 12, 6),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  const Text(
                    'RECENT CHATS',
                    style: TextStyle(
                      color: MatteColors.textMuted,
                      fontSize: 10.5,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.7,
                    ),
                  ),
                  Text(
                    '${sessions.length}',
                    style: const TextStyle(
                      color: MatteColors.textMuted,
                      fontSize: 10.5,
                    ),
                  ),
                ],
              ),
            ),

            Expanded(
              child: sessions.isEmpty
                  ? const Center(
                      child: Text(
                        'No conversations yet',
                        style: TextStyle(
                          color: MatteColors.textMuted,
                          fontSize: 12,
                        ),
                      ),
                    )
                  : ListView.builder(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 4,
                      ),
                      itemCount: sessions.length,
                      itemBuilder: (context, index) {
                        final session = sessions[index];
                        final isSelected =
                            activeDestination == SynapseDestination.chat &&
                                session.id == activeSessionId;
                        return _RecentChatItem(
                          session: session,
                          isSelected: isSelected,
                          onSelect: () => onSelectSession(session.id),
                          onRename: (newTitle) =>
                              apiService.renameSession(session.id, newTitle),
                          onDelete: () => apiService.deleteSession(session.id),
                        );
                      },
                    ),
            ),

            const Divider(height: 1, color: MatteColors.borderSubtle),

            // 5. Bottom Section: System Health & Settings Entry
            Padding(
              padding: const EdgeInsets.all(10),
              child: Column(
                children: [
                  // Subtle Backend Health Strip
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 10,
                      vertical: 7,
                    ),
                    margin: const EdgeInsets.only(bottom: 6),
                    decoration: BoxDecoration(
                      color: MatteColors.inset,
                      borderRadius: BorderRadius.circular(5),
                      border: Border.all(
                        color: MatteColors.borderSubtle,
                        width: 1,
                      ),
                    ),
                    child: Row(
                      children: [
                        Container(
                          width: 7,
                          height: 7,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: health.isOnline
                                ? MatteColors.statusConnected
                                : MatteColors.statusWarning,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            health.isEmbeddedMode
                                ? 'Standalone Engine Ready'
                                : (health.isOnline
                                    ? 'API Online · Ollama ${health.ollama}'
                                    : 'Backend Offline'),
                            style: const TextStyle(
                              color: MatteColors.textSecondary,
                              fontSize: 11.5,
                            ),
                            overflow: TextOverflow.ellipsis,
                          ),
                        ),
                        InkWell(
                          onTap: apiService.refreshSystemStatus,
                          borderRadius: BorderRadius.circular(4),
                          child: const Padding(
                            padding: EdgeInsets.all(2),
                            child: Icon(
                              Icons.refresh_rounded,
                              size: 13,
                              color: MatteColors.textMuted,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                  _SidebarNavTile(
                    icon: Icons.tune_rounded,
                    label: 'Settings',
                    isSelected:
                        activeDestination == SynapseDestination.settings,
                    onTap: () {
                      if (onOpenSettingsModal != null) {
                        onOpenSettingsModal!();
                      } else {
                        onSelectDestination(SynapseDestination.settings);
                      }
                    },
                    trailing: Text(
                      apiService.useQwenModel
                          ? apiService.modelName
                          : 'Rule-Based',
                      style: const TextStyle(
                        color: MatteColors.textMuted,
                        fontSize: 11,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _NewChatButton extends StatefulWidget {
  final VoidCallback onPressed;

  const _NewChatButton({required this.onPressed});

  @override
  State<_NewChatButton> createState() => _NewChatButtonState();
}

class _NewChatButtonState extends State<_NewChatButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onPressed,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 120),
          height: 36,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: BoxDecoration(
            color: _hovered ? MatteColors.panelHover : MatteColors.inset,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(
              color:
                  _hovered ? MatteColors.borderStrong : MatteColors.borderSubtle,
              width: 1,
            ),
          ),
          child: const Row(
            children: [
              Icon(
                Icons.add_rounded,
                size: 16,
                color: MatteColors.textPrimary,
              ),
              SizedBox(width: 8),
              Expanded(
                child: Text(
                  'New Chat',
                  style: TextStyle(
                    color: MatteColors.textPrimary,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              Text(
                '⌘N',
                style: TextStyle(
                  color: MatteColors.textMuted,
                  fontSize: 11,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _SidebarNavTile extends StatefulWidget {
  final IconData icon;
  final String label;
  final bool isSelected;
  final VoidCallback onTap;
  final Widget? trailing;

  const _SidebarNavTile({
    required this.icon,
    required this.label,
    required this.isSelected,
    required this.onTap,
    this.trailing,
  });

  @override
  State<_SidebarNavTile> createState() => _SidebarNavTileState();
}

class _SidebarNavTileState extends State<_SidebarNavTile> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final bgColor = widget.isSelected
        ? MatteColors.panelHover
        : (_hovered ? MatteColors.panelHover.withValues(alpha: 0.6) : Colors.transparent);

    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onTap,
        child: Container(
          height: 35,
          padding: const EdgeInsets.symmetric(horizontal: 10),
          decoration: BoxDecoration(
            color: bgColor,
            borderRadius: BorderRadius.circular(6),
            border: Border.all(
              color: widget.isSelected
                  ? MatteColors.borderStrong
                  : Colors.transparent,
              width: 1,
            ),
          ),
          child: Row(
            children: [
              Icon(
                widget.icon,
                size: 16,
                color: widget.isSelected
                    ? MatteColors.textPrimary
                    : MatteColors.textSecondary,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  widget.label,
                  style: TextStyle(
                    color: widget.isSelected
                        ? MatteColors.textPrimary
                        : MatteColors.textSecondary,
                    fontSize: 13,
                    fontWeight:
                        widget.isSelected ? FontWeight.w500 : FontWeight.w400,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (widget.trailing != null) widget.trailing!,
            ],
          ),
        ),
      ),
    );
  }
}

class _ConnectorStatusBadge extends StatelessWidget {
  final ConnectorStatus status;

  const _ConnectorStatusBadge({required this.status});

  @override
  Widget build(BuildContext context) {
    Color dotColor;
    switch (status) {
      case ConnectorStatus.connected:
        dotColor = MatteColors.statusConnected;
        break;
      case ConnectorStatus.needsLogin:
        dotColor = MatteColors.statusWarning;
        break;
      default:
        dotColor = MatteColors.statusMuted;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: MatteColors.inset,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: MatteColors.borderSubtle, width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 6,
            height: 6,
            decoration: BoxDecoration(
              color: dotColor,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 5),
          Text(
            status.label,
            style: const TextStyle(
              color: MatteColors.textSecondary,
              fontSize: 10.5,
            ),
          ),
        ],
      ),
    );
  }
}

class _GraphCountBadge extends StatelessWidget {
  final int nodeCount;

  const _GraphCountBadge({required this.nodeCount});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: MatteColors.inset,
        borderRadius: BorderRadius.circular(4),
        border: Border.all(color: MatteColors.borderSubtle, width: 1),
      ),
      child: Text(
        nodeCount > 0 ? '$nodeCount nodes' : '3D / 2D',
        style: const TextStyle(
          color: MatteColors.textMuted,
          fontSize: 10.5,
        ),
      ),
    );
  }
}

class _RecentChatItem extends StatefulWidget {
  final ChatSession session;
  final bool isSelected;
  final VoidCallback onSelect;
  final ValueChanged<String> onRename;
  final VoidCallback onDelete;

  const _RecentChatItem({
    required this.session,
    required this.isSelected,
    required this.onSelect,
    required this.onRename,
    required this.onDelete,
  });

  @override
  State<_RecentChatItem> createState() => _RecentChatItemState();
}

class _RecentChatItemState extends State<_RecentChatItem> {
  bool _hovered = false;

  Future<void> _showRenameDialog(BuildContext context) async {
    final controller = TextEditingController(text: widget.session.title);
    final result = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text(
          'Rename Conversation',
          style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
        ),
        content: TextField(
          controller: controller,
          autofocus: true,
          style: const TextStyle(color: MatteColors.textPrimary, fontSize: 13.5),
          decoration: const InputDecoration(
            hintText: 'Enter chat title...',
          ),
          onSubmitted: (val) => Navigator.of(ctx).pop(val),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text(
              'Cancel',
              style: TextStyle(color: MatteColors.textSecondary),
            ),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(controller.text),
            child: const Text(
              'Save',
              style: TextStyle(color: MatteColors.textPrimary),
            ),
          ),
        ],
      ),
    );
    if (result != null && result.trim().isNotEmpty) {
      widget.onRename(result.trim());
    }
  }

  @override
  Widget build(BuildContext context) {
    final showActions = _hovered || widget.isSelected;
    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onSelect,
        child: Container(
          height: 34,
          margin: const EdgeInsets.only(bottom: 2),
          padding: const EdgeInsets.only(left: 10, right: 6),
          decoration: BoxDecoration(
            color: widget.isSelected
                ? MatteColors.panelHover
                : (_hovered
                    ? MatteColors.panelHover.withValues(alpha: 0.5)
                    : Colors.transparent),
            borderRadius: BorderRadius.circular(6),
            border: Border.all(
              color: widget.isSelected
                  ? MatteColors.borderSubtle
                  : Colors.transparent,
              width: 1,
            ),
          ),
          child: Row(
            children: [
              Icon(
                Icons.notes_rounded,
                size: 14,
                color: widget.isSelected
                    ? MatteColors.textPrimary
                    : MatteColors.textMuted,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  widget.session.title,
                  style: TextStyle(
                    color: widget.isSelected
                        ? MatteColors.textPrimary
                        : MatteColors.textSecondary,
                    fontSize: 12.5,
                    fontWeight:
                        widget.isSelected ? FontWeight.w500 : FontWeight.w400,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              if (showActions) ...[
                InkWell(
                  onTap: () => _showRenameDialog(context),
                  borderRadius: BorderRadius.circular(4),
                  child: const Padding(
                    padding: EdgeInsets.all(4),
                    child: Icon(
                      Icons.edit_outlined,
                      size: 13,
                      color: MatteColors.textMuted,
                    ),
                  ),
                ),
                InkWell(
                  onTap: widget.onDelete,
                  borderRadius: BorderRadius.circular(4),
                  child: const Padding(
                    padding: EdgeInsets.all(4),
                    child: Icon(
                      Icons.delete_outline_rounded,
                      size: 13,
                      color: MatteColors.textMuted,
                    ),
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
