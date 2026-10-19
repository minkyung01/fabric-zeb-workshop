"""One offline scene for the Korean architecture SVG and editable Excalidraw."""
import base64
import hashlib
import html
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 1600, 1180

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

    def chip(self, key, x, y, w, h, title, detail, palette, *, plain=False, extra=None):
        accent, tint, line, ink = palette
        self.cards.append({"id": key, "x": x, "y": y, "width": w, "height": h, **(extra or {})})
        self.rect(x, y, w, h, fill=tint, line=line, width=1.25, radius=14)
        self.rect(x+12, y+14, 5, h-28, fill=accent, line="transparent", width=0, radius=3)
        if plain:
            self.text(x+28, y+16, title, 20, w-40, weight=600, fill=ink, split=True)
            self.text(x+28, y+44, detail, 20, w-40, fill=SUBTLE)
        else:
            self.text(x+28, y+16, title, 20, w-40, weight=700, fill=ink, spacing=1.2)
            self.text(x+28, y+44, detail, 20, w-40, weight=600)

    def layer(self, key, x, y, w, h, title, purpose):
        m = METALS[key]
        self.chip(key, x, y, w, h, title, purpose, (m["mid"], m["tint"], m["line"], m["dark"]),
                  extra={"role": "medallion", "schema": key})

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
            '<title id="title">건설 ZEB 인증 컨트롤 타워 | Microsoft Fabric</title>',
            '<desc id="desc">Notebook이 공공 인증 4종과 Contoso 내부 데이터를 OneLake의 schema-enabled Lakehouse에 Bronze로 적재하고, Silver에서 표기를 맞춘 뒤 Gold 업무 데이터와 ops 운영 지표를 만듭니다. Gold는 Ontology와 Data agent, Direct Lake 모델과 Power BI, Eventhouse 위험 이벤트와 Operations agent로 이어집니다. Operations agent가 Teams로 보완안을 제안하고 담당자가 승인하면 Notebook이 조치를 기록하고 Silver·Gold를 다시 계산합니다. Foundry 근거 재검토는 선택입니다.</desc>',
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

    d.rect(40, 28, 6, 74, fill=BLUE, line="transparent", width=0, radius=3,
           gradient={"stops": ["#2AA9F5", "#0067B8"], "dir": "v"})
    d.text(62, 22, "건설 ZEB 인증 컨트롤 타워 | Microsoft Fabric", 34, 900, weight=700, split=True)
    d.text(62, 72, "공공 인증과 현장 데이터를 연결해 등급 위험을 찾고, 담당자 승인으로 보완안을 반영합니다.",
           22, 930, fill=SUBTLE)
    d.rect(1014, 64, 546, 48, line=CARD_LINE, radius=24)
    x = 1038
    for role, name, text_width in (("flow", "실습 흐름", 85), ("approval", "승인 후 반영", 110),
                                   ("optional", "선택 검토", 85)):
        color, dashed = ROLES[role]
        d.stroke("arrow", [(x, 88), (x + 42, 88)], color=color, dashed=dashed, end=True)
        d.text(x + 54, 74, name, 20, text_width + 8)
        x += 54 + text_width + 28

    d.rect(40, 128, 1160, 1012, fill="#F2F7FD", line=PANEL_LINE, width=1.5, radius=24,
           gradient={"stops": ["#F7FAFE", "#EBF3FC"], "dir": "v"})
    d.rect(60, 138, 250, 44, line="#CFE0F1", width=1, radius=22)
    d.icon("fabric", 70, 144, 32)
    d.text(114, 143.2, "Microsoft Fabric", 24, 190, weight=600)

    # OneLake holds the Lakehouse; the medallion is only the schema layout inside it.
    d.rect(80, 226, 1080, 280, fill="#E6F0FB", line="#B5D1EE", width=1.25, radius=22,
           gradient={"stops": ["#EDF5FD", "#D8E8F8"], "dir": "v"})
    d.rect(96, 240, 1048, 184, line="#C5D6EA", width=1.25, radius=16, shadow=True)
    d.icon("lakehouse", 112, 250, 40)
    d.text(164, 254.6, "schema-enabled Lakehouse | 메달리온 세 계층을 스키마로 구분", 22, 960,
           weight=600, split=True)
    d.stroke("line", [(112, 300), (1128, 300)], color="#E3EAF3", width=1.5)
    d.chip("source", 120, 316, 217, 88, "Notebook | 수집", "공공 4종·Contoso",
           ("#9FB1C8", WHITE, CARD_LINE, INK), plain=True)
    d.layer("bronze", 381, 316, 217, 88, "BRONZE", "원천 그대로")
    d.layer("silver", 642, 316, 217, 88, "SILVER", "정제·표기 통일")
    d.layer("gold", 903, 316, 217, 88, "GOLD", "업무 데이터·ops")
    d.rect(110, 441, 46, 46, line="#CFE0F1", width=1, radius=12)
    d.icon("onelake", 116, 447, 34)
    d.text(170, 447.2, "OneLake | 공통 저장소", 24, 330, weight=600, split=True)

    d.card("ontology", 80, 616, 330, 120, "ontology", "Ontology | 내장 agent", "업무 개념·관계·규칙")
    d.card("model", 455, 616, 330, 120, "semantic-model", "Semantic model", "Direct Lake")
    d.card("eventhouse", 830, 616, 330, 120, "eventhouse", "Eventhouse", "위험 이벤트 상태")
    d.card("dataagent", 80, 790, 330, 120, "data-agent", "Data agent", "업무 질문·근거 답변")
    d.card("powerbi", 455, 790, 330, 120, "power-bi", "Power BI", "인증 현황·컨트롤 타워")
    d.card("operations", 830, 790, 330, 120, "operations-agent", "Operations agent", "위험 감시·제안")
    d.card("apply", 830, 964, 330, 132, "notebook", "Notebook | 승인 반영",
           "조치 기록 → 재계산\n실제 설계·발주 변경 없음")
    d.card("foundry", 1250, 226, 310, 128, "foundry", "Foundry | 선택", "승인 전 근거 재검토", dashed=True)
    d.card("teams", 1250, 790, 310, 120, "teams", "Teams", "제안·담당자 승인",
           accent=("#F4FAF4", "#8CC08C"))

    d.arrow("source-to-bronze", [(337, 360), (381, 360)])
    d.arrow("bronze-to-silver", [(598, 360), (642, 360)])
    d.arrow("silver-to-gold", [(859, 360), (903, 360)])
    # Gold fans out below OneLake so the right margin stays free for the approval loop.
    for route, cx in (("gold-to-ontology", 245), ("gold-to-directlake", 620), ("gold-to-eventhouse", 995)):
        d.arrow(route, [(1011.5, 404), (1011.5, 560), (cx, 560), (cx, 616)])
    d.arrow("ontology-to-dataagent", [(245, 736), (245, 790)])
    d.arrow("model-to-powerbi", [(620, 736), (620, 790)])
    d.arrow("eventhouse-to-operations", [(995, 736), (995, 790)])
    d.arrow("operations-to-teams", [(1160, 850), (1250, 850)])
    d.arrow("teams-to-apply", [(1405, 910), (1405, 1118), (995, 1118), (995, 1096)], role="approval")
    d.arrow("apply-to-lakehouse", [(1160, 1030), (1180, 1030), (1180, 280), (1144, 280)], role="approval")
    d.arrow("foundry-to-ontology", [(1250, 290), (1225, 290), (1225, 198), (60, 198), (60, 676), (80, 676)],
            role="optional")
    d.arrow("teams-foundry-review", [(1405, 354), (1405, 790)], role="optional", both=True)
    d.label(1100, 588, "명시적 전송", 105, SOFT_BLUE)
    d.label(1180, 536, "조치 기록 → 재계산", 175, GREEN)
    d.label(1310, 1118, "Teams 승인", 100, GREEN)
    d.label(1405, 572, "선택 검토", 85, MUTED)
    d.save()
    print(f"Built Korean architecture SVG + Excalidraw + shared scene ({WIDTH}×{HEIGHT}).")


if __name__ == "__main__":
    build()
