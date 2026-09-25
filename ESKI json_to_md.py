# -*- coding: utf-8 -*-
import eng_to_ipa as ipa_lib
import json
import os
import re
import shutil
from datetime import datetime, timedelta

import yaml

INPUT_JSON = "output.json"
ZENGIN_JSON = "output_zengin.json"
BENZER_JSON = "output_benzer.json"
OUTPUT_DIR = "content/phrasal-verbs"
INDEX_FILE = "content/phrasal-verbs-index.json"

# Yayın planı: 1108 içeriği bugünden geriye doğru yay
GUNLUK_YAYIN = 1
BASLANGIC_TARIHI = datetime.now() - timedelta(days=1108)

# Hugo teması sayfa başlığını H1 olarak basıyorsa False yap
H1_YAZ = False

# Global kayıtlar
TUM_KAYITLAR = {}
ZENGIN_DATA = {}
BENZER_DATA = {}

TR_KARAKTERLER = {
    "ç": "c", "Ç": "c",
    "ğ": "g", "Ğ": "g",
    "ı": "i", "İ": "i",
    "ö": "o", "Ö": "o",
    "ş": "s", "Ş": "s",
    "ü": "u", "Ü": "u",
}


def slugify(text):
    """'blow up | to explode' → 'blow-up'"""
    kelime = text.split("|")[0].strip().lower()
    for tr, en in TR_KARAKTERLER.items():
        kelime = kelime.replace(tr, en)
    kelime = re.sub(r"[^a-z0-9]+", "-", kelime)
    kelime = kelime.strip("-")
    return kelime or "bilinmeyen"


def tarih_hesapla(index):
    """Index'e göre ileri tarihli yayın tarihi hesaplar."""
    gun_farki = index // GUNLUK_YAYIN
    return (BASLANGIC_TARIHI + timedelta(days=gun_farki)).strftime("%Y-%m-%d")


def kelime_sinirinda_kes(metin, limit=155):
    """Metni kelime sınırından keser, ortadan kesmez."""
    if not metin:
        return ""
    if len(metin) <= limit:
        return metin
    kesik = metin[:limit].rsplit(" ", 1)[0]
    return kesik + "..."


def ipa_uret(kelime):
    """Phrasal verb'ün IPA (fonetik) karşılığını üretir."""
    pv = kelime.split("|")[0].strip().lower()
    try:
        ipa_sonuc = ipa_lib.convert(pv)
        if "*" in ipa_sonuc:
            return None
        return ipa_sonuc
    except Exception:
        return None


def iliskili_phrasal_verbler(kelime, max_adet=6):
    """Aynı ana fiille kurulan diğer phrasal verb'leri bulur."""
    bu_pv = kelime.split("|")[0].strip().lower()
    ana_fiil = bu_pv.split()[0]

    iliskili = []
    for diger_kelime in TUM_KAYITLAR:
        if diger_kelime == kelime:
            continue

        diger_pv = diger_kelime.split("|")[0].strip().lower()
        diger_ana_fiil = diger_pv.split()[0]

        if diger_ana_fiil != ana_fiil:
            continue

        if diger_pv == bu_pv:
            continue

        diger_slug = slugify(diger_kelime)
        diger_baslik = TUM_KAYITLAR[diger_kelime].get("title", diger_kelime)
        iliskili.append((diger_slug, diger_baslik))

        if len(iliskili) >= max_adet:
            break

    return iliskili


def benzer_link_bul(benzer_pv):
    """Benzer phrasal verb için slug ve başlık bulur.
    
    Returns:
        (slug, baslik) veya (None, None)
    """
    for diger_kelime in TUM_KAYITLAR:
        diger_pv = diger_kelime.split("|")[0].strip().lower()
        if diger_pv == benzer_pv.lower():
            diger_slug = slugify(diger_kelime)
            diger_baslik = TUM_KAYITLAR[diger_kelime].get("title", diger_kelime)
            return (diger_slug, diger_baslik)
    return (None, None)


def markdown_uret(kelime, veri, slug, tarih):
    """Tek bir phrasal verb kaydından Markdown içeriği üretir."""
    title = veri.get("title", "")
    short_answer = veri.get("short_answer", "")
    origin = veri.get("origin", "")
    examples = veri.get("examples", [])
    tags = veri.get("tags", [])

    # YAML frontmatter
    frontmatter = {
        "title": title,
        "description": kelime_sinirinda_kes(short_answer, 155),
        "tags": tags if tags else [],
        "phrasal_verb": kelime.split("|")[0].strip().lower(),
        "url": f"/phrasal-verbs/{slug}/",
        "date": tarih,
        "draft": False,
    }

    fm_text = yaml.dump(
        frontmatter,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
    )

    icerik = ["---", fm_text.strip(), "---", ""]

    # Başlık
    if H1_YAZ:
        icerik.append(f"# {title}")
        icerik.append("")

    # IPA (fonetik yazı)
    ipa_metin = ipa_uret(kelime)
    if ipa_metin:
        icerik.append(f"**Telaffuz:** `/{ipa_metin}/`")
        icerik.append("")

    # Köken
    if origin:
        icerik.append("## Köken ve Yapı")
        icerik.append("")
        icerik.append(origin)
        icerik.append("")

    # Örnek cümleler
    if examples:
        icerik.append("## Örnek Cümleler")
        icerik.append("")
        for i, ex in enumerate(examples, start=1):
            en = ex.get("en", "")
            tr = ex.get("tr", "")
            icerik.append(f"**{i}.** {en}")
            icerik.append("")
            icerik.append(f"*{tr}*")
            icerik.append("")

    # Zenginleştirilmiş veri
    zengin = ZENGIN_DATA.get(kelime, {})

    # Sık Yapılan Hatalar
    if zengin.get("sik_hata"):
        icerik.append("## Sık Yapılan Hatalar")
        icerik.append("")
        icerik.append(f"❌ **Yanlış:** {zengin['sik_hata']}")
        icerik.append("")
        if zengin.get("dogru_kullanim"):
            icerik.append(f"✅ **Doğru:** {zengin['dogru_kullanim']}")
            icerik.append("")

    # Eş ve Zıt Anlamlılar
    if zengin.get("benzer") or zengin.get("zit"):
        icerik.append("## Eş ve Zıt Anlamlılar")
        icerik.append("")
        if zengin.get("benzer"):
            icerik.append(f"**Benzer:** {', '.join(zengin['benzer'])}")
            icerik.append("")
        if zengin.get("zit"):
            icerik.append(f"**Zıt:** {', '.join(zengin['zit'])}")
            icerik.append("")

    # Kullanım Notu
    if zengin.get("kullanim_notu"):
        icerik.append("## Kullanım Notu")
        icerik.append("")
        icerik.append(zengin["kullanim_notu"])
        icerik.append("")

    # Benzer Phrasal Verb'ler (link + düz metin)
    benzerler = BENZER_DATA.get(kelime, [])
    if benzerler:
        icerik.append("## Benzer Phrasal Verb'ler")
        icerik.append("")
        eklenen_sluglar = set()  # Tekrar kontrolü
        for b in benzerler:
            benzer_slug, benzer_baslik = benzer_link_bul(b)
            if benzer_slug and benzer_slug not in eklenen_sluglar:
                eklenen_sluglar.add(benzer_slug)
                icerik.append(f"- [{benzer_baslik}](/phrasal-verbs/{benzer_slug}/)")
        icerik.append("")

    # İlişkili phrasal verb'ler
    iliskili = iliskili_phrasal_verbler(kelime)
    if iliskili:
        icerik.append("## İlişkili Phrasal Verb'ler")
        icerik.append("")
        for diger_slug, diger_baslik in iliskili:
            icerik.append(f"- [{diger_baslik}](/phrasal-verbs/{diger_slug}/)")
        icerik.append("")

    return "\n".join(icerik)


def main():
    global TUM_KAYITLAR, ZENGIN_DATA, BENZER_DATA

    if not os.path.exists(INPUT_JSON):
        print(f"HATA: {INPUT_JSON} bulunamadı!")
        return

    # === RERUN TEMİZLİĞİ ===
    if os.path.exists(OUTPUT_DIR):
        silinen = len([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".md")])
        shutil.rmtree(OUTPUT_DIR)
        print(f"Eski klasör temizlendi ({silinen} dosya silindi).")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    TUM_KAYITLAR = data

    # Zenginleştirilmiş veriyi yükle
    if os.path.exists(ZENGIN_JSON):
        with open(ZENGIN_JSON, "r", encoding="utf-8") as f:
            ZENGIN_DATA = json.load(f)
        print(f"Zenginleştirilmiş veri yüklendi: {len(ZENGIN_DATA)} kayıt")
    else:
        ZENGIN_DATA = {}
        print("UYARI: output_zengin.json bulunamadı.")

    # Benzer phrasal verb'leri yükle
    if os.path.exists(BENZER_JSON):
        with open(BENZER_JSON, "r", encoding="utf-8") as f:
            BENZER_DATA = json.load(f)
        print(f"Benzer phrasal verb'ler yüklendi: {len(BENZER_DATA)} kayıt")
    else:
        BENZER_DATA = {}
        print("UYARI: output_benzer.json bulunamadı.")

    slug_sayac = {}
    yazilan = 0
    atlanan = 0
    hatali = []
    index_data = {}

    for i, (kelime, veri) in enumerate(data.items()):
        try:
            base_slug = slugify(kelime)

            if base_slug not in slug_sayac:
                slug_sayac[base_slug] = 0
                slug = base_slug
            else:
                slug_sayac[base_slug] += 1
                sayac = slug_sayac[base_slug] + 1
                slug = f"{base_slug}-{sayac}"

            tarih = tarih_hesapla(i)
            md = markdown_uret(kelime, veri, slug, tarih)

            dosya_yolu = os.path.join(OUTPUT_DIR, f"{slug}.md")
            with open(dosya_yolu, "w", encoding="utf-8") as f:
                f.write(md)

            index_data[slug] = {
                "title": veri.get("title", ""),
                "phrasal_verb": kelime.split("|")[0].strip().lower(),
                "tags": veri.get("tags", []),
                "date": tarih,
            }

            yazilan += 1

            if yazilan % 100 == 0:
                print(f"  {yazilan} dosya yazıldı...")

        except Exception as e:
            atlanan += 1
            hatali.append((kelime, str(e)))

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

    print()
    print("=== BİTTİ ===")
    print(f"Toplam kayıt: {len(data)}")
    print(f"Yazılan dosya: {yazilan}")
    print(f"Atlanan: {atlanan}")
    print(f"Çıktı klasörü: {OUTPUT_DIR}")
    print(f"Index dosyası: {INDEX_FILE}")

    if hatali:
        print()
        print("Hatalı kayıtlar (ilk 10):")
        for kelime, hata in hatali[:10]:
            print(f"  - {kelime[:60]}: {hata}")


if __name__ == "__main__":
    main()