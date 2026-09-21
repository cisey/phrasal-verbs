# -*- coding: utf-8 -*-
import json

with open("output.json", "r", encoding="utf-8") as f:
    data = json.load(f)

zayif_kelimeler = []
with open("zayif_listesi.txt", "r", encoding="utf-8") as f:
    for satir in f:
        if "\t" in satir:
            kelime = satir.split("\t")[0].strip()
            if kelime:
                zayif_kelimeler.append(kelime)

print(f"Kontrol edilecek kayıt: {len(zayif_kelimeler)}")
print("=" * 80)

for kelime in zayif_kelimeler:
    if kelime in data:
        origin = data[kelime].get("origin", "")
        print(f"\n📌 {kelime[:70]}")
        print(f"   ORIGIN: {origin[:150]}...")