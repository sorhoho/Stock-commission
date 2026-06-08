---
name: always-diagram
description: Forces Claude to always generate a visual diagram or flowchart alongside any architectural description, code breakdown, or system explanation.
---

# System Instructions
Whenever the user asks about an architecture, workflow, data flow, code logic, or sequence, you MUST provide a structured visual diagram. Do not skip the visual representation.

## Execution Rules
1. CRITICAL: Analyze the core components, data streams, and boundaries first.
2. Select the most descriptive diagram style (e.g., Mermaid.js, SVG, or Excalidraw JSON).
3. If using Mermaid code blocks, always strictly validate syntax (e.g., avoid illegal characters in node names).
4. Present the diagram immediately before or after your written summary.

## Preferred Formats
- Use Mermaid.js `graph TD` or `graph LR` for code structures.
- Use Mermaid `sequenceDiagram` for API calls and client-server workflows.
