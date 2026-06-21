"""最终验证移动端版本管理所有功能"""
import requests

B = 'http://127.0.0.1:8000/api/v1'

# Login
r = requests.post(f'{B}/auth/login/swagger?username=lireal&password=123456')
t = r.json()['access_token']
h = {'Authorization': f'Bearer {t}'}

# Create published version
r1 = requests.post(f'{B}/mobile/versions', headers=h, json={
    'app_name': '企业App', 'platform': 0, 'version_name': '2.0.0',
    'version_code': 200, 'publish_status': 1, 'force_update': True,
    'changelog': '重大更新', 'download_url': 'https://example.com/app-v2.apk',
})
assert r1.status_code == 200, f'Create failed: {r1.text}'
vid = r1.json()['data']['id']
print(f'Created version ID={vid}')

# Latest endpoint (no auth)
r2 = requests.get(f'{B}/mobile/versions/latest?platform=0')
assert r2.status_code == 200, f'Latest failed: {r2.text}'
d = r2.json()['data']
assert d['version_code'] == 200
assert d['force_update'] is True
print(f'Latest: v{d["version_name"]} (code={d["version_code"]}), force={d["force_update"]}')

# Download count
r3 = requests.post(f'{B}/mobile/versions/{vid}/download')
assert r3.status_code == 200, f'Download failed: {r3.text}'
print(f'Download count: {r3.json()["data"]["download_count"]}')

# Viewer can see
r4 = requests.post(f'{B}/auth/login/swagger?username=admin&password=123456')
vt = r4.json()['access_token']
vh = {'Authorization': f'Bearer {vt}'}
r5 = requests.get(f'{B}/mobile/versions', headers=vh)
assert r5.status_code == 200
assert r5.json()['data']['total'] >= 1
print(f'Viewer can see versions (total={r5.json()["data"]["total"]})')

# Viewer cannot create
r6 = requests.post(f'{B}/mobile/versions', headers=vh, json={
    'app_name': 'x', 'platform': 0, 'version_name': '9.9.9', 'version_code': 999,
})
assert r6.status_code == 403, f'Viewer create should 403: {r6.status_code}'
print(f'Viewer create blocked (403)')

# Cleanup
requests.delete(f'{B}/mobile/versions', headers=h, params={'pks': vid})
print(f'Cleaned up version {vid}')

print('\nAll mobile version management features verified!')
