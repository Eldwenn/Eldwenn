"""Paketlenmiş uygulamayı doğrulayan duman testi (CI'da --selftest ile çalışır)."""
import os
import tempfile

import pdf_export
import services
from db import Database
from format import today_iso


def cekirdek(klasor):
    """Veritabanı, hesaplamalar ve PDF üretimi (tkinter gerektirmez)."""
    db = Database(os.path.join(klasor, "test.db"))
    cid = db.add_customer("Test Müşteri Çağlar Şığ", "0532", "a@b.c", "Adres")
    db.add_debt(cid, 100000, today_iso(), "2000-01-01", "Test borcu")
    db.add_payment(cid, 25000, today_iso(), "Nakit")
    ozet = services.summary(db, today_iso())
    assert ozet["geciken_tutar"] == 75000, ozet
    bugun = today_iso()
    pdf_export.musteri_ekstresi_pdf(db, cid, bugun, os.path.join(klasor, "e.pdf"))
    pdf_export.bakiye_raporu_pdf(db, bugun, os.path.join(klasor, "b.pdf"))
    pdf_export.geciken_raporu_pdf(db, bugun, os.path.join(klasor, "g.pdf"))
    for ad in ("e.pdf", "b.pdf", "g.pdf"):
        with open(os.path.join(klasor, ad), "rb") as f:
            assert f.read(5) == b"%PDF-", ad
    return db


def calistir():
    """Tüm yığını dener (arayüz dahil). Başarıda None, hatada ayrıntılı metin döndürür."""
    import traceback
    try:
        with tempfile.TemporaryDirectory() as klasor:
            db = cekirdek(klasor)
            from ui import App
            app = App(db)
            app.update()
            app.destroy()
            db.close()
        return None
    except Exception:
        return traceback.format_exc()
