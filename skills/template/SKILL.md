---
name: custom-skill-template
description: Standardized template for authoring high-performance agent skills in the Synapse framework.
tags: [template, agent-skill, custom-guidelines]
tools: []
metadata:
  author: Your Name
  version: 1.0.0
---

# Custom Skill Template

This template defines the operational rules, domain knowledge, and behavioral guidelines for an autonomous agent capability within Synapse.

## Skill Overview
Provide a concise 1-2 sentence description of what this skill accomplishes and the problems it solves.

## Activation Criteria
List the conditions, keywords, or user intents that trigger this skill:
- Trigger pattern 1 (e.g., questions about database optimization)
- Trigger pattern 2 (e.g., requests to review pull requests)

## Operational Protocol
1. **Analyze Input**: Identify user intent, extract key parameters, and check if external tools are needed.
2. **Retrieve Context**: Use Synapse Hybrid RAG to pull relevant document chunks and knowledge graph triples.
3. **Execute Tool Calls**: If fresh external data is required, call associated connector tools safely.
4. **Synthesize & Cite**: Ground all generated answers in retrieved facts and cite document sources.

## Output Formatting Guidelines
- Use clean Markdown with headers, bullet points, and code fences.
- Maintain an executive, actionable, and objective tone.
- Avoid unsubstantiated speculation when source facts are absent.

## Few-Shot Examples

### Example 1
**User:** What are the key indexing strategies for time-series tables?
**Assistant:** 
1. Use composite indexes with the partition key and timestamp column.
2. Consider BRIN (Block Range Index) for append-only append streams to save 90%+ RAM.
