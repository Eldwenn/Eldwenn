"""Müşteri takip ve ödeme takibi programı. Çalıştırma: python main.py"""
import os
import sys
import traceback
from datetime import datetime

from config import data_dir


def hata_kaydet(metin):
    """Hatayı hata.log dosyasına ekler; kaydedilen yolu döndürür."""
    yol = os.path.join(data_dir(), "hata.log")
    try:
        with open(yol, "a", encoding="utf-8") as f:
            f.write(f"--- {datetime.now():%d.%m.%Y %H:%M:%S} ---\n{metin}\n")
    except OSError:
        pass
    return yol


def hata_bildir(tip, deger, tb):
    metin = "".join(traceback.format_exception(tip, deger, tb))
    yol = hata_kaydet(metin)
    try:
        from tkinter import messagebox
        messagebox.showerror("Beklenmeyen hata", f"{deger}\n\nAyrıntılar şu dosyaya kaydedildi:\n{yol}")
    except Exception:
        pass


def selftest():
    import selftest as st
    sonuc = st.calistir()
    cikti = sys.argv[sys.argv.index("--selftest") + 1:][:1]
    yol = cikti[0] if cikti else os.path.join(data_dir(), "selftest.txt")
    with open(yol, "w", encoding="utf-8") as f:
        f.write("OK\n" if sonuc is None else sonuc)
    return 0 if sonuc is None else 1


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    sys.excepthook = hata_bildir
    from db import Database
    from ui import App
    app = App(Database(os.path.join(data_dir(), "musteri_takip.db")))
    app.report_callback_exception = hata_bildir
    app.mainloop()


if __name__ == "__main__":
    main()
