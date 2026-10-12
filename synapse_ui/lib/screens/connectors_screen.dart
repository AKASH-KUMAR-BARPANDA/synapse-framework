import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../models/connector.dart';
import '../services/api_service.dart';
import '../theme/matte_theme.dart';

/// Extensible MCP & External Data Connectors management screen (`/connectors`).
class ConnectorsScreen extends StatefulWidget {
  final ApiService apiService;
  final VoidCallback? onOpenGraph;

  const ConnectorsScreen({
    super.key,
    required this.apiService,
    this.onOpenGraph,
  });

  @override
  State<ConnectorsScreen> createState() => _ConnectorsScreenState();
}

class _ConnectorsScreenState extends State<ConnectorsScreen> {
  Timer? _syncPollTimer;
  bool _isUploading = false;
  bool _isLoggingIn = false;
  bool _isDisconnecting = false;
  bool _isTriggeringSync = false;
  String? _feedbackBannerMessage;
  bool _feedbackIsError = false;

  // Gmail Sync Parameters
  final TextEditingController _queryController =
      TextEditingController(text: 'label:INBOX');
  int _maxResults = 5;
  bool _extractGraph = true;

  @override
  void initState() {
    super.initState();
    _refreshAll();
  }

  @override
  void dispose() {
    _syncPollTimer?.cancel();
    _queryController.dispose();
    super.dispose();
  }

  Future<void> _refreshAll() async {
    await widget.apiService.fetchAuthStatus();
    final syncState = await widget.apiService.fetchSyncStatus();
    if (syncState.isSyncing) {
      _startPollingSyncStatus();
    }
  }

  void _startPollingSyncStatus() {
    _syncPollTimer?.cancel();
    _syncPollTimer = Timer.periodic(const Duration(milliseconds: 1200), (timer) async {
      if (!mounted) {
        timer.cancel();
        return;
      }
      final state = await widget.apiService.fetchSyncStatus();
      if (!state.isSyncing) {
        timer.cancel();
        // Refresh graph stats once sync finishes
        try {
          await widget.apiService.fetchGraphData();
        } catch (_) {}
      }
    });
  }

  void _setFeedback(String message, {bool isError = false}) {
    if (!mounted) return;
    setState(() {
      _feedbackBannerMessage = message;
      _feedbackIsError = isError;
    });
  }

  Future<void> _pickAndUploadCredentials() async {
    setState(() {
      _isUploading = true;
      _feedbackBannerMessage = null;
    });

    try {
      final files = await FilePicker.pickFiles(
        type: FileType.custom,
        allowedExtensions: ['json'],
        dialogTitle: 'Select Google OAuth credentials.json',
      );

      if (files.isEmpty) {
        setState(() => _isUploading = false);
        return;
      }

      final file = files.first;
      final fileBytes = await file.readAsBytes();
      await widget.apiService.uploadGmailCredentials(
        filePath: file.path,
        bytes: fileBytes,
        fileName: file.name.isNotEmpty ? file.name : 'credentials.json',
      );

      _setFeedback(
        'Uploaded credentials.json successfully. You can now click "Connect Account".',
      );
    } catch (e) {
      _setFeedback('Upload failed: $e', isError: true);
    } finally {
      if (mounted) {
        setState(() => _isUploading = false);
      }
    }
  }

  Future<void> _showPasteCredentialsModal() async {
    final controller = TextEditingController();
    final pastedJson = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text(
          'Paste Google OAuth credentials.json',
          style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
        ),
        content: SizedBox(
          width: 480,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'Paste the contents of your Google Cloud OAuth 2.0 Client ID JSON file ("installed" or "web"):',
                style: TextStyle(
                  color: MatteColors.textSecondary,
                  fontSize: 12.5,
                ),
              ),
              const SizedBox(height: 10),
              TextField(
                controller: controller,
                maxLines: 7,
                style: const TextStyle(
                  color: MatteColors.textPrimary,
                  fontFamily: 'monospace',
                  fontSize: 12,
                ),
                decoration: const InputDecoration(
                  hintText: '{"installed":{"client_id":"...","project_id":"..."}}',
                ),
              ),
            ],
          ),
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
              'Upload JSON',
              style: TextStyle(color: MatteColors.textPrimary),
            ),
          ),
        ],
      ),
    );

    if (pastedJson == null || pastedJson.trim().isEmpty) return;

    setState(() {
      _isUploading = true;
      _feedbackBannerMessage = null;
    });
    try {
      final bytes = Uint8List.fromList(utf8.encode(pastedJson.trim()));
      await widget.apiService.uploadGmailCredentials(
        bytes: bytes,
        fileName: 'credentials.json',
      );
      _setFeedback(
        'Saved credentials.json successfully. Ready to authenticate.',
      );
    } catch (e) {
      _setFeedback('Invalid credentials JSON: $e', isError: true);
    } finally {
      if (mounted) {
        setState(() => _isUploading = false);
      }
    }
  }

  Future<void> _handleGmailLogin() async {
    setState(() {
      _isLoggingIn = true;
      _feedbackBannerMessage = null;
    });
    try {
      await widget.apiService.loginGmail();
      _setFeedback('Gmail account connected via OAuth 2.0.');
    } catch (e) {
      _setFeedback('OAuth login failed: $e', isError: true);
    } finally {
      if (mounted) {
        setState(() => _isLoggingIn = false);
      }
    }
  }

  Future<void> _handleGmailDisconnect() async {
    setState(() {
      _isDisconnecting = true;
      _feedbackBannerMessage = null;
    });
    try {
      await widget.apiService.disconnectGmail();
      _setFeedback('Gmail token removed and account disconnected.');
    } catch (e) {
      _setFeedback('Disconnect failed: $e', isError: true);
    } finally {
      if (mounted) {
        setState(() => _isDisconnecting = false);
      }
    }
  }

  Future<void> _handleSyncNow() async {
    setState(() {
      _isTriggeringSync = true;
      _feedbackBannerMessage = null;
    });
    try {
      final query = _queryController.text.trim().isEmpty
          ? 'label:INBOX'
          : _queryController.text.trim();
      final res = await widget.apiService.triggerGmailSync(
        query: query,
        maxResults: _maxResults,
        extractGraph: _extractGraph,
      );
      _setFeedback(
        (res['message'] ?? 'Background sync initiated.').toString(),
      );
      _startPollingSyncStatus();
    } catch (e) {
      _setFeedback('Failed to trigger Gmail sync: $e', isError: true);
    } finally {
      if (mounted) {
        setState(() => _isTriggeringSync = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isMobile = MatteBreakpoints.isMobile(context);
    final connectors = widget.apiService.connectors;
    final syncState = widget.apiService.syncState;

    return Container(
      color: MatteColors.canvas,
      child: SingleChildScrollView(
        padding: EdgeInsets.symmetric(
          horizontal: isMobile ? 16 : 32,
          vertical: 24,
        ),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 880),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Header Row
                Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Data Connectors & MCP Integrations',
                            style: TextStyle(
                              color: MatteColors.textPrimary,
                              fontSize: 19,
                              fontWeight: FontWeight.w600,
                              letterSpacing: -0.3,
                            ),
                          ),
                          const SizedBox(height: 4),
                          const Text(
                            'Connect personal data sources via Model Context Protocol (stdio) to populate your local ChromaDB vector index and NetworkX knowledge graph.',
                            style: TextStyle(
                              color: MatteColors.textSecondary,
                              fontSize: 13,
                              height: 1.4,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 12),
                    _MatteActionButton(
                      label: 'Refresh',
                      icon: Icons.refresh_rounded,
                      onPressed: _refreshAll,
                    ),
                  ],
                ),

                const SizedBox(height: 18),

                // Optional Feedback Banner
                if (_feedbackBannerMessage != null) ...[
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 14,
                      vertical: 10,
                    ),
                    margin: const EdgeInsets.only(bottom: 16),
                    decoration: BoxDecoration(
                      color: MatteColors.panel,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(
                        color: _feedbackIsError
                            ? MatteColors.statusDanger
                            : MatteColors.nodeProject,
                        width: 1,
                      ),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          _feedbackIsError
                              ? Icons.error_outline_rounded
                              : Icons.check_circle_outline_rounded,
                          size: 16,
                          color: _feedbackIsError
                              ? MatteColors.statusDanger
                              : MatteColors.nodeProject,
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            _feedbackBannerMessage!,
                            style: const TextStyle(
                              color: MatteColors.textPrimary,
                              fontSize: 12.5,
                            ),
                          ),
                        ),
                        InkWell(
                          onTap: () =>
                              setState(() => _feedbackBannerMessage = null),
                          child: const Icon(
                            Icons.close_rounded,
                            size: 15,
                            color: MatteColors.textMuted,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],

                // Live Background Sync Progress Card
                if (syncState.isSyncing ||
                    syncState.progress.isNotEmpty ||
                    syncState.hasError)
                  _SyncProgressBanner(
                    syncState: syncState,
                  ),

                // Active Connector: Gmail MCP
                ...connectors.where((c) => !c.isPlaceholder).map(
                      (connector) => _buildActiveGmailCard(
                        context,
                        connector,
                        syncState,
                        isMobile,
                      ),
                    ),

                const SizedBox(height: 22),

                // Upcoming / Extensible Connectors Header
                const Text(
                  'EXTENSIBLE MCP CONNECTORS (ROADMAP)',
                  style: TextStyle(
                    color: MatteColors.textMuted,
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.7,
                  ),
                ),
                const SizedBox(height: 10),

                // Placeholder Connectors Grid
                LayoutBuilder(
                  builder: (context, constraints) {
                    final columns = constraints.maxWidth > 620 ? 2 : 1;
                    final placeholders =
                        connectors.where((c) => c.isPlaceholder).toList();
                    return GridView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: placeholders.length,
                      gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: columns,
                        crossAxisSpacing: 14,
                        mainAxisSpacing: 14,
                        mainAxisExtent: 195,
                      ),
                      itemBuilder: (context, index) {
                        return _PlaceholderConnectorCard(
                          connector: placeholders[index],
                        );
                      },
                    );
                  },
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildActiveGmailCard(
    BuildContext context,
    ConnectorModel gmail,
    SyncStateModel syncState,
    bool isMobile,
  ) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: MatteTheme.panelDecoration(borderRadius: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Top Title + Status Chip
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 38,
                height: 38,
                decoration: BoxDecoration(
                  color: MatteColors.inset,
                  borderRadius: BorderRadius.circular(7),
                  border: Border.all(
                    color: MatteColors.borderSubtle,
                    width: 1,
                  ),
                ),
                child: const Icon(
                  Icons.mail_outline_rounded,
                  size: 19,
                  color: MatteColors.nodeEmail,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Wrap(
                      spacing: 8,
                      runSpacing: 6,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        Text(
                          gmail.name,
                          style: const TextStyle(
                            color: MatteColors.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 7,
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
                            gmail.protocolBadge,
                            style: const TextStyle(
                              color: MatteColors.textMuted,
                              fontSize: 11,
                              fontFamily: 'monospace',
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 5),
                    Text(
                      gmail.description,
                      style: const TextStyle(
                        color: MatteColors.textSecondary,
                        fontSize: 13,
                        height: 1.45,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              _StatusChip(status: gmail.status),
            ],
          ),

          const SizedBox(height: 14),

          // Capabilities Chips
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: gmail.capabilities
                .map(
                  (cap) => Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 3.5,
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
                      cap,
                      style: const TextStyle(
                        color: MatteColors.textSecondary,
                        fontSize: 11,
                      ),
                    ),
                  ),
                )
                .toList(),
          ),

          const SizedBox(height: 16),
          const Divider(height: 1, color: MatteColors.borderSubtle),
          const SizedBox(height: 16),

          // State-Driven Action Zone
          if (gmail.status == ConnectorStatus.unconfigured)
            _buildUnconfiguredUploadZone()
          else if (gmail.status == ConnectorStatus.needsLogin)
            _buildNeedsLoginZone()
          else if (gmail.status == ConnectorStatus.connected)
            _buildConnectedSyncZone(syncState, isMobile),
        ],
      ),
    );
  }

  /// State 1: Unconfigured (`credentials.json` missing)
  Widget _buildUnconfiguredUploadZone() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: MatteTheme.insetDecoration(borderRadius: 6),
      child: Column(
        children: [
          const Icon(
            Icons.upload_file_outlined,
            size: 26,
            color: MatteColors.textSecondary,
          ),
          const SizedBox(height: 8),
          const Text(
            'Upload Google OAuth Client Secrets (credentials.json)',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: MatteColors.textPrimary,
              fontSize: 13.5,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            'Download your Desktop/Web OAuth 2.0 Client JSON from Google Cloud Console and upload it to `connectors/credentials.json`.',
            textAlign: TextAlign.center,
            style: TextStyle(
              color: MatteColors.textMuted,
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 14),
          Wrap(
            spacing: 10,
            runSpacing: 8,
            alignment: WrapAlignment.center,
            children: [
              _MatteActionButton(
                label: _isUploading
                    ? 'Uploading...'
                    : 'Select credentials.json',
                icon: Icons.folder_open_rounded,
                isPrimary: true,
                isLoading: _isUploading,
                onPressed: _isUploading ? null : _pickAndUploadCredentials,
              ),
              _MatteActionButton(
                label: 'Paste JSON Content',
                icon: Icons.content_paste_rounded,
                onPressed: _isUploading ? null : _showPasteCredentialsModal,
              ),
            ],
          ),
        ],
      ),
    );
  }

  /// State 2: Needs Login (`credentials.json` present, `token.json` missing)
  Widget _buildNeedsLoginZone() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: MatteTheme.insetDecoration(borderRadius: 6),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Icon(
                Icons.vpn_key_outlined,
                size: 18,
                color: MatteColors.statusWarning,
              ),
              SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'OAuth Credentials Loaded · Authorization Required',
                      style: TextStyle(
                        color: MatteColors.textPrimary,
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    SizedBox(height: 2),
                    Text(
                      'Click "Connect Account" to complete the local Google OAuth 2.0 read-only flow.',
                      style: TextStyle(
                        color: MatteColors.textMuted,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              _MatteActionButton(
                label: 'Replace JSON',
                icon: Icons.upload_file_outlined,
                onPressed: _isUploading ? null : _pickAndUploadCredentials,
              ),
              _MatteActionButton(
                label: _isLoggingIn ? 'Authorizing...' : 'Connect Account',
                icon: Icons.login_rounded,
                isPrimary: true,
                isLoading: _isLoggingIn,
                onPressed: _isLoggingIn ? null : _handleGmailLogin,
              ),
            ],
          ),
        ],
      ),
    );
  }

  /// State 3: Connected (`token.json` active — Sync Now & Disconnect)
  Widget _buildConnectedSyncZone(SyncStateModel syncState, bool isMobile) {
    final busy = syncState.isSyncing || _isTriggeringSync;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Sync Configuration Bar
        Container(
          padding: const EdgeInsets.all(12),
          decoration: MatteTheme.insetDecoration(borderRadius: 6),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'GMAIL MCP SYNC PARAMETERS',
                style: TextStyle(
                  color: MatteColors.textMuted,
                  fontSize: 10.5,
                  fontWeight: FontWeight.w600,
                  letterSpacing: 0.6,
                ),
              ),
              const SizedBox(height: 10),
              Wrap(
                spacing: 12,
                runSpacing: 10,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  // Query Input
                  SizedBox(
                    width: isMobile ? double.infinity : 260,
                    child: TextField(
                      controller: _queryController,
                      style: const TextStyle(
                        color: MatteColors.textPrimary,
                        fontSize: 12.5,
                        fontFamily: 'monospace',
                      ),
                      decoration: const InputDecoration(
                        labelText: 'Gmail Search Query',
                        labelStyle: TextStyle(
                          color: MatteColors.textMuted,
                          fontSize: 11.5,
                        ),
                        hintText: 'label:INBOX',
                      ),
                    ),
                  ),

                  // Max Results Selector
                  Container(
                    height: 38,
                    padding: const EdgeInsets.symmetric(horizontal: 10),
                    decoration: BoxDecoration(
                      color: MatteColors.panel,
                      borderRadius: BorderRadius.circular(6),
                      border: Border.all(
                        color: MatteColors.borderSubtle,
                        width: 1,
                      ),
                    ),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<int>(
                        value: _maxResults,
                        dropdownColor: MatteColors.panel,
                        style: const TextStyle(
                          color: MatteColors.textPrimary,
                          fontSize: 12.5,
                        ),
                        items: const [
                          DropdownMenuItem(value: 5, child: Text('5 emails')),
                          DropdownMenuItem(value: 10, child: Text('10 emails')),
                          DropdownMenuItem(value: 20, child: Text('20 emails')),
                          DropdownMenuItem(value: 50, child: Text('50 emails')),
                        ],
                        onChanged: (val) {
                          if (val != null) setState(() => _maxResults = val);
                        },
                      ),
                    ),
                  ),

                  // Extract Graph Triples Toggle
                  InkWell(
                    onTap: () =>
                        setState(() => _extractGraph = !_extractGraph),
                    borderRadius: BorderRadius.circular(6),
                    child: Container(
                      height: 38,
                      padding: const EdgeInsets.symmetric(horizontal: 10),
                      decoration: BoxDecoration(
                        color: MatteColors.panel,
                        borderRadius: BorderRadius.circular(6),
                        border: Border.all(
                          color: _extractGraph
                              ? MatteColors.borderStrong
                              : MatteColors.borderSubtle,
                          width: 1,
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            _extractGraph
                                ? Icons.check_box_outlined
                                : Icons.check_box_outline_blank_rounded,
                            size: 16,
                            color: _extractGraph
                                ? MatteColors.nodeProject
                                : MatteColors.textMuted,
                          ),
                          const SizedBox(width: 6),
                          const Text(
                            'Extract Graph Triples (LLM)',
                            style: TextStyle(
                              color: MatteColors.textSecondary,
                              fontSize: 12,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),

        const SizedBox(height: 14),

        // Action Buttons Row: Sync Now + Disconnect
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            _MatteActionButton(
              label: _isDisconnecting ? 'Disconnecting...' : 'Disconnect',
              icon: Icons.link_off_rounded,
              isDanger: true,
              isLoading: _isDisconnecting,
              onPressed: _isDisconnecting ? null : _handleGmailDisconnect,
            ),
            _MatteActionButton(
              label: busy ? 'Syncing Inbox...' : 'Sync Now',
              icon: Icons.sync_rounded,
              isPrimary: true,
              isLoading: busy,
              onPressed: busy ? null : _handleSyncNow,
            ),
          ],
        ),
      ],
    );
  }
}

class _SyncProgressBanner extends StatelessWidget {
  final SyncStateModel syncState;

  const _SyncProgressBanner({
    required this.syncState,
  });

  @override
  Widget build(BuildContext context) {
    final borderColor = syncState.hasError
        ? MatteColors.statusDanger
        : (syncState.isSyncing
            ? MatteColors.nodeEmail
            : MatteColors.borderSubtle);

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: MatteColors.panel,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: borderColor, width: 1),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              if (syncState.isSyncing)
                const SizedBox(
                  width: 14,
                  height: 14,
                  child: CircularProgressIndicator(
                    strokeWidth: 1.8,
                    color: MatteColors.nodeEmail,
                  ),
                )
              else
                Icon(
                  syncState.hasError
                      ? Icons.warning_amber_rounded
                      : Icons.check_circle_outline_rounded,
                  size: 15,
                  color: syncState.hasError
                      ? MatteColors.statusDanger
                      : MatteColors.nodeProject,
                ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  syncState.progress.isNotEmpty
                      ? syncState.progress
                      : (syncState.isSyncing
                          ? 'Synchronizing...'
                          : 'Sync Idle'),
                  style: const TextStyle(
                    color: MatteColors.textPrimary,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                decoration: BoxDecoration(
                  color: MatteColors.inset,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(color: MatteColors.borderSubtle, width: 1),
                ),
                child: Text(
                  '${syncState.itemsSynced} items indexed',
                  style: const TextStyle(
                    color: MatteColors.textSecondary,
                    fontSize: 11,
                  ),
                ),
              ),
            ],
          ),
          if (syncState.hasError) ...[
            const SizedBox(height: 6),
            Text(
              'Error: ${syncState.error}',
              style: const TextStyle(
                color: MatteColors.statusDanger,
                fontSize: 12,
              ),
            ),
          ],
          if (syncState.lastSyncedAt != null && !syncState.isSyncing) ...[
            const SizedBox(height: 6),
            Text(
              'Last synced: ${syncState.lastSyncedAt}',
              style: const TextStyle(
                color: MatteColors.textMuted,
                fontSize: 11,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _PlaceholderConnectorCard extends StatelessWidget {
  final ConnectorModel connector;

  const _PlaceholderConnectorCard({required this.connector});

  @override
  Widget build(BuildContext context) {
    final IconData iconData = connector.id == 'notion'
        ? Icons.article_outlined
        : Icons.calendar_month_outlined;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: MatteTheme.panelDecoration(borderRadius: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 32,
                height: 32,
                decoration: BoxDecoration(
                  color: MatteColors.inset,
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(color: MatteColors.borderSubtle, width: 1),
                ),
                child: Icon(
                  iconData,
                  size: 16,
                  color: MatteColors.textSecondary,
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      connector.name,
                      style: const TextStyle(
                        color: MatteColors.textPrimary,
                        fontSize: 14,
                        fontWeight: FontWeight.w600,
                      ),
                      overflow: TextOverflow.ellipsis,
                    ),
                    Text(
                      connector.protocolBadge,
                      style: const TextStyle(
                        color: MatteColors.textMuted,
                        fontSize: 11,
                      ),
                    ),
                  ],
                ),
              ),
              _StatusChip(status: connector.status),
            ],
          ),
          const SizedBox(height: 10),
          Expanded(
            child: Text(
              connector.description,
              style: const TextStyle(
                color: MatteColors.textSecondary,
                fontSize: 12,
                height: 1.4,
              ),
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(height: 8),
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: connector.capabilities
                .map(
                  (c) => Container(
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
                      c,
                      style: const TextStyle(
                        color: MatteColors.textMuted,
                        fontSize: 10.5,
                      ),
                    ),
                  ),
                )
                .toList(),
          ),
        ],
      ),
    );
  }
}

class _StatusChip extends StatelessWidget {
  final ConnectorStatus status;

  const _StatusChip({required this.status});

  @override
  Widget build(BuildContext context) {
    Color dotColor;
    switch (status) {
      case ConnectorStatus.connected:
        dotColor = MatteColors.statusConnected;
        break;
      case ConnectorStatus.needsLogin:
      case ConnectorStatus.apiKeySetup:
        dotColor = MatteColors.statusWarning;
        break;
      case ConnectorStatus.unconfigured:
      case ConnectorStatus.comingSoon:
        dotColor = MatteColors.statusMuted;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: MatteColors.inset,
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
              color: dotColor,
              shape: BoxShape.circle,
            ),
          ),
          const SizedBox(width: 6),
          Text(
            status.label,
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

class _MatteActionButton extends StatefulWidget {
  final String label;
  final IconData icon;
  final VoidCallback? onPressed;
  final bool isPrimary;
  final bool isDanger;
  final bool isLoading;

  const _MatteActionButton({
    required this.label,
    required this.icon,
    this.onPressed,
    this.isPrimary = false,
    this.isDanger = false,
    this.isLoading = false,
  });

  @override
  State<_MatteActionButton> createState() => _MatteActionButtonState();
}

class _MatteActionButtonState extends State<_MatteActionButton> {
  bool _hovered = false;

  @override
  Widget build(BuildContext context) {
    final disabled = widget.onPressed == null;
    Color bg;
    if (widget.isPrimary) {
      bg = _hovered && !disabled
          ? MatteColors.textSecondary
          : MatteColors.textPrimary;
    } else {
      bg = _hovered && !disabled ? MatteColors.panelHover : MatteColors.panel;
    }

    final fg = widget.isPrimary
        ? MatteColors.canvas
        : (widget.isDanger
            ? MatteColors.statusDanger
            : MatteColors.textPrimary);

    return MouseRegion(
      onEnter: (_) => setState(() => _hovered = true),
      onExit: (_) => setState(() => _hovered = false),
      child: GestureDetector(
        onTap: widget.onPressed,
        child: Opacity(
          opacity: disabled ? 0.55 : 1.0,
          child: Container(
            height: 34,
            padding: const EdgeInsets.symmetric(horizontal: 12),
            decoration: BoxDecoration(
              color: bg,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(
                color: widget.isPrimary
                    ? MatteColors.textPrimary
                    : (widget.isDanger
                        ? MatteColors.statusDanger.withValues(alpha: 0.5)
                        : MatteColors.borderStrong),
                width: 1,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (widget.isLoading)
                  SizedBox(
                    width: 13,
                    height: 13,
                    child: CircularProgressIndicator(
                      strokeWidth: 1.7,
                      color: fg,
                    ),
                  )
                else
                  Icon(widget.icon, size: 14, color: fg),
                const SizedBox(width: 7),
                Text(
                  widget.label,
                  style: TextStyle(
                    color: fg,
                    fontSize: 12.5,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
