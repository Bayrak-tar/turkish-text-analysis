# Ad Soyad : Bayram Bayraktar
# Tarih    : 24.09.2026
#

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from html.parser import HTMLParser


@dataclass
class AramaSonucu:
    baslik: str
    adres: str
    ozet: str
    kaynak: str


class AramaMotoru(ABC):
    ad = "?"
    sorgu_turu = "dogal"
    ZAMAN_ASIMI = 8
    TARAYICI = "Mozilla/5.0 (X11; Linux x86_64) KonuSiniflandirici/1.0"

    def _indir(self, adres, veri=None):
        if veri is not None:
            veri = urllib.parse.urlencode(veri).encode("utf-8")
        istek = urllib.request.Request(adres, data=veri, headers={"User-Agent": self.TARAYICI})
        with urllib.request.urlopen(istek, timeout=self.ZAMAN_ASIMI) as cevap:
            return cevap.read().decode("utf-8", errors="replace")

    @abstractmethod
    def ara(self, sorgu, adet):
        """[AramaSonucu, ...] dondurur."""


class VikipediArama(AramaMotoru):
    ad = "Vikipedi"
    sorgu_turu = "anahtar"
    API = "https://tr.wikipedia.org/w/api.php"

    def ara(self, sorgu, adet):
        kelimeler = sorgu.split()
        basliklar = []
        while kelimeler and not basliklar:
            basliklar = self._basliklar(" ".join(kelimeler), adet)
            kelimeler = kelimeler[:-1] if len(kelimeler) > 1 else []
        if not basliklar:
            return []
        ozetler = self._ozetler(basliklar)
        return [AramaSonucu(b, "https://tr.wikipedia.org/wiki/" + urllib.parse.quote(b.replace(" ", "_")),
                            ozetler.get(b, ""), self.ad) for b in basliklar]

    def _basliklar(self, sorgu, adet):
        parametreler = {"action": "query", "list": "search", "srsearch": sorgu,
                        "srlimit": adet, "format": "json", "utf8": 1}
        veri = json.loads(self._indir(self.API + "?" + urllib.parse.urlencode(parametreler)))
        return [s["title"] for s in veri.get("query", {}).get("search", [])]

    def _ozetler(self, basliklar):
        parametreler = {"action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1,
                        "exsentences": 3, "exlimit": len(basliklar), "titles": "|".join(basliklar),
                        "format": "json", "utf8": 1}
        veri = json.loads(self._indir(self.API + "?" + urllib.parse.urlencode(parametreler)))
        sayfalar = veri.get("query", {}).get("pages", {}).values()
        return {s["title"]: re.sub(r"\s+", " ", s.get("extract", "")).strip() for s in sayfalar if "title" in s}


class _DuckDuckGoAyristirici(HTMLParser):
    """DuckDuckGo html sayfasindaki sonuc basliklarini, linkleri ve ozetleri toplar."""

    def __init__(self):
        super().__init__()
        self.sonuclar = []
        self._alan = None       
        self._tampon = []
        self._adres = ""

    def handle_starttag(self, etiket, nitelikler):
        nitelikler = dict(nitelikler)
        siniflar = (nitelikler.get("class") or "").split()
        if etiket == "a" and "result__a" in siniflar:
            self._alan, self._tampon = "baslik", []
            self._adres = nitelikler.get("href", "")
        elif "result__snippet" in siniflar:
            self._alan, self._tampon = "ozet", []

    def handle_endtag(self, etiket):
        if self._alan and etiket in ("a", "div", "td"):
            metin = re.sub(r"\s+", " ", "".join(self._tampon)).strip()
            if self._alan == "baslik":
                self.sonuclar.append({"baslik": metin, "adres": self._adres, "ozet": ""})
            elif self.sonuclar:
                self.sonuclar[-1]["ozet"] = metin
            self._alan = None

    def handle_data(self, veri):
        if self._alan:
            self._tampon.append(veri)


class DuckDuckGoArama(AramaMotoru):
    ad = "DuckDuckGo"
    ADRES = "https://html.duckduckgo.com/html/"

    def ara(self, sorgu, adet):
        return self.sonuclari_ayikla(self._indir(self.ADRES, {"q": sorgu, "kl": "tr-tr"}), adet)

    def sonuclari_ayikla(self, html, adet):
        ayristirici = _DuckDuckGoAyristirici()
        ayristirici.feed(html)
        sonuclar = []
        for s in ayristirici.sonuclar:
            adres = self._gercek_adres(s["adres"])
            # reklam linkleri duckduckgo uzerinden y.js ile yonlendiriliyor
            if not adres or "duckduckgo.com/y.js" in adres:
                continue
            sonuclar.append(AramaSonucu(s["baslik"], adres, s["ozet"], self.ad))
            if len(sonuclar) == adet:
                break
        return sonuclar

    @staticmethod
    def _gercek_adres(adres):
        # linkler "//duckduckgo.com/l/?uddg=<asil adres>" seklinde geliyor
        if "uddg=" in adres:
            sorgu = urllib.parse.urlparse(adres).query
            return urllib.parse.parse_qs(sorgu).get("uddg", [""])[0]
        if adres.startswith("//"):
            return "https:" + adres
        return adres


class BilgiToplayici:
    """Birden fazla arama motorunu kullanip sonuclari birlestirir."""

    def __init__(self, motorlar, sonuc_sayisi=3):
        self.motorlar = motorlar
        self.sonuc_sayisi = sonuc_sayisi
        self.hatalar = []
        self._onbellek = {}

    def topla(self, sorgu):
        """sorgu: dogal ve anahtar halleri olan bir AramaSorgusu. Her motor kendi turunu kullanir."""
        anahtar = (sorgu.dogal, sorgu.anahtar)
        self.hatalar = []
        if anahtar in self._onbellek:
            return self._onbellek[anahtar]

        sonuclar, gorulen = [], set()
        for motor in self.motorlar:
            metin = sorgu.anahtar if motor.sorgu_turu == "anahtar" else sorgu.dogal
            try:
                bulunan = motor.ara(metin, self.sonuc_sayisi)
            except (urllib.error.URLError, OSError, ValueError, KeyError) as hata:
                self.hatalar.append(f"{motor.ad}: {getattr(hata, 'reason', hata)}")
                continue
            for s in bulunan:
                if s.adres not in gorulen:
                    gorulen.add(s.adres)
                    sonuclar.append(s)

        # hata olduysa onbellege yazma, sonraki denemede tekrar denensin
        if sonuclar and not self.hatalar:
            self._onbellek[anahtar] = sonuclar
        return sonuclar
