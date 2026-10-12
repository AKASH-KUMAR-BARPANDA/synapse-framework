import 'package:flutter/material.dart';

import '../services/api_service.dart';
import '../theme/matte_theme.dart';

/// Desktop sub-sections inside Settings so every setting item on macOS / Desktop
/// renders a full-width desktop dashboard view (matching the Connectors screen)
/// rather than a mobile bottom sheet.
enum _DesktopSettingsSection {
  overview,
  workspaceProfile,
  languageModel,
  capabilities,
  permissionsPrivacy,
  colorMode,
  graphPalette,
  fontStyle,
}

/// Polished, responsive Settings screen:
/// - On Mobile (`<= 768px`): Uncluttered Claude-inspired grouped cards + bottom sheets.
/// - On Desktop (`> 768px`, macOS): Full-width (`maxWidth: 880`) desktop layout matching
///   `ConnectorsScreen`, with a top section tab bar, 2-column desktop cards, and dedicated
///   desktop views for Workspace Profile, Language Model, Capabilities, Permissions & Privacy,
///   Color Mode, Graph Palette, and Font Style.
class SettingsScreen extends StatefulWidget {
  final ApiService apiService;
  final bool isDialog;
  final VoidCallback? onOpenConnectors;

  const SettingsScreen({
    super.key,
    required this.apiService,
    this.isDialog = false,
    this.onOpenConnectors,
  });

  /// Optional modal helper if ever invoked as a dialog.
  static Future<void> showAsDialog(
    BuildContext context,
    ApiService apiService, {
    VoidCallback? onOpenConnectors,
  }) {
    return showDialog<void>(
      context: context,
      builder: (ctx) => Dialog(
        backgroundColor: MatteColors.canvas,
        insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 24),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: MatteColors.borderSubtle, width: 1),
        ),
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 920, maxHeight: 760),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: SettingsScreen(
              apiService: apiService,
              isDialog: true,
              onOpenConnectors: onOpenConnectors,
            ),
          ),
        ),
      ),
    );
  }

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  bool _isTestingHealth = false;
  String? _toastMessage;
  _DesktopSettingsSection _activeDesktopSection =
      _DesktopSettingsSection.overview;

  String _paletteDisplayName(String id) {
    switch (id) {
      case 'stone':
        return 'Stone (Anthropic)';
      case 'basalt':
        return 'Basalt (Slate)';
      case 'zinc':
      default:
        return 'Zinc (Linear)';
    }
  }

  void _showStatusBanner(String msg) {
    if (!mounted) return;
    setState(() => _toastMessage = msg);
    ScaffoldMessenger.of(context).clearSnackBars();
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        backgroundColor: MatteColors.panelHover,
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 2),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(10),
          side: const BorderSide(color: MatteColors.borderStrong, width: 1),
        ),
        content: Text(
          msg,
          style: const TextStyle(
            color: MatteColors.textPrimary,
            fontSize: 12.5,
          ),
        ),
      ),
    );
    Future.delayed(const Duration(seconds: 3), () {
      if (mounted && _toastMessage == msg) {
        setState(() => _toastMessage = null);
      }
    });
  }

  Future<void> _verifyConnection() async {
    setState(() => _isTestingHealth = true);
    final health = await widget.apiService.checkHealth();
    if (!mounted) return;
    setState(() => _isTestingHealth = false);
    _showStatusBanner(
      health.isOnline
          ? 'Engine verified · Active mode: ${widget.apiService.activeEngineBadge}'
          : 'Local server offline · Using on-device engine',
    );
  }

  /// Routes an action to a full Desktop sub-view on macOS/Desktop or a BottomSheet on Mobile.
  void _openSection(_DesktopSettingsSection section, VoidCallback mobileSheet) {
    final isMobile = MatteBreakpoints.isMobile(context);
    if (isMobile) {
      mobileSheet();
    } else {
      setState(() => _activeDesktopSection = section);
    }
  }

  // ===========================================================================
  // Mobile Bottom Sheets (Used only when width <= 768px)
  // ===========================================================================

  Future<void> _openWorkspaceProfileSheet() async {
    final stats = widget.apiService.graphStats;
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: MatteColors.panel,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        side: BorderSide(color: MatteColors.borderSubtle, width: 1),
      ),
      builder: (ctx) {
        return Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const _SheetHandle(),
              const SizedBox(height: 18),
              const Text(
                'Workspace Profile',
                style: TextStyle(
                  color: MatteColors.textPrimary,
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 6),
              const Text(
                'Your local personal intelligence workspace and indexed memory statistics.',
                style: TextStyle(
                  color: MatteColors.textSecondary,
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: MatteColors.inset,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: MatteColors.borderSubtle, width: 1),
                ),
                child: Column(
                  children: [
                    const _InfoRow(label: 'Owner', value: 'Akash'),
                    const Divider(height: 18, color: MatteColors.borderSubtle),
                    _InfoRow(
                      label: 'Active Engine',
                      value: widget.apiService.activeEngineBadge,
                    ),
                    const Divider(height: 18, color: MatteColors.borderSubtle),
                    _InfoRow(
                      label: 'Knowledge Graph',
                      value:
                          '${stats.totalNodes} nodes · ${stats.totalEdges} relations',
                    ),
                    const Divider(height: 18, color: MatteColors.borderSubtle),
                    _InfoRow(
                      label: 'Indexed Emails',
                      value: '${widget.apiService.syncState.itemsSynced} items',
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              const _ComingSoonFeatureTile(
                icon: Icons.cloud_sync_outlined,
                title: 'Multi-Device Encrypted Sync',
                subtitle: 'End-to-end encrypted graph sync across devices',
              ),
              const SizedBox(height: 8),
              const _ComingSoonFeatureTile(
                icon: Icons.badge_outlined,
                title: 'Custom Persona & System Prompt',
                subtitle: 'Tailor response tone and domain expertise',
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _openModelConfigurationSheet() async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: MatteColors.panel,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        side: BorderSide(color: MatteColors.borderSubtle, width: 1),
      ),
      builder: (ctx) {
        return ListenableBuilder(
          listenable: widget.apiService,
          builder: (ctx, _) {
            return Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const _SheetHandle(),
                    const SizedBox(height: 18),
                    const Text(
                      'Language Model & Engine',
                      style: TextStyle(
                        color: MatteColors.textPrimary,
                        fontSize: 17,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 6),
                    const Text(
                      'Switch between the local Qwen 2.5 neural model for richer reasoning or the built-in Rule-Based Engine for instant 0 MB lookups.',
                      style: TextStyle(
                        color: MatteColors.textSecondary,
                        fontSize: 13,
                        height: 1.38,
                      ),
                    ),
                    const SizedBox(height: 16),
                    _buildLanguageModelCards(isDesktopGrid: false),
                  ],
                ),
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _openCapabilitiesSheet() async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: MatteColors.panel,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        side: BorderSide(color: MatteColors.borderSubtle, width: 1),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setSheetState) {
            final useRag = widget.apiService.defaultUseRag;

            return Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const _SheetHandle(),
                  const SizedBox(height: 18),
                  const Text(
                    'Capabilities',
                    style: TextStyle(
                      color: MatteColors.textPrimary,
                      fontSize: 17,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Manage retrieval-augmented generation and upcoming agentic tools.',
                    style: TextStyle(
                      color: MatteColors.textSecondary,
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 16),
                  Container(
                    decoration: BoxDecoration(
                      color: MatteColors.inset,
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                        color: MatteColors.borderSubtle,
                        width: 1,
                      ),
                    ),
                    child: SwitchListTile(
                      value: useRag,
                      activeThumbColor: MatteColors.textPrimary,
                      activeTrackColor: MatteColors.nodeProject,
                      inactiveThumbColor: MatteColors.textMuted,
                      inactiveTrackColor: MatteColors.panel,
                      title: const Text(
                        'Hybrid RAG Retrieval',
                        style: TextStyle(
                          color: MatteColors.textPrimary,
                          fontSize: 14.5,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      subtitle: const Text(
                        'Query ChromaDB vectors & NetworkX graph relations automatically',
                        style: TextStyle(
                          color: MatteColors.textSecondary,
                          fontSize: 12,
                        ),
                      ),
                      onChanged: (val) async {
                        await widget.apiService
                            .updateSettings(defaultUseRag: val);
                        setSheetState(() {});
                        if (mounted) setState(() {});
                      },
                    ),
                  ),
                  const SizedBox(height: 12),
                  const _ComingSoonFeatureTile(
                    icon: Icons.mic_none_rounded,
                    title: 'Offline Voice & Whisper Dictation',
                    subtitle: 'On-device speech-to-text voice queries',
                  ),
                  const SizedBox(height: 8),
                  const _ComingSoonFeatureTile(
                    icon: Icons.document_scanner_outlined,
                    title: 'PDF & Document OCR Ingestion',
                    subtitle: 'Index local PDFs and screenshots into graph',
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _openPermissionsPrivacySheet() async {
    await showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: MatteColors.panel,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        side: BorderSide(color: MatteColors.borderSubtle, width: 1),
      ),
      builder: (ctx) {
        return Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const _SheetHandle(),
              const SizedBox(height: 18),
              const Text(
                'Permissions & Privacy',
                style: TextStyle(
                  color: MatteColors.textPrimary,
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 6),
              const Text(
                'Synapse processes your personal knowledge strictly on-device with zero external telemetry.',
                style: TextStyle(
                  color: MatteColors.textSecondary,
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: 16),
              Container(
                padding: const EdgeInsets.all(14),
                decoration: BoxDecoration(
                  color: MatteColors.inset,
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: MatteColors.borderSubtle, width: 1),
                ),
                child: const Column(
                  children: [
                    _InfoRow(
                      label: 'Local Vector & Graph Storage',
                      value: 'Granted (On-Device)',
                    ),
                    Divider(height: 18, color: MatteColors.borderSubtle),
                    _InfoRow(
                      label: 'External Analytics / Telemetry',
                      value: 'Disabled (0%)',
                    ),
                    Divider(height: 18, color: MatteColors.borderSubtle),
                    _InfoRow(
                      label: 'Gmail OAuth Scope',
                      value: 'Read-Only (gmail.readonly)',
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              const _ComingSoonFeatureTile(
                icon: Icons.fingerprint_rounded,
                title: 'Biometric Vault Lock',
                subtitle: 'Require fingerprint / FaceID to open Synapse',
              ),
              const SizedBox(height: 8),
              const _ComingSoonFeatureTile(
                icon: Icons.archive_outlined,
                title: 'Encrypted Knowledge Export',
                subtitle: 'Export .synapse encrypted archive snapshot',
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _openColorModeSheet() async {
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: MatteColors.panel,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        side: BorderSide(color: MatteColors.borderSubtle, width: 1),
      ),
      builder: (ctx) {
        return Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const _SheetHandle(),
              const SizedBox(height: 18),
              const Text(
                'Color Mode',
                style: TextStyle(
                  color: MatteColors.textPrimary,
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 6),
              const Text(
                'Surface appearance calibrated to the Synapse Solid Matte specification.',
                style: TextStyle(
                  color: MatteColors.textSecondary,
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: 16),
              _buildColorModeContent(),
            ],
          ),
        );
      },
    );
  }

  Future<void> _openPaletteSheet() async {
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: MatteColors.panel,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        side: BorderSide(color: MatteColors.borderSubtle, width: 1),
      ),
      builder: (ctx) {
        return StatefulBuilder(
          builder: (ctx, setSheetState) {
            return Padding(
              padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const _SheetHandle(),
                  const SizedBox(height: 18),
                  const Text(
                    'Knowledge Graph Palette',
                    style: TextStyle(
                      color: MatteColors.textPrimary,
                      fontSize: 17,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Select the Solid Matte color tokens used to render graph nodes.',
                    style: TextStyle(
                      color: MatteColors.textSecondary,
                      fontSize: 13,
                    ),
                  ),
                  const SizedBox(height: 16),
                  _buildPaletteOptionsList(
                    onSelected: () {
                      setSheetState(() {});
                      if (ctx.mounted) Navigator.of(ctx).pop();
                    },
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Future<void> _openFontStyleSheet() async {
    await showModalBottomSheet<void>(
      context: context,
      backgroundColor: MatteColors.panel,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        side: BorderSide(color: MatteColors.borderSubtle, width: 1),
      ),
      builder: (ctx) {
        return Padding(
          padding: const EdgeInsets.fromLTRB(20, 16, 20, 28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const _SheetHandle(),
              const SizedBox(height: 18),
              const Text(
                'Font Style',
                style: TextStyle(
                  color: MatteColors.textPrimary,
                  fontSize: 17,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 6),
              const Text(
                'Typography settings for chat streams and code blocks.',
                style: TextStyle(
                  color: MatteColors.textSecondary,
                  fontSize: 13,
                ),
              ),
              const SizedBox(height: 16),
              _buildFontStyleContent(),
            ],
          ),
        );
      },
    );
  }

  // ===========================================================================
  // Clear Conversation History Confirmation Dialog
  // ===========================================================================
  Future<void> _confirmAndClearHistory() async {
    final count = widget.apiService.sessions.length;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: MatteColors.panel,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: MatteColors.borderStrong, width: 1),
        ),
        title: const Text(
          'Clear Conversation History?',
          style: TextStyle(
            color: MatteColors.textPrimary,
            fontSize: 16.5,
            fontWeight: FontWeight.w600,
          ),
        ),
        content: Text(
          'This will permanently remove all $count saved chat session(s) on this device and start a fresh thread.',
          style: const TextStyle(
            color: MatteColors.textSecondary,
            fontSize: 13.5,
            height: 1.4,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text(
              'Cancel',
              style: TextStyle(color: MatteColors.textSecondary),
            ),
          ),
          InkWell(
            onTap: () => Navigator.of(ctx).pop(true),
            borderRadius: BorderRadius.circular(20),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: MatteColors.statusDanger,
                borderRadius: BorderRadius.circular(20),
              ),
              child: const Text(
                'Clear All',
                style: TextStyle(
                  color: MatteColors.textPrimary,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
        ],
      ),
    );

    if (confirmed == true) {
      await widget.apiService.clearAllSessions();
      _showStatusBanner('Cleared all local conversation history.');
    }
  }

  // ===========================================================================
  // Shared Content Builders (Used in both Desktop Views & Mobile Sheets)
  // ===========================================================================

  Widget _buildLanguageModelCards({required bool isDesktopGrid}) {
    final api = widget.apiService;
    final isDownloaded = api.isQwenDownloaded;
    final isQwenOn = api.useQwenModel;
    final isRuleBasedOn = api.isRuleBasedActive;
    final isDownloading = api.isDownloadingQwen;
    final progress = api.qwenDownloadProgress;
    final downloadedMB = api.qwenDownloadedMB;
    final totalMB = api.qwenTotalMB;
    final speed = api.qwenDownloadSpeedMBps;
    final error = api.qwenDownloadError;

    final qwenCard = Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: isQwenOn ? MatteColors.panelHover : MatteColors.panel,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isQwenOn ? MatteColors.nodePerson : MatteColors.borderSubtle,
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: MatteColors.inset,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: MatteColors.borderSubtle, width: 1),
                ),
                child: const Icon(
                  Icons.auto_awesome_outlined,
                  size: 19,
                  color: MatteColors.nodePerson,
                ),
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Qwen 2.5 0.5B Instruct (qwen2.5:0.5b)',
                      style: TextStyle(
                        color: MatteColors.textPrimary,
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    SizedBox(height: 2),
                    Text(
                      '469 MB GGUF · Local Neural LLM (llama.cpp / Ollama)',
                      style: TextStyle(
                        color: MatteColors.textSecondary,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              if (isDownloaded)
                Switch(
                  value: isQwenOn,
                  activeThumbColor: MatteColors.textPrimary,
                  activeTrackColor: MatteColors.nodeProject,
                  inactiveThumbColor: MatteColors.textMuted,
                  inactiveTrackColor: MatteColors.inset,
                  onChanged: (val) async {
                    await api.setEngineMode(useQwen: val);
                    _showStatusBanner(
                      val
                          ? 'Switched to Qwen 2.5 (0.5B) Neural Model'
                          : 'Switched to Rule-Based Engine',
                    );
                  },
                ),
            ],
          ),
          const SizedBox(height: 12),
          const Text(
            'Benefits: Deep contextual synthesis, multi-email summarization, and natural conversational writing 100% offline.',
            style: TextStyle(
              color: MatteColors.textSecondary,
              fontSize: 12.5,
              height: 1.4,
            ),
          ),
          if (error != null && !isDownloading) ...[
            const SizedBox(height: 10),
            Text(
              'Error: $error',
              style: const TextStyle(
                color: MatteColors.statusDanger,
                fontSize: 12,
              ),
            ),
          ],
          const SizedBox(height: 14),
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
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: progress > 0.01 ? progress : null,
                minHeight: 6,
                backgroundColor: MatteColors.canvas,
                valueColor: const AlwaysStoppedAnimation<Color>(
                  MatteColors.nodeProject,
                ),
              ),
            ),
            const SizedBox(height: 8),
            Align(
              alignment: Alignment.centerRight,
              child: TextButton(
                onPressed: api.cancelQwenDownload,
                child: const Text(
                  'Pause / Cancel',
                  style: TextStyle(
                    color: MatteColors.textSecondary,
                    fontSize: 12,
                  ),
                ),
              ),
            ),
          ] else if (!isDownloaded)
            _WhitePillButton(
              label: 'Download Qwen 2.5 (469 MB)',
              onTap: () => api.downloadQwenModel(),
            )
          else
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(
                  isQwenOn
                      ? 'Status: Active (On)'
                      : 'Status: Downloaded (Off)',
                  style: TextStyle(
                    color: isQwenOn
                        ? MatteColors.nodeProject
                        : MatteColors.textMuted,
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                InkWell(
                  onTap: () async {
                    await api.deleteQwenModel();
                    _showStatusBanner(
                      'Removed Qwen 2.5 weights (469 MB freed) · Rule-Based Engine active',
                    );
                  },
                  child: const Text(
                    'Remove Model (469 MB)',
                    style: TextStyle(
                      color: MatteColors.statusDanger,
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ),
              ],
            ),
        ],
      ),
    );

    final ruleBasedCard = Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: isRuleBasedOn ? MatteColors.panelHover : MatteColors.panel,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color:
              isRuleBasedOn ? MatteColors.nodeProject : MatteColors.borderSubtle,
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 36,
                height: 36,
                decoration: BoxDecoration(
                  color: MatteColors.inset,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: MatteColors.borderSubtle, width: 1),
                ),
                child: const Icon(
                  Icons.bolt_rounded,
                  size: 20,
                  color: MatteColors.nodeProject,
                ),
              ),
              const SizedBox(width: 12),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Rule-Based RAG Engine',
                      style: TextStyle(
                        color: MatteColors.textPrimary,
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    SizedBox(height: 2),
                    Text(
                      '0 MB · Built-in Deterministic Engine',
                      style: TextStyle(
                        color: MatteColors.textSecondary,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              Switch(
                value: isRuleBasedOn,
                activeThumbColor: MatteColors.textPrimary,
                activeTrackColor: MatteColors.nodeProject,
                inactiveThumbColor: MatteColors.textMuted,
                inactiveTrackColor: MatteColors.inset,
                onChanged: (useRuleBased) async {
                  await api.setEngineMode(useQwen: !useRuleBased);
                  _showStatusBanner(
                    useRuleBased
                        ? 'Rule-Based Engine enabled'
                        : 'Qwen 2.5 (0.5B) Neural Model enabled',
                  );
                },
              ),
            ],
          ),
          const SizedBox(height: 12),
          const Text(
            'Benefits: Instant response speed, zero storage or battery impact, deterministic vector chunk & graph triple matching.',
            style: TextStyle(
              color: MatteColors.textSecondary,
              fontSize: 12.5,
              height: 1.4,
            ),
          ),
          const SizedBox(height: 14),
          Text(
            isRuleBasedOn
                ? 'Status: Active (0 MB overhead)'
                : 'Status: Standby (Switch on anytime)',
            style: TextStyle(
              color: isRuleBasedOn
                  ? MatteColors.nodeProject
                  : MatteColors.textMuted,
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );

    if (isDesktopGrid) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(child: qwenCard),
              const SizedBox(width: 16),
              Expanded(child: ruleBasedCard),
            ],
          ),
          const SizedBox(height: 22),
          const Text(
            'UPCOMING LOCAL MODELS (ROADMAP)',
            style: TextStyle(
              color: MatteColors.textMuted,
              fontSize: 11,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.7,
            ),
          ),
          const SizedBox(height: 10),
          const Row(
            children: [
              Expanded(
                child: _ComingSoonFeatureTile(
                  icon: Icons.memory_rounded,
                  title: 'Llama 3.2 1B Instruct (GGUF)',
                  subtitle: 'Extended 128k context local model',
                ),
              ),
              SizedBox(width: 14),
              Expanded(
                child: _ComingSoonFeatureTile(
                  icon: Icons.hub_outlined,
                  title: 'DeepSeek R1 Distill 1.5B',
                  subtitle: 'Chain-of-thought local reasoning model',
                ),
              ),
            ],
          ),
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        qwenCard,
        const SizedBox(height: 12),
        ruleBasedCard,
        const SizedBox(height: 12),
        const _ComingSoonFeatureTile(
          icon: Icons.memory_rounded,
          title: 'Llama 3.2 1B Instruct (GGUF)',
          subtitle: 'Extended 128k context local model',
        ),
      ],
    );
  }

  Widget _buildColorModeContent({bool isDesktop = false}) {
    final activeCard = Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
      decoration: BoxDecoration(
        color: MatteColors.panelHover,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: MatteColors.borderStrong, width: 1),
      ),
      child: const Row(
        children: [
          Icon(
            Icons.dark_mode_outlined,
            size: 22,
            color: MatteColors.nodePerson,
          ),
          SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Solid Matte Dark (#09090b)',
                  style: TextStyle(
                    color: MatteColors.textPrimary,
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                SizedBox(height: 3),
                Text(
                  'Default Zinc 950 low-glare dark canvas with 1px structural borders',
                  style: TextStyle(
                    color: MatteColors.textSecondary,
                    fontSize: 12.5,
                  ),
                ),
              ],
            ),
          ),
          Icon(
            Icons.check_circle_rounded,
            size: 19,
            color: MatteColors.nodeProject,
          ),
        ],
      ),
    );

    const comingSoonLight = _ComingSoonFeatureTile(
      icon: Icons.light_mode_outlined,
      title: 'Solid Matte Daylight (Warm Paper)',
      subtitle: 'High-contrast matte light theme calibrated for daylight',
    );

    if (isDesktop) {
      return Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(child: activeCard),
          const SizedBox(width: 16),
          const Expanded(child: comingSoonLight),
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        activeCard,
        const SizedBox(height: 10),
        comingSoonLight,
      ],
    );
  }

  Widget _buildPaletteOptionsList({
    VoidCallback? onSelected,
    bool isDesktopGrid = false,
  }) {
    final current = widget.apiService.graphPalette;
    final options = [
      (
        'zinc',
        'Zinc (Linear)',
        'Cool slate & lavender graph accents for engineering workspaces'
      ),
      (
        'stone',
        'Stone (Anthropic)',
        'Warm terracotta, sage & ochre tones inspired by editorial paper'
      ),
      (
        'basalt',
        'Basalt (Slate)',
        'Deep mineral indigo & teal accents for high-density graphs'
      ),
    ];

    final cards = options.map((opt) {
      final id = opt.$1;
      final title = opt.$2;
      final desc = opt.$3;
      final isSelected = current == id;
      final swatches =
          MatteColors.graphPalettes[id] ?? MatteColors.graphPalettes['zinc']!;

      return InkWell(
        onTap: () async {
          await widget.apiService.updateSettings(graphPalette: id);
          if (mounted) setState(() {});
          onSelected?.call();
          _showStatusBanner('Applied $title graph palette');
        },
        borderRadius: BorderRadius.circular(12),
        child: Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            color: isSelected ? MatteColors.panelHover : MatteColors.panel,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isSelected
                  ? MatteColors.nodePerson
                  : MatteColors.borderSubtle,
              width: 1,
            ),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      title,
                      style: const TextStyle(
                        color: MatteColors.textPrimary,
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  if (isSelected)
                    const Icon(
                      Icons.check_circle_rounded,
                      size: 18,
                      color: MatteColors.nodeProject,
                    ),
                ],
              ),
              const SizedBox(height: 6),
              Text(
                desc,
                style: const TextStyle(
                  color: MatteColors.textSecondary,
                  fontSize: 12.5,
                  height: 1.38,
                ),
              ),
              const SizedBox(height: 14),
              Row(
                children: swatches.entries.take(5).map((entry) {
                  return Padding(
                    padding: const EdgeInsets.only(right: 8),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: MatteColors.inset,
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
                            width: 10,
                            height: 10,
                            decoration: BoxDecoration(
                              color: entry.value,
                              shape: BoxShape.circle,
                            ),
                          ),
                          const SizedBox(width: 5),
                          Text(
                            entry.key,
                            style: const TextStyle(
                              color: MatteColors.textSecondary,
                              fontSize: 10.5,
                            ),
                          ),
                        ],
                      ),
                    ),
                  );
                }).toList(),
              ),
            ],
          ),
        ),
      );
    }).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (int i = 0; i < cards.length; i++) ...[
          if (i > 0) const SizedBox(height: 12),
          cards[i],
        ],
      ],
    );
  }

  Widget _buildFontStyleContent({bool isDesktop = false}) {
    final activeFontCard = Container(
      padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
      decoration: BoxDecoration(
        color: MatteColors.panelHover,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: MatteColors.borderStrong, width: 1),
      ),
      child: const Row(
        children: [
          Icon(
            Icons.font_download_outlined,
            size: 22,
            color: MatteColors.nodePerson,
          ),
          SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Inter (System Sans)',
                  style: TextStyle(
                    color: MatteColors.textPrimary,
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                SizedBox(height: 3),
                Text(
                  'Clean geometric sans-serif tuned for high density & legibility',
                  style: TextStyle(
                    color: MatteColors.textSecondary,
                    fontSize: 12.5,
                  ),
                ),
              ],
            ),
          ),
          Icon(
            Icons.check_circle_rounded,
            size: 19,
            color: MatteColors.nodeProject,
          ),
        ],
      ),
    );

    if (isDesktop) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          activeFontCard,
          const SizedBox(height: 16),
          const Row(
            children: [
              Expanded(
                child: _ComingSoonFeatureTile(
                  icon: Icons.menu_book_outlined,
                  title: 'Editorial Serif',
                  subtitle: 'Book-style serif typography for long-form reading',
                ),
              ),
              SizedBox(width: 14),
              Expanded(
                child: _ComingSoonFeatureTile(
                  icon: Icons.code_rounded,
                  title: 'JetBrains Mono Full-UI',
                  subtitle: 'Developer monospace across all workspace panels',
                ),
              ),
            ],
          ),
        ],
      );
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        activeFontCard,
        const SizedBox(height: 10),
        const _ComingSoonFeatureTile(
          icon: Icons.menu_book_outlined,
          title: 'Editorial Serif',
          subtitle: 'Book-style serif typography for long-form reading',
        ),
        const SizedBox(height: 8),
        const _ComingSoonFeatureTile(
          icon: Icons.code_rounded,
          title: 'JetBrains Mono Full-UI',
          subtitle: 'Developer monospace across all panels',
        ),
      ],
    );
  }

  // ===========================================================================
  // Desktop Sub-Page Builders (Matches ConnectorsScreen Desktop Layout)
  // ===========================================================================

  Widget _buildDesktopSettingsLayout(
    BuildContext context, {
    required HealthStatus health,
    required bool isStandalone,
    required int sessionCount,
    required String activePalette,
    required Map<String, Color> swatches,
    required int enabledCapabilities,
    required String modelSubtitle,
  }) {
    final navTabs = <(_DesktopSettingsSection, String, IconData)>[
      (_DesktopSettingsSection.overview, 'Overview', Icons.grid_view_rounded),
      (
        _DesktopSettingsSection.workspaceProfile,
        'Workspace Profile',
        Icons.account_circle_outlined
      ),
      (
        _DesktopSettingsSection.languageModel,
        'Language Model',
        Icons.smart_toy_outlined
      ),
      (
        _DesktopSettingsSection.capabilities,
        'Capabilities',
        Icons.tune_rounded
      ),
      (
        _DesktopSettingsSection.permissionsPrivacy,
        'Permissions & Privacy',
        Icons.shield_outlined
      ),
      (
        _DesktopSettingsSection.colorMode,
        'Color Mode',
        Icons.dark_mode_outlined
      ),
      (
        _DesktopSettingsSection.graphPalette,
        'Graph Palette',
        Icons.palette_outlined
      ),
      (
        _DesktopSettingsSection.fontStyle,
        'Font Style',
        Icons.font_download_outlined
      ),
    ];

    return Container(
      color: MatteColors.canvas,
      child: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 24),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 880),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // 1. Desktop Page Header Row (Matches ConnectorsScreen)
                Row(
                  children: [
                    if (_activeDesktopSection !=
                        _DesktopSettingsSection.overview) ...[
                      InkWell(
                        onTap: () => setState(
                          () => _activeDesktopSection =
                              _DesktopSettingsSection.overview,
                        ),
                        borderRadius: BorderRadius.circular(6),
                        child: Container(
                          height: 34,
                          padding: const EdgeInsets.symmetric(horizontal: 10),
                          margin: const EdgeInsets.only(right: 12),
                          decoration: MatteTheme.panelDecoration(borderRadius: 6),
                          child: const Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(
                                Icons.arrow_back_rounded,
                                size: 15,
                                color: MatteColors.textPrimary,
                              ),
                              SizedBox(width: 6),
                              Text(
                                'All Settings',
                                style: TextStyle(
                                  color: MatteColors.textPrimary,
                                  fontSize: 12.5,
                                  fontWeight: FontWeight.w500,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ],
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            _desktopTitleForSection(_activeDesktopSection),
                            style: const TextStyle(
                              color: MatteColors.textPrimary,
                              fontSize: 19,
                              fontWeight: FontWeight.w600,
                              letterSpacing: -0.3,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            _desktopSubtitleForSection(_activeDesktopSection),
                            style: const TextStyle(
                              color: MatteColors.textSecondary,
                              fontSize: 13,
                              height: 1.4,
                            ),
                          ),
                        ],
                      ),
                    ),
                    const SizedBox(width: 12),
                    _OutlinePillButton(
                      label: _isTestingHealth ? 'Verifying...' : 'Verify Status',
                      onTap: _isTestingHealth ? null : _verifyConnection,
                    ),
                  ],
                ),

                const SizedBox(height: 16),

                // 2. Desktop Section Pill Navigation Bar
                SingleChildScrollView(
                  scrollDirection: Axis.horizontal,
                  child: Row(
                    children: navTabs.map((tab) {
                      final isSelected = _activeDesktopSection == tab.$1;
                      return Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: InkWell(
                          onTap: () =>
                              setState(() => _activeDesktopSection = tab.$1),
                          borderRadius: BorderRadius.circular(6),
                          child: Container(
                            height: 34,
                            padding: const EdgeInsets.symmetric(horizontal: 12),
                            decoration: BoxDecoration(
                              color: isSelected
                                  ? MatteColors.panelHover
                                  : MatteColors.panel,
                              borderRadius: BorderRadius.circular(6),
                              border: Border.all(
                                color: isSelected
                                    ? MatteColors.borderStrong
                                    : MatteColors.borderSubtle,
                                width: 1,
                              ),
                            ),
                            child: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  tab.$3,
                                  size: 15,
                                  color: isSelected
                                      ? MatteColors.nodePerson
                                      : MatteColors.textSecondary,
                                ),
                                const SizedBox(width: 7),
                                Text(
                                  tab.$2,
                                  style: TextStyle(
                                    color: isSelected
                                        ? MatteColors.textPrimary
                                        : MatteColors.textSecondary,
                                    fontSize: 12.5,
                                    fontWeight: isSelected
                                        ? FontWeight.w600
                                        : FontWeight.w500,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ),

                const SizedBox(height: 20),

                // 3. Active Desktop Section Content
                switch (_activeDesktopSection) {
                  _DesktopSettingsSection.overview =>
                    _buildDesktopOverviewSection(
                      health: health,
                      isStandalone: isStandalone,
                      sessionCount: sessionCount,
                      activePalette: activePalette,
                      swatches: swatches,
                      enabledCapabilities: enabledCapabilities,
                      modelSubtitle: modelSubtitle,
                    ),
                  _DesktopSettingsSection.workspaceProfile =>
                    _buildDesktopWorkspaceProfileView(isStandalone: isStandalone),
                  _DesktopSettingsSection.languageModel =>
                    _buildLanguageModelCards(isDesktopGrid: true),
                  _DesktopSettingsSection.capabilities =>
                    _buildDesktopCapabilitiesView(),
                  _DesktopSettingsSection.permissionsPrivacy =>
                    _buildDesktopPermissionsPrivacyView(),
                  _DesktopSettingsSection.colorMode =>
                    _buildColorModeContent(isDesktop: true),
                  _DesktopSettingsSection.graphPalette =>
                    _buildPaletteOptionsList(isDesktopGrid: true),
                  _DesktopSettingsSection.fontStyle =>
                    _buildFontStyleContent(isDesktop: true),
                },
              ],
            ),
          ),
        ),
      ),
    );
  }

  String _desktopTitleForSection(_DesktopSettingsSection section) {
    switch (section) {
      case _DesktopSettingsSection.overview:
        return 'Workspace & Engine Settings';
      case _DesktopSettingsSection.workspaceProfile:
        return 'Workspace Profile & Telemetry';
      case _DesktopSettingsSection.languageModel:
        return 'Language Model & Inference Engine';
      case _DesktopSettingsSection.capabilities:
        return 'Hybrid RAG & Agentic Capabilities';
      case _DesktopSettingsSection.permissionsPrivacy:
        return 'Permissions, Security & Local Privacy';
      case _DesktopSettingsSection.colorMode:
        return 'Color Mode & Surface Calibration';
      case _DesktopSettingsSection.graphPalette:
        return 'Knowledge Graph Node Palettes';
      case _DesktopSettingsSection.fontStyle:
        return 'Workspace Typography & Font Style';
    }
  }

  String _desktopSubtitleForSection(_DesktopSettingsSection section) {
    switch (section) {
      case _DesktopSettingsSection.overview:
        return 'Manage your local AI inference engine, hybrid RAG indexing, MCP connectors, and Solid Matte appearance.';
      case _DesktopSettingsSection.workspaceProfile:
        return 'Inspect your local workspace owner identity, ChromaDB & NetworkX memory counts, and runtime endpoints.';
      case _DesktopSettingsSection.languageModel:
        return 'Toggle between Qwen 2.5 (0.5B) for deep neural synthesis or the 0 MB Rule-Based Engine for instant lookups.';
      case _DesktopSettingsSection.capabilities:
        return 'Configure automatic ChromaDB vector + NetworkX graph retrieval and inspect upcoming local capabilities.';
      case _DesktopSettingsSection.permissionsPrivacy:
        return 'Verify on-device storage isolation, OAuth read-only scopes, and zero-telemetry guarantees.';
      case _DesktopSettingsSection.colorMode:
        return 'Configure the Solid Matte dark canvas specification across all desktop panels.';
      case _DesktopSettingsSection.graphPalette:
        return 'Choose the color token palette used to render Person, Email, Project, Tool, and Topic nodes.';
      case _DesktopSettingsSection.fontStyle:
        return 'Customize typography for conversational streams, entity inspectors, and code blocks.';
    }
  }

  Widget _buildDesktopOverviewSection({
    required HealthStatus health,
    required bool isStandalone,
    required int sessionCount,
    required String activePalette,
    required Map<String, Color> swatches,
    required int enabledCapabilities,
    required String modelSubtitle,
  }) {
    final stats = widget.apiService.graphStats;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // Top Hero Card (Desktop Wide Banner)
        Container(
          padding: const EdgeInsets.all(20),
          decoration: MatteTheme.panelDecoration(borderRadius: 10),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: MatteColors.inset,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: MatteColors.borderStrong, width: 1),
                ),
                child: const Icon(
                  Icons.auto_awesome_outlined,
                  size: 22,
                  color: MatteColors.nodePerson,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          widget.apiService.useQwenModel
                              ? 'Qwen 2.5 (0.5B) Neural Engine Active'
                              : 'Rule-Based RAG Engine Active (0 MB)',
                          style: const TextStyle(
                            color: MatteColors.textPrimary,
                            fontSize: 16,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(width: 10),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 9,
                            vertical: 3,
                          ),
                          decoration: BoxDecoration(
                            color: MatteColors.textPrimary,
                            borderRadius: BorderRadius.circular(20),
                          ),
                          child: Text(
                            widget.apiService.useQwenModel
                                ? 'Qwen 2.5'
                                : 'Rule-Based',
                            style: const TextStyle(
                              color: MatteColors.canvas,
                              fontSize: 11,
                              fontWeight: FontWeight.w700,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 5),
                    Text(
                      widget.apiService.useQwenModel
                          ? 'Full local neural synthesis is active over your ChromaDB vectors (${widget.apiService.syncState.itemsSynced} emails) and NetworkX graph (${stats.totalNodes} nodes).'
                          : 'Instant deterministic keyword & graph lookup is active. Switch to Qwen 2.5 anytime for full neural reasoning.',
                      style: const TextStyle(
                        color: MatteColors.textSecondary,
                        fontSize: 13,
                        height: 1.4,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 16),
              _WhitePillButton(
                label: 'Configure Model',
                onTap: () => setState(
                  () => _activeDesktopSection =
                      _DesktopSettingsSection.languageModel,
                ),
              ),
            ],
          ),
        ),

        const SizedBox(height: 18),

        // Desktop 2-Column Settings Grid (Matches ConnectorsScreen style)
        Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Left Column: Workspace & Intelligence
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    'WORKSPACE & INTELLIGENCE',
                    style: TextStyle(
                      color: MatteColors.textMuted,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.7,
                    ),
                  ),
                  const SizedBox(height: 8),
                  _SettingsGroupCard(
                    items: [
                      _SettingsRowItem(
                        icon: Icons.account_circle_outlined,
                        title: 'Workspace profile',
                        subtitle:
                            'Akash · ${stats.totalNodes} nodes · ${widget.apiService.syncState.itemsSynced} emails',
                        onTap: () => setState(
                          () => _activeDesktopSection =
                              _DesktopSettingsSection.workspaceProfile,
                        ),
                      ),
                      _SettingsRowItem(
                        icon: Icons.smart_toy_outlined,
                        title: 'Language model',
                        subtitle: modelSubtitle,
                        onTap: () => setState(
                          () => _activeDesktopSection =
                              _DesktopSettingsSection.languageModel,
                        ),
                      ),
                      _SettingsRowItem(
                        icon: Icons.tune_rounded,
                        title: 'Capabilities',
                        subtitle:
                            '$enabledCapabilities enabled · ${widget.apiService.defaultUseRag ? "Hybrid RAG on" : "Direct mode"}',
                        onTap: () => setState(
                          () => _activeDesktopSection =
                              _DesktopSettingsSection.capabilities,
                        ),
                      ),
                      _SettingsRowItem(
                        icon: Icons.widgets_outlined,
                        title: 'Connectors',
                        subtitle: health.isGmailConnected
                            ? 'Gmail MCP · Connected'
                            : 'Gmail, Notion, Calendar',
                        onTap: () {
                          if (widget.isDialog) {
                            Navigator.of(context).pop();
                          }
                          widget.onOpenConnectors?.call();
                        },
                      ),
                    ],
                  ),
                ],
              ),
            ),

            const SizedBox(width: 18),

            // Right Column: Appearance, Privacy & Data
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    'APPEARANCE, PRIVACY & DATA',
                    style: TextStyle(
                      color: MatteColors.textMuted,
                      fontSize: 11,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.7,
                    ),
                  ),
                  const SizedBox(height: 8),
                  _SettingsGroupCard(
                    items: [
                      _SettingsRowItem(
                        icon: Icons.shield_outlined,
                        title: 'Permissions & privacy',
                        subtitle: '100% local storage · Zero telemetry',
                        onTap: () => setState(
                          () => _activeDesktopSection =
                              _DesktopSettingsSection.permissionsPrivacy,
                        ),
                      ),
                      _SettingsRowItem(
                        icon: Icons.dark_mode_outlined,
                        title: 'Color mode',
                        subtitle: 'Solid Matte Dark (#09090b)',
                        onTap: () => setState(
                          () => _activeDesktopSection =
                              _DesktopSettingsSection.colorMode,
                        ),
                      ),
                      _SettingsRowItem(
                        icon: Icons.palette_outlined,
                        title: 'Graph palette',
                        subtitle: _paletteDisplayName(activePalette),
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: swatches.values
                              .take(5)
                              .map(
                                (c) => Container(
                                  width: 10,
                                  height: 10,
                                  margin: const EdgeInsets.only(left: 4),
                                  decoration: BoxDecoration(
                                    color: c,
                                    shape: BoxShape.circle,
                                  ),
                                ),
                              )
                              .toList(),
                        ),
                        onTap: () => setState(
                          () => _activeDesktopSection =
                              _DesktopSettingsSection.graphPalette,
                        ),
                      ),
                      _SettingsRowItem(
                        icon: Icons.font_download_outlined,
                        title: 'Font style',
                        subtitle: 'Inter (System Sans)',
                        onTap: () => setState(
                          () => _activeDesktopSection =
                              _DesktopSettingsSection.fontStyle,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),

        const SizedBox(height: 18),

        // Bottom Desktop Danger / Session Management Bar
        _SettingsGroupCard(
          items: [
            _SettingsRowItem(
              icon: Icons.delete_outline_rounded,
              title: 'Clear conversation history',
              subtitle:
                  '$sessionCount saved session(s) on this device · Permanently remove local chat threads',
              iconColor: MatteColors.statusDanger,
              titleColor: MatteColors.statusDanger,
              onTap: _confirmAndClearHistory,
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildDesktopWorkspaceProfileView({required bool isStandalone}) {
    final stats = widget.apiService.graphStats;
    final sync = widget.apiService.syncState;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        // 4 Desktop Metric Cards across top
        Row(
          children: [
            Expanded(
              child: _DesktopMetricCard(
                icon: Icons.person_outline_rounded,
                label: 'WORKSPACE OWNER',
                value: 'Akash',
                sublabel: isStandalone
                    ? 'akash@synapse.local'
                    : widget.apiService.backendUrl,
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: _DesktopMetricCard(
                icon: Icons.memory_rounded,
                label: 'ACTIVE ENGINE',
                value: widget.apiService.activeEngineBadge,
                sublabel: widget.apiService.useQwenModel
                    ? 'Local Neural LLM'
                    : 'Deterministic 0 MB',
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: _DesktopMetricCard(
                icon: Icons.hub_outlined,
                label: 'KNOWLEDGE GRAPH',
                value: '${stats.totalNodes} Nodes',
                sublabel: '${stats.totalEdges} directed relations',
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: _DesktopMetricCard(
                icon: Icons.mail_outline_rounded,
                label: 'INDEXED MEMORY',
                value: '${sync.itemsSynced} Emails',
                sublabel: 'ChromaDB vector chunks',
              ),
            ),
          ],
        ),
        const SizedBox(height: 22),
        const Text(
          'UPCOMING WORKSPACE FEATURES (ROADMAP)',
          style: TextStyle(
            color: MatteColors.textMuted,
            fontSize: 11,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.7,
          ),
        ),
        const SizedBox(height: 10),
        const Row(
          children: [
            Expanded(
              child: _ComingSoonFeatureTile(
                icon: Icons.cloud_sync_outlined,
                title: 'Multi-Device Encrypted Sync',
                subtitle: 'End-to-end encrypted graph sync across devices',
              ),
            ),
            SizedBox(width: 14),
            Expanded(
              child: _ComingSoonFeatureTile(
                icon: Icons.badge_outlined,
                title: 'Custom Persona & System Prompt',
                subtitle: 'Tailor response tone and domain expertise',
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildDesktopCapabilitiesView() {
    final useRag = widget.apiService.defaultUseRag;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Container(
          padding: const EdgeInsets.all(18),
          decoration: MatteTheme.panelDecoration(borderRadius: 10),
          child: Row(
            children: [
              Container(
                width: 40,
                height: 40,
                decoration: BoxDecoration(
                  color: MatteColors.inset,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: MatteColors.borderSubtle, width: 1),
                ),
                child: const Icon(
                  Icons.grain_rounded,
                  size: 20,
                  color: MatteColors.nodeProject,
                ),
              ),
              const SizedBox(width: 14),
              const Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Hybrid RAG Retrieval (ChromaDB + NetworkX)',
                      style: TextStyle(
                        color: MatteColors.textPrimary,
                        fontSize: 15.5,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    SizedBox(height: 3),
                    Text(
                      'Automatically retrieves top-k semantic email chunks from ChromaDB and 1-hop entity relations from your NetworkX knowledge graph on every chat turn.',
                      style: TextStyle(
                        color: MatteColors.textSecondary,
                        fontSize: 12.5,
                        height: 1.4,
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(width: 14),
              Switch(
                value: useRag,
                activeThumbColor: MatteColors.textPrimary,
                activeTrackColor: MatteColors.nodeProject,
                inactiveThumbColor: MatteColors.textMuted,
                inactiveTrackColor: MatteColors.inset,
                onChanged: (val) async {
                  await widget.apiService.updateSettings(defaultUseRag: val);
                  if (mounted) setState(() {});
                },
              ),
            ],
          ),
        ),
        const SizedBox(height: 22),
        const Text(
          'EXTENSIBLE AGENTIC CAPABILITIES (ROADMAP)',
          style: TextStyle(
            color: MatteColors.textMuted,
            fontSize: 11,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.7,
          ),
        ),
        const SizedBox(height: 10),
        const Row(
          children: [
            Expanded(
              child: _ComingSoonFeatureTile(
                icon: Icons.mic_none_rounded,
                title: 'Offline Voice & Whisper Dictation',
                subtitle: 'On-device speech-to-text voice queries',
              ),
            ),
            SizedBox(width: 14),
            Expanded(
              child: _ComingSoonFeatureTile(
                icon: Icons.document_scanner_outlined,
                title: 'PDF & Document OCR Ingestion',
                subtitle: 'Index local PDFs and screenshots into graph',
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildDesktopPermissionsPrivacyView() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            const Expanded(
              child: _DesktopMetricCard(
                icon: Icons.storage_rounded,
                label: 'VECTOR & GRAPH STORAGE',
                value: '100% On-Device',
                sublabel: 'Local ChromaDB & NetworkX state',
              ),
            ),
            const SizedBox(width: 14),
            const Expanded(
              child: _DesktopMetricCard(
                icon: Icons.visibility_off_outlined,
                label: 'EXTERNAL TELEMETRY',
                value: 'Disabled (0%)',
                sublabel: 'Zero analytics or cloud logging',
              ),
            ),
            const SizedBox(width: 14),
            Expanded(
              child: _DesktopMetricCard(
                icon: Icons.lock_outline_rounded,
                label: 'GMAIL OAUTH SCOPE',
                value: 'Read-Only',
                sublabel: 'gmail.readonly local token',
              ),
            ),
          ],
        ),
        const SizedBox(height: 22),
        const Text(
          'SECURITY & VAULT CONTROLS (ROADMAP)',
          style: TextStyle(
            color: MatteColors.textMuted,
            fontSize: 11,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.7,
          ),
        ),
        const SizedBox(height: 10),
        const Row(
          children: [
            Expanded(
              child: _ComingSoonFeatureTile(
                icon: Icons.fingerprint_rounded,
                title: 'Biometric Vault Lock',
                subtitle: 'Require TouchID / FaceID to unlock Synapse',
              ),
            ),
            SizedBox(width: 14),
            Expanded(
              child: _ComingSoonFeatureTile(
                icon: Icons.archive_outlined,
                title: 'Encrypted Knowledge Export',
                subtitle: 'Export .synapse encrypted archive snapshot',
              ),
            ),
          ],
        ),
      ],
    );
  }

  // ===========================================================================
  // Main Build Method
  // ===========================================================================
  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: widget.apiService,
      builder: (context, _) {
        final isMobile = MatteBreakpoints.isMobile(context);
        final health = widget.apiService.healthStatus;
        final isStandalone =
            widget.apiService.isStandaloneEdition || health.isEmbeddedMode;
        final sessionCount = widget.apiService.sessions.length;
        final activePalette = widget.apiService.graphPalette;
        final swatches = MatteColors.graphPalettes[activePalette] ??
            MatteColors.graphPalettes['zinc']!;

        int enabledCapabilities = 2;
        if (widget.apiService.defaultUseRag) enabledCapabilities++;
        if (widget.apiService.useQwenModel) enabledCapabilities++;
        if (health.isGmailConnected) enabledCapabilities++;

        final modelSubtitle = widget.apiService.useQwenModel
            ? 'Qwen 2.5 (0.5B) · Active'
            : (widget.apiService.isQwenDownloaded
                ? 'Rule-Based Engine · Active (Qwen 2.5 Off)'
                : 'Rule-Based Engine · Active (Qwen 469 MB available)');

        // Desktop / macOS View (> 768px): Render full-width Desktop Settings layout
        if (!isMobile) {
          return _buildDesktopSettingsLayout(
            context,
            health: health,
            isStandalone: isStandalone,
            sessionCount: sessionCount,
            activePalette: activePalette,
            swatches: swatches,
            enabledCapabilities: enabledCapabilities,
            modelSubtitle: modelSubtitle,
          );
        }

        // Mobile View (<= 768px): Render Claude-inspired grouped mobile layout
        return Container(
          color: MatteColors.canvas,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Expanded(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 14,
                  ),
                  child: Center(
                    child: ConstrainedBox(
                      constraints: const BoxConstraints(maxWidth: 560),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          // 1. Top Identity / Active Runtime Pill Card
                          InkWell(
                            onTap: () => _openSection(
                              _DesktopSettingsSection.workspaceProfile,
                              _openWorkspaceProfileSheet,
                            ),
                            borderRadius: BorderRadius.circular(16),
                            child: Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 18,
                                vertical: 16,
                              ),
                              decoration: BoxDecoration(
                                color: MatteColors.panel,
                                borderRadius: BorderRadius.circular(16),
                                border: Border.all(
                                  color: MatteColors.borderSubtle,
                                  width: 1,
                                ),
                              ),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      isStandalone
                                          ? 'akash@synapse.local'
                                          : widget.apiService.backendUrl
                                              .replaceFirst(
                                                  RegExp(r'^https?://'), ''),
                                      style: const TextStyle(
                                        color: MatteColors.textPrimary,
                                        fontSize: 15.5,
                                        fontWeight: FontWeight.w500,
                                      ),
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                                  const SizedBox(width: 12),
                                  Container(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 12,
                                      vertical: 5,
                                    ),
                                    decoration: BoxDecoration(
                                      color: MatteColors.textPrimary,
                                      borderRadius: BorderRadius.circular(20),
                                    ),
                                    child: Text(
                                      widget.apiService.useQwenModel
                                          ? 'Qwen 2.5'
                                          : 'Rule-Based',
                                      style: const TextStyle(
                                        color: MatteColors.canvas,
                                        fontSize: 12,
                                        fontWeight: FontWeight.w700,
                                      ),
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),

                          const SizedBox(height: 14),

                          // 2. Hero Model / Engine Switcher Card
                          Container(
                            padding: const EdgeInsets.all(20),
                            decoration: BoxDecoration(
                              color: MatteColors.panel,
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(
                                color: MatteColors.borderSubtle,
                                width: 1,
                              ),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  widget.apiService.useQwenModel
                                      ? 'Qwen 2.5 (0.5B) Neural Engine Active'
                                      : 'Want deeper AI reasoning?',
                                  style: const TextStyle(
                                    color: MatteColors.textPrimary,
                                    fontSize: 17,
                                    fontWeight: FontWeight.w600,
                                    letterSpacing: -0.2,
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  widget.apiService.useQwenModel
                                      ? 'Full local neural synthesis is enabled over your ChromaDB vectors and NetworkX knowledge graph.'
                                      : 'Enable the local Qwen 2.5 (0.5B · 469 MB) model for natural multi-step synthesis, or stay on the instant 0 MB Rule-Based Engine.',
                                  style: const TextStyle(
                                    color: MatteColors.textSecondary,
                                    fontSize: 14,
                                    height: 1.38,
                                  ),
                                ),
                                const SizedBox(height: 16),
                                Wrap(
                                  spacing: 10,
                                  runSpacing: 10,
                                  children: [
                                    _WhitePillButton(
                                      label: 'Configure Model',
                                      onTap: () => _openSection(
                                        _DesktopSettingsSection.languageModel,
                                        _openModelConfigurationSheet,
                                      ),
                                    ),
                                    _OutlinePillButton(
                                      label: _isTestingHealth
                                          ? 'Verifying...'
                                          : 'Verify Status',
                                      onTap: _isTestingHealth
                                          ? null
                                          : _verifyConnection,
                                    ),
                                  ],
                                ),
                              ],
                            ),
                          ),

                          const SizedBox(height: 14),

                          // 3. Group 1: Workspace Profile & Language Model
                          _SettingsGroupCard(
                            items: [
                              _SettingsRowItem(
                                icon: Icons.account_circle_outlined,
                                title: 'Workspace profile',
                                subtitle:
                                    'Akash · ${widget.apiService.graphStats.totalNodes} graph nodes',
                                onTap: () => _openSection(
                                  _DesktopSettingsSection.workspaceProfile,
                                  _openWorkspaceProfileSheet,
                                ),
                              ),
                              _SettingsRowItem(
                                icon: Icons.smart_toy_outlined,
                                title: 'Language model',
                                subtitle: modelSubtitle,
                                onTap: () => _openSection(
                                  _DesktopSettingsSection.languageModel,
                                  _openModelConfigurationSheet,
                                ),
                              ),
                            ],
                          ),

                          const SizedBox(height: 14),

                          // 4. Group 2: Capabilities, Connectors, Permissions
                          _SettingsGroupCard(
                            items: [
                              _SettingsRowItem(
                                icon: Icons.tune_rounded,
                                title: 'Capabilities',
                                subtitle:
                                    '$enabledCapabilities enabled · ${widget.apiService.defaultUseRag ? "Hybrid RAG on" : "Direct mode"}',
                                onTap: () => _openSection(
                                  _DesktopSettingsSection.capabilities,
                                  _openCapabilitiesSheet,
                                ),
                              ),
                              _SettingsRowItem(
                                icon: Icons.widgets_outlined,
                                title: 'Connectors',
                                subtitle: health.isGmailConnected
                                    ? 'Gmail MCP · Connected'
                                    : 'Gmail, Notion, Calendar',
                                onTap: () {
                                  if (widget.isDialog) {
                                    Navigator.of(context).pop();
                                  }
                                  if (widget.onOpenConnectors != null) {
                                    widget.onOpenConnectors!.call();
                                  } else {
                                    _showStatusBanner(
                                      'Open Connectors from the navigation menu.',
                                    );
                                  }
                                },
                              ),
                              _SettingsRowItem(
                                icon: Icons.shield_outlined,
                                title: 'Permissions & privacy',
                                subtitle: '100% local storage · Zero telemetry',
                                onTap: () => _openSection(
                                  _DesktopSettingsSection.permissionsPrivacy,
                                  _openPermissionsPrivacySheet,
                                ),
                              ),
                            ],
                          ),

                          const SizedBox(height: 14),

                          // 5. Group 3: Appearance & Typography
                          _SettingsGroupCard(
                            items: [
                              _SettingsRowItem(
                                icon: Icons.dark_mode_outlined,
                                title: 'Color mode',
                                subtitle: 'Solid Matte Dark (#09090b)',
                                onTap: () => _openSection(
                                  _DesktopSettingsSection.colorMode,
                                  _openColorModeSheet,
                                ),
                              ),
                              _SettingsRowItem(
                                icon: Icons.palette_outlined,
                                title: 'Graph palette',
                                subtitle: _paletteDisplayName(activePalette),
                                trailing: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: swatches.values
                                      .take(5)
                                      .map(
                                        (c) => Container(
                                          width: 10,
                                          height: 10,
                                          margin:
                                              const EdgeInsets.only(left: 4),
                                          decoration: BoxDecoration(
                                            color: c,
                                            shape: BoxShape.circle,
                                          ),
                                        ),
                                      )
                                      .toList(),
                                ),
                                onTap: () => _openSection(
                                  _DesktopSettingsSection.graphPalette,
                                  _openPaletteSheet,
                                ),
                              ),
                              _SettingsRowItem(
                                icon: Icons.font_download_outlined,
                                title: 'Font style',
                                subtitle: 'Inter (System Sans)',
                                onTap: () => _openSection(
                                  _DesktopSettingsSection.fontStyle,
                                  _openFontStyleSheet,
                                ),
                              ),
                            ],
                          ),

                          const SizedBox(height: 14),

                          // 6. Group 4: Clear Conversation History
                          _SettingsGroupCard(
                            items: [
                              _SettingsRowItem(
                                icon: Icons.delete_outline_rounded,
                                title: 'Clear conversation history',
                                subtitle:
                                    '$sessionCount saved session(s) on this device',
                                iconColor: MatteColors.statusDanger,
                                titleColor: MatteColors.statusDanger,
                                onTap: _confirmAndClearHistory,
                              ),
                            ],
                          ),

                          const SizedBox(height: 24),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}

class _DesktopMetricCard extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final String sublabel;

  const _DesktopMetricCard({
    required this.icon,
    required this.label,
    required this.value,
    required this.sublabel,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: MatteTheme.panelDecoration(borderRadius: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(icon, size: 16, color: MatteColors.nodePerson),
              const SizedBox(width: 7),
              Expanded(
                child: Text(
                  label,
                  style: const TextStyle(
                    color: MatteColors.textMuted,
                    fontSize: 10.5,
                    fontWeight: FontWeight.w600,
                    letterSpacing: 0.6,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            value,
            style: const TextStyle(
              color: MatteColors.textPrimary,
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
            overflow: TextOverflow.ellipsis,
          ),
          const SizedBox(height: 3),
          Text(
            sublabel,
            style: const TextStyle(
              color: MatteColors.textSecondary,
              fontSize: 12,
            ),
            overflow: TextOverflow.ellipsis,
          ),
        ],
      ),
    );
  }
}

class _SheetHandle extends StatelessWidget {
  const _SheetHandle();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Container(
        width: 36,
        height: 4,
        decoration: BoxDecoration(
          color: MatteColors.borderStrong,
          borderRadius: BorderRadius.circular(2),
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final String label;
  final String value;

  const _InfoRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: MatteColors.textSecondary,
            fontSize: 13,
          ),
        ),
        const SizedBox(width: 12),
        Flexible(
          child: Text(
            value,
            textAlign: TextAlign.right,
            style: const TextStyle(
              color: MatteColors.textPrimary,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ],
    );
  }
}

class _ComingSoonFeatureTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;

  const _ComingSoonFeatureTile({
    required this.icon,
    required this.title,
    required this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: MatteColors.inset,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: MatteColors.borderSubtle, width: 1),
      ),
      child: Row(
        children: [
          Icon(icon, size: 19, color: MatteColors.textMuted),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: MatteColors.textSecondary,
                    fontSize: 13.5,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  subtitle,
                  style: const TextStyle(
                    color: MatteColors.textMuted,
                    fontSize: 11.5,
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
            decoration: BoxDecoration(
              color: MatteColors.panel,
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: MatteColors.borderSubtle, width: 1),
            ),
            child: const Text(
              'Coming Soon',
              style: TextStyle(
                color: MatteColors.textMuted,
                fontSize: 10.5,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Grouped rounded matte card matching the Solid Matte Settings aesthetic.
class _SettingsGroupCard extends StatelessWidget {
  final List<_SettingsRowItem> items;

  const _SettingsGroupCard({required this.items});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: MatteColors.panel,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: MatteColors.borderSubtle,
          width: 1,
        ),
      ),
      child: Column(
        children: [
          for (int i = 0; i < items.length; i++) ...[
            if (i > 0)
              const Divider(
                height: 1,
                thickness: 1,
                color: MatteColors.borderSubtle,
              ),
            items[i],
          ],
        ],
      ),
    );
  }
}

/// Individual row inside a [_SettingsGroupCard] with clean vertical centering and chevron.
class _SettingsRowItem extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? subtitle;
  final Widget? trailing;
  final Color? iconColor;
  final Color? titleColor;
  final VoidCallback? onTap;

  const _SettingsRowItem({
    required this.icon,
    required this.title,
    this.subtitle,
    this.trailing,
    this.iconColor,
    this.titleColor,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 15),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Icon(
              icon,
              size: 21,
              color: iconColor ?? MatteColors.textPrimary,
            ),
            const SizedBox(width: 15),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      color: titleColor ?? MatteColors.textPrimary,
                      fontSize: 15,
                      fontWeight: FontWeight.w500,
                      height: 1.2,
                    ),
                  ),
                  if (subtitle != null && subtitle!.isNotEmpty) ...[
                    const SizedBox(height: 3),
                    Text(
                      subtitle!,
                      style: const TextStyle(
                        color: MatteColors.textSecondary,
                        fontSize: 12.5,
                        height: 1.25,
                      ),
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ],
                ],
              ),
            ),
            if (trailing != null) ...[
              const SizedBox(width: 10),
              trailing!,
            ] else ...[
              const SizedBox(width: 8),
              const Icon(
                Icons.chevron_right_rounded,
                size: 18,
                color: MatteColors.textMuted,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _WhitePillButton extends StatelessWidget {
  final String label;
  final VoidCallback? onTap;

  const _WhitePillButton({
    required this.label,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(24),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 9),
        decoration: BoxDecoration(
          color: MatteColors.textPrimary,
          borderRadius: BorderRadius.circular(24),
        ),
        child: Text(
          label,
          style: const TextStyle(
            color: MatteColors.canvas,
            fontSize: 13.5,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }
}

class _OutlinePillButton extends StatelessWidget {
  final String label;
  final VoidCallback? onTap;

  const _OutlinePillButton({
    required this.label,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(24),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 9),
        decoration: BoxDecoration(
          color: MatteColors.inset,
          borderRadius: BorderRadius.circular(24),
          border: Border.all(
            color: MatteColors.borderStrong,
            width: 1,
          ),
        ),
        child: Text(
          label,
          style: const TextStyle(
            color: MatteColors.textPrimary,
            fontSize: 13.5,
            fontWeight: FontWeight.w500,
          ),
        ),
      ),
    );
  }
}
