"""测试 mobile API 功能"""
import requests
import sys

BASE = 'http://127.0.0.1:8000/api/v1'

# Login
r = requests.post(f'{BASE}/auth/login/swagger?username=lireal&password=123456')
print(f'Login: {r.status_code}')
if r.status_code != 200:
    print('Login failed'); sys.exit(1)

token = r.json()['access_token']
headers = {'Authorization': f'Bearer {token}'}

# GET /all
r2 = requests.get(f'{BASE}/mobile/versions/all', headers=headers)
print(f'GET /all: {r2.status_code}', end='')
if r2.status_code == 200:
    print(f' -> {len(r2.json()["data"])} items')
else:
    print(f' -> {r2.text[:100]}')

# GET /latest
r3 = requests.get(f'{BASE}/mobile/versions/latest?platform=0')
print(f'GET /latest (no auth): {r3.status_code}')

# POST create
payload = {'app_name': '测试App', 'platform': 0, 'version_name': '1.0.0', 'version_code': 100}
r4 = requests.post(f'{BASE}/mobile/versions', headers=headers, json=payload)
print(f'POST create: {r4.status_code}', end='')
if r4.status_code == 200:
    created_id = r4.json()['data']['id']
    print(f' -> ID={created_id}')
else:
    print(f' -> {r4.text[:100]}')
    created_id = None

# GET paginated
r5 = requests.get(f'{BASE}/mobile/versions', headers=headers)
print(f'GET paginated: {r5.status_code}', end='')
if r5.status_code == 200:
    print(f' -> total={r5.json()["data"]["total"]}')
else:
    print()

# Check viewer user has no write access
r6 = requests.post(f'{BASE}/auth/login/swagger?username=admin&password=123456')
if r6.status_code == 200:
    viewer_token = r6.json()['access_token']
    viewer_headers = {'Authorization': f'Bearer {viewer_token}'}
    r7 = requests.post(f'{BASE}/mobile/versions', headers=viewer_headers, json=payload)
    print(f'Viewer POST create: {r7.status_code} (expected 403)')

# Cleanup
if created_id:
    r8 = requests.delete(f'{BASE}/mobile/versions', headers=headers, params={'pks': created_id})
    print(f'DELETE {created_id}: {r8.status_code}')

print('\nAll tests done!')
