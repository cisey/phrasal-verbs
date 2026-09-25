# -*- coding: utf-8 -*-
import json

with open("output.json", "r", encoding="utf-8") as f:
    data = json.load(f)

with open("output_benzer.json", "r", encoding="utf-8") as f:
    benzer = json.load(f)

# output.json'daki phrasal verb'leri topla
mevcut_pv = set()
for k in data:
    pv = k.split("|")[0].strip().lower()
    mevcut_pv.add(pv)

# Filtrele
filtrelenmis = {}
toplam_atilan = 0
for kelime, benzerler in benzer.items():
    yeni_benzerler = [b for b in benzerler if b.lower() in mevcut_pv]
    atilan = len(benzerler) - len(yeni_benzerler)
    toplam_atilan += atilan
    if yeni_benzerler:
        filtrelenmis[kelime] = yeni_benzerler

with open("output_benzer.json", "w", encoding="utf-8") as f:
    json.dump(filtrelenmis, f, ensure_ascii=False, indent=2)

print(f"Filtrelendi. Toplam atılan: {toplam_atilan}")
print(f"Kalan kayıt: {len(filtrelenmis)}")