# -*- coding: utf-8 -*-
import json

with open("output.json", "r", encoding="utf-8") as f:
    data = json.load(f)

zayif = []

for k, v in data.items():
    title = v.get("title", "")
    short = v.get("short_answer", "")
    origin = v.get("origin", "")

    sebepler = []

    if len(title) < 20:
        sebepler.append("title kısa")
    if title.lower() == k.split(" | ")[0].lower():
        sebepler.append("title = kelime")
    if len(short) < 100:
        sebepler.append("short_answer kısa")
    if len(origin) < 20:
        sebepler.append("origin kısa")
    # origin içinde İngilizce kelime var mı (basit kontrol)
    if origin and any(w in origin.lower() for w in ["the ", "is ", "comes from", "derived from", "based on", "phrase", "verb"]):
        sebepler.append("origin İngilizce olabilir")

    if sebepler:
        zayif.append((k, ", ".join(sebepler)))

print(f"Toplam kayıt: {len(data)}")
print(f"Zayıf kayıt: {len(zayif)}")
print()
for kelime, sebep in zayif[:50]:
    print(f"- {kelime[:70]}")
    print(f"  → {sebep}")
print()
if len(zayif) > 50:
    print(f"... ve {len(zayif) - 50} tane daha")

# Silinecekler listesini dosyaya kaydet
with open("zayif_listesi.txt", "w", encoding="utf-8") as f:
    for kelime, sebep in zayif:
        f.write(f"{kelime}\t{sebep}\n")

print(f"\nTam liste 'zayif_listesi.txt' dosyasına kaydedildi.")