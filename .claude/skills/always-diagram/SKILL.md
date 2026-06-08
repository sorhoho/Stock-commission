---
name: always-diagram
description: >
  Forces Claude to always produce an Excalidraw JSON diagram alongside any
  architectural description, code breakdown, data-flow, or sequence explanation.
  The JSON can be pasted directly into https://excalidraw.com (File → Open → paste).
---

# Always-Diagram — Excalidraw Edition

Whenever the user asks about an architecture, workflow, data flow, code logic,
or sequence you **MUST** produce a valid Excalidraw JSON scene.  Never skip it.

---

## Rules

1. **Analyse first** — identify components, boundaries, and data-flow direction.
2. **Choose layout** — left-to-right (`graph LR`) for pipelines; top-to-bottom
   (`graph TD`) for hierarchies; sequence lanes for API flows.
3. **Output the diagram first**, then the written summary below it.
4. **Always wrap the JSON in a fenced code block** labelled `json`.
5. **After the JSON**, include one sentence: *"Paste into https://excalidraw.com → File → Open."*

---

## Excalidraw JSON Schema (strict — follow exactly)

### Top-level envelope
```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "claude-always-diagram",
  "elements": [],
  "appState": { "gridSize": null, "viewBackgroundColor": "#ffffff" },
  "files": {}
}
```

### Element base fields (required on EVERY element)
| Field | Type | Notes |
|---|---|---|
| `id` | string | unique, e.g. `"el-1"` |
| `type` | string | `rectangle` \| `ellipse` \| `diamond` \| `arrow` \| `line` \| `text` |
| `x`, `y` | number | top-left corner in px |
| `width`, `height` | number | px |
| `angle` | number | radians, usually `0` |
| `strokeColor` | string | hex, e.g. `"#1e1e2e"` |
| `backgroundColor` | string | hex or `"transparent"` |
| `fillStyle` | string | `"solid"` \| `"hachure"` \| `"cross-hatch"` |
| `strokeWidth` | number | `1` or `2` |
| `roughness` | number | `0` = smooth, `1` = hand-drawn, `2` = very rough |
| `opacity` | number | `0`–`100` |
| `groupIds` | array | `[]` |
| `frameId` | null | `null` |
| `roundness` | null\|object | `null` or `{"type":3}` for rounded rect |
| `seed` | number | any integer |
| `version` | number | `1` |
| `versionNonce` | number | any integer |
| `isDeleted` | boolean | `false` |
| `boundElements` | null\|array | arrow binding refs or `null` |
| `updated` | number | epoch ms, e.g. `1700000000000` |
| `link` | null | `null` |
| `locked` | boolean | `false` |

### Additional fields by type

**text**
```json
{
  "text": "Label",
  "fontSize": 16,
  "fontFamily": 1,
  "textAlign": "center",
  "verticalAlign": "middle",
  "baseline": 18,
  "containerId": null,
  "originalText": "Label",
  "lineHeight": 1.25
}
```

**arrow / line**
```json
{
  "points": [[0, 0], [120, 0]],
  "lastCommittedPoint": null,
  "startBinding": null,
  "endBinding": null,
  "startArrowhead": null,
  "endArrowhead": "arrow"
}
```
To bind an arrow to a shape set:
```json
"startBinding": { "elementId": "el-1", "focus": 0, "gap": 8 },
"endBinding":   { "elementId": "el-2", "focus": 0, "gap": 8 }
```

---

## Layout conventions

| Pattern | Spacing |
|---|---|
| Box width | 160 px typical, 200 px for long labels |
| Box height | 60 px typical |
| Horizontal gap | 80 px between boxes |
| Vertical gap | 60 px between rows |
| Text inside box | Same `x+width/2`, `y+height/2`; `containerId` = box id |

## Colour palette (hand-drawn friendly)

| Meaning | strokeColor | backgroundColor |
|---|---|---|
| Service / component | `#1e1e2e` | `#cdd6f4` |
| Database / store | `#1e1e2e` | `#a6e3a1` |
| Kafka / queue | `#1e1e2e` | `#fab387` |
| External / client | `#1e1e2e` | `#f5c2e7` |
| Decision / gateway | `#1e1e2e` | `#f9e2af` |
| Arrow / line | `#45475a` | `transparent` |

---

## Minimal worked example — two services connected by an arrow

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "claude-always-diagram",
  "elements": [
    {
      "id": "box-a", "type": "rectangle",
      "x": 40, "y": 100, "width": 160, "height": 60, "angle": 0,
      "strokeColor": "#1e1e2e", "backgroundColor": "#cdd6f4",
      "fillStyle": "solid", "strokeWidth": 2, "roughness": 1, "opacity": 100,
      "groupIds": [], "frameId": null, "roundness": {"type": 3},
      "seed": 1, "version": 1, "versionNonce": 1,
      "isDeleted": false, "boundElements": [{"id":"arr-1","type":"arrow"}],
      "updated": 1700000000000, "link": null, "locked": false
    },
    {
      "id": "txt-a", "type": "text",
      "x": 40, "y": 115, "width": 160, "height": 30, "angle": 0,
      "strokeColor": "#1e1e2e", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 1, "roughness": 0, "opacity": 100,
      "groupIds": [], "frameId": null, "roundness": null,
      "seed": 2, "version": 1, "versionNonce": 2,
      "isDeleted": false, "boundElements": null,
      "updated": 1700000000000, "link": null, "locked": false,
      "text": "Service A", "fontSize": 16, "fontFamily": 1,
      "textAlign": "center", "verticalAlign": "middle", "baseline": 18,
      "containerId": "box-a", "originalText": "Service A", "lineHeight": 1.25
    },
    {
      "id": "arr-1", "type": "arrow",
      "x": 200, "y": 130, "width": 80, "height": 0, "angle": 0,
      "strokeColor": "#45475a", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "roughness": 1, "opacity": 100,
      "groupIds": [], "frameId": null, "roundness": {"type": 2},
      "seed": 3, "version": 1, "versionNonce": 3,
      "isDeleted": false, "boundElements": null,
      "updated": 1700000000000, "link": null, "locked": false,
      "points": [[0,0],[80,0]],
      "lastCommittedPoint": null,
      "startBinding": {"elementId":"box-a","focus":0,"gap":8},
      "endBinding":   {"elementId":"box-b","focus":0,"gap":8},
      "startArrowhead": null, "endArrowhead": "arrow"
    },
    {
      "id": "box-b", "type": "rectangle",
      "x": 280, "y": 100, "width": 160, "height": 60, "angle": 0,
      "strokeColor": "#1e1e2e", "backgroundColor": "#a6e3a1",
      "fillStyle": "solid", "strokeWidth": 2, "roughness": 1, "opacity": 100,
      "groupIds": [], "frameId": null, "roundness": {"type": 3},
      "seed": 4, "version": 1, "versionNonce": 4,
      "isDeleted": false, "boundElements": [{"id":"arr-1","type":"arrow"}],
      "updated": 1700000000000, "link": null, "locked": false
    },
    {
      "id": "txt-b", "type": "text",
      "x": 280, "y": 115, "width": 160, "height": 30, "angle": 0,
      "strokeColor": "#1e1e2e", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 1, "roughness": 0, "opacity": 100,
      "groupIds": [], "frameId": null, "roundness": null,
      "seed": 5, "version": 1, "versionNonce": 5,
      "isDeleted": false, "boundElements": null,
      "updated": 1700000000000, "link": null, "locked": false,
      "text": "Service B", "fontSize": 16, "fontFamily": 1,
      "textAlign": "center", "verticalAlign": "middle", "baseline": 18,
      "containerId": "box-b", "originalText": "Service B", "lineHeight": 1.25
    }
  ],
  "appState": { "gridSize": null, "viewBackgroundColor": "#ffffff" },
  "files": {}
}
```
