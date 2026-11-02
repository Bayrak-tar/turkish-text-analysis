# Ad Soyad : Bayram Bayraktar
# Tarih    : 24.09.2026
#
# Konu agaci, Naive Bayes ve TF-IDF siniflandiricilari.
# Genel konu Naive Bayes ile, alt konular TF-IDF kosinus benzerligi ile bulunur.

import math
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field


class AltKonu:
    def __init__(self, ad, genel_konu):
        self.ad = ad
        self.genel_konu = genel_konu
        self.ozellikler = Counter()

    @property
    def tam_ad(self):
        return f"{self.genel_konu.ad} > {self.ad}"

    def __repr__(self):
        return f"AltKonu({self.tam_ad})"


class GenelKonu:
    def __init__(self, ad):
        self.ad = ad
        self.ozellikler = Counter()     # genel konunun kendi kelimeleri
        self.alt_konular = []

    def tum_ozellikler(self):
        toplam = Counter(self.ozellikler)
        for alt in self.alt_konular:
            toplam.update(alt.ozellikler)
        return toplam


class KonuAgaci:
    def __init__(self):
        self.genel_konular = {}
        self.uyarilar = []      # konu dosyasindaki tutarsizliklar, program yine de calisir

    @property
    def alt_konular(self):
        return [alt for g in self.genel_konular.values() for alt in g.alt_konular]

    def dosyadan_yukle(self, yol, ozellik_cikarici):
        genel = None
        with open(yol, encoding="utf-8") as dosya:
            for satir_no, satir in enumerate(dosya, 1):
                satir = satir.strip()
                if not satir or satir.startswith("#"):
                    continue
                if satir.startswith("[") and satir.endswith("]"):
                    ad = satir[1:-1].strip()
                    genel = self.genel_konular.setdefault(ad, GenelKonu(ad))
                    continue
                if genel is None or ":" not in satir:
                    raise ValueError(f"{yol}:{satir_no} satiri okunamadi -> {satir}")

                baslik, kelimeler = satir.split(":", 1)
                baslik = baslik.strip()
                anahtarlar = [ozellik_cikarici.sozluge_ekle(k) for k in kelimeler.split(",") if k.strip()]
                # ayni kelime iki kez yazildiysa agirligi ikiye katlanmasin
                anahtarlar = list(dict.fromkeys(a for a in anahtarlar if a))
                if not anahtarlar:
                    self.uyarilar.append(f"{yol}:{satir_no} '{baslik}' icin kelime yok, atlandi")
                    continue

                if baslik == "*":
                    genel.ozellikler.update(anahtarlar)
                elif any(a.ad == baslik for a in genel.alt_konular):
                    self.uyarilar.append(f"{yol}:{satir_no} '{genel.ad} > {baslik}' iki kez tanimli")
                else:
                    alt = AltKonu(baslik, genel)
                    alt.ozellikler.update(anahtarlar)
                    genel.alt_konular.append(alt)
        return self

    def veritabanindan_yukle(self, veritabani, ozellik_cikarici):
        """Konu agacini kalici SQLite modelinden yukler."""
        for genel_ad, genel_anahtarlar, altlar in veritabani.konu_agaci_verisi():
            genel = GenelKonu(genel_ad)
            genel.ozellikler.update(genel_anahtarlar)
            for anahtar in genel_anahtarlar:
                ozellik_cikarici.sozluge_ekle(anahtar.replace("_", " "))
            for alt_ad, anahtarlar in altlar:
                alt = AltKonu(alt_ad, genel)
                alt.ozellikler.update(anahtarlar)
                for anahtar in anahtarlar:
                    ozellik_cikarici.sozluge_ekle(anahtar.replace("_", " "))
                genel.alt_konular.append(alt)
            self.genel_konular[genel_ad] = genel
        return self

class NaiveBayes:
    """Multinomial Naive Bayes. Onsel olasiliklar esit kabul edilir."""

    def __init__(self, alfa=0.05):
        self.alfa = alfa
        self._sayim = defaultdict(Counter)
        self._toplam = Counter()
        self._kelimeler = set()

    def ornek_ekle(self, sinif, ozellikler, agirlik=1.0):
        for ozellik, adet in ozellikler.items():
            self._sayim[sinif][ozellik] += adet * agirlik
            self._toplam[sinif] += adet * agirlik
            self._kelimeler.add(ozellik)

    def olasiliklar(self, ozellikler):
        bilinen = {o: n for o, n in ozellikler.items() if o in self._kelimeler}
        if not bilinen:
            return []

        v = len(self._kelimeler)
        log_puan = {}
        for sinif in self._sayim:
            payda = self._toplam[sinif] + self.alfa * v
            puan = 0.0
            for ozellik, adet in bilinen.items():
                puan += adet * math.log((self._sayim[sinif][ozellik] + self.alfa) / payda)
            log_puan[sinif] = puan

        # log-sum-exp ile normalize et (tasmayi onlemek icin)
        en_buyuk = max(log_puan.values())
        toplam = sum(math.exp(p - en_buyuk) for p in log_puan.values())
        sonuc = [(s, math.exp(p - en_buyuk) / toplam) for s, p in log_puan.items()]
        return sorted(sonuc, key=lambda x: -x[1])


class TfIdf:
    """Her alt konu bir belge gibi dusunulur, sorgu ile kosinus benzerligi hesaplanir."""

    def __init__(self):
        self._idf = {}
        self._vektorler = {}
        self._normlar = {}
        self._ters_indeks = defaultdict(list)

    def egit(self, belgeler):
        self._vektorler.clear()
        self._normlar.clear()
        self._ters_indeks.clear()
        n = len(belgeler)
        df = Counter()
        for ozellikler in belgeler.values():
            df.update(set(ozellikler))
        self._idf = {o: math.log((n + 1) / (sayi + 1)) + 1 for o, sayi in df.items()}

        for belge, ozellikler in belgeler.items():
            vektor = {o: self._tf(adet) * self._idf[o] for o, adet in ozellikler.items()}
            self._vektorler[belge] = vektor
            self._normlar[belge] = math.sqrt(sum(x * x for x in vektor.values())) or 1.0
            for o in vektor:
                self._ters_indeks[o].append(belge)

    @staticmethod
    def _tf(adet):
        # agirlikli sayimlar 1'in altina dusebiliyor, log orada negatif olur
        return 1 + math.log(adet) if adet >= 1 else adet

    def benzerlikler(self, ozellikler):
        sorgu = {o: self._tf(adet) * self._idf[o] for o, adet in ozellikler.items() if o in self._idf}
        if not sorgu:
            return {}
        sorgu_normu = math.sqrt(sum(x * x for x in sorgu.values()))

        carpim = Counter()
        for o, deger in sorgu.items():
            for belge in self._ters_indeks[o]:
                carpim[belge] += deger * self._vektorler[belge][o]
        return {b: c / (sorgu_normu * self._normlar[b]) for b, c in carpim.items()}


@dataclass
class SiniflandirmaSonucu:
    metin: str
    genel_konu: str = None
    guven: float = 0.0
    genel_olasiliklar: list = field(default_factory=list)
    alt_konular: list = field(default_factory=list)       # [(AltKonu, puan)]
    anahtar_kelimeler: list = field(default_factory=list)
    taninmayan: list = field(default_factory=list)
    ozellikler: dict = field(default_factory=dict)            # ozellik -> agirlik (odak agir)
    yuzeyler: dict = field(default_factory=dict)              # ozellik -> metindeki hali

    @property
    def belirsiz(self):
        return self.genel_konu is None


class KonuSiniflandirici:
    ALT_KONU_ESIGI = 0.4        # en iyi alt konu puaninin bu orani ve ustu alinir
    OGRENME_GUVENI = 0.75
    OGRENME_TEKRARI = 2         # bir kelime ayni konuda kac kez gorulurse ogrenilsin
    OGRENILEN_AGIRLIK = 0.5

    def __init__(self, agac, ozellik_cikarici):
        self.adim_adim = False
        self.agac = agac
        self.cikarici = ozellik_cikarici
        self.bayes = NaiveBayes()
        self.tfidf = TfIdf()
        self._ogrenme_adaylari = defaultdict(list)   # (kok, konu) -> gorulen bicimler
        self._ogretilen = set()
        self._alt_adlari = {}

    def egit(self):
        self.bayes = NaiveBayes()
        for genel in self.agac.genel_konular.values():
            self.bayes.ornek_ekle(genel.ad, genel.tum_ozellikler())
        self.tfidf.egit({alt: alt.ozellikler for alt in self.agac.alt_konular})
        self._alt_adlari = {alt: set(self.cikarici.cikar(alt.ad)[0]) for alt in self.agac.alt_konular}

    def orneklerden_egit(self, yol):
        """Etiketli metinleri egitir; degerlendirme dosyasi bu metoda verilmez."""
        with open(yol, encoding="utf-8") as dosya:
            ornekler = json.load(dosya)
        altlar = {a.tam_ad: a for a in self.agac.alt_konular}
        # Hatali etiket varsa modeli kismen degistirmeden once dur.
        for o in ornekler:
            if not isinstance(o.get("metin"), str) or not o["metin"].strip():
                raise ValueError("Egitim metni bos olamaz")
            if o.get("genel_konu") not in self.agac.genel_konular:
                raise ValueError("Bilinmeyen egitim konusu")
            if any(ad not in altlar for ad in o.get("alt_konular", [])):
                raise ValueError("Bilinmeyen egitim alt konusu")
        # Yalnizca acikca etiketlenmis terimler sozluge eklenir; metindeki her
        # bilinmeyen fiili veya ozel adi konu kelimesi olarak ezberlemeyiz.
        for o in ornekler:
            for terim in o.get("terimler", []):
                self.cikarici.sozluge_ekle(terim)
        for o in ornekler:
            ozellikler, _, _ = self.cikarici.cikar(o["metin"])
            self.agac.genel_konular[o["genel_konu"]].ozellikler.update(ozellikler)
            # Cok etiketli metindeki butun kelimeleri her alt konuya dagitma.
            if len(o.get("alt_konular", [])) == 1:
                alt = altlar[o["alt_konular"][0]]
                terimler = {self.cikarici.sozluge_ekle(t) for t in o.get("terimler", [])}
                alt.ozellikler.update({k: v for k, v in ozellikler.items()
                                      if k in alt.ozellikler or k in terimler})
        self.egit()
        return len(ornekler)

    def siniflandir(self, metin):
        ozellikler, taninmayan, yuzeyler = self.cikarici.cikar(metin)
        if self.adim_adim:
            print("\n[2] Özellikler çıkarıldı. İncele: ozellikler, taninmayan, yuzeyler.")
            breakpoint()
        sonuc = SiniflandirmaSonucu(metin=metin, taninmayan=taninmayan, ozellikler=dict(ozellikler),
                                    yuzeyler=yuzeyler,
                                    anahtar_kelimeler=[o.replace("_", " ") for o in ozellikler])

        olasiliklar = self.bayes.olasiliklar(ozellikler)
        if self.adim_adim:
            print("\n[3] Genel konu puanları hesaplandı. İncele: olasiliklar. İlk eleman seçilecek.")
            breakpoint()
        if not olasiliklar:
            return sonuc

        sonuc.genel_olasiliklar = olasiliklar
        sonuc.genel_konu, sonuc.guven = olasiliklar[0]
        sonuc.alt_konular = self._alt_konulari_sec(ozellikler, sonuc.genel_konu)
        if self.adim_adim:
            print("\n[5] Genel ve alt konular seçildi. İncele: sonuc.genel_konu, sonuc.guven, sonuc.alt_konular.")
            breakpoint()
        return sonuc

    def _alt_konulari_sec(self, ozellikler, genel_konu):
        puanlar = self.tfidf.benzerlikler(ozellikler)
        if self.adim_adim:
            print("\n[4] Alt konu benzerlikleri hesaplandı. İncele: puanlar, genel_konu. Sıradaki işlem: alt konu seçimi.")
            breakpoint()
        if not puanlar:
            return []
        en_iyi = max(puanlar.values())
        secilen = []
        for alt, p in puanlar.items():
            ad_ozellikleri = self._alt_adlari[alt]
            acik_ad = bool(ad_ozellikleri) and set(ad_ozellikleri) <= set(ozellikler)
            eslesen = set(alt.ozellikler) & set(ozellikler)
            ozgul = any(len(self.tfidf._ters_indeks[o]) == 1 for o in eslesen)
            # Acikca anilan veya kendine ozgu kaniti olan bir alt konu, diger
            # konular daha yuksek puan aldi diye elenmez. Sayisal ust sinir yok.
            if acik_ad or ozgul or p >= en_iyi * self.ALT_KONU_ESIGI:
                secilen.append((alt, p))
        # once kazanan genel konunun alt konulari, sonra digerleri
        secilen.sort(key=lambda x: (x[0].genel_konu.ad != genel_konu, -x[1]))
        return secilen

    def ogren(self, sonuc, kok_bulucu, yasakli_kokler):
        """
        Guvenle siniflandirilan metinlerde tekrar eden kelimeleri onay adayi yapar.
        Bu metot sozlugu veya modeli degistirmez.
        """
        if sonuc.belirsiz or sonuc.guven < self.OGRENME_GUVENI or len(sonuc.anahtar_kelimeler) < 2:
            return []

        yeni = []
        for kelime in set(sonuc.taninmayan):
            if len(kelime) < 4 or yasakli_kokler.intersection(kok_bulucu.adaylar(kelime)):
                continue
            anahtar = (kok_bulucu.genel_kok(kelime), sonuc.genel_konu)
            bicimler = self._ogrenme_adaylari[anahtar]
            bicimler.append(kelime)
            if len(bicimler) == self.OGRENME_TEKRARI:
                kok = self._ortak_kok(bicimler, kok_bulucu) or anahtar[0]
                # Tahminler yalnizca adaydir; kullanici onayi olmadan modeli
                # degistirmek yanlis siniflandirmayi kalici hale getirebilir.
                yeni.append((kok, sonuc.genel_konu))
        return yeni

    @staticmethod
    def _ortak_kok(bicimler, kok_bulucu):
        # gorulen butun bicimlerin ortak en uzun koku: "kitabı" + "kitaplar" -> "kitap"
        ortak = set(kok_bulucu.adaylar(bicimler[0]))
        for bicim in bicimler[1:]:
            ortak &= kok_bulucu.adaylar(bicim)
        ortak = [k for k in ortak if len(k) >= 4]
        return max(ortak, key=len) if ortak else None

    def kelime_ogret(self, kelime, genel_konu, alt_konu=""):
        if genel_konu not in self.agac.genel_konular:
            raise ValueError("Bilinmeyen genel konu: " + genel_konu)
        alt = next((a for a in self.agac.genel_konular[genel_konu].alt_konular
                    if a.ad == alt_konu), None)
        if alt_konu and alt is None:
            raise ValueError("Bu genel konuya ait olmayan alt konu: " + alt_konu)
        if not self.cikarici.metin.icerik_kelimeleri(kelime):
            raise ValueError("Anlamli bir kelime veya terim giriniz")
        anahtar = self.cikarici.sozluge_ekle(kelime)
        kimlik = (anahtar, genel_konu, alt_konu)
        if anahtar and kimlik not in self._ogretilen:
            self._ogretilen.add(kimlik)
            hedef = alt if alt else self.agac.genel_konular[genel_konu]
            hedef.ozellikler[anahtar] += self.OGRENILEN_AGIRLIK
            self.egit()
