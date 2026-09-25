# -*- coding: utf-8 -*-
from dotenv import load_dotenv
load_dotenv()

import json
import os
import time
from openai import OpenAI

INPUT_JSON = "output.json"
OUTPUT_JSON = "output_zengin.json"

client = OpenAI(
    base_url="https://evren-llmapi.ssyz.org.tr/v1",
    api_key=os.environ.get("EVREN_API_KEY")
)

MODEL = "deepseek-v4-flash"

# Test modu: sadece ilk 3 kaydı işle
TEST_MODU = False
TEST_ADET = 3


def zenginlestir(kelime, veri):
    """Bir phrasal verb için ek bilgiler üretir."""
    pv = kelime.split("|")[0].strip()
    anlam = veri.get("short_answer", "")[:200]
    
    prompt = f"""Aşağıdaki İngilizce phrasal verb için Türkçe bilgiler üret:

Phrasal Verb: {pv}
Anlam: {anlam}

Şu formatta JSON döndür (başka bir şey yazma):
{{
  "sik_hata": "En sık yapılan 1 hata (yanlış kullanım örneği)",
  "dogru_kullanim": "Doğru kullanım örneği",
  "benzer": ["benzer1", "benzer2", "benzer3"],
  "zit": ["zit1", "zit2"],
  "kullanim_notu": "1 cümlelik kullanım notu (resmi mi, günlük mü)"
}}

Sadece JSON döndür, başka açıklama yapma."""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "Sen bir İngilizce-Türkçe sözlük asistanısın. Sadece JSON formatında cevap verirsin."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4096
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
        
        return json.loads(content)
    except Exception as e:
        print(f"  HATA: {e}")
        return None


def main():
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Mevcut zengin veriyi yükle (varsa)
    if os.path.exists(OUTPUT_JSON):
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            zengin_data = json.load(f)
    else:
        zengin_data = {}
    
    # Test modu
    if TEST_MODU:
        kelimeler = list(data.keys())[:TEST_ADET]
    else:
        kelimeler = list(data.keys())
    
    print(f"Toplam {len(kelimeler)} kelime işlenecek.")
    print(f"Model: {MODEL}")
    print()
    
    for i, kelime in enumerate(kelimeler):
        if kelime in zengin_data:
            print(f"[{i+1}/{len(kelimeler)}] ATLANDI: {kelime[:50]}")
            continue
        
        print(f"[{i+1}/{len(kelimeler)}] İşleniyor: {kelime[:50]}")
        sonuc = zenginlestir(kelime, data[kelime])
        
        if sonuc:
            zengin_data[kelime] = sonuc
            print(f"  ✓ Başarılı")
        else:
            print(f"  ✗ Başarısız")
        
        # Her 10 kayıtta bir kaydet
        if (i + 1) % 10 == 0:
            with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
                json.dump(zengin_data, f, ensure_ascii=False, indent=2)
            print(f"  → Ara kayıt yapıldı ({len(zengin_data)} kayıt)")
        
        time.sleep(1)  # API'yi yormamak için
    
    # Son kayıt
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(zengin_data, f, ensure_ascii=False, indent=2)
    
    print()
    print("=== BİTTİ ===")
    print(f"İşlenen: {len(zengin_data)}")
    print(f"Çıktı: {OUTPUT_JSON}")


if __name__ == "__main__":
    main()