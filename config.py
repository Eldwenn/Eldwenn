"""Firma bilgileri ve dosya yolları."""
import os
import sys

FIRMA_ADI = "Yıldız Yapı Mimarlık"
UYGULAMA_ADI = "Müşteri Takip"


def resource_path(goreli):
    """Kaynak dosya yolu (PyInstaller paketinde de çalışır)."""
    taban = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(taban, goreli)


def data_dir():
    """Veritabanı klasörü. Windows'ta kurulum klasörü yazılamaz, bu yüzden APPDATA kullanılır."""
    if os.name == "nt":
        klasor = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")),
                              "Yildiz Yapi Mimarlik", "Musteri Takip")
    else:
        klasor = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(klasor, exist_ok=True)
    return klasor
