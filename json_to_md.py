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
OUTPUT_DIR = "site/content/phrasal-verbs"
INDEX_FILE = "site/content/phrasal-verbs-index.json"

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
    kelime = text.split("|")[0].strip().lower()
    for tr, en in TR_KARAKTERLER.items():
        kelime = kelime.replace(tr, en)
    kelime = re.sub(r"[^a-z0-9]+", "-", kelime)
    kelime = kelime.strip("-")
    return kelime or "bilinmeyen"


def tarih_hesapla(index):
    gun_farki = index // GUNLUK_YAYIN
    return (BASLANGIC_TARIHI + timedelta(days=gun_farki)).strftime("%Y-%m-%d")


def kelime_sinirinda_kes(metin, limit=155):
    if not metin:
        return ""
    if len(metin) <= limit:
        return metin
    kesik = metin[:limit].rsplit(" ", 1)[0]
    return kesik + "..."


def ipa_uret(kelime):
    pv = kelime.split("|")[0].strip().lower()
    try:
        ipa_sonuc = ipa_lib.convert(pv)
        if "*" in ipa_sonuc:
            return None
        return ipa_sonuc
    except Exception:
        return None


def iliskili_phrasal_verbler(kelime, max_adet=6):
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
    for diger_kelime in TUM_KAYITLAR:
        diger_pv = diger_kelime.split("|")[0].strip().lower()
        if diger_pv == benzer_pv.lower():
            diger_slug = slugify(diger_kelime)
            diger_baslik = TUM_KAYITLAR[diger_kelime].get("title", diger_kelime)
            return (diger_slug, diger_baslik)
    return (None, None)


def markdown_uret(kelime, veri, slug, tarih):
    title = veri.get("title", "")
    short_answer = veri.get("short_answer", "")
    origin = veri.get("origin", "")
    examples = veri.get("examples", [])
    tags = veri.get("tags", [])
    pv_sade = kelime.split("|")[0].strip().lower()

    frontmatter = {
        "title": title,
        "description": kelime_sinirinda_kes(short_answer, 155),
        "tags": tags if tags else [],
        "phrasal_verb": pv_sade,
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

    if H1_YAZ:
        icerik.append(f"# {title}")
        icerik.append("")

    # Dinle Butonu ve IPA (Fonetik) - Modern Tasarım
    ipa_metin = ipa_uret(kelime)
    ipa_gosterim = f"/{ipa_metin}/" if ipa_metin else ""
    
    icerik.append('<div style="display: flex; align-items: center; gap: 12px; margin-bottom: 24px;">')
    if ipa_gosterim:
        icerik.append(f'  <span style="font-size: 1.1rem; color: var(--primary-orange);"><b>Telaffuz:</b> <code>{ipa_gosterim}</code></span>')
    
    ses_js = f"const msg = new SpeechSynthesisUtterance('{pv_sade.replace(chr(39), chr(92)+chr(39))}'); msg.lang = 'en-US'; window.speechSynthesis.speak(msg);"
    icerik.append(f'  <button onclick="{ses_js}" style="background-color: var(--primary-orange); color: white; border: none; border-radius: 50%; width: 36px; height: 36px; cursor: pointer; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1);" title="Dinle"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon><path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path><path d="M19.07 4.93a10 10 0 0 1 0 14.14"></path></svg></button>')
    icerik.append('</div>')
    icerik.append("")

    if origin:
        icerik.append('<div class="custom-card">')
        icerik.append("")
        icerik.append("## 📖 Köken ve Yapı")
        icerik.append("")
        icerik.append(origin)
        icerik.append("")
        icerik.append("</div>")
        icerik.append("")

    if examples:
        icerik.append('<div class="custom-card info-card">')
        icerik.append("")
        icerik.append("## 💬 Örnek Cümleler")
        icerik.append("")
        for i, ex in enumerate(examples, start=1):
            en = ex.get("en", "")
            tr = ex.get("tr", "")
            icerik.append(f"**{i}.** {en}")
            icerik.append("")
            icerik.append(f"*{tr}*")
            icerik.append("")
            if i != len(examples):
                icerik.append("---")
                icerik.append("")
        icerik.append("</div>")
        icerik.append("")

    zengin = ZENGIN_DATA.get(kelime, {})

    if zengin.get("sik_hata"):
        icerik.append('<div class="custom-card error-card">')
        icerik.append("")
        icerik.append("## ⚠️ Sık Yapılan Hatalar")
        icerik.append("")
        icerik.append(f"❌ **Yanlış:** {zengin['sik_hata']}")
        icerik.append("")
        if zengin.get("dogru_kullanim"):
            icerik.append(f"✅ **Doğru:** {zengin['dogru_kullanim']}")
            icerik.append("")
        icerik.append("</div>")
        icerik.append("")

    if zengin.get("benzer") or zengin.get("zit"):
        icerik.append('<div class="custom-card">')
        icerik.append("")
        icerik.append("## 🔗 Eş ve Zıt Anlamlılar")
        icerik.append("")
        if zengin.get("benzer"):
            icerik.append(f"🔄 **Benzer:** {', '.join(zengin['benzer'])}")
            icerik.append("")
        if zengin.get("zit"):
            icerik.append(f"↔️ **Zıt:** {', '.join(zengin['zit'])}")
            icerik.append("")
        icerik.append("</div>")
        icerik.append("")

    if zengin.get("kullanim_notu"):
        icerik.append('<div class="custom-card">')
        icerik.append("")
        icerik.append("## 💡 Kullanım Notu")
        icerik.append("")
        icerik.append(zengin["kullanim_notu"])
        icerik.append("")
        icerik.append("</div>")
        icerik.append("")

    benzerler = BENZER_DATA.get(kelime, [])
    iliskili = iliskili_phrasal_verbler(kelime)
    
    if benzerler or iliskili:
        icerik.append('<div class="custom-card">')
        icerik.append("")
        if benzerler:
            icerik.append("## 📌 Benzer Phrasal Verb'ler")
            icerik.append("")
            eklenen_sluglar = set()
            for b in benzerler:
                benzer_slug, benzer_baslik = benzer_link_bul(b)
                if benzer_slug and benzer_slug not in eklenen_sluglar:
                    eklenen_sluglar.add(benzer_slug)
                    icerik.append(f"- [{benzer_baslik}](/phrasal-verbs/{benzer_slug}/)")
            icerik.append("")
        
        if iliskili:
            icerik.append("## 🔍 İlişkili Phrasal Verb'ler")
            icerik.append("")
            for diger_slug, diger_baslik in iliskili:
                icerik.append(f"- [{diger_baslik}](/phrasal-verbs/{diger_slug}/)")
            icerik.append("")
        icerik.append("</div>")
        icerik.append("")

    return "\n".join(icerik)


def main():
    global TUM_KAYITLAR, ZENGIN_DATA, BENZER_DATA
    if not os.path.exists(INPUT_JSON):
        print(f"HATA: {INPUT_JSON} bulunamadı!")
        return
    if os.path.exists(OUTPUT_DIR):
        silinen = len([f for f in os.listdir(OUTPUT_DIR) if f.endswith(".md")])
        shutil.rmtree(OUTPUT_DIR)
        print(f"Eski klasör temizlendi ({silinen} dosya silindi).")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    TUM_KAYITLAR = data
    if os.path.exists(ZENGIN_JSON):
        with open(ZENGIN_JSON, "r", encoding="utf-8") as f:
            ZENGIN_DATA = json.load(f)
        print(f"Zenginleştirilmiş veri yüklendi: {len(ZENGIN_DATA)} kayıt")
    else:
        ZENGIN_DATA = {}
        print("UYARI: output_zengin.json bulunamadı.")
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

if __name__ == "__main__":
    main()