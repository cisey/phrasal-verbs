# -*- coding: utf-8 -*-
from dotenv import load_dotenv
load_dotenv()

import os
from openai import OpenAI

client = OpenAI(
    base_url="https://evren-llmapi.ssyz.org.tr/v1",
    api_key=os.environ.get("EVREN_API_KEY")
)

response = client.chat.completions.create(
    model="deepseek-v4-flash",
    messages=[
        {"role": "system", "content": "Sen bir İngilizce-Türkçe sözlük asistanısın."},
        {"role": "user", "content": "Blow up ne demek? Türkçe anlamını 1 cümleyle açıkla."}
    ],
    max_tokens=4096
)

print("=== CEVAP ===")
print(response.choices[0].message.content)
print()
print("=== KULLANIM ===")
print(f"Prompt: {response.usage.prompt_tokens} token")
print(f"Completion: {response.usage.completion_tokens} token")
print(f"Toplam: {response.usage.total_tokens} token")