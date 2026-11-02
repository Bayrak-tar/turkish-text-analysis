# Ad Soyad : Bayram Bayraktar
# Tarih    : 24.09.2026
# Ayrilmis metinlerle siniflandirma olcumu; uygulama veritabanini acmaz.

import argparse
import json
from collections import Counter
from pathlib import Path

from dil_isleme import OzellikCikarici
from siniflandirma import KonuAgaci, KonuSiniflandirici

KOK = Path(__file__).resolve().parent


def olc(model, ornekler):
    dogru = tam_alt = tp = fp = fn = 0
    matris = Counter()
    farklar = []
    for o in ornekler:
        s = model.siniflandir(o["metin"])
        beklenen = set(o["alt_konular"])
        bulunan = {a.tam_ad for a, _ in s.alt_konular}
        dogru += s.genel_konu == o["genel_konu"]
        tam_alt += beklenen == bulunan
        tp += len(beklenen & bulunan)
        fp += len(bulunan - beklenen)
        fn += len(beklenen - bulunan)
        matris[(o["genel_konu"] or "Belirsiz", s.genel_konu or "Belirsiz")] += 1
        if beklenen != bulunan or s.genel_konu != o["genel_konu"]:
            farklar.append({"metin": o["metin"], "beklenen_genel": o["genel_konu"],
                           "bulunan_genel": s.genel_konu,
                           "eksik": sorted(beklenen - bulunan), "fazla": sorted(bulunan - beklenen)})
    kesinlik = tp / (tp + fp) if tp + fp else 0.0
    duyarlilik = tp / (tp + fn) if tp + fn else 0.0
    return {"ornek_sayisi": len(ornekler), "genel_dogruluk": dogru / len(ornekler),
            "alt_tam_eslesme": tam_alt / len(ornekler), "alt_kesinlik_micro": kesinlik,
            "alt_duyarlilik_micro": duyarlilik,
            "alt_f1_micro": 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0,
            "tp": tp, "fp": fp, "fn": fn,
            "karisiklik_matrisi": [{"gercek": g, "tahmin": t, "adet": n}
                                  for (g, t), n in sorted(matris.items())], "farklar": farklar}


def raporla(sonuc):
    satirlar = ["# Sınıflandırma değerlendirmesi", "",
                "Eğitim: 18, değerlendirme: 20 elle yazılmış ve elle etiketlenmiş örnek metin.",
                "Bunlar dışarıdan toplanmış, bağımsız uzmanlarca doğrulanmış bir veri kümesi değildir.",
                "Eğitim ile değerlendirme metinleri ayrıdır; değerlendirme sırasında öğrenme ve internet araması kapalıdır.",
                "Küçük küme yalnızca üç genel konuyu, belirsiz metinleri ve seçilmiş alt konuları kapsar.",
                "Sonuçlar 42 genel konu / 1220 alt konunun tamamındaki başarıyı göstermez.",
                "Alt konu etiketleri metnin hedef konularıdır; ek çıktılar yanlış pozitif olarak sayılır.", "",
                "| Model | Genel doğruluk | Alt kesinlik | Alt duyarlılık | Alt F1 | Alt tam eşleşme |",
                "|---|---:|---:|---:|---:|---:|"]
    for ad, m in sonuc.items():
        satirlar.append("| " + ad + " | " + " | ".join(f"%{m[k]*100:.1f}" for k in
                         ["genel_dogruluk", "alt_kesinlik_micro", "alt_duyarlilik_micro", "alt_f1_micro", "alt_tam_eslesme"]) + " |")
    m = sonuc["Sözlük + etiketli metin"]
    satirlar += ["", "Kesinlik, bulunan alt konuların ne kadarının etikette bulunduğunu; duyarlılık, beklenenlerin ne kadarının yakalandığını ölçer. F1 ikisini birlikte değerlendirir. Alt konu ölçümleri mikro ortalamadır.",
                 "", "## Genel konu karışıklık matrisi", ""]
    etiketler = sorted({r[k] for r in m["karisiklik_matrisi"] for k in ("gercek", "tahmin")})
    hucreler = {(r["gercek"], r["tahmin"]): r["adet"] for r in m["karisiklik_matrisi"]}
    satirlar += ["| Gerçek / Tahmin | " + " | ".join(etiketler) + " |", "|---|" + "---:|" * len(etiketler)]
    for g in etiketler:
        satirlar.append("| " + g + " | " + " | ".join(str(hucreler.get((g, t), 0)) for t in etiketler) + " |")
    satirlar += ["", "## Etiketten farklı sonuçlar", ""]
    for f in m["farklar"]:
        satirlar += ["- " + f["metin"], "  Eksik: " + (", ".join(f["eksik"]) or "yok") +
                     "; fazla: " + (", ".join(f["fazla"]) or "yok") + "."]
    satirlar += ["", "Model güveni, ölçülmüş doğruluk veya kalibre edilmiş başarı olasılığı değildir.",
                 "Daha geniş, bağımsız etiketli Türkçe veriyle ölçüm gerekir. Bu rapor internet kaynaklarının canlı erişimini ölçmez.", ""]
    return "\n".join(satirlar)


def main():
    parser = argparse.ArgumentParser(description="Ayrılmış veriyle başarı ölçümü")
    parser.add_argument("--rapor", type=Path, help="Markdown raporunu bu yola yaz")
    args = parser.parse_args()
    ornekler = json.loads((KOK / "veri/degerlendirme.json").read_text(encoding="utf-8"))
    egitim = json.loads((KOK / "veri/egitim.json").read_text(encoding="utf-8"))
    if {o["metin"].strip().casefold() for o in egitim} & {o["metin"].strip().casefold() for o in ornekler}:
        raise ValueError("Egitim ve degerlendirme metinleri cakismamali")
    cikarici = OzellikCikarici()
    agac = KonuAgaci().dosyadan_yukle(KOK / "veri/konular.txt", cikarici)
    model = KonuSiniflandirici(agac, cikarici)
    model.egit()
    sonuc = {"Sözlük": olc(model, ornekler)}
    model.orneklerden_egit(KOK / "veri/egitim.json")
    sonuc["Sözlük + etiketli metin"] = olc(model, ornekler)
    print(json.dumps(sonuc, ensure_ascii=False, indent=2))
    if args.rapor:
        args.rapor.write_text(raporla(sonuc), encoding="utf-8")


if __name__ == "__main__":
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
