# -*- coding: utf-8 -*-
import json
import shutil

shutil.copy("output.json", "output.json.yedek")
print("Yedek alındı: output.json.yedek")

with open("output.json", "r", encoding="utf-8") as f:
    data = json.load(f)

zayif_kelimeler = []
with open("zayif_listesi.txt", "r", encoding="utf-8") as f:
    for satir in f:
        if "\t" in satir:
            kelime = satir.split("\t")[0].strip()
            if kelime:
                zayif_kelimeler.append(kelime)

print(f"Silinecek kelime sayısı: {len(zayif_kelimeler)}")

temiz = {k: v for k, v in data.items() if k not in zayif_kelimeler}

print(f"Önce: {len(data)}")
print(f"Sonra: {len(temiz)}")
print(f"Silinen: {len(data) - len(temiz)}")

with open("output.json", "w", encoding="utf-8") as f:
    json.dump(temiz, f, ensure_ascii=False, indent=2)

print("\noutput.json güncellendi.")