# -*- coding: utf-8 -*-
import json

with open("output.json", "r", encoding="utf-8") as f:
    data = json.load(f)

bozuk = []

for kelime, kayit in data.items():
    # 1. Obje değil mi?
    if not isinstance(kayit, dict):
        bozuk.append((kelime, "obje değil (liste veya başka tip)"))
        continue

    # 2. Gerekli alanlar var mı?
    gerekli = ["title", "short_answer", "origin", "examples", "tags"]
    eksik = [g for g in gerekli if g not in kayit]
    if eksik:
        bozuk.append((kelime, f"eksik alanlar: {eksik}"))
        continue

    # 3. Placeholder mı?
    if kayit["title"] in ("...", "") or kayit["short_answer"] in ("...", ""):
        bozuk.append((kelime, "placeholder (...)"))
        continue

    # 4. examples boş mu?
    if not kayit["examples"] or len(kayit["examples"]) < 1:
        bozuk.append((kelime, "examples boş"))
        continue

print(f"Toplam kayıt: {len(data)}")
print(f"Bozuk kayıt: {len(bozuk)}")
print()
for kelime, sebep in bozuk:
    print(f"- {kelime[:70]}  →  {sebep}")