"""One offline scene for the Korean architecture SVG and editable Excalidraw."""
import base64
import hashlib
import html
import json
import re
from reference import ROOT

WIDTH, HEIGHT = 1900, 1960
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

    def layer(self, key, x, color, title, purpose, notebook, detail):
        self.cards.append({"id": key, "x": x, "y": 535, "width": 405, "height": 345,
                           "role": "medallion", "schema": key, "notebook": notebook})
        self.rect(x, 535, 405, 345, color=color)
        self.element("rectangle", x+20, 553, 7, 45, backgroundColor=color,
                     strokeColor=color, strokeWidth=0)
        self.text(x+42, 555, title, 30, 345, True)
        self.text(x+20, 610, purpose, 20, 370, True)
        self.icon("notebook", x+20, 649, 26)
        self.text(x+58, 650, notebook + " | Spark", 18, 325)
        self.text(x+20, 695, detail, 18, 370)

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
            '<desc id="desc">OneLake 안의 schema-enabled Lakehouse에 Bronze 원천 보존, Silver 타입·키 검증, Gold 업무 entity·계산 결과를 분리합니다. Spark Notebook이 각 계층을 쓰고 SQL endpoint는 읽기 검산합니다. Gold만 Ontology·Direct Lake·명시적 위험 snapshot의 근거로 소비합니다. 승인 기록은 별도 audit이며 Foundry는 선택 확장입니다.</desc>',
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

    d.rect(40, 245, 1400, 1470, dashed=True, container=True)
    d.icon("fabric", 63, 262, 44)
    d.text(120, 269, "Microsoft Fabric | 정제·계산부터 근거 검토·승인 기록까지", 25, 1220, True)
    d.text(70, 309, "참가자별 workspace · schema-enabled Lakehouse · OneLake Delta", 18, 1100)
    d.card("files", 70, 350, 405, 130, "lakehouse", "Files | 보존한 원천 bytes",
           "가상 fixture JSON + 실제 공공 ZEB CSV\n원본 파일 보존 ≠ Bronze Delta table")
    d.icon("onelake", 535, 363, 44)
    d.text(595, 368, "OneLake | 세 계층을 담는 공통 저장소", 25, 795, True)
    d.text(535, 414, "한 참가자 · 한 schema-enabled Lakehouse\nFiles와 Bronze / Silver / Gold 모두 OneLake 안에 저장", 19, 840)
    d.rect(55, 500, 1370, 430, dashed=True, container=True)
    d.text(535, 502, "MEDALLION | 원천 보존 → 품질 검증 → 업무 판단 근거", 22, 870, True)
    d.layer("bronze", 70, "#9B6A43", "Bronze | Raw", "원천 값·출처를 보존", "01_bronze",
           "bronze.erp_project · 8행\nbronze.bim_design_version · 18행\n원천 값 string + source hash\nSYNTHETIC 16 + 공공 ZEB 1\n완료: bytes hash·행 수 대조")
    d.layer("silver", 535, "#788AA3", "Silver | Enriched", "타입·정체성·관계를 검증", "02_silver",
           "silver.mdm_site_xref · 8행\nsilver.bim_design_version · 18행\ntrim·명시 타입·현행/제출 키 검증\n잘못된 cast·중복/고아 → 중단\n완료: 원천 행 수·metadata 유지")
    d.layer("gold", 1000, "#A47B19", "Gold | Curated", "업무 entity + 계산 결과", "03_gold",
           "gold.site_status · 8행\ngold.option_eval · 63행\ngold.po_status · 25행 / 초과 0\n업무 entity 12 + 계산 결과 3\n완료: 독립 SQL·Decimal 검산")
    d.text(75, 894, "06_public_zeb: 필수 공공 경로가 Bronze → Silver 각 9,760행(p01) 생성 · 가상 현장과 이름 join 금지", 18, 1320)
    d.text(70, 944, "SQL analytics endpoint = Delta 읽기·독립 검산 | 쓰기는 Spark · Gold만 아래 업무 소비 경로의 공통 근거", 18, 1340)

    d.card("ontology", 70, 1040, 405, 250, "ontology", "Ontology | native agent",
           "06  10개 entity · 10개 relationship\n현장 → 설계 → VE·보완안·위험\n키와 관계로 Gold 근거 연결\nPlan → 근거 검토 → Act 검토\n내장 agent로 이유·대안을 질문\n별도 Data agent는 필수 아님")
    d.text(70, 1320, "HS-D: 제출 V2 ↔ 현행 V3\n주거 4등급: SS ≥ 40 또는 PE < 70\n에너지 기준 충족 ≠ 발주·시공 가능", 18, 420)
    d.card("model", 535, 1040, 405, 155, "semantic-model", "Semantic model",
           "07  OneLake Gold → Direct Lake\n4개 테이블 · 관계·측정값 연결\n현장·설계·조합을 같은 기준으로")
    d.card("powerbi", 535, 1235, 405, 155, "power-bi", "Power BI | 현황·비교",
           "07  첫 현황 페이지는 직접 작성\nCopilot으로 보완안 비교 페이지\n질문·인사이트 확인 후 저장")
    d.card("eventhouse", 1000, 1040, 405, 155, "eventhouse", "Eventhouse | 위험 snapshot",
           "08  OneLake snapshot 명시적 수집\n위험 현장 4개 · KQL로 근거 확인\n자동 스트리밍 연결은 아님")
    d.card("operations", 1000, 1235, 405, 155, "operations-agent", "Operations agent",
           "08  snapshot 조회·위험 감시\nopen 위험 → Teams 보완안 제안\n사람 확인 전 실행하지 않음")
    d.text(70, 1450, "승인 기록 | audit는 네 번째 medallion 계층이 아닌 별도 통제·증적 경로", 21, 900, True)
    d.card("audit-store", 70, 1500, 405, 160, "lakehouse", "audit.decision_log",
           "OneLake의 별도 audit schema\n승인 후 검토 결정·근거 hash 기록\nBronze / Silver / Gold 변경 없음")
    d.card("audit", 1000, 1500, 405, 160, "notebook", "Notebook | 결정 기록",
           "10  Confirm 후 action 실행\n05_decision_log → audit만 기록\n07_verify_readonly로 결과 확인")
    d.text(535, 1618, "실제 설계·발주·시공은 바꾸지 않습니다.\n실행 여부·미완료 단계는 별도 확인합니다.", 17, 430)

    d.rect(1490, 350, 370, 530, dashed=True, container=True)
    d.text(1510, 372, "메달리온을 읽는 법", 25, 330, True)
    d.text(1510, 430, "원천에서 판단 근거까지\n계층마다 품질과 책임이 달라집니다.\n\nBronze: 무엇을 받았는가?\nSilver: 어떤 현장·설계인가?\nGold: 어떤 위험·대안인가?\n\nOneLake는 다음 ETL 단계가 아니라\n세 계층 전체의 저장 기반입니다.\n\n실습은 schema로 논리 분리합니다.\n운영의 권한·격리는 별도 설계합니다.", 19, 330)
    d.rect(1490, 940, 370, 350, dashed=True, container=True)
    d.icon("foundry", 1510, 957, 44)
    d.text(1570, 965, "Microsoft Foundry", 23, 280, True)
    d.text(1510, 1006, "09  선택 확장 | 기본 실습 필수 아님", 18, 330)
    d.card("foundry", 1510, 1050, 330, 185, "foundry-agent", "Foundry agent",
           "승인 전 보완안 근거 재검토\nFabric IQ → Ontology 근거\n검토 결과를 Teams로 가져와\n담당자가 최종 판단", dashed=True)
    d.text(1510, 1245, "별도 동의·비용·지역 확인 필요", 18, 330)
    d.rect(1490, 1340, 370, 365, dashed=True, container=True)
    d.card("teams", 1510, 1360, 330, 325, "teams", "Microsoft Teams",
           "08  Agent 제안 수신 후 대기\n현장·설계·보완안의 근거 확인\n필요하면 09 Foundry 재검토\n\n10  담당자 Proceed → Confirm\n기록할 식별자·내용을 검토\n확인 후 Fabric action 실행\n결정 로그 확인 → 감시 종료")

    d.arrow("files-to-bronze", [(270, 480), (270, 535)])
    d.label(290, 480, "01·06 수집", 110)
    d.arrow("bronze-to-silver", [(475, 750), (535, 750)])
    d.label(481, 714, "검증", 40)
    d.arrow("silver-to-gold", [(940, 750), (1000, 750)])
    d.label(946, 714, "계산", 40)
    d.arrow("gold-to-ontology", [(1405, 820), (1430, 820), (1430, 990), (270, 990), (270, 1040)])
    d.arrow("gold-to-directlake", [(1405, 820), (1430, 820), (1430, 990), (735, 990), (735, 1040)])
    d.arrow("gold-to-snapshot", [(1405, 820), (1430, 820), (1430, 990), (1200, 990), (1200, 1040)])
    d.label(290, 1004, "Gold entity·관계", 190)
    d.label(755, 1004, "Direct Lake", 150)
    d.label(1218, 1004, "04_snapshot", 150)
    d.arrow("model-to-powerbi", [(735, 1195), (735, 1235)])
    d.label(760, 1200, "관계·측정값", 135)
    d.arrow("snapshot-to-operations", [(1200, 1195), (1200, 1235)])
    d.label(1220, 1200, "KQL 조회", 110)
    d.arrow("operations-to-teams", [(1405, 1315), (1460, 1315), (1460, 1450), (1510, 1450)])
    d.label(1417, 1300, "제안", 40)
    d.arrow("teams-to-audit", [(1510, 1620), (1405, 1620)])
    d.label(1422, 1590, "확인", 40)
    d.arrow("audit-to-snapshot", [(1200, 1500), (1200, 1460), (965, 1460), (965, 1170), (1000, 1170)])
    d.label(983, 1424, "명시적 recorded 상태 반영", 255)
    d.arrow("audit-to-onelake", [(1000, 1580), (475, 1580)])
    d.label(540, 1544, "승인 기록만 저장 · Gold는 그대로 유지", 415)
    d.arrow("foundry-to-ontology", [(1510, 1135), (1480, 1135), (1480, 1415), (495, 1415), (495, 1240), (475, 1240)], dashed=True)
    d.label(610, 1400, "선택: Fabric IQ → Ontology", 300)
    d.arrow("teams-foundry-review", [(1710, 1235), (1710, 1360)], dashed=True, both=True)
    d.label(1550, 1300, "승인 전 검토 · Teams 복귀", 285)

    d.rect(40, 1750, 1820, 140, dashed=True, container=True)
    d.text(65, 1766, "운영에 적용할 때 | 미래 범위 · 이 워크숍에서는 구현하지 않음", 22, 1750, True)
    d.text(70, 1812, "원천 시스템 연결·증분 수집\nERP·PMS·BIM·SCM 추출·일정 수집", 19, 500)
    d.text(660, 1812, "계층별 권한·품질 통제\n별도 Lakehouse/workspace · 격리·재처리", 19, 560)
    d.text(1260, 1812, "공학·인증 및 승인 후 업무 반영\n효과·시공성·법적 인증·발주 변경 별도", 19, 550)
    d.arrow("legend-core", [(60, 1930), (120, 1930)])
    d.text(135, 1915, "실선: 기본 실습 흐름", 18, 340)
    d.arrow("legend-optional", [(525, 1930), (585, 1930)], dashed=True)
    d.text(600, 1915, "점선: 선택 확장·제품/논리 경계", 18, 610)
    d.text(1340, 1915, "개념 구성도 · 실제 화면 아님", 18, 500)
    d.save()
    print(f"Built Korean medallion SVG + Excalidraw + shared scene ({WIDTH}×{HEIGHT}).")


if __name__ == "__main__":
    build()
