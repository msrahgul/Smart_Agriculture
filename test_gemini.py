import os, requests
from dotenv import load_dotenv

load_dotenv()
key = os.environ.get('GEMINI_API_KEY', '')
if key.startswith(':"'):
    key = key[2:-1]
elif key.startswith('"'):
    key = key.strip('"')

resp = requests.post(
    f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}',
    json={'contents': [{'parts': [{'text': 'hi'}]}]}
)
print(resp.status_code)
print(resp.text[:100])
