# -*- coding: utf-8 -*-
from dotenv import load_dotenv
load_dotenv()

import json
import os
import time
from openai import OpenAI

INPUT_JSON = "output.json"
ZENGIN_JSON = "output_zengin.json"
OUTPUT_JSON = "output_benzer.json"

client = OpenAI(
    base_url="https://evren-llmapi.ssyz.org.tr/v1",
    api_key=os.environ.get("EVREN_API_KEY")
)

MODEL = "qwen3.8-flash-next"

# Test modu: sadece ilk 3 kaydı işle
TEST_MODU = False
TEST_ADET = 3


def benzer_phrasal_verbler_uret(kelime, veri):
    """Anlamca yakın phrasal verb'leri üretir."""
    pv = kelime.split("|")[0].strip()
    anlam = veri.get("short_answer", "")[:200]
    
    prompt = f"""Aşağıdaki İngilizce phrasal verb'e ANLAMCA YAKIN 3-4 phrasal verb bul.

Phrasal Verb: {pv}
Anlam: {anlam}

ÖNEMLİ KURALLAR:
- Sadece PHRASAL VERB'ler yaz (tek kelime değil, en az 2 kelime)
- Anlamca GERÇEKTEN yakın olanları seç
- Cevabı sadece JSON array olarak döndür
- Başka açıklama yapma

Örnek format:
["make up", "add up to", "answer for"]

Şimdi {pv} için 3-4 anlamca yakın phrasal verb döndür:"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Sen bir İngilizce sözlük asistanısın. Sadece JSON array formatında cevap verirsin."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1024
        )
        
        content = response.choices[0].message.content
        if not content:
            return None
        
        # JSON'u temizle
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        # JSON array olarak parse et
        benzerler = json.loads(content)
        if not isinstance(benzerler, list):
            return None
        
        # Sadece string olanları al
        return [str(b).strip().lower() for b in benzerler if isinstance(b, str)]
    except Exception as e:
        print(f"  HATA: {e}")
        return None


def main():
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Mevcut veriyi yükle (varsa)
    if os.path.exists(OUTPUT_JSON):
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            benzer_data = json.load(f)
    else:
        benzer_data = {}
    
    # Test modu
    if TEST_MODU:
        kelimeler = list(data.keys())[:TEST_ADET]
    else:
        kelimeler = list(data.keys())
    
    print(f"Toplam {len(kelimeler)} kelime işlenecek.")
    print(f"Model: {MODEL}")
    print()
    
    for i, kelime in enumerate(kelimeler):
        if kelime in benzer_data:
            print(f"[{i+1}/{len(kelimeler)}] ATLANDI: {kelime[:50]}")
            continue
        
        print(f"[{i+1}/{len(kelimeler)}] İşleniyor: {kelime[:50]}")
        sonuc = benzer_phrasal_verbler_uret(kelime, data[kelime])
        
        if sonuc:
            benzer_data[kelime] = sonuc
            print(f"  ✓ Başarılı: {sonuc}")
        else:
            print(f"  ✗ Başarısız")
        
        # Her 10 kayıtta bir kaydet
        if (i + 1) % 10 == 0:
            with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
                json.dump(benzer_data, f, ensure_ascii=False, indent=2)
            print(f"  → Ara kayıt yapıldı ({len(benzer_data)} kayıt)")
        
        # time.sleep(1)
    
    # Son kayıt
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(benzer_data, f, ensure_ascii=False, indent=2)
    
    print()
    print("=== BİTTİ ===")
    print(f"İşlenen: {len(benzer_data)}")
    print(f"Çıktı: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()