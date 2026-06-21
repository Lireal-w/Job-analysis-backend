"""
观赏者用户和数据设置脚本

功能:
1. 创建菜单权限按钮 (datasource/dataset 的 add/edit/del)
2. 创建"观赏"部门
3. 创建"观赏者"角色（仅可查看数据）
4. 创建观赏者专有数据源和数据集
5. 创建两个观赏者用户: admin / user (密码均为 123456)
6. 验证权限隔离

只有 lireal (超级管理员) 可以添加/修改/删除数据，
其他观赏者用户仅能查看数据。
"""

import sys
import requests

BASE_URL = 'http://127.0.0.1:8000/api/v1'
VERBOSE = True
ADMIN_USERNAME = 'lireal'
ADMIN_PASSWORD = '123456'


def log(msg): print(f'[INFO] {msg}')
def log_step(step):
    print(f'\n{"="*60}\n  >>> {step}\n{"="*60}')
def log_error(msg): print(f'[ERROR] {msg}')
def log_success(msg): print(f'[SUCCESS] {msg}')


class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.is_superuser = False

    def request(self, method, path, **kwargs):
        url = f'{self.base_url}{path}'
        headers = kwargs.pop('headers', {})
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        if VERBOSE:
            print(f'  {method} {url}')
        resp = self.session.request(method, url, headers=headers, **kwargs)
        if VERBOSE and resp.status_code >= 400:
            print(f'  -> Status: {resp.status_code}, Body: {resp.text[:300]}')
        elif VERBOSE:
            print(f'  -> Status: {resp.status_code}')
        return resp

    def get(self, path, **kwargs): return self.request('GET', path, **kwargs)
    def post(self, path, **kwargs): return self.request('POST', path, **kwargs)
    def put(self, path, **kwargs): return self.request('PUT', path, **kwargs)
    def delete(self, path, **kwargs): return self.request('DELETE', path, **kwargs)

    def login(self, username, password):
        resp = self.request('POST', f'/auth/login/swagger?username={username}&password={password}')
        if resp.status_code != 200:
            return False
        data = resp.json()
        self.token = data['access_token']
        self.current_user = data.get('user', {})
        self.is_superuser = self.current_user.get('is_superuser', False)
        self.user_id = self.current_user.get('id')
        self.dept_id = self.current_user.get('dept_id')
        log_success(f'登录成功: {username} (ID: {self.user_id})')
        return True

    def create_dept(self, name):
        resp = self.post('/sys/depts', json={
            'name': name, 'sort': 0, 'leader': f'{name}负责人',
            'phone': '13800138000', 'email': f'{name}@test.com', 'status': 1
        })
        if resp.status_code != 200:
            return None
        log_success(f'创建部门: {name}')
        return self._find_dept(name)

    def _find_dept(self, name):
        resp = self.get('/sys/depts')
        if resp.status_code != 200:
            return None
        def find(tree, name):
            for item in tree:
                if item['name'] == name:
                    return item
                if item.get('children'):
                    r = find(item['children'], name)
                    if r:
                        return r
            return None
        return find(resp.json()['data'], name)

    def create_role(self, name):
        resp = self.post('/sys/roles', json={'name': name, 'status': 1})
        if resp.status_code != 200:
            return None
        log_success(f'创建角色: {name}')
        rr = self.get('/sys/roles/all')
        if rr.status_code == 200:
            for r in rr.json()['data']:
                if r['name'] == name:
                    return r
        return None

    def create_user(self, username, password, nickname, dept_id, role_ids):
        resp = self.post('/sys/users', json={
            'username': username, 'password': password,
            'nickname': nickname, 'dept_id': dept_id, 'roles': role_ids
        })
        if resp.status_code != 200:
            return None
        log_success(f'创建用户: {username}')
        return resp.json()['data']

    def assign_role_menus(self, role_id, menu_ids):
        resp = self.put(f'/sys/roles/{role_id}/menus', json={'menus': menu_ids})
        return resp.status_code == 200

    def create_menu_button(self, title, name, parent_id, perms):
        resp = self.post('/sys/menus', json={
            'title': title, 'name': name, 'parent_id': parent_id,
            'sort': 0, 'type': 2, 'status': 1, 'display': 0, 'cache': 1,
            'perms': perms, 'path': None, 'icon': None, 'component': None,
            'link': None, 'remark': None,
        })
        return resp.status_code == 200

    def create_datasource(self, name, dept_id=None):
        data = {'name': name, 'db_type': 'mysql', 'host': 'localhost', 'port': 3306,
                'database_name': 'test_db', 'username': 'test', 'password': 'test',
                'description': f'观赏数据源-{name}'}
        if dept_id is not None:
            data['dept_id'] = dept_id
        resp = self.post('/sys/datasources', json=data)
        if resp.status_code != 200:
            return None
        log_success(f'创建数据源: {name}')
        rr = self.get('/sys/datasources/all')
        if rr.status_code == 200:
            for item in rr.json()['data']:
                if item['name'] == name:
                    return item
        return None

    def create_dataset(self, name, dept_id=None):
        data = {'name': name, 'description': f'观赏数据集-{name}', 'source_type': 'manual'}
        if dept_id is not None:
            data['dept_id'] = dept_id
        resp = self.post('/sys/data-storage/datasets', json=data)
        if resp.status_code != 200:
            return None
        log_success(f'创建数据集: {name}')
        rr = self.get('/sys/data-storage/datasets/all')
        if rr.status_code == 200:
            for item in rr.json()['data']:
                if item['name'] == name:
                    return item
        return None


def flatten_menus(tree):
    result = []
    def walk(items):
        for item in items:
            result.append(item)
            if item.get('children'):
                walk(item['children'])
    walk(tree)
    return result


def main():
    client = APIClient(BASE_URL)

    log_step('1. Lireal 登录')
    if not client.login(ADMIN_USERNAME, ADMIN_PASSWORD):
        log_error('登录失败'); sys.exit(1)

    log_step('2. 获取菜单树')
    mr = client.get('/sys/menus')
    if mr.status_code != 200:
        log_error('获取菜单失败'); sys.exit(1)
    menus = flatten_menus(mr.json()['data'])
    log(f'共 {len(menus)} 个菜单')

    ds_menu = next((m for m in menus if m['name'] == 'datasource' and m['type'] == 1), None)
    dt_menu = next((m for m in menus if m['name'] == 'dataset' and m['type'] == 1), None)

    if not ds_menu: log_error('找不到数据源菜单(83)'); sys.exit(1)
    if not dt_menu: log_error('找不到数据集菜单(86)'); sys.exit(1)
    log(f'数据源菜单ID={ds_menu["id"]}, 数据集菜单ID={dt_menu["id"]}')

    log_step('3. 创建权限按钮')
    buttons = [
        ('新增数据源', 'AddDatasource', ds_menu['id'], 'datasource:add'),
        ('修改数据源', 'EditDatasource', ds_menu['id'], 'datasource:edit'),
        ('删除数据源', 'DeleteDatasource', ds_menu['id'], 'datasource:del'),
        ('新增数据集', 'AddDataset', dt_menu['id'], 'dataset:add'),
        ('修改数据集', 'EditDataset', dt_menu['id'], 'dataset:edit'),
        ('删除数据集', 'DeleteDataset', dt_menu['id'], 'dataset:del'),
    ]
    existing_names = {m['name'] for m in menus}
    for title, name, pid, perms in buttons:
        if name in existing_names:
            log(f'  按钮已存在: {name}')
            continue
        if client.create_menu_button(title, name, pid, perms):
            log_success(f'  创建: {name} ({perms})')
        else:
            log_error(f'  创建失败: {name}')

    # 刷新菜单
    mr = client.get('/sys/menus')
    menus = flatten_menus(mr.json()['data'])

    log_step('4. 创建观赏部门')
    dept = client.create_dept('观赏')
    if not dept: log_error('失败'); sys.exit(1)
    dept_id = dept['id']
    log(f'部门ID={dept_id}')

    log_step('5. 创建观赏者角色')
    role = client.create_role('观赏者')
    if not role: log_error('失败'); sys.exit(1)
    role_id = role['id']
    log(f'角色ID={role_id}')

    log_step('6. 分配只读菜单')
    view_ids = [m['id'] for m in menus if m['type'] != 2]
    log(f'分配 {len(view_ids)} 个查看菜单')
    if client.assign_role_menus(role_id, view_ids):
        log_success('分配成功')
    else:
        log_error('分配失败')

    log_step('7. 创建观赏数据源和数据集')
    dss = [client.create_datasource(n, dept_id) for n in
           ['观赏MySQL数据源', '观赏PG数据源', '观赏API数据源']]
    dsets = [client.create_dataset(n, dept_id) for n in
             ['观赏日报数据集', '观赏周报数据集', '观赏月报数据集']]
    dss = [d for d in dss if d]
    dsets = [d for d in dsets if d]
    log(f'数据源: {[d["id"] for d in dss]}, 数据集: {[d["id"] for d in dsets]}')

    log_step('8. 创建观赏者用户')
    u1 = client.create_user('admin', '123456', '观赏者Admin', dept_id, [role_id])
    u2 = client.create_user('user', '123456', '观赏者User', dept_id, [role_id])
    if not u1 or not u2:
        log_error('创建用户失败'); sys.exit(1)

    log_step('9. 权限验证')
    ok, fail = 0, 0
    def check(cond, desc):
        nonlocal ok, fail
        if cond:
            log_success(f'  ✓ {desc}'); ok += 1
        else:
            log_error(f'  ✗ {desc}'); fail += 1

    log('--- Lireal ---')
    td = client.create_datasource('_tmp_test_ds_', 1)
    check(td is not None, 'Lireal 可以创建数据源')
    if td:
        check(client.delete('/sys/datasources', params={'pks': td['id']}).status_code == 200,
              'Lireal 可以删除数据源')

    log('\n--- 观赏者用户 ---')
    for u in [u1, u2]:
        uname = u['username']
        log(f'\n  [{uname}]')
        vc = APIClient(BASE_URL)
        check(vc.login(uname, '123456'), '登录')
        if not vc.token:
            continue
        check(not vc.is_superuser, '非超级管理员')

        r1 = vc.get('/sys/datasources/all')
        check(r1.status_code == 200, 'GET 数据源列表')
        if r1.status_code == 200:
            items = r1.json()['data']
            check(any(d.get('dept_id') == dept_id for d in items), '可见观赏数据源')

        r2 = vc.get('/sys/data-storage/datasets/all')
        check(r2.status_code == 200, 'GET 数据集列表')
        if r2.status_code == 200:
            items = r2.json()['data']
            check(any(d.get('dept_id') == dept_id for d in items), '可见观赏数据集')

        r3 = vc.post('/sys/datasources', json={'name': f't_{uname}', 'db_type': 'mysql',
                                               'host': 'x', 'port': 3306})
        check(r3.status_code == 403, 'POST 数据源拒绝(403)')

        r4 = vc.post('/sys/data-storage/datasets', json={'name': f't_{uname}', 'source_type': 'manual'})
        check(r4.status_code == 403, 'POST 数据集拒绝(403)')

        if r1.status_code == 200:
            my = [d for d in r1.json()['data'] if d.get('dept_id') == dept_id]
            if my:
                r5 = vc.put(f'/sys/datasources/{my[0]["id"]}', json={'description': 'x'})
                check(r5.status_code == 403, 'PUT 数据源拒绝(403)')

                r6 = vc.delete('/sys/datasources', params={'pks': my[0]['id']})
                check(r6.status_code == 403, 'DELETE 数据源拒绝(403)')

    log_step('结果')
    total = ok + fail
    log(f'通过: {ok}/{total} | 失败: {fail}')
    if fail == 0:
        log_success('全部通过！🎉')
        print()
        print(' 环境摘要')
        print(' ┌──────────────────┬─────────────────────────┐')
        print(' │ 超级管理员 (可写) │ lireal / 123456         │')
        print(' │ 观赏者 (只读)    │ admin / 123456          │')
        print(' │ 观赏者 (只读)    │ user / 123456           │')
        print(' └──────────────────┴─────────────────────────┘')
        return True
    return False


if __name__ == '__main__':
    main()
    sys.exit(0)
