# model_test.py - finds which free Gemini models YOUR key can use
import re
from google import genai

text = open("config.ini", encoding="utf-8").read()
match = re.search(r"gemini_api_key\s*=\s*(.+)", text)
KEY = match.group(1).strip().strip('"') if match else ""

client = genai.Client(api_key=KEY)

for name in ["gemini-3.1-flash-lite", "gemini-3.5-flash",
             "gemini-3.8-flash", "gemini-2.5-flash"]:
    try:
        client.models.generate_content(model=name, contents="say ok",
                                         config={"max_output_tokens": 3})
        print("   WORKS ->  " + name)
    except Exception as error:
        print("   dead  ->  " + name + "   |   " + str(error)[:50])

input("\nPress Enter to close...")