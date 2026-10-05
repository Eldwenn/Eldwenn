"""Logolu PDF çıktıları: müşteri ekstresi, bakiye raporu, geciken ödemeler raporu."""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from xml.sax.saxutils import escape

import services
from config import FIRMA_ADI, resource_path
from format import format_date, format_tl

KIRMIZI = colors.HexColor("#E31E24")
_fontlar_yuklu = False


def _fontlari_yukle():
    global _fontlar_yuklu
    if not _fontlar_yuklu:
        pdfmetrics.registerFont(TTFont("TR", resource_path("assets/DejaVuSans.ttf")))
        pdfmetrics.registerFont(TTFont("TR-B", resource_path("assets/DejaVuSans-Bold.ttf")))
        pdfmetrics.registerFontFamily("TR", normal="TR", bold="TR-B", italic="TR", boldItalic="TR-B")
        _fontlar_yuklu = True


def _stiller():
    return {
        "normal": ParagraphStyle("n", fontName="TR", fontSize=9, leading=12),
        "sag": ParagraphStyle("r", fontName="TR", fontSize=9, leading=12, alignment=2),
        "baslik": ParagraphStyle("h", fontName="TR-B", fontSize=15, leading=19),
        "alt": ParagraphStyle("a", fontName="TR-B", fontSize=11, leading=14, spaceBefore=8, spaceAfter=4),
        "firma": ParagraphStyle("f", fontName="TR-B", fontSize=17, leading=21, textColor=KIRMIZI),
        "kalin": ParagraphStyle("b", fontName="TR-B", fontSize=9, leading=12),
        "kalin_sag": ParagraphStyle("br", fontName="TR-B", fontSize=9, leading=12, alignment=2),
    }


def _p(metin, stil):
    return Paragraph(escape(str(metin)), stil)


def _ust_bilgi(st, baslik, bugun):
    logo = Image(resource_path("assets/logo.png"), width=18 * mm, height=18.5 * mm)
    sol = [_p(FIRMA_ADI, st["firma"]), _p(baslik, st["baslik"])]
    tablo = Table([[logo, sol, _p(format_date(bugun), st["sag"])]], colWidths=[24 * mm, 126 * mm, 30 * mm])
    tablo.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                               ("LINEBELOW", (0, 0), (-1, 0), 1.2, KIRMIZI),
                               ("BOTTOMPADDING", (0, 0), (-1, 0), 6)]))
    return [tablo, Spacer(1, 6 * mm)]


def _veri_tablosu(basliklar, satirlar, genislikler, sag_kolonlar, st, toplam_satiri=None):
    veri = [[_p(b, st["kalin_sag"] if i in sag_kolonlar else st["kalin"]) for i, b in enumerate(basliklar)]]
    for s in satirlar:
        veri.append([_p(h, st["sag"] if i in sag_kolonlar else st["normal"]) for i, h in enumerate(s)])
    if toplam_satiri:
        veri.append([_p(h, st["kalin_sag"] if i in sag_kolonlar else st["kalin"])
                     for i, h in enumerate(toplam_satiri)])
    t = Table(veri, colWidths=[g * mm for g in genislikler], repeatRows=1)
    stil = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3D6D7")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE")]
    if toplam_satiri:
        stil.append(("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EEEEEE")))
    t.setStyle(TableStyle(stil))
    return t


def _olustur(yol, baslik, bugun, icerik_fn):
    _fontlari_yukle()
    st = _stiller()

    def alt_bilgi(canvas, doc):
        canvas.saveState()
        canvas.setFont("TR", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(15 * mm, 8 * mm, FIRMA_ADI)
        canvas.drawRightString(195 * mm, 8 * mm, f"Sayfa {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(yol, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
                            topMargin=12 * mm, bottomMargin=16 * mm, title=f"{FIRMA_ADI} - {baslik}",
                            author=FIRMA_ADI)
    doc.build(_ust_bilgi(st, baslik, bugun) + icerik_fn(st), onFirstPage=alt_bilgi, onLaterPages=alt_bilgi)


def musteri_ekstresi_pdf(db, cid, bugun, yol):
    m = db.get_customer(cid)
    b = services.customer_balance(db, cid)
    borclar = services.debt_status(db, cid, bugun)
    odemeler = db.list_payments(cid)

    def icerik(st):
        iletisim = " · ".join(x for x in (m["telefon"], m["eposta"]) if x)
        ogeler = [_p(m["ad"], st["kalin"])]
        if iletisim:
            ogeler.append(_p(iletisim, st["normal"]))
        if m["adres"]:
            ogeler.append(_p(m["adres"], st["normal"]))
        ogeler.append(_p("Borçlar", st["alt"]))
        ogeler.append(_veri_tablosu(
            ["Tarih", "Açıklama", "Vade", "Tutar", "Kalan"],
            [[format_date(d["tarih"]), d["aciklama"], format_date(d["vade"]),
              format_tl(d["tutar"]), format_tl(d["kalan"])] for d in borclar] or [["", "Kayıt yok", "", "", ""]],
            [24, 66, 24, 33, 33], {3, 4}, st))
        ogeler.append(_p("Ödemeler", st["alt"]))
        ogeler.append(_veri_tablosu(
            ["Tarih", "Yöntem", "Açıklama", "Tutar"],
            [[format_date(p["tarih"]), p["yontem"], p["aciklama"], format_tl(p["tutar"])]
             for p in odemeler] or [["", "", "Kayıt yok", ""]],
            [24, 36, 84, 36], {3}, st))
        ogeler.append(Spacer(1, 6 * mm))
        ogeler.append(_veri_tablosu(
            ["Toplam Borç", "Toplam Ödeme", "Kalan Bakiye"],
            [[format_tl(b["toplam_borc"]), format_tl(b["toplam_odeme"]), format_tl(b["bakiye"])]],
            [60, 60, 60], {0, 1, 2}, st))
        return ogeler

    _olustur(yol, "Müşteri Ekstresi", bugun, icerik)


def bakiye_raporu_pdf(db, bugun, yol):
    satirlar = services.balances(db)

    def icerik(st):
        toplam = sum(s["bakiye"] for s in satirlar)
        return [_veri_tablosu(
            ["Müşteri", "Telefon", "Toplam Borç", "Toplam Ödeme", "Bakiye"],
            [[s["ad"], s["telefon"], format_tl(s["toplam_borc"]), format_tl(s["toplam_odeme"]),
              format_tl(s["bakiye"])] for s in satirlar] or [["Kayıt yok", "", "", "", ""]],
            [48, 30, 34, 34, 34], {2, 3, 4}, st, ["TOPLAM", "", "", "", format_tl(toplam)])]

    _olustur(yol, "Müşteri Bakiyeleri", bugun, icerik)


def geciken_raporu_pdf(db, bugun, yol):
    satirlar = services.overdue_list(db, bugun)

    def icerik(st):
        toplam = sum(s["kalan"] for s in satirlar)
        return [_veri_tablosu(
            ["Müşteri", "Telefon", "Açıklama", "Vade", "Kalan", "Gün"],
            [[s["musteri_ad"], s["telefon"], s["aciklama"], format_date(s["vade"]),
              format_tl(s["kalan"]), s["gecikme_gun"]] for s in satirlar] or [["Geciken ödeme yok", "", "", "", "", ""]],
            [40, 28, 42, 22, 32, 16], {4, 5}, st, ["TOPLAM", "", "", "", format_tl(toplam), ""])]

    _olustur(yol, "Geciken Ödemeler", bugun, icerik)


def usta_raporu_pdf(db, bugun, yol):
    satirlar = services.usta_isler(db)

    def icerik(st):
        toplam = sum(r["toplam"] for r in satirlar)
        odenen = sum(r["odenen"] for r in satirlar)
        return [_veri_tablosu(
            ["Firma / Usta", "Müşteri", "İş / Proje", "Toplam", "Ödenen", "Kalan", "Durum"],
            [[r["usta_ad"], r["musteri_ad"], r["is_adi"], format_tl(r["toplam"]), format_tl(r["odenen"]),
              format_tl(r["kalan"]), services.USTA_DURUM_ADI[r["durum"]]] for r in satirlar]
            or [["Kayıt yok", "", "", "", "", "", ""]],
            [28, 24, 28, 24, 24, 24, 28], {3, 4, 5}, st,
            ["TOPLAM", "", "", format_tl(toplam), format_tl(odenen), format_tl(toplam - odenen), ""])]

    _olustur(yol, "Firma / Usta Ödemeleri", bugun, icerik)
