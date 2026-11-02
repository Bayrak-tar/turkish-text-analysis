# Ad Soyad : Bayram Bayraktar
# Tarih    : 24.09.2026
#
# Sohbet takibi ve arama sorgusu olusturma.
#   SohbetBaglami  : metinlerin sonuclarini biriktirir, eski metinlerin etkisi her adimda azalir.
#   SorguOlusturucu: sohbetten ve son metinden arama motorlarina gidecek sorguyu kurar.

import re
from collections import Counter
from dataclasses import dataclass

from dil_isleme import DURAK_KELIMELER, TurkceMetin

METIN = TurkceMetin()

# Kendi basina konu olmayan, bilginin hangi bicimde istendigini gosteren alt konular
ICERIK_BICIMLERI = {"Kitaplar": "kitaplar", "Roman": "romanlar", "Çizgi Roman": "çizgi romanlar",
                    "Sesli Kitap ve E-Kitap": "sesli kitaplar", "Filmler": "filmler",
                    "Diziler": "diziler", "Belgeseller": "belgeseller", "Podcast": "podcastler",
                    "Online Eğitim": "online kurslar", "YouTube ve İçerik Üretimi": "video"}

# Soru kelimeleri. Ekli halleri de soru sayilir: "neresidir", "nasildir", "kacinci"
SORU_KOKLERI = ("nasıl", "nere", "hangi", "kaç", "niçin", "niye")
SORU_KELIMELERI = {"ne", "neden", "nedir", "nelerdir", "neler", "kim", "kimdir", "kimin",
                   "mi", "mı", "mu", "mü", "midir", "mıdır", "mudur", "müdür"}
ISTEK_EKLERI = {"misin", "mısın", "musun", "müsün", "misiniz", "mısınız", "musunuz", "müsünüz"}
# Tek baslarina arama degeri olmayan soru ekleri: "belgeseller var mi" -> "belgeseller"
SORU_EKLERI = {"mi", "mı", "mu", "mü", "midir", "mıdır", "mudur", "müdür",
               "miyim", "mıyım", "muyum", "müyüm", "miyiz", "mıyız", "muyuz", "müyüz"} | ISTEK_EKLERI


def soru_kelimesi_mi(kelime):
    return kelime in SORU_KELIMELERI or kelime.startswith(SORU_KOKLERI)


def soru_mu(metin):
    kelimeler = METIN.kelimeler(metin)
    return ("?" in metin or any(soru_kelimesi_mi(k) for k in kelimeler)
            or bool(ISTEK_EKLERI.intersection(kelimeler)))


def bicim_istegi_mi(sonuc):
    """
    Metin yeni konu acmiyor, sadece bilginin bicimini mi istiyor ("bu konuda kitap onerir misin")?
    Sart soru olmasi: "yeni bir roman okumaya basladim" konunun kendisini bildirir.
    """
    kendi = [a for a, _ in sonuc.alt_konular if a.genel_konu.ad == sonuc.genel_konu]
    return bool(kendi) and all(a.ad in ICERIK_BICIMLERI for a in kendi) and soru_mu(sonuc.metin)


class SohbetBaglami:
    AZALMA = 0.85           # her yeni metinde eski puanlar bu oranla carpilir
    EN_DUSUK_OLASILIK = 0.15
    ODAK_ORANI = 0.3        # en guclu konunun bu orani kadar agirligi olan konular odakta sayilir
    EN_FAZLA_ODAK = 3

    def __init__(self):
        self.genel_agirlik = Counter()
        self.alt_agirlik = Counter()    # AltKonu -> puan
        self.son_sonuc = None
        self.aktif_bicim = None
        self.bicim_konusu = None
        self.son_icerik = None

    def ekle(self, sonuc):
        """Bir siniflandirma sonucunu sohbet gecmisine isler."""
        self.son_sonuc = sonuc
        if sonuc.belirsiz:
            # agirliklari degistirmez ama son metin odur: bilinmeyen bir terim sorulmus olabilir
            return

        bicim = next((a for a, _ in sonuc.alt_konular if a.ad in ICERIK_BICIMLERI), None)
        icerik_altlari = [a for a, _ in sonuc.alt_konular if a.ad not in ICERIK_BICIMLERI]
        sadece_bicim = bool(bicim) and not icerik_altlari
        icerik_konusu = (icerik_altlari[0].genel_konu.ad if bicim and icerik_altlari
                         else sonuc.genel_konu)
        if bicim:
            self.aktif_bicim = bicim
            self.bicim_konusu = (self.son_icerik.genel_konu if sadece_bicim and self.son_icerik
                                 else None if sadece_bicim else icerik_konusu)
        elif self.aktif_bicim:
            if self.bicim_konusu and icerik_konusu != self.bicim_konusu:
                self.aktif_bicim = None
                self.bicim_konusu = None
            else:
                self.bicim_konusu = icerik_konusu
        if not sadece_bicim:
            self.son_icerik = sonuc

        for konu in self.genel_agirlik:
            self.genel_agirlik[konu] *= self.AZALMA
        for alt in self.alt_agirlik:
            self.alt_agirlik[alt] *= self.AZALMA

        # sadece bicim isteyen metin ("bu konuda kitap onerir misin") sohbetin konusunu degistirmez
        if not (self.genel_agirlik and bicim_istegi_mi(sonuc)):
            # en olasi konu her zaman, digerleri ancak belli bir olasiligin ustundeyse eklenir
            for sira, (konu, olasilik) in enumerate(sonuc.genel_olasiliklar):
                if sira == 0 or olasilik >= self.EN_DUSUK_OLASILIK:
                    self.genel_agirlik[konu] += olasilik

        # alt konu puanlari metinden metne farkli olceklerde, en iyisine gore normalize ediliyor
        if sonuc.alt_konular:
            en_iyi = max(p for _, p in sonuc.alt_konular) or 1.0
            for alt, puan in sonuc.alt_konular:
                self.alt_agirlik[alt] += puan / en_iyi


    def genel_konu(self):
        if not self.genel_agirlik:
            return None
        return self.genel_agirlik.most_common(1)[0][0]

    def odak_konular(self):
        """
        Sohbette one cikan genel konulari ve her birinin en guclu alt konusunu dondurur.
        [(genel konu adi, AltKonu veya None), ...] agirliga gore sirali.
        """
        if not self.genel_agirlik:
            return []
        en_buyuk = self.genel_agirlik.most_common(1)[0][1]
        odak = []
        for konu, agirlik in self.genel_agirlik.most_common():
            if agirlik < en_buyuk * self.ODAK_ORANI or len(odak) == self.EN_FAZLA_ODAK:
                break
            altlar = [(a, p) for a, p in self.alt_agirlik.items() if a.genel_konu.ad == konu]
            en_iyi_alt = max(altlar, key=lambda x: x[1])[0] if altlar else None
            odak.append((konu, en_iyi_alt))
        return odak

    def en_guclu_alt_konu(self, genel, haric=()):
        """Sohbet boyunca bir genel konu altinda en cok puan toplayan alt konu."""
        altlar = [(a, p) for a, p in self.alt_agirlik.items()
                  if a.genel_konu.ad == genel and a.ad not in haric]
        return max(altlar, key=lambda x: x[1])[0] if altlar else None

    def en_guclu_bicim(self):
        """
        Sohbette istenen icerik bicimi. Bir kez istenen bicim sonraki metinlerde de gecerlidir
        ("programlama dilleri" + "kitap oner" -> programlama kitaplari).
        Metin sayisina gore degil, icerik konusu degistiginde birakilir.
        """
        return self.aktif_bicim


@dataclass
class AramaSorgusu:
    dogal: str      # dogal dilde sorgu, genel arama motorlari icin ("gokkusagi nasil olusur")
    anahtar: str    # anahtar kelime sorgusu, ansiklopedi aramasi icin ("gokkusagi")
    tur: str        # "soru", "bicim", "konu" ya da "tanımsız"

    def __bool__(self):
        return bool(self.dogal)


class SorguOlusturucu:
    """
    Sorgu dort durumda farkli kurulur (oncelik sirasiyla):
      0. Son metnin konusu hic anlasilamadiysa ve bir soruysa metin oldugu gibi aranir:
         "e-Mustahsil ne demektir" -> sozlukte olmayan terimi arama motoru bilir.
      1. Son metin kitap, video gibi bir bicim istiyorsa konu o bicimle birlestirilir:
         "java programlama dilleri hakkinda kitaplar"
      2. Son metin dogrudan bir soruysa sorunun kendisi aranir, istek kaliplari atilir:
         "kalburabasti tarifi verir misin" -> "kalburabasti tarifi"
      3. Bilgi veren metinlerde sohbetin konusu aranir. Sohbette gecmis bir bicim varsa onunla
         birlestirilir (kitap + bilim -> "bilimsel kitaplar", ardindan biyoloji -> "biyoloji
         hakkinda bilimsel kitaplar"), yoksa alt konu son metne ozgu ayrintilarla daraltilir.
    Birbiriyle ilgisiz iki konu (heykel + ilac gibi) hicbir durumda birlestirilmez.
    """

    AYRINTILI_BICIMLER = {"video"}
    SIFATLAR = {"Bilim": "bilimsel", "Felsefe": "felsefi"}     # "bilimsel kitaplar"

    KORUNAN_KELIMELER = {"en", "daha", "ile", "ve", "veya", "diğer", "başka"}  # "en faydali", "diger iller"
    YENI_SORU_KELIMELERI = {"peki", "ayrıca"}
    DOLGU_KELIMELERI = {"lütfen", "acaba", "bana", "bize", "bilgi", "almak", "istiyorum", "istiyoruz",
                        "rica", "ederim", "vs", "falan", "filan", "şuanda", "yardımcı", "olur"}

    NET_METIN_GUVENI = 0.4  # son metin bu guvenin ustundeyse arama onun konusuyla yapilir
    EN_UZUN_SORU = 8        # daha uzun sorular anahtar kelimelerine indirgenir
    EN_FAZLA_ANAHTAR = 4
    ODAK_ESIGI = 3          # dil isleme modulunun odak kelimelere verdigi agirlik
    EN_FAZLA_YAYGINLIK = 2  # bir kelime en fazla bu kadar alt konuda geciyorsa ozgul sayilir

    def __init__(self, agac):
        self.metin = METIN
        # her ozelligin kac alt konuda gectigi: az ise o alt konuya ozgu bir ayrintidir
        self._yayginlik = Counter()
        for alt in agac.alt_konular:
            self._yayginlik.update(alt.ozellikler.keys())
        # genel konularin kendi kelimeleri ("bilim", "spor") sorguya ayrinti olarak eklenmez
        self._genel_kelimeler = {o for g in agac.genel_konular.values() for o in g.ozellikler}
        self._genel_tum = {g.ad: set(g.tum_ozellikler()) for g in agac.genel_konular.values()}

    def olustur(self, baglam):
        son = baglam.son_sonuc
        if son is None:
            return AramaSorgusu("", "", "konu")
        devam = self._devam_sorgusu(son, baglam)
        if devam:
            return devam
        if son.belirsiz:
            return self._tanimsiz_sorgu(son)
        odak = baglam.odak_konular()
        if not odak:
            return AramaSorgusu("", "", "konu")

        son_bicim = self._son_metin_bicimi(son)
        if not son_bicim:
            soru = self._soru_sorgusu(son, baglam)
            if soru:
                return soru
        # daha once istenen bicim sonraki metinlerde de gecerli olur
        bicim_alt = son_bicim or baglam.en_guclu_bicim()

        genel = self._ana_konu(son, odak, bicim_alt)
        konu_alt = next((a for a, _ in son.alt_konular
                         if a.genel_konu.ad == genel and a.ad not in ICERIK_BICIMLERI), None)
        if konu_alt is None and genel:
            konu_alt = baglam.en_guclu_alt_konu(genel, haric=ICERIK_BICIMLERI)
        if genel is None or (bicim_alt and bicim_alt.genel_konu.ad == genel and konu_alt is None):
            # sadece bicimden bahsedilmis ("kitap okuyorum")
            bicim = ICERIK_BICIMLERI[bicim_alt.ad] if bicim_alt else ""
            return AramaSorgusu(bicim, bicim, "bicim")

        konu = konu_alt.ad if konu_alt else genel
        if bicim_alt:
            parcalar = self._bicimli(son, genel, konu, konu_alt, bicim_alt)
            anahtar = [p for p in parcalar if p != "hakkında"]
            tur = "bicim"
        else:
            parcalar = self._metin_sorgusu(son, genel) or [konu] + self._ayrintilar(son, genel, konu)
            anahtar, tur = parcalar, "konu"
        return AramaSorgusu(self.metin.kucult(" ".join(parcalar)),
                            self.metin.kucult(" ".join(anahtar)), tur)

    # ---- tanimsiz metin ----

    def _devam_sorgusu(self, son, baglam):
        """Acik gondermeli, yeni terim icermeyen sorular onceki icerigi kullanir."""
        onceki = baglam.son_icerik
        if onceki is None or onceki is son:
            return None
        kelimeler = self.metin.kelimeler(son.metin)
        gonderme = {"bunun", "bunu", "buna", "bunların", "bunları", "onun", "onu"}
        metin = self.metin.kucult(son.metin)
        if not (set(kelimeler) & gonderme or "bu konu" in metin):
            return None
        genel_sozler = (DURAK_KELIMELER | self.DOLGU_KELIMELERI | SORU_EKLERI |
                        {"fazla", "ver", "verir", "anlat", "anlatır", "açıkla", "açıklar",
                         "detay", "detaylı", "ayrıntı", "ayrıntılı", "örnek", "örnekler"})
        yeni_terimler = [k for k in son.taninmayan if k not in genel_sozler and not soru_kelimesi_mi(k)]
        if yeni_terimler:
            return None
        alt = next((a for a, _ in onceki.alt_konular if a.ad not in ICERIK_BICIMLERI), None)
        konu = alt.ad if alt else onceki.genel_konu
        bicim = baglam.en_guclu_bicim()
        parcalar = ([konu, "hakkında", ICERIK_BICIMLERI[bicim.ad]] if bicim
                    else [konu, "hakkında detaylı bilgi"])
        return AramaSorgusu(self.metin.kucult(" ".join(parcalar)), self.metin.kucult(konu), "devam")

    EN_UZUN_TANIMSIZ = 120      # daha uzun metinler sorgu olarak gonderilmez
    EN_KISA_TERIM = 3
    # Emoji ve sus noktalama atilir; anlam tasiyan isaretler ("2+2", "%15", "e-devlet") kalir.
    _ISARETLER = re.compile(r"[^\w\s+\-*/=%.,'#&]", re.UNICODE)

    def _tanimsiz_sorgu(self, son):
        """
        Konusu anlasilamayan metin icin sorgu: sozlukte olmayan bir terim sorulmus olabilir
        ("e-Mustahsil ne demektir"), arama motorlari bu terimleri bilir. Metin hem soru olmali
        hem de sorulacak bir terim icermeli, yoksa bosuna istek gonderilir.
        """
        metin = " ".join(son.metin.split())
        terimler = [k for k in son.taninmayan if len(k) >= self.EN_KISA_TERIM
                    and not soru_kelimesi_mi(k) and k not in SORU_EKLERI
                    and k not in self.DOLGU_KELIMELERI]
        if not terimler or not soru_mu(metin) or len(metin) > self.EN_UZUN_TANIMSIZ:
            return AramaSorgusu("", "", "konu")
        # kelimelere ayirmadan kuruluyor ki "e-Mustahsil", "2+2" gibi yazimlar bozulmasin
        ham = self._ISARETLER.sub(" ", metin).split()
        # Buyuk harfle yazilmis taninmayan terim tirnaga aliniyor: arama motorlari bilmedikleri
        # terimi sessizce benzerine ceviriyor ("Kadirgali kac bolum" -> baska bir dizi). Kucuk
        # harfli siradan kelimeleri sabitlemek ise sonuclari gereksiz daraltir.
        vurgulu = next((h for h in ham if any(c.isupper() for c in h)
                        and set(self.metin.kelimeler(h)) & set(terimler)), None)
        sorgu = " ".join(f'"{self.metin.kucult(h)}"' if h == vurgulu else self.metin.kucult(h)
                         for h in ham)
        # Vikipedi'ye soru degil sorulan terim gider ("carkifelek nedir" -> "carkifelek").
        # Turkcede sorulan sey soru kelimesinden once gelir, sonrasi ansiklopedide gurultudur.
        kelimeler = self.metin.kelimeler(metin)
        soru_yeri = next((i for i, k in enumerate(kelimeler)
                          if soru_kelimesi_mi(k) or k in SORU_EKLERI), len(kelimeler))
        sorulan = [k for k in kelimeler[:soru_yeri] if k in set(terimler)]
        anahtar = (sorulan or terimler)[:self.EN_FAZLA_ANAHTAR]
        return AramaSorgusu(sorgu, " ".join(anahtar), "tanımsız")

    # ---- bicim ----

    def _son_metin_bicimi(self, son):
        return next((a for a, _ in son.alt_konular if a.ad in ICERIK_BICIMLERI), None)

    def _bicimli(self, son, genel, konu, konu_alt, bicim_alt):
        bicim = ICERIK_BICIMLERI[bicim_alt.ad]
        if bicim in self.AYRINTILI_BICIMLER:
            return [konu] + self._ayrintilar(son, genel, konu) + [bicim]
        # kitapta sadece odaktaki ayrinti eklenir, yoksa kategori duzeyinde kalinir
        onek = self._ayrintilar(son, genel, konu, sadece_odak=True)[:1]
        sifat = self.SIFATLAR.get(genel)
        if konu_alt:
            return onek + [konu, "hakkında"] + ([sifat] if sifat else []) + [bicim]
        return onek + [sifat or genel, bicim]

    def _ana_konu(self, son, odak, bicim_alt):
        # Metin ya yeterince net olmali ya da kendi konusuna ait bir alt konu icermeli; ikisi
        # de yoksa sohbetin konusu kullanilir ("peki fiyatlari nasil" gibi devam cumleleri).
        kendi_alt_konusu = any(a.genel_konu.ad == son.genel_konu for a, _ in son.alt_konular)
        if son.guven >= self.NET_METIN_GUVENI or kendi_alt_konusu:
            # metin bicimin konusuna (Edebiyat) gitmis ama asil konu baska olabilir:
            # "java programlama dili kitaplari" -> Teknoloji
            if bicim_alt and son.genel_konu == bicim_alt.genel_konu.ad:
                for alt, _ in son.alt_konular:
                    if alt.genel_konu.ad != son.genel_konu and alt.ad not in ICERIK_BICIMLERI:
                        return alt.genel_konu.ad
                # metinde bicimden baska konu yok, konu sohbetin geri kalanindan gelir
                konu = next((g for g, _ in odak if g != son.genel_konu), None)
                if konu:
                    return konu
            return son.genel_konu
        for genel, alt in odak:
            if not (alt and alt.ad in ICERIK_BICIMLERI):
                return genel
        return None

    # ---- soru ----

    def _soru_sorgusu(self, son, baglam):
        """
        Sorunun istek kaliplarindan ve durak kelimelerden arindirilmis hali. Uzun sorular
        anahtar kelimelere indirgenir; hic anahtar kelime yoksa sohbetin konusu basa eklenir.
        """
        if not soru_mu(son.metin):
            return None
        kelimeler = self.metin.kelimeler(son.metin)
        # "X fethetmis, peki diger iller nasil": asil soru son parcada, oncesinden sadece
        # anahtar kelimeler alinir
        baglam_kelimeleri = []
        parcalar = self._soru_parcalari(son.metin)
        if len(parcalar) > 1:
            kelimeler = parcalar[-1]
            onceki = " ".join(" ".join(p) for p in parcalar[:-1])
            baglam_kelimeleri = [k for k in self._anahtar_kelimeler(son) if k.split()[0] in onceki][:1]
        kalan = []
        for i, kelime in enumerate(kelimeler):
            sonraki = kelimeler[i + 1] if i + 1 < len(kelimeler) else ""
            if kelime in ISTEK_EKLERI or sonraki in ISTEK_EKLERI or kelime in self.DOLGU_KELIMELERI:
                continue    # "verir misin", "aciklar misin"
            if (kelime in DURAK_KELIMELER and not soru_kelimesi_mi(kelime)
                    and kelime not in self.KORUNAN_KELIMELER):
                continue
            kalan.append(kelime)
        # sondaki soru eki arama motoruna bir sey katmaz: "belgeseller var mi" -> "belgeseller"
        while kalan and (kalan[-1] in self.KORUNAN_KELIMELER or kalan[-1] in SORU_EKLERI):
            kalan.pop()
        if not kalan or all(soru_kelimesi_mi(k) or k in self.KORUNAN_KELIMELER for k in kalan):
            return None

        anahtar = self._anahtar_kelimeler(son)
        if len(kalan) > self.EN_UZUN_SORU and anahtar:
            kalan = anahtar + self._soru_kalibi(kalan)
        kalan = [k for k in baglam_kelimeleri if k not in kalan] + kalan
        if not son.ozellikler and baglam.genel_konu():
            konu = self.metin.kucult(baglam.genel_konu())
            kalan, anahtar = [konu] + kalan, [konu] + anahtar
        return AramaSorgusu(" ".join(kalan), " ".join(anahtar or kalan), "soru")

    def _soru_parcalari(self, metin):
        """
        Metni cumlelere ve "peki", "ayrica" gibi yeni soru baslatan kelimelerden boler.
        Soru kelimesi iceren son parca asil sorudur, sonrakiler atilir.
        """
        parcalar = [[]]
        for cumle in self.metin.cumleler(metin):
            if parcalar[-1]:
                parcalar.append([])
            for kelime in cumle:
                if kelime in self.YENI_SORU_KELIMELERI and parcalar[-1]:
                    parcalar.append([])
                    continue
                parcalar[-1].append(kelime)
        sorulu = [i for i, p in enumerate(parcalar) if any(soru_kelimesi_mi(k) for k in p)]
        return parcalar[:sorulu[-1] + 1] if sorulu else parcalar

    def _soru_kalibi(self, kelimeler):
        """Uzun sorudan soru kalibini alir: "... nasil yapabilirim" -> ["nasil", "yapabilirim"]"""
        for i, kelime in enumerate(kelimeler):
            if soru_kelimesi_mi(kelime) and kelime not in {"mi", "mı", "mu", "mü"}:
                return kelimeler[i:i + 2]
        return []

    def _anahtar_kelimeler(self, son):
        """Anahtar kelimeler + ozel adlar: "Turkiyenin baskenti neresidir" -> ["turkiye", "baskenti"]"""
        sirali = sorted(son.ozellikler.items(), key=lambda x: (x[1] < 1, list(son.ozellikler).index(x[0])))
        kelimeler = []
        for ozellik, _ in sirali:
            yuzey = son.yuzeyler.get(ozellik, ozellik.replace("_", " "))
            # "istanbul fetih" varken ayrica "fetih" eklenmesin
            if not set(yuzey.split()) <= set(" ".join(kelimeler).split()):
                kelimeler.append(yuzey)
        adlar = [a for a in self.metin.ozel_adlar(son.metin) if a not in " ".join(kelimeler)]
        return (adlar + kelimeler)[:self.EN_FAZLA_ANAHTAR]

    def _metin_sorgusu(self, son, genel):
        """
        Metin ozgul bir ayrinti iceriyorsa kategori adi yerine kendi anahtar kelimeleri daha
        iyi bir sorgudur: "Selimiye camii gezdim..." -> "selimiye cami mimari".
        Ozgul ayrinti yoksa None doner, kategori duzeyinde aranir.
        """
        if son.genel_konu != genel:
            return None
        ayrintilar = set(self._ayrintilar(son, genel, "", hepsi=True))
        if not ayrintilar:
            return None
        kelimeler = [son.yuzeyler.get(o, o.replace("_", " ")) for o, agirlik in son.ozellikler.items()
                     if agirlik >= 1 or son.yuzeyler.get(o) in ayrintilar]
        return kelimeler[:self.EN_FAZLA_ANAHTAR]

    # ---- ayrinti ----

    def _ayrintilar(self, son, genel, konu_adi, en_fazla=2, sadece_odak=False, hepsi=False):
        """
        Metinde gecen, arama konusuna ait ve az sayida alt konuda gecen (ozgul) kelimeler.
        Once odaktaki ve on plandakiler, yoksa arka plandakiler alinir. Genel konu kelimeleri
        ("bilim", "spor") ve konu adinda zaten gecenler eklenmez.
        """
        ad_kelimeleri = self.metin.kucult(konu_adi).split()
        adaylar = []
        for sira, (ozellik, agirlik) in enumerate(son.ozellikler.items()):
            if (ozellik not in self._genel_tum.get(genel, ()) or ozellik in self._genel_kelimeler
                    or self._yayginlik[ozellik] > self.EN_FAZLA_YAYGINLIK):
                continue
            if any(k.startswith(p) or p.startswith(k) for k in ozellik.split("_") for p in ad_kelimeleri):
                continue
            if sadece_odak and agirlik < self.ODAK_ESIGI:
                continue
            adaylar.append((agirlik < 1, -agirlik, sira, son.yuzeyler.get(ozellik, ozellik.replace("_", " "))))
        adaylar.sort()
        if hepsi:
            return [a[3] for a in adaylar]
        on_plan = [a for a in adaylar if not a[0]]
        return [a[3] for a in (on_plan or adaylar)[:en_fazla]]
