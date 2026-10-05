# Müşteri Takip ve Ödeme Takibi

Türkçe arayüzlü, TL kullanan masaüstü program (Python, tkinter, SQLite). Ek paket gerekmez.

## Kurulum ve çalıştırma
- Python 3.8+ gerekir. Linux'ta tkinter için: `sudo apt install python3-tk`
- Çalıştırma: `python main.py` (veriler aynı klasörde `musteri_takip.db` dosyasına kaydedilir)

## Özellikler
- **Müşteriler**: ekle, düzenle, sil, ara (çift tıkla detay).
- **Borç/ödeme takibi**: müşteri detayında borç (vade tarihli) ve ödeme ekleme, kalan bakiye.
  Ödemeler en eski vadeli borçtan başlayarak uygulanır.
- **Geciken ödemeler**: vadesi geçen borçlar, gecikme günü ile (kırmızı).
- **Panel**: toplam alacak, bu ay tahsilat, geciken tutar.
- **Raporlar**: CSV dışa aktarma (Excel uyumlu) ve yazdırılabilir müşteri ekstresi (HTML).

## Testler
`python -m unittest discover tests`
