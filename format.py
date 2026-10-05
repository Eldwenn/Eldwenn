"""TL ve tarih biçimleme/ayrıştırma yardımcıları."""
from datetime import date, datetime


def format_tl(kurus):
    """1234567 -> '12.345,67 ₺'"""
    negatif = kurus < 0
    kurus = abs(int(kurus))
    lira, kr = divmod(kurus, 100)
    metin = f"{lira:,}".replace(",", ".") + f",{kr:02d} ₺"
    return "-" + metin if negatif else metin


def parse_tl(metin):
    """'1.234,56' veya '1234,5' -> kuruş (int). Geçersizse ValueError."""
    t = metin.replace("₺", "").replace("TL", "").replace(" ", "").strip()
    if not t:
        raise ValueError("Tutar boş olamaz")
    if "," in t:
        t = t.replace(".", "").replace(",", ".")
    elif t.count(".") == 1 and len(t.split(".")[1]) <= 2:
        pass  # 12.5 -> ondalık
    else:
        t = t.replace(".", "")
    try:
        sayi = round(float(t) * 100)
    except ValueError:
        raise ValueError(f"Geçersiz tutar: {metin}") from None
    return sayi


def format_date(iso):
    """'2026-10-05' -> '05.10.2026'"""
    if not iso:
        return ""
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%d.%m.%Y")


def parse_date(metin):
    """'05.10.2026' -> '2026-10-05'. Boşsa None, geçersizse ValueError."""
    metin = metin.strip()
    if not metin:
        return None
    try:
        return datetime.strptime(metin, "%d.%m.%Y").date().isoformat()
    except ValueError:
        raise ValueError(f"Geçersiz tarih (gg.aa.yyyy olmalı): {metin}") from None


def today_iso():
    return date.today().isoformat()
