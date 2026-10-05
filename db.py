"""SQLite veri katmanı."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS musteriler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad TEXT NOT NULL,
    telefon TEXT DEFAULT '',
    eposta TEXT DEFAULT '',
    adres TEXT DEFAULT '',
    notlar TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS borclar (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    musteri_id INTEGER NOT NULL REFERENCES musteriler(id) ON DELETE CASCADE,
    tutar INTEGER NOT NULL CHECK (tutar > 0),
    aciklama TEXT DEFAULT '',
    tarih TEXT NOT NULL,
    vade TEXT
);
CREATE TABLE IF NOT EXISTS odemeler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    musteri_id INTEGER NOT NULL REFERENCES musteriler(id) ON DELETE CASCADE,
    tutar INTEGER NOT NULL CHECK (tutar > 0),
    tarih TEXT NOT NULL,
    yontem TEXT DEFAULT '',
    aciklama TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS usta_isler (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usta_ad TEXT NOT NULL,
    is_adi TEXT NOT NULL,
    musteri_id INTEGER REFERENCES musteriler(id) ON DELETE SET NULL,
    musteri_ad TEXT DEFAULT '',
    adres TEXT DEFAULT '',
    aciklama TEXT DEFAULT '',
    toplam INTEGER NOT NULL CHECK (toplam > 0),
    notlar TEXT DEFAULT '',
    tarih TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS usta_odemeleri (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    is_id INTEGER NOT NULL REFERENCES usta_isler(id) ON DELETE CASCADE,
    tutar INTEGER NOT NULL CHECK (tutar > 0),
    tarih TEXT NOT NULL,
    tur TEXT DEFAULT 'Nakit',
    notlar TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_usta_odemeleri_is ON usta_odemeleri(is_id);
"""

ODEME_TURLERI = ("Nakit", "Havale", "EFT", "Diğer")


class Database:
    def __init__(self, path="musteri_takip.db"):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(SCHEMA)

    def close(self):
        self.conn.close()

    # --- müşteriler ---
    def add_customer(self, ad, telefon="", eposta="", adres="", notlar=""):
        if not ad.strip():
            raise ValueError("Müşteri adı boş olamaz")
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO musteriler (ad, telefon, eposta, adres, notlar) VALUES (?,?,?,?,?)",
                (ad.strip(), telefon.strip(), eposta.strip(), adres.strip(), notlar.strip()))
        return cur.lastrowid

    def update_customer(self, cid, ad, telefon="", eposta="", adres="", notlar=""):
        if not ad.strip():
            raise ValueError("Müşteri adı boş olamaz")
        with self.conn:
            self.conn.execute(
                "UPDATE musteriler SET ad=?, telefon=?, eposta=?, adres=?, notlar=? WHERE id=?",
                (ad.strip(), telefon.strip(), eposta.strip(), adres.strip(), notlar.strip(), cid))

    def delete_customer(self, cid):
        with self.conn:
            self.conn.execute("DELETE FROM musteriler WHERE id=?", (cid,))

    def get_customer(self, cid):
        return self.conn.execute("SELECT * FROM musteriler WHERE id=?", (cid,)).fetchone()

    def list_customers(self, search=""):
        s = f"%{search.strip()}%"
        return self.conn.execute(
            "SELECT * FROM musteriler WHERE ad LIKE ? OR telefon LIKE ? OR eposta LIKE ? "
            "ORDER BY ad COLLATE NOCASE", (s, s, s)).fetchall()

    # --- borçlar ---
    def add_debt(self, musteri_id, tutar, tarih, vade=None, aciklama=""):
        if tutar <= 0:
            raise ValueError("Borç tutarı sıfırdan büyük olmalı")
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO borclar (musteri_id, tutar, aciklama, tarih, vade) VALUES (?,?,?,?,?)",
                (musteri_id, tutar, aciklama.strip(), tarih, vade))
        return cur.lastrowid

    def get_debt(self, did):
        return self.conn.execute("SELECT * FROM borclar WHERE id=?", (did,)).fetchone()

    def update_debt(self, did, tutar, tarih, vade=None, aciklama=""):
        if tutar <= 0:
            raise ValueError("Borç tutarı sıfırdan büyük olmalı")
        with self.conn:
            self.conn.execute("UPDATE borclar SET tutar=?, tarih=?, vade=?, aciklama=? WHERE id=?",
                              (tutar, tarih, vade, aciklama.strip(), did))

    def delete_debt(self, did):
        with self.conn:
            self.conn.execute("DELETE FROM borclar WHERE id=?", (did,))

    def list_debts(self, musteri_id):
        return self.conn.execute(
            "SELECT * FROM borclar WHERE musteri_id=? ORDER BY COALESCE(vade, tarih), id",
            (musteri_id,)).fetchall()

    # --- ödemeler ---
    def add_payment(self, musteri_id, tutar, tarih, yontem="", aciklama=""):
        if tutar <= 0:
            raise ValueError("Ödeme tutarı sıfırdan büyük olmalı")
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO odemeler (musteri_id, tutar, tarih, yontem, aciklama) VALUES (?,?,?,?,?)",
                (musteri_id, tutar, tarih, yontem.strip(), aciklama.strip()))
        return cur.lastrowid

    def get_payment(self, pid):
        return self.conn.execute("SELECT * FROM odemeler WHERE id=?", (pid,)).fetchone()

    def update_payment(self, pid, tutar, tarih, yontem="", aciklama=""):
        if tutar <= 0:
            raise ValueError("Ödeme tutarı sıfırdan büyük olmalı")
        with self.conn:
            self.conn.execute("UPDATE odemeler SET tutar=?, tarih=?, yontem=?, aciklama=? WHERE id=?",
                              (tutar, tarih, yontem.strip(), aciklama.strip(), pid))

    def recent_payments(self, limit=8):
        return self.conn.execute(
            "SELECT o.*, m.ad AS musteri_ad FROM odemeler o JOIN musteriler m ON m.id=o.musteri_id "
            "ORDER BY o.tarih DESC, o.id DESC LIMIT ?", (limit,)).fetchall()

    def delete_payment(self, pid):
        with self.conn:
            self.conn.execute("DELETE FROM odemeler WHERE id=?", (pid,))

    def list_payments(self, musteri_id):
        return self.conn.execute(
            "SELECT * FROM odemeler WHERE musteri_id=? ORDER BY tarih DESC, id DESC",
            (musteri_id,)).fetchall()

    # --- firma / usta ödemeleri ---
    _USTA_SELECT = (
        "SELECT i.id, i.usta_ad, i.is_adi, i.musteri_id, "
        "COALESCE(m.ad, i.musteri_ad) AS musteri_ad, i.adres, i.aciklama, i.toplam, i.notlar, "
        "i.tarih AS kayit_tarihi, "
        "COALESCE((SELECT SUM(tutar) FROM usta_odemeleri o WHERE o.is_id = i.id), 0) AS odenen, "
        "(SELECT MAX(tarih) FROM usta_odemeleri o WHERE o.is_id = i.id) AS son_odeme "
        "FROM usta_isler i LEFT JOIN musteriler m ON m.id = i.musteri_id ")

    @staticmethod
    def _usta_dogrula(usta_ad, is_adi, toplam):
        if not usta_ad.strip():
            raise ValueError("Firma / usta adı boş olamaz")
        if not is_adi.strip():
            raise ValueError("İş / proje adı boş olamaz")
        if toplam <= 0:
            raise ValueError("Toplam anlaşılan tutar sıfırdan büyük olmalı")

    def add_usta_is(self, usta_ad, is_adi, toplam, tarih, musteri_id=None, musteri_ad="",
                    adres="", aciklama="", notlar=""):
        self._usta_dogrula(usta_ad, is_adi, toplam)
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO usta_isler (usta_ad, is_adi, musteri_id, musteri_ad, adres, aciklama, "
                "toplam, notlar, tarih) VALUES (?,?,?,?,?,?,?,?,?)",
                (usta_ad.strip(), is_adi.strip(), musteri_id, musteri_ad.strip(), adres.strip(),
                 aciklama.strip(), toplam, notlar.strip(), tarih))
        return cur.lastrowid

    def update_usta_is(self, iid, usta_ad, is_adi, toplam, musteri_id=None, musteri_ad="",
                       adres="", aciklama="", notlar=""):
        self._usta_dogrula(usta_ad, is_adi, toplam)
        odenen = self.usta_odenen(iid)
        if toplam < odenen:
            raise ValueError("Toplam tutar, şimdiye kadar ödenen tutardan küçük olamaz")
        with self.conn:
            self.conn.execute(
                "UPDATE usta_isler SET usta_ad=?, is_adi=?, musteri_id=?, musteri_ad=?, adres=?, "
                "aciklama=?, toplam=?, notlar=? WHERE id=?",
                (usta_ad.strip(), is_adi.strip(), musteri_id, musteri_ad.strip(), adres.strip(),
                 aciklama.strip(), toplam, notlar.strip(), iid))

    def delete_usta_is(self, iid):
        with self.conn:
            self.conn.execute("DELETE FROM usta_isler WHERE id=?", (iid,))

    def get_usta_is(self, iid):
        return self.conn.execute(self._USTA_SELECT + "WHERE i.id=?", (iid,)).fetchone()

    def list_usta_isler(self):
        return self.conn.execute(self._USTA_SELECT + "ORDER BY i.id DESC").fetchall()

    def usta_adlari(self):
        return [r[0] for r in self.conn.execute(
            "SELECT DISTINCT usta_ad FROM usta_isler ORDER BY usta_ad COLLATE NOCASE")]

    def usta_odenen(self, iid):
        return self.conn.execute(
            "SELECT COALESCE(SUM(tutar),0) FROM usta_odemeleri WHERE is_id=?", (iid,)).fetchone()[0]

    def _usta_odeme_dogrula(self, iid, tutar, tur, haric_odeme=None):
        if tutar <= 0:
            raise ValueError("Ödeme tutarı sıfırdan büyük olmalı")
        if tur not in ODEME_TURLERI:
            raise ValueError("Ödeme türü Nakit, Havale, EFT veya Diğer olmalı")
        is_ = self.conn.execute("SELECT toplam FROM usta_isler WHERE id=?", (iid,)).fetchone()
        if is_ is None:
            raise ValueError("Kayıt bulunamadı")
        odenen = self.usta_odenen(iid)
        if haric_odeme is not None:
            odenen -= self.get_usta_odeme(haric_odeme)["tutar"]
        kalan = is_["toplam"] - odenen
        if tutar > kalan:
            from format import format_tl
            raise ValueError(f"Ödeme tutarı kalan borçtan ({format_tl(kalan)}) fazla olamaz")

    def add_usta_odeme(self, iid, tutar, tarih, tur="Nakit", notlar=""):
        self._usta_odeme_dogrula(iid, tutar, tur)
        with self.conn:
            cur = self.conn.execute(
                "INSERT INTO usta_odemeleri (is_id, tutar, tarih, tur, notlar) VALUES (?,?,?,?,?)",
                (iid, tutar, tarih, tur, notlar.strip()))
        return cur.lastrowid

    def update_usta_odeme(self, oid, tutar, tarih, tur="Nakit", notlar=""):
        eski = self.get_usta_odeme(oid)
        if eski is None:
            raise ValueError("Ödeme kaydı bulunamadı")
        self._usta_odeme_dogrula(eski["is_id"], tutar, tur, haric_odeme=oid)
        with self.conn:
            self.conn.execute("UPDATE usta_odemeleri SET tutar=?, tarih=?, tur=?, notlar=? WHERE id=?",
                              (tutar, tarih, tur, notlar.strip(), oid))

    def delete_usta_odeme(self, oid):
        with self.conn:
            self.conn.execute("DELETE FROM usta_odemeleri WHERE id=?", (oid,))

    def get_usta_odeme(self, oid):
        return self.conn.execute("SELECT * FROM usta_odemeleri WHERE id=?", (oid,)).fetchone()

    def list_usta_odemeleri(self, iid):
        return self.conn.execute(
            "SELECT * FROM usta_odemeleri WHERE is_id=? ORDER BY tarih, id", (iid,)).fetchall()
