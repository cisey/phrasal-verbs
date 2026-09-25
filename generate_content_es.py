# -*- coding: utf-8 -*-
"""
İngilizce phrasal verb'ler için İSPANYOLCA içerik üretimi.

Bu script, Türkçe için kullandığın iki scripti (ana içerik üretimi + ilişkili
phrasal verb üretimi) tek dosyada birleştirir. Türkçe dosyalarına (output.json,
output_benzer.json) HİÇ dokunmaz — tamamen ayrı dosya isimleri kullanır.

Kullanım:
    python generate_content_es.py --step main       # Sadece ana içeriği üret
    python generate_content_es.py --step related    # Sadece ilişkili kelimeleri üret
    python generate_content_es.py --step all         # İkisini sırayla çalıştır (varsayılan)
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
# İstersen buraya nvidia/groq gibi diğer sağlayıcıları da aynı şekilde ekleyebilirsin.
SAĞLAYICILAR = {
    "evren": {
        "base_url": "https://evren-llmapi.ssyz.org.tr/v1",
        "api_key": os.environ.get("EVREN_API_KEY", ""),
        "model_main": "deepseek-v4-flash",
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
        print(f"Uyarı: {CONFIG_DOSYASI} bulunamadı, varsayılan '{VARSAYILAN_SAĞLAYICI}' kullanılıyor.")
        return VARSAYILAN_SAĞLAYICI
    with open(CONFIG_DOSYASI, "r", encoding="utf-8") as f:
        for satir in f:
            satir = satir.strip()
            if satir.startswith("provider"):
                _, _, deger = satir.partition("=")
                secim = deger.strip().lower()
                if secim in SAĞLAYICILAR:
                    return secim
                print(f"Uyarı: Bilinmeyen sağlayıcı '{secim}', varsayılan '{VARSAYILAN_SAĞLAYICI}' kullanılıyor.")
                return VARSAYILAN_SAĞLAYICI
    return VARSAYILAN_SAĞLAYICI


AKTIF_SAĞLAYICI = saglayici_oku()
AYARLAR = SAĞLAYICILAR[AKTIF_SAĞLAYICI]

client = OpenAI(base_url=AYARLAR["base_url"], api_key=AYARLAR["api_key"])

# === DOSYA AYARLARI (İSPANYOLCA — Türkçe dosyalarıyla ASLA karışmaz) ===
INPUT_CSV = "phrases.csv"
OUTPUT_JSON = "output_es.json"
RELATED_JSON = "output_es_benzer.json"
ERROR_LOG = "hatalilar_es.txt"

TEST_MODU = False
TEST_ADET = 3

# === İSPANYOLCA İÇERİK ÜRETİM PROMPT'U ===
PROMPT_MAIN = """IMPORTANTE: Devuelve ÚNICAMENTE JSON. No expliques nada. No escribas "Aquí está el JSON:". Empieza directamente con {{ y termina con }}.

Rol: Eres un lexicógrafo profesional de inglés-español y experto en contenido SEO.

Tarea: Analiza el phrasal verb en inglés que se te da y responde SOLO en el siguiente formato JSON.

Entrada: {girdi}

REGLAS MUY IMPORTANTES:
- Tu salida DEBE ser únicamente un objeto JSON válido. El primer carácter debe ser {{ y el último }}.
- No agregues ninguna explicación, saludo o nota al principio o al final.
- NO uses bloques de código Markdown (```).
- NO uses comillas simples ('), usa solo comillas dobles (").
- Todos los campos deben completarse, ningún campo puede quedar vacío o con "...".
- El campo "origin" DEBE estar en ESPAÑOL. NO escribas la explicación en inglés.
- El campo "title" NO debe ser una sola palabra. Escribe un título long-tail, optimizado para clics.
- El phrasal verb en inglés dentro del "title" SIEMPRE debe escribirse en minúsculas y entre comillas simples ('account for', no "Account For" ni "Account for").

Reglas de contenido:
1. El campo "title" debe ser long-tail y optimizado para clics, con el phrasal verb en minúsculas entre comillas simples (Ej: "¿Qué significa 'blow up'? Significado y Ejemplos").
2. El campo "short_answer" debe responder claramente a la pregunta "¿Qué significa X?" (párrafo de 40-50 palabras).
3. Indica el equivalente más natural en español.
4. Incluye al menos 2 frases de ejemplo naturales en inglés con su traducción al español.
5. Si existe, incluye una nota breve e interesante sobre el origen/estructura de la expresión.
6. Para el campo "tags", elige SOLO 1 o 2 de estas 4 categorías, las que mejor encajen: ["Inglés de Negocios", "Conversación Cotidiana", "Inglés Académico", "Inglés para Exámenes"]

Esquema JSON esperado:
{{
  "title": "...",
  "short_answer": "...",
  "origin": "...",
  "examples": [{{"en": "...", "es": "..."}}],
  "tags": ["..."]
}}

Ahora da ÚNICAMENTE la salida JSON para: {girdi}"""

PROMPT_RELATED = """Encuentra 3-4 phrasal verbs en inglés con un significado CERCANO al siguiente.

Phrasal Verb: {pv}
Significado: {anlam}

REGLAS IMPORTANTES:
- Escribe SOLO phrasal verbs (mínimo 2 palabras, no una sola palabra)
- Elige los que sean REALMENTE cercanos en significado
- Devuelve la respuesta SOLO como un array JSON
- No des ninguna otra explicación

Formato de ejemplo:
["make up", "add up to", "answer for"]

Ahora da 3-4 phrasal verbs con significado cercano a {pv}:"""


def clean_json_response(raw_text):
    """Çok agresif temizlik: markdown, tek tırnak, eksik kaçış, trailing comma."""
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
    """Ana içerik JSON'unun geçerliliğini kontrol eder (İspanyolca örnek alanı: 'es')."""
    if not isinstance(json_veri, dict):
        raise ValueError(f"JSON obje değil, {type(json_veri).__name__}")

    gerekli = ["title", "short_answer", "origin", "examples", "tags"]
    eksik = [g for g in gerekli if g not in json_veri]
    if eksik:
        raise ValueError(f"Eksik alanlar: {eksik}")

    if json_veri["title"] in ("...", "") or json_veri["short_answer"] in ("...", ""):
        raise ValueError("Placeholder değer içeriyor")

    if not isinstance(json_veri["examples"], list) or len(json_veri["examples"]) < 1:
        raise ValueError("examples boş veya liste değil")

    for e in json_veri["examples"]:
        if not isinstance(e, dict) or "en" not in e or "es" not in e:
            raise ValueError("example formatı hatalı (en/es bekleniyor)")

    if not isinstance(json_veri["tags"], list) or len(json_veri["tags"]) < 1:
        raise ValueError("tags boş veya liste değil")


def model_cagir(prompt_text, model_adi):
    kwargs = {
        "model": model_adi,
        "messages": [
            {
                "role": "system",
                "content": "Eres un asistente que SOLO devuelve JSON válido. El primer carácter de tu salida debe ser { y el último }. No uses Markdown, explicaciones ni comillas simples.",
            },
            {"role": "user", "content": prompt_text},
        ],
        "temperature": 0.0,
        "max_tokens": 1500,
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
            girdi = degerler[4].strip() if len(degerler) > 4 else ""

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

                    time.sleep(2)
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
                    elif any(k in hata_mesaji for k in ("JSON çıkarılamadı", "Placeholder", "Eksik alanlar", "examples", "tags", "JSON obje değil")):
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
    parser = argparse.ArgumentParser(description="İspanyolca phrasal verb içeriği üretir.")
    parser.add_argument("--step", choices=["main", "related", "all"], default="all")
    args = parser.parse_args()

    if args.step in ("main", "all"):
        adim_ana_icerik()
    if args.step in ("related", "all"):
        adim_iliskili_kelimeler()


if __name__ == "__main__":
    main()