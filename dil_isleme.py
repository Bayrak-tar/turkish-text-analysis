# Ad Soyad : Bayram Bayraktar
# Tarih    : 23.09.2026
#


import re
from collections import Counter

UNLULER = "aeıioöuü"
KALIN_UNLULER = "aıou"

# Anlami olmayan / her konuda gecebilecek kelimeler
DURAK_KELIMELER = set("""
ve veya ile ama fakat ancak lakin çünkü ki de da mi mı mu mü bu şu o bir birkaç bazı her hiç çok
daha en az pek gibi için kadar sonra önce göre rağmen dolayı ben sen biz siz onlar beni bana benim
seni sana senin onu ona onun bizi bize bizim sizi size sizin onları onlara onların kendi kendim
kendimi kendini ne neden niye nasıl nerede nereye nereden hangi kim şey şeyler şeyi işte zaten sadece
yalnızca bile hem ya yani artık hala henüz şimdi dün yarın var yok olarak olan oldu olur olmak
değil evet hayır tamam peki belki galiba sanırım bence acaba gerçekten özellikle genellikle bazen
hep hiçbir tüm bütün diğer başka aynı böyle şöyle öyle ise eğer dolayısıyla iken ayrıca bunu buna
bunun bunlar bunları bunlardan şunu şuna orada burada şurada içinde üzerine üzerinde hakkında
konusunda arasında beri diye gene yine merhaba selam lütfen teşekkürler teşekkür ederim ediyorum
oldukça biraz baya bayağı epey fazlasıyla hepsi herkes birçok birlikte beraber sürekli asla
neyi neye neyin neyle konu konuda konuyu konuya konudan konular konuları konuların konunun konusu
""".split())

# Kendinden kisa bir sozluk kokune yanlislikla eslesen yaygin kelimeler
# (fayda -> fay+da, adam -> ada+m, kazandi -> kaza, hissediyorum -> hisse)
KISA_KOK_ISTISNALARI = {"fayda", "adam", "kasım", "kasa", "kasap", "selam", "selim",
                        "kanat", "kanal", "dilek", "arıza", "ayın", "oyun",
                        "kazan", "hisset", "mantıklı", "mantıksız", "merak"}

# Konu kelimesiyle ayni yazilan yaygin kisi adlari. Cumle ortasinda buyuk harfle
# yazilmislarsa ("Ayse Deniz'i seviyor") kisi adi kabul edilir, konu kelimesi sayilmaz.
# Cumle basinda her kelime buyuk harfle basladigi icin orada bu ayrim yapilamaz.
KISI_ADLARI = {"altın", "aslan", "bayram", "bulut", "deniz", "gümüş", "kartal", "kaya", "melek",
               "mercan", "papatya", "sedef", "sevgi", "toprak", "yaprak", "yağmur", "yıldız",
               "çiçek", "ırmak", "şafak", "şahin"}

# Ogrenme sirasinda sozluge eklenmesini istemedigimiz genel kokler
ORTAK_KOKLER = set("""
et ed ol yap sev gel git gid al ver gör bak bil iste düşün söyle konuş başla bitir kal dur çık gir
bul anlat anla öğren merak hisset dene kullan ilgilen ilgi bahset konu zaman yıl insan hayat dünya
kişi güzel harika ilginç önemli büyük küçük yeni eski iyi kötü farklı özel fazla gerek lazım
istiyor seviyor düşünüyor biliyor yapıyor geliyor gidiyor okuyor şekil durum sebep sonuç
""".split())


def son_unlu(kelime):
    for harf in reversed(kelime):
        if harf in UNLULER:
            return harf
    return None


def ilk_unlu(kelime):
    for harf in kelime:
        if harf in UNLULER:
            return harf
    return None


def unlu_uyumlu(kok, ek):
    """Kokun son unlusu ile ekin ilk unlusu arasinda buyuk/kucuk unlu uyumu var mi?"""
    s = son_unlu(kok)
    e = ilk_unlu(ek)
    if s is None:
        return False
    if e is None or e in "oö":      # -yor gibi uyuma girmeyen ekler
        return True
    if e in "ae":
        return (e == "a") == (s in KALIN_UNLULER)
    beklenen = {"a": "ı", "ı": "ı", "o": "u", "u": "u",
                "e": "i", "i": "i", "ö": "ü", "ü": "ü"}[s]
    return e == beklenen


class TurkceMetin:
    """Metni kucuk harfe cevirip kelimelerine ayirir."""

    _donusum = str.maketrans({"I": "ı", "İ": "i", "Â": "a", "â": "a",
                              "Î": "i", "î": "i", "Û": "u", "û": "u"})
    # Aritmetik ifadeler tek kelime sayilir, yoksa "2+2" sorguda "2 2" olup anlamini yitiriyor
    _kelime = re.compile(r"[a-zçğıöşü0-9]+(?:[+*×÷^][a-zçğıöşü0-9]+)*")
    _kesme = re.compile(r"['’`][a-zçğıöşü]+")
    _tire = re.compile(r"(?<=[a-zçğıöşü0-9])-(?=[a-zçğıöşü0-9])")

    _karisik = re.compile(r"\w*I\w*")

    def kucult(self, metin):
        # IPSec, LinkedIn gibi karisik yazimlarda buyuk I Ingilizce "i"dir; "Işık" gibilere dokunulmaz
        metin = self._karisik.sub(self._yabanci_i, metin)
        return metin.translate(self._donusum).lower()

    @staticmethod
    def _yabanci_i(eslesme):
        kelime = eslesme.group()
        karisik = any(h.islower() for h in kelime) and any(h.isupper() for h in kelime[1:])
        return kelime.replace("I", "i") if karisik else kelime

    def kelimeler(self, metin):
        metin = self.kucult(metin)
        metin = metin.replace("kur'an", "kuran").replace("kur’an", "kuran")
        metin = self._kesme.sub("", metin)        # Ankara'da -> ankara
        metin = self._tire.sub("", metin)         # e-spor -> espor, f-16 -> f16
        return self._kelime.findall(metin)

    _ozel_ad = re.compile(r"([A-ZÇĞİÖŞÜ][a-zçğıöşüA-ZÇĞİÖŞÜ0-9]*)(?:['’`]([a-zçğıöşü]+))?")
    # Kesmesiz yazimda atilabilecek ekler. Adin sonuyla karisanlar (-ya, -in, -la) listede yok:
    # yoksa "Turkiye" -> "turki", "Mugla" -> "mug" olur.
    _ad_ekleri = ("nın", "nin", "nun", "nün", "ndan", "nden", "nda", "nde", "yla", "yle",
                  "dan", "den", "tan", "ten", "da", "de", "ta", "te")

    @staticmethod
    def _cumle_basi_mi(metin, konum):
        onceki = metin[:konum].rstrip()
        return not onceki or onceki[-1] in ".!?;:"

    def ozel_adlar(self, metin):
        """Buyuk harfli kelimeleri eksiz dondurur: "Turkiye'nin" -> turkiye, "Amerikayla" -> amerika."""
        adlar = []
        for eslesme in self._ozel_ad.finditer(metin):
            kelime, kesmeli_ek = self.kucult(eslesme.group(1)), eslesme.group(2)
            if kelime in DURAK_KELIMELER:
                continue
            # Her cumle buyuk harfle basladigi icin cumle basi ozel ad sayilmaz ("Bol soslu
            # istiridye"); kesme isaretli ek varsa ("Turkiye'nin") ozel ad oldugu bellidir.
            if not kesmeli_ek and self._cumle_basi_mi(metin, eslesme.start(1)):
                continue
            if not kesmeli_ek:
                for ek in self._ad_ekleri:
                    if (kelime.endswith(ek) and len(kelime) - len(ek) >= 4
                            and unlu_uyumlu(kelime[:-len(ek)], ek)):
                        kelime = kelime[:-len(ek)]
                        break
            if kelime not in adlar:
                adlar.append(kelime)
        return adlar

    def cumleler(self, metin):
        """Metni cumlelere ayirip her cumlenin kelimelerini dondurur."""
        return [k for k in (self.kelimeler(c) for c in re.split(r"[.!?;]+", metin)) if k]

    def icerik_kelimeleri(self, metin):
        return [k for k in self.kelimeler(metin) if k not in DURAK_KELIMELER]


class KokBulucu:
    """
    Kelimenin sonundan ekleri atarak olasi kok adaylarini uretir. Tek bir "dogru kok"
    aramak yerine aday uretip sozlukte eslesen en uzun adayi secmek daha saglam calisti.

    Ek turleri:
      U -> unluyle baslayan ek, kok unsuzle bitmeli (kitap-ı)
      K -> kaynastirmali ek, kok unluyle bitmeli (oda-sı, oku-yor)
      S -> serbest
    """

    EKLER = [
        # cogul, iyelik, hal ekleri
        ("lar", "S"), ("ler", "S"),
        ("ı", "U"), ("i", "U"), ("u", "U"), ("ü", "U"),
        ("ım", "U"), ("im", "U"), ("um", "U"), ("üm", "U"),
        ("ın", "U"), ("in", "U"), ("un", "U"), ("ün", "U"),
        ("ımız", "U"), ("imiz", "U"), ("umuz", "U"), ("ümüz", "U"),
        ("ınız", "U"), ("iniz", "U"), ("unuz", "U"), ("ünüz", "U"),
        ("a", "U"), ("e", "U"),
        ("m", "K"), ("n", "K"), ("mız", "K"), ("miz", "K"), ("muz", "K"), ("müz", "K"),
        ("nız", "K"), ("niz", "K"), ("nuz", "K"), ("nüz", "K"),
        ("sı", "K"), ("si", "K"), ("su", "K"), ("sü", "K"),
        ("yı", "K"), ("yi", "K"), ("yu", "K"), ("yü", "K"),
        ("ya", "K"), ("ye", "K"), ("na", "K"), ("ne", "K"),
        ("nın", "K"), ("nin", "K"), ("nun", "K"), ("nün", "K"),
        ("nda", "K"), ("nde", "K"), ("ndan", "K"), ("nden", "K"),
        ("yla", "K"), ("yle", "K"), ("yken", "K"),
        ("da", "S"), ("de", "S"), ("ta", "S"), ("te", "S"),
        ("dan", "S"), ("den", "S"), ("tan", "S"), ("ten", "S"),
        ("la", "S"), ("le", "S"), ("ki", "S"),
        # ek fiil ve fiil cekimleri
        ("dır", "S"), ("dir", "S"), ("dur", "S"), ("dür", "S"),
        ("tır", "S"), ("tir", "S"), ("tur", "S"), ("tür", "S"),
        ("dı", "S"), ("di", "S"), ("du", "S"), ("dü", "S"),
        ("tı", "S"), ("ti", "S"), ("tu", "S"), ("tü", "S"),
        ("mış", "S"), ("miş", "S"), ("muş", "S"), ("müş", "S"),
        ("yor", "K"), ("ıyor", "U"), ("iyor", "U"), ("uyor", "U"), ("üyor", "U"),
        ("ar", "U"), ("er", "U"), ("ır", "U"), ("ir", "U"), ("ur", "U"), ("ür", "U"),
        ("acak", "U"), ("ecek", "U"), ("yacak", "K"), ("yecek", "K"),
        ("abil", "U"), ("ebil", "U"), ("yabil", "K"), ("yebil", "K"),
        ("mak", "S"), ("mek", "S"), ("ma", "S"), ("me", "S"),
        ("sın", "S"), ("sin", "S"), ("sun", "S"), ("sün", "S"),
        ("ken", "S"),
        ("sa", "S"), ("se", "S"), ("sam", "S"), ("sem", "S"), ("san", "S"), ("sen", "S"),
        ("sak", "S"), ("sek", "S"),
        ("malı", "S"), ("meli", "S"),
        ("yım", "K"), ("yim", "K"), ("yum", "K"), ("yüm", "K"),
        ("ıl", "U"), ("il", "U"), ("ul", "U"), ("ül", "U"),
        ("dığı", "S"), ("diği", "S"), ("duğu", "S"), ("düğü", "S"),
        ("tığı", "S"), ("tiği", "S"), ("tuğu", "S"), ("tüğü", "S"),
        # yapim ekleri (bilimsel -> bilim, futbolcu -> futbol)
        ("sel", "S"), ("sal", "S"),
        ("cı", "S"), ("ci", "S"), ("cu", "S"), ("cü", "S"),
        ("çı", "S"), ("çi", "S"), ("çu", "S"), ("çü", "S"),
        ("lık", "S"), ("lik", "S"), ("luk", "S"), ("lük", "S"),
        ("lı", "S"), ("li", "S"), ("lu", "S"), ("lü", "S"),
        ("sız", "S"), ("siz", "S"), ("suz", "S"), ("süz", "S"),
        ("ca", "S"), ("ce", "S"), ("ça", "S"), ("çe", "S"),
    ]

    UYUMSUZ_EKLER = {"yor", "ki", "ken", "yken"}
    # edilgen eki kisa koklerde isim sonlariyla karisiyor (kızıl -> kız), sadece uzun koklerde ayiriyoruz
    EDILGEN_EKLER = {"ıl", "il", "ul", "ül"}
    YUMUSAMA = {"b": "p", "c": "ç", "d": "t", "ğ": "k", "g": "k"}
    # Unlu dusmesi (sehir -> sehr-i): iki unsuzle biten govdeye uyumlu dar unlu geri konur
    DAR_UNLULER = {"a": "ı", "ı": "ı", "o": "u", "u": "u", "e": "i", "i": "i", "ö": "ü", "ü": "ü"}
    # Kurala uymayan alintilar
    DUSEN_UNLU_ISTISNALARI = {"nakl": "nakil", "haps": "hapis", "kayb": "kayıp", "kayd": "kayıt",
                              "nakd": "nakit", "vakt": "vakit", "lütf": "lütuf"}
    # Unlu dusmesi kokle ilk ek arasinda olur. Bu hal ekleri iyelikten sonra geldigi icin
    # atilinca hala kok sinirindayiz ("akl-im-dan"); yapim eki ya da ikinci bir iyelik eki
    # atildiysa oradaki unsuz cifti tesadufidir ("etki-si" -> "etk" -> "etik" olmamali).
    KOK_SINIRI_EKLERI = {"da", "de", "ta", "te", "dan", "den", "tan", "ten",
                         "nda", "nde", "ndan", "nden", "a", "e", "ya", "ye", "na", "ne",
                         "ı", "i", "u", "ü", "yı", "yi", "yu", "yü", "nı", "ni", "nu", "nü",
                         "la", "le", "yla", "yle", "nın", "nin", "nun", "nün", "ki"}

    def __init__(self, en_kisa_kok=2):
        self.en_kisa_kok = en_kisa_kok
        self._onbellek = {}

    def adaylar(self, kelime):
        """Kelimenin olasi tum kok adaylari."""
        return self._coz(kelime)[0]

    def dusmeli_adaylar(self, kelime):
        """Unlu dusmesi geri konarak uretilen adaylar; baska kelimeye denk gelebilir (atki -> atik)."""
        return self._coz(kelime)[1]

    def _coz(self, kelime):
        if kelime in self._onbellek:
            return self._onbellek[kelime]

        bulunan, dusmeli = {kelime}, set()
        islenecek = [(kelime, True)]    # (bicim, hala kok sinirinda miyiz)
        sira = 0
        while sira < len(islenecek):
            parca, sinirda = islenecek[sira]
            sira += 1
            for ek, tur in self.EKLER:
                if not parca.endswith(ek) or len(parca) - len(ek) < self.en_kisa_kok:
                    continue
                kok = parca[:-len(ek)]
                if not self._ek_uygun(kok, ek, tur):
                    continue
                yeniler = [(y, parca in dusmeli) for y in self._kok_bicimleri(kok, ek, tur)]
                # unlu dusmesi sadece unluyle baslayan bir ek dogrudan koke geldiginde olur
                if tur == "U" and sinirda:
                    acik = self.unlu_geri_koy(kok)
                    if acik:
                        yeniler.append((acik, True))
                kok_sinirinda = sinirda and ek in self.KOK_SINIRI_EKLERI
                for yeni, dusmeden in yeniler:
                    if yeni not in bulunan:
                        bulunan.add(yeni)
                        if dusmeden:
                            dusmeli.add(yeni)
                        islenecek.append((yeni, kok_sinirinda))

        # "et" ile kurulan bilesik fiiller: fetih + et -> fethet, kesif + et -> kesfet
        for aday in list(bulunan):
            if aday.endswith("et"):
                acik = self.unlu_geri_koy(aday[:-2])
                if acik and acik not in bulunan:
                    bulunan.add(acik)
                    dusmeli.add(acik)

        sonuc = (frozenset(bulunan), frozenset(dusmeli))
        self._onbellek[kelime] = sonuc
        return sonuc

    def _ek_uygun(self, kok, ek, tur):
        if son_unlu(kok) is None:
            return False
        if ek in self.EDILGEN_EKLER and len(kok) < 4:
            return False
        kok_unluyle_biter = kok[-1] in UNLULER
        if tur == "U" and kok_unluyle_biter:
            return False
        if tur == "K" and not kok_unluyle_biter:
            return False
        if ek in self.UYUMSUZ_EKLER or unlu_uyumlu(kok, ek):
            return True
        # alinti kelimeler uyuma uymayabiliyor (alkol-ü); kisa koklerde izin vermiyoruz,
        # yoksa "kanun" -> "kan" gibi hatalar cikiyor
        return len(kok) >= 4

    @classmethod
    def unlu_geri_koy(cls, govde):
        """"sehr" -> "sehir", "akl" -> "akil". Govde iki unsuzle bitmiyorsa None doner."""
        if govde in cls.DUSEN_UNLU_ISTISNALARI:
            return cls.DUSEN_UNLU_ISTISNALARI[govde]
        if len(govde) < 3 or govde[-1] in UNLULER or govde[-2] in UNLULER:
            return None
        onceki = son_unlu(govde)
        return govde[:-1] + cls.DAR_UNLULER[onceki] + govde[-1] if onceki else None

    def _kok_bicimleri(self, kok, ek, tur):
        bicimler = [kok]
        if tur == "U":
            if kok[-1] in self.YUMUSAMA:
                bicimler.append(kok[:-1] + self.YUMUSAMA[kok[-1]])
        # unlu daralmasi: ertele-yor -> erteliyor, basla-yor -> basliyor
        if ek == "yor" and len(kok) >= 3 and kok[-1] in "ıiuü":
            govde = kok[:-1]
            bicimler.append(govde + ("a" if son_unlu(govde) in KALIN_UNLULER else "e"))
        return bicimler

    def genel_kok(self, kelime, en_az=4):
        """Ogrenme icin kullanilir: en az `en_az` harfli en kisa aday."""
        uygun = [a for a in self.adaylar(kelime) if len(a) >= en_az]
        return min(uygun, key=len) if uygun else kelime


class SikiEslestirici:
    """Kisa kelimeler (kan, çay, göz) serbest ek atmada cok hata verdigi icin sadece
    cogul + iyelik + hal zincirlerine izin verilir."""

    def __init__(self):
        self._unluden_sonra = self._zincirleri_olustur(unlu_ile_biter=True)
        self._unsuzden_sonra = self._zincirleri_olustur(unlu_ile_biter=False)

    @staticmethod
    def _zincirleri_olustur(unlu_ile_biter):
        iyelik_unlu = ["m", "n", "sı", "si", "su", "sü", "mız", "miz", "muz", "müz",
                       "nız", "niz", "nuz", "nüz"]
        iyelik_unsuz = ["ım", "im", "um", "üm", "ın", "in", "un", "ün", "ı", "i", "u", "ü",
                        "ımız", "imiz", "umuz", "ümüz", "ınız", "iniz", "unuz", "ünüz"]
        hal_unlu = ["yı", "yi", "yu", "yü", "ya", "ye", "da", "de", "dan", "den",
                    "nın", "nin", "nun", "nün", "yla", "yle", "ki", "daki", "deki"]
        hal_unsuz = ["ı", "i", "u", "ü", "a", "e", "da", "de", "ta", "te", "dan", "den",
                     "tan", "ten", "ın", "in", "un", "ün", "la", "le", "ki",
                     "daki", "deki", "taki", "teki"]
        hal_zamir_n = ["nı", "ni", "nu", "nü", "na", "ne", "nda", "nde", "ndan", "nden",
                       "nın", "nin", "nun", "nün", "yla", "yle"]
        ucuncu_teklik = {"ı", "i", "u", "ü", "sı", "si", "su", "sü"}

        zincirler = set()
        for cogul in ("", "lar", "ler"):
            taban_unlu = unlu_ile_biter and not cogul
            zincirler.add(cogul)
            for hal in (hal_unlu if taban_unlu else hal_unsuz):
                zincirler.add(cogul + hal)
            for iyelik in (iyelik_unlu if taban_unlu else iyelik_unsuz):
                zincirler.add(cogul + iyelik)
                if iyelik in ucuncu_teklik:
                    sonraki = hal_zamir_n
                else:
                    sonraki = hal_unsuz
                for hal in sonraki:
                    zincirler.add(cogul + iyelik + hal)
        return zincirler

    def eslesir(self, kok, kelime):
        if not kelime.startswith(kok):
            return False
        kalan = kelime[len(kok):]
        if not kalan:
            return True
        zincirler = self._unluden_sonra if kok[-1] in UNLULER else self._unsuzden_sonra
        return kalan in zincirler and unlu_uyumlu(kok, kalan)


# Kendinden onceki kelimenin metnin asil konusu oldugunu gosteren kaliplar
# ("bitki konusunda bilgi almak istiyorum", "tarih hakkinda", "yapay zeka ile ilgili")
ODAK_KALIPLARI = {"hakkında", "hakkındaki", "konusunda", "konusundaki", "konusu", "konusuyla",
                  "konulu", "üzerine", "dair", "ilişkin", "ilgili",
                  # tanim sorulari: "X nedir", "X kimdir"
                  "nedir", "nelerdir", "kimdir"}
# Bu kaliplarla baslayan kelimeler de ayni isi goruyor ("tatil yeri onerir misin", "merak ediyorum")
ODAK_KOKLERI = ("merak", "öner", "tavsiye")
# Kendinden SONRAKI kelimenin konu oldugunu gosteren soru kelimesi ("hangi spor dalina").
# "hangi ulkelere", "hangi donemde" gibi genel soru isimleri bu kurala dahil degil.
ODAK_SORU = "hangi"
GENEL_SORU_ISIMLERI = {"ülke", "dönem", "tarih", "şehir", "bölge", "yaş", "zaman", "yer", "kıta"}
# "... ama ben asil X ile ilgileniyorum": zitlik bagacindan onceki kisim arka plan sayilir
ZITLIK_BAGLACLARI = {"ama", "fakat", "ancak", "lakin", "aslında", "oysa"}
BAGLACLAR = {"ve", "veya", "ile", "ya", "da", "de"}
# Kendinden SONRA konunun geldigini gosteren ifadeler: "asil ilgilendigim konu, X"
ILERI_ODAK_KELIMELERI = {"ilgilendiğim", "ilgilendiğimiz", "istediğim", "istediğimiz", "sorum",
                         "sorumuz", "merakım", "derdim", "asıl", "esas"}
# Kendinden ONCEKI kismin arka plan oldugunu gosteren fiiller: "sanat tarihinden bahsettim"
ARKA_PLAN_KOKLERI = ("bahset", "bahsed", "değin", "konuştu", "konuşul")
# Tamlamada konuyu degil niteligini soyleyen isimler: "kuruyemis markalari", "yag cesidi"
NITELIK_ISIMLERI = {"marka", "çeşit", "tür", "model", "fiyat", "şirket", "isim", "özellik",
                    "fayda", "zarar", "örnek"}
# belirtisiz isim tamlamasinin ikinci kelimesindeki iyelik ekleri (kedi mamasi, dna mutasyonlari)
IYELIK_EKLERI = ("ları", "leri", "sı", "si", "su", "sü", "ı", "i", "u", "ü")

# Rakam-islem-rakam kalibi ("2+2"): konu kelimesi olmasa da aritmetik soru oldugunu gosterir.
# Cikarma ve bolme isaretleri skor/tarih yazimlariyla karistigi icin ("2-1", "12/05") listede yok.
ARITMETIK = re.compile(r"\d+\s*[+*×÷^]\s*\d+")
ARITMETIK_ANAHTARI = "aritmetik_işlem"


class OzellikCikarici:
    """
    Konu sozlugundeki kelime ve kelime gruplarini metinde arar; her eslesme bir ozelliktir.
    Kelime gruplari "_" ile birlestirilir ("kara delik" -> "kara_delik").
    """

    def __init__(self, metin_isleyici=None, kok_bulucu=None):
        self.metin = metin_isleyici or TurkceMetin()
        self.kok = kok_bulucu or KokBulucu()
        self.siki = SikiEslestirici()
        self._normal = set()        # serbest ek atilarak eslesen tekil kelimeler
        self._siki = set()          # sadece cekim ekleriyle eslesen tekil kelimeler
        self._gruplar = {}          # ilk kelime -> [(kelimeler, anahtar), ...]

    def sozluge_ekle(self, ifade):
        """Sozluge bir kelime/kelime grubu ekler ve ozellik anahtarini dondurur."""
        ifade = self.metin.kucult(ifade.strip())
        zorla_siki = ifade.startswith("!")
        ifade = ifade.lstrip("!")
        parcalar = tuple(self.metin.kelimeler(ifade))
        # metinde durak kelimeler atildigi icin gruplardan da atiliyor, yoksa "suc ve ceza" eslesmez
        if len(parcalar) > 1:
            parcalar = tuple(k for k in parcalar if k not in DURAK_KELIMELER)
        if not parcalar:
            return None

        if len(parcalar) == 1:
            kelime = parcalar[0]
            if zorla_siki or len(kelime) <= 3:
                self._siki.add(kelime)
            else:
                self._normal.add(kelime)
            return kelime

        anahtar = "_".join(parcalar)
        liste = self._gruplar.setdefault(parcalar[0], [])
        if (parcalar, anahtar) not in liste:
            liste.append((parcalar, anahtar))
            liste.sort(key=lambda x: -len(x[0]))   # uzun grup once denensin
        return anahtar

    def _kelime_eslesir(self, sozluk_kelimesi, kelime):
        if len(sozluk_kelimesi) <= 3:
            return self.siki.eslesir(sozluk_kelimesi, kelime)
        return sozluk_kelimesi in self.kok.adaylar(kelime)

    def _tekil_eslesme(self, kelime):
        # serbest eslesmeler: kok adaylari ile sozlugun kesisimi
        adaylar = [a for a in self.kok.adaylar(kelime) if a in self._normal]
        # unlu dusmesiyle uretilen kokler cakisabiliyor (atki -> atik), once duz eslesmelere bakilir
        dusmeli = self.kok.dusmeli_adaylar(kelime)
        adaylar = [a for a in adaylar if a not in dusmeli] or adaylar
        # siki eslesmeler: kelimenin baslangicinda sozlukte olan kisa kokler
        istisna = KISA_KOK_ISTISNALARI.intersection(self.kok.adaylar(kelime))
        if istisna:
            # istisna kokten kisa adaylar yanlis eslesmedir (kazandı -> kaza degil)
            en_kisa = min(len(k) for k in istisna)
            adaylar = [a for a in adaylar if len(a) >= en_kisa]
            return max(adaylar, key=len) if adaylar else None
        for i in range(2, len(kelime) + 1):
            on = kelime[:i]
            if on in self._siki and self.siki.eslesir(on, kelime):
                adaylar.append(on)
        # "tatlı" hem "tat" hem "tatlı" ile eslesir, en uzunu daha anlamli
        return max(adaylar, key=len) if adaylar else None

    def _grup_eslesmesi(self, kelimeler, i):
        kelime = kelimeler[i]
        ilk_adaylar = set(self.kok.adaylar(kelime))
        ilk_adaylar.update(kelime[:j] for j in range(2, 4))
        for ilk in ilk_adaylar:
            for parcalar, anahtar in self._gruplar.get(ilk, ()):
                son = i + len(parcalar)
                if son > len(kelimeler):
                    continue
                if all(self._kelime_eslesir(p, kelimeler[i + j])
                       or (j > 0 and len(parcalar[0]) >= 4 and self._yakin_mi(p, kelimeler[i + j]))
                       for j, p in enumerate(parcalar)):
                    return anahtar, len(parcalar)
        return None, 0

    @staticmethod
    def _tek_harf_farkli(a, b):
        """a ile b arasinda tek harf ekleme, silme ya da degistirme farki var mi"""
        if abs(len(a) - len(b)) > 1 or a == b:
            return False
        if len(a) > len(b):
            a, b = b, a
        i = 0
        while i < len(a) and a[i] == b[i]:
            i += 1
        return a[i + 1:] == b[i + 1:] if len(a) == len(b) else a[i:] == b[i + 1:]

    def _yakin_mi(self, sozluk_kelimesi, kelime):
        """
        Yazim hatasi toleransi ("bilgisayar muhendsligi"). Sadece kelime gruplarinin uzun
        kelimelerinde izin verilir; kisa kelimede tek harf farki baska bir kelime demektir
        ("ise yariyor" / "is ariyor").
        """
        if len(sozluk_kelimesi) < self.YAZIM_TOLERANSI_UZUNLUGU:
            return False
        return any(self._tek_harf_farkli(aday, sozluk_kelimesi) for aday in self.kok.adaylar(kelime)
                   if len(aday) >= self.YAZIM_TOLERANSI_UZUNLUGU - 1)

    ODAK_AGIRLIGI = 3
    YAZIM_TOLERANSI_UZUNLUGU = 8
    # metinde bir odak kalibi varsa geri kalan kelimeler arka plan sayilip daha az agirlik alir
    ARKA_PLAN_AGIRLIGI = 0.5

    def _iyelikli_mi(self, kelime):
        """Kelime iyelik eki aliyor mu? Sonrasinda hal eki olabilir: "dili", "diliyle", "mamasina" """
        if kelime.endswith(IYELIK_EKLERI):
            return True
        return any(kelime.endswith(ek) and kelime[:-len(ek)].endswith(IYELIK_EKLERI)
                   for ek in self.HAL_EKLERI if len(kelime) - len(ek) >= 3)

    @staticmethod
    def _kalip_mi(kelime):
        return kelime in ODAK_KALIPLARI or kelime.startswith(ODAK_KOKLERI)

    def _odaklari_bul(self, tum, eslesmeler):
        """
        eslesmeler: [(anahtar, baslangic, bitis)]. (odak, zayif) sira numaralarini dondurur.
        Her kalip kendisine en yakin eslesmeyi isaretler: "uygun fiyatli otel onerir misin"
        -> otel (fiyat degil).
        """
        odak, zayif = set(), set()
        bitisler = {bit: n for n, (_, _, bit) in enumerate(eslesmeler)}
        eslesme_ici = {k for _, bas, bit in eslesmeler for k in range(bas, bit + 1)}
        for m, kelime in enumerate(tum):
            if m in eslesme_ici:        # "kitap onerisi" gibi zaten bir anahtar kelimenin parcasi
                continue
            sonraki = tum[m + 1] if m + 1 < len(tum) else ""
            # "ile ilgili", "ile ilgileniyorum", "X nasil bir sirket"
            kalip = (self._kalip_mi(kelime) or (kelime == "ile" and sonraki.startswith("ilgil"))
                     or (kelime == "nasıl" and sonraki == "bir"))
            if kalip:
                # kaliptan hemen onceki ya da arada tek kelime olan eslesme
                for mesafe in (1, 2):
                    if m - mesafe in bitisler:
                        odak.add(bitisler[m - mesafe])
                        break
            elif kelime == ODAK_SORU:
                for n, (anahtar, bas, _) in enumerate(eslesmeler):
                    if bas == m + 1:
                        # "hangi spor" konu, "hangi ulkede" ise konunun bir ozelligini soruyor
                        (zayif if anahtar in GENEL_SORU_ISIMLERI else odak).add(n)
            elif kelime == "bu" and sonraki.startswith("konu"):
                # "... IPSec ne ise yariyor, bu konulari ogrenebilecegim kitap": onceki kisim konu
                odak.update(n for n, (_, _, bit) in enumerate(eslesmeler) if bit < m)

        # Odak oncekilere iki durumda yayilir: arada sadece baglac varsa ("X ve Y hakkinda")
        # ya da bitisik ve iyelik ekliyse ("Dede Korkut hikayeleri"). "uygun fiyatli otel"
        # gibi iyelik eki olmayan bitisik kelimelere yayilmaz.
        for n in sorted(odak, reverse=True):
            while n > 0 and n - 1 not in odak:
                arasi = tum[eslesmeler[n - 1][2] + 1:eslesmeler[n][1]]
                tamlama = not arasi and self._iyelikli_mi(tum[eslesmeler[n][2]])
                if not tamlama and not (arasi and all(k in BAGLACLAR for k in arasi)):
                    break
                n -= 1
                odak.add(n)
        return odak, zayif - odak

    @staticmethod
    def _ileri_odak_mi(tum, m):
        kelime, onceki = tum[m], tum[m - 1] if m > 0 else ""
        return (kelime in ILERI_ODAK_KELIMELERI
                or (kelime in ("ettiğim", "ettiğimiz") and onceki == "merak")
                or (kelime.startswith("çeken") and onceki.startswith("ilgi")))

    @staticmethod
    def _arka_plan_fiili_mi(tum, m):
        kelime, onceki = tum[m], tum[m - 1] if m > 0 else ""
        return kelime.startswith(ARKA_PLAN_KOKLERI) or (onceki == "söz" and kelime.startswith(("et", "ed")))

    def _cumle_rolleri(self, tum, cumle_no, eslesmeler):
        """
        Cumle duzeyinde (odak, arka plan) sira numaralarini bulur: ileri odak ifadesinden
        cumle sonuna kadarki eslesmeler odak, "bahsettim" gibi fiillerden oncekiler arka plandir.
        """
        odak, arka = set(), set()
        for no in set(cumle_no):
            yerler = [m for m, c in enumerate(cumle_no) if c == no]
            ileri = [m for m in yerler if self._ileri_odak_mi(tum, m)]
            if ileri:
                bolge = [n for n, (_, b, _) in enumerate(eslesmeler)
                         if b > ileri[-1] and cumle_no[b] == no]
                odak.update(bolge)
            for m in yerler:
                if self._arka_plan_fiili_mi(tum, m):
                    arka.update(n for n, (_, b, bit) in enumerate(eslesmeler)
                                if bit < m and cumle_no[b] == no)
        return odak, arka - odak

    # Sorguda kelimenin dogal halini kullanmak icin atilan ekler. 3. kisi iyelik ve cogul
    # ekleri kaliyor, tamlamanin parcasi oluyorlar: "telif haklarina" -> "telif haklari"
    HAL_EKLERI = ("ndan", "nden", "nın", "nin", "nun", "nün", "nda", "nde", "yla", "yle", "dan", "den",
                  "tan", "ten", "ın", "in", "un", "ün", "da", "de", "ta", "te", "ya", "ye", "na", "ne",
                  "la", "le", "a", "e")
    KISI_EKLERI = ("ımız", "imiz", "umuz", "ümüz", "ınız", "iniz", "unuz", "ünüz", "mız", "miz", "muz",
                   "müz", "nız", "niz", "nuz", "nüz", "ım", "im", "um", "üm", "m")

    BELIRTME_EKLERI = ("nı", "ni", "nu", "nü", "yı", "yi", "yu", "yü", "ı", "i", "u", "ü")

    def _yuzey(self, kelimeler, kokler):
        """
        Eslesen ifadenin sorguda kullanilacak hali: son kelime iyelik ekini korur ("telif
        haklari"), oncekilerden belirtme eki atilir. Metindeki bicim sozluk kokuyle
        baslamiyorsa (fethedildi / fetih) kok kullanilir, cekimli fiil sorguya uymaz.
        """
        sonuc = []
        for i, (kelime, kok) in enumerate(zip(kelimeler, kokler)):
            if not kelime.startswith(kok):
                sonuc.append(kok)
                continue
            kelime = self._yalin(kelime, kok)
            if i < len(kelimeler) - 1:
                kelime = next((kelime[:-len(ek)] for ek in self.BELIRTME_EKLERI
                               if kelime.endswith(ek) and kelime[:-len(ek)].startswith(kok)), kelime)
            sonuc.append(kelime)
        return " ".join(sonuc)

    def _yalin(self, kelime, kok):
        """Hal ve kisi ekini atar; kalan kisim sozluk kokuyle baslamiyorsa eke dokunulmaz."""
        for ekler in (self.HAL_EKLERI, self.KISI_EKLERI):
            for ek in ekler:
                if kelime.endswith(ek) and kelime[:-len(ek)].startswith(kok):
                    kelime = kelime[:-len(ek)]
                    break
        return kelime

    def cikar(self, metin):
        """(ozellik sayaci, taninmayan kelimeler, yuzey bicimleri) dondurur."""
        tum, cumle_no = [], []
        for no, cumle in enumerate(self.metin.cumleler(metin)):
            tum.extend(cumle)
            cumle_no.extend([no] * len(cumle))
        # icerik kelimelerinin tum kelimeler icindeki yerleri, odak kaliplarini bulmak icin lazim
        yerler = [j for j, k in enumerate(tum) if k not in DURAK_KELIMELER]
        kelimeler = [tum[j] for j in yerler]
        kisi_adlari = KISI_ADLARI.intersection(self.metin.ozel_adlar(metin))

        bulunan = []        # (ozellik, baslangic, bitis)
        taninmayan = []
        i = 0
        while i < len(kelimeler):
            anahtar, uzunluk = self._grup_eslesmesi(kelimeler, i)
            if not anahtar:
                anahtar, uzunluk = self._tekil_eslesme(kelimeler[i]), 1
                if anahtar in kisi_adlari:
                    anahtar = None      # konu kelimesi degil, kisi adi
            if anahtar:
                bulunan.append((anahtar, yerler[i], yerler[i + uzunluk - 1]))
            elif not kelimeler[i].isdigit():
                taninmayan.append(kelimeler[i])
            i += uzunluk

        odaklar, zayiflar = self._odaklari_bul(tum, bulunan)
        cumle_odak, arka_fiil = self._cumle_rolleri(tum, cumle_no, bulunan)
        odaklar |= cumle_odak
        zayiflar |= arka_fiil - odaklar
        # nitelik ismi tamlamanin basindaysa odak ve agirlik onundeki niteleyiciye gecer
        for n in range(1, len(bulunan)):
            anahtar, bas, bit = bulunan[n]
            if (anahtar in NITELIK_ISIMLERI and bulunan[n - 1][2] == bas - 1
                    and self._iyelikli_mi(tum[bit])):
                if n in odaklar:
                    odaklar.discard(n)
                    odaklar.add(n - 1)
                zayiflar.add(n)
        # zitlik bagacindan sonra odak varsa oncesi arka plandir ("... ama ben X ile
        # ilgileniyorum"); odak yoksa sonrasi ayni konunun devamidir, dokunulmuyor
        zitlik = max((j for j, k in enumerate(tum) if k in ZITLIK_BAGLACLARI), default=-1)
        arka_plan = set()
        if any(bulunan[n][1] > zitlik for n in odaklar):
            arka_plan = {n for n, (_, bas, _) in enumerate(bulunan) if bas < zitlik}
            odaklar -= arka_plan

        yuzeyler = {}
        for anahtar, bas, bit in bulunan:
            if anahtar not in yuzeyler:
                yuzeyler[anahtar] = self._yuzey(tum[bas:bit + 1], anahtar.split("_"))

        # kelimeyle degil kalipla taninan ozellik; sozlukte karsiligi yoksa siniflandirici eler
        if ARITMETIK.search(metin):
            yuzeyler.setdefault(ARITMETIK_ANAHTARI, "aritmetik işlem")

        ozellikler = Counter()
        if ARITMETIK_ANAHTARI in yuzeyler:
            ozellikler[ARITMETIK_ANAHTARI] += 1
        for n, (anahtar, _, _) in enumerate(bulunan):
            if n in odaklar:
                ozellikler[anahtar] += self.ODAK_AGIRLIGI
            elif n in arka_plan or n in zayiflar or odaklar:
                ozellikler[anahtar] += self.ARKA_PLAN_AGIRLIGI
            else:
                ozellikler[anahtar] += 1
        return ozellikler, taninmayan, yuzeyler
