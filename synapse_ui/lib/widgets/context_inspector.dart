import 'package:flutter/material.dart';

import '../models/message.dart';
import '../theme/matte_theme.dart';

/// Collapsible "Retrieved Context" accordion card above assistant responses
/// whenever `use_rag: true`. Displays retrieved ChromaDB vector chunks and
/// NetworkX graph triples.
class ContextInspector extends StatefulWidget {
  final RetrievedContext? contextData;
  final bool isStreaming;
  final bool contextReceived;

  const ContextInspector({
    super.key,
    required this.contextData,
    this.isStreaming = false,
    this.contextReceived = false,
  });

  @override
  State<ContextInspector> createState() => _ContextInspectorState();
}

class _ContextInspectorState extends State<ContextInspector> {
  bool _isExpanded = false;

  @override
  Widget build(BuildContext context) {
    final data = widget.contextData;
    final chunks = data?.chunks ?? const [];
    final triples = data?.graphTriples ?? const [];
    final total = chunks.length + triples.length;

    String summaryLabel;
    if (!widget.contextReceived && widget.isStreaming) {
      summaryLabel = 'Retrieving hybrid RAG context (ChromaDB + NetworkX)...';
    } else if (total == 0) {
      summaryLabel = 'Hybrid RAG Checked · 0 local sources matched';
    } else {
      summaryLabel =
          'Retrieved Context · ${chunks.length} Vector Chunks · ${triples.length} Graph Relations';
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: MatteColors.panel,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(
          color: _isExpanded
              ? MatteColors.borderStrong
              : MatteColors.borderSubtle,
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Accordion Header
          InkWell(
            onTap: () => setState(() => _isExpanded = !_isExpanded),
            borderRadius: BorderRadius.circular(6),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              child: Row(
                children: [
                  Container(
                    width: 6,
                    height: 6,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: total > 0
                          ? MatteColors.nodeProject
                          : MatteColors.textMuted,
                    ),
                  ),
                  const SizedBox(width: 8),
                  const Icon(
                    Icons.layers_outlined,
                    size: 14,
                    color: MatteColors.textSecondary,
                  ),
                  const SizedBox(width: 7),
                  Expanded(
                    child: Text(
                      summaryLabel,
                      style: const TextStyle(
                        color: MatteColors.textSecondary,
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ),
                  if (total > 0)
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 6,
                        vertical: 1.5,
                      ),
                      margin: const EdgeInsets.only(right: 6),
                      decoration: BoxDecoration(
                        color: MatteColors.inset,
                        borderRadius: BorderRadius.circular(4),
                        border: Border.all(
                          color: MatteColors.borderSubtle,
                          width: 1,
                        ),
                      ),
                      child: Text(
                        '$total sources',
                        style: const TextStyle(
                          color: MatteColors.textMuted,
                          fontSize: 10.5,
                        ),
                      ),
                    ),
                  Icon(
                    _isExpanded
                        ? Icons.keyboard_arrow_up_rounded
                        : Icons.keyboard_arrow_down_rounded,
                    size: 16,
                    color: MatteColors.textMuted,
                  ),
                ],
              ),
            ),
          ),

          // Expanded Inspector Content
          if (_isExpanded) ...[
            const Divider(height: 1, color: MatteColors.borderSubtle),
            Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // 1. NetworkX Knowledge Graph Relations
                  Row(
                    children: [
                      const Icon(
                        Icons.account_tree_outlined,
                        size: 13,
                        color: MatteColors.nodePerson,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        'NETWORKX GRAPH RELATIONS (${triples.length})',
                        style: const TextStyle(
                          color: MatteColors.textMuted,
                          fontSize: 10.5,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  if (triples.isEmpty)
                    const Padding(
                      padding: EdgeInsets.only(bottom: 10),
                      child: Text(
                        'No direct entity triples matched in the local graph store.',
                        style: TextStyle(
                          color: MatteColors.textMuted,
                          fontSize: 12,
                        ),
                      ),
                    )
                  else
                    Padding(
                      padding: const EdgeInsets.only(bottom: 12),
                      child: Wrap(
                        spacing: 6,
                        runSpacing: 6,
                        children: triples
                            .map((triple) => _GraphTripleChip(triple: triple))
                            .toList(),
                      ),
                    ),

                  // 2. ChromaDB Vector Document Chunks
                  Row(
                    children: [
                      const Icon(
                        Icons.description_outlined,
                        size: 13,
                        color: MatteColors.nodeEmail,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        'CHROMADB VECTOR CHUNKS (${chunks.length})',
                        style: const TextStyle(
                          color: MatteColors.textMuted,
                          fontSize: 10.5,
                          fontWeight: FontWeight.w600,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 6),
                  if (chunks.isEmpty)
                    const Text(
                      'No vector chunks returned for this query.',
                      style: TextStyle(
                        color: MatteColors.textMuted,
                        fontSize: 12,
                      ),
                    )
                  else
                    ...chunks.asMap().entries.map(
                          (entry) => _ChunkCard(
                            index: entry.key + 1,
                            chunk: entry.value,
                          ),
                        ),
                ],
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _GraphTripleChip extends StatelessWidget {
  final GraphTriple triple;

  const _GraphTripleChip({required this.triple});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
      decoration: BoxDecoration(
        color: MatteColors.inset,
        borderRadius: BorderRadius.circular(5),
        border: Border.all(color: MatteColors.borderSubtle, width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Flexible(
            child: Text(
              triple.source,
              style: const TextStyle(
                color: MatteColors.nodePerson,
                fontSize: 11.5,
                fontWeight: FontWeight.w500,
              ),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (triple.target.isNotEmpty) ...[
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 6),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
                decoration: BoxDecoration(
                  color: MatteColors.panel,
                  borderRadius: BorderRadius.circular(3),
                  border: Border.all(color: MatteColors.borderSubtle, width: 1),
                ),
                child: Text(
                  triple.relation,
                  style: const TextStyle(
                    color: MatteColors.textMuted,
                    fontSize: 9.5,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ),
            Flexible(
              child: Text(
                triple.target,
                style: const TextStyle(
                  color: MatteColors.nodeEmail,
                  fontSize: 11.5,
                  fontWeight: FontWeight.w500,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _ChunkCard extends StatelessWidget {
  final int index;
  final RagChunk chunk;

  const _ChunkCard({
    required this.index,
    required this.chunk,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 6),
      padding: const EdgeInsets.all(10),
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
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 5, vertical: 1),
                decoration: BoxDecoration(
                  color: MatteColors.panel,
                  borderRadius: BorderRadius.circular(3),
                  border: Border.all(color: MatteColors.borderSubtle, width: 1),
                ),
                child: Text(
                  '#$index · ${chunk.source.toUpperCase()}',
                  style: const TextStyle(
                    color: MatteColors.nodeEmail,
                    fontSize: 10,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
              if (chunk.subject.isNotEmpty) ...[
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    chunk.subject,
                    style: const TextStyle(
                      color: MatteColors.textSecondary,
                      fontSize: 11.5,
                      fontWeight: FontWeight.w500,
                    ),
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: 6),
          Text(
            chunk.content,
            style: const TextStyle(
              color: MatteColors.textSecondary,
              fontSize: 12,
              height: 1.45,
            ),
          ),
        ],
      ),
    );
  }
}
