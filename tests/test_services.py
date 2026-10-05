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

    def test_bos_veritabani_pdf(self):
        db = Database(":memory:")
        with tempfile.TemporaryDirectory() as t:
            pdf_export.bakiye_raporu_pdf(db, "2026-10-05", os.path.join(t, "b.pdf"))
            pdf_export.geciken_raporu_pdf(db, "2026-10-05", os.path.join(t, "g.pdf"))


if __name__ == "__main__":
    unittest.main()
