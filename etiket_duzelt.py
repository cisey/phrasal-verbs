# -*- coding: utf-8 -*-
import json

# Yanlış etiketleri temizle
YANLIS_ETIKETLER = [
    'İngilizce Phrasal Verbs',
    'İngilizce Kelime Bilgisi',
    'İngilizce Türkçe Sözlük',
    'İngilizce Sözlük',
]

with open('output.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

duzeltilen = 0
for kelime, veri in data.items():
    tags = veri.get('tags', [])
    
    # Yanlış etiketleri temizle
    yeni_tags = []
    for t in tags:
        # Genel yanlış etiketler
        if t in YANLIS_ETIKETLER:
            continue
        # "Ne Demek" içeren etiketler
        if 'Ne Demek' in t or 'ne demek' in t or 'Anlamı' in t:
            continue
        # Phrasal verb'ün kendisini içeren etiketler (örneğin "Account For")
        pv = kelime.split('|')[0].strip().lower()
        if t.lower().strip() == pv:
            continue
        yeni_tags.append(t)
    
    # Eğer hiç etiket kalmazsa, varsayılan ekle
    if not yeni_tags:
        yeni_tags = ['Günlük Konuşma']
    
    if yeni_tags != tags:
        veri['tags'] = yeni_tags
        duzeltilen += 1
        print(f"  Düzeltildi: {kelime[:50]} -> {yeni_tags}")

with open('output.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print()
print(f"=== BİTTİ ===")
print(f"Düzeltilen kayıt: {duzeltilen}")
print(f"Toplam kayıt: {len(data)}")