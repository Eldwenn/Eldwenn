"""CSV dışa aktarma."""
import csv

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


def export_usta_csv(db, path):
    _write_csv(path, ["Firma / Usta", "Müşteri", "İş / Proje", "Toplam", "Ödenen", "Kalan", "Tarih", "Durum"],
               [[r["usta_ad"], r["musteri_ad"], r["is_adi"], format_tl(r["toplam"]), format_tl(r["odenen"]),
                 format_tl(r["kalan"]), format_date(r["tarih"]), services.USTA_DURUM_ADI[r["durum"]]]
                for r in services.usta_isler(db)])
