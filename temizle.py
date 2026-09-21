# -*- coding: utf-8 -*-
import json

with open("output.json", "r", encoding="utf-8") as f:
    data = json.load(f)

temiz = {}
silinen = []

for kelime, kayit in data.items():
    # 1. Obje mi?
    if not isinstance(kayit, dict):
        silinen.append((kelime, "obje değil"))
        continue

    # 2. Gerekli alanlar var mı?
    gerekli = ["title", "short_answer", "origin", "examples", "tags"]
    eksik = [g for g in gerekli if g not in kayit]
    if eksik:
        silinen.append((kelime, f"eksik: {eksik}"))
        continue

    # 3. Placeholder mı?
    if kayit["title"] in ("...", "") or kayit["short_answer"] in ("...", ""):
        silinen.append((kelime, "placeholder"))
        continue

    # 4. examples boş mu?
    if not isinstance(kayit["examples"], list) or len(kayit["examples"]) < 1:
        silinen.append((kelime, "examples boş"))
        continue

    # 5. examples içinde en/tr var mı?
    if not all(isinstance(e, dict) and "en" in e and "tr" in e for e in kayit["examples"]):
        silinen.append((kelime, "example hatalı"))
        continue

    temiz[kelime] = kayit

# Yedek al
with open("output.json.bak", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# Temizlenmiş hali kaydet
with open("output.json", "w", encoding="utf-8") as f:
    json.dump(temiz, f, ensure_ascii=False, indent=2)

print(f"Önce: {len(data)}")
print(f"Sonra: {len(temiz)}")
print(f"Silinen: {len(silinen)}")
print(f"Yedek: output.json.bak")
print()
for kelime, sebep in silinen:
    print(f"- {kelime[:70]} → {sebep}")