"""İş mantığı: bakiye, gecikme ve özet hesapları (arayüzden bağımsız)."""
from datetime import date


def _days_between(vade_iso, bugun_iso):
    return (date.fromisoformat(bugun_iso) - date.fromisoformat(vade_iso)).days


def customer_balance(db, cid):
    toplam_borc = sum(d["tutar"] for d in db.list_debts(cid))
    toplam_odeme = sum(p["tutar"] for p in db.list_payments(cid))
    return {"toplam_borc": toplam_borc, "toplam_odeme": toplam_odeme,
            "bakiye": toplam_borc - toplam_odeme}


def debt_status(db, cid, bugun):
    """Her borç için ödenen/kalan tutarı ve gecikme gününü döndürür.

    Ödemeler en eski vadeli borçtan başlayarak uygulanır (vadesizler sona).
    """
    odenecek = sum(p["tutar"] for p in db.list_payments(cid))
    borclar = sorted(db.list_debts(cid), key=lambda d: (d["vade"] is None, d["vade"] or "", d["id"]))
    sonuc = []
    for d in borclar:
        odenen = min(odenecek, d["tutar"])
        odenecek -= odenen
        kalan = d["tutar"] - odenen
        gecikme = 0
        if kalan > 0 and d["vade"] and d["vade"] < bugun:
            gecikme = _days_between(d["vade"], bugun)
        sonuc.append({"id": d["id"], "musteri_id": cid, "tutar": d["tutar"],
                      "odenen": odenen, "kalan": kalan, "tarih": d["tarih"],
                      "vade": d["vade"], "aciklama": d["aciklama"],
                      "gecikme_gun": gecikme})
    return sonuc


def overdue_list(db, bugun):
    """Vadesi geçmiş ve kalanı olan tüm borçlar (en çok geciken önce)."""
    satirlar = []
    for m in db.list_customers():
        for d in debt_status(db, m["id"], bugun):
            if d["gecikme_gun"] > 0:
                satirlar.append({**d, "musteri_ad": m["ad"], "telefon": m["telefon"]})
    satirlar.sort(key=lambda r: -r["gecikme_gun"])
    return satirlar


def balances(db):
    """Tüm müşteriler için bakiye satırları."""
    satirlar = []
    for m in db.list_customers():
        b = customer_balance(db, m["id"])
        satirlar.append({"id": m["id"], "ad": m["ad"], "telefon": m["telefon"], **b})
    return satirlar


def summary(db, bugun):
    """Panel özeti: toplam alacak, ay tahsilatı, geciken tutar ve müşteri sayısı."""
    bakiyeler = balances(db)
    toplam_alacak = sum(b["bakiye"] for b in bakiyeler if b["bakiye"] > 0)
    ay = bugun[:7]
    tahsilat = db.conn.execute(
        "SELECT COALESCE(SUM(tutar),0) FROM odemeler WHERE substr(tarih,1,7)=?", (ay,)).fetchone()[0]
    geciken = overdue_list(db, bugun)
    return {"musteri_sayisi": len(bakiyeler), "toplam_alacak": toplam_alacak,
            "ay_tahsilat": tahsilat,
            "geciken_tutar": sum(r["kalan"] for r in geciken),
            "geciken_musteri": len({r["musteri_id"] for r in geciken})}


def customers_overview(db, bugun, search="", filtre="tumu"):
    """Müşteri listesi satırları: bakiye ve durum (gecikmis / guncel / borcu_yok).

    filtre: tumu | borclu | gecikmis | borcu_yok
    """
    satirlar = []
    for m in db.list_customers(search):
        b = customer_balance(db, m["id"])
        gecikme = max((d["gecikme_gun"] for d in debt_status(db, m["id"], bugun)), default=0)
        durum = "gecikmis" if gecikme > 0 else ("guncel" if b["bakiye"] > 0 else "borcu_yok")
        satirlar.append({"id": m["id"], "ad": m["ad"], "telefon": m["telefon"], "eposta": m["eposta"],
                         "gecikme_gun": gecikme, "durum": durum, **b})
    if filtre == "borclu":
        satirlar = [s for s in satirlar if s["bakiye"] > 0]
    elif filtre in ("gecikmis", "borcu_yok"):
        satirlar = [s for s in satirlar if s["durum"] == filtre]
    return satirlar


def upcoming_list(db, bugun, gun=7):
    """Önümüzdeki `gun` gün içinde vadesi dolacak, kalanı olan borçlar (en yakın önce)."""
    son = date.fromisoformat(bugun).toordinal() + gun
    satirlar = []
    for m in db.list_customers():
        for d in debt_status(db, m["id"], bugun):
            if d["kalan"] > 0 and d["vade"] and bugun <= d["vade"] \
                    and date.fromisoformat(d["vade"]).toordinal() <= son:
                kalan_gun = (date.fromisoformat(d["vade"]) - date.fromisoformat(bugun)).days
                satirlar.append({**d, "musteri_ad": m["ad"], "telefon": m["telefon"], "kalan_gun": kalan_gun})
    satirlar.sort(key=lambda r: (r["vade"], r["id"]))
    return satirlar


# --- Firma / Usta ödemeleri ---
USTA_DURUM_ADI = {"odenmedi": "Ödenmedi", "kismi": "Kısmen Ödendi", "tamam": "Tamamen Ödendi"}


def usta_durum(toplam, odenen):
    """odenmedi | kismi | tamam"""
    if odenen <= 0:
        return "odenmedi"
    return "tamam" if odenen >= toplam else "kismi"


def usta_isler(db, arama="", durum="tumu", baslangic=None, bitis=None):
    """Firma/usta kayıtları (en yeni önce). Tarih = son ödeme tarihi, yoksa kayıt tarihi.

    arama: firma/usta, müşteri veya iş adında geçen metin. durum: tumu|odenmedi|kismi|tamam.
    baslangic/bitis: ISO tarih (dahil), None ise sınırsız.
    """
    aranan = arama.strip().casefold()
    satirlar = []
    for r in db.list_usta_isler():
        tarih = r["son_odeme"] or r["kayit_tarihi"]
        d = usta_durum(r["toplam"], r["odenen"])
        if aranan and not any(aranan in (r[k] or "").casefold() for k in ("usta_ad", "musteri_ad", "is_adi")):
            continue
        if durum != "tumu" and d != durum:
            continue
        if baslangic and tarih < baslangic:
            continue
        if bitis and tarih > bitis:
            continue
        satirlar.append({**dict(r), "kalan": r["toplam"] - r["odenen"], "durum": d, "tarih": tarih})
    return satirlar


def usta_summary(db, bugun):
    """Özet kutuları: toplam borç, toplam ödenen, kalan borç, bu ay yapılan ödeme (tüm kayıtlar üzerinden)."""
    isler = db.list_usta_isler()
    toplam = sum(r["toplam"] for r in isler)
    odenen = sum(r["odenen"] for r in isler)
    ay = db.conn.execute(
        "SELECT COALESCE(SUM(tutar),0) FROM usta_odemeleri WHERE substr(tarih,1,7)=?", (bugun[:7],)).fetchone()[0]
    return {"kayit": len(isler), "toplam": toplam, "odenen": odenen, "kalan": toplam - odenen,
            "ay_odeme": ay, "acik_kayit": sum(1 for r in isler if r["toplam"] > r["odenen"])}


def tarih_araligi(ad, bugun):
    """Filtre adından (baslangic, bitis) ISO tarih çifti. bugun: ISO tarih. 'Tüm tarihler' -> (None, None)."""
    from datetime import timedelta
    b = date.fromisoformat(bugun)
    if ad == "Bugün":
        return bugun, bugun
    if ad == "Bu hafta":
        pazartesi = b - timedelta(days=b.weekday())
        return pazartesi.isoformat(), (pazartesi + timedelta(days=6)).isoformat()
    if ad == "Bu ay":
        return b.replace(day=1).isoformat(), bugun[:7] + "-31"
    if ad == "Geçen ay":
        onceki_son = b.replace(day=1) - timedelta(days=1)
        return onceki_son.replace(day=1).isoformat(), onceki_son.isoformat()
    if ad == "Son 30 gün":
        return (b - timedelta(days=30)).isoformat(), bugun
    if ad == "Bu yıl":
        return f"{b.year}-01-01", f"{b.year}-12-31"
    return None, None
