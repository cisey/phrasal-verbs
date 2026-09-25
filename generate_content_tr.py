# -*- coding: utf-8 -*-
"""
İngilizce phrasal verb'ler için TÜM ALANLARI İÇEREN TÜRKÇE içerik üretimi.

Kullanım:
    python generate_content_tr.py --step main        # Sadece ana içeriği üret
    python generate_content_tr.py --step related     # Sadece ilişkili kelimeleri üret
    python generate_content_tr.py --step all         # İkisini sırayla çalıştır (varsayılan)
"""

import argparse
import csv
import json
import os
import re
import time

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# === API SAĞLAYICI AYARLARI ===
SAĞLAYICILAR = {
    "evren": {
        "base_url": "https://evren-llmapi.ssyz.org.tr/v1",
        "api_key": "evren_llm_tjRpbV0kZZ0as2bNld5aNvvkfDNsBm87m3GJtJHrojY",
        "model_main": "glm-5.3",
        "model_related": "qwen3.8-flash-next",
        "json_mode": False,
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
        "model_main": "deepseek-chat",
        "model_related": "deepseek-chat",
        "json_mode": True,
    },
}
CONFIG_DOSYASI = "config.txt"
VARSAYILAN_SAĞLAYICI = "evren"


def saglayici_oku():
    if not os.path.exists(CONFIG_DOSYASI):
        return VARSAYILAN_SAĞLAYICI
    with open(CONFIG_DOSYASI, "r", encoding="utf-8") as f:
        for satir in f:
            satir = satir.strip()
            if satir.startswith("provider"):
                _, _, deger = satir.partition("=")
                secim = deger.strip().lower()
                if secim in SAĞLAYICILAR:
                    return secim
                return VARSAYILAN_SAĞLAYICI
    return VARSAYILAN_SAĞLAYICI


AKTIF_SAĞLAYICI = saglayici_oku()
AYARLAR = SAĞLAYICILAR[AKTIF_SAĞLAYICI]

client = OpenAI(base_url=AYARLAR["base_url"], api_key=AYARLAR["api_key"])

# === DOSYA AYARLARI ===
INPUT_CSV = "yeni_phrasal_verbler.csv"
OUTPUT_JSON = "output_tr.json"
RELATED_JSON = "output_tr_benzer.json"
ERROR_LOG = "hatalilar_tr.txt"

TEST_MODU = False
TEST_ADET = 3

# === TÜRKÇE İÇERİK ÜRETİM PROMPT'U ===
PROMPT_MAIN = """ÖNEMLİ: YALNIZCA JSON döndür. Hiçbir açıklama yapma. Doğrudan {{ ile başla ve }} ile bitir.

Rol: Profesyonel bir İngilizce-Türkçe sözlükbilimci ve SEO içerik uzmanısın.

Görev: Sana verilen İngilizce phrasal verb'ü analiz et ve SADECE aşağıdaki JSON formatında yanıtla.

Girdi: {girdi}

ÇOK ÖNEMLİ KURALLAR:
- Çıktın SADECE geçerli bir JSON nesnesi OLMALIDIR. İlk karakter {{ ve son karakter }} olmalıdır.
- Başında veya sonunda hiçbir açıklama, selamlama veya not ekleme.
- Tek tırnak (') KULLANMA, yalnızca çift tırnak (") kullan.
- "origin" ve "kullanim_notu" alanları TÜRKÇE OLMALIDIR.
- "title" içindeki İngilizce phrasal verb HER ZAMAN küçük harflerle ve tek tırnak içinde yazılmalıdır ('wipe out' gibi).

İçerik Kuralları (Gelişmiş Şema):
1. title: Long-tail ve tıklanmaya optimize edilmiş olmalı (Örn: "'wipe out' ne demek? Anlamı, Kullanımı ve Örnek Cümleler").
2. short_answer: "X ne anlama geliyor?" sorusuna net bir Türkçe yanıt vermelidir (40-50 kelimelik bir paragraf).
3. pronunciation: Kelimenin IPA fonetik telaffuzu (Örn: "/waɪp aʊt/"). Sadece İngilizce karakterlerle.
4. origin: Varsa, ifadenin kökeni veya yapısı hakkında ilginç, kısa bir Türkçe not.
5. examples: Doğal İngilizce ile yazılmış en az 2 örnek cümle ve bu cümlelerin Türkçe çevirileri.
6. sik_hata: Bu phrasal verb'ün sık yapılan yanlış kullanımına bir örnek İNGİLİZCE cümle (Örn: "The disease wiped out.").
7. dogru_kullanim: Yukarıdaki yanlışın doğrusu olan İNGİLİZCE cümle (Örn: "The disease wiped out the population.").
8. benzer: Bu ifadeyle EŞ veya YAKIN anlamlı 2-3 İngilizce kelime/phrasal verb (Liste formatında).
9. zit: Bu ifadeyle ZIT anlamlı 1-2 İngilizce kelime/phrasal verb (Yoksa boş liste [] bırak).
10. kullanim_notu: Kelimenin resmi/günlük dilde kullanımına veya belli başlı bağlamlarda (haber, felaket vb.) sık geçip geçmediğine dair kısa bir Türkçe not.
11. tags: Şu 4 kategoriden SADECE ifadenin en çok uyduğu 1 veya 2 tanesini seç: ["İş İngilizcesi", "Günlük Konuşma", "Akademik İngilizce", "Sınav İngilizcesi"]

Beklenen JSON Şeması:
{{
  "title": "...",
  "short_answer": "...",
  "pronunciation": "...",
  "origin": "...",
  "examples": [{{"en": "...", "tr": "..."}}],
  "sik_hata": "...",
  "dogru_kullanim": "...",
  "benzer": ["...", "..."],
  "zit": ["..."],
  "kullanim_notu": "...",
  "tags": ["..."]
}}

Şimdi SADECE şu kelime için JSON çıktısını ver: {girdi}"""

PROMPT_RELATED = """Aşağıdaki kelimeyle YAKIN anlama sahip 3-4 İngilizce phrasal verb bul.

Phrasal Verb: {pv}
Anlamı: {anlam}

ÖNEMLİ KURALLAR:
- SADECE phrasal verb yaz (en az 2 kelime, tek kelimelik fiiller yazma)
- Anlamca GERÇEKTEN yakın olanları seç
- Yanıtı SADECE bir JSON dizisi (array) olarak döndür
- Başka hiçbir açıklama yapma

Örnek format:
["make up", "add up to", "answer for"]

Şimdi {pv} kelimesine yakın anlama sahip 3-4 phrasal verb ver:"""


def clean_json_response(raw_text):
    if not raw_text:
        return None

    text = raw_text.strip()
    if "```" in text:
        parts = [p for p in text.split("```") if p.strip()]
        if parts:
            text = max(parts, key=len).strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()

    start = -1
    for idx, ch in enumerate(text):
        if ch in "{[":
            start = idx
            break

    if start == -1:
        return None

    depth = 0
    in_string = False
    escape_next = False
    end_idx = -1
    open_ch = text[start]
    close_ch = "}" if open_ch == "{" else "]"

    for i, ch in enumerate(text[start:], start=start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\":
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                end_idx = i
                break

    if end_idx == -1:
        return None

    json_str = text[start:end_idx + 1]

    for fixer in (
        lambda s: s,
        lambda s: s.replace("'", '"'),
        lambda s: re.sub(r",\s*([}\]])", r"\1", s),
        lambda s: re.sub(r",\s*([}\]])", r"\1", s).replace("'", '"'),
    ):
        fixed = fixer(json_str)
        try:
            json.loads(fixed)
            return fixed
        except json.JSONDecodeError:
            continue

    return None


def ana_icerik_dogrula(json_veri):
    if not isinstance(json_veri, dict):
        raise ValueError(f"JSON obje değil, {type(json_veri).__name__}")

    gerekli = [
        "title", "short_answer", "pronunciation", "origin", "examples", 
        "sik_hata", "dogru_kullanim", "benzer", "zit", "kullanim_notu", "tags"
    ]
    eksik = [g for g in gerekli if g not in json_veri]
    if eksik:
        raise ValueError(f"Eksik alanlar: {eksik}")

    if json_veri["title"] in ("...", "") or json_veri["short_answer"] in ("...", ""):
        raise ValueError("Placeholder değer içeriyor")

    if not isinstance(json_veri["examples"], list) or len(json_veri["examples"]) < 1:
        raise ValueError("examples boş veya liste değil")

    for e in json_veri["examples"]:
        if not isinstance(e, dict) or "en" not in e or "tr" not in e:
            raise ValueError("example formatı hatalı (en/tr bekleniyor)")

    if not isinstance(json_veri["benzer"], list):
        raise ValueError("benzer alanı liste değil")
    
    if not isinstance(json_veri["zit"], list):
        raise ValueError("zit alanı liste değil")

    if not isinstance(json_veri["tags"], list) or len(json_veri["tags"]) < 1:
        raise ValueError("tags boş veya liste değil")


def model_cagir(prompt_text, model_adi):
    kwargs = {
        "model": model_adi,
        "messages": [
            {
                "role": "system",
                "content": "Sen SADECE geçerli JSON döndüren bir asistansın. Çıktının ilk karakteri { ve son karakteri } olmalıdır. Markdown, açıklama veya tek tırnak kullanma.",
            },
            {"role": "user", "content": prompt_text},
        ],
        "temperature": 0.0,
        "max_tokens": 2000,
    }
    if AYARLAR.get("json_mode"):
        kwargs["response_format"] = {"type": "json_object"}

    cevap = client.chat.completions.create(**kwargs)
    return cevap.choices[0].message.content


# === ADIM 1: ANA İÇERİK ÜRETİMİ ===
def adim_ana_icerik():
    print(f"[ANA İÇERİK] Aktif sağlayıcı: {AKTIF_SAĞLAYICI.upper()} — Model: {AYARLAR['model_main']}")

    sonuclar = {}
    if os.path.exists(OUTPUT_JSON):
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            try:
                sonuclar = json.load(f)
                print(f"Önceki çalıştırmadan {len(sonuclar)} satır yüklendi.")
            except json.JSONDecodeError:
                print("Uyarı: Mevcut JSON dosyası bozuk, sıfırdan başlanıyor.")

    with open(INPUT_CSV, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))[1:] 

    if not reader:
        print("CSV dosyası boş veya okunamadı.")
        return

    if TEST_MODU:
        reader = reader[:TEST_ADET]

    print(f"Toplam {len(reader)} satır işlenecek.\n")

    basarili, hatali = 0, 0

    try:
        for i, degerler in enumerate(reader, start=1):
            girdi = degerler[0].strip() if len(degerler) > 0 else ""

            if not girdi or girdi in sonuclar:
                continue

            basarili_mi, son_hata = False, None

            for deneme in range(1, 6):
                try:
                    raw_text = model_cagir(PROMPT_MAIN.format(girdi=girdi), AYARLAR["model_main"])
                    json_text = clean_json_response(raw_text)
                    if not json_text:
                        raise ValueError("JSON çıkarılamadı")

                    json_veri = json.loads(json_text)
                    ana_icerik_dogrula(json_veri)

                    sonuclar[girdi] = json_veri
                    basarili += 1
                    basarili_mi = True

                    ek = "" if deneme == 1 else f" (deneme {deneme})"
                    print(f"[{i}/{len(reader)}] OK{ek}: {girdi[:60]}")

                    if basarili % 10 == 0:
                        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
                            json.dump(sonuclar, f, ensure_ascii=False, indent=2)

                    time.sleep(1)
                    break

                except Exception as e:
                    son_hata = e
                    hata_mesaji = str(e)

                    if "429" in hata_mesaji or "rate_limit" in hata_mesaji.lower():
                        bekleme = 15
                        print(f"[{i}/{len(reader)}] 429 (limit), {bekleme} sn... (deneme {deneme}/5)")
                        time.sleep(bekleme)
                    elif "503" in hata_mesaji or "overloaded" in hata_mesaji.lower():
                        bekleme = 10 * deneme
                        print(f"[{i}/{len(reader)}] 503 (sunucu yoğun), {bekleme} sn... (deneme {deneme}/5)")
                        time.sleep(bekleme)
                    elif any(k in hata_mesaji for k in ("JSON çıkarılamadı", "Placeholder", "Eksik alanlar", "examples", "tags", "JSON obje değil", "example formatı hatalı")):
                        print(f"[{i}/{len(reader)}] Doğrulama hatası ({hata_mesaji}), tekrar... (deneme {deneme}/5)")
                        time.sleep(2)
                    else:
                        print(f"[{i}/{len(reader)}] Kalıcı hata: {e}")
                        break

            if not basarili_mi:
                hatali += 1
                print(f"[{i}/{len(reader)}] ATLANDI ({girdi[:60]}): {son_hata}")
                with open(ERROR_LOG, "a", encoding="utf-8") as log_f:
                    log_f.write(f"{girdi} - {str(son_hata)}\n")

    finally:
        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(sonuclar, f, ensure_ascii=False, indent=2)

    print(f"\n=== ANA İÇERİK BİTTİ === Başarılı: {basarili} | Hatalı: {hatali} | Toplam: {len(sonuclar)}\n")


# === ADIM 2: İLİŞKİLİ PHRASAL VERB ÜRETİMİ ===
def benzer_uret(kelime, veri):
    pv = kelime.split("|")[0].strip()
    anlam = veri.get("short_answer", "")[:200]

    try:
        raw = model_cagir(PROMPT_RELATED.format(pv=pv, anlam=anlam), AYARLAR["model_related"])
        content = clean_json_response(raw) or raw.strip()

        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        benzerler = json.loads(content)
        if not isinstance(benzerler, list):
            return None
        return [str(b).strip().lower() for b in benzerler if isinstance(b, str)]
    except Exception as e:
        print(f"  HATA: {e}")
        return None


def adim_iliskili_kelimeler():
    print(f"[İLİŞKİLİ KELİMELER] Model: {AYARLAR['model_related']}")

    if not os.path.exists(OUTPUT_JSON):
        print(f"Önce ana içeriği üretmen gerekiyor ({OUTPUT_JSON} bulunamadı).")
        return

    with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    benzer_data = {}
    if os.path.exists(RELATED_JSON):
        with open(RELATED_JSON, "r", encoding="utf-8") as f:
            benzer_data = json.load(f)

    kelimeler = list(data.keys())[:TEST_ADET] if TEST_MODU else list(data.keys())
    print(f"Toplam {len(kelimeler)} kelime işlenecek.\n")

    for i, kelime in enumerate(kelimeler):
        if kelime in benzer_data:
            print(f"[{i + 1}/{len(kelimeler)}] ATLANDI: {kelime[:50]}")
            continue

        print(f"[{i + 1}/{len(kelimeler)}] İşleniyor: {kelime[:50]}")
        sonuc = benzer_uret(kelime, data[kelime])

        if sonuc:
            benzer_data[kelime] = sonuc
            print(f"  ✓ Başarılı: {sonuc}")
        else:
            print("  ✗ Başarısız")

        if (i + 1) % 10 == 0:
            with open(RELATED_JSON, "w", encoding="utf-8") as f:
                json.dump(benzer_data, f, ensure_ascii=False, indent=2)
            print(f"  → Ara kayıt yapıldı ({len(benzer_data)} kayıt)")

    with open(RELATED_JSON, "w", encoding="utf-8") as f:
        json.dump(benzer_data, f, ensure_ascii=False, indent=2)

    print(f"\n=== İLİŞKİLİ KELİMELER BİTTİ === İşlenen: {len(benzer_data)}\n")


def main():
    parser = argparse.ArgumentParser(description="Türkçe phrasal verb içeriği üretir.")
    parser.add_argument("--step", choices=["main", "related", "all"], default="all")
    args = parser.parse_args()

    if args.step in ("main", "all"):
        adim_ana_icerik()
    if args.step in ("related", "all"):
        adim_iliskili_kelimeler()


if __name__ == "__main__":
    main()