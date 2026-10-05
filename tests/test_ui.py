"""Arayüz testleri (tkinter ve ekran yoksa atlanır)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import tkinter as tk
    _kok = tk.Tk()
    _kok.destroy()
    TK_VAR = True
except Exception:  # tkinter kurulu değil veya ekran yok
    TK_VAR = False

if TK_VAR:
    import ui
    from db import Database


@unittest.skipUnless(TK_VAR, "tkinter/ekran yok")
class UstaArayuzTest(unittest.TestCase):
    def setUp(self):
        self.db = Database(":memory:")
        self.ali = self.db.add_customer("Ali Yılmaz", adres="Kadıköy, İstanbul")
        self.app = ui.App(self.db)
        self.app.git("usta")
        self.app.update()
        self.sayfa = self.app.sayfalar["usta"]

    def tearDown(self):
        self.app.update()
        self.app.destroy()

    def form_uygula(self, degerler, cagri, kaydet=True):
        """Modal formu açan `cagri`yı çalıştırır; form açılınca alanları doldurup kaydeder.

        (kaydedildi mı, hata metni, form içindeki hesap etiketleri) döndürür.
        """
        sonuc = {}

        def doldur():
            f = [w for w in self.app.winfo_children() if isinstance(w, ui.Form)][-1]
            for k, v in degerler.items():
                f.ayarla(k, v)
            sonuc["hesap"] = [e.cget("text") for e, _ in f.hesaplar]
            if kaydet:
                f._kaydet()
            sonuc["tamam"] = f.tamam
            if f.winfo_exists():   # hata varsa form açık kalır
                sonuc["hata"] = f.hata.cget("text")
                f.destroy()
            else:
                sonuc["hata"] = ""

        self.app.after(100, doldur)
        cagri()
        return sonuc

    def yeni_kayit(self, toplam="50.000,00", odenen="20.000,00", **ek):
        v = dict(usta_ad="Demir Usta", is_adi="Kaba inşaat", musteri="", toplam=toplam, odenen=odenen,
                 tarih="02.10.2026", tur="Havale")
        v.update(ek)
        return self.form_uygula(v, self.app.usta_formu)

    def test_yeni_kayit_ve_ilk_odeme(self):
        s = self.yeni_kayit()
        self.assertTrue(s["tamam"], s.get("hata"))
        self.assertEqual(s["hesap"], ["30.000,00 ₺"])     # kalan otomatik hesaplanır
        r = self.db.list_usta_isler()[0]
        self.assertEqual((r["toplam"], r["odenen"]), (5000000, 2000000))
        self.assertEqual(self.db.list_usta_odemeleri(r["id"])[0]["tur"], "Havale")
        self.assertEqual(self.sayfa.kartlar["kalan"].deger.cget("text"), "30.000,00 ₺")
        self.assertEqual(len(self.sayfa.tree.get_children()), 1)

    def test_parca_parca_odeme_ve_fazla_odeme(self):
        self.yeni_kayit()
        iid = self.db.list_usta_isler()[0]["id"]
        s = self.form_uygula(dict(tutar="15.000,00", tarih="05.10.2026", tur="Nakit", notlar="2. ödeme"),
                             lambda: self.app.usta_odeme_formu(iid))
        self.assertTrue(s["tamam"], s.get("hata"))
        self.assertEqual(s["hesap"], ["15.000,00 ₺"])      # ödeme sonrası kalan
        self.assertEqual(self.db.get_usta_is(iid)["odenen"], 3500000)
        s = self.form_uygula(dict(tutar="15.000,01"), lambda: self.app.usta_odeme_formu(iid))
        self.assertFalse(s["tamam"])
        self.assertIn("fazla", s["hata"])                  # form açık kalıp hata gösterdi
        self.assertEqual(self.db.get_usta_is(iid)["odenen"], 3500000)
        s = self.form_uygula(dict(tutar="15.000,00"), lambda: self.app.usta_odeme_formu(iid))
        self.assertTrue(s["tamam"])
        self.assertEqual(self.sayfa.kartlar["kalan"].deger.cget("text"), "0,00 ₺")
        self.assertEqual(self.sayfa.tree.item(str(iid), "values")[7], "Tamamen Ödendi")
        self.assertIn("odendi", self.sayfa.tree.item(str(iid), "tags"))

    def test_gecersiz_girisler_kayit_birakmaz(self):
        for ek in (dict(usta_ad=""), dict(is_adi=" "), dict(toplam="abc"), dict(toplam="0"),
                   dict(odenen="60.000,00"), dict(tarih="2026-10-02")):
            s = self.yeni_kayit(**ek)
            self.assertFalse(s["tamam"], ek)
            self.assertTrue(s["hata"], ek)
        self.assertEqual(self.db.list_usta_isler(), [])

    def test_musteri_secince_adres_gelir(self):
        sonuc = {}

        def doldur():
            f = [w for w in self.app.winfo_children() if isinstance(w, ui.Form)][-1]
            f.ayarla("musteri", "Ali Yılmaz")
            f.widgetler["musteri"].event_generate("<<ComboboxSelected>>")
            sonuc["adres"] = f.getir("adres")
            f.destroy()

        self.app.after(100, doldur)
        self.app.usta_formu()
        self.assertEqual(sonuc["adres"], "Kadıköy, İstanbul")

    def test_duzenleme_ve_musteri_baglantisi(self):
        self.yeni_kayit(odenen="20.000,00")
        iid = self.db.list_usta_isler()[0]["id"]
        s = self.form_uygula(dict(toplam="10.000,00"), lambda: self.app.usta_formu(iid))
        self.assertFalse(s["tamam"])                       # ödenenin altına inemez
        s = self.form_uygula(dict(toplam="60.000,00", musteri="ali yılmaz", is_adi="Kaba + ince"),
                             lambda: self.app.usta_formu(iid))
        self.assertTrue(s["tamam"], s.get("hata"))
        r = self.db.get_usta_is(iid)
        self.assertEqual((r["toplam"], r["musteri_id"], r["is_adi"]), (6000000, self.ali, "Kaba + ince"))
        self.assertEqual(s["hesap"], ["40.000,00 ₺"])

    def test_arama_ve_filtreler(self):
        self.yeni_kayit(usta_ad="Demir Usta", musteri="Ali Yılmaz")
        self.yeni_kayit(usta_ad="Boya Ltd.", is_adi="Cephe", toplam="2.000,00", odenen="2.000,00")
        self.app.update()
        say = lambda: len(self.sayfa.tree.get_children())
        self.assertEqual(say(), 2)
        self.sayfa.arama.set("boya"); self.app.update()
        self.assertEqual(say(), 1)
        self.sayfa.arama.set("ali"); self.app.update()          # müşteri adına göre
        self.assertEqual(say(), 1)
        self.sayfa.arama.set("")
        self.sayfa.durum.set("Tamamen Ödendi"); self.sayfa.yenile()
        self.assertEqual(say(), 1)
        self.sayfa.durum.set("Kısmen Ödendi"); self.sayfa.yenile()
        self.assertEqual(say(), 1)
        self.sayfa.durum.set("Ödenmedi"); self.sayfa.yenile()
        self.assertEqual(say(), 0)
        self.sayfa.durum.set("Tüm durumlar")
        self.sayfa.tarih.set("Geçen ay"); self.sayfa.yenile()   # ödemeler 2026-10-02'de
        self.assertEqual(say(), 0)
        self.sayfa.tarih.set("Tüm tarihler"); self.sayfa.yenile()
        self.assertEqual(say(), 2)

    def test_satir_islemleri_tiklama(self):
        self.yeni_kayit()
        self.app.update()
        iid = str(self.db.list_usta_isler()[0]["id"])
        cagri = []
        self.app.usta_odeme_formu = lambda i, o=None: cagri.append(("odeme", i))
        self.app.usta_formu = lambda i=None: cagri.append(("duzenle", i))
        self.app.usta_sil = lambda i: cagri.append(("sil", i))
        self.app.usta_detay = lambda i: cagri.append(("gecmis", i))
        tree = self.sayfa.tree
        x0, y0, w, h = tree.bbox(iid, "islem")
        font = ui.tkfont.Font(font=ui.ttk.Style(self.app).lookup("Treeview", "font"))
        sayfa = self.sayfa

        def tikla(x, olay="<ButtonRelease-1>"):
            tree.event_generate(olay, x=x, y=y0 + h // 2)
            self.app.update()

        x = x0 + 6
        merkezler = []
        for ad in sayfa.ISLEMLER:
            wd = font.measure(ad)
            merkezler.append(x + wd // 2)
            x += wd + font.measure(sayfa.AYRAC)
        for m in merkezler:
            tikla(m)
        self.assertEqual(cagri, [("odeme", int(iid)), ("duzenle", int(iid)), ("sil", int(iid))])
        cagri.clear()
        from types import SimpleNamespace
        sayfa._cift_tik(SimpleNamespace(x=tree.bbox(iid, "usta")[0] + 10, y=y0 + h // 2))  # çift tık
        self.assertEqual(cagri, [("gecmis", int(iid))])

    def test_kirpilan_hucre_ipucu(self):
        from types import SimpleNamespace
        self.yeni_kayit(usta_ad="Çok Uzun İsimli Firma ve Ustalık Hizmetleri Ltd. Şti.")
        self.app.update()
        iid = str(self.db.list_usta_isler()[0]["id"])
        x, y, w, h = self.sayfa.tree.bbox(iid, "usta")
        balonlar = lambda: [w for w in self.sayfa.tree.winfo_children() if isinstance(w, tk.Toplevel)]
        # fare olayını doğrudan işleyiciye veriyoruz (sentetik olay Windows'ta güvenilir değil)
        self.sayfa.hucre_ipucu._hareket(SimpleNamespace(x=x + 8, y=y + h // 2, x_root=100, y_root=100))
        self.app.after(900, self.app.quit)
        self.app.mainloop()                      # balon 500 ms sonra çıkar
        self.assertEqual(len(balonlar()), 1)
        self.assertIn("Çok Uzun İsimli", balonlar()[0].winfo_children()[0].cget("text"))
        self.sayfa.hucre_ipucu._gizle()
        self.assertEqual(balonlar(), [])

    def test_detay_penceresi_ve_gecmis(self):
        self.yeni_kayit()
        iid = self.db.list_usta_isler()[0]["id"]
        self.db.add_usta_odeme(iid, 1000000, "2026-10-03", "EFT", "ara ödeme")
        d = ui.UstaDetay(self.app, self.db, iid)
        self.app.update()
        self.assertEqual(len(d.tree.get_children()), 2)
        self.assertEqual(d.k_kalan.deger.cget("text"), "20.000,00 ₺")
        d.tree.selection_set(d.tree.get_children()[1])
        from unittest import mock
        with mock.patch.object(ui.messagebox, "askyesno", return_value=True):
            d.odeme_sil()
        self.assertEqual(d.k_kalan.deger.cget("text"), "30.000,00 ₺")
        d.destroy()

    def test_kayit_silme_ve_diger_sayfalar(self):
        from unittest import mock
        self.yeni_kayit()
        iid = self.db.list_usta_isler()[0]["id"]
        with mock.patch.object(ui.messagebox, "askyesno", return_value=True):
            self.app.usta_sil(iid)
        self.assertEqual(self.db.list_usta_isler(), [])
        self.assertEqual(self.sayfa.kartlar["toplam"].deger.cget("text"), "0,00 ₺")
        for sayfa in ("panel", "musteri", "geciken", "rapor", "usta"):   # mevcut sayfalar bozulmamış
            self.app.git(sayfa)
            self.app.update()


if __name__ == "__main__":
    unittest.main()
