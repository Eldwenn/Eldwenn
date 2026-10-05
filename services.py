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
