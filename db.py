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
"""


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

    def delete_payment(self, pid):
        with self.conn:
            self.conn.execute("DELETE FROM odemeler WHERE id=?", (pid,))

    def list_payments(self, musteri_id):
        return self.conn.execute(
            "SELECT * FROM odemeler WHERE musteri_id=? ORDER BY tarih DESC, id DESC",
            (musteri_id,)).fetchall()
