"""tkinter arayüzü: kenar çubuklu, kartlı panelli modern tasarım."""
import os
import subprocess
import sys
import tkinter as tk
from datetime import date, timedelta
from tkinter import filedialog, messagebox, ttk
from tkinter import font as tkfont

import export
import pdf_export
import services
from config import FIRMA_ADI, resource_path
from format import format_date, format_tl, parse_date, parse_tl, today_iso

# ---- Renkler (logodaki kırmızı temel alındı) ----
KIRMIZI = "#E31E24"
KIRMIZI_KOYU = "#B9161B"
KIRMIZI_ACIK = "#FDECEC"
YAN_BG = "#1F2328"
YAN_HOVER = "#2D333B"
YAN_YAZI = "#C9D1D9"
ZEMIN = "#F4F5F7"
BEYAZ = "#FFFFFF"
KENAR = "#E1E4E8"
YAZI = "#1F2328"
SOLUK = "#6B7280"
YESIL = "#1E8E3E"
YESIL_ACIK = "#E7F5EC"
TURUNCU = "#B45309"
TURUNCU_ACIK = "#FEF3C7"
SATIR_ALT = "#F8F9FB"

ODEME_YONTEMLERI = ["Nakit", "Havale/EFT", "Kredi Kartı", "Çek", "Senet"]


class Dugme(ttk.Button):
    """Metne göre boyutlanan ttk düğmesi (varsayılan en az 9 karakter genişliği yerine)."""

    def __init__(self, parent, **kw):
        kw.setdefault("width", 0)
        super().__init__(parent, **kw)


def tutar_metni(kurus):
    """Forma yazılacak tutar: 11000050 -> '110.000,50'"""
    lira, kr = divmod(int(kurus), 100)
    return f"{lira:,}".replace(",", ".") + f",{kr:02d}"


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


def tema_kur(root):
    """Yazı tipi ve ttk stillerini ayarlar."""
    aileler = set(tkfont.families())
    aile = next((a for a in ("Segoe UI", "Calibri", "Helvetica", "DejaVu Sans") if a in aileler), "TkDefaultFont")
    for ad in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont", "TkFixedFont"):
        try:
            tkfont.nametofont(ad).configure(family=aile, size=10)
        except tk.TclError:
            pass
    root.configure(bg=ZEMIN)
    st = ttk.Style(root)
    st.theme_use("clam")
    st.configure(".", background=ZEMIN, foreground=YAZI, font=(aile, 10), bordercolor=KENAR,
                 focuscolor=ZEMIN, troughcolor=ZEMIN)
    st.configure("TFrame", background=ZEMIN)
    st.configure("Beyaz.TFrame", background=BEYAZ)
    st.configure("TLabel", background=ZEMIN, foreground=YAZI)
    st.configure("Beyaz.TLabel", background=BEYAZ)
    st.configure("Soluk.TLabel", foreground=SOLUK)
    st.configure("BeyazSoluk.TLabel", background=BEYAZ, foreground=SOLUK)
    st.configure("Baslik.TLabel", font=(aile, 18, "bold"))
    st.configure("Alt.TLabel", font=(aile, 11, "bold"))
    st.configure("Hata.TLabel", background=BEYAZ, foreground=KIRMIZI)
    # düğmeler
    st.configure("TButton", background=BEYAZ, foreground=YAZI, bordercolor="#C9CED6", padding=(14, 7),
                 relief="solid", borderwidth=1, lightcolor=BEYAZ, darkcolor=BEYAZ)
    st.map("TButton", background=[("active", "#EEF0F3"), ("pressed", "#E3E6EA")])
    st.configure("Accent.TButton", background=KIRMIZI, foreground=BEYAZ, bordercolor=KIRMIZI,
                 lightcolor=KIRMIZI, darkcolor=KIRMIZI, font=(aile, 10, "bold"))
    st.map("Accent.TButton", background=[("active", KIRMIZI_KOYU), ("pressed", KIRMIZI_KOYU)],
           foreground=[("active", BEYAZ)])
    st.configure("Tehlike.TButton", foreground=KIRMIZI, bordercolor="#F0B4B6")
    # giriş alanları
    st.configure("TEntry", fieldbackground=BEYAZ, bordercolor=KENAR, lightcolor=KENAR,
                 darkcolor=KENAR, padding=6)
    st.map("TEntry", bordercolor=[("focus", KIRMIZI)], lightcolor=[("focus", KIRMIZI)],
           darkcolor=[("focus", KIRMIZI)])
    st.configure("TCombobox", fieldbackground=BEYAZ, background=BEYAZ, bordercolor=KENAR,
                 arrowcolor=SOLUK, padding=5)
    st.map("TCombobox", fieldbackground=[("readonly", BEYAZ)], bordercolor=[("focus", KIRMIZI)])
    # tablolar
    st.configure("Treeview", background=BEYAZ, fieldbackground=BEYAZ, foreground=YAZI, rowheight=30,
                 borderwidth=0, font=(aile, 10))
    st.configure("Treeview.Heading", background="#EEF0F3", foreground=YAZI, relief="flat",
                 font=(aile, 10, "bold"), padding=(8, 7), borderwidth=0)
    st.map("Treeview.Heading", background=[("active", "#E3E6EA")])
    st.map("Treeview", background=[("selected", KIRMIZI_ACIK)], foreground=[("selected", YAZI)])
    st.configure("TNotebook", background=ZEMIN, borderwidth=0)
    st.configure("TNotebook.Tab", padding=(18, 8), background="#E9EBEF", foreground=SOLUK,
                 font=(aile, 10, "bold"))
    st.map("TNotebook.Tab", background=[("selected", BEYAZ)], foreground=[("selected", KIRMIZI)])
    st.configure("Vertical.TScrollbar", background="#D0D4DA", troughcolor=ZEMIN, bordercolor=ZEMIN,
                 arrowcolor=SOLUK)
    # Tk 8.6.9 (Python 3.8/Windows) Treeview etiket renk hatası için çözüm
    def duzelt(secenek):
        return [e for e in st.map("Treeview", query_opt=secenek)
                if e[:2] != ("!disabled", "!selected")]
    st.map("Treeview", foreground=duzelt("foreground"), background=duzelt("background"))
    return aile


def ortala(pencere, ana=None):
    """Pencereyi ekranda veya ana pencerenin üstünde ortalar (boyutu geometry'den, yoksa istenen boyuttan alır)."""
    pencere.update_idletasks()
    boyut = pencere.geometry().split("+")[0]
    try:
        w, h = (int(x) for x in boyut.split("x"))
    except ValueError:
        w = h = 1
    if w <= 1 or h <= 1:
        w, h = pencere.winfo_reqwidth(), pencere.winfo_reqheight()
    if ana is not None and ana.winfo_ismapped():
        x = ana.winfo_rootx() + (ana.winfo_width() - w) // 2
        y = ana.winfo_rooty() + (ana.winfo_height() - h) // 3
    else:
        x = (pencere.winfo_screenwidth() - w) // 2
        y = (pencere.winfo_screenheight() - h) // 3
    pencere.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")


def tablo(parent, kolonlar, yukseklik=10):
    """kolonlar: [(anahtar, başlık, genişlik, hizalama[w/e/center])] -> (çerçeve, Treeview)"""
    cerceve = tk.Frame(parent, bg=BEYAZ, highlightbackground=KENAR, highlightthickness=1,
                       width=100, height=yukseklik * 30 + 40)
    cerceve.pack_propagate(False)  # içerik genişliği pencereyi taşırmasın
    tree = ttk.Treeview(cerceve, columns=[k[0] for k in kolonlar], show="headings", height=yukseklik,
                        selectmode="browse")
    for k, baslik, genislik, hiza in kolonlar:
        tree.heading(k, text=baslik, anchor=hiza)
        tree.column(k, width=genislik, anchor=hiza, minwidth=60)
    sb = ttk.Scrollbar(cerceve, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=sb.set)
    tree.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    ilk_genislik = {k[0]: k[2] for k in kolonlar}

    def sigdir(olay):
        mevcut = olay.width - 24  # kaydırma çubuğu payı
        toplam = sum(ilk_genislik.values())
        oran = min(1.0, mevcut / toplam) if mevcut > 0 else 1.0
        for k, g in ilk_genislik.items():
            tree.column(k, width=max(55, int(g * oran)))

    cerceve.bind("<Configure>", sigdir)
    tree.tag_configure("alt", background=SATIR_ALT)
    tree.tag_configure("gec", background=KIRMIZI_ACIK, foreground=KIRMIZI_KOYU)
    tree.tag_configure("yakin", background=TURUNCU_ACIK, foreground=TURUNCU)
    tree.tag_configure("temiz", foreground=SOLUK)
    return cerceve, tree


def doldur(tree, satirlar):
    """satirlar: [(iid, değerler, etiketler)]"""
    tree.delete(*tree.get_children())
    for i, (iid, degerler, etiketler) in enumerate(satirlar):
        tags = tuple(etiketler) or (("alt",) if i % 2 else ())
        tree.insert("", "end", iid=iid, values=degerler, tags=tags)


class Kart(tk.Frame):
    """Özet kartı: başlık, büyük değer, alt açıklama ve renkli üst şerit."""

    def __init__(self, parent, baslik, renk=KIRMIZI):
        super().__init__(parent, bg=BEYAZ, highlightbackground=KENAR, highlightthickness=1)
        tk.Frame(self, bg=renk, height=4).pack(fill="x")
        iç = tk.Frame(self, bg=BEYAZ)
        iç.pack(fill="both", expand=True, padx=14, pady=(10, 12))
        ttk.Label(iç, text=baslik, style="BeyazSoluk.TLabel").pack(anchor="w")
        self.deger = tk.Label(iç, text="-", bg=BEYAZ, fg=YAZI, font=("", 17, "bold"), anchor="w")
        self.deger.pack(anchor="w", pady=(2, 0))
        self.alt = ttk.Label(iç, text="", style="BeyazSoluk.TLabel")
        self.alt.pack(anchor="w")

    def ayarla(self, deger, alt="", renk=None):
        self.deger.config(text=deger, fg=renk or YAZI)
        self.alt.config(text=alt)


class Form(tk.Toplevel):
    """Modal giriş formu. Doğrulama hatasında pencere açık kalır, hata altta gösterilir.

    alanlar: [dict(anahtar, etiket, deger="", tur="metin|not|tarih|tutar|secim",
                   secenekler=[], hizli=[gün sayıları])]
    uygula(degerler): kaydı yapar, ValueError fırlatırsa hata gösterilir.
    """

    def __init__(self, ana, baslik, alanlar, uygula, alt_baslik="", kaydet_metni="Kaydet"):
        super().__init__(ana)
        self.title(baslik)
        self.configure(bg=BEYAZ)
        self.transient(ana.winfo_toplevel())
        self.resizable(False, False)
        self.tamam = False
        self.uygula = uygula
        self.girdiler = {}
        govde = ttk.Frame(self, style="Beyaz.TFrame", padding=(24, 20, 24, 8))
        govde.pack(fill="both", expand=True)
        ttk.Label(govde, text=baslik, style="Beyaz.TLabel", font=("", 14, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w")
        satir = 1
        if alt_baslik:
            ttk.Label(govde, text=alt_baslik, style="BeyazSoluk.TLabel").grid(
                row=1, column=0, columnspan=2, sticky="w", pady=(2, 0))
            satir = 2
        ttk.Frame(govde, style="Beyaz.TFrame", height=10).grid(row=satir, column=0)
        satir += 1
        ilk = None
        for a in alanlar:
            ttk.Label(govde, text=a["etiket"], style="Beyaz.TLabel").grid(
                row=satir, column=0, sticky="nw", padx=(0, 16), pady=7)
            tur = a.get("tur", "metin")
            if tur == "not":
                w = tk.Text(govde, width=38, height=4, relief="flat", wrap="word",
                            highlightbackground=KENAR, highlightcolor=KIRMIZI, highlightthickness=1,
                            padx=6, pady=5)
                w.insert("1.0", a.get("deger", ""))
                w.grid(row=satir, column=1, sticky="we", pady=4)
                self.girdiler[a["anahtar"]] = lambda w=w: w.get("1.0", "end").strip()
            elif tur == "secim":
                w = ttk.Combobox(govde, values=a.get("secenekler", []), width=36)
                w.set(a.get("deger", ""))
                w.grid(row=satir, column=1, sticky="we", pady=4)
                self.girdiler[a["anahtar"]] = w.get
            else:
                kutu = ttk.Frame(govde, style="Beyaz.TFrame")
                kutu.grid(row=satir, column=1, sticky="w", pady=4)
                w = ttk.Entry(kutu, width={"tarih": 14, "tutar": 22}.get(tur, 38),
                              justify="right" if tur == "tutar" else "left")
                w.insert(0, a.get("deger", ""))
                w.pack(side="left")
                if tur == "tarih":
                    Dugme(kutu, text="Bugün", padding=(8, 4),
                               command=lambda w=w: self._tarih_ayarla(w, 0)).pack(side="left", padx=(6, 0))
                    for g in a.get("hizli", []):
                        Dugme(kutu, text=f"+{g} gün", padding=(8, 4),
                                   command=lambda w=w, g=g: self._tarih_ayarla(w, g)).pack(side="left", padx=(4, 0))
                if tur == "tutar":
                    ttk.Label(kutu, text="₺", style="BeyazSoluk.TLabel").pack(side="left", padx=(6, 0))
                self.girdiler[a["anahtar"]] = w.get
            if ilk is None:
                ilk = w
            satir += 1
        self.hata = ttk.Label(govde, text="", style="Hata.TLabel", wraplength=380)
        self.hata.grid(row=satir, column=0, columnspan=2, sticky="w", pady=(6, 0))
        alt = ttk.Frame(self, style="Beyaz.TFrame", padding=(24, 8, 24, 20))
        alt.pack(fill="x")
        Dugme(alt, text="İptal", command=self.destroy).pack(side="right")
        Dugme(alt, text=kaydet_metni, style="Accent.TButton", command=self._kaydet).pack(
            side="right", padx=(0, 8))
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", self._enter)
        ortala(self, ana.winfo_toplevel())
        self.grab_set()
        if ilk is not None:
            ilk.focus_set()
        self.wait_window()

    @staticmethod
    def _tarih_ayarla(girdi, gun):
        girdi.delete(0, "end")
        girdi.insert(0, format_date((date.today() + timedelta(days=gun)).isoformat()))

    def _enter(self, olay):
        if not isinstance(olay.widget, tk.Text):
            self._kaydet()

    def _kaydet(self):
        degerler = {k: f() for k, f in self.girdiler.items()}
        try:
            self.uygula(degerler)
        except ValueError as e:
            self.hata.config(text=str(e))
            return
        self.tamam = True
        self.destroy()


class SayfaTaslagi(ttk.Frame):
    """Sayfa başlığı + içerik alanı."""

    def __init__(self, app, baslik, aciklama=""):
        super().__init__(app.icerik)
        self.app = app
        ust = ttk.Frame(self)
        ust.pack(fill="x", padx=24, pady=(20, 10))
        sol = ttk.Frame(ust)
        sol.pack(side="left")
        ttk.Label(sol, text=baslik, style="Baslik.TLabel").pack(anchor="w")
        if aciklama:
            ttk.Label(sol, text=aciklama, style="Soluk.TLabel").pack(anchor="w")
        self.ust_sag = ttk.Frame(ust)
        self.ust_sag.pack(side="right")
        self.govde = ttk.Frame(self)
        self.govde.pack(fill="both", expand=True, padx=24, pady=(0, 16))

    def yenile(self):
        pass


class PanelSayfa(SayfaTaslagi):
    def __init__(self, app):
        super().__init__(app, "Panel", "Alacak durumunuza genel bakış")
        Dugme(self.ust_sag, text="+ Yeni Müşteri", style="Accent.TButton",
                   command=app.musteri_ekle).pack(side="right")
        Dugme(self.ust_sag, text="Borç / Ödeme İşle", command=app.hizli_islem).pack(
            side="right", padx=(0, 8))
        kartlar = ttk.Frame(self.govde)
        kartlar.pack(fill="x")
        self.kartlar = {}
        for i, (anahtar, baslik, renk) in enumerate((
                ("alacak", "Toplam Alacak", KIRMIZI), ("tahsilat", "Bu Ay Tahsilat", YESIL),
                ("geciken", "Geciken Tutar", "#C2410C"), ("musteri", "Müşteri Sayısı", "#475569"))):
            k = Kart(kartlar, baslik, renk)
            k.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            kartlar.columnconfigure(i, weight=1, uniform="kart")
            self.kartlar[anahtar] = k
        orta = ttk.Frame(self.govde)
        orta.pack(fill="both", expand=True, pady=(18, 0))
        orta.columnconfigure(0, weight=1, uniform="k")
        orta.columnconfigure(1, weight=1, uniform="k")
        orta.rowconfigure(1, weight=1)
        orta.rowconfigure(3, weight=1)
        ttk.Label(orta, text="Geciken Ödemeler", style="Alt.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        c1, self.geciken_tree = tablo(orta, [("m", "Müşteri", 150, "w"), ("v", "Vade", 80, "center"),
                                            ("k", "Kalan", 100, "e"), ("g", "Gün", 50, "center")], 6)
        c1.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        ttk.Label(orta, text="Yaklaşan Ödemeler (7 gün)", style="Alt.TLabel").grid(
            row=0, column=1, sticky="w", pady=(0, 6), padx=(8, 0))
        c2, self.yaklasan_tree = tablo(orta, [("m", "Müşteri", 150, "w"), ("v", "Vade", 80, "center"),
                                             ("k", "Kalan", 100, "e"), ("g", "Kalan gün", 85, "center")], 6)
        c2.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        ttk.Label(orta, text="Son Tahsilatlar", style="Alt.TLabel").grid(
            row=2, column=0, sticky="w", pady=(16, 6), columnspan=2)
        c3, self.son_tree = tablo(orta, [("t", "Tarih", 90, "center"), ("m", "Müşteri", 200, "w"),
                                        ("y", "Yöntem", 120, "w"), ("a", "Açıklama", 220, "w"),
                                        ("u", "Tutar", 110, "e")], 5)
        c3.grid(row=3, column=0, columnspan=2, sticky="nsew")
        for tree in (self.geciken_tree, self.yaklasan_tree):
            tree.bind("<Double-1>", lambda e, t=tree: app.musteri_detay_iid(t.selection()))

    def yenile(self):
        db, bugun = self.app.db, today_iso()
        s = services.summary(db, bugun)
        self.kartlar["alacak"].ayarla(format_tl(s["toplam_alacak"]), "tüm açık bakiyeler")
        self.kartlar["tahsilat"].ayarla(format_tl(s["ay_tahsilat"]), "içinde bulunulan ay", YESIL)
        self.kartlar["geciken"].ayarla(
            format_tl(s["geciken_tutar"]),
            f"{s['geciken_musteri']} müşteri vadesi geçmiş" if s["geciken_musteri"] else "gecikme yok",
            KIRMIZI if s["geciken_tutar"] else YESIL)
        self.kartlar["musteri"].ayarla(str(s["musteri_sayisi"]), "kayıtlı müşteri")
        geciken = services.overdue_list(db, bugun)[:50]
        doldur(self.geciken_tree, [(f"{r['musteri_id']}:{r['id']}", (
            r["musteri_ad"], format_date(r["vade"]), format_tl(r["kalan"]), r["gecikme_gun"]), ("gec",))
            for r in geciken])
        yaklasan = services.upcoming_list(db, bugun, 7)
        doldur(self.yaklasan_tree, [(f"{r['musteri_id']}:{r['id']}", (
            r["musteri_ad"], format_date(r["vade"]), format_tl(r["kalan"]),
            "bugün" if r["kalan_gun"] == 0 else r["kalan_gun"]), ("yakin",)) for r in yaklasan])
        doldur(self.son_tree, [(str(p["id"]), (
            format_date(p["tarih"]), p["musteri_ad"], p["yontem"], p["aciklama"], format_tl(p["tutar"])), ())
            for p in db.recent_payments(8)])


class MusteriSayfa(SayfaTaslagi):
    DURUM = {"gecikmis": "Gecikmiş", "guncel": "Güncel", "borcu_yok": "Borcu yok"}

    def __init__(self, app):
        super().__init__(app, "Müşteriler", "Müşteri kayıtları ve bakiyeleri")
        Dugme(self.ust_sag, text="+ Yeni Müşteri", style="Accent.TButton",
                   command=app.musteri_ekle).pack(side="right")
        araç = ttk.Frame(self.govde)
        araç.pack(fill="x", pady=(0, 10))
        self.arama = tk.StringVar()
        self.arama.trace_add("write", lambda *a: self.yenile())
        self.giris = ttk.Entry(araç, textvariable=self.arama, width=24)
        self.giris.pack(side="left")
        self.ipucu = tk.Label(araç, text="Ad, telefon veya e-posta ara…", bg=BEYAZ, fg=SOLUK, cursor="xterm")
        self.ipucu.bind("<Button-1>", lambda e: self.giris.focus_set())
        self.filtre = ttk.Combobox(araç, state="readonly", width=14,
                                   values=["Tüm müşteriler", "Borcu olanlar", "Gecikmiş", "Borcu yok"])
        self.filtre.current(0)
        self.filtre.pack(side="left", padx=(10, 0))
        self.filtre.bind("<<ComboboxSelected>>", lambda e: self.yenile())
        for ad, komut, stil in (("Sil", self.sil, "Tehlike.TButton"), ("Düzenle", self.duzenle, "TButton"),
                                ("Ödeme Al", self.odeme_al, "TButton"), ("Borç Ekle", self.borc_ekle, "TButton"),
                                ("Detay", self.detay, "TButton")):
            Dugme(araç, text=ad, command=komut, style=stil).pack(side="right", padx=(6, 0))
        cerceve, self.tree = tablo(self.govde, [
            ("ad", "Müşteri", 170, "w"), ("telefon", "Telefon", 115, "w"), ("eposta", "E-posta", 150, "w"),
            ("borc", "Toplam Borç", 115, "e"), ("odeme", "Ödenen", 105, "e"), ("bakiye", "Kalan Bakiye", 120, "e"),
            ("durum", "Durum", 145, "center")], 16)
        cerceve.pack(fill="both", expand=True)
        self.alt = ttk.Label(self.govde, text="", style="Soluk.TLabel")
        self.alt.pack(anchor="w", pady=(8, 0))
        self.tree.bind("<Double-1>", lambda e: self.detay())
        self.tree.bind("<Return>", lambda e: self.detay())
        self.tree.bind("<Delete>", lambda e: self.sil())
        self.menu = tk.Menu(self.tree, tearoff=0)
        for ad, komut in (("Detay", self.detay), ("Borç Ekle", self.borc_ekle), ("Ödeme Al", self.odeme_al),
                          ("PDF Ekstre", self.ekstre), ("Düzenle", self.duzenle), ("Sil", self.sil)):
            self.menu.add_command(label=ad, command=komut)
        self.tree.bind("<Button-3>", self._sag_tik)
        self.tree.bind("<Button-2>", self._sag_tik)

    def _sag_tik(self, olay):
        iid = self.tree.identify_row(olay.y)
        if iid:
            self.tree.selection_set(iid)
            self.menu.tk_popup(olay.x_root, olay.y_root)

    def _ipucu_goster(self, *_):
        if self.arama.get():
            self.ipucu.place_forget()
        else:
            self.ipucu.place(in_=self.giris, x=10, rely=0.5, anchor="w")

    def yenile(self):
        filtre = ["tumu", "borclu", "gecikmis", "borcu_yok"][self.filtre.current()]
        satirlar = services.customers_overview(self.app.db, today_iso(), self.arama.get(), filtre)
        sec = self.tree.selection()
        veri = []
        for r in satirlar:
            durum = self.DURUM[r["durum"]]
            if r["durum"] == "gecikmis":
                durum += f" ({r['gecikme_gun']} gün)"
            etiket = {"gecikmis": ("gec",), "borcu_yok": ("temiz",)}.get(r["durum"], ())
            veri.append((str(r["id"]), (r["ad"], r["telefon"], r["eposta"], format_tl(r["toplam_borc"]),
                                        format_tl(r["toplam_odeme"]), format_tl(r["bakiye"]), durum), etiket))
        doldur(self.tree, veri)
        if sec and self.tree.exists(sec[0]):
            self.tree.selection_set(sec[0])
        toplam = sum(r["bakiye"] for r in satirlar if r["bakiye"] > 0)
        self.alt.config(text=f"{len(satirlar)} müşteri listeleniyor · toplam açık bakiye: {format_tl(toplam)}")
        self._ipucu_goster()

    def secili(self):
        sec = self.tree.selection()
        if not sec:
            messagebox.showinfo("Müşteri seçin", "Lütfen listeden bir müşteri seçin.", parent=self.app)
            return None
        return int(sec[0])

    def detay(self):
        cid = self.secili()
        if cid is not None:
            self.app.musteri_detay(cid)

    def duzenle(self):
        cid = self.secili()
        if cid is not None:
            self.app.musteri_duzenle(cid)

    def sil(self):
        cid = self.secili()
        if cid is not None:
            self.app.musteri_sil(cid)

    def borc_ekle(self):
        cid = self.secili()
        if cid is not None:
            self.app.borc_formu(cid)

    def odeme_al(self):
        cid = self.secili()
        if cid is not None:
            self.app.odeme_formu(cid)

    def ekstre(self):
        cid = self.secili()
        if cid is not None:
            self.app.pdf_ekstre(cid)


class GecikenSayfa(SayfaTaslagi):
    def __init__(self, app):
        super().__init__(app, "Geciken Ödemeler", "Vadesi geçmiş ve henüz ödenmemiş borçlar")
        Dugme(self.ust_sag, text="PDF Rapor", command=app.pdf_geciken).pack(side="right")
        self.ozet = ttk.Label(self.govde, text="", style="Alt.TLabel")
        self.ozet.pack(anchor="w", pady=(0, 8))
        cerceve, self.tree = tablo(self.govde, [
            ("m", "Müşteri", 220, "w"), ("t", "Telefon", 120, "w"), ("a", "Açıklama", 240, "w"),
            ("v", "Vade", 90, "center"), ("k", "Kalan", 120, "e"), ("g", "Gecikme", 100, "center")], 18)
        cerceve.pack(fill="both", expand=True)
        self.tree.bind("<Double-1>", lambda e: app.musteri_detay_iid(self.tree.selection()))
        ttk.Label(self.govde, text="Satıra çift tıklayarak müşteri detayına gidebilirsiniz.",
                  style="Soluk.TLabel").pack(anchor="w", pady=(8, 0))

    def yenile(self):
        satirlar = services.overdue_list(self.app.db, today_iso())
        doldur(self.tree, [(f"{r['musteri_id']}:{r['id']}", (
            r["musteri_ad"], r["telefon"], r["aciklama"], format_date(r["vade"]), format_tl(r["kalan"]),
            f"{r['gecikme_gun']} gün"), ("gec",) if i % 2 == 0 else ()) for i, r in enumerate(satirlar)])
        toplam = sum(r["kalan"] for r in satirlar)
        self.ozet.config(text=f"{len(satirlar)} geciken kalem · toplam {format_tl(toplam)}" if satirlar
                         else "Geciken ödeme yok")


class RaporSayfa(SayfaTaslagi):
    def __init__(self, app):
        super().__init__(app, "Raporlar", "PDF ve Excel (CSV) çıktıları")
        self.musteriler = {}
        ttk.Label(self.govde, text="Müşteri Ekstresi", style="Alt.TLabel").pack(anchor="w")
        satir = ttk.Frame(self.govde)
        satir.pack(fill="x", pady=(6, 18))
        self.secim = ttk.Combobox(satir, state="readonly", width=40)
        self.secim.pack(side="left")
        Dugme(satir, text="PDF Ekstre Al", style="Accent.TButton", command=self.ekstre).pack(
            side="left", padx=(10, 0))
        ttk.Label(self.govde, text="Genel PDF Raporları (firma logolu)", style="Alt.TLabel").pack(anchor="w")
        satir = ttk.Frame(self.govde)
        satir.pack(fill="x", pady=(6, 18))
        Dugme(satir, text="Bakiye Raporu (PDF)", command=app.pdf_bakiyeler).pack(side="left")
        Dugme(satir, text="Geciken Ödemeler (PDF)", command=app.pdf_geciken).pack(side="left", padx=(8, 0))
        ttk.Label(self.govde, text="Excel için CSV Dışa Aktarma", style="Alt.TLabel").pack(anchor="w")
        satir = ttk.Frame(self.govde)
        satir.pack(fill="x", pady=(6, 0))
        Dugme(satir, text="Müşteriler", command=app.csv_musteriler).pack(side="left")
        Dugme(satir, text="Bakiyeler", command=app.csv_bakiyeler).pack(side="left", padx=(8, 0))
        Dugme(satir, text="Geciken Liste", command=app.csv_geciken).pack(side="left", padx=(8, 0))

    def yenile(self):
        self.musteriler = {m["ad"] + f"  (#{m['id']})": m["id"] for m in self.app.db.list_customers()}
        self.secim.config(values=list(self.musteriler))
        if self.secim.get() not in self.musteriler:
            self.secim.set(next(iter(self.musteriler), ""))

    def ekstre(self):
        cid = self.musteriler.get(self.secim.get())
        if cid is None:
            messagebox.showinfo("Müşteri seçin", "Lütfen bir müşteri seçin.", parent=self.app)
            return
        self.app.pdf_ekstre(cid)


class App(tk.Tk):
    SAYFALAR = (("panel", "Panel"), ("musteri", "Müşteriler"), ("geciken", "Geciken Ödemeler"),
                ("rapor", "Raporlar"))

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.title(f"{FIRMA_ADI} - Müşteri Takip")
        self.geometry("%dx%d" % (min(1280, self.winfo_screenwidth() - 40),
                                 min(760, self.winfo_screenheight() - 90)))
        self.minsize(1100, 600)
        tema_kur(self)
        self.logo_kucuk = None
        try:
            logo = tk.PhotoImage(file=resource_path("assets/logo.png"))
            self.iconphoto(True, logo)
            self.logo_kucuk = logo.subsample(max(1, logo.width() // 56))
            self._logo = logo
        except tk.TclError:
            pass
        self._yan_menu_kur()
        sag = ttk.Frame(self)
        sag.pack(side="left", fill="both", expand=True)
        self.durum = tk.Label(sag, text="", bg=BEYAZ, fg=SOLUK, anchor="w", padx=14, pady=4,
                              highlightbackground=KENAR, highlightthickness=1)
        self.durum.pack(fill="x", side="bottom")
        self.icerik = ttk.Frame(sag)
        self.icerik.pack(fill="both", expand=True)
        self.sayfalar = {"panel": PanelSayfa(self), "musteri": MusteriSayfa(self),
                         "geciken": GecikenSayfa(self), "rapor": RaporSayfa(self)}
        self.aktif = None
        self.bind("<F5>", lambda e: self.yenile())
        self.bind("<Control-n>", lambda e: self.musteri_ekle())
        self.bind("<Control-f>", lambda e: self._ara_odak())
        self.git("panel")
        ortala(self)

    # ---- yan menü ----
    def _yan_menu_kur(self):
        yan = tk.Frame(self, bg=YAN_BG, width=210)
        yan.pack(side="left", fill="y")
        yan.pack_propagate(False)
        ust = tk.Frame(yan, bg=YAN_BG)
        ust.pack(fill="x", padx=18, pady=(22, 20))
        if self.logo_kucuk:
            tk.Label(ust, image=self.logo_kucuk, bg=YAN_BG).pack(side="left", padx=(0, 10))
        tk.Label(ust, text="Yıldız Yapı\nMimarlık", bg=YAN_BG, fg=BEYAZ, justify="left",
                 font=("", 12, "bold")).pack(side="left")
        tk.Label(yan, text="MÜŞTERİ TAKİP", bg=YAN_BG, fg="#6E7681", anchor="w",
                 font=("", 8, "bold")).pack(fill="x", padx=22, pady=(0, 6))
        self.menu_ogeleri = {}
        for anahtar, ad in self.SAYFALAR:
            cerceve = tk.Frame(yan, bg=YAN_BG, cursor="hand2")
            cerceve.pack(fill="x")
            serit = tk.Frame(cerceve, bg=YAN_BG, width=4)
            serit.pack(side="left", fill="y")
            etiket = tk.Label(cerceve, text=ad, bg=YAN_BG, fg=YAN_YAZI, anchor="w", padx=18, pady=11,
                              font=("", 11), cursor="hand2")
            etiket.pack(side="left", fill="x", expand=True)
            for w in (cerceve, etiket):
                w.bind("<Button-1>", lambda e, a=anahtar: self.git(a))
                w.bind("<Enter>", lambda e, a=anahtar: self._vurgu(a, True))
                w.bind("<Leave>", lambda e, a=anahtar: self._vurgu(a, False))
            self.menu_ogeleri[anahtar] = (cerceve, serit, etiket)
        tk.Label(yan, text="Kısayollar\nCtrl+N  Yeni müşteri\nCtrl+F  Ara\nF5  Yenile", bg=YAN_BG,
                 fg="#6E7681", justify="left", anchor="w", font=("", 8)).pack(
            side="bottom", fill="x", padx=22, pady=18)

    def _vurgu(self, anahtar, uzerinde):
        cerceve, serit, etiket = self.menu_ogeleri[anahtar]
        if anahtar == self.aktif:
            return
        renk = YAN_HOVER if uzerinde else YAN_BG
        for w in (cerceve, etiket):
            w.config(bg=renk)

    def git(self, anahtar):
        if self.aktif:
            self.sayfalar[self.aktif].pack_forget()
        self.aktif = anahtar
        for a, (cerceve, serit, etiket) in self.menu_ogeleri.items():
            secili = a == anahtar
            bg = YAN_HOVER if secili else YAN_BG
            cerceve.config(bg=bg)
            etiket.config(bg=bg, fg=BEYAZ if secili else YAN_YAZI)
            serit.config(bg=KIRMIZI if secili else bg)
        self.sayfalar[anahtar].pack(fill="both", expand=True)
        self.yenile()

    def yenile(self):
        self.sayfalar[self.aktif].yenile()
        s = services.summary(self.db, today_iso())
        self.durum.config(text=f"Bugün: {format_date(today_iso())}    ·    {s['musteri_sayisi']} müşteri    ·    "
                               f"Toplam alacak: {format_tl(s['toplam_alacak'])}    ·    "
                               f"Geciken: {format_tl(s['geciken_tutar'])}")

    def _ara_odak(self):
        self.git("musteri")
        self.sayfalar["musteri"].giris.focus_set()

    def _hata(self, e):
        messagebox.showerror("Hata", str(e), parent=self)

    # ---- müşteri işlemleri ----
    @staticmethod
    def _musteri_alanlari(m=None):
        g = (lambda k: m[k] if m else "")
        return [dict(anahtar="ad", etiket="Ad / Ünvan *", deger=g("ad")),
                dict(anahtar="telefon", etiket="Telefon", deger=g("telefon")),
                dict(anahtar="eposta", etiket="E-posta", deger=g("eposta")),
                dict(anahtar="adres", etiket="Adres", deger=g("adres"), tur="not"),
                dict(anahtar="notlar", etiket="Not", deger=g("notlar"), tur="not")]

    def musteri_ekle(self):
        f = Form(self, "Yeni Müşteri", self._musteri_alanlari(),
                 lambda v: self.db.add_customer(**v), "Müşteri bilgilerini girin.")
        if f.tamam:
            self.git("musteri")

    def musteri_duzenle(self, cid):
        f = Form(self, "Müşteriyi Düzenle", self._musteri_alanlari(self.db.get_customer(cid)),
                 lambda v: self.db.update_customer(cid, **v))
        if f.tamam:
            self.yenile()

    def musteri_sil(self, cid):
        m = self.db.get_customer(cid)
        if messagebox.askyesno("Müşteriyi sil", f"'{m['ad']}' ve tüm borç/ödeme kayıtları kalıcı olarak "
                               "silinecek.\n\nDevam edilsin mi?", icon="warning", parent=self):
            self.db.delete_customer(cid)
            self.yenile()

    def musteri_detay(self, cid):
        DetayPenceresi(self, self.db, cid)

    def musteri_detay_iid(self, secim):
        if secim:
            self.musteri_detay(int(secim[0].split(":")[0]))

    def hizli_islem(self):
        """Müşteri seçtirip borç veya ödeme formu açar."""
        musteriler = self.db.list_customers()
        if not musteriler:
            messagebox.showinfo("Müşteri yok", "Önce bir müşteri ekleyin.", parent=self)
            return
        secenek = {f"{m['ad']}  (#{m['id']})": m["id"] for m in musteriler}
        islem = {}

        def uygula(v):
            if v["musteri"] not in secenek:
                raise ValueError("Listeden bir müşteri seçin.")
            islem["cid"], islem["tur"] = secenek[v["musteri"]], v["islem"]

        Form(self, "Borç / Ödeme İşle", [
            dict(anahtar="musteri", etiket="Müşteri *", tur="secim", secenekler=list(secenek)),
            dict(anahtar="islem", etiket="İşlem *", tur="secim", deger="Ödeme Al",
                 secenekler=["Ödeme Al", "Borç Ekle"])], uygula, kaydet_metni="Devam")
        if islem:
            (self.odeme_formu if islem["tur"] == "Ödeme Al" else self.borc_formu)(islem["cid"])

    # ---- borç / ödeme formları ----
    def borc_formu(self, cid, did=None):
        d = self.db.get_debt(did) if did else None
        m = self.db.get_customer(cid)

        def uygula(v):
            tutar = parse_tl(v["tutar"])
            tarih = parse_date(v["tarih"]) or today_iso()
            vade = parse_date(v["vade"])
            if vade and vade < tarih:
                raise ValueError("Vade tarihi borç tarihinden önce olamaz.")
            if did:
                self.db.update_debt(did, tutar, tarih, vade, v["aciklama"])
            else:
                self.db.add_debt(cid, tutar, tarih, vade, v["aciklama"])

        f = Form(self, "Borç Düzenle" if d else "Borç Ekle", [
            dict(anahtar="tutar", etiket="Tutar *", tur="tutar",
                 deger=tutar_metni(d["tutar"]) if d else ""),
            dict(anahtar="tarih", etiket="Borç tarihi", tur="tarih",
                 deger=format_date(d["tarih"] if d else today_iso())),
            dict(anahtar="vade", etiket="Vade tarihi", tur="tarih", hizli=[15, 30, 60],
                 deger=format_date(d["vade"]) if d and d["vade"] else ""),
            dict(anahtar="aciklama", etiket="Açıklama", deger=d["aciklama"] if d else "")],
            uygula, alt_baslik=m["ad"])
        if f.tamam:
            self.yenile()
        return f.tamam

    def odeme_formu(self, cid, pid=None):
        p = self.db.get_payment(pid) if pid else None
        m = self.db.get_customer(cid)
        bakiye = services.customer_balance(self.db, cid)["bakiye"]

        def uygula(v):
            tutar = parse_tl(v["tutar"])
            tarih = parse_date(v["tarih"]) or today_iso()
            if pid:
                self.db.update_payment(pid, tutar, tarih, v["yontem"], v["aciklama"])
            else:
                self.db.add_payment(cid, tutar, tarih, v["yontem"], v["aciklama"])

        f = Form(self, "Ödeme Düzenle" if p else "Ödeme Al", [
            dict(anahtar="tutar", etiket="Tutar *", tur="tutar",
                 deger=tutar_metni(p["tutar"]) if p else (tutar_metni(bakiye) if bakiye > 0 else "")),
            dict(anahtar="tarih", etiket="Ödeme tarihi", tur="tarih",
                 deger=format_date(p["tarih"] if p else today_iso())),
            dict(anahtar="yontem", etiket="Ödeme yöntemi", tur="secim", secenekler=ODEME_YONTEMLERI,
                 deger=p["yontem"] if p else "Nakit"),
            dict(anahtar="aciklama", etiket="Açıklama", deger=p["aciklama"] if p else "")],
            uygula, alt_baslik=f"{m['ad']} · kalan bakiye: {format_tl(bakiye)}")
        if f.tamam:
            self.yenile()
        return f.tamam

    # ---- dışa aktarma ----
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

    def csv_musteriler(self):
        self._kaydet(".csv", "musteriler.csv", lambda y: export.export_customers_csv(self.db, y), "CSV")

    def csv_bakiyeler(self):
        self._kaydet(".csv", "bakiyeler.csv", lambda y: export.export_balances_csv(self.db, y), "CSV")

    def csv_geciken(self):
        self._kaydet(".csv", "geciken.csv", lambda y: export.export_overdue_csv(self.db, y, today_iso()), "CSV")

    def pdf_bakiyeler(self):
        self._kaydet(".pdf", "bakiye_raporu.pdf",
                     lambda y: pdf_export.bakiye_raporu_pdf(self.db, today_iso(), y), "PDF")

    def pdf_geciken(self):
        self._kaydet(".pdf", "geciken_odemeler.pdf",
                     lambda y: pdf_export.geciken_raporu_pdf(self.db, today_iso(), y), "PDF")

    def pdf_ekstre(self, cid):
        ad = self.db.get_customer(cid)["ad"].replace(" ", "_")
        self._kaydet(".pdf", f"ekstre_{ad}.pdf",
                     lambda y: pdf_export.musteri_ekstresi_pdf(self.db, cid, today_iso(), y), "PDF")


class DetayPenceresi(tk.Toplevel):
    def __init__(self, app, db, cid):
        super().__init__(app)
        self.app, self.db, self.cid = app, db, cid
        self.configure(bg=ZEMIN)
        self.geometry("920x640")
        self.minsize(820, 560)
        # üst bilgi
        ust = ttk.Frame(self, padding=(24, 18, 24, 6))
        ust.pack(fill="x")
        sol = ttk.Frame(ust)
        sol.pack(side="left")
        self.ad = ttk.Label(sol, style="Baslik.TLabel")
        self.ad.pack(anchor="w")
        self.iletisim = ttk.Label(sol, style="Soluk.TLabel")
        self.iletisim.pack(anchor="w")
        sag = ttk.Frame(ust)
        sag.pack(side="right")
        Dugme(sag, text="PDF Ekstre", command=lambda: app.pdf_ekstre(cid)).pack(side="right")
        Dugme(sag, text="Müşteriyi Düzenle", command=self.duzenle).pack(side="right", padx=(0, 8))
        # kartlar
        kartlar = ttk.Frame(self, padding=(24, 8, 24, 0))
        kartlar.pack(fill="x")
        self.k_borc, self.k_odeme, self.k_kalan = (Kart(kartlar, "Toplam Borç", "#475569"),
                                                   Kart(kartlar, "Ödenen", YESIL), Kart(kartlar, "Kalan Bakiye", KIRMIZI))
        for i, k in enumerate((self.k_borc, self.k_odeme, self.k_kalan)):
            k.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            kartlar.columnconfigure(i, weight=1, uniform="k")
        # sekmeler
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True, padx=24, pady=(14, 20))
        borc = ttk.Frame(self.nb, padding=(0, 10, 0, 0))
        odeme = ttk.Frame(self.nb, padding=(0, 10, 0, 0))
        self.nb.add(borc, text="  Borçlar  ")
        self.nb.add(odeme, text="  Ödemeler  ")
        self.borc_tree = self._sekme(borc, [
            ("tarih", "Tarih", 90, "center"), ("aciklama", "Açıklama", 230, "w"), ("vade", "Vade", 90, "center"),
            ("tutar", "Tutar", 110, "e"), ("kalan", "Kalan", 110, "e"), ("gun", "Durum", 110, "center")],
            [("Borç Ekle", lambda: self.app.borc_formu(cid) and self.yenile(), "Accent.TButton"),
             ("Düzenle", self.borc_duzenle, "TButton"), ("Sil", self.borc_sil, "Tehlike.TButton")])
        self.odeme_tree = self._sekme(odeme, [
            ("tarih", "Tarih", 90, "center"), ("yontem", "Yöntem", 130, "w"), ("aciklama", "Açıklama", 270, "w"),
            ("tutar", "Tutar", 120, "e")],
            [("Ödeme Al", lambda: self.app.odeme_formu(cid) and self.yenile(), "Accent.TButton"),
             ("Düzenle", self.odeme_duzenle, "TButton"), ("Sil", self.odeme_sil, "Tehlike.TButton")])
        self.bind("<Escape>", lambda e: self.destroy())
        self.yenile()
        ortala(self, app)

    def _sekme(self, kap, kolonlar, dugmeler):
        cubuk = ttk.Frame(kap)
        cubuk.pack(fill="x", pady=(0, 8))
        for ad, komut, stil in dugmeler:
            Dugme(cubuk, text=ad, command=komut, style=stil).pack(side="left", padx=(0, 6))
        cerceve, tree = tablo(kap, kolonlar, 10)
        cerceve.pack(fill="both", expand=True)
        return tree

    def yenile(self):
        m = self.db.get_customer(self.cid)
        if m is None:
            self.destroy()
            return
        b = services.customer_balance(self.db, self.cid)
        self.title(f"{m['ad']} - Müşteri Detayı")
        self.ad.config(text=m["ad"])
        self.iletisim.config(text="  ·  ".join(x for x in (m["telefon"], m["eposta"], m["adres"].replace("\n", ", "))
                                               if x) or "İletişim bilgisi girilmemiş")
        self.k_borc.ayarla(format_tl(b["toplam_borc"]))
        self.k_odeme.ayarla(format_tl(b["toplam_odeme"]), renk=YESIL)
        self.k_kalan.ayarla(format_tl(b["bakiye"]), "borcu yok" if b["bakiye"] <= 0 else "", KIRMIZI if b["bakiye"] > 0 else YESIL)
        veri = []
        for d in services.debt_status(self.db, self.cid, today_iso()):
            if d["gecikme_gun"]:
                durum, etiket = f"{d['gecikme_gun']} gün gecikti", ("gec",)
            elif d["kalan"] == 0:
                durum, etiket = "Ödendi", ("temiz",)
            else:
                durum, etiket = "Bekliyor", ()
            veri.append((str(d["id"]), (format_date(d["tarih"]), d["aciklama"], format_date(d["vade"]) or "-",
                                        format_tl(d["tutar"]), format_tl(d["kalan"]), durum), etiket))
        doldur(self.borc_tree, veri)
        doldur(self.odeme_tree, [(str(p["id"]), (format_date(p["tarih"]), p["yontem"], p["aciklama"],
                                                 format_tl(p["tutar"])), ()) for p in self.db.list_payments(self.cid)])
        self.app.yenile()

    def duzenle(self):
        self.app.musteri_duzenle(self.cid)
        self.yenile()

    def _secili(self, tree, ad):
        sec = tree.selection()
        if not sec:
            messagebox.showinfo("Kayıt seçin", f"Lütfen listeden bir {ad} seçin.", parent=self)
            return None
        return int(sec[0])

    def borc_duzenle(self):
        i = self._secili(self.borc_tree, "borç")
        if i is not None and self.app.borc_formu(self.cid, i):
            self.yenile()

    def odeme_duzenle(self):
        i = self._secili(self.odeme_tree, "ödeme")
        if i is not None and self.app.odeme_formu(self.cid, i):
            self.yenile()

    def borc_sil(self):
        i = self._secili(self.borc_tree, "borç")
        if i is not None and messagebox.askyesno("Borcu sil", "Seçili borç silinsin mi?", parent=self):
            self.db.delete_debt(i)
            self.yenile()

    def odeme_sil(self):
        i = self._secili(self.odeme_tree, "ödeme")
        if i is not None and messagebox.askyesno("Ödemeyi sil", "Seçili ödeme silinsin mi?", parent=self):
            self.db.delete_payment(i)
            self.yenile()
