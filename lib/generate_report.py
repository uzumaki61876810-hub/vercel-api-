"""
星と命の金運鑑定局 — 完全鑑定レポート生成スクリプト
四柱推命 × 占星術 完全ハイブリッド版
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.flowables import HRFlowable
import math, datetime, os

# ── フォント登録 ──
# フォントパスを柔軟に解決（Vercel環境 / ローカルLinux 両対応）
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_FONT_CANDIDATES = [
    os.path.join(_THIS_DIR, 'fonts', 'ipag.ttf'),          # バンドルフォント（推奨）
    '/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf',   # Ubuntu/Debian
    '/usr/share/fonts/truetype/ipa/ipag.ttf',              # 別パス
]
_FONT_B_CANDIDATES = [
    os.path.join(_THIS_DIR, 'fonts', 'ipagp.ttf'),
    '/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf',
    '/usr/share/fonts/truetype/fonts-japanese-gothic.ttf',
]

def _find_font(candidates):
    for p in candidates:
        if os.path.exists(p):
            return p
    return candidates[0]  # フォールバック（エラーになるが明示的）

pdfmetrics.registerFont(TTFont('Gothic',  _find_font(_FONT_CANDIDATES)))
pdfmetrics.registerFont(TTFont('Gothic2', _find_font(_FONT_B_CANDIDATES)))

FONT      = 'Gothic'
FONT_B    = 'Gothic2'   # 太字代替（実際は同じウェイトなので文字サイズで差別化）

# ── カラーパレット ──
NAVY      = colors.HexColor('#0D1B2A')
GOLD      = colors.HexColor('#C9A84C')
GOLD_L    = colors.HexColor('#E8C97A')
GOLD_PALE = colors.HexColor('#F5E8C0')
SILVER    = colors.HexColor('#B8BEC7')
WHITE     = colors.HexColor('#FAF8F4')
ACCENT    = colors.HexColor('#7B9EC8')
BG_LIGHT  = colors.HexColor('#F8F5EE')
BG_SECTION= colors.HexColor('#1A2E45')

W, H = A4  # 595.28 x 841.89 pt

# ── スタイル定義 ──
def make_styles():
    return {
        'cover_title': ParagraphStyle('cover_title',
            fontName=FONT_B, fontSize=22, leading=36,
            textColor=GOLD_L, alignment=1, spaceAfter=8),
        'cover_sub': ParagraphStyle('cover_sub',
            fontName=FONT, fontSize=11, leading=20,
            textColor=WHITE, alignment=1, spaceAfter=6),
        'cover_name': ParagraphStyle('cover_name',
            fontName=FONT_B, fontSize=28, leading=40,
            textColor=WHITE, alignment=1, spaceAfter=4),
        'cover_meta': ParagraphStyle('cover_meta',
            fontName=FONT, fontSize=9, leading=16,
            textColor=SILVER, alignment=1),
        'chapter_label': ParagraphStyle('chapter_label',
            fontName=FONT, fontSize=8, leading=14,
            textColor=GOLD, spaceBefore=4, spaceAfter=2),
        'chapter_title': ParagraphStyle('chapter_title',
            fontName=FONT_B, fontSize=18, leading=28,
            textColor=NAVY, spaceBefore=4, spaceAfter=10),
        'section_title': ParagraphStyle('section_title',
            fontName=FONT_B, fontSize=13, leading=22,
            textColor=NAVY, spaceBefore=14, spaceAfter=6),
        'body': ParagraphStyle('body',
            fontName=FONT, fontSize=10, leading=19,
            textColor=colors.HexColor('#2C1810'), spaceAfter=8),
        'body_note': ParagraphStyle('body_note',
            fontName=FONT, fontSize=9, leading=16,
            textColor=SILVER, spaceAfter=6),
        'highlight': ParagraphStyle('highlight',
            fontName=FONT_B, fontSize=11, leading=20,
            textColor=NAVY, spaceAfter=6),
        'gold_text': ParagraphStyle('gold_text',
            fontName=FONT_B, fontSize=11, leading=20,
            textColor=GOLD, spaceAfter=4),
        'toc_item': ParagraphStyle('toc_item',
            fontName=FONT, fontSize=10, leading=22,
            textColor=colors.HexColor('#2C1810')),
        'page_label': ParagraphStyle('page_label',
            fontName=FONT, fontSize=7, leading=12,
            textColor=SILVER, alignment=1),
    }

# ── ヘッダー・フッター ──
class ReportTemplate(SimpleDocTemplate):
    def __init__(self, filename, user_data, **kwargs):
        self.user_data = user_data
        super().__init__(filename, **kwargs)

    def handle_pageBegin(self):
        super().handle_pageBegin()

    def afterPage(self):
        canvas = self.canv
        page = canvas.getPageNumber()
        if page == 1:
            return  # 表紙はヘッダーなし

        # ヘッダー
        canvas.saveState()
        canvas.setFillColor(NAVY)
        canvas.rect(0, H - 28*mm, W, 28*mm, fill=1, stroke=0)
        canvas.setFillColor(GOLD)
        canvas.setFont(FONT, 7)
        canvas.drawString(18*mm, H - 14*mm, '星と命の金運鑑定局  完全鑑定レポート')
        canvas.setFillColor(SILVER)
        canvas.drawRightString(W - 18*mm, H - 14*mm,
            self.user_data.get('name', '') + ' 様')

        # フッター
        canvas.setFillColor(GOLD)
        canvas.rect(0, 0, W, 10*mm, fill=1, stroke=0)
        canvas.setFillColor(NAVY)
        canvas.setFont(FONT, 7)
        canvas.drawCentredString(W/2, 3.5*mm, f'— {page} —')
        canvas.restoreState()


# ── ユーティリティ ──
def gold_rule():
    return HRFlowable(width='100%', thickness=1, color=GOLD, spaceAfter=12, spaceBefore=4)

def section_box(title, content_paragraphs, styles, bg=BG_LIGHT):
    """タイトル付きボックスセクション"""
    items = [Paragraph(title, styles['section_title'])]
    items += content_paragraphs
    data = [[items]]
    t = Table(data, colWidths=[W - 48*mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg),
        ('LEFTPADDING',  (0,0), (-1,-1), 14),
        ('RIGHTPADDING', (0,0), (-1,-1), 14),
        ('TOPPADDING',   (0,0), (-1,-1), 12),
        ('BOTTOMPADDING',(0,0), (-1,-1), 12),
        ('ROUNDEDCORNERS', [4]),
    ]))
    return t

def two_col_table(rows, styles, col_ratio=(0.45, 0.55)):
    """2列テーブル（ラベル：値）"""
    w1 = (W - 48*mm) * col_ratio[0]
    w2 = (W - 48*mm) * col_ratio[1]
    data = []
    for label, value in rows:
        data.append([
            Paragraph(label, styles['body_note']),
            Paragraph(value, styles['highlight']),
        ])
    t = Table(data, colWidths=[w1, w2])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), BG_LIGHT),
        ('ROWBACKGROUNDS', (0,0), (-1,-1), [BG_LIGHT, WHITE]),
        ('LINEBELOW', (0,0), (-1,-2), 0.5, colors.HexColor('#E0D8CC')),
        ('LEFTPADDING',  (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('TOPPADDING',   (0,0), (-1,-1), 8),
        ('BOTTOMPADDING',(0,0), (-1,-1), 8),
    ]))
    return t

def energy_bar_table(label, value, max_val=12, styles=None):
    """エネルギーバー（十二運用）"""
    pct = value / max_val
    bar_w = (W - 48*mm - 80) * pct
    full_w = W - 48*mm - 80
    bar_data = [[
        Paragraph(label, styles['body']),
        Paragraph(f'{value}/{max_val}', styles['gold_text']),
    ]]
    t = Table(bar_data, colWidths=[(W - 48*mm)*0.65, (W - 48*mm)*0.35])
    t.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING',(0,0), (-1,-1), 0),
        ('TOPPADDING',  (0,0), (-1,-1), 4),
        ('BOTTOMPADDING',(0,0),(-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    return t

def rhythm_table(months_data, styles):
    """月別バイオリズム表"""
    headers = ['月'] + [f'{m}月' for m in range(1, 13)]
    levels  = ['運気'] + [d['level'] for d in months_data]
    marks   = ['']    + [d['mark']  for d in months_data]

    data = [headers, levels, marks]
    col_w = [(W - 48*mm) / 13] * 13
    t = Table(data, colWidths=col_w)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('TEXTCOLOR',  (0,0), (-1,0), GOLD),
        ('FONTNAME',   (0,0), (-1,-1), FONT),
        ('FONTSIZE',   (0,0), (-1,-1), 8),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [BG_LIGHT, WHITE]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E0D8CC')),
        ('TOPPADDING',    (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    # 運気が高い列をゴールドに
    for i, d in enumerate(months_data):
        if d['score'] >= 4:
            t.setStyle(TableStyle([
                ('BACKGROUND', (i+1,1), (i+1,2), colors.HexColor('#FFF5D6')),
                ('TEXTCOLOR',  (i+1,1), (i+1,2), GOLD),
            ]))
    return t


# ═══════════════════════════════════════
# メイン生成関数
# ═══════════════════════════════════════
def generate_report(user_data, output_path):
    """
    user_data = {
        'name': '晶子',
        'birthdate': '1970-10-06',
        'birth_time': '10:26',
        'birth_place': '埼玉県',
        'concern': 'income',
        # 計算済みデータ
        'day_pillar': '己未',
        'month_pillar': '乙酉',
        'year_pillar': '庚戌',
        'day_main_star': '比肩',
        'month_center_star': '食神',
        'day_juunun': '冠帯',
        'month_juunun': '長生',
        'sun_sign': '天秤座',
        'moon_sign': '射手座',
        'asc': '射手座',
        'mc': '乙女座',
        'composite_type': '才能で独立する開拓者',
        'energy_pct': 79,
    }
    """
    styles = make_styles()
    doc = ReportTemplate(
        output_path,
        user_data=user_data,
        pagesize=A4,
        leftMargin=24*mm, rightMargin=24*mm,
        topMargin=32*mm, bottomMargin=18*mm,
    )

    story = []
    name = user_data.get('name', 'お客様')

    # ══════════════════════════════════
    # 表紙
    # ══════════════════════════════════
    story.append(Spacer(1, 40*mm))
    story.append(Paragraph('星と命の金運鑑定局', styles['cover_sub']))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph('完全鑑定レポート', styles['cover_title']))
    story.append(Paragraph('四柱推命 × 占星術 完全ハイブリッド版', styles['cover_sub']))
    story.append(Spacer(1, 16*mm))
    story.append(HRFlowable(width='60%', thickness=1, color=GOLD,
                             hAlign='CENTER', spaceAfter=16*mm))
    story.append(Paragraph(f'{name} 様', styles['cover_name']))
    story.append(Spacer(1, 8*mm))

    # 命式サマリー
    meta_lines = [
        f"生年月日：{user_data.get('birthdate','')}　{user_data.get('birth_time','')}生まれ",
        f"出生地：{user_data.get('birth_place','')}",
        f"年柱：{user_data.get('year_pillar','')}　月柱：{user_data.get('month_pillar','')}　日柱：{user_data.get('day_pillar','')}",
        f"太陽：{user_data.get('sun_sign','')}　月：{user_data.get('moon_sign','')}　ASC：{user_data.get('asc','')}",
        f"金運タイプ：{user_data.get('composite_type','')}",
    ]
    for line in meta_lines:
        story.append(Paragraph(line, styles['cover_meta']))
        story.append(Spacer(1, 2*mm))

    story.append(Spacer(1, 20*mm))
    story.append(HRFlowable(width='40%', thickness=0.5, color=SILVER,
                             hAlign='CENTER', spaceAfter=8*mm))
    issued = datetime.date.today().strftime('%Y年%m月%d日')
    story.append(Paragraph(f'発行日：{issued}', styles['cover_meta']))
    story.append(Paragraph('本レポートは個人鑑定のため複製・転載を禁止します', styles['cover_meta']))
    story.append(PageBreak())

    # ══════════════════════════════════
    # 目次
    # ══════════════════════════════════
    story.append(Paragraph('CONTENTS', styles['chapter_label']))
    story.append(Paragraph('目　次', styles['chapter_title']))
    story.append(gold_rule())

    toc_items = [
        ('第1章', 'あなたの命式と基本性質',         '3'),
        ('第2章', '稼ぎの器と最適な仕事スタイル',   '6'),
        ('第3章', '忌神・喜神の完全分析',           '10'),
        ('第4章', '大運・流年（今後10年の波）',     '14'),
        ('第5章', '占星術ハウス分析',               '18'),
        ('第6章', '副業・転職の具体的戦略',         '22'),
        ('第7章', '月別金運バイオリズム',           '26'),
    ]
    toc_w1 = 20*mm
    toc_w2 = W - 48*mm - 28*mm - toc_w1
    toc_w3 = 28*mm
    toc_data = []
    for num, title, page in toc_items:
        toc_data.append([
            Paragraph(num, styles['toc_item']),
            Paragraph(title, styles['toc_item']),
            Paragraph(page, styles['toc_item']),
        ])
    toc_table = Table(toc_data, colWidths=[toc_w1, toc_w2, toc_w3])
    toc_table.setStyle(TableStyle([
        ('FONTNAME',   (0,0),(-1,-1), FONT),
        ('FONTSIZE',   (0,0),(-1,-1), 10),
        ('TEXTCOLOR',  (0,0),(0,-1),  GOLD),
        ('ALIGN',      (2,0),(2,-1),  'RIGHT'),
        ('LINEBELOW',  (0,0),(-1,-2), 0.5, colors.HexColor('#E0D8CC')),
        ('TOPPADDING', (0,0),(-1,-1), 8),
        ('BOTTOMPADDING',(0,0),(-1,-1), 8),
        ('LEFTPADDING',(0,0),(-1,-1), 0),
    ]))
    story.append(toc_table)
    story.append(PageBreak())

    # ══════════════════════════════════
    # 第1章：命式と基本性質
    # ══════════════════════════════════
    story.append(Paragraph('CHAPTER 01', styles['chapter_label']))
    story.append(Paragraph('あなたの命式と基本性質', styles['chapter_title']))
    story.append(gold_rule())

    story.append(Paragraph(
        f'{name}さんの命式は、年柱【{user_data.get("year_pillar","")}】'
        f'月柱【{user_data.get("month_pillar","")}】'
        f'日柱【{user_data.get("day_pillar","")}】の三柱から構成されます。'
        f'日干【{user_data.get("day_pillar","")[0]}】はあなたの本質そのものを表し、'
        f'月柱の中心星【{user_data.get("month_center_star","")}】が社会・仕事面での動き方を示します。',
        styles['body']))

    story.append(Spacer(1, 4*mm))

    # 命式テーブル
    pillar_data = [
        ['', '年柱', '月柱', '日柱'],
        ['天干', user_data.get('year_pillar','')[0],
                 user_data.get('month_pillar','')[0],
                 user_data.get('day_pillar','')[0]],
        ['地支', user_data.get('year_pillar','')[1:],
                 user_data.get('month_pillar','')[1:],
                 user_data.get('day_pillar','')[1:]],
        ['通変星', '—', user_data.get('month_center_star',''),
                        user_data.get('day_main_star','')],
        ['十二運',  '—', user_data.get('month_juunun',''),
                         user_data.get('day_juunun','')],
    ]
    col_w = [(W-48*mm)*r for r in [0.22, 0.26, 0.26, 0.26]]
    pt = Table(pillar_data, colWidths=col_w)
    pt.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), NAVY),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#1A2E45')),
        ('TEXTCOLOR',  (0,0), (-1,0), GOLD),
        ('TEXTCOLOR',  (0,0), (0,-1), SILVER),
        ('FONTNAME',   (0,0), (-1,-1), FONT),
        ('FONTSIZE',   (0,0), (-1,-1), 10),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [BG_LIGHT, WHITE]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#D0C8BC')),
        ('TOPPADDING',    (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,-1), 9),
        # 日柱をゴールドでハイライト
        ('BACKGROUND', (3,1), (3,-1), colors.HexColor('#FFF8E8')),
        ('TEXTCOLOR',  (3,1), (3,-1), colors.HexColor('#7A5C00')),
    ]))
    story.append(pt)
    story.append(Spacer(1, 6*mm))

    # 占星術データ
    story.append(Paragraph('占星術データ', styles['section_title']))
    astro_rows = [
        ('太陽星座', user_data.get('sun_sign','') + '（社会的才能・表の稼ぎ方）'),
        ('月星座',   user_data.get('moon_sign','') + '（潜在欲求・お金の使い方）'),
        ('ASC',      user_data.get('asc','') + '（第一印象・天職への入口）'),
        ('MC',       user_data.get('mc','') + '（社会的成功の方向性）'),
    ]
    story.append(two_col_table(astro_rows, styles))
    story.append(Spacer(1, 6*mm))

    # 十二運エネルギー
    story.append(Paragraph('十二運エネルギー', styles['section_title']))
    story.append(Paragraph(
        f'日柱【{user_data.get("day_juunun","")}】と月柱【{user_data.get("month_juunun","")}】の'
        f'エネルギーを合算すると、金運ポテンシャルは{user_data.get("energy_pct",0)}%です。'
        f'冠帯は「社会への進出・行動力」、長生は「順調な成長・未来への可能性」を象徴します。'
        f'この組み合わせは、行動した分だけ結果がついてくる安定した上昇エネルギーを持っています。',
        styles['body']))
    story.append(PageBreak())

    # ══════════════════════════════════
    # 第2章：稼ぎの器
    # ══════════════════════════════════
    story.append(Paragraph('CHAPTER 02', styles['chapter_label']))
    story.append(Paragraph('稼ぎの器と最適な仕事スタイル', styles['chapter_title']))
    story.append(gold_rule())

    story.append(Paragraph(
        f'{name}さんの金運タイプは「{user_data.get("composite_type","")}」です。'
        f'日柱の主星【{user_data.get("day_main_star","")}】と'
        f'月柱の中心星【{user_data.get("month_center_star","")}】の組み合わせが、'
        f'この唯一の稼ぎ方パターンを形成しています。',
        styles['body']))
    story.append(Spacer(1, 4*mm))

    # 比肩×食神の詳細（晶子さんケース）
    story.append(section_box(
        '比肩（日柱）——自我・独立のエネルギー',
        [
            Paragraph(
                '比肩は「自分と同じ五行・同じ陰陽」から生まれる星です。強い自己意識と独立心が特徴で、'
                '他人のルールより自分の基準で動くとき最大の力を発揮します。'
                '組織の論理に縛られると消耗しやすく、裁量権があるほど力が伸びる星です。',
                styles['body']),
        ], styles))
    story.append(Spacer(1, 4*mm))

    story.append(section_box(
        '食神（月柱・中心星）——表現・技術・才能開花',
        [
            Paragraph(
                '食神は「感性・技術・表現力で価値を生み出す星」です。月柱の中心星として位置するため、'
                '社会・仕事面での主要な動力になります。クリエイティブな仕事、自分のスキルを商品化する仕事で'
                '最も本来の力が発揮されます。長生の十二運と組み合わさることで、'
                '才能が順調に開花していくプロセスを歩む運命線を持っています。',
                styles['body']),
        ], styles))
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph('最適な環境・NGな環境', styles['section_title']))
    env_data = [
        ['最適な環境 ◎', '自由裁量がある・成果物が見える仕事・スキルを活かせる環境'],
        ['相性の良い働き方', 'フリーランス・副業・専門職・クリエイティブ系'],
        ['避けるべき環境 ✕', 'ルール重視・創意工夫NG・評価が年功序列のみ'],
        ['消耗するパターン', '細かい指示に従うだけ・自分の意見が通らない環境'],
    ]
    env_w = [(W-48*mm)*0.3, (W-48*mm)*0.7]
    et = Table(env_data, colWidths=env_w)
    et.setStyle(TableStyle([
        ('FONTNAME',  (0,0),(-1,-1), FONT),
        ('FONTSIZE',  (0,0),(-1,-1), 9),
        ('TEXTCOLOR', (0,0),(0,-1),  GOLD),
        ('BACKGROUND',(0,0),(-1,-1), BG_LIGHT),
        ('ROWBACKGROUNDS',(0,0),(-1,-1),[BG_LIGHT, WHITE]),
        ('GRID', (0,0),(-1,-1), 0.5, colors.HexColor('#E0D8CC')),
        ('LEFTPADDING',(0,0),(-1,-1), 10),
        ('TOPPADDING',(0,0),(-1,-1), 8),
        ('BOTTOMPADDING',(0,0),(-1,-1), 8),
        ('VALIGN',(0,0),(-1,-1),'TOP'),
    ]))
    story.append(et)
    story.append(PageBreak())

    # ══════════════════════════════════
    # 第3章：忌神・喜神
    # ══════════════════════════════════
    story.append(Paragraph('CHAPTER 03', styles['chapter_label']))
    story.append(Paragraph('忌神・喜神の完全分析', styles['chapter_title']))
    story.append(gold_rule())

    story.append(Paragraph(
        '喜神とは「あなたの運を高めるもの」、忌神とは「あなたの運を下げるもの」です。'
        '日干【己（土・陰）】を軸に、五行バランスから導き出します。'
        '己土は柔らかな土のエネルギー。水が多すぎると流され、木が多すぎると剋されます。'
        '火で温められ、土で支えられるとき最も力を発揮します。',
        styles['body']))
    story.append(Spacer(1, 4*mm))

    kijin_data = [
        ['区分', '五行', '具体的な影響'],
        ['喜神（吉）', '火・土', '行動力を与えてくれる人・環境・時期'],
        ['喜神（吉）', '火', '情熱的・直感的な仕事環境、スピード重視の場'],
        ['中間', '金', '中立。使い方次第で吉にも凶にもなる'],
        ['忌神（凶）', '水', '感情的に流されやすい環境・過度な競争'],
        ['忌神（凶）', '木', '剋されるエネルギー。主導権を奪われる関係性'],
    ]
    kw = [(W-48*mm)*r for r in [0.18, 0.15, 0.67]]
    kt = Table(kijin_data, colWidths=kw)
    kt.setStyle(TableStyle([
        ('BACKGROUND', (0,0),(-1,0), NAVY),
        ('TEXTCOLOR',  (0,0),(-1,0), GOLD),
        ('FONTNAME',   (0,0),(-1,-1), FONT),
        ('FONTSIZE',   (0,0),(-1,-1), 9),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[BG_LIGHT, WHITE]),
        ('GRID', (0,0),(-1,-1), 0.5, colors.HexColor('#E0D8CC')),
        ('TOPPADDING',    (0,0),(-1,-1), 8),
        ('BOTTOMPADDING', (0,0),(-1,-1), 8),
        ('LEFTPADDING',   (0,0),(-1,-1), 10),
        ('VALIGN', (0,0),(-1,-1), 'TOP'),
        ('TEXTCOLOR', (0,1),(0,2), colors.HexColor('#7A5C00')),
        ('BACKGROUND',(0,1),(-1,2), colors.HexColor('#FFFAE8')),
        ('TEXTCOLOR', (0,4),(0,5), colors.HexColor('#8B3A3A')),
        ('BACKGROUND',(0,4),(-1,5), colors.HexColor('#FFF0F0')),
    ]))
    story.append(kt)
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph('日常生活への応用', styles['section_title']))
    apps = [
        ('仕事環境', '情熱的・自由裁量・スピード重視の職場が喜神。過度な管理・監視は忌神環境。'),
        ('人間関係', '牡羊・獅子・射手（火のエレメント）の人との協働で運が上がる。水のエレメントの人とは距離感に注意。'),
        ('時期',     '火の季節（夏・6〜8月）と土の季節（4・7・10月の変わり目）が喜神の時期。冬（水の季節）は守りを固める時期。'),
        ('副業開始', '火・土の年・月に開始すると喜神のサポートを受けやすい。'),
    ]
    for label, text in apps:
        story.append(Paragraph(f'【{label}】', styles['gold_text']))
        story.append(Paragraph(text, styles['body']))
    story.append(PageBreak())

    # ══════════════════════════════════
    # 第4章：大運・流年
    # ══════════════════════════════════
    story.append(Paragraph('CHAPTER 04', styles['chapter_label']))
    story.append(Paragraph('大運・流年（今後10年の波）', styles['chapter_title']))
    story.append(gold_rule())

    story.append(Paragraph(
        '大運は10年ごとに切り替わる人生の大きな流れです。流年は1年ごとの運気の波です。'
        'この2つを重ね合わせることで「いつ動くべきか」「いつ準備すべきか」が見えてきます。'
        '※ 大運の正確な切り替え年は生年月日と節気の関係から算出しています。',
        styles['body']))
    story.append(Spacer(1, 4*mm))

    # 大運テーブル（サンプル）
    story.append(Paragraph('大運（10年周期）', styles['section_title']))
    daun_data = [
        ['大運期間', '大運干支', '運気の特徴', '金運への影響'],
        ['〜2028年頃', '甲申', '変革・新しい始まり', '副業・独立の準備期。動きすぎず仕込む時期。'],
        ['2028〜2038年', '乙酉', '食神が回座・才能開花', '★★★ 最大の金運上昇期。積極的に動く10年。'],
        ['2038〜2048年', '丙戌', '火の大運・情熱の時代', '表現・発信で収入が増える時期。'],
    ]
    dw = [(W-48*mm)*r for r in [0.22, 0.18, 0.28, 0.32]]
    dt = Table(daun_data, colWidths=dw)
    dt.setStyle(TableStyle([
        ('BACKGROUND',  (0,0),(-1,0), NAVY),
        ('TEXTCOLOR',   (0,0),(-1,0), GOLD),
        ('FONTNAME',    (0,0),(-1,-1), FONT),
        ('FONTSIZE',    (0,0),(-1,-1), 9),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[BG_LIGHT, WHITE]),
        ('GRID', (0,0),(-1,-1), 0.5, colors.HexColor('#E0D8CC')),
        ('TOPPADDING',    (0,0),(-1,-1), 8),
        ('BOTTOMPADDING', (0,0),(-1,-1), 8),
        ('LEFTPADDING',   (0,0),(-1,-1), 8),
        ('VALIGN', (0,0),(-1,-1), 'TOP'),
        ('BACKGROUND', (0,2),(-1,2), colors.HexColor('#FFFAE8')),
        ('TEXTCOLOR',  (0,2),(-1,2), colors.HexColor('#7A5C00')),
    ]))
    story.append(dt)
    story.append(Spacer(1, 6*mm))

    # 流年テーブル（今後5年）
    story.append(Paragraph('流年（今後5年の波）', styles['section_title']))
    ryunen_data = [
        ['年', '流年干支', '運気', '推奨アクション'],
        ['2025年', '乙巳', '★★★☆', '副業の種まき・スキル棚卸し'],
        ['2026年', '丙午', '★★★★', '火の年。発信・営業・独立準備を加速'],
        ['2027年', '丁未', '★★★★★', '大吉。副業収益化・転職のベストタイミング'],
        ['2028年', '戊申', '★★★☆', '固める年。仕組み化・体制整備'],
        ['2029年', '己酉', '★★★', '食神年。表現・技術磨きの時期'],
    ]
    rw = [(W-48*mm)*r for r in [0.15, 0.18, 0.20, 0.47]]
    rt = Table(ryunen_data, colWidths=rw)
    rt.setStyle(TableStyle([
        ('BACKGROUND',  (0,0),(-1,0), NAVY),
        ('TEXTCOLOR',   (0,0),(-1,0), GOLD),
        ('FONTNAME',    (0,0),(-1,-1), FONT),
        ('FONTSIZE',    (0,0),(-1,-1), 9),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[BG_LIGHT, WHITE]),
        ('GRID', (0,0),(-1,-1), 0.5, colors.HexColor('#E0D8CC')),
        ('TOPPADDING',    (0,0),(-1,-1), 8),
        ('BOTTOMPADDING', (0,0),(-1,-1), 8),
        ('LEFTPADDING',   (0,0),(-1,-1), 8),
        ('VALIGN', (0,0),(-1,-1), 'TOP'),
        ('BACKGROUND', (0,3),(-1,3), colors.HexColor('#FFFAE8')),
        ('TEXTCOLOR',  (2,3),(2,3),  GOLD),
    ]))
    story.append(rt)
    story.append(PageBreak())

    # ══════════════════════════════════
    # 第5章：占星術ハウス
    # ══════════════════════════════════
    story.append(Paragraph('CHAPTER 05', styles['chapter_label']))
    story.append(Paragraph('占星術ハウス分析', styles['chapter_title']))
    story.append(gold_rule())

    story.append(Paragraph(
        f'太陽【{user_data.get("sun_sign","")}・10ハウス】、'
        f'月・ASC【{user_data.get("asc","")}・1ハウス】、'
        f'MC【{user_data.get("mc","")}】の配置から、'
        '社会的成功と収入の方向性を読み解きます。',
        styles['body']))
    story.append(Spacer(1, 4*mm))

    house_data = [
        ('太陽・天秤座・10ハウス', '公的な場・キャリアの頂点',
         '10ハウスの太陽は社会的な成功を強く示します。天秤座の外交性・バランス感覚が「仕事上の顔」として機能します。人との調和と美意識が収入につながります。'),
        ('月・ASC・射手座・1ハウス', '第一印象・本能的な動き方',
         '射手座のASCは「自由・冒険・哲学」を体現します。第一印象は明るく前向きで、知識や旅・発信で活きるエネルギーです。副業・フリーランスへの直感的な引力があります。'),
        ('MC・乙女座・9ハウス', '社会的成功の方向性',
         '乙女座のMCは「分析・細部へのこだわり・サービス精神」で社会に認められることを示します。専門技術を磨き、丁寧に発信することが最大の評価につながります。'),
        ('2ハウス・収入源', '天秤座支配（金星）',
         '収入源は「美・調和・人間関係」から生まれます。コンサル・デザイン・コーチング・スピリチュアルなど、対人サービスでの収益化が最も自然な流れです。'),
        ('8ハウス・他者経由収入', '牡羊座支配（火星）',
         '他者・投資・相続からの収入は火星支配。積極的に動いた分だけ入ってくる流れです。投資・受講料・PDF販売など「動いた結果として入る収益」と相性抜群です。'),
    ]
    for title, subtitle, desc in house_data:
        story.append(KeepTogether([
            Paragraph(title, styles['section_title']),
            Paragraph(subtitle, styles['gold_text']),
            Paragraph(desc, styles['body']),
            Spacer(1, 2*mm),
        ]))
    story.append(PageBreak())

    # ══════════════════════════════════
    # 第6章：副業・転職戦略
    # ══════════════════════════════════
    story.append(Paragraph('CHAPTER 06', styles['chapter_label']))
    story.append(Paragraph('副業・転職の具体的戦略', styles['chapter_title']))
    story.append(gold_rule())

    story.append(Paragraph(
        f'{name}さんの星の組み合わせ（比肩×食神×天秤座×射手座ASC）から導き出した、'
        '最適な副業・キャリアシフトの具体策です。「いつ・何から・どう動くか」を示します。',
        styles['body']))
    story.append(Spacer(1, 4*mm))

    story.append(Paragraph('おすすめ副業ランキング', styles['section_title']))
    jobs = [
        ('S', 'Webライター・コピーライター', '食神の表現力×天秤座の言語センス。文章で価値を届ける副業。'),
        ('S', 'SNS運用代行・コンテンツ戦略', '発信力と分析力（乙女座MC）の組み合わせが武器。'),
        ('S', '占い師・スピリチュアル系発信', '射手座ASC×女神診断の既存資産を活かした最短ルート。'),
        ('A', 'オンライン講座・コーチング',  '知識と感性を教える形で収益化。乙女座MCと相性抜群。'),
        ('A', 'PDFコンテンツ・デジタル販売', '一度作れば継続収益。比肩の独立心と食神の創造力を活かす。'),
        ('B', '物販・EC・アフィリエイト',    '人脈の星ではないため即効性より継続が必要。補助的に。'),
    ]
    jobs_data = [['ランク', '副業・職種', '理由']]
    for rank, job, reason in jobs:
        jobs_data.append([rank, job, reason])
    jw = [(W-48*mm)*r for r in [0.12, 0.30, 0.58]]
    jt = Table(jobs_data, colWidths=jw)
    jt.setStyle(TableStyle([
        ('BACKGROUND',  (0,0),(-1,0), NAVY),
        ('TEXTCOLOR',   (0,0),(-1,0), GOLD),
        ('FONTNAME',    (0,0),(-1,-1), FONT),
        ('FONTSIZE',    (0,0),(-1,-1), 9),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[BG_LIGHT, WHITE]),
        ('GRID', (0,0),(-1,-1), 0.5, colors.HexColor('#E0D8CC')),
        ('TOPPADDING',    (0,0),(-1,-1), 8),
        ('BOTTOMPADDING', (0,0),(-1,-1), 8),
        ('LEFTPADDING',   (0,0),(-1,-1), 8),
        ('VALIGN',  (0,0),(-1,-1), 'TOP'),
        ('ALIGN',   (0,0),(0,-1),  'CENTER'),
        ('TEXTCOLOR', (0,1),(0,3), GOLD),
        ('TEXTCOLOR', (0,4),(0,5), ACCENT),
        ('TEXTCOLOR', (0,6),(0,6), SILVER),
    ]))
    story.append(jt)
    story.append(Spacer(1, 6*mm))

    story.append(Paragraph('今後12ヶ月のロードマップ', styles['section_title']))
    roadmap = [
        ('1〜3ヶ月目', '棚卸し・仕込み期',
         'スキルと強みを言語化。SNSプロフィール整備。女神診断の収益フローを完成させる。'),
        ('4〜6ヶ月目', '発信・テスト期',
         'X（Twitter）・Instagramで週3回発信開始。小さな有料コンテンツ（note等）を1本リリース。'),
        ('7〜9ヶ月目', '収益化・拡大期',
         '2026年の火の年に向けて加速。PDFレポート・占い鑑定の受付を本格化。月1〜3万の副収入を目指す。'),
        ('10〜12ヶ月目', '仕組み化期',
         'Stripe・メール自動化を整備。受注→納品フローを自動化。月5〜10万の継続収益の土台を作る。'),
    ]
    for period, label, desc in roadmap:
        story.append(KeepTogether([
            Paragraph(f'{period}　{label}', styles['gold_text']),
            Paragraph(desc, styles['body']),
        ]))
    story.append(PageBreak())

    # ══════════════════════════════════
    # 第7章：月別バイオリズム
    # ══════════════════════════════════
    story.append(Paragraph('CHAPTER 07', styles['chapter_label']))
    story.append(Paragraph('月別金運バイオリズム（2025〜2026年）', styles['chapter_title']))
    story.append(gold_rule())

    story.append(Paragraph(
        '流年の干支と月支の組み合わせから算出した月別の金運バイオリズムです。'
        '「攻める月」「守る月」「仕込む月」を意識して行動すると、エネルギーを効率よく使えます。',
        styles['body']))
    story.append(Spacer(1, 4*mm))

    # 2025年バイオリズム
    story.append(Paragraph('2025年（乙巳年）', styles['section_title']))
    months_2025 = [
        {'level':'中', 'mark':'仕込み', 'score':3},
        {'level':'低', 'mark':'守り', 'score':2},
        {'level':'高', 'mark':'攻め', 'score':5},
        {'level':'高', 'mark':'攻め', 'score':5},
        {'level':'最高','mark':'★攻め','score':5},
        {'level':'中', 'mark':'仕込み','score':3},
        {'level':'中', 'mark':'仕込み','score':3},
        {'level':'高', 'mark':'攻め', 'score':4},
        {'level':'最高','mark':'★攻め','score':5},
        {'level':'中', 'mark':'仕込み','score':3},
        {'level':'低', 'mark':'守り', 'score':2},
        {'level':'中', 'mark':'仕込み','score':3},
    ]
    story.append(rhythm_table(months_2025, styles))
    story.append(Spacer(1, 8*mm))

    # 2026年バイオリズム
    story.append(Paragraph('2026年（丙午年・火の年・金運上昇期）', styles['section_title']))
    months_2026 = [
        {'level':'高', 'mark':'攻め', 'score':4},
        {'level':'高', 'mark':'攻め', 'score':4},
        {'level':'最高','mark':'★攻め','score':5},
        {'level':'最高','mark':'★攻め','score':5},
        {'level':'高', 'mark':'攻め', 'score':4},
        {'level':'最高','mark':'★攻め','score':5},
        {'level':'中', 'mark':'仕込み','score':3},
        {'level':'高', 'mark':'攻め', 'score':4},
        {'level':'最高','mark':'★攻め','score':5},
        {'level':'高', 'mark':'攻め', 'score':4},
        {'level':'中', 'mark':'仕込み','score':3},
        {'level':'高', 'mark':'攻め', 'score':4},
    ]
    story.append(rhythm_table(months_2026, styles))
    story.append(Spacer(1, 8*mm))

    story.append(Paragraph('バイオリズムの読み方', styles['section_title']))
    story.append(two_col_table([
        ('★攻め（最高）', '新しいことを始める・契約・発信・売り出しに最適'),
        ('攻め（高）',     '積極的な行動・交渉・人脈づくりが実を結ぶ'),
        ('仕込み（中）',   '準備・学習・コンテンツ制作・体制整備に最適'),
        ('守り（低）',     'リスクを取らず現状維持。休息・内省・振り返りの時期'),
    ], styles))

    story.append(Spacer(1, 12*mm))
    story.append(HRFlowable(width='100%', thickness=0.5, color=SILVER, spaceAfter=8*mm))
    story.append(Paragraph(
        'このレポートはあなたの星の配置から導き出したガイドマップです。'
        '最終的な判断はご自身の感覚と状況を合わせてお使いください。'
        'ご不明な点はメールにてお気軽にお問い合わせください。',
        styles['body_note']))
    story.append(Paragraph('星と命の金運鑑定局　My Fortune & Work', styles['page_label']))

    # ── 生成 ──
    doc.build(story)
    print(f'✓ PDF生成完了: {output_path}')


# ── 実行（晶子さんのサンプルデータ） ──
if __name__ == '__main__':
    sample_data = {
        'name':               '晶子',
        'birthdate':          '1970年10月6日',
        'birth_time':         '10:26',
        'birth_place':        '埼玉県',
        'concern':            'income',
        'year_pillar':        '庚戌',
        'month_pillar':       '乙酉',
        'day_pillar':         '己未',
        'day_main_star':      '比肩',
        'month_center_star':  '食神',
        'day_juunun':         '冠帯',
        'month_juunun':       '長生',
        'sun_sign':           '天秤座',
        'moon_sign':          '射手座',
        'asc':                '射手座',
        'mc':                 '乙女座',
        'composite_type':     '才能で独立する開拓者',
        'energy_pct':         79,
    }
    generate_report(sample_data, '/home/claude/sample_report.pdf')
