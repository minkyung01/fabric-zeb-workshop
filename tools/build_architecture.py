"""One offline scene for the Korean architecture SVG and editable Excalidraw."""
import base64
import hashlib
import html
import json
import re
from reference import ROOT

WIDTH, HEIGHT = 1600, 1100
BLUE, MUTED = "#0078D4", "#788AA3"


class Diagram:
    def __init__(self):
        self.elements, self.files, self.cards, self.routes = [], {}, [], []

    def element(self, kind, x, y, w, h, **extra):
        value = {
            "id": f"zeb-{len(self.elements)}", "type": kind, "x": x, "y": y,
            "width": w, "height": h, "angle": 0, "strokeColor": BLUE,
            "backgroundColor": "transparent", "fillStyle": "solid", "strokeWidth": 1.5,
            "strokeStyle": "solid", "roughness": 0, "opacity": 100, "groupIds": [],
            "frameId": None, "roundness": None, "seed": len(self.elements) + 1,
            "version": 1, "versionNonce": 1, "isDeleted": False,
            "boundElements": None, "updated": 0, "link": None, "locked": False,
        }
        value.update(extra)
        self.elements.append(value)
        return value

    def rect(self, x, y, w, h, *, dashed=False, container=False, color=None):
        self.element("rectangle", x, y, w, h, roundness={"type": 3},
                     backgroundColor="transparent" if container else "#ffffff",
                     strokeColor=color or (MUTED if dashed else BLUE),
                     strokeStyle="dashed" if dashed else "solid")

    def text(self, x, y, value, size=20, width=340, bold=False):
        # Measured-line layout is shared by both exports; no zero-sized text.
        self.element("text", x, y, width, size * 1.4 * len(value.split("\n")),
                     text=value, originalText=value, fontSize=size, fontFamily=2,
                     strokeColor="#000000", textAlign="left", verticalAlign="top",
                     containerId=None, autoResize=False, lineHeight=1.4,
                     customData={"bold": bold})

    def icon(self, name, x, y, size=40):
        raw = (ROOT / "assets" / "icons" / f"{name}.svg").read_bytes()
        file_id = hashlib.sha256(raw).hexdigest()
        self.files[file_id] = {
            "id": file_id, "mimeType": "image/svg+xml", "created": 0,
            "dataURL": "data:image/svg+xml;base64," + base64.b64encode(raw).decode(),
            "lastRetrieved": 0,
        }
        # Respect the original aspect ratio, including the non-square Azure marks.
        tag = raw.decode().split(">")[0]
        viewbox = re.search(r'viewBox="([^"]+)"', tag)
        if viewbox:
            _, _, iw, ih = map(float, viewbox[1].split())
        else:
            iw = float(re.search(r'width="([0-9.]+)', tag)[1])
            ih = float(re.search(r'height="([0-9.]+)', tag)[1])
        w, h = size * iw / max(iw, ih), size * ih / max(iw, ih)
        self.element("image", x + (size-w)/2, y + (size-h)/2, w, h,
                     fileId=file_id, status="saved", scale=[1, 1], crop=None,
                     customData={"productIcon": name})

    def card(self, key, x, y, w, h, icon, title, detail, *, dashed=False):
        self.cards.append({"id": key, "x": x, "y": y, "width": w, "height": h})
        self.rect(x, y, w, h, dashed=dashed)
        self.icon(icon, x+18, y+16)
        self.text(x+72, y+24, title, 22, w-86, True)
        self.text(x+20, y+64, detail, 20, w-40)

    def layer(self, key, x, color, title, purpose):
        self.cards.append({"id": key, "x": x, "y": 350, "width": 310, "height": 150,
                          "role": "medallion", "schema": key})
        self.rect(x, 350, 310, 150)
        self.element("rectangle", x+20, 373, 7, 45, backgroundColor=color,
                     strokeColor=color, strokeWidth=0)
        self.text(x+42, 375, title, 30, 250, True)
        self.text(x+20, 441, purpose, 24, 275, True)

    def arrow(self, key, points, *, dashed=False, both=False):
        self.routes.append({"id": key, "points": points, "optional": dashed})
        x, y = points[0]
        self.element("arrow", x, y,
                     max(p[0] for p in points)-min(p[0] for p in points),
                     max(p[1] for p in points)-min(p[1] for p in points),
                     points=[[px-x, py-y] for px, py in points],
                     startArrowhead="arrow" if both else None, endArrowhead="arrow",
                     startBinding=None, endBinding=None,
                     strokeColor=MUTED if dashed else BLUE,
                     strokeStyle="dashed" if dashed else "solid")

    def label(self, x, y, value, width):
        self.element("rectangle", x-5, y-2, width+10, 30,
                     backgroundColor="#ffffff", strokeColor="transparent", strokeWidth=0)
        self.text(x, y, value, 20, width)

    def save(self):
        folder = ROOT / "assets"
        scene = {"width": WIDTH, "height": HEIGHT, "cards": self.cards,
                 "routes": self.routes, "elements": self.elements, "files": self.files}
        (folder / "architecture.scene.json").write_text(
            json.dumps(scene, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (folder / "architecture.excalidraw").write_text(json.dumps({
            "type": "excalidraw", "version": 2, "source": "fabric-zeb-workshop",
            "elements": self.elements, "files": self.files,
            "appState": {"viewBackgroundColor": "#ffffff"},
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        svg = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            '<title id="title">건설 ZEB 워크숍 | Microsoft Fabric</title>',
            '<desc id="desc">Bronze 원천 보존, Silver 정제·연결, Gold 업무지표·판단근거의 세 계층은 OneLake 공통 저장소를 사용합니다. Gold에서 Ontology 내장 agent, Direct Lake 모델과 Power BI, 명시적 snapshot과 Eventhouse 및 Operations agent로 연결됩니다. Teams 담당자 승인 후 Notebook은 결정 기록만 저장하며 설계·발주는 변경하지 않습니다. Foundry 근거 재검토는 선택입니다.</desc>',
            f'<rect width="{WIDTH}" height="{HEIGHT}" fill="white"/>',
            '<defs>',
        ]
        for name, color in (("core", BLUE), ("optional", MUTED)):
            svg.append(f'<marker id="{name}" markerWidth="9" markerHeight="8" refX="8" refY="4" orient="auto-start-reverse"><path d="M0,0 L8,4 L0,8 Z" fill="{color}"/></marker>')
        svg.append("</defs>")
        for e in self.elements:
            x, y, w, h = (e[k] for k in ("x", "y", "width", "height"))
            kind = e["type"]
            color = e["strokeColor"]
            dash = ' stroke-dasharray="7 6"' if e["strokeStyle"] == "dashed" else ""
            if kind == "rectangle":
                fill = "none" if e["backgroundColor"] == "transparent" else e["backgroundColor"]
                rx = 12 if e["roundness"] else 0
                svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{color}" stroke-width="{e["strokeWidth"]}"{dash}/>')
            elif kind == "text":
                size = e["fontSize"]
                weight = 600 if e["customData"]["bold"] else 400
                for i, line in enumerate(e["text"].split("\n")):
                    svg.append(f'<text x="{x}" y="{y+size+i*size*1.4}" font-family="Segoe UI, Malgun Gothic, 맑은 고딕, Arial, sans-serif" font-size="{size}" font-weight="{weight}" fill="#000000">{html.escape(line)}</text>')
            elif kind == "image":
                url = self.files[e["fileId"]]["dataURL"]
                svg.append(f'<image x="{x}" y="{y}" width="{w}" height="{h}" href="{url}" preserveAspectRatio="xMidYMid meet"/>')
            elif kind == "arrow":
                points = " ".join(f"{x+px},{y+py}" for px, py in e["points"])
                marker = "optional" if e["strokeStyle"] == "dashed" else "core"
                start = f' marker-start="url(#{marker})"' if e["startArrowhead"] else ""
                svg.append(f'<polyline points="{points}" fill="none" stroke="{color}" stroke-width="1.7" stroke-linejoin="round" marker-end="url(#{marker})"{start}{dash}/>')
        svg.append("</svg>")
        (folder / "architecture.svg").write_text("\n".join(svg)+"\n", encoding="utf-8")


def build():
    d = Diagram()
    d.text(40, 28, "건설 ZEB 워크숍 | Microsoft Fabric", 30, 1500, True)
    d.text(40, 78, "현장·설계 데이터를 연결해 ZEB 현황과 보완안을 검토하고, 담당자의 결정을 기록합니다.", 22, 1500)
    d.rect(40, 125, 1120, 925, container=True)
    d.icon("fabric", 65, 141, 40)
    d.text(120, 145, "Microsoft Fabric", 24, 450, True)
    d.card("files", 80, 205, 310, 110, "lakehouse", "Files | 원천", "현장·설계·공공 ZEB")
    d.layer("bronze", 80, "#9B6A43", "BRONZE", "원천 보존")
    d.layer("silver", 445, "#788AA3", "SILVER", "정제·연결")
    d.layer("gold", 810, "#A47B19", "GOLD", "업무지표·판단근거")
    d.rect(80, 530, 1040, 75)
    d.icon("onelake", 100, 548, 40)
    d.text(158, 550, "OneLake | 공통 저장소", 24, 480, True)
    d.text(695, 553, "schema-enabled Lakehouse", 22, 410)

    d.card("ontology", 80, 700, 310, 125, "ontology", "Ontology | 내장 agent", "근거 질의")
    d.card("model", 445, 700, 310, 125, "semantic-model", "Semantic model", "Direct Lake")
    d.card("eventhouse", 810, 700, 310, 125, "eventhouse", "Eventhouse", "위험 snapshot")
    d.card("powerbi", 445, 865, 310, 125, "power-bi", "Power BI", "현황·보완안")
    d.card("operations", 810, 865, 310, 125, "operations-agent", "Operations agent", "위험 감시·제안")
    d.card("audit", 80, 865, 310, 125, "notebook", "Notebook | 결정 기록",
           "결정 기록만 저장\n설계·발주 변경 없음")
    d.card("foundry", 1220, 205, 340, 125, "foundry", "Foundry | 선택", "승인 전 근거 재검토", dashed=True)
    d.card("teams", 1220, 865, 340, 125, "teams", "Teams", "제안·담당자 승인")

    d.arrow("files-to-bronze", [(235, 315), (235, 350)])
    d.arrow("bronze-to-silver", [(390, 425), (445, 425)])
    d.arrow("silver-to-gold", [(755, 425), (810, 425)])
    for route, x in (("gold-to-ontology", 235), ("gold-to-directlake", 600), ("gold-to-snapshot", 965)):
        d.arrow(route, [(1120, 425), (1140, 425), (1140, 650), (x, 650), (x, 700)])
    d.label(980, 664, "명시적 수집", 120)
    d.arrow("model-to-powerbi", [(600, 825), (600, 865)])
    d.arrow("snapshot-to-operations", [(965, 825), (965, 865)])
    d.arrow("operations-to-teams", [(1120, 925), (1220, 925)])
    d.arrow("teams-to-audit", [(1390, 990), (1390, 1025), (235, 1025), (235, 990)])
    d.label(685, 1009, "승인 후 기록", 140)
    d.arrow("foundry-to-ontology", [(1220, 265), (1185, 265), (1185, 185),
                                 (60, 185), (60, 760), (80, 760)], dashed=True)
    d.arrow("teams-foundry-review", [(1390, 330), (1390, 865)], dashed=True, both=True)
    d.label(1245, 565, "선택 검토", 100)
    d.text(40, 1064, "실선: 기본 흐름 · 점선: 선택 검토", 20, 700)
    d.save()
    print(f"Built Korean medallion SVG + Excalidraw + shared scene ({WIDTH}×{HEIGHT}).")


if __name__ == "__main__":
    build()
