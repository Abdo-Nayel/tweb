from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_ARABIC_FONT = None
_ARABIC_FONT_PATH = None
_ARABIC_RESHAPER = None


def _has_arabic(text):
    return bool(text) and any('\u0600' <= ch <= '\u06FF' for ch in str(text))


def _resolve_arabic_font_path():
    static_fonts = Path(settings.BASE_DIR) / 'static' / 'fonts'
    candidates = [
        static_fonts / 'NotoSansArabic-Regular.ttf',
        static_fonts / 'Amiri-Regular.ttf',
        Path('/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf'),
        Path('/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf'),
        Path('/usr/share/fonts/opentype/noto/NotoSansArabic-Regular.ttf'),
    ]
    for path in candidates:
        if path.exists():
            return path
    raise RuntimeError(
        'Arabic PDF font not found. Place NotoSansArabic-Regular.ttf in static/fonts/ '
        'or install fonts-noto-arabic on the server.'
    )


def _arabic_font_name():
    global _ARABIC_FONT, _ARABIC_FONT_PATH
    if _ARABIC_FONT:
        return _ARABIC_FONT

    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    font_path = _resolve_arabic_font_path()
    _ARABIC_FONT_PATH = font_path
    pdfmetrics.registerFont(TTFont('AppArabic', str(font_path)))
    _ARABIC_FONT = 'AppArabic'
    return _ARABIC_FONT


def _get_reshaper():
    global _ARABIC_RESHAPER, _ARABIC_FONT_PATH
    if _ARABIC_RESHAPER:
        return _ARABIC_RESHAPER

    import arabic_reshaper

    if not _ARABIC_FONT_PATH:
        _arabic_font_name()
    try:
        config = arabic_reshaper.config_for_true_type_font(str(_ARABIC_FONT_PATH))
        _ARABIC_RESHAPER = arabic_reshaper.ArabicReshaper(config)
    except ImportError:
        _ARABIC_RESHAPER = arabic_reshaper.ArabicReshaper()
    return _ARABIC_RESHAPER


def _arabic_pdf_text(text):
    """تشكيل الحروف + ترتيب bidi — مطلوب لعرض العربي صحيحاً في ReportLab."""
    if not text:
        return ''
    s = str(text)
    if not _has_arabic(s):
        return s
    from bidi.algorithm import get_display

    reshaper = _get_reshaper()
    return get_display(reshaper.reshape(s))


def _pdf_cell(text, style):
    safe = str(text or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    return Paragraph(_arabic_pdf_text(safe).replace('\n', '<br/>'), style)


def _rtl_row(cells):
    """عكس ترتيب الأعمدة — ReportLab يرسم من اليسار لليمين."""
    return list(reversed(cells))


def _ledger_rows(entries, total_in, total_out, net_balance, current_balance, title):
    rows = [_rtl_row(['التاريخ', 'المرجع', 'البيان', 'وارد', 'صادر'])]
    for e in entries:
        rows.append(_rtl_row([
            str(e['date']),
            e['ref'] or '',
            e['desc'] or '',
            str(e['in']) if e['in'] else '',
            str(e['out']) if e['out'] else '',
        ]))
    rows.append(_rtl_row(['', '', 'إجمالي الفترة', str(total_in), str(total_out)]))
    rows.append(_rtl_row(['', '', 'صافي الفترة', str(net_balance), '']))
    rows.append(_rtl_row(['', '', 'الرصيد الحالي', str(current_balance), '']))
    return rows


def export_ledger_excel(entries, total_in, total_out, net_balance, current_balance, title, filename):
    wb = Workbook()
    ws = wb.active
    ws.title = 'كشف حساب'
    ws.append([title])
    ws.append([])
    for row in _ledger_rows(entries, total_in, total_out, net_balance, current_balance, title)[1:]:
        ws.append(list(reversed(row)))
    buf = BytesIO()
    wb.save(buf)
    response = HttpResponse(
        buf.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def export_ledger_pdf(entries, total_in, total_out, net_balance, current_balance, title, filename):
    return export_table_pdf(
        title=title,
        headers=['التاريخ', 'المرجع', 'البيان', 'وارد', 'صادر'],
        rows=[
            [
                str(e['date']), e['ref'] or '', e['desc'] or '',
                str(e['in']) if e['in'] else '', str(e['out']) if e['out'] else '',
            ]
            for e in entries
        ],
        footer_rows=[
            ['', '', 'إجمالي الفترة', str(total_in), str(total_out)],
            ['', '', 'صافي الفترة', str(net_balance), ''],
            ['', '', 'الرصيد الحالي', str(current_balance), ''],
        ],
        filename=filename,
    )


def export_table_pdf(title, headers, rows, filename, footer_rows=None, landscape_mode=True):
    font = _arabic_font_name()
    cell_style = ParagraphStyle(
        name='PdfCell',
        fontName=font,
        fontSize=9,
        alignment=TA_RIGHT,
        leading=13,
        wordWrap='RTL',
    )
    title_style = ParagraphStyle(
        name='PdfTitle',
        fontName=font,
        fontSize=16,
        alignment=TA_CENTER,
        leading=20,
        textColor=colors.HexColor('#1e3a5f'),
        wordWrap='RTL',
    )
    header_style = ParagraphStyle(
        name='PdfHeader',
        fontName=font,
        fontSize=10,
        alignment=TA_CENTER,
        leading=12,
        textColor=colors.white,
        wordWrap='RTL',
    )

    buf = BytesIO()
    page = landscape(A4) if landscape_mode else A4
    doc = SimpleDocTemplate(buf, pagesize=page, rightMargin=28, leftMargin=28, topMargin=28, bottomMargin=28)
    story = [_pdf_cell(title, title_style), Spacer(1, 14)]

    rtl_headers = _rtl_row(headers)
    data = [[_pdf_cell(cell, header_style) for cell in rtl_headers]]
    for row in rows:
        data.append([_pdf_cell(cell, cell_style) for cell in _rtl_row(row)])
    for row in footer_rows or []:
        data.append([_pdf_cell(cell, cell_style) for cell in _rtl_row(row)])

    table = Table(data, repeatRows=1)
    footer_start = len(data) - len(footer_rows or [])
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3d6a99')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#cbd5e1')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
    ]
    if footer_rows:
        style_cmds.append(('BACKGROUND', (0, footer_start), (-1, -1), colors.HexColor('#f1f5f9')))
        style_cmds.append(('FONTNAME', (0, footer_start), (-1, -1), font))
    table.setStyle(TableStyle(style_cmds))
    story.append(table)
    doc.build(story)
    response = HttpResponse(buf.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
