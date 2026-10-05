"""tkinter arayüzü."""
import os
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

import export
import pdf_export
import services
from config import FIRMA_ADI, resource_path
from format import format_date, format_tl, parse_date, parse_tl, today_iso


def pdf_ac(yol):
    """Oluşturulan PDF'i varsayılan okuyucuda açar."""
    try:
        if sys.platform.startswith("win"):
            os.startfile(yol)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", yol])
        else:
            subprocess.Popen(["xdg-open", yol])
    except OSError:
        pass


class FormDialog(simpledialog.Dialog):
    """Basit alan listesi formu. alanlar: [(anahtar, etiket, varsayılan)]"""

    def __init__(self, parent, baslik, alanlar):
        self.alanlar = alanlar
        self.girdiler = {}
        self.sonuc = None
        super().__init__(parent, baslik)

    def body(self, master):
        for i, (anahtar, etiket, varsayilan) in enumerate(self.alanlar):
            ttk.Label(master, text=etiket).grid(row=i, column=0, sticky="w", padx=4, pady=3)
            e = ttk.Entry(master, width=36)
            e.insert(0, varsayilan or "")
            e.grid(row=i, column=1, padx=4, pady=3)
            self.girdiler[anahtar] = e
        return next(iter(self.girdiler.values()))

    def apply(self):
        self.sonuc = {k: e.get() for k, e in self.girdiler.items()}


def tablo(parent, kolonlar, yukseklik=12):
    """kolonlar: [(anahtar, başlık, genişlik)] -> (frame, Treeview)"""
    frame = ttk.Frame(parent)
    tree = ttk.Treeview(frame, columns=[k for k, _, _ in kolonlar], show="headings", height=yukseklik)
    for k, baslik, w in kolonlar:
        tree.heading(k, text=baslik)
        tree.column(k, width=w, anchor="w")
    sb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    return frame, tree


class App(tk.Tk):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.title(f"{FIRMA_ADI} - Müşteri Takip ve Ödeme Takibi")
        self.geometry("1000x620")
        try:
            self.logo = tk.PhotoImage(file=resource_path("assets/logo.png"))
            self.iconphoto(True, self.logo)
            self.logo_kucuk = self.logo.subsample(max(1, self.logo.width() // 48))
        except tk.TclError:
            self.logo_kucuk = None
        baslik = ttk.Frame(self)
        baslik.pack(fill="x", padx=10, pady=(8, 0))
        if self.logo_kucuk:
            ttk.Label(baslik, image=self.logo_kucuk).pack(side="left", padx=(0, 10))
        ttk.Label(baslik, text=FIRMA_ADI, font=("", 18, "bold"), foreground="#E31E24").pack(side="left")
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=6, pady=6)
        self.panel = ttk.Frame(self.nb)
        self.musteri = ttk.Frame(self.nb)
        self.geciken = ttk.Frame(self.nb)
        self.rapor = ttk.Frame(self.nb)
        for f, ad in ((self.panel, "Panel"), (self.musteri, "Müşteriler"),
                      (self.geciken, "Geciken Ödemeler"), (self.rapor, "Raporlar")):
            self.nb.add(f, text=ad)
        self._panel_kur()
        self._musteri_kur()
        self._geciken_kur()
        self._rapor_kur()
        self.nb.bind("<<NotebookTabChanged>>", lambda e: self.yenile())
        self.yenile()

    def yenile(self):
        self._panel_yenile()
        self._musteri_yenile()
        self._geciken_yenile()

    def _hata(self, e):
        messagebox.showerror("Hata", str(e), parent=self)

    # ---------------- Panel ----------------
    def _panel_kur(self):
        self.panel_etiketler = {}
        for i, (anahtar, ad) in enumerate((
                ("musteri_sayisi", "Müşteri sayısı"), ("toplam_alacak", "Toplam alacak"),
                ("ay_tahsilat", "Bu ay tahsilat"), ("geciken_tutar", "Geciken tutar"),
                ("geciken_musteri", "Geciken müşteri sayısı"))):
            ttk.Label(self.panel, text=ad, font=("", 12)).grid(row=i, column=0, sticky="w", padx=20, pady=12)
            l = ttk.Label(self.panel, text="", font=("", 14, "bold"))
            l.grid(row=i, column=1, sticky="w", padx=20)
            self.panel_etiketler[anahtar] = l

    def _panel_yenile(self):
        s = services.summary(self.db, today_iso())
        for k, l in self.panel_etiketler.items():
            para = k in ("toplam_alacak", "ay_tahsilat", "geciken_tutar")
            l.config(text=format_tl(s[k]) if para else str(s[k]))
        self.panel_etiketler["geciken_tutar"].config(foreground="red" if s["geciken_tutar"] else "")

    # ---------------- Müşteriler ----------------
    def _musteri_kur(self):
        ust = ttk.Frame(self.musteri)
        ust.pack(fill="x", padx=6, pady=6)
        ttk.Label(ust, text="Ara:").pack(side="left")
        self.arama = tk.StringVar()
        self.arama.trace_add("write", lambda *a: self._musteri_yenile())
        ttk.Entry(ust, textvariable=self.arama, width=30).pack(side="left", padx=6)
        for ad, komut in (("Ekle", self.musteri_ekle), ("Düzenle", self.musteri_duzenle),
                          ("Sil", self.musteri_sil), ("Detay / Borç-Ödeme", self.musteri_detay)):
            ttk.Button(ust, text=ad, command=komut).pack(side="left", padx=3)
        frame, self.musteri_tree = tablo(self.musteri, [
            ("ad", "Ad", 220), ("telefon", "Telefon", 130), ("eposta", "E-posta", 200),
            ("bakiye", "Bakiye", 120)], 18)
        frame.pack(fill="both", expand=True, padx=6, pady=6)
        self.musteri_tree.bind("<Double-1>", lambda e: self.musteri_detay())

    def _musteri_yenile(self):
        self.musteri_tree.delete(*self.musteri_tree.get_children())
        for m in self.db.list_customers(self.arama.get()):
            b = services.customer_balance(self.db, m["id"])
            self.musteri_tree.insert("", "end", iid=str(m["id"]),
                                     values=(m["ad"], m["telefon"], m["eposta"], format_tl(b["bakiye"])))

    def _secili_musteri(self):
        sec = self.musteri_tree.selection()
        if not sec:
            messagebox.showinfo("Bilgi", "Önce bir müşteri seçin.", parent=self)
            return None
        return int(sec[0])

    def _musteri_alanlari(self, m=None):
        g = (lambda k: m[k] if m else "")
        return [("ad", "Ad *", g("ad")), ("telefon", "Telefon", g("telefon")),
                ("eposta", "E-posta", g("eposta")), ("adres", "Adres", g("adres")),
                ("notlar", "Not", g("notlar"))]

    def musteri_ekle(self):
        d = FormDialog(self, "Müşteri Ekle", self._musteri_alanlari())
        if d.sonuc:
            try:
                self.db.add_customer(**d.sonuc)
            except ValueError as e:
                return self._hata(e)
            self.yenile()

    def musteri_duzenle(self):
        cid = self._secili_musteri()
        if cid is None:
            return
        d = FormDialog(self, "Müşteriyi Düzenle", self._musteri_alanlari(self.db.get_customer(cid)))
        if d.sonuc:
            try:
                self.db.update_customer(cid, **d.sonuc)
            except ValueError as e:
                return self._hata(e)
            self.yenile()

    def musteri_sil(self):
        cid = self._secili_musteri()
        if cid is None:
            return
        m = self.db.get_customer(cid)
        if messagebox.askyesno("Sil", f"'{m['ad']}' ve tüm borç/ödeme kayıtları silinsin mi?", parent=self):
            self.db.delete_customer(cid)
            self.yenile()

    def musteri_detay(self):
        cid = self._secili_musteri()
        if cid is not None:
            DetayPenceresi(self, self.db, cid)

    # ---------------- Geciken ----------------
    def _geciken_kur(self):
        frame, self.geciken_tree = tablo(self.geciken, [
            ("musteri", "Müşteri", 200), ("telefon", "Telefon", 120), ("aciklama", "Açıklama", 220),
            ("vade", "Vade", 90), ("kalan", "Kalan", 110), ("gun", "Gecikme (gün)", 100)], 22)
        frame.pack(fill="both", expand=True, padx=6, pady=6)
        self.geciken_tree.tag_configure("gec", foreground="red")

    def _geciken_yenile(self):
        self.geciken_tree.delete(*self.geciken_tree.get_children())
        for r in services.overdue_list(self.db, today_iso()):
            self.geciken_tree.insert("", "end", tags=("gec",), values=(
                r["musteri_ad"], r["telefon"], r["aciklama"], format_date(r["vade"]),
                format_tl(r["kalan"]), r["gecikme_gun"]))

    # ---------------- Raporlar ----------------
    def _rapor_kur(self):
        ttk.Label(self.rapor, text="PDF raporlar (firma logolu)", font=("", 11, "bold")).pack(
            padx=20, pady=(14, 4), anchor="w")
        for ad, komut in (("Bakiye raporu (PDF)", self.pdf_bakiyeler),
                          ("Geciken ödemeler raporu (PDF)", self.pdf_geciken),
                          ("Seçili müşteri ekstresi (PDF)", self.pdf_ekstre)):
            ttk.Button(self.rapor, text=ad, command=komut, width=40).pack(padx=20, pady=5, anchor="w")
        ttk.Label(self.rapor, text="Ekstre için önce 'Müşteriler' sekmesinde bir müşteri seçin.").pack(
            padx=20, anchor="w")
        ttk.Label(self.rapor, text="Excel için CSV dışa aktarma", font=("", 11, "bold")).pack(
            padx=20, pady=(18, 4), anchor="w")
        for ad, komut in (("Müşterileri CSV olarak aktar", self.csv_musteriler),
                          ("Bakiyeleri CSV olarak aktar", self.csv_bakiyeler),
                          ("Geciken listesini CSV olarak aktar", self.csv_geciken)):
            ttk.Button(self.rapor, text=ad, command=komut, width=40).pack(padx=20, pady=5, anchor="w")

    def _kaydet(self, uzanti, ad, fonksiyon, aciklama):
        yol = filedialog.asksaveasfilename(parent=self, defaultextension=uzanti, initialfile=ad,
                                           filetypes=[(aciklama, "*" + uzanti)])
        if not yol:
            return
        try:
            fonksiyon(yol)
        except OSError as e:
            return self._hata(f"Dosya kaydedilemedi (başka programda açık olabilir):\n{e}")
        if uzanti == ".pdf":
            pdf_ac(yol)
        else:
            messagebox.showinfo("Tamam", f"Kaydedildi:\n{yol}", parent=self)

    def _csv(self, ad, fonksiyon):
        self._kaydet(".csv", ad, fonksiyon, "CSV")

    def csv_musteriler(self):
        self._csv("musteriler.csv", lambda y: export.export_customers_csv(self.db, y))

    def csv_bakiyeler(self):
        self._csv("bakiyeler.csv", lambda y: export.export_balances_csv(self.db, y))

    def csv_geciken(self):
        self._csv("geciken.csv", lambda y: export.export_overdue_csv(self.db, y, today_iso()))

    def pdf_bakiyeler(self):
        self._kaydet(".pdf", "bakiye_raporu.pdf", lambda y: pdf_export.bakiye_raporu_pdf(
            self.db, today_iso(), y), "PDF")

    def pdf_geciken(self):
        self._kaydet(".pdf", "geciken_odemeler.pdf", lambda y: pdf_export.geciken_raporu_pdf(
            self.db, today_iso(), y), "PDF")

    def pdf_ekstre(self, cid=None):
        if cid is None:
            sec = self.musteri_tree.selection()
            if not sec:
                messagebox.showinfo("Bilgi", "Önce 'Müşteriler' sekmesinde bir müşteri seçin.", parent=self)
                return
            cid = int(sec[0])
        ad = self.db.get_customer(cid)["ad"].replace(" ", "_")
        self._kaydet(".pdf", f"ekstre_{ad}.pdf", lambda y: pdf_export.musteri_ekstresi_pdf(
            self.db, cid, today_iso(), y), "PDF")


class DetayPenceresi(tk.Toplevel):
    def __init__(self, app, db, cid):
        super().__init__(app)
        self.app, self.db, self.cid = app, db, cid
        self.geometry("900x560")
        self.ozet = ttk.Label(self, font=("", 12, "bold"))
        self.ozet.pack(anchor="w", padx=10, pady=8)

        ttk.Label(self, text="Borçlar").pack(anchor="w", padx=10)
        f1, self.borc_tree = tablo(self, [
            ("tarih", "Tarih", 90), ("aciklama", "Açıklama", 240), ("vade", "Vade", 90),
            ("tutar", "Tutar", 110), ("kalan", "Kalan", 110), ("gun", "Gecikme", 80)], 6)
        f1.pack(fill="both", expand=True, padx=10)
        self.borc_tree.tag_configure("gec", foreground="red")
        b1 = ttk.Frame(self)
        b1.pack(fill="x", padx=10, pady=4)
        ttk.Button(b1, text="Borç Ekle", command=self.borc_ekle).pack(side="left", padx=3)
        ttk.Button(b1, text="Seçili Borcu Sil", command=self.borc_sil).pack(side="left", padx=3)
        ttk.Button(b1, text="PDF Ekstre Al", command=lambda: self.app.pdf_ekstre(self.cid)).pack(
            side="right", padx=3)

        ttk.Label(self, text="Ödemeler").pack(anchor="w", padx=10)
        f2, self.odeme_tree = tablo(self, [
            ("tarih", "Tarih", 90), ("yontem", "Yöntem", 120), ("aciklama", "Açıklama", 240),
            ("tutar", "Tutar", 110)], 6)
        f2.pack(fill="both", expand=True, padx=10)
        b2 = ttk.Frame(self)
        b2.pack(fill="x", padx=10, pady=4)
        ttk.Button(b2, text="Ödeme Ekle", command=self.odeme_ekle).pack(side="left", padx=3)
        ttk.Button(b2, text="Seçili Ödemeyi Sil", command=self.odeme_sil).pack(side="left", padx=3)
        self.yenile()

    def yenile(self):
        m = self.db.get_customer(self.cid)
        b = services.customer_balance(self.db, self.cid)
        self.title(f"{m['ad']} - Detay")
        self.ozet.config(text=f"{m['ad']}   |   Borç: {format_tl(b['toplam_borc'])}   "
                              f"Ödenen: {format_tl(b['toplam_odeme'])}   Kalan: {format_tl(b['bakiye'])}")
        self.borc_tree.delete(*self.borc_tree.get_children())
        for d in services.debt_status(self.db, self.cid, today_iso()):
            self.borc_tree.insert("", "end", iid=str(d["id"]),
                                  tags=("gec",) if d["gecikme_gun"] else (),
                                  values=(format_date(d["tarih"]), d["aciklama"], format_date(d["vade"]),
                                          format_tl(d["tutar"]), format_tl(d["kalan"]),
                                          f"{d['gecikme_gun']} gün" if d["gecikme_gun"] else ""))
        self.odeme_tree.delete(*self.odeme_tree.get_children())
        for p in self.db.list_payments(self.cid):
            self.odeme_tree.insert("", "end", iid=str(p["id"]), values=(
                format_date(p["tarih"]), p["yontem"], p["aciklama"], format_tl(p["tutar"])))
        self.app.yenile()

    def borc_ekle(self):
        d = FormDialog(self, "Borç Ekle", [
            ("tutar", "Tutar (₺) *", ""), ("tarih", "Tarih (gg.aa.yyyy)", format_date(today_iso())),
            ("vade", "Vade (gg.aa.yyyy)", ""), ("aciklama", "Açıklama", "")])
        if d.sonuc:
            try:
                self.db.add_debt(self.cid, parse_tl(d.sonuc["tutar"]),
                                 parse_date(d.sonuc["tarih"]) or today_iso(),
                                 parse_date(d.sonuc["vade"]), d.sonuc["aciklama"])
            except ValueError as e:
                return self.app._hata(e)
            self.yenile()

    def odeme_ekle(self):
        d = FormDialog(self, "Ödeme Ekle", [
            ("tutar", "Tutar (₺) *", ""), ("tarih", "Tarih (gg.aa.yyyy)", format_date(today_iso())),
            ("yontem", "Yöntem (nakit/havale...)", ""), ("aciklama", "Açıklama", "")])
        if d.sonuc:
            try:
                self.db.add_payment(self.cid, parse_tl(d.sonuc["tutar"]),
                                    parse_date(d.sonuc["tarih"]) or today_iso(),
                                    d.sonuc["yontem"], d.sonuc["aciklama"])
            except ValueError as e:
                return self.app._hata(e)
            self.yenile()

    def borc_sil(self):
        sec = self.borc_tree.selection()
        if sec and messagebox.askyesno("Sil", "Seçili borç silinsin mi?", parent=self):
            self.db.delete_debt(int(sec[0]))
            self.yenile()

    def odeme_sil(self):
        sec = self.odeme_tree.selection()
        if sec and messagebox.askyesno("Sil", "Seçili ödeme silinsin mi?", parent=self):
            self.db.delete_payment(int(sec[0]))
            self.yenile()
