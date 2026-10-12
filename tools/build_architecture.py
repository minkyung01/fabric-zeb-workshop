"""Fresh editable architecture scene → SVG and Excalidraw, entirely offline."""
import html
import json
from reference import ROOT


def build():
    folder = ROOT / "assets"
    folder.mkdir(exist_ok=True)
    boxes = [
        [20, 80, 1220, 600, "Owned participant Fabric workspace p01..p12", "One schema-enabled Lakehouse each; never write to read-only reference", "container"],
        [50, 155, 240, 145, "Files + Bronze", "Retained SYNTHETIC fixtures\nREQUIRED genuine public ZEB\nMissing public = blocked stage", "blue"],
        [350, 155, 240, 145, "Silver", "Typed identity mapping\nERP / PMS / BIM / WBS\nKeys + certificate version", "blue"],
        [650, 155, 240, 145, "Gold", "8 site baselines / 63 subsets\nProvisional OR / strict PE\nEngineering feasibility blocked", "blue"],
        [940, 155, 260, 145, "Direct Lake / Power BI", "Manual status -> Copilot page\nREQUIRED questions + insights\nInspect, save and reopen", "blue"],
        [50, 410, 240, 150, "Ontology / native agent", "Learner-created ~10 entities\nPlan -> evidence -> reviewed Act\nNo physical action binding", "purple"],
        [350, 410, 260, 150, "Eventhouse / Operations", "EXPLICIT JSONL -> proposal\nBind RecordZEBDecision Notebook\nExplicit recorded sync; no stream", "purple"],
        [700, 410, 480, 150, "05_decision_log -> audit", "Teams Confirm -> creator-delegated Notebook action\n5 string identifiers; idempotent MERGE; no human flag\nVerify audit -> explicit recorded status -> agent Stop", "green"],
        [50, 770, 320, 145, "Teams (outside Fabric)", "Proposal -> WAIT -> human review\nProceed -> verify fields -> Confirm\nCreator execution != human identity", "orange"],
        [450, 770, 320, 145, "Foundry (OPTIONAL)", "External Fabric IQ evidence review\nSeparate consent / cost / region gate\nNever required for the core path", "orange"],
        [850, 770, 340, 145, "Future ERP / site work", "NOT IMPLEMENTED\nPhysical simulation / procurement\nEngineering + legal review required", "future"],
    ]
    arrows = [
        [290, 220, 350, 220, False], [590, 220, 650, 220, False],
        [890, 220, 940, 220, False], [770, 300, 770, 355, False],
        [770, 355, 170, 355, False], [170, 355, 170, 410, False],
        [680, 300, 480, 410, False], [480, 560, 210, 770, False],
        [370, 830, 450, 830, True], [450, 870, 370, 870, True],
        [260, 770, 740, 560, False], [1060, 560, 1060, 770, True],
    ]
    scene = {"width": 1260, "height": 1020, "boxes": boxes, "arrows": arrows}
    (folder / "architecture.scene.json").write_text(json.dumps(scene, indent=2) + "\n", encoding="utf-8")
    colors = {"blue": ("#0078D4", "#CFE4FA"), "purple": ("#5C2D91", "#E8DAEF"),
              "green": ("#107C10", "#DFF6DD"), "orange": ("#F7630C", "#FFF4CE"),
              "future": ("#64748B", "#F3F2F1"), "container": ("#0078D4", "transparent")}
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="1260" height="1020" viewBox="0 0 1260 1020">',
           '<rect width="1260" height="1020" fill="white"/>',
           '<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#0078D4"/></marker></defs>']
    elements = []
    def element(kind, x, y, w, h, **extra):
        value = {"id": f"zeb-{len(elements)}", "type": kind, "x": x, "y": y, "width": w, "height": h,
                 "angle": 0, "strokeColor": "#0078D4", "backgroundColor": "transparent", "fillStyle": "solid",
                 "strokeWidth": 2, "strokeStyle": "solid", "roughness": 0, "opacity": 100,
                 "groupIds": [], "frameId": None, "roundness": None, "seed": len(elements) + 1,
                 "version": 1, "versionNonce": 1, "isDeleted": False, "boundElements": None,
                 "updated": 0, "link": None, "locked": False}
        value.update(extra)
        elements.append(value)
    def text(x, y, value, size=16, width=1100):
        lines = value.split("\n")
        element("text", x, y, width, size * 2.5 * len(lines), text=value, originalText=value,
                fontSize=size, fontFamily=2, strokeColor="#000000", textAlign="left",
                verticalAlign="top", containerId=None, autoResize=True, lineHeight=1.25)
        for i, line in enumerate(lines):
            svg.append(f'<text x="{x}" y="{y+size+i*23}" font-family="Segoe UI,Arial" font-size="{size}" fill="#000000">{html.escape(line)}</text>')
    text(30, 20, "Construction ZEB workshop | offline-authored architecture illustration", 24)
    for x, y, w, h, title, detail, kind in boxes:
        stroke, fill = colors[kind]
        element("rectangle", x, y, w, h, strokeColor=stroke, backgroundColor=fill,
                strokeStyle="dashed" if kind == "future" else "solid", roundness={"type": 3})
        dash = 'stroke-dasharray="8 6"' if kind == "future" else ""
        svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill if fill != "transparent" else "none"}" stroke="{stroke}" stroke-width="2" {dash}/>')
        text(x + 14, y + 12, title, 17, w - 24)
        text(x + 14, y + 43, detail, 14, w - 24)
    for x1, y1, x2, y2, dashed in arrows:
        element("arrow", x1, y1, abs(x2-x1), abs(y2-y1),
                points=[[0, 0], [x2-x1, y2-y1]], startArrowhead=None, endArrowhead="arrow",
                startBinding=None, endBinding=None, strokeStyle="dashed" if dashed else "solid")
        dash = 'stroke-dasharray="8 6"' if dashed else ""
        svg.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#0078D4" stroke-width="2" marker-end="url(#arrow)" {dash}/>')
    text(30, 950, "Solid: core flow. Dashed: optional / future. Diagram is NOT a live screenshot.\nCapacity remains paused. No cloud deployment, agent run or rehearsal has been performed.", 16)
    svg.append("</svg>")
    (folder / "architecture.svg").write_text("\n".join(svg) + "\n", encoding="utf-8")
    (folder / "architecture.excalidraw").write_text(json.dumps({
        "type": "excalidraw", "version": 2, "source": "fabric-zeb-workshop",
        "elements": elements, "appState": {"viewBackgroundColor": "#ffffff"}, "files": {}
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Fresh SVG + editable Excalidraw + scene; render PNG with tools/render_architecture.ps1")


if __name__ == "__main__":
    build()
