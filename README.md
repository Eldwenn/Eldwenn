# Yıldız Yapı Mimarlık - Müşteri Takip ve Ödeme Takibi

Türkçe arayüzlü, TL kullanan masaüstü program (Python, tkinter, SQLite). Raporlar firma logolu PDF olarak alınır.

## Kurulum dosyası (setup.exe)
**Seçenek 1 - GitHub'dan hazır indir:** Depoda *Actions → Windows kurulum dosyasi* çalışmasının sonunda
`YildizYapi_MusteriTakip_Kurulum` paketi (içinde `.exe`) oluşur; indirip çift tıklayın. Python kurmaya gerek yoktur.

**Seçenek 2 - Windows'ta kendiniz üretin:** Python 3.8 (Windows 7 uyumu için, 32 bit önerilir) ve [Inno Setup 6](https://jrsoftware.org/isdl.php)
kurun, sonra `build_windows.bat` çalıştırın. Çıktı: `installer\Output\YildizYapi_MusteriTakip_Kurulum.exe`

Veriler kurulum klasörüne değil `%APPDATA%\Yildiz Yapi Mimarlik\Musteri Takip\musteri_takip.db` dosyasına
kaydedilir; program güncellenince veya kaldırılınca silinmez. Yedek için bu dosyayı kopyalayın.

## Windows uyumluluğu
Kurulum dosyası Python 3.8 (32 bit) ile üretilir: **Windows 7 SP1, 8, 10 ve 11**'de, 32 ve 64 bit sistemlerde çalışır.
Windows 7'de Service Pack 1 ve güncel Windows güncellemeleri (KB2999226 veya Visual C++ 2015-2019 x86
çalışma zamanı) kurulu olmalıdır. Beklenmeyen bir hata olursa program bir uyarı gösterir ve ayrıntıyı
`%APPDATA%\Yildiz Yapi Mimarlik\Musteri Takip\hata.log` dosyasına yazar.

## Kurulumsuz çalıştırma
`pip install -r requirements.txt` ve `python main.py` (Linux'ta `sudo apt install python3-tk`)

## Özellikler
- **Müşteriler**: ekle, düzenle, sil, ara (çift tıkla detay).
- **Borç/ödeme takibi**: detayda vade tarihli borç ve ödeme; kalan bakiye. Ödemeler en eski vadeli borçtan düşülür.
- **Geciken ödemeler**: vadesi geçenler, gecikme günüyle (kırmızı).
- **Panel**: toplam alacak, bu ay tahsilat, geciken tutar.
- **PDF**: müşteri ekstresi, bakiye raporu, geciken ödemeler raporu (logo + firma adı üstbilgisi).
- **CSV**: müşteri, bakiye, geciken listesi (Excel uyumlu).

## Testler
`python -m unittest discover tests`
