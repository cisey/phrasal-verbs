# -*- coding: utf-8 -*-
import json
import os
import re
import shutil
from datetime import datetime, timedelta

import yaml

INPUT_JSON = "output.json"
OUTPUT_DIR = "content/phrasal-verbs"
INDEX_FILE = "content/phrasal-verbs-index.json"

# Yayın planı
GUNLUK_YAYIN = 3
BASLANGIC_TARIHI = datetime.now()

# Hugo teması sayfa başlığını H1 olarak basıyorsa False yap
H1_YAZ = True

TR_KARAKTERLER = {
    "ç": "c", "Ç": "c",
    "ğ": "g", "Ğ": "g",
    "ı": "i", "İ": "i",
    "ö": "o", "Ö": "o",
    "ş": "s", "Ş": "s",
    "ü": "u", "Ü": "u",
}

# short_answer içinde sık geçen, slug'a katkısı olmayan dolgu kelimeler
DOLGU_KELIMELER = {
    "bir", "birine", "birisi", "biri", "bu", "şu", "o",
    "ingilizce", "türkçe", "türkçede", "türkçesi", "türkcede",
    "anlamına", "anlamı", "anlam", "anlamda", "anlamlar",
    "gelir", "gelen", "gelmek", "geliyor", "gelir.",
    "olan", "olarak", "ise", "veya", "ya", "da", "de",
    "phrasal", "verb", "verbdür", "verb'dür", "ifade",
    "ifadesi", "kelime", "kelimesi", "çok", "en", "ve",
    "ki", "mi", "mu", "mı", "mü", "ise", "ama", "fakat",
    "genellikle", "çoğunlukla", "bazen", "biraz", "daha",
    "şey", "şeyi", "şeyler", "durum", "durumda", "durumu",
    "zaman", "zamanı", "yer", "yerde", "yeri",
    "kadar", "gibi", "için", "ile", "hem", "ya",
}


def slugify(text):
    """'blow up | to explode' → 'blow-up'"""
    kelime = text.split("|")[0].strip().lower()
    for tr, en in TR_KARAKTERLER.items():
        kelime = kelime.replace(tr, en)
    kelime = re.sub(r"[^a-z0-9]+", "-", kelime)
    kelime = kelime.strip("-")
    return kelime or "bilinmeyen"


def anlam_slug_ekle(kelime, veri):
    """Slug'a anlamdan kısa bir ipucu ekler.

    short_answer'ın ilk cümlesinden anlamlı (dolgu olmayan) kelimeleri
    çeker, phrasal verb'ün kendisini atlar, sonucu slug formatına çevirir.
    """
    short = veri.get("short_answer", "")
    if not short:
        return None

    # İlk cümleyi al (noktadan kes)
    ilk_cumle = short.split(".")[0].strip()
    if not ilk_cumle:
        return None

    kelimeler = ilk_cumle.split()

    # Phrasal verb'ün kendisini (baştaki kelimeleri) atla
    # Örn: "Stand by, birine destek..." → "Stand by" kısmını geç
    pv_kelimeleri = kelime.split("|")[0].strip().lower().split()

    i = 0
    while i < len(kelimeler) and i < len(pv_kelimeleri):
        temiz = kelimeler[i].lower().strip(",;:!?'\"")
        if temiz == pv_kelimeleri[i]:
            i += 1
        else:
            break

    # Kalan kelimelerden anlamlı olanları topla
    anlamli = []
    for k in kelimeler[i:]:
        temiz = k.lower().strip(",;:!?'\"")
        # Dolgu kelimesi mi?
        if temiz in DOLGU_KELIMELER:
            continue
        # Çok kısa mı?
        if len(temiz) < 3:
            continue
        # Sadece sayı mı?
        if temiz.isdigit():
            continue

        anlamli.append(temiz)
        if len(anlamli) >= 3:
            break

    if not anlamli:
        return None

    parca = "-".join(anlamli)

    # Türkçe karakterleri çevir
    for tr, en in TR_KARAKTERLER.items():
        parca = parca.replace(tr, en)

    parca = re.sub(r"[^a-z0-9]+", "-", parca)
    parca = parca.strip("-")

    if not parca:
        return None

    if len(parca) > 40:
        parca = parca[:40].rstrip("-")

    return parca or None


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


def markdown_uret(kelime, veri, slug, tarih):
    """Tek bir phrasal verb kaydından Markdown içeriği üretir."""
    title = veri.get("title", "")
    short_answer = veri.get("short_answer", "")
    origin = veri.get("origin", "")
    examples = veri.get("examples", [])
    tags = veri.get("tags", [])

    # YAML frontmatter (PyYAML ile otomatik kaçış)
    frontmatter = {
        "title": title,
        "description": kelime_sinirinda_kes(short_answer, 155),
        "tags": tags if tags else [],
        "phrasal_verb": kelime.split("|")[0].strip().lower(),
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

    # Başlık (tema zaten basıyorsa kapatılabilir)
    if H1_YAZ:
        icerik.append(f"# {title}")
        icerik.append("")

    # Kısa cevap
    icerik.append(short_answer)
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

    # Etiketler
    if tags:
        icerik.append("## Etiketler")
        icerik.append("")
        icerik.append(" ".join([f"`{t}`" for t in tags]))
        icerik.append("")

    return "\n".join(icerik)


def main():
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

    # Aynı base_slug'ın kaç kere kullanıldığını takip et
    slug_sayac = {}

    yazilan = 0
    atlanan = 0
    hatali = []

    # İlişkili link altyapısı için index verisi
    index_data = {}

    for i, (kelime, veri) in enumerate(data.items()):
        try:
            base_slug = slugify(kelime)

            if base_slug not in slug_sayac:
                # İlk kez görülüyor → düz slug
                slug_sayac[base_slug] = 0
                slug = base_slug
            else:
                slug_sayac[base_slug] += 1

                # Anlamdan slug üretmeyi dene
                anlam = anlam_slug_ekle(kelime, veri)

                # Anlam slug'ı geçerli mi? (boş olmasın, base_slug ile aynı olmasın)
                if anlam and anlam != base_slug:
                    slug = f"{base_slug}-{anlam}"
                else:
                    # FALLBACK: a, b, c, d... harf ekle
                    harf_index = slug_sayac[base_slug] - 1
                    harf = chr(ord("a") + harf_index)
                    slug = f"{base_slug}-{harf}"

                # Çakışma devam ediyorsa numara ekle
                sayac = 2
                orijinal_slug = slug
                while os.path.exists(os.path.join(OUTPUT_DIR, f"{slug}.md")):
                    slug = f"{orijinal_slug}-{sayac}"
                    sayac += 1

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