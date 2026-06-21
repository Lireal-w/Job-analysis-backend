"""设置移动端版本管理菜单权限"""
import sys
import requests

BASE_URL = 'http://127.0.0.1:8000/api/v1'
API = {'base': BASE_URL}


def log(msg): print(f'[INFO] {msg}')
def log_step(s): print(f'\n{"="*60}\n  >>> {s}\n{"="*60}')
def log_ok(m): print(f'[SUCCESS] {m}')
def log_err(m): print(f'[ERROR] {m}')


class Client:
    def __init__(self):
        self.s = requests.Session()
        self.token = None

    def req(self, method, path, **kw):
        url = f'{API["base"]}{path}'
        h = kw.pop('headers', {})
        if self.token: h['Authorization'] = f'Bearer {self.token}'
        r = self.s.request(method, url, headers=h, **kw)
        if r.status_code >= 400: print(f'  {method} {path} -> {r.status_code}: {r.text[:150]}')
        return r

    def login(self):
        r = self.req('POST', '/auth/login/swagger?username=lireal&password=123456')
        if r.status_code != 200: log_err('Login failed'); sys.exit(1)
        self.token = r.json()['access_token']
        log_ok('Logged in as lireal')
        return True

    def get(self, p, **kw): return self.req('GET', p, **kw)
    def post(self, p, **kw): return self.req('POST', p, **kw)
    def put(self, p, **kw): return self.req('PUT', p, **kw)

    def create_menu(self, title, name, parent_id, type_, perms=None, path=None, sort=0, component=None):
        data = dict(title=title, name=name, parent_id=parent_id, sort=sort,
                    type=type_, status=1, display=1 if type_ != 2 else 0,
                    cache=1, perms=perms, path=path, icon=None, component=component,
                    link=None, remark=None)
        return self.post('/sys/menus', json=data)

    def assign_role_menus(self, role_id, menu_ids):
        return self.put(f'/sys/roles/{role_id}/menus', json={'menus': menu_ids})


def main():
    c = Client()
    c.login()

    # Get all menus
    mr = c.get('/sys/menus')
    menus = []
    def walk(items):
        for m in items:
            menus.append(m)
            if m.get('children'): walk(m['children'])
    walk(mr.json()['data'])
    names = {m['name']: m for m in menus}

    log_step('1. 创建移动端管理菜单目录')
    if 'MobileManage' in names:
        parent_id = names['MobileManage']['id']
        log(f'移动端管理菜单已存在 (ID={parent_id})')
    else:
        r = c.create_menu('移动端管理', 'MobileManage', None, 0, sort=8)
        if r.status_code != 200: log_err('创建父菜单失败'); sys.exit(1)
        # Refresh
        mr = c.get('/sys/menus')
        menus = []; walk(mr.json()['data'])
        names = {m['name']: m for m in menus}
        parent_id = names['MobileManage']['id']
        log_ok(f'创建移动端管理目录 (ID={parent_id})')

    log_step('2. 创建版本管理菜单')
    if 'AppVersion' in names:
        version_id = names['AppVersion']['id']
        log(f'版本管理菜单已存在 (ID={version_id})')
    else:
        r = c.create_menu('版本管理', 'AppVersion', parent_id, 1,
                          path='/mobile/version',
                          component='/mobile/version/index')
        if r.status_code != 200: log_err('创建版本管理菜单失败'); sys.exit(1)
        mr = c.get('/sys/menus')
        menus = []; walk(mr.json()['data'])
        names = {m['name']: m for m in menus}
        version_id = names['AppVersion']['id']
        log_ok(f'创建版本管理菜单 (ID={version_id})')

    log_step('3. 创建按钮权限')
    buttons = [
        ('新增版本', 'AddAppVersion', version_id, 'mobile:version:add'),
        ('修改版本', 'EditAppVersion', version_id, 'mobile:version:edit'),
        ('删除版本', 'DeleteAppVersion', version_id, 'mobile:version:del'),
    ]
    for title, name, pid, perms in buttons:
        if name in names:
            log(f'按钮已存在: {name}')
            continue
        r = c.create_menu(title, name, pid, 2, perms=perms)
        if r.status_code == 200:
            log_ok(f'创建按钮: {name} ({perms})')
        else:
            log_err(f'创建按钮失败: {name}')

    log_step('4. 更新菜单列表')
    mr = c.get('/sys/menus')
    menus = []; walk(mr.json()['data'])
    names = {m['name']: m for m in menus}

    # 获取观赏者角色
    roles_r = c.get('/sys/roles/all')
    if roles_r.status_code == 200:
        viewer_role = next((r for r in roles_r.json()['data'] if r['name'] == '观赏者'), None)
        if viewer_role:
            # 给观赏者角色分配查看菜单(不含按钮)
            view_ids = [m['id'] for m in menus if m['type'] != 2]
            c.assign_role_menus(viewer_role['id'], view_ids)
            log_ok(f'更新观赏者角色菜单 ({len(view_ids)} 个查看菜单)')

    # 验证
    log_step('5. 验证')
    # 创建一条测试记录
    r = c.post('/mobile/versions', json={
        'app_name': '企业App', 'platform': 0, 'version_name': '1.0.0', 'version_code': 100
    })
    if r.status_code == 200:
        ver_id = r.json()['data']['id']
        log_ok('创建测试版本成功')

        # 测试观赏者用户可查看
        vc = Client()
        r2 = vc.req('POST', '/auth/login/swagger?username=admin&password=123456')
        if r2.status_code == 200:
            vc.token = r2.json()['access_token']
            r3 = vc.req('GET', '/mobile/versions/all')
            if r3.status_code == 200:
                log_ok('观赏者可查看版本列表')
            r4 = vc.req('POST', '/mobile/versions', json={'app_name':'x','platform':0,'version_name':'0.1','version_code':999})
            if r4.status_code == 403:
                log_ok('观赏者创建版本被拒绝(403)')

        # 清理
        c.req('DELETE', '/mobile/versions', params={'pks': ver_id})
        log_ok('清理测试数据')

    log_step('✅ 完成')
    print('移动端版本管理环境就绪!')


if __name__ == '__main__':
    main()
