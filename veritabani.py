# Ad Soyad : Bayram Bayraktar
# Tarih    : 24.09.2026
#
# SQLite veritabani islemleri. Her program calismasi bir "oturum" olarak kaydedilir.

import sqlite3
from datetime import datetime

TABLOLAR = """
CREATE TABLE IF NOT EXISTS oturumlar (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    baslangic   TEXT NOT NULL,
    bitis       TEXT,
    sohbet_konusu TEXT
);

CREATE TABLE IF NOT EXISTS metinler (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    oturum_id   INTEGER NOT NULL REFERENCES oturumlar(id),
    metin       TEXT NOT NULL,
    genel_konu  TEXT,
    guven       REAL,
    anahtar_kelimeler TEXT,
    sohbet_konusu TEXT,
    tarih       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS metin_alt_konulari (
    metin_id    INTEGER NOT NULL REFERENCES metinler(id),
    genel_konu  TEXT NOT NULL,
    alt_konu    TEXT NOT NULL,
    puan        REAL
);

CREATE TABLE IF NOT EXISTS arama_sorgulari (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    oturum_id   INTEGER NOT NULL REFERENCES oturumlar(id),
    metin_id    INTEGER REFERENCES metinler(id),
    sorgu       TEXT NOT NULL,
    anahtar_sorgu TEXT,
    sorgu_turu  TEXT,
    tarih       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS arama_sonuclari (
    sorgu_id    INTEGER NOT NULL REFERENCES arama_sorgulari(id),
    kaynak      TEXT,
    baslik      TEXT,
    adres       TEXT,
    ozet        TEXT
);

CREATE INDEX IF NOT EXISTS metin_oturum ON metinler(oturum_id);
CREATE INDEX IF NOT EXISTS sorgu_oturum ON arama_sorgulari(oturum_id);
CREATE INDEX IF NOT EXISTS sonuc_sorgu ON arama_sonuclari(sorgu_id);

CREATE TABLE IF NOT EXISTS ogrenilen_kelimeler (
    kelime      TEXT NOT NULL,
    genel_konu  TEXT NOT NULL,
    tarih       TEXT NOT NULL,
    PRIMARY KEY (kelime, genel_konu)
);

CREATE TABLE IF NOT EXISTS onayli_kelimeler (
    kelime TEXT NOT NULL,
    genel_konu TEXT NOT NULL,
    alt_konu TEXT NOT NULL DEFAULT '',
    tarih TEXT NOT NULL,
    PRIMARY KEY (kelime, genel_konu, alt_konu)
);

CREATE TABLE IF NOT EXISTS genel_konular (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad TEXT NOT NULL UNIQUE,
    sira INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS alt_konular (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    genel_konu_id INTEGER NOT NULL REFERENCES genel_konular(id) ON DELETE CASCADE,
    ad TEXT NOT NULL,
    sira INTEGER NOT NULL DEFAULT 0,
    UNIQUE (genel_konu_id, ad)
);
CREATE TABLE IF NOT EXISTS konu_anahtarlari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    genel_konu_id INTEGER NOT NULL REFERENCES genel_konular(id) ON DELETE CASCADE,
    alt_konu_id INTEGER REFERENCES alt_konular(id) ON DELETE CASCADE,
    anahtar TEXT NOT NULL,
    sira INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS konu_anahtar_genel_tekil
    ON konu_anahtarlari(genel_konu_id, anahtar) WHERE alt_konu_id IS NULL;
CREATE UNIQUE INDEX IF NOT EXISTS konu_anahtar_alt_tekil
    ON konu_anahtarlari(alt_konu_id, anahtar) WHERE alt_konu_id IS NOT NULL;

"""


def _simdi():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Veritabani:
    def __init__(self, yol):
        self.baglanti = sqlite3.connect(yol)
        self.baglanti.execute("PRAGMA foreign_keys = ON")
        self.baglanti.executescript(TABLOLAR)
        self.oturum_id = None

    def konu_agaci_var(self):
        return self.baglanti.execute("SELECT 1 FROM genel_konular LIMIT 1").fetchone() is not None

    def konu_agaci_verisi(self):
        sonuc = []
        for genel_id, ad in self.baglanti.execute(
                "SELECT id, ad FROM genel_konular ORDER BY sira, id").fetchall():
            genel_anahtarlar = [r[0] for r in self.baglanti.execute(
                "SELECT anahtar FROM konu_anahtarlari "
                "WHERE genel_konu_id=? AND alt_konu_id IS NULL ORDER BY sira, id", (genel_id,))]
            altlar = []
            for alt_id, alt_ad in self.baglanti.execute(
                    "SELECT id, ad FROM alt_konular WHERE genel_konu_id=? ORDER BY sira, id",
                    (genel_id,)).fetchall():
                anahtarlar = [r[0] for r in self.baglanti.execute(
                    "SELECT anahtar FROM konu_anahtarlari WHERE alt_konu_id=? ORDER BY sira, id", (alt_id,))]
                altlar.append((alt_ad, anahtarlar))
            sonuc.append((ad, genel_anahtarlar, altlar))
        return sonuc

    def konu_agaci_kaydet(self, agac):
        """TXT'den ilk yuklenen agaci konu tablolarina aktarir."""
        with self.baglanti:
            self.baglanti.execute("DELETE FROM genel_konular")
            for genel_sira, genel in enumerate(agac.genel_konular.values()):
                genel_id = self.baglanti.execute(
                    "INSERT INTO genel_konular (ad, sira) VALUES (?, ?)", (genel.ad, genel_sira)
                ).lastrowid
                self.baglanti.executemany(
                    "INSERT INTO konu_anahtarlari (genel_konu_id, anahtar, sira) VALUES (?, ?, ?)",
                    [(genel_id, kelime, i) for i, kelime in enumerate(genel.ozellikler)])
                for alt_sira, alt in enumerate(genel.alt_konular):
                    alt_id = self.baglanti.execute(
                        "INSERT INTO alt_konular (genel_konu_id, ad, sira) VALUES (?, ?, ?)",
                        (genel_id, alt.ad, alt_sira)).lastrowid
                    self.baglanti.executemany(
                        "INSERT INTO konu_anahtarlari (genel_konu_id, alt_konu_id, anahtar, sira) "
                        "VALUES (?, ?, ?, ?)",
                        [(genel_id, alt_id, kelime, i) for i, kelime in enumerate(alt.ozellikler)])

    def konu_ekle(self, ad, anahtarlar):
        if not ad.strip() or not anahtarlar:
            raise ValueError("Konu adi ve en az bir anahtar kelime gerekli")
        with self.baglanti:
            sira = self.baglanti.execute("SELECT COALESCE(MAX(sira), -1)+1 FROM genel_konular").fetchone()[0]
            genel_id = self.baglanti.execute(
                "INSERT INTO genel_konular (ad, sira) VALUES (?, ?)", (ad.strip(), sira)).lastrowid
            self._anahtar_ekle(genel_id, None, anahtarlar)

    def alt_konu_ekle(self, genel_ad, alt_ad, anahtarlar):
        if not alt_ad.strip() or not anahtarlar:
            raise ValueError("Alt konu adi ve en az bir anahtar kelime gerekli")
        with self.baglanti:
            genel_id = self._genel_id(genel_ad)
            sira = self.baglanti.execute(
                "SELECT COALESCE(MAX(sira), -1)+1 FROM alt_konular WHERE genel_konu_id=?", (genel_id,)
            ).fetchone()[0]
            alt_id = self.baglanti.execute(
                "INSERT INTO alt_konular (genel_konu_id, ad, sira) VALUES (?, ?, ?)",
                (genel_id, alt_ad.strip(), sira)).lastrowid
            self._anahtar_ekle(genel_id, alt_id, anahtarlar)

    def anahtar_ekle(self, genel_ad, alt_ad, anahtarlar):
        with self.baglanti:
            genel_id = self._genel_id(genel_ad)
            alt_id = self._alt_id(genel_id, alt_ad) if alt_ad else None
            return self._anahtar_ekle(genel_id, alt_id, anahtarlar)

    def _anahtar_ekle(self, genel_id, alt_id, anahtarlar):
        sutun, kimlik = ("alt_konu_id", alt_id) if alt_id is not None else ("genel_konu_id", genel_id)
        sira = self.baglanti.execute(
            f"SELECT COALESCE(MAX(sira), -1)+1 FROM konu_anahtarlari WHERE {sutun}=?", (kimlik,)
        ).fetchone()[0]
        eklenen = 0
        for kelime in dict.fromkeys(anahtarlar):
            if not kelime:
                continue
            cursor = self.baglanti.execute(
                "INSERT OR IGNORE INTO konu_anahtarlari (genel_konu_id, alt_konu_id, anahtar, sira) "
                "VALUES (?, ?, ?, ?)", (genel_id, alt_id, kelime, sira))
            eklenen += cursor.rowcount
            sira += cursor.rowcount
        if not eklenen:
            raise ValueError("Yeni anahtar kelime eklenmedi; hepsi zaten kayıtlı olabilir")
        return eklenen

    def anahtar_sil(self, genel_ad, alt_ad, anahtarlar):
        with self.baglanti:
            genel_id = self._genel_id(genel_ad)
            alt_id = self._alt_id(genel_id, alt_ad) if alt_ad else None
            silinen = 0
            for kelime in set(anahtarlar):
                if alt_id is None:
                    cur = self.baglanti.execute(
                        "DELETE FROM konu_anahtarlari WHERE genel_konu_id=? AND alt_konu_id IS NULL AND anahtar=?",
                        (genel_id, kelime))
                else:
                    cur = self.baglanti.execute(
                        "DELETE FROM konu_anahtarlari WHERE alt_konu_id=? AND anahtar=?", (alt_id, kelime))
                silinen += cur.rowcount
            if not silinen:
                raise ValueError("Silinecek anahtar kelime bulunamadi")
            return silinen

    def alt_konu_sil(self, genel_ad, alt_ad):
        with self.baglanti:
            genel_id = self._genel_id(genel_ad)
            alt_id = self._alt_id(genel_id, alt_ad)
            self.baglanti.execute("DELETE FROM alt_konular WHERE id=?", (alt_id,))

    def konu_sil(self, genel_ad):
        with self.baglanti:
            genel_id = self._genel_id(genel_ad)
            self.baglanti.execute("DELETE FROM genel_konular WHERE id=?", (genel_id,))

    def _genel_id(self, ad):
        row = self.baglanti.execute("SELECT id FROM genel_konular WHERE ad=?", (ad.strip(),)).fetchone()
        if row is None:
            raise ValueError(f"Genel konu bulunamadi: {ad}")
        return row[0]

    def _alt_id(self, genel_id, ad):
        row = self.baglanti.execute(
            "SELECT id FROM alt_konular WHERE genel_konu_id=? AND ad=?", (genel_id, ad.strip())).fetchone()
        if row is None:
            raise ValueError(f"Alt konu bulunamadi: {ad}")
        return row[0]

    def oturum_baslat(self):
        imlec = self.baglanti.execute("INSERT INTO oturumlar (baslangic) VALUES (?)", (_simdi(),))
        self.baglanti.commit()
        self.oturum_id = imlec.lastrowid

    def oturum_bitir(self, sohbet_konusu):
        self.baglanti.execute("UPDATE oturumlar SET bitis = ?, sohbet_konusu = ? WHERE id = ?",
                              (_simdi(), sohbet_konusu, self.oturum_id))
        self.baglanti.commit()

    def metin_kaydet(self, sonuc, sohbet_konusu):
        imlec = self.baglanti.execute(
            "INSERT INTO metinler (oturum_id, metin, genel_konu, guven, anahtar_kelimeler, "
            "sohbet_konusu, tarih) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (self.oturum_id, sonuc.metin, sonuc.genel_konu, round(sonuc.guven, 4),
             ", ".join(sonuc.anahtar_kelimeler), sohbet_konusu, _simdi()))
        metin_id = imlec.lastrowid
        self.baglanti.executemany(
            "INSERT INTO metin_alt_konulari (metin_id, genel_konu, alt_konu, puan) VALUES (?, ?, ?, ?)",
            [(metin_id, alt.genel_konu.ad, alt.ad, round(puan, 4)) for alt, puan in sonuc.alt_konular])
        self.baglanti.commit()
        return metin_id

    def arama_kaydet(self, metin_id, sorgu, sonuclar):
        imlec = self.baglanti.execute(
            "INSERT INTO arama_sorgulari (oturum_id, metin_id, sorgu, anahtar_sorgu, sorgu_turu, tarih) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (self.oturum_id, metin_id, sorgu.dogal, sorgu.anahtar, sorgu.tur, _simdi()))
        self.baglanti.executemany(
            "INSERT INTO arama_sonuclari (sorgu_id, kaynak, baslik, adres, ozet) VALUES (?, ?, ?, ?, ?)",
            [(imlec.lastrowid, s.kaynak, s.baslik, s.adres, s.ozet) for s in sonuclar])
        self.baglanti.commit()

    def kelime_kaydet(self, kelime, genel_konu):
        self.baglanti.execute("INSERT OR IGNORE INTO ogrenilen_kelimeler VALUES (?, ?, ?)",
                              (kelime, genel_konu, _simdi()))
        self.baglanti.commit()

    def ogrenilen_kelimeler(self):
        return self.baglanti.execute("SELECT kelime, genel_konu FROM ogrenilen_kelimeler").fetchall()

    def kapat(self):
        self.baglanti.close()

    def onayli_kelime_kaydet(self, kelime, genel_konu, alt_konu=""):
        with self.baglanti:
            self.baglanti.execute("INSERT OR IGNORE INTO onayli_kelimeler VALUES (?, ?, ?, ?)",
                                  (kelime, genel_konu, alt_konu, _simdi()))

    def onayli_kelimeler(self):
        # Eski otomatik tahmin kayitlari silinmez, fakat onaylanmis sayilmaz.
        return self.baglanti.execute("SELECT kelime, genel_konu, alt_konu FROM onayli_kelimeler").fetchall()
