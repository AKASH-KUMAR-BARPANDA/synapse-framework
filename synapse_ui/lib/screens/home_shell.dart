import 'package:flutter/material.dart';

import '../services/api_service.dart';
import '../theme/matte_theme.dart';
import '../widgets/sidebar.dart';
import 'chat_screen.dart';
import 'connectors_screen.dart';
import 'graph_screen.dart';
import 'settings_screen.dart';

/// Responsive application shell adapting smoothly across Desktop, Tablet, and Mobile.
/// - Width > 768px: Collapsible Left Matte Sidebar + Main Content Area (with optional Split Graph view)
/// - Width <= 768px: Clean full-screen interface with Top Drawer navigation
class HomeShell extends StatefulWidget {
  final ApiService apiService;

  const HomeShell({
    super.key,
    required this.apiService,
  });

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  final GlobalKey<ScaffoldState> _scaffoldKey = GlobalKey<ScaffoldState>();

  SynapseDestination _activeDestination = SynapseDestination.chat;
  bool _isSidebarCollapsed = false;
  bool _isSplitGraphActive = false;

  void _handleSelectDestination(SynapseDestination dest) {
    setState(() {
      _activeDestination = dest;
      if (dest == SynapseDestination.graph) {
        _isSplitGraphActive = false;
      }
    });
    if (_scaffoldKey.currentState?.isDrawerOpen ?? false) {
      Navigator.of(context).pop();
    }
  }

  void _handleNewChat() {
    widget.apiService.createNewSession();
    setState(() {
      _activeDestination = SynapseDestination.chat;
    });
    if (_scaffoldKey.currentState?.isDrawerOpen ?? false) {
      Navigator.of(context).pop();
    }
  }

  void _handleSelectSession(String sessionId) {
    widget.apiService.selectSession(sessionId);
    setState(() {
      _activeDestination = SynapseDestination.chat;
    });
    if (_scaffoldKey.currentState?.isDrawerOpen ?? false) {
      Navigator.of(context).pop();
    }
  }

  String _titleForDestination() {
    switch (_activeDestination) {
      case SynapseDestination.chat:
        return widget.apiService.activeSession?.title ?? 'New Chat';
      case SynapseDestination.connectors:
        return 'Connectors';
      case SynapseDestination.graph:
        return 'Knowledge Graph';
      case SynapseDestination.settings:
        return 'Settings';
    }
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: widget.apiService,
      builder: (context, _) {
        final isMobile = MatteBreakpoints.isMobile(context);

        return Scaffold(
          key: _scaffoldKey,
          backgroundColor: MatteColors.canvas,
          drawer: isMobile
              ? Drawer(
                  width: MatteBreakpoints.sidebarExpandedWidth + 20,
                  backgroundColor: MatteColors.panel,
                  child: MatteSidebar(
                    apiService: widget.apiService,
                    activeDestination: _activeDestination,
                    onSelectDestination: _handleSelectDestination,
                    onNewChat: _handleNewChat,
                    onSelectSession: _handleSelectSession,
                    onToggleCollapse: () => Navigator.of(context).pop(),
                    isDrawer: true,
                  ),
                )
              : null,
          body: SafeArea(
            child: Row(
              children: [
                // Desktop & Tablet Collapsible Matte Sidebar
                if (!isMobile && !_isSidebarCollapsed)
                  MatteSidebar(
                    apiService: widget.apiService,
                    activeDestination: _activeDestination,
                    onSelectDestination: _handleSelectDestination,
                    onNewChat: _handleNewChat,
                    onSelectSession: _handleSelectSession,
                    onToggleCollapse: () =>
                        setState(() => _isSidebarCollapsed = true),
                  ),

                // Main Content Area (Right)
                Expanded(
                  child: Column(
                    children: [
                      _buildTopHeaderBar(context, isMobile),
                      if (!(isMobile &&
                          _activeDestination == SynapseDestination.settings))
                        const Divider(
                          height: 1,
                          color: MatteColors.borderSubtle,
                        ),
                      Expanded(
                        child: _buildBodyContent(context, isMobile),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildTopHeaderBar(BuildContext context, bool isMobile) {
    final health = widget.apiService.healthStatus;
    final isSettings = _activeDestination == SynapseDestination.settings;
    final isChat = _activeDestination == SynapseDestination.chat;

    if (isMobile && !isChat) {
      // Clean centered header bar (Claude style) for Settings, Connectors, and Graph on mobile
      return Container(
        height: 52,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        color: MatteColors.canvas,
        child: Row(
          children: [
            IconButton(
              onPressed: () => _scaffoldKey.currentState?.openDrawer(),
              icon: const Icon(
                Icons.notes_rounded,
                size: 22,
                color: MatteColors.textSecondary,
              ),
              tooltip: 'Open Navigation Drawer',
              visualDensity: VisualDensity.compact,
            ),
            Expanded(
              child: Text(
                _titleForDestination(),
                textAlign: TextAlign.center,
                style: const TextStyle(
                  color: MatteColors.textPrimary,
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                  letterSpacing: -0.2,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            IconButton(
              onPressed: () => widget.apiService.checkHealth(),
              icon: Icon(
                Icons.info_outline_rounded,
                size: 21,
                color: health.isOnline
                    ? MatteColors.textSecondary
                    : MatteColors.statusWarning,
              ),
              tooltip: 'Verify System Status',
              visualDensity: VisualDensity.compact,
            ),
          ],
        ),
      );
    }

    return Container(
      height: 48,
      padding: const EdgeInsets.symmetric(horizontal: 12),
      color: MatteColors.canvas,
      child: Row(
        children: [
          // Hamburger Drawer Button (Mobile) or Expand Sidebar Button (Desktop)
          if (isMobile)
            IconButton(
              onPressed: () => _scaffoldKey.currentState?.openDrawer(),
              icon: const Icon(
                Icons.notes_rounded,
                size: 21,
                color: MatteColors.textPrimary,
              ),
              tooltip: 'Open Navigation Drawer',
              visualDensity: VisualDensity.compact,
            )
          else if (_isSidebarCollapsed) ...[
            IconButton(
              onPressed: () => setState(() => _isSidebarCollapsed = false),
              icon: const Icon(
                Icons.view_sidebar_outlined,
                size: 18,
                color: MatteColors.textSecondary,
              ),
              tooltip: 'Expand Sidebar',
              visualDensity: VisualDensity.compact,
            ),
            const SizedBox(width: 4),
            IconButton(
              onPressed: _handleNewChat,
              icon: const Icon(
                Icons.add_comment_outlined,
                size: 17,
                color: MatteColors.textSecondary,
              ),
              tooltip: 'New Chat',
              visualDensity: VisualDensity.compact,
            ),
            const SizedBox(width: 8),
          ],

          // Active View / Chat Title
          Expanded(
            child: Row(
              children: [
                Flexible(
                  child: Text(
                    _titleForDestination(),
                    style: const TextStyle(
                      color: MatteColors.textPrimary,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 7,
                    vertical: 2.5,
                  ),
                  decoration: BoxDecoration(
                    color: MatteColors.panel,
                    borderRadius: BorderRadius.circular(5),
                    border: Border.all(
                      color: MatteColors.borderSubtle,
                      width: 1,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 5,
                        height: 5,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: health.isOnline
                              ? MatteColors.statusConnected
                              : MatteColors.statusWarning,
                        ),
                      ),
                      const SizedBox(width: 5),
                      Text(
                        widget.apiService.activeEngineBadge,
                        style: const TextStyle(
                          color: MatteColors.textMuted,
                          fontSize: 10.5,
                          fontFamily: 'monospace',
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // Desktop Split Knowledge Graph Toggle (when in Chat view)
          if (!isMobile && isChat)
            Padding(
              padding: const EdgeInsets.only(right: 6),
              child: InkWell(
                onTap: () =>
                    setState(() => _isSplitGraphActive = !_isSplitGraphActive),
                borderRadius: BorderRadius.circular(5),
                child: Container(
                  height: 28,
                  padding: const EdgeInsets.symmetric(horizontal: 9),
                  decoration: BoxDecoration(
                    color: _isSplitGraphActive
                        ? MatteColors.panelHover
                        : MatteColors.panel,
                    borderRadius: BorderRadius.circular(5),
                    border: Border.all(
                      color: _isSplitGraphActive
                          ? MatteColors.borderStrong
                          : MatteColors.borderSubtle,
                      width: 1,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.grain_rounded,
                        size: 14,
                        color: _isSplitGraphActive
                            ? MatteColors.nodePerson
                            : MatteColors.textSecondary,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        _isSplitGraphActive ? 'Close Split Graph' : 'Split Graph',
                        style: TextStyle(
                          color: _isSplitGraphActive
                              ? MatteColors.textPrimary
                              : MatteColors.textSecondary,
                          fontSize: 11.5,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),

          // Mobile Quick "+ New Chat" Action
          if (isMobile)
            IconButton(
              onPressed: _handleNewChat,
              icon: const Icon(
                Icons.add_rounded,
                size: 20,
                color: MatteColors.textPrimary,
              ),
              tooltip: 'New Chat',
              visualDensity: VisualDensity.compact,
            ),

          // Quick Settings Trigger (hidden if already on Settings screen)
          if (!isSettings)
            IconButton(
              onPressed: () =>
                  _handleSelectDestination(SynapseDestination.settings),
              icon: const Icon(
                Icons.tune_rounded,
                size: 17,
                color: MatteColors.textSecondary,
              ),
              tooltip: 'Settings',
              visualDensity: VisualDensity.compact,
            ),
        ],
      ),
    );
  }

  Widget _buildBodyContent(BuildContext context, bool isMobile) {
    switch (_activeDestination) {
      case SynapseDestination.chat:
        final chatView = ChatScreen(
          apiService: widget.apiService,
          onOpenConnectors: () =>
              _handleSelectDestination(SynapseDestination.connectors),
          onOpenGraph: () =>
              _handleSelectDestination(SynapseDestination.graph),
        );

        if (!isMobile && _isSplitGraphActive) {
          return Row(
            children: [
              Expanded(flex: 11, child: chatView),
              const VerticalDivider(
                width: 1,
                color: MatteColors.borderSubtle,
              ),
              Expanded(
                flex: 9,
                child: GraphScreen(apiService: widget.apiService),
              ),
            ],
          );
        }
        return chatView;

      case SynapseDestination.connectors:
        return ConnectorsScreen(
          apiService: widget.apiService,
          onOpenGraph: () =>
              _handleSelectDestination(SynapseDestination.graph),
        );

      case SynapseDestination.graph:
        return GraphScreen(apiService: widget.apiService);

      case SynapseDestination.settings:
        return SettingsScreen(
          apiService: widget.apiService,
          onOpenConnectors: () =>
              _handleSelectDestination(SynapseDestination.connectors),
        );
    }
  }
}
