# Ad Soyad : Bayram Bayraktar
# Tarih    : 24.09.2026
#
# Turkce metin konu siniflandirici.
# Calistirma: python proje.py
#
# Kullanicinin girdigi her metnin genel konusu ve alt konulari bulunur, veritabanina
# kaydedilir. Tum metinlerden sohbetin konusu cikarilir ve bu konu internette aranir.

import argparse
import bdb
import os
import sqlite3
import sys

from arama import BilgiToplayici, DuckDuckGoArama, VikipediArama
from dil_isleme import DURAK_KELIMELER, ORTAK_KOKLER, OzellikCikarici
from siniflandirma import KonuAgaci, KonuSiniflandirici
from sohbet import SohbetBaglami, SorguOlusturucu
from veritabani import Veritabani

KLASOR = os.path.dirname(os.path.abspath(__file__))
KONU_DOSYASI = os.path.join(KLASOR, "veri", "konular.txt")
EGITIM_DOSYASI = os.path.join(KLASOR, "veri", "egitim.json")


class Uygulama:
    """Siniflandirma, sohbet takibi, arama ve kayit adimlarini bir araya getirir."""

    def __init__(self, veritabani_yolu, cevrimici=True, sonuc_sayisi=3, adim_adim=False):
        self.adim_adim = adim_adim
        self.cikarici = OzellikCikarici()
        self.veritabani = Veritabani(veritabani_yolu)
        if not self.veritabani.konu_agaci_var():
            ilk_agac = KonuAgaci().dosyadan_yukle(KONU_DOSYASI, self.cikarici)
            self.veritabani.konu_agaci_kaydet(ilk_agac)
        self.sohbet = SohbetBaglami()
        self._siniflandiriciyi_yenile()
        self.bilgi = BilgiToplayici([VikipediArama(), DuckDuckGoArama()], sonuc_sayisi) if cevrimici else None
        self._son_sorgu = None
        self.veritabani.oturum_baslat()

    def _siniflandiriciyi_yenile(self):
        self.cikarici = OzellikCikarici()
        self.agac = KonuAgaci().veritabanindan_yukle(self.veritabani, self.cikarici)
        self.siniflandirici = KonuSiniflandirici(self.agac, self.cikarici)
        self.siniflandirici.egit()
        self.siniflandirici.orneklerden_egit(EGITIM_DOSYASI)
        for kelime, konu, alt in self.veritabani.onayli_kelimeler():
            if konu in self.agac.genel_konular and (not alt or any(a.ad == alt for a in self.agac.genel_konular[konu].alt_konular)):
                self.siniflandirici.kelime_ogret(kelime, konu, alt)
        self.sorgu_olusturucu = SorguOlusturucu(self.agac)
        self.siniflandirici.adim_adim = self.adim_adim

    def konu_ekle(self, ad, terimler):
        anahtarlar = self._terimleri_normalize_et(terimler)
        self.veritabani.konu_ekle(ad, anahtarlar)
        self._siniflandiriciyi_yenile()

    def alt_konu_ekle(self, genel, alt, terimler):
        anahtarlar = self._terimleri_normalize_et(terimler)
        self.veritabani.alt_konu_ekle(genel, alt, anahtarlar)
        self._siniflandiriciyi_yenile()

    def anahtar_ekle(self, genel, alt, terimler):
        anahtarlar = self._terimleri_normalize_et(terimler)
        sayi = self.veritabani.anahtar_ekle(genel, alt, anahtarlar)
        self._siniflandiriciyi_yenile()
        return sayi

    def anahtar_sil(self, genel, alt, terimler):
        anahtarlar = self._terimleri_normalize_et(terimler)
        sayi = self.veritabani.anahtar_sil(genel, alt, anahtarlar)
        self._siniflandiriciyi_yenile()
        return sayi

    def alt_konu_sil(self, genel, alt):
        self.veritabani.alt_konu_sil(genel, alt)
        self._siniflandiriciyi_yenile()

    def konu_sil(self, genel):
        self.veritabani.konu_sil(genel)
        self._siniflandiriciyi_yenile()

    def _terimleri_normalize_et(self, terimler):
        anahtarlar = [self.cikarici.sozluge_ekle(t.strip()) for t in terimler.split(",") if t.strip()]
        anahtarlar = list(dict.fromkeys(k for k in anahtarlar if k))
        if not anahtarlar:
            raise ValueError("En az bir anlamli anahtar kelime giriniz")
        return anahtarlar

    def isle(self, metin):
        """
        Bir metni tum adimlardan gecirir.
        (siniflandirma sonucu, arama sorgusu, arama sonuclari, ogrenilen kelimeler) dondurur.
        Basarili sorgu tekrarlanmaz; hatali veya bos arama yeniden denenir.
        """
        if self.adim_adim:
            print("\n[1] Metin alındı. İncele: metin. Sıradaki işlem: sınıflandırma.")
            breakpoint()
        sonuc = self.siniflandirici.siniflandir(metin)
        if self.adim_adim:
            print("\n[6] Sınıflandırma tamamlandı. İncele: sonuc. Sıradaki işlem: sohbet bağlamı.")
            breakpoint()
        self.sohbet.ekle(sonuc)
        if self.adim_adim:
            print("\n[7] Sohbet güncellendi. İncele: self.sohbet.genel_agirlik. Sıradaki işlem: metin kaydı.")
            breakpoint()
        metin_id = self.veritabani.metin_kaydet(sonuc, self.sohbet.genel_konu())
        if self.adim_adim:
            print("\n[8] Metin ve konuları kaydedildi. İncele: metin_id. Sıradaki işlem: öğrenme adayları.")
            breakpoint()

        yeni_kelimeler = self.siniflandirici.ogren(sonuc, self.cikarici.kok, ORTAK_KOKLER | DURAK_KELIMELER)
        if self.adim_adim:
            print("\n[9] Öğrenme adayları hazır. İncele: yeni_kelimeler. Sıradaki işlem: sorgu oluşturma.")
            breakpoint()

        sorgu, sonuclar = None, []
        yeni_sorgu = self.sorgu_olusturucu.olustur(self.sohbet)
        if self.adim_adim:
            print("\n[10] Sorgu hazır. İncele: yeni_sorgu, self._son_sorgu. Sıradaki işlem: gerekiyorsa arama.")
            breakpoint()
        if yeni_sorgu and yeni_sorgu != self._son_sorgu:
            # sohbetin konusu degismediyse ayni sorgu tekrar aranmiyor
            sorgu = yeni_sorgu
            if self.cevrimici:
                sonuclar = self.bilgi.topla(sorgu)
                if self.adim_adim:
                    print("\n[11] Arama tamamlandı. İncele: sonuclar, self.arama_hatalari. Sıradaki işlem: arama kaydı.")
                    breakpoint()
                self.veritabani.arama_kaydet(metin_id, sorgu, sonuclar)
                self._son_sorgu = sorgu if sonuclar and not self.bilgi.hatalar else None
            else:
                self._son_sorgu = sorgu
        if self.adim_adim:
            print("\n[12] Metin işleme bitti. İncele: sonuc, sorgu, sonuclar. Sıradaki işlem: konsola yazdırma.")
            breakpoint()
        return sonuc, sorgu, sonuclar, yeni_kelimeler

    def kelime_onayla(self, kelime, genel_konu, alt_konu=""):
        self.siniflandirici.kelime_ogret(kelime, genel_konu, alt_konu)
        self.veritabani.onayli_kelime_kaydet(kelime, genel_konu, alt_konu)
        self.sorgu_olusturucu = SorguOlusturucu(self.agac)

    @property
    def cevrimici(self):
        return self.bilgi is not None

    @property
    def arama_hatalari(self):
        return self.bilgi.hatalar if self.bilgi else []

    def kapat(self):
        self.veritabani.oturum_bitir(self.sohbet.genel_konu())
        self.veritabani.kapat()


class KonsolArayuzu:
    CIKIS_KOMUTLARI = {"çıkış", "cikis", "çık", "cik", "q", "exit", "quit"}
    OZET_UZUNLUGU = 300
    DUSUK_GUVEN = 0.3

    def __init__(self, uygulama):
        self.uygulama = uygulama

    def calistir(self):
        agac = self.uygulama.agac
        print(f"{len(agac.genel_konular)} genel konu, {len(agac.alt_konular)} alt konu yüklendi.")
        for uyari in agac.uyarilar:
            print(f"Uyarı: {uyari}")
        print("Bir metin yazın. Çıkmak için 'çıkış' yazın.\n")
        print("Konu yönetimi: /konular, /konu-ekle, /alt-ekle, /anahtar-ekle, /anahtar-sil, /alt-sil, /konu-sil")
        print("Kelime öğretme: /ogret terim | Genel konu | Alt konu (alt konu isteğe bağlı)\n")
        try:
            while True:
                try:
                    metin = input("Metin Giriniz : ").strip()
                except EOFError:
                    break
                if not metin:
                    continue
                if metin.lower() in self.CIKIS_KOMUTLARI:
                    break
                try:
                    if metin.startswith(("/konular", "/konu-ekle", "/alt-ekle", "/anahtar-ekle",
                                         "/anahtar-sil", "/alt-sil", "/konu-sil")):
                        self._konu_komutunu_isle(metin)
                        continue
                    if metin.startswith("/ogret "):
                        alanlar = [a.strip() for a in metin[7:].split("|")]
                        if len(alanlar) not in (2, 3):
                            raise ValueError("/ogret terim | Genel konu | Alt konu")
                        self.uygulama.kelime_onayla(*alanlar)
                        print("Onaylanan terim öğrenildi ve kaydedildi.\n")
                        continue
                    self._goster(*self.uygulama.isle(metin))
                    if self.uygulama.adim_adim:
                        print("\n[13] Çıktı gösterildi. Sıradaki işlem: yeni metin bekleme.")
                        breakpoint()
                except bdb.BdbQuit:
                    break
                except Exception as hata:      # bir metin hata verse de sohbet kesilmesin
                    print(f"Bu metin işlenemedi ({type(hata).__name__}: {hata}). Devam edebilirsiniz.\n")
        except KeyboardInterrupt:
            print()
        finally:
            konu = self.uygulama.sohbet.genel_konu()
            self.uygulama.kapat()
            if konu:
                print(f"Sohbetin genel konusu: {konu}")
            print("Kayıtlar veritabanına yazıldı.")

    def _konu_komutunu_isle(self, metin):
        komut, _, arguman = metin.partition(" ")
        alanlar = [a.strip() for a in arguman.split("|")]
        u = self.uygulama
        if komut == "/konular":
            if arguman.strip():
                raise ValueError("Kullanım: /konular")
            for genel in u.agac.genel_konular.values():
                print(f"- {genel.ad}")
                for alt in genel.alt_konular:
                    print(f"    - {alt.ad}")
            print()
        elif komut == "/konu-ekle" and len(alanlar) == 2:
            u.konu_ekle(alanlar[0], alanlar[1])
            print(f"'{alanlar[0]}' konusu eklendi ve sınıflandırıcı yenilendi.\n")
        elif komut == "/alt-ekle" and len(alanlar) == 3:
            u.alt_konu_ekle(*alanlar)
            print(f"'{alanlar[0]} > {alanlar[1]}' alt konusu eklendi ve sınıflandırıcı yenilendi.\n")
        elif komut == "/anahtar-ekle" and len(alanlar) == 3:
            sayi = u.anahtar_ekle(*alanlar)
            print(f"{sayi} anahtar kelime eklendi; sınıflandırıcı yenilendi.\n")
        elif komut == "/anahtar-sil" and len(alanlar) == 3:
            sayi = u.anahtar_sil(*alanlar)
            print(f"{sayi} anahtar kelime silindi; sınıflandırıcı yenilendi.\n")
        elif komut == "/alt-sil" and len(alanlar) == 2:
            u.alt_konu_sil(*alanlar)
            print("Alt konu silindi ve sınıflandırıcı yenilendi.\n")
        elif komut == "/konu-sil" and len(alanlar) == 1:
            u.konu_sil(alanlar[0])
            print("Genel konu ve alt konuları silindi; sınıflandırıcı yenilendi.\n")
        else:
            raise ValueError(
                "Kullanımlar: /konular | /konu-ekle ad | kelimeler | "
                "/alt-ekle genel | alt | kelimeler | /anahtar-ekle genel | alt (boş olabilir) | kelimeler | "
                "/anahtar-sil genel | alt (boş olabilir) | kelimeler | /alt-sil genel | alt | /konu-sil genel")

    def _goster(self, sonuc, sorgu, sonuclar, yeni_kelimeler):
        if sonuc.belirsiz:
            print("Metnin konusu anlaşılamadı, bilinen bir anahtar kelime bulunamadı.")
        else:
            not_ = " - metinde az ipucu var, emin değilim" if sonuc.guven < self.DUSUK_GUVEN else ""
            print(f"Genel konu : {sonuc.genel_konu} (model güveni %{sonuc.guven * 100:.0f}){not_}")
            ikinci, olasilik = (sonuc.genel_olasiliklar + [(None, 0)])[1]
            # ikinci konu ya kendi basina guclu ya da birinciye yakinsa gosteriliyor
            if olasilik >= 0.15 or olasilik >= sonuc.guven / 2:
                print(f"             ikinci ihtimal: {ikinci} (%{olasilik * 100:.0f})")
            if sonuc.alt_konular:
                print("Alt konular: " + ", ".join(alt.tam_ad for alt, _ in sonuc.alt_konular))
            else:
                print("Alt konular: belirgin bir alt konu yok")
            print("Kelimeler  : " + ", ".join(sonuc.anahtar_kelimeler))

        for kelime, konu in yeni_kelimeler:
            print(f"Öğrenme adayı: '{kelime}' -> {konu}. Doğruysa /ogret komutuyla onaylayabilirsiniz.")

        sohbet = self.uygulama.sohbet
        if sohbet.genel_konu():
            print(f"Sohbetin konusu: {sohbet.genel_konu()}")

        if sorgu and not self.uygulama.cevrimici:
            print(f"\nArama sorgusu: “{sorgu.dogal}”  (çevrimdışı mod, arama yapılmadı)")
        elif sorgu:
            # sorgunun kendisi tirnak icerebildigi icin disarida farkli tirnak kullaniliyor
            ek = f"  (Vikipedi: “{sorgu.anahtar}”)" if sorgu.anahtar != sorgu.dogal else ""
            print(f"\nİnternette aranan: “{sorgu.dogal}”{ek}")
            for s in sonuclar:
                ozet = s.ozet if len(s.ozet) <= self.OZET_UZUNLUGU else s.ozet[:self.OZET_UZUNLUGU] + "..."
                print(f"  - {s.baslik} [{s.kaynak}]\n    {s.adres}")
                if ozet:
                    print(f"    {ozet}")
            # bir kaynak cevap vermezse (orn. istek siniri) digerinin sonuclari yine gosterilir
            if not sonuclar:
                print("  Sonuç alınamadı. " + "; ".join(self.uygulama.arama_hatalari))
            elif self.uygulama.arama_hatalari:
                print("  (Ulaşılamayan kaynak: " + "; ".join(self.uygulama.arama_hatalari) + ")")
        print()


def arguman_oku():
    ayristirici = argparse.ArgumentParser(description="Turkce metin konu siniflandirici")
    ayristirici.add_argument("--veritabani", default=os.path.join(KLASOR, "kayitlar.db"),
                             help="SQLite dosyasi (varsayilan: kayitlar.db)")
    ayristirici.add_argument("--cevrimdisi", action="store_true", help="internet aramasi yapma")
    ayristirici.add_argument("--adim-adim", action="store_true", help="metin isleme asamalarinda debugger ile dur")
    ayristirici.add_argument("--sonuc-sayisi", type=int, default=3, help="her kaynaktan alinacak sonuc sayisi")
    return ayristirici.parse_args()


def main():
    # Windows konsolunda Turkce karakterler bozulmasin
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    argumanlar = arguman_oku()
    try:
        uygulama = Uygulama(argumanlar.veritabani, not argumanlar.cevrimdisi,
                            argumanlar.sonuc_sayisi, argumanlar.adim_adim)
    except FileNotFoundError as hata:
        sys.exit(f"Veri dosyası bulunamadı: {hata.filename}")
    except ValueError as hata:              # konu dosyasinda bozuk satir
        sys.exit(f"Konu dosyası okunamadı: {hata}")
    except sqlite3.Error as hata:
        sys.exit(f"Veritabanı açılamadı ({argumanlar.veritabani}): {hata}")
    KonsolArayuzu(uygulama).calistir()


if __name__ == "__main__":
    main()
