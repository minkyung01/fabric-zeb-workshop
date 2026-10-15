"""One offline scene for the Korean architecture SVG and editable Excalidraw."""
import base64
import hashlib
import html
import json
import math
import re
from reference import ROOT

WIDTH, HEIGHT = 1600, 1100

# Microsoft blue leads, neutrals carry the structure, green marks the approved path.
BLUE, GREEN, MUTED = "#0078D4", "#107C10", "#7F8DA3"
INK, SUBTLE, WHITE = "#1B1A19", "#605E5C", "#FFFFFF"
CARD_LINE, PANEL_LINE, SOFT_BLUE = "#D5DEE9", "#A9CBEB", "#9CC4EC"
FONT = "Segoe UI, Malgun Gothic, 맑은 고딕, Arial, sans-serif"
ROLES = {"flow": (BLUE, False), "approval": (GREEN, False), "optional": (MUTED, True)}
METALS = {
    "bronze": {"dark": "#8C5528", "mid": "#C0824A", "light": "#F3D9BC", "tint": "#FCF6F0", "line": "#E6CFB8"},
    "silver": {"dark": "#4F5E75", "mid": "#8E9CB1", "light": "#E3E8EF", "tint": "#F6F8FA", "line": "#D2D9E3"},
    "gold": {"dark": "#855D00", "mid": "#DDA51D", "light": "#FAEBB4", "tint": "#FFFAEC", "line": "#EBD596"},
}


def rounded(points, radius=14):
    """Orthogonal polyline as an SVG path with softened corners."""
    path = [f"M{points[0][0]:g},{points[0][1]:g}"]
    for (x0, y0), (x1, y1), (x2, y2) in zip(points, points[1:], points[2:]):
        a, b = math.hypot(x0 - x1, y0 - y1), math.hypot(x2 - x1, y2 - y1)
        r = min(radius, a / 2, b / 2)
        path.append(f"L{x1 + (x0 - x1) * r / a:g},{y1 + (y0 - y1) * r / a:g} "
                    f"Q{x1:g},{y1:g} {x1 + (x2 - x1) * r / b:g},{y1 + (y2 - y1) * r / b:g}")
    path.append(f"L{points[-1][0]:g},{points[-1][1]:g}")
    return " ".join(path)


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

    # Shared styling hints live in customData: Excalidraw ignores them and falls
    # back to solid fills and black text, the SVG adds gradients, shadows and tints.
    def rect(self, x, y, w, h, *, fill=WHITE, line=CARD_LINE, width=1.25, dashed=False,
             radius=14, shadow=False, gradient=None):
        hints = {"radius": radius}
        if shadow:
            hints["shadow"] = True
        if gradient:
            hints["gradient"] = gradient
        self.element("rectangle", x, y, w, h, roundness={"type": 3} if radius else None,
                     backgroundColor=fill, strokeColor=line, strokeWidth=width,
                     strokeStyle="dashed" if dashed else "solid", customData=hints)

    def ellipse(self, x, y, w, h, *, fill="transparent", line=BLUE, width=1, opacity=100, gradient=None):
        self.element("ellipse", x, y, w, h, backgroundColor=fill, strokeColor=line,
                     strokeWidth=width, opacity=opacity,
                     customData={"gradient": gradient} if gradient else {})

    def text(self, x, y, value, size=20, width=340, *, weight=400, fill=INK, align="left",
             split=False, spacing=0):
        # Measured-line layout is shared by both exports; no zero-sized text.
        hints = {"bold": weight >= 600, "weight": weight, "fill": fill}
        if split:
            hints["split"] = True
        if spacing:
            hints["spacing"] = spacing
        self.element("text", x, y, width, round(size * 1.4 * len(value.split("\n")), 2),
                     text=value, originalText=value, fontSize=size, fontFamily=2,
                     strokeColor="#000000", textAlign=align, verticalAlign="top",
                     containerId=None, autoResize=False, lineHeight=1.4, customData=hints)

    def icon(self, name, x, y, size=48):
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

    def stroke(self, kind, points, *, color, width=2.25, dashed=False, start=False, end=False):
        x, y = points[0]
        self.element(kind, x, y,
                     max(p[0] for p in points)-min(p[0] for p in points),
                     max(p[1] for p in points)-min(p[1] for p in points),
                     points=[[px-x, py-y] for px, py in points],
                     startArrowhead="arrow" if start else None,
                     endArrowhead="arrow" if end else None,
                     startBinding=None, endBinding=None, strokeColor=color,
                     strokeWidth=width, strokeStyle="dashed" if dashed else "solid")

    def card(self, key, x, y, w, h, icon, title, detail, *, dashed=False, accent=None):
        self.cards.append({"id": key, "x": x, "y": y, "width": w, "height": h})
        self.rect(x, y, w, h, fill=accent[0] if accent else WHITE,
                  line=MUTED if dashed else accent[1] if accent else CARD_LINE,
                  width=1.5 if dashed or accent else 1.25, dashed=dashed, shadow=not dashed)
        self.icon(icon, x+18, y+(h-54)/2, 54)
        top = y + (h - (36.8 + 28 * (detail.count("\n") + 1))) / 2
        self.text(x+86, top, title, 22, w-100, weight=600, split=True)
        self.text(x+86, top+36.8, detail, 20, w-100, fill=SUBTLE)

    def layer(self, key, x, y, w, h, title, purpose):
        m = METALS[key]
        self.cards.append({"id": key, "x": x, "y": y, "width": w, "height": h,
                          "role": "medallion", "schema": key})
        self.rect(x, y, w, h, fill=m["tint"], line=m["line"], width=1.5, shadow=True)
        cy = y + h / 2
        self.ellipse(x+18, cy-27, 54, 54, fill=m["mid"], line=m["dark"], width=1,
                     gradient={"stops": [m["light"], m["mid"], m["dark"]], "dir": "d"})
        self.ellipse(x+28, cy-17, 34, 34, line=WHITE, width=2, opacity=80)
        top = y + (h - 62.8) / 2
        self.text(x+86, top, title, 20, w-100, weight=700, fill=m["dark"], spacing=1.2)
        self.text(x+86, top+32, purpose, 22, w-100, weight=600)

    def arrow(self, key, points, *, role="flow", both=False):
        color, dashed = ROLES[role]
        self.routes.append({"id": key, "points": points, "optional": role == "optional"})
        self.stroke("arrow", points, color=color, dashed=dashed, start=both, end=True)

    def label(self, cx, cy, value, text_width, color):
        w = text_width + 32
        self.rect(cx-w/2, cy-15, w, 30, line=color, width=1.25, radius=15)
        self.text(cx-w/2, cy-14, value, 20, w, align="center")

    def svg(self):
        defs = [
            '<filter id="shadow" x="-6%" y="-6%" width="112%" height="125%" color-interpolation-filters="sRGB">'
            '<feDropShadow dx="0" dy="2" stdDeviation="3" flood-color="#0B3A66" flood-opacity="0.12"/></filter>']
        body, gradients, markers = [], {}, {}

        def paint(color, hint):
            if not hint:
                return "none" if color == "transparent" else color
            key = json.dumps(hint, sort_keys=True)
            if key not in gradients:
                gradients[key] = f"grad{len(gradients)}"
                x2, y2 = {"h": (1, 0), "v": (0, 1), "d": (1, 1)}[hint["dir"]]
                stops = "".join(f'<stop offset="{i / (len(hint["stops"]) - 1):g}" stop-color="{c}"/>'
                                for i, c in enumerate(hint["stops"]))
                defs.append(f'<linearGradient id="{gradients[key]}" x1="0" y1="0" x2="{x2}" y2="{y2}">{stops}</linearGradient>')
            return f"url(#{gradients[key]})"

        def marker(color):
            name = "arrow-" + color.lstrip("#")
            if name not in markers:
                markers[name] = True
                defs.append(f'<marker id="{name}" markerUnits="userSpaceOnUse" markerWidth="14" markerHeight="12" '
                            f'refX="12.5" refY="6" orient="auto-start-reverse"><path d="M1,1 L12.5,6 L1,11 Z" '
                            f'fill="{color}" stroke="{color}" stroke-width="1.4" stroke-linejoin="round"/></marker>')
            return name

        for e in self.elements:
            x, y, w, h = (e[k] for k in ("x", "y", "width", "height"))
            kind, color, hints = e["type"], e["strokeColor"], e.get("customData") or {}
            dash = ' stroke-dasharray="6 7"' if e["strokeStyle"] == "dashed" else ""
            if kind in ("rectangle", "ellipse"):
                line = "none" if e["strokeWidth"] == 0 or color == "transparent" else color
                look = (f'fill="{paint(e["backgroundColor"], hints.get("gradient"))}" stroke="{line}" '
                        f'stroke-width="{e["strokeWidth"]}"{dash}')
                if e["opacity"] != 100:
                    look += f' opacity="{e["opacity"] / 100:g}"'
                if kind == "rectangle":
                    shadow = ' filter="url(#shadow)"' if hints.get("shadow") else ""
                    body.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" '
                                f'rx="{hints.get("radius", 0)}" {look}{shadow}/>')
                else:
                    body.append(f'<ellipse cx="{x + w / 2:g}" cy="{y + h / 2:g}" rx="{w / 2:g}" ry="{h / 2:g}" {look}/>')
            elif kind == "text":
                size, centered = e["fontSize"], e["textAlign"] == "center"
                weight = hints.get("weight", 600 if hints.get("bold") else 400)
                anchor = ' text-anchor="middle"' if centered else ""
                anchor += f' letter-spacing="{hints["spacing"]}"' if hints.get("spacing") else ""
                for i, line in enumerate(e["text"].split("\n")):
                    head, sep, tail = line.partition(" | ") if hints.get("split") else (line, "", "")
                    rest = (f'<tspan font-weight="400" fill="{SUBTLE}"> | {html.escape(tail)}</tspan>' if sep else "")
                    body.append(f'<text x="{x + w / 2 if centered else x:g}" y="{y + size * 1.1 + i * size * 1.4:g}"{anchor} '
                                f'font-family="{FONT}" font-size="{size}" font-weight="{weight}" '
                                f'fill="{hints.get("fill", "#000000")}">{html.escape(head)}{rest}</text>')
            elif kind == "image":
                url = self.files[e["fileId"]]["dataURL"]
                body.append(f'<image x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" href="{url}" preserveAspectRatio="xMidYMid meet"/>')
            elif kind in ("arrow", "line"):
                points = [(x + px, y + py) for px, py in e["points"]]
                heads = "".join(f' marker-{side}="url(#{marker(color)})"' for side, key in
                                (("end", "endArrowhead"), ("start", "startArrowhead")) if e[key])
                body.append(f'<path d="{rounded(points)}" fill="none" stroke="{color}" stroke-width="{e["strokeWidth"]}" '
                            f'stroke-linecap="round" stroke-linejoin="round"{heads}{dash}/>')
        return "\n".join([
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="title desc">',
            '<title id="title">건설 ZEB 워크숍 | Microsoft Fabric</title>',
            '<desc id="desc">Bronze 원천 보존, Silver 정제·연결, Gold 업무지표·판단근거의 세 계층은 OneLake 공통 저장소를 사용합니다. Gold에서 Ontology 내장 agent, Direct Lake 모델과 Power BI, 명시적 snapshot과 Eventhouse 및 Operations agent로 연결됩니다. Teams 담당자 승인 후 Notebook은 결정 기록만 저장하며 설계·발주는 변경하지 않습니다. Foundry 근거 재검토는 선택입니다.</desc>',
            f'<rect width="{WIDTH}" height="{HEIGHT}" fill="white"/>',
            "<defs>", *defs, "</defs>", *body, "</svg>"]) + "\n"

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
        (folder / "architecture.svg").write_text(self.svg(), encoding="utf-8")


def build():
    d = Diagram()
    mid = (245, 620, 995)

    d.rect(40, 28, 6, 74, fill=BLUE, line="transparent", width=0, radius=3,
           gradient={"stops": ["#2AA9F5", "#0067B8"], "dir": "v"})
    d.text(62, 22, "건설 ZEB 워크숍 | Microsoft Fabric", 34, 900, weight=700, split=True)
    d.text(62, 72, "현장·설계 데이터를 연결해 ZEB 현황과 보완안을 검토하고, 담당자의 결정을 기록합니다.",
           22, 930, fill=SUBTLE)
    d.rect(1014, 64, 546, 48, line=CARD_LINE, radius=24)
    x = 1038
    for role, name, text_width in (("flow", "기본 흐름", 85), ("approval", "승인 후 기록", 110),
                                   ("optional", "선택 검토", 85)):
        color, dashed = ROLES[role]
        d.stroke("arrow", [(x, 88), (x + 42, 88)], color=color, dashed=dashed, end=True)
        d.text(x + 54, 74, name, 20, text_width + 8)
        x += 54 + text_width + 28

    d.rect(40, 128, 1160, 930, fill="#F2F7FD", line=PANEL_LINE, width=1.5, radius=24,
           gradient={"stops": ["#F7FAFE", "#EBF3FC"], "dir": "v"})
    d.rect(60, 138, 250, 44, line="#CFE0F1", width=1, radius=22)
    d.icon("fabric", 70, 144, 32)
    d.text(114, 143.2, "Microsoft Fabric", 24, 190, weight=600)

    d.card("files", 80, 222, 330, 128, "lakehouse", "Files | 원천", "현장·설계·공공 ZEB")
    d.layer("bronze", 80, 388, 330, 128, "BRONZE", "원천 보존")
    d.layer("silver", 455, 388, 330, 128, "SILVER", "정제·연결")
    d.layer("gold", 830, 388, 330, 128, "GOLD", "업무지표·판단근거")
    for cx in mid:
        d.stroke("line", [(cx, 516), (cx, 542)], color=SOFT_BLUE, width=2)
    d.rect(80, 542, 1080, 70, fill="#DCEBFA", line=PANEL_LINE, width=1.25, radius=16,
           gradient={"stops": ["#EEF6FE", "#D6E9FA"], "dir": "h"})
    d.rect(94, 552, 50, 50, line="#CFE0F1", width=1, radius=14)
    d.icon("onelake", 100, 558, 38)
    d.text(160, 560.2, "OneLake | 공통 저장소", 24, 330, weight=600, split=True)
    d.rect(832, 557, 304, 40, line=PANEL_LINE, width=1.25, radius=20)
    d.text(832, 561.6, "schema-enabled Lakehouse", 22, 304, align="center")

    d.card("ontology", 80, 700, 330, 128, "ontology", "Ontology | 내장 agent", "근거 질의")
    d.card("model", 455, 700, 330, 128, "semantic-model", "Semantic model", "Direct Lake")
    d.card("eventhouse", 830, 700, 330, 128, "eventhouse", "Eventhouse", "위험 snapshot")
    d.card("powerbi", 455, 868, 330, 128, "power-bi", "Power BI", "현황·보완안")
    d.card("operations", 830, 868, 330, 128, "operations-agent", "Operations agent", "위험 감시·제안")
    d.card("audit", 80, 868, 330, 128, "notebook", "Notebook | 결정 기록",
           "결정 기록만 저장\n설계·발주 변경 없음")
    d.card("foundry", 1250, 222, 310, 128, "foundry", "Foundry | 선택", "승인 전 근거 재검토", dashed=True)
    d.card("teams", 1250, 868, 310, 128, "teams", "Teams", "제안·담당자 승인",
           accent=("#F4FAF4", "#8CC08C"))

    d.arrow("files-to-bronze", [(245, 350), (245, 388)])
    d.arrow("bronze-to-silver", [(410, 452), (455, 452)])
    d.arrow("silver-to-gold", [(785, 452), (830, 452)])
    for route, cx in (("gold-to-ontology", 245), ("gold-to-directlake", 620), ("gold-to-snapshot", 995)):
        d.arrow(route, [(1160, 452), (1180, 452), (1180, 646), (cx, 646), (cx, 700)])
    d.arrow("model-to-powerbi", [(620, 828), (620, 868)])
    d.arrow("snapshot-to-operations", [(995, 828), (995, 868)])
    d.arrow("operations-to-teams", [(1160, 932), (1250, 932)])
    d.arrow("teams-to-audit", [(1405, 996), (1405, 1030), (245, 1030), (245, 996)], role="approval")
    d.arrow("foundry-to-ontology", [(1250, 286), (1225, 286), (1225, 198), (60, 198), (60, 764), (80, 764)],
            role="optional")
    d.arrow("teams-foundry-review", [(1405, 350), (1405, 868)], role="optional", both=True)
    d.label(1011 + 137/2, 673, "명시적 수집", 105, SOFT_BLUE)
    d.label(700, 1030, "승인 후 기록", 110, GREEN)
    d.label(1405, 609, "선택 검토", 85, MUTED)
    d.save()
    print(f"Built Korean medallion SVG + Excalidraw + shared scene ({WIDTH}×{HEIGHT}).")


if __name__ == "__main__":
    build()
