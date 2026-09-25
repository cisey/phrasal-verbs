from dotenv import load_dotenv
load_dotenv()
# -*- coding: utf-8 -*-
import csv
import json
import os
import re
import time

# === API SAĞLAYICI AYARLARI ===
SAĞLAYICILAR = {
    "evren": {
        "base_url": "https://evren-llmapi.ssyz.org.tr/v1",
        "api_key": os.environ.get("EVREN_API_KEY", ""),
        "model": "deepseek-v4-flash",
    },
    "nvidia": {
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key": os.environ.get("NVIDIA_API_KEY", ""),
        "model": "nvidia/nemotron-3-super-120b-a12b",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": os.environ.get("GROQ_API_KEY", ""),
        "model": "openai/gpt-oss-120b",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
        "model": "deepseek-chat",
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
                else:
                    print(f"Uyarı: Bilinmeyen sağlayıcı '{secim}', varsayılan '{VARSAYILAN_SAĞLAYICI}' kullanılıyor.")
                    return VARSAYILAN_SAĞLAYICI
    print(f"Uyarı: config.txt'de 'provider' satırı yok, varsayılan '{VARSAYILAN_SAĞLAYICI}' kullanılıyor.")
    return VARSAYILAN_SAĞLAYICI


AKTIF_SAĞLAYICI = saglayici_oku()
AYARLAR = SAĞLAYICILAR[AKTIF_SAĞLAYICI]

from openai import OpenAI

client = OpenAI(
    base_url=AYARLAR["base_url"],
    api_key=AYARLAR["api_key"]
)
MODEL_NAME = AYARLAR["model"]

# === DOSYA AYARLARI ===
INPUT_CSV = "phrases.csv"
OUTPUT_JSON = "output.json"
ERROR_LOG = "hatalilar.txt"


PROMPT_SABLONU = """ÖNEMLİ: Sadece ve sadece JSON döndür. Açıklama yapma. "İşte JSON:" gibi giriş yazma. Doğrudan {{ ile başla, }} ile bitir.

Rol: Sen profesyonel bir İngilizce-Türkçe sözlükbilimci ve SEO içerik uzmanısın.

Görev: Sana verilen İngilizce phrasal verb'ü analiz et ve SADECE aşağıdaki JSON formatında çıktı ver.

Girdi: {girdi}

ÇOK ÖNEMLİ KURALLAR:
- Çıktın SADECE geçerli bir JSON objesi olmalıdır. İlk karakter {{ son karakter }} olmalı.
- Başına veya sonuna HİÇBİR açıklama, selamlama, not ekleme.
- Markdown kod bloğu (```) KULLANMA.
- Tek tırnak (') KULLANMA, sadece çift tırnak (") kullan.
- Tüm alanlar doldurulmalı, hiçbir alan boş veya "..." olmayacak.
- origin alanı MUTLAKA Türkçe olmalıdır. İngilizce açıklama YAZMA.
- title alanı tek kelime OLMAMALIDIR. Uzun kuyruklu, tıklama odaklı bir başlık yaz.

İçerik Kuralları:
1. title alanı uzun kuyruklu ve tıklama odaklı olmalı (Örn: "Blow up Ne Demek? Anlamı ve Örnek Cümleler").
2. short_answer alanı "X ne demek?" sorusuna net ve yalın cevap vermelidir (40-50 kelimelik paragraf).
3. Türkçedeki en doğal karşılığı belirtilmelidir.
4. En az 2 doğal örnek cümle ve Türkçe çevirisi eklenmelidir.
5. Varsa ilgi çekici kısa köken/yapı notu yazılmalıdır.
6. tags alanı için SADECE şu 4 kategoriden en uygun 1 veya 2 tanesini seç: ["İş İngilizcesi", "Günlük Konuşma", "Akademik İngilizce", "Sınav İngilizcesi"]

Beklenen JSON şeması:
{{
  "title": "...",
  "short_answer": "...",
  "origin": "...",
  "examples": [{{"en": "...", "tr": "..."}}],
  "tags": ["..."]
}}

Şimdi SADECE JSON çıktısını ver:"""


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

    try:
        json.loads(json_str)
        return json_str
    except json.JSONDecodeError:
        pass

    fixed = json_str.replace("'", '"')
    try:
        json.loads(fixed)
        return fixed
    except json.JSONDecodeError:
        pass

    fixed = re.sub(r',\s*([}\]])', r'\1', json_str)
    try:
        json.loads(fixed)
        return fixed
    except json.JSONDecodeError:
        pass

    fixed = re.sub(r',\s*([}\]])', r'\1', json_str).replace("'", '"')
    try:
        json.loads(fixed)
        return fixed
    except json.JSONDecodeError:
        pass

    return None


def veriyi_dogrula(json_veri):
    """Modelin döndürdüğü JSON'un geçerli olup olmadığını kontrol eder.
    Geçersizse ValueError fırlatır, script retry mekanizmasını devreye sokar."""
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
        if not isinstance(e, dict) or "en" not in e or "tr" not in e:
            raise ValueError("example formatı hatalı")

    if not isinstance(json_veri["tags"], list) or len(json_veri["tags"]) < 1:
        raise ValueError("tags boş veya liste değil")


def model_cagir(girdi):
    """DeepSeek JSON modu ile çağrı yapar."""
    kwargs = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": "Sen sadece geçerli JSON döndüren bir asistansın. Çıktının ilk karakteri { son karakteri } olmalı. Markdown, açıklama veya tek tırnak kullanma. Sadece JSON."
            },
            {
                "role": "user",
                "content": PROMPT_SABLONU.format(girdi=girdi)
            }
        ],
        "temperature": 0.0,
        "max_tokens": 1500,
    }

    # JSON modu sadece DeepSeek ve Groq'ta desteklenir
    if AKTIF_SAĞLAYICI in ("deepseek", "groq"):
        kwargs["response_format"] = {"type": "json_object"}

    cevap = client.chat.completions.create(**kwargs)
    return cevap.choices[0].message.content


# === BAŞLANGIÇ ===
print(f"Aktif sağlayıcı: {AKTIF_SAĞLAYICI.upper()}")
print(f"Model: {MODEL_NAME}")
print()

sonuclar = {}
if os.path.exists(OUTPUT_JSON):
    with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
        try:
            sonuclar = json.load(f)
            print(f"Önceki çalıştırmadan {len(sonuclar)} satır yüklendi.")
        except json.JSONDecodeError:
            print("Uyarı: Mevcut JSON dosyası bozuk, sıfırdan başlanıyor.")

with open(INPUT_CSV, "r", encoding="utf-8") as f:
    reader = list(csv.reader(f))

reader = reader[1:]

if not reader:
    print("CSV dosyası boş veya okunamadı.")
    exit()

print(f"Toplam {len(reader)} satır işlenecek.")
print(f"İlk satır örneği: {reader[0][4][:80] if len(reader[0]) > 4 else 'YOK'}")
print("Başlıyor... (Ctrl+C ile durdurabilirsin)\n")

basarili = 0
hatali = 0

try:
    for i, degerler in enumerate(reader, start=1):
        girdi = degerler[4].strip() if len(degerler) > 4 else ""

        if not girdi or girdi in sonuclar:
            continue

        basarili_mi = False
        son_hata = None

        for deneme in range(1, 6):
            try:
                raw_text = model_cagir(girdi)
                json_text = clean_json_response(raw_text)

                if not json_text:
                    raise ValueError("JSON çıkarılamadı")

                json_veri = json.loads(json_text)

                # === VALİDASYON ===
                veriyi_dogrula(json_veri)
                # === VALİDASYON SONU ===

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
                elif "503" in hata_mesaji or "Service temporarily overloaded" in hata_mesaji:
                    bekleme = 10 * deneme
                    print(f"[{i}/{len(reader)}] 503 (sunucu yoğun), {bekleme} sn... (deneme {deneme}/5)")
                    time.sleep(bekleme)
                elif "JSON çıkarılamadı" in hata_mesaji or "Placeholder" in hata_mesaji or "Eksik alanlar" in hata_mesaji or "examples" in hata_mesaji or "tags" in hata_mesaji or "JSON obje değil" in hata_mesaji:
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

print(f"\n=== BİTTİ ===")
print(f"Sağlayıcı: {AKTIF_SAĞLAYICI}")
print(f"Bu çalıştırmada başarılı: {basarili}")
print(f"Hatalı: {hatali}")
print(f"Toplam kayıt (tüm zamanlar): {len(sonuclar)}")
print(f"Çıktı dosyası: {OUTPUT_JSON}")