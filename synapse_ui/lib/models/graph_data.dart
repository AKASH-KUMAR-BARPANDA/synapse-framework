import 'dart:ui';

/// Represents a node in the NetworkX Knowledge Graph (`GET /graph/data`).
class GraphNode {
  final String id;
  final String label;
  final String type;
  final String colorHex;
  final int degree;
  final Map<String, dynamic> metadata;

  // Mutable layout coordinates for interactive force-directed canvas
  Offset position;
  Offset velocity;
  bool isPinned;

  GraphNode({
    required this.id,
    required this.label,
    required this.type,
    required this.colorHex,
    required this.degree,
    this.metadata = const {},
    this.position = Offset.zero,
    this.velocity = Offset.zero,
    this.isPinned = false,
  });

  factory GraphNode.fromJson(Map<String, dynamic> json) {
    final id = (json['id'] ?? json['name'] ?? '').toString();
    final label = (json['label'] ?? json['name'] ?? id).toString();
    final type = (json['type'] ?? 'Default').toString();
    final colorHex = (json['color'] ?? '#71717a').toString();
    final degree =
        (json['degree'] as num?)?.toInt() ?? (json['val'] as num?)?.toInt() ?? 1;
    final meta = json['metadata'] is Map
        ? Map<String, dynamic>.from(json['metadata'] as Map)
        : <String, dynamic>{};

    return GraphNode(
      id: id,
      label: label,
      type: type,
      colorHex: colorHex,
      degree: degree,
      metadata: meta,
    );
  }
}

/// Represents a directed edge in the NetworkX Knowledge Graph (`GET /graph/data`).
class GraphLink {
  final String source;
  final String target;
  final String relation;
  final Map<String, dynamic> metadata;

  const GraphLink({
    required this.source,
    required this.target,
    required this.relation,
    this.metadata = const {},
  });

  factory GraphLink.fromJson(Map<String, dynamic> json) {
    final meta = json['metadata'] is Map
        ? Map<String, dynamic>.from(json['metadata'] as Map)
        : <String, dynamic>{};

    return GraphLink(
      source: (json['source'] ?? '').toString(),
      target: (json['target'] ?? '').toString(),
      relation: (json['relation'] ?? 'RELATED').toString(),
      metadata: meta,
    );
  }
}

/// Summary statistics for the Knowledge Graph.
class GraphStats {
  final int totalNodes;
  final int totalEdges;

  const GraphStats({
    this.totalNodes = 0,
    this.totalEdges = 0,
  });

  factory GraphStats.fromJson(Map<String, dynamic> json) {
    return GraphStats(
      totalNodes: (json['total_nodes'] as num?)?.toInt() ?? 0,
      totalEdges: (json['total_edges'] as num?)?.toInt() ?? 0,
    );
  }
}

/// Full payload returned by `GET /graph/data`.
class GraphData {
  final List<GraphNode> nodes;
  final List<GraphLink> links;
  final GraphStats stats;
  final Map<String, String> palette;

  const GraphData({
    this.nodes = const [],
    this.links = const [],
    this.stats = const GraphStats(),
    this.palette = const {},
  });

  bool get isEmpty => nodes.isEmpty;

  factory GraphData.fromJson(Map<String, dynamic> json) {
    final rawNodes = (json['nodes'] ?? []) as List<dynamic>;
    final rawLinks = (json['links'] ?? json['edges'] ?? []) as List<dynamic>;
    final rawStats = json['stats'] is Map
        ? Map<String, dynamic>.from(json['stats'] as Map)
        : <String, dynamic>{};

    final tokens = json['tokens'] is Map
        ? Map<String, dynamic>.from(json['tokens'] as Map)
        : <String, dynamic>{};
    final rawPalette = tokens['palette'] is Map
        ? Map<String, dynamic>.from(tokens['palette'] as Map)
        : <String, dynamic>{};

    final nodes = rawNodes
        .whereType<Map>()
        .map((n) => GraphNode.fromJson(Map<String, dynamic>.from(n)))
        .toList();

    final links = rawLinks
        .whereType<Map>()
        .map((l) => GraphLink.fromJson(Map<String, dynamic>.from(l)))
        .toList();

    return GraphData(
      nodes: nodes,
      links: links,
      stats: rawStats.isNotEmpty
          ? GraphStats.fromJson(rawStats)
          : GraphStats(totalNodes: nodes.length, totalEdges: links.length),
      palette: rawPalette.map((k, v) => MapEntry(k, v.toString())),
    );
  }
}
