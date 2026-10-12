import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/scheduler.dart';

import '../models/graph_data.dart';
import '../services/api_service.dart';
import '../theme/matte_theme.dart';

/// Interactive Knowledge Graph Visualizer (`/graph`) fetching data from `GET /graph/data`.
/// Supports force-directed physics layout, pinch-to-zoom, pan, node dragging,
/// search filtering, palette switching, and tap-on-node entity inspector.
class GraphScreen extends StatefulWidget {
  final ApiService apiService;

  const GraphScreen({
    super.key,
    required this.apiService,
  });

  @override
  State<GraphScreen> createState() => _GraphScreenState();
}

class _GraphScreenState extends State<GraphScreen>
    with SingleTickerProviderStateMixin {
  static const Size _virtualCanvasSize = Size(2200, 1600);
  static const Offset _canvasCenter = Offset(1100, 800);

  final TransformationController _transformController =
      TransformationController();
  final TextEditingController _searchController = TextEditingController();

  late final Ticker _physicsTicker;
  GraphData _graphData = const GraphData();
  final Map<String, GraphNode> _nodeById = {};

  bool _isLoading = true;
  String? _errorMessage;
  String _searchQuery = '';
  String _selectedTypeFilter = 'All';
  GraphNode? _selectedNode;
  GraphNode? _draggedNode;
  int _simulationStep = 0;
  static const int _maxSimulationSteps = 240;

  @override
  void initState() {
    super.initState();
    _physicsTicker = createTicker(_onPhysicsTick);
    _loadGraph();
  }

  @override
  void dispose() {
    _physicsTicker.dispose();
    _transformController.dispose();
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _loadGraph() async {
    setState(() {
      _isLoading = true;
      _errorMessage = null;
    });

    try {
      final data = await widget.apiService.fetchGraphData();
      if (!mounted) return;

      _initializeNodePositions(data);
      setState(() {
        _graphData = data;
        _isLoading = false;
        if (_selectedNode != null) {
          _selectedNode = _nodeById[_selectedNode!.id];
        }
      });

      WidgetsBinding.instance.addPostFrameCallback((_) {
        _centerViewport();
      });

      _restartPhysicsSimulation();
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
        _errorMessage = e.toString();
      });
    }
  }

  void _initializeNodePositions(GraphData data) {
    _nodeById.clear();
    final count = data.nodes.length;
    if (count == 0) return;

    final radius = math.min(340.0, math.max(140.0, count * 14.0));
    for (int i = 0; i < count; i++) {
      final node = data.nodes[i];
      final angle = (2 * math.pi * i) / count;
      // Golden-angle spiral offset so nodes don't stack on a single ring
      final ringFactor = 0.35 + 0.65 * ((i % 5) / 4.0);
      node.position = Offset(
        _canvasCenter.dx + math.cos(angle) * radius * ringFactor,
        _canvasCenter.dy + math.sin(angle) * radius * ringFactor,
      );
      node.velocity = Offset.zero;
      _nodeById[node.id] = node;
    }
  }

  void _restartPhysicsSimulation() {
    _simulationStep = 0;
    if (!_physicsTicker.isActive && _graphData.nodes.length > 1) {
      _physicsTicker.start();
    }
  }

  void _onPhysicsTick(Duration elapsed) {
    if (!mounted || _graphData.nodes.isEmpty) {
      _physicsTicker.stop();
      return;
    }

    if (_simulationStep >= _maxSimulationSteps && _draggedNode == null) {
      _physicsTicker.stop();
      return;
    }

    _simulationStep++;
    final nodes = _graphData.nodes;
    final links = _graphData.links;
    final n = nodes.length;

    const double repulsionStrength = 6200.0;
    const double springStiffness = 0.032;
    const double idealEdgeLength = 155.0;
    const double centerGravity = 0.012;
    const double damping = 0.80;

    final forces = List<Offset>.filled(n, Offset.zero);

    // 1. All-pairs Coulomb repulsion
    for (int i = 0; i < n; i++) {
      for (int j = i + 1; j < n; j++) {
        final delta = nodes[i].position - nodes[j].position;
        final distSq = math.max(64.0, delta.distanceSquared);
        final dist = math.sqrt(distSq);
        final forceMag = repulsionStrength / distSq;
        final unit = delta / dist;
        final f = unit * forceMag;
        forces[i] += f;
        forces[j] -= f;
      }
    }

    // 2. Hooke spring attraction along directed edges
    final indexById = <String, int>{};
    for (int i = 0; i < n; i++) {
      indexById[nodes[i].id] = i;
    }

    for (final link in links) {
      final srcIdx = indexById[link.source];
      final tgtIdx = indexById[link.target];
      if (srcIdx == null || tgtIdx == null || srcIdx == tgtIdx) continue;

      final delta = nodes[tgtIdx].position - nodes[srcIdx].position;
      final dist = math.max(1.0, delta.distance);
      final displacement = dist - idealEdgeLength;
      final springForce = (delta / dist) * (displacement * springStiffness);

      forces[srcIdx] += springForce;
      forces[tgtIdx] -= springForce;
    }

    // 3. Gentle pull toward canvas center & velocity integration
    for (int i = 0; i < n; i++) {
      final node = nodes[i];
      if (node.isPinned || node == _draggedNode) continue;

      final toCenter = _canvasCenter - node.position;
      final totalForce = forces[i] + (toCenter * centerGravity);

      var vel = (node.velocity + totalForce) * damping;
      if (vel.distance > 18.0) {
        vel = (vel / vel.distance) * 18.0;
      }
      node.velocity = vel;
      node.position = Offset(
        (node.position.dx + vel.dx).clamp(100.0, _virtualCanvasSize.width - 100.0),
        (node.position.dy + vel.dy).clamp(100.0, _virtualCanvasSize.height - 100.0),
      );
    }

    setState(() {});
  }

  void _centerViewport() {
    if (!mounted) return;
    final renderBox = context.findRenderObject() as RenderBox?;
    if (renderBox == null || !renderBox.hasSize) return;
    final viewSize = renderBox.size;

    const initialScale = 0.85;
    final tx = (viewSize.width / 2) - (_canvasCenter.dx * initialScale);
    final ty = (viewSize.height / 2) - (_canvasCenter.dy * initialScale);

    final matrix = Matrix4.identity()
      ..translateByDouble(tx, ty, 0.0, 1.0)
      ..scaleByDouble(initialScale, initialScale, 1.0, 1.0);
    _transformController.value = matrix;
  }

  void _zoomBy(double factor) {
    final currentMatrix = _transformController.value.clone();
    final currentScale = currentMatrix.getMaxScaleOnAxis();
    final targetScale = (currentScale * factor).clamp(0.28, 3.0);
    final effectiveFactor = targetScale / currentScale;

    final renderBox = context.findRenderObject() as RenderBox?;
    final focal = renderBox != null && renderBox.hasSize
        ? Offset(renderBox.size.width / 2, renderBox.size.height / 2)
        : const Offset(400, 300);

    final sceneFocal = _transformController.toScene(focal);
    currentMatrix
      ..translateByDouble(sceneFocal.dx, sceneFocal.dy, 0.0, 1.0)
      ..scaleByDouble(effectiveFactor, effectiveFactor, 1.0, 1.0)
      ..translateByDouble(-sceneFocal.dx, -sceneFocal.dy, 0.0, 1.0);

    setState(() {
      _transformController.value = currentMatrix;
    });
  }

  void _focusOnNode(GraphNode node) {
    setState(() => _selectedNode = node);
    final renderBox = context.findRenderObject() as RenderBox?;
    if (renderBox == null || !renderBox.hasSize) return;
    final viewSize = renderBox.size;

    const targetScale = 1.15;
    final tx = (viewSize.width / 2) - (node.position.dx * targetScale);
    final ty = (viewSize.height / 2) - (node.position.dy * targetScale);

    final matrix = Matrix4.identity()
      ..translateByDouble(tx, ty, 0.0, 1.0)
      ..scaleByDouble(targetScale, targetScale, 1.0, 1.0);
    _transformController.value = matrix;
  }

  GraphNode? _hitTestNode(Offset localViewportPosition) {
    final scenePoint = _transformController.toScene(localViewportPosition);
    for (final node in _graphData.nodes.reversed) {
      if (!_isNodeVisible(node)) continue;
      final hitRadius = _nodeRadius(node) + 10.0;
      if ((node.position - scenePoint).distance <= hitRadius) {
        return node;
      }
    }
    return null;
  }

  double _nodeRadius(GraphNode node) {
    return math.max(9.0, math.min(22.0, 8.0 + node.degree * 2.2));
  }

  bool _isNodeVisible(GraphNode node) {
    if (_selectedTypeFilter != 'All' &&
        node.type.toLowerCase() != _selectedTypeFilter.toLowerCase()) {
      return false;
    }
    return true;
  }

  @override
  Widget build(BuildContext context) {
    final isMobile = MatteBreakpoints.isMobile(context);
    final paletteName = widget.apiService.graphPalette;

    return Container(
      color: MatteColors.canvas,
      child: Stack(
        children: [
          // 1. Interactive Force-Directed Graph Viewport
          if (_isLoading)
            const Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SizedBox(
                    width: 22,
                    height: 22,
                    child: CircularProgressIndicator(
                      strokeWidth: 2,
                      color: MatteColors.nodePerson,
                    ),
                  ),
                  SizedBox(height: 12),
                  Text(
                    'Loading NetworkX Knowledge Graph...',
                    style: TextStyle(
                      color: MatteColors.textSecondary,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            )
          else if (_errorMessage != null)
            _buildErrorView()
          else if (_graphData.isEmpty)
            _buildEmptyGraphView()
          else
            Positioned.fill(
              child: GestureDetector(
                behavior: HitTestBehavior.opaque,
                onTapUp: (details) {
                  final hit = _hitTestNode(details.localPosition);
                  setState(() => _selectedNode = hit);
                },
                child: InteractiveViewer(
                  transformationController: _transformController,
                  constrained: false,
                  boundaryMargin: const EdgeInsets.all(900),
                  minScale: 0.25,
                  maxScale: 3.0,
                  child: GestureDetector(
                    onPanStart: (details) {
                      for (final node in _graphData.nodes.reversed) {
                        if ((node.position - details.localPosition).distance <=
                            _nodeRadius(node) + 12.0) {
                          setState(() {
                            _draggedNode = node;
                            _selectedNode = node;
                          });
                          break;
                        }
                      }
                    },
                    onPanUpdate: (details) {
                      if (_draggedNode != null) {
                        setState(() {
                          _draggedNode!.position += details.delta;
                        });
                        if (!_physicsTicker.isActive) {
                          _simulationStep = _maxSimulationSteps - 35;
                          _physicsTicker.start();
                        }
                      }
                    },
                    onPanEnd: (_) {
                      setState(() => _draggedNode = null);
                    },
                    child: SizedBox(
                      width: _virtualCanvasSize.width,
                      height: _virtualCanvasSize.height,
                      child: CustomPaint(
                        painter: _KnowledgeGraphPainter(
                          nodes: _graphData.nodes,
                          links: _graphData.links,
                          nodeById: _nodeById,
                          selectedNode: _selectedNode,
                          paletteName: paletteName,
                          searchQuery: _searchQuery,
                          selectedTypeFilter: _selectedTypeFilter,
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ),

          // 2. Top Floating HUD Controls (Title, Search, Palette, Refresh)
          Positioned(
            top: 14,
            left: 14,
            right: _selectedNode != null && !isMobile ? 334 : 14,
            child: _buildTopHud(isMobile, paletteName),
          ),

          // 3. Bottom-Left Entity Type Legend & Filter Bar
          Positioned(
            bottom: 14,
            left: 14,
            right: isMobile ? 70 : null,
            child: _buildLegendBar(paletteName),
          ),

          // 4. Bottom-Right Zoom & Layout Controls
          Positioned(
            bottom: 14,
            right: _selectedNode != null && !isMobile ? 334 : 14,
            child: _buildZoomControls(),
          ),

          // 5. Selected Node Entity Inspector Panel (Desktop Right Panel / Mobile Bottom Sheet)
          if (_selectedNode != null)
            if (isMobile)
              Positioned(
                left: 12,
                right: 12,
                bottom: 64,
                child: _buildNodeInspectorCard(
                  _selectedNode!,
                  paletteName,
                  isMobile: true,
                ),
              )
            else
              Positioned(
                top: 0,
                bottom: 0,
                right: 0,
                width: 320,
                child: _buildNodeInspectorCard(
                  _selectedNode!,
                  paletteName,
                  isMobile: false,
                ),
              ),
        ],
      ),
    );
  }

  Widget _buildTopHud(bool isMobile, String paletteName) {
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      alignment: WrapAlignment.spaceBetween,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        // Stats Badge
        Container(
          height: 36,
          padding: const EdgeInsets.symmetric(horizontal: 12),
          decoration: MatteTheme.panelDecoration(borderRadius: 6),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 7,
                height: 7,
                decoration: const BoxDecoration(
                  color: MatteColors.nodeProject,
                  shape: BoxShape.circle,
                ),
              ),
              const SizedBox(width: 8),
              const Text(
                'Synapse Graph',
                style: TextStyle(
                  color: MatteColors.textPrimary,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(width: 8),
              Text(
                '${_graphData.stats.totalNodes} nodes · ${_graphData.stats.totalEdges} edges',
                style: const TextStyle(
                  color: MatteColors.textMuted,
                  fontSize: 12,
                ),
              ),
            ],
          ),
        ),

        // Search + Palette Selector + Refresh
        Wrap(
          spacing: 8,
          runSpacing: 8,
          crossAxisAlignment: WrapCrossAlignment.center,
          children: [
            // Search Input
            Container(
              width: isMobile ? 175 : 210,
              height: 36,
              padding: const EdgeInsets.symmetric(horizontal: 10),
              decoration: MatteTheme.panelDecoration(borderRadius: 6),
              child: Row(
                children: [
                  const Icon(
                    Icons.search_rounded,
                    size: 15,
                    color: MatteColors.textMuted,
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: TextField(
                      controller: _searchController,
                      onChanged: (val) =>
                          setState(() => _searchQuery = val.trim()),
                      onSubmitted: (val) {
                        final q = val.trim().toLowerCase();
                        if (q.isEmpty) return;
                        for (final n in _graphData.nodes) {
                          if (n.label.toLowerCase().contains(q)) {
                            _focusOnNode(n);
                            break;
                          }
                        }
                      },
                      style: const TextStyle(
                        color: MatteColors.textPrimary,
                        fontSize: 12.5,
                      ),
                      decoration: const InputDecoration(
                        hintText: 'Find entity...',
                        border: InputBorder.none,
                        enabledBorder: InputBorder.none,
                        focusedBorder: InputBorder.none,
                        filled: false,
                        contentPadding: EdgeInsets.zero,
                        isDense: true,
                      ),
                    ),
                  ),
                  if (_searchQuery.isNotEmpty)
                    InkWell(
                      onTap: () {
                        _searchController.clear();
                        setState(() => _searchQuery = '');
                      },
                      child: const Icon(
                        Icons.close_rounded,
                        size: 14,
                        color: MatteColors.textMuted,
                      ),
                    ),
                ],
              ),
            ),

            // Palette Dropdown (`zinc`, `stone`, `basalt`)
            Container(
              height: 36,
              padding: const EdgeInsets.symmetric(horizontal: 10),
              decoration: MatteTheme.panelDecoration(borderRadius: 6),
              child: DropdownButtonHideUnderline(
                child: DropdownButton<String>(
                  value: paletteName,
                  dropdownColor: MatteColors.panel,
                  style: const TextStyle(
                    color: MatteColors.textSecondary,
                    fontSize: 12,
                  ),
                  items: const [
                    DropdownMenuItem(
                      value: 'zinc',
                      child: Text('Zinc (Linear)'),
                    ),
                    DropdownMenuItem(
                      value: 'stone',
                      child: Text('Stone (Anthropic)'),
                    ),
                    DropdownMenuItem(
                      value: 'basalt',
                      child: Text('Basalt (Slate)'),
                    ),
                  ],
                  onChanged: (val) {
                    if (val != null) {
                      widget.apiService.updateSettings(graphPalette: val);
                    }
                  },
                ),
              ),
            ),

            // Refresh Graph Button
            InkWell(
              onTap: _loadGraph,
              borderRadius: BorderRadius.circular(6),
              child: Container(
                height: 36,
                padding: const EdgeInsets.symmetric(horizontal: 10),
                decoration: MatteTheme.panelDecoration(borderRadius: 6),
                child: const Icon(
                  Icons.refresh_rounded,
                  size: 16,
                  color: MatteColors.textSecondary,
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }

  Widget _buildLegendBar(String paletteName) {
    const types = ['All', 'Person', 'Email', 'Project', 'Tool', 'Topic'];

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: MatteTheme.panelDecoration(borderRadius: 6),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: types.map((type) {
            final isSelected = _selectedTypeFilter == type;
            final color = type == 'All'
                ? MatteColors.textPrimary
                : MatteColors.colorForNodeType(type, palette: paletteName);

            return Padding(
              padding: const EdgeInsets.only(right: 6),
              child: InkWell(
                onTap: () => setState(() => _selectedTypeFilter = type),
                borderRadius: BorderRadius.circular(4),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 4,
                  ),
                  decoration: BoxDecoration(
                    color: isSelected
                        ? MatteColors.panelHover
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(4),
                    border: Border.all(
                      color: isSelected
                          ? MatteColors.borderStrong
                          : Colors.transparent,
                      width: 1,
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      if (type != 'All') ...[
                        Container(
                          width: 7,
                          height: 7,
                          decoration: BoxDecoration(
                            color: color,
                            borderRadius: BorderRadius.circular(2),
                          ),
                        ),
                        const SizedBox(width: 6),
                      ],
                      Text(
                        type,
                        style: TextStyle(
                          color: isSelected
                              ? MatteColors.textPrimary
                              : MatteColors.textSecondary,
                          fontSize: 11.5,
                          fontWeight:
                              isSelected ? FontWeight.w600 : FontWeight.w400,
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
    );
  }

  Widget _buildZoomControls() {
    return Container(
      decoration: MatteTheme.panelDecoration(borderRadius: 6),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          _ZoomIconButton(
            icon: Icons.add_rounded,
            tooltip: 'Zoom in',
            onTap: () => _zoomBy(1.22),
          ),
          const Divider(height: 1, color: MatteColors.borderSubtle),
          _ZoomIconButton(
            icon: Icons.remove_rounded,
            tooltip: 'Zoom out',
            onTap: () => _zoomBy(0.82),
          ),
          const Divider(height: 1, color: MatteColors.borderSubtle),
          _ZoomIconButton(
            icon: Icons.center_focus_strong_outlined,
            tooltip: 'Center viewport',
            onTap: _centerViewport,
          ),
          const Divider(height: 1, color: MatteColors.borderSubtle),
          _ZoomIconButton(
            icon: Icons.auto_fix_high_outlined,
            tooltip: 'Re-layout force simulation',
            onTap: () {
              _initializeNodePositions(_graphData);
              _restartPhysicsSimulation();
            },
          ),
        ],
      ),
    );
  }

  Widget _buildNodeInspectorCard(
    GraphNode node,
    String paletteName, {
    required bool isMobile,
  }) {
    final nodeColor =
        MatteColors.colorForNodeType(node.type, palette: paletteName);

    final outgoing =
        _graphData.links.where((l) => l.source == node.id).toList();
    final incoming =
        _graphData.links.where((l) => l.target == node.id).toList();

    return Container(
      constraints: isMobile ? const BoxConstraints(maxHeight: 280) : null,
      decoration: BoxDecoration(
        color: MatteColors.panel,
        borderRadius: isMobile ? BorderRadius.circular(8) : BorderRadius.zero,
        border: isMobile
            ? Border.all(color: MatteColors.borderStrong, width: 1)
            : const Border(
                left: BorderSide(color: MatteColors.borderSubtle, width: 1),
              ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 14, 10, 12),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 10,
                  height: 10,
                  margin: const EdgeInsets.only(top: 5),
                  decoration: BoxDecoration(
                    color: nodeColor,
                    borderRadius: BorderRadius.circular(2.5),
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        node.label,
                        style: const TextStyle(
                          color: MatteColors.textPrimary,
                          fontSize: 14.5,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Wrap(
                        spacing: 6,
                        children: [
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
                              node.type.toUpperCase(),
                              style: TextStyle(
                                color: nodeColor,
                                fontSize: 10,
                                fontWeight: FontWeight.w600,
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
                              'Degree: ${node.degree}',
                              style: const TextStyle(
                                color: MatteColors.textMuted,
                                fontSize: 10,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: () => setState(() => _selectedNode = null),
                  icon: const Icon(
                    Icons.close_rounded,
                    size: 16,
                    color: MatteColors.textMuted,
                  ),
                  visualDensity: VisualDensity.compact,
                ),
              ],
            ),
          ),

          const Divider(height: 1, color: MatteColors.borderSubtle),

          // Connections List
          Expanded(
            child: ListView(
              padding: const EdgeInsets.all(14),
              children: [
                if (outgoing.isNotEmpty) ...[
                  Text(
                    'OUTGOING RELATIONS (${outgoing.length})',
                    style: const TextStyle(
                      color: MatteColors.textMuted,
                      fontSize: 10.5,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(height: 8),
                  ...outgoing.map(
                    (edge) => _buildConnectionTile(
                      relation: edge.relation,
                      neighborId: edge.target,
                      isOutgoing: true,
                      paletteName: paletteName,
                    ),
                  ),
                  const SizedBox(height: 14),
                ],
                if (incoming.isNotEmpty) ...[
                  Text(
                    'INCOMING RELATIONS (${incoming.length})',
                    style: const TextStyle(
                      color: MatteColors.textMuted,
                      fontSize: 10.5,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(height: 8),
                  ...incoming.map(
                    (edge) => _buildConnectionTile(
                      relation: edge.relation,
                      neighborId: edge.source,
                      isOutgoing: false,
                      paletteName: paletteName,
                    ),
                  ),
                ],
                if (outgoing.isEmpty && incoming.isEmpty)
                  const Text(
                    'No connected edges for this node.',
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
    );
  }

  Widget _buildConnectionTile({
    required String relation,
    required String neighborId,
    required bool isOutgoing,
    required String paletteName,
  }) {
    final neighbor = _nodeById[neighborId];
    final neighborColor = MatteColors.colorForNodeType(
      neighbor?.type,
      palette: paletteName,
    );

    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: InkWell(
        onTap: neighbor != null ? () => _focusOnNode(neighbor) : null,
        borderRadius: BorderRadius.circular(5),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
          decoration: BoxDecoration(
            color: MatteColors.inset,
            borderRadius: BorderRadius.circular(5),
            border: Border.all(color: MatteColors.borderSubtle, width: 1),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    isOutgoing
                        ? Icons.arrow_forward_rounded
                        : Icons.arrow_back_rounded,
                    size: 12,
                    color: MatteColors.textMuted,
                  ),
                  const SizedBox(width: 5),
                  Text(
                    relation,
                    style: const TextStyle(
                      color: MatteColors.textMuted,
                      fontSize: 10,
                      fontWeight: FontWeight.w600,
                      letterSpacing: 0.4,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 4),
              Row(
                children: [
                  Container(
                    width: 6,
                    height: 6,
                    decoration: BoxDecoration(
                      color: neighborColor,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 6),
                  Expanded(
                    child: Text(
                      neighborId,
                      style: const TextStyle(
                        color: MatteColors.textPrimary,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildErrorView() {
    return Center(
      child: Container(
        constraints: const BoxConstraints(maxWidth: 420),
        padding: const EdgeInsets.all(20),
        decoration: MatteTheme.panelDecoration(borderRadius: 8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(
              Icons.cloud_off_rounded,
              size: 28,
              color: MatteColors.statusWarning,
            ),
            const SizedBox(height: 10),
            const Text(
              'Unable to Load Knowledge Graph',
              style: TextStyle(
                color: MatteColors.textPrimary,
                fontSize: 15,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              _errorMessage ?? 'Check that FastAPI server is running.',
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: MatteColors.textSecondary,
                fontSize: 12.5,
              ),
            ),
            const SizedBox(height: 14),
            InkWell(
              onTap: _loadGraph,
              borderRadius: BorderRadius.circular(6),
              child: Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 8,
                ),
                decoration: BoxDecoration(
                  color: MatteColors.textPrimary,
                  borderRadius: BorderRadius.circular(6),
                ),
                child: const Text(
                  'Retry Connection',
                  style: TextStyle(
                    color: MatteColors.canvas,
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyGraphView() {
    return const Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.grain_rounded,
            size: 36,
            color: MatteColors.textMuted,
          ),
          SizedBox(height: 10),
          Text(
            'Knowledge Graph is Empty',
            style: TextStyle(
              color: MatteColors.textPrimary,
              fontSize: 15,
              fontWeight: FontWeight.w600,
            ),
          ),
          SizedBox(height: 4),
          Text(
            'Sync Gmail in Connectors to populate entities and relational triples.',
            style: TextStyle(
              color: MatteColors.textMuted,
              fontSize: 12.5,
            ),
          ),
        ],
      ),
    );
  }
}

class _ZoomIconButton extends StatelessWidget {
  final IconData icon;
  final String tooltip;
  final VoidCallback onTap;

  const _ZoomIconButton({
    required this.icon,
    required this.tooltip,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: InkWell(
        onTap: onTap,
        child: SizedBox(
          width: 34,
          height: 34,
          child: Icon(
            icon,
            size: 16,
            color: MatteColors.textSecondary,
          ),
        ),
      ),
    );
  }
}

/// CustomPainter rendering the Solid Matte Knowledge Graph canvas, subtle grid,
/// directed edges with relation labels, and matte entity nodes.
class _KnowledgeGraphPainter extends CustomPainter {
  final List<GraphNode> nodes;
  final List<GraphLink> links;
  final Map<String, GraphNode> nodeById;
  final GraphNode? selectedNode;
  final String paletteName;
  final String searchQuery;
  final String selectedTypeFilter;

  _KnowledgeGraphPainter({
    required this.nodes,
    required this.links,
    required this.nodeById,
    required this.selectedNode,
    required this.paletteName,
    required this.searchQuery,
    required this.selectedTypeFilter,
  });

  bool _isVisible(GraphNode node) {
    if (selectedTypeFilter != 'All' &&
        node.type.toLowerCase() != selectedTypeFilter.toLowerCase()) {
      return false;
    }
    return true;
  }

  bool _matchesQuery(GraphNode node) {
    if (searchQuery.isEmpty) return true;
    final q = searchQuery.toLowerCase();
    return node.label.toLowerCase().contains(q) ||
        node.type.toLowerCase().contains(q);
  }

  double _radiusFor(GraphNode node) {
    return math.max(9.0, math.min(22.0, 8.0 + node.degree * 2.2));
  }

  @override
  void paint(Canvas canvas, Size size) {
    // 1. Subtle Matte Coordinate Dot Grid
    final dotPaint = Paint()
      ..color = MatteColors.borderSubtle.withValues(alpha: 0.45)
      ..style = PaintingStyle.fill;

    const double gridSpacing = 48.0;
    for (double x = 0; x < size.width; x += gridSpacing) {
      for (double y = 0; y < size.height; y += gridSpacing) {
        canvas.drawCircle(Offset(x, y), 1.0, dotPaint);
      }
    }

    // 2. Draw Directed Edges
    final defaultEdgePaint = Paint()
      ..color = MatteColors.borderSubtle
      ..strokeWidth = 1.15
      ..style = PaintingStyle.stroke;

    final highlightedEdgePaint = Paint()
      ..color = MatteColors.textSecondary
      ..strokeWidth = 1.8
      ..style = PaintingStyle.stroke;

    final dimmedEdgePaint = Paint()
      ..color = MatteColors.panel
      ..strokeWidth = 0.8
      ..style = PaintingStyle.stroke;

    for (final link in links) {
      final src = nodeById[link.source];
      final tgt = nodeById[link.target];
      if (src == null || tgt == null) continue;
      if (!_isVisible(src) || !(_isVisible(tgt))) continue;

      final isConnectedToSelected = selectedNode != null &&
          (selectedNode!.id == src.id || selectedNode!.id == tgt.id);

      final isSearchRelevant =
          searchQuery.isEmpty || _matchesQuery(src) || _matchesQuery(tgt);

      final edgePaint = isConnectedToSelected
          ? highlightedEdgePaint
          : (isSearchRelevant ? defaultEdgePaint : dimmedEdgePaint);

      canvas.drawLine(src.position, tgt.position, edgePaint);

      // Draw subtle directional arrow head near target node
      final delta = tgt.position - src.position;
      final dist = delta.distance;
      if (dist > 36) {
        final unit = delta / dist;
        final arrowTip = tgt.position - unit * (_radiusFor(tgt) + 3.0);
        final perp = Offset(-unit.dy, unit.dx);
        final p1 = arrowTip - (unit * 7.0) + (perp * 3.5);
        final p2 = arrowTip - (unit * 7.0) - (perp * 3.5);
        final arrowPath = Path()
          ..moveTo(arrowTip.dx, arrowTip.dy)
          ..lineTo(p1.dx, p1.dy)
          ..lineTo(p2.dx, p2.dy)
          ..close();
        canvas.drawPath(
          arrowPath,
          Paint()
            ..color = edgePaint.color
            ..style = PaintingStyle.fill,
        );

        // Draw relation label if connected to selected node
        if (isConnectedToSelected) {
          final mid = (src.position + tgt.position) / 2;
          final tp = TextPainter(
            text: TextSpan(
              text: link.relation,
              style: const TextStyle(
                color: MatteColors.textSecondary,
                fontSize: 9.5,
                fontWeight: FontWeight.w600,
                backgroundColor: MatteColors.canvas,
              ),
            ),
            textDirection: TextDirection.ltr,
          )..layout();
          tp.paint(canvas, mid - Offset(tp.width / 2, tp.height / 2));
        }
      }
    }

    // 3. Draw Solid Matte Nodes & Labels (Strictly zero artificial glow)
    for (final node in nodes) {
      if (!_isVisible(node)) continue;

      final isSelected = selectedNode?.id == node.id;
      final isMatched = _matchesQuery(node);
      final radius = _radiusFor(node);

      final baseColor =
          MatteColors.colorForNodeType(node.type, palette: paletteName);
      final fillColor = isMatched ? baseColor : MatteColors.panelHover;

      // Solid matte circle fill
      canvas.drawCircle(
        node.position,
        isSelected ? radius + 2.0 : radius,
        Paint()
          ..color = fillColor
          ..style = PaintingStyle.fill,
      );

      // Crisp 1px/2px matte border ring
      canvas.drawCircle(
        node.position,
        isSelected ? radius + 2.0 : radius,
        Paint()
          ..color = isSelected
              ? MatteColors.textPrimary
              : MatteColors.canvas
          ..strokeWidth = isSelected ? 2.0 : 1.5
          ..style = PaintingStyle.stroke,
      );

      // Node Label below circle
      if (isMatched || isSelected) {
        final displayLabel = node.label.length > 34
            ? '${node.label.substring(0, 32)}…'
            : node.label;

        final tp = TextPainter(
          text: TextSpan(
            text: displayLabel,
            style: TextStyle(
              color: isSelected
                  ? MatteColors.textPrimary
                  : MatteColors.textSecondary,
              fontSize: isSelected ? 11.5 : 10.5,
              fontWeight: isSelected ? FontWeight.w600 : FontWeight.w400,
            ),
          ),
          textDirection: TextDirection.ltr,
          maxLines: 1,
        )..layout(maxWidth: 200);

        final labelOffset = Offset(
          node.position.dx - (tp.width / 2),
          node.position.dy + radius + 5.0,
        );

        // Matte pill behind label for legibility
        final bgRect = RRect.fromRectAndRadius(
          Rect.fromLTWH(
            labelOffset.dx - 4,
            labelOffset.dy - 1.5,
            tp.width + 8,
            tp.height + 3,
          ),
          const Radius.circular(3),
        );
        canvas.drawRRect(
          bgRect,
          Paint()..color = MatteColors.canvas.withValues(alpha: 0.85),
        );

        tp.paint(canvas, labelOffset);
      }
    }
  }

  @override
  bool shouldRepaint(covariant _KnowledgeGraphPainter oldDelegate) => true;
}
