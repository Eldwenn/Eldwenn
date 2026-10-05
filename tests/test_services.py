import csv
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import export
import pdf_export
import services
from db import Database
from format import format_date, format_tl, parse_date, parse_tl


class FormatTest(unittest.TestCase):
    def test_tl(self):
        self.assertEqual(format_tl(123456), "1.234,56 ₺")
        self.assertEqual(format_tl(5), "0,05 ₺")
        self.assertEqual(format_tl(-250000), "-2.500,00 ₺")

    def test_parse_tl(self):
        self.assertEqual(parse_tl("1.234,56"), 123456)
        self.assertEqual(parse_tl("1234,5 ₺"), 123450)
        self.assertEqual(parse_tl("1.234"), 123400)
        self.assertEqual(parse_tl("12.5"), 1250)
        with self.assertRaises(ValueError):
            parse_tl("abc")
        with self.assertRaises(ValueError):
            parse_tl("")

    def test_date(self):
        self.assertEqual(parse_date("05.10.2026"), "2026-10-05")
        self.assertEqual(format_date("2026-10-05"), "05.10.2026")
        self.assertIsNone(parse_date(""))
        with self.assertRaises(ValueError):
            parse_date("2026-10-05")


class ServiceTest(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.ali = self.db.add_customer("Ali Yılmaz", "0555 111")
        self.veli = self.db.add_customer("Veli Kaya")

    def test_bakiye_ve_kismi_odeme(self):
        self.db.add_debt(self.ali, 100000, "2026-09-01", "2026-09-15")
        self.db.add_debt(self.ali, 50000, "2026-09-10", "2026-10-30")
        self.db.add_payment(self.ali, 120000, "2026-09-20")
        b = services.customer_balance(self.db, self.ali)
        self.assertEqual(b["bakiye"], 30000)
        d = services.debt_status(self.db, self.ali, "2026-10-05")
        self.assertEqual(d[0]["kalan"], 0)          # en eski borç önce kapanır
        self.assertEqual(d[1]["kalan"], 30000)
        self.assertEqual(d[1]["gecikme_gun"], 0)    # vadesi henüz gelmedi

    def test_gecikme(self):
        self.db.add_debt(self.ali, 100000, "2026-09-01", "2026-09-15")
        self.db.add_payment(self.ali, 40000, "2026-09-20")
        geciken = services.overdue_list(self.db, "2026-10-05")
        self.assertEqual(len(geciken), 1)
        self.assertEqual(geciken[0]["kalan"], 60000)
        self.assertEqual(geciken[0]["gecikme_gun"], 20)
        self.assertEqual(geciken[0]["musteri_ad"], "Ali Yılmaz")

    def test_vadesiz_borc_gecikmez(self):
        self.db.add_debt(self.veli, 1000, "2026-01-01")
        self.assertEqual(services.overdue_list(self.db, "2026-10-05"), [])

    def test_ozet(self):
        self.db.add_debt(self.ali, 100000, "2026-09-01", "2026-09-15")
        self.db.add_payment(self.ali, 40000, "2026-10-02")
        s = services.summary(self.db, "2026-10-05")
        self.assertEqual(s["musteri_sayisi"], 2)
        self.assertEqual(s["toplam_alacak"], 60000)
        self.assertEqual(s["ay_tahsilat"], 40000)
        self.assertEqual(s["geciken_tutar"], 60000)
        self.assertEqual(s["geciken_musteri"], 1)

    def test_musteri_ozeti_ve_filtre(self):
        self.db.add_debt(self.ali, 100000, "2026-09-01", "2026-09-15")
        self.db.add_debt(self.veli, 5000, "2026-10-01", "2026-12-01")
        tum = {r["ad"]: r for r in services.customers_overview(self.db, "2026-10-05")}
        self.assertEqual(tum["Ali Yılmaz"]["durum"], "gecikmis")
        self.assertEqual(tum["Ali Yılmaz"]["gecikme_gun"], 20)
        self.assertEqual(tum["Veli Kaya"]["durum"], "guncel")
        self.assertEqual([r["ad"] for r in services.customers_overview(self.db, "2026-10-05", "", "gecikmis")],
                         ["Ali Yılmaz"])
        self.db.add_payment(self.veli, 5000, "2026-10-02")
        self.assertEqual([r["ad"] for r in services.customers_overview(self.db, "2026-10-05", "", "borcu_yok")],
                         ["Veli Kaya"])
        self.assertEqual(len(services.customers_overview(self.db, "2026-10-05", "ali")), 1)

    def test_yaklasan_ve_son_odemeler(self):
        self.db.add_debt(self.ali, 10000, "2026-10-01", "2026-10-08")
        self.db.add_debt(self.veli, 20000, "2026-10-01", "2026-11-30")
        yak = services.upcoming_list(self.db, "2026-10-05", 7)
        self.assertEqual([(r["musteri_ad"], r["kalan_gun"]) for r in yak], [("Ali Yılmaz", 3)])
        self.db.add_payment(self.ali, 100, "2026-10-02")
        self.db.add_payment(self.veli, 200, "2026-10-04")
        son = self.db.recent_payments(1)
        self.assertEqual(son[0]["musteri_ad"], "Veli Kaya")

    def test_duzenleme(self):
        d = self.db.add_debt(self.ali, 1000, "2026-09-01")
        self.db.update_debt(d, 2500, "2026-09-02", "2026-10-01", "yeni")
        self.assertEqual(self.db.get_debt(d)["tutar"], 2500)
        p = self.db.add_payment(self.ali, 100, "2026-09-03")
        self.db.update_payment(p, 300, "2026-09-04", "Nakit")
        self.assertEqual(self.db.get_payment(p)["yontem"], "Nakit")
        with self.assertRaises(ValueError):
            self.db.update_debt(d, 0, "2026-09-02")

    def test_silme_cascade(self):
        self.db.add_debt(self.ali, 1000, "2026-09-01")
        self.db.add_payment(self.ali, 500, "2026-09-02")
        self.db.delete_customer(self.ali)
        self.assertEqual(self.db.conn.execute("SELECT COUNT(*) FROM borclar").fetchone()[0], 0)
        self.assertEqual(self.db.conn.execute("SELECT COUNT(*) FROM odemeler").fetchone()[0], 0)

    def test_arama_ve_dogrulama(self):
        self.assertEqual([m["ad"] for m in self.db.list_customers("veli")], ["Veli Kaya"])
        with self.assertRaises(ValueError):
            self.db.add_customer("  ")
        with self.assertRaises(ValueError):
            self.db.add_debt(self.ali, 0, "2026-01-01")


class UstaTest(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.m = self.db.add_customer("Ali Yılmaz", adres="Kadıköy")

    def test_parca_parca_odeme(self):
        i = self.db.add_usta_is("Usta Hasan", "Mutfak tadilatı", 5000000, "2026-10-01", self.m)
        self.db.add_usta_odeme(i, 2000000, "2026-10-02", "Nakit")
        self.db.add_usta_odeme(i, 1500000, "2026-10-04", "Havale", "2. taksit")
        r = self.db.get_usta_is(i)
        self.assertEqual((r["toplam"], r["odenen"]), (5000000, 3500000))
        self.assertEqual(r["son_odeme"], "2026-10-04")
        self.assertEqual(r["musteri_ad"], "Ali Yılmaz")
        self.assertEqual([o["tutar"] for o in self.db.list_usta_odemeleri(i)], [2000000, 1500000])
        self.assertEqual(services.usta_isler(self.db)[0]["kalan"], 1500000)
        self.assertEqual(services.usta_isler(self.db)[0]["durum"], "kismi")

    def test_fazla_odeme_engellenir(self):
        i = self.db.add_usta_is("Usta", "İş", 10000, "2026-10-01")
        self.db.add_usta_odeme(i, 6000, "2026-10-02")
        with self.assertRaises(ValueError):
            self.db.add_usta_odeme(i, 4001, "2026-10-03")
        self.db.add_usta_odeme(i, 4000, "2026-10-03")
        self.assertEqual(services.usta_isler(self.db)[0]["durum"], "tamam")

    def test_odeme_duzenleme_ve_silme(self):
        i = self.db.add_usta_is("Usta", "İş", 10000, "2026-10-01")
        o1 = self.db.add_usta_odeme(i, 6000, "2026-10-02")
        self.db.update_usta_odeme(o1, 10000, "2026-10-02", "EFT")    # kendi tutarı hariç tutulur
        with self.assertRaises(ValueError):
            self.db.update_usta_odeme(o1, 10001, "2026-10-02", "EFT")
        self.db.delete_usta_odeme(o1)
        self.assertEqual(services.usta_isler(self.db)[0]["durum"], "odenmedi")

    def test_dogrulama(self):
        with self.assertRaises(ValueError):
            self.db.add_usta_is(" ", "İş", 100, "2026-10-01")
        with self.assertRaises(ValueError):
            self.db.add_usta_is("Usta", "", 100, "2026-10-01")
        with self.assertRaises(ValueError):
            self.db.add_usta_is("Usta", "İş", 0, "2026-10-01")
        i = self.db.add_usta_is("Usta", "İş", 10000, "2026-10-01")
        with self.assertRaises(ValueError):
            self.db.add_usta_odeme(i, 100, "2026-10-02", "Çek")
        self.db.add_usta_odeme(i, 6000, "2026-10-02")
        with self.assertRaises(ValueError):
            self.db.update_usta_is(i, "Usta", "İş", 5999)             # ödenenin altına inemez

    def test_ozet_ve_filtreler(self):
        a = self.db.add_usta_is("Demir Usta", "Kaba inşaat", 10000000, "2026-09-01", self.m)
        b = self.db.add_usta_is("Boya Ltd.", "Dış cephe", 2000000, "2026-09-10", None, "Zeynep Kaya")
        self.db.add_usta_odeme(a, 4000000, "2026-10-02")
        self.db.add_usta_odeme(b, 2000000, "2026-09-15")
        s = services.usta_summary(self.db, "2026-10-05")
        self.assertEqual((s["toplam"], s["odenen"], s["kalan"], s["ay_odeme"]),
                         (12000000, 6000000, 6000000, 4000000))
        self.assertEqual([r["usta_ad"] for r in services.usta_isler(self.db, "demir")], ["Demir Usta"])
        self.assertEqual([r["usta_ad"] for r in services.usta_isler(self.db, "zeynep")], ["Boya Ltd."])
        self.assertEqual([r["usta_ad"] for r in services.usta_isler(self.db, "kaba")], ["Demir Usta"])
        self.assertEqual([r["usta_ad"] for r in services.usta_isler(self.db, "", "tamam")], ["Boya Ltd."])
        self.assertEqual([r["usta_ad"] for r in services.usta_isler(self.db, "", "tumu", "2026-10-01", "2026-10-31")],
                         ["Demir Usta"])
        self.assertEqual(self.db.usta_adlari(), ["Boya Ltd.", "Demir Usta"])

    def test_tarih_araligi(self):
        self.assertEqual(services.tarih_araligi("Tüm tarihler", "2026-10-05"), (None, None))
        self.assertEqual(services.tarih_araligi("Bugün", "2026-10-05"), ("2026-10-05", "2026-10-05"))
        self.assertEqual(services.tarih_araligi("Bu hafta", "2026-10-05"), ("2026-10-05", "2026-10-11"))  # pazartesi
        self.assertEqual(services.tarih_araligi("Bu ay", "2026-10-05"), ("2026-10-01", "2026-10-31"))
        self.assertEqual(services.tarih_araligi("Geçen ay", "2026-10-05"), ("2026-09-01", "2026-09-30"))
        self.assertEqual(services.tarih_araligi("Geçen ay", "2026-01-15"), ("2025-12-01", "2025-12-31"))
        self.assertEqual(services.tarih_araligi("Son 30 gün", "2026-10-05"), ("2026-09-05", "2026-10-05"))
        self.assertEqual(services.tarih_araligi("Bu yıl", "2026-10-05"), ("2026-01-01", "2026-12-31"))

    def test_musteri_silinince_kayit_kalir(self):
        i = self.db.add_usta_is("Usta", "İş", 1000, "2026-10-01", self.m, "Ali Yılmaz")
        self.db.delete_customer(self.m)
        r = self.db.get_usta_is(i)
        self.assertIsNone(r["musteri_id"])
        self.assertEqual(r["musteri_ad"], "Ali Yılmaz")
        self.db.delete_usta_is(i)
        self.assertEqual(self.db.conn.execute("SELECT COUNT(*) FROM usta_odemeleri").fetchone()[0], 0)

    def test_eski_veritabani_yukseltme(self):
        with tempfile.TemporaryDirectory() as t:
            yol = os.path.join(t, "eski.db")
            import sqlite3
            c = sqlite3.connect(yol)
            c.executescript("CREATE TABLE musteriler (id INTEGER PRIMARY KEY AUTOINCREMENT, ad TEXT NOT NULL, "
                            "telefon TEXT DEFAULT '', eposta TEXT DEFAULT '', adres TEXT DEFAULT '', notlar TEXT DEFAULT '');"
                            "INSERT INTO musteriler (ad) VALUES ('Eski Müşteri');")
            c.commit(); c.close()
            db = Database(yol)
            self.assertEqual(db.list_customers()[0]["ad"], "Eski Müşteri")
            db.add_usta_is("Usta", "İş", 100, "2026-10-01")
            db.close()


class ExportTest(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.c = self.db.add_customer("Ayşe <Öz>", "0532")
        self.db.add_debt(self.c, 100000, "2026-09-01", "2026-09-15", "Mal bedeli")
        self.db.add_payment(self.c, 25000, "2026-09-20", "havale")

    def test_csv(self):
        with tempfile.TemporaryDirectory() as t:
            yol = os.path.join(t, "geciken.csv")
            export.export_overdue_csv(self.db, yol, "2026-10-05")
            with open(yol, encoding="utf-8-sig") as f:
                satirlar = list(csv.reader(f, delimiter=";"))
            self.assertEqual(satirlar[1][0], "Ayşe <Öz>")
            self.assertEqual(satirlar[1][4], "750,00 ₺")
            export.export_balances_csv(self.db, os.path.join(t, "b.csv"))
            export.export_customers_csv(self.db, os.path.join(t, "m.csv"))

    def test_pdf(self):
        with tempfile.TemporaryDirectory() as t:
            for ad, fn in (("e.pdf", lambda y: pdf_export.musteri_ekstresi_pdf(self.db, self.c, "2026-10-05", y)),
                           ("b.pdf", lambda y: pdf_export.bakiye_raporu_pdf(self.db, "2026-10-05", y)),
                           ("g.pdf", lambda y: pdf_export.geciken_raporu_pdf(self.db, "2026-10-05", y))):
                yol = os.path.join(t, ad)
                fn(yol)
                with open(yol, "rb") as f:
                    self.assertEqual(f.read(5), b"%PDF-")
                self.assertGreater(os.path.getsize(yol), 5000)  # logo + font gömülü

    def test_usta_cikti(self):
        i = self.db.add_usta_is("Usta <Hasan>", "Mutfak", 5000000, "2026-10-01", self.c, "Ayşe")
        self.db.add_usta_odeme(i, 2000000, "2026-10-02", "Nakit")
        with tempfile.TemporaryDirectory() as t:
            yol = os.path.join(t, "u.csv")
            export.export_usta_csv(self.db, yol)
            with open(yol, encoding="utf-8-sig") as f:
                satirlar = list(csv.reader(f, delimiter=";"))
            self.assertEqual(satirlar[1][0], "Usta <Hasan>")
            self.assertEqual(satirlar[1][5], "30.000,00 ₺")
            self.assertEqual(satirlar[1][7], "Kısmen Ödendi")
            pdf = os.path.join(t, "u.pdf")
            pdf_export.usta_raporu_pdf(self.db, "2026-10-05", pdf)
            with open(pdf, "rb") as f:
                self.assertEqual(f.read(5), b"%PDF-")

    def test_selftest_cekirdek(self):
        import selftest
        with tempfile.TemporaryDirectory() as t:
            selftest.cekirdek(t).close()

    def test_bos_veritabani_pdf(self):
        db = Database(":memory:")
        with tempfile.TemporaryDirectory() as t:
            pdf_export.bakiye_raporu_pdf(db, "2026-10-05", os.path.join(t, "b.pdf"))
            pdf_export.geciken_raporu_pdf(db, "2026-10-05", os.path.join(t, "g.pdf"))


if __name__ == "__main__":
    unittest.main()
