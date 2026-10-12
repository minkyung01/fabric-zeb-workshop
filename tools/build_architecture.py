"""One offline scene for the Korean architecture SVG and editable Excalidraw."""
import base64
import hashlib
import html
import json
import re
from reference import ROOT

WIDTH, HEIGHT = 1900, 1460
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

    def rect(self, x, y, w, h, *, dashed=False, container=False):
        self.element("rectangle", x, y, w, h, roundness={"type": 3},
                     backgroundColor="transparent" if container else "#ffffff",
                     strokeColor=MUTED if dashed else BLUE,
                     strokeStyle="dashed" if dashed else "solid")

    def text(self, x, y, value, size=18, width=340, bold=False):
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
        self.text(x+72, y+24, title, 21, w-86, True)
        self.text(x+20, y+74, detail, 18, w-40)

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
        self.element("rectangle", x-5, y-2, width+10, 27,
                     backgroundColor="#ffffff", strokeColor="transparent", strokeWidth=0)
        self.text(x, y, value, 17, width)

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
            '<title id="title">건설 현장 ZEB 인증 위험·보완안 검토 | Microsoft Fabric</title>',
            '<desc id="desc">OneLake Gold를 공통 근거로 Ontology와 Direct Lake를 연결하고, 명시적 위험 snapshot을 감시한 Operations agent의 제안을 사람이 Teams에서 검토합니다. 승인 후 Notebook은 결정 로그만 기록합니다. Foundry는 선택 확장입니다.</desc>',
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
    d.text(40, 30, "건설 현장 ZEB 인증 위험·보완안 검토 | Microsoft Fabric", 36, 1800, True)
    d.text(40, 87, "HS-D 제출 설계 V2와 VE 변경 설계 V3를 비교하고, 같은 Gold 근거로 보완안을 검토합니다.", 22, 1800)
    for x, title, detail in [
        (40, "① 현황 계산", "02–04  원천 정제·에너지 지표 계산"),
        (510, "② 보완안 비교", "05·07  63개 조합·기준 충족 여부"),
        (980, "③ Agent 제안", "06·08  근거 질의·위험 감시·Teams 제안"),
        (1450, "④ 담당자 결정", "10–11  Proceed → Confirm → 기록 확인"),
    ]:
        d.rect(x, 145, 410, 74)
        d.text(x+18, 157, title, 22, 375, True)
        d.text(x+18, 190, detail, 17, 375)
    for x in (450, 920, 1390):
        d.arrow(f"decision-{x}", [(x, 181), (x+60, 181)])

    d.rect(40, 245, 1400, 935, dashed=True, container=True)
    d.icon("fabric", 63, 262, 44)
    d.text(120, 269, "Microsoft Fabric | 정제·계산부터 근거 검토·승인 기록까지", 25, 1220, True)
    d.text(70, 309, "참가자별 workspace · schema-enabled Lakehouse · OneLake Delta", 18, 1100)
    d.card("files", 70, 365, 350, 155, "lakehouse", "Files | 원천 데이터",
           "02·06  실제 공공 ZEB 원천\n가상 ERP · PMS · BIM · SCM\n실제 고객 시스템 연동 아님")
    d.card("spark", 70, 555, 350, 155, "notebook", "Notebook | Spark 정제",
           "02–04  Bronze → Silver → Gold\n타입·코드·설계 버전 연결\n키·단위 확인 후 지표 계산")
    d.card("gold", 70, 740, 350, 230, "onelake", "OneLake | Lakehouse",
           "bronze / silver / gold / audit\n04–05 Gold: 8개 현장 · 63개 조합\nHS-D 제출 V2 ↔ 변경 V3\n자립률 SS · 1차 에너지 PE\n비용·기간·근거로 보완안 비교\n교육 기준 · 공학 검증은 별도")
    d.card("ontology", 495, 365, 405, 270, "ontology", "Ontology | native agent",
           "06  10개 entity · 10개 relationship\n현장 → 설계 → VE·보완안·위험\n키와 관계로 Gold 근거 연결\nPlan → 근거 검토 → Act 검토\n내장 agent로 이유·대안을 질문\n별도 Data agent는 필수 아님")
    d.text(495, 661, "판단 기준 | 주거 4등급: SS ≥ 40 또는 PE < 70\n에너지 기준 충족 ≠ 발주·시공 가능", 18, 500)
    d.card("model", 1040, 365, 365, 155, "semantic-model", "Semantic model",
           "07  OneLake Gold → Direct Lake\n4개 테이블 · 관계·측정값 연결\n현장·설계·조합을 같은 기준으로")
    d.card("powerbi", 1040, 560, 365, 155, "power-bi", "Power BI | 현황·비교",
           "07  첫 현황 페이지는 직접 작성\nCopilot으로 보완안 비교 페이지\n질문·인사이트 확인 후 저장")
    d.card("eventhouse", 495, 775, 405, 160, "eventhouse", "Eventhouse | 위험 snapshot",
           "08  OneLake snapshot 명시적 수집\n위험 현장 4개 · KQL로 근거 확인\n자동 스트리밍 연결은 아님")
    d.card("operations", 1040, 775, 365, 160, "operations-agent", "Operations agent",
           "08  snapshot 조회·위험 감시\nopen 위험 → Teams 보완안 제안\n사람 확인 전 실행하지 않음")
    d.card("audit", 1040, 985, 365, 155, "notebook", "Notebook | 결정 기록",
           "10  Confirm 후 action 실행\n05_decision_log → audit만 기록\n07_verify_readonly로 결과 확인")
    d.text(495, 1000, "실제 설계·발주·시공은 바꾸지 않습니다.\n승인은 검토 결정의 기록입니다.\n실제 실행·미완료 단계는 별도 확인합니다.", 18, 440)

    d.rect(1490, 245, 370, 410, dashed=True, container=True)
    d.icon("foundry", 1510, 264, 44)
    d.text(1570, 272, "Microsoft Foundry", 23, 280, True)
    d.text(1510, 319, "09  선택 확장 | 기본 실습 필수 아님", 18, 330)
    d.card("foundry", 1510, 365, 330, 195, "foundry-agent", "Foundry agent",
           "승인 전 보완안 근거 재검토\nFabric IQ → Ontology 근거\n검토 결과를 Teams로 가져와\n담당자가 최종 판단", dashed=True)
    d.text(1510, 596, "별도 동의·비용·지역 확인 필요", 18, 330)
    d.rect(1490, 740, 370, 395, dashed=True, container=True)
    d.card("teams", 1510, 760, 330, 350, "teams", "Microsoft Teams",
           "08  Agent 제안 수신 후 대기\n현장·설계·보완안의 근거 확인\n필요하면 09 Foundry 재검토\n\n10  담당자 Proceed → Confirm\n기록할 식별자·내용을 검토\n확인 후 Fabric action 실행\n결정 로그 확인 → 감시 종료")

    d.arrow("files-to-spark", [(245, 520), (245, 555)])
    d.label(265, 526, "정제", 40)
    d.arrow("spark-to-gold", [(245, 710), (245, 740)])
    d.label(265, 714, "계산", 40)
    d.arrow("gold-to-ontology", [(420, 800), (460, 800), (460, 585), (495, 585)])
    d.label(431, 713, "근거", 38)
    d.arrow("gold-to-directlake", [(460, 585), (460, 342), (1015, 342), (1015, 420), (1040, 420)])
    d.label(645, 328, "OneLake Gold → Direct Lake", 300)
    d.arrow("model-to-powerbi", [(1220, 520), (1220, 560)])
    d.label(1250, 530, "관계·측정값", 120)
    d.arrow("gold-to-snapshot", [(420, 855), (495, 855)])
    d.label(431, 827, "수집", 40)
    d.arrow("snapshot-to-operations", [(900, 845), (1040, 845)])
    d.label(915, 815, "KQL 조회", 100)
    d.arrow("operations-to-teams", [(1405, 845), (1510, 845)])
    d.label(1426, 814, "제안", 40)
    d.arrow("teams-to-audit", [(1510, 1055), (1405, 1055)])
    d.label(1422, 1025, "확인", 40)
    d.arrow("audit-to-snapshot", [(1040, 1055), (965, 1055), (965, 965), (705, 965), (705, 935)])
    d.label(723, 947, "명시적 recorded 상태 반영", 255)
    d.arrow("audit-to-onelake", [(1220, 1140), (1220, 1157), (245, 1157), (245, 970)])
    d.label(510, 1142, "OneLake audit.decision_log | 승인 기록만 저장", 490)
    d.arrow("foundry-to-ontology", [(1510, 465), (1462, 465), (1462, 740), (930, 740), (930, 610), (900, 610)], dashed=True)
    d.label(1060, 725, "선택: Fabric IQ → Ontology", 300)
    d.arrow("teams-foundry-review", [(1710, 560), (1710, 760)], dashed=True, both=True)
    d.label(1550, 669, "승인 전 검토 · Teams 복귀", 285)

    d.rect(40, 1220, 1820, 165, dashed=True, container=True)
    d.text(65, 1236, "운영에 적용할 때 연결 | 미래 범위 · 이 워크숍에서는 구현하지 않음", 22, 1750, True)
    d.text(70, 1282, "원천 시스템 연결\nERP·PMS·BIM·SCM 추출·일정 수집", 19, 500)
    d.text(660, 1282, "공학·인증 검증\n설비 상호작용·배타성·시공성·법적 인증", 19, 560)
    d.text(1260, 1282, "승인 후 업무 시스템 반영\n발주·시공 변경은 별도 통제·승인 필요", 19, 550)
    d.arrow("legend-core", [(60, 1420), (120, 1420)])
    d.text(135, 1405, "실선: 기본 실습 흐름", 18, 340)
    d.arrow("legend-optional", [(525, 1420), (585, 1420)], dashed=True)
    d.text(600, 1405, "점선: 선택 확장·제품 경계·미래 연결", 18, 610)
    d.text(1340, 1405, "개념 구성도 · 실제 화면 아님", 18, 500)
    d.save()
    print("Built Korean architecture SVG + Excalidraw + shared scene (1900×1460).")


if __name__ == "__main__":
    build()
