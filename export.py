"""CSV dışa aktarma ve yazdırılabilir müşteri ekstresi."""
import csv
from html import escape

import services
from format import format_date, format_tl


def _write_csv(path, header, rows):
    # utf-8-sig + ';' : Türkçe Excel'de doğru açılır
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(header)
        w.writerows(rows)


def export_customers_csv(db, path):
    _write_csv(path, ["Ad", "Telefon", "E-posta", "Adres", "Not"],
               [[m["ad"], m["telefon"], m["eposta"], m["adres"], m["notlar"]]
                for m in db.list_customers()])


def export_balances_csv(db, path):
    _write_csv(path, ["Müşteri", "Telefon", "Toplam Borç", "Toplam Ödeme", "Bakiye"],
               [[b["ad"], b["telefon"], format_tl(b["toplam_borc"]),
                 format_tl(b["toplam_odeme"]), format_tl(b["bakiye"])]
                for b in services.balances(db)])


def export_overdue_csv(db, path, bugun):
    _write_csv(path, ["Müşteri", "Telefon", "Açıklama", "Vade", "Kalan", "Gecikme (gün)"],
               [[r["musteri_ad"], r["telefon"], r["aciklama"], format_date(r["vade"]),
                 format_tl(r["kalan"]), r["gecikme_gun"]]
                for r in services.overdue_list(db, bugun)])


def statement_html(db, cid, bugun):
    """Müşteri ekstresi: tarayıcıda açıp yazdırılabilir/PDF kaydedilebilir HTML."""
    m = db.get_customer(cid)
    b = services.customer_balance(db, cid)
    borclar = services.debt_status(db, cid, bugun)
    odemeler = db.list_payments(cid)
    e = escape
    borc_satir = "".join(
        f"<tr><td>{format_date(d['tarih'])}</td><td>{e(d['aciklama'])}</td>"
        f"<td>{format_date(d['vade'])}</td><td class=r>{format_tl(d['tutar'])}</td>"
        f"<td class=r>{format_tl(d['kalan'])}</td></tr>" for d in borclar)
    odeme_satir = "".join(
        f"<tr><td>{format_date(p['tarih'])}</td><td>{e(p['yontem'])}</td>"
        f"<td>{e(p['aciklama'])}</td><td class=r>{format_tl(p['tutar'])}</td></tr>"
        for p in odemeler)
    return f"""<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><title>Ekstre - {e(m['ad'])}</title>
<style>body{{font-family:sans-serif;margin:2em}}table{{border-collapse:collapse;width:100%;margin-bottom:1.5em}}
th,td{{border:1px solid #999;padding:4px 8px;text-align:left}}.r{{text-align:right}}</style></head><body>
<h1>Müşteri Ekstresi</h1>
<p><b>{e(m['ad'])}</b><br>{e(m['telefon'])} {e(m['eposta'])}<br>{e(m['adres'])}</p>
<p>Tarih: {format_date(bugun)}</p>
<h2>Borçlar</h2><table><tr><th>Tarih</th><th>Açıklama</th><th>Vade</th><th>Tutar</th><th>Kalan</th></tr>{borc_satir}</table>
<h2>Ödemeler</h2><table><tr><th>Tarih</th><th>Yöntem</th><th>Açıklama</th><th>Tutar</th></tr>{odeme_satir}</table>
<p>Toplam borç: {format_tl(b['toplam_borc'])}<br>Toplam ödeme: {format_tl(b['toplam_odeme'])}<br>
<b>Kalan bakiye: {format_tl(b['bakiye'])}</b></p></body></html>"""
