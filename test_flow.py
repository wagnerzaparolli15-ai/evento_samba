import requests, re

BASE = 'http://127.0.0.1:5000'
s = requests.Session()

# 1) Simula compra
resp = s.post(BASE + '/comprar', data={'nome': 'Teste Usuario', 'telefone': '21999999999'})
print('POST /comprar ->', resp.status_code)
print('contains nome?', 'Teste Usuario' in resp.text)

# tenta extrair a url de checkin do HTML
m = re.search(r'https?://[^"\s]+/checkin/\d+', resp.text)
if m:
    print('checkin_url:', m.group(0))
else:
    m2 = re.search(r'/checkin/\d+', resp.text)
    print('checkin_path:', m2.group(0) if m2 else 'não encontrada')

# 2) Verifica /admin
admin = s.get(BASE + '/admin')
print('/admin ->', admin.status_code)
print('admin snippet:\n', admin.text[:800])
