"""
部门数据隔离测试脚本

测试场景:
1. admin 登录
2. admin 创建三个部门，每个部门有一个账户
3. admin 为每个部门创建数据源和数据集
4. 各部门账户只能访问本部门的数据源和数据集
5. 跨部门访问返回 404
"""

import sys
import time
import json
import traceback

import requests

BASE_URL = 'http://127.0.0.1:8000/api/v1'
VERBOSE = True


def log(msg: str):
    """打印日志"""
    print(f'[INFO] {msg}')


def log_step(step: str):
    """打印步骤"""
    print(f'\n{"="*60}')
    print(f'  >>> {step}')
    print(f'{"="*60}')


def log_error(msg: str):
    """打印错误"""
    print(f'[ERROR] {msg}')


def log_success(msg: str):
    """打印成功"""
    print(f'[SUCCESS] {msg}')


class APITestClient:
    """API 测试客户端"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.current_user = None

    def request(self, method: str, path: str, **kwargs):
        """发送请求"""
        url = f'{self.base_url}{path}'
        headers = kwargs.pop('headers', {})
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        if VERBOSE:
            print(f'  {method} {url}')

        resp = self.session.request(method, url, headers=headers, **kwargs)
        if VERBOSE:
            if resp.status_code >= 400:
                print(f'  -> Status: {resp.status_code}, Body: {resp.text[:500]}')
            else:
                print(f'  -> Status: {resp.status_code}')

        return resp

    def get(self, path: str, **kwargs):
        return self.request('GET', path, **kwargs)

    def post(self, path: str, **kwargs):
        return self.request('POST', path, **kwargs)

    def put(self, path: str, **kwargs):
        return self.request('PUT', path, **kwargs)

    def delete(self, path: str, **kwargs):
        return self.request('DELETE', path, **kwargs)

    def login(self, username: str, password: str):
        """登录并获取token"""
        # 尝试 swagger 登录（使用查询参数方式，兼容 FastAPI swagger 模式）
        resp = self.request(
            'POST',
            f'/auth/login/swagger?username={username}&password={password}',
        )

        if resp.status_code != 200:
            log(f'  Swagger登录失败，尝试验证码登录...')
            # Fallback: 获取验证码后登录
            captcha_resp = self.get('/auth/captcha')
            if captcha_resp.status_code == 200:
                captcha_data = captcha_resp.json().get('data', {})
                if captcha_data.get('is_enabled', True):
                    resp = self.post(
                        '/auth/login',
                        json={
                            'username': username,
                            'password': password,
                            'uuid': captcha_data.get('uuid'),
                            'captcha': captcha_data.get('code', ''),
                        },
                    )

        if resp.status_code != 200:
            log_error(f'登录失败: {resp.text}')
            return False

        data = resp.json()
        # Swagger 登录和普通登录返回格式不同
        if 'access_token' in data:
            self.token = data['access_token']
            self.current_user = data.get('user', {})
        else:
            self.token = data['data']['access_token']
            self.current_user = data['data']['user']

        log_success(f'登录成功: {username} (ID: {self.current_user.get("id", "?")})')
        # 如果是管理员，标记
        self.is_superuser = self.current_user.get('is_superuser', False)
        self.user_id = self.current_user.get('id')
        self.dept_id = self.current_user.get('dept_id')
        return True

    def create_dept(self, name: str, parent_id: int = None, sort: int = 0,
                    leader: str = None, phone: str = None, email: str = None):
        """创建部门"""
        data = {
            'name': name,
            'parent_id': parent_id,
            'sort': sort,
            'leader': leader or f'{name}负责人',
            'phone': phone or '13800138000',
            'email': email or f'{name}@test.com',
            'status': 1,
        }
        resp = self.post('/sys/depts', json=data)
        if resp.status_code != 200:
            log_error(f'创建部门失败: {resp.text}')
            return None
        log_success(f'创建部门成功: {name}')
        return self._get_dept_by_name(name)

    def _get_dept_by_name(self, name: str):
        """通过名称获取部门信息"""
        resp = self.get('/sys/depts')
        if resp.status_code != 200:
            return None
        data = resp.json()
        # 扁平化递归查找
        def find(tree, name):
            for item in tree:
                if item['name'] == name:
                    return item
                children = item.get('children')
                if children:
                    result = find(children, name)
                    if result:
                        return result
            return None
        return find(data['data'], name)

    def create_role(self, name: str, status: int = 1):
        """创建角色"""
        data = {
            'name': name,
            'status': status,
        }
        resp = self.post('/sys/roles', json=data)
        if resp.status_code != 200:
            log_error(f'创建角色失败: {resp.text}')
            return None
        log_success(f'创建角色成功: {name}')
        # 获取角色详情
        roles_resp = self.get('/sys/roles/all')
        if roles_resp.status_code == 200:
            roles = roles_resp.json()['data']
            for role in roles:
                if role['name'] == name:
                    return role
        return None

    def create_user(self, username: str, password: str, nickname: str,
                    dept_id: int, role_ids: list[int]):
        """创建用户"""
        data = {
            'username': username,
            'password': password,
            'nickname': nickname,
            'dept_id': dept_id,
            'roles': role_ids,
        }
        resp = self.post('/sys/users', json=data)
        if resp.status_code != 200:
            log_error(f'创建用户失败: {resp.text}')
            return None
        log_success(f'创建用户成功: {username}')
        return resp.json()['data']

    def create_datasource(self, name: str, db_type: str = 'mysql',
                          host: str = 'localhost', port: int = 3306,
                          database_name: str = None, username: str = None,
                          password: str = None, description: str = None,
                          dept_id: int = None):
        """创建数据源"""
        data = {
            'name': name,
            'db_type': db_type,
            'host': host,
            'port': port,
            'database_name': database_name or 'test_db',
            'username': username or 'test_user',
            'password': password or 'test_pass',
            'description': description or f'数据源-{name}',
        }
        if dept_id is not None:
            data['dept_id'] = dept_id
        resp = self.post('/sys/datasources', json=data)
        if resp.status_code != 200:
            log_error(f'创建数据源失败: {resp.text}')
            return None
        log_success(f'创建数据源成功: {name}')
        # 获取数据源ID
        all_resp = self.get('/sys/datasources/all')
        if all_resp.status_code == 200:
            items = all_resp.json()['data']
            for item in items:
                if item['name'] == name:
                    return item
        return None

    def create_dataset(self, name: str, description: str = None,
                       layer_id: int = None, source_type: str = 'manual',
                       dept_id: int = None):
        """创建数据集"""
        data = {
            'name': name,
            'description': description or f'数据集-{name}',
            'source_type': source_type,
        }
        if layer_id is not None:
            data['layer_id'] = layer_id
        if dept_id is not None:
            data['dept_id'] = dept_id
        resp = self.post('/sys/data-storage/datasets', json=data)
        if resp.status_code != 200:
            log_error(f'创建数据集失败: {resp.text}')
            return None
        log_success(f'创建数据集成功: {name}')
        # 获取数据集ID
        all_resp = self.get('/sys/data-storage/datasets/all')
        if all_resp.status_code == 200:
            items = all_resp.json()['data']
            for item in items:
                if item['name'] == name:
                    return item
        return None

    def get_datasource(self, pk: int, expect_status: int = 200):
        """获取数据源详情"""
        resp = self.get(f'/sys/datasources/{pk}')
        if resp.status_code != expect_status:
            log_error(f'获取数据源 {pk} 期望状态 {expect_status}，实际 {resp.status_code}: {resp.text[:200]}')
            return None
        if resp.status_code == 200:
            return resp.json()['data']
        return None

    def get_all_datasources(self):
        """获取所有数据源"""
        resp = self.get('/sys/datasources/all')
        if resp.status_code == 200:
            return resp.json()['data']
        return []

    def get_dataset(self, pk: int, expect_status: int = 200):
        """获取数据集详情"""
        resp = self.get(f'/sys/data-storage/datasets/{pk}')
        if resp.status_code != expect_status:
            log_error(f'获取数据集 {pk} 期望状态 {expect_status}，实际 {resp.status_code}: {resp.text[:200]}')
            return None
        if resp.status_code == 200:
            return resp.json()['data']
        return None

    def get_all_datasets(self):
        """获取所有数据集"""
        resp = self.get('/sys/data-storage/datasets/all')
        if resp.status_code == 200:
            return resp.json()['data']
        return []

    def update_datasource(self, pk: int, data: dict, expect_status: int = 200):
        """更新数据源"""
        resp = self.put(f'/sys/datasources/{pk}', json=data)
        if resp.status_code != expect_status:
            log_error(f'更新数据源 {pk} 期望状态 {expect_status}，实际 {resp.status_code}')
            return False
        return resp.status_code == 200

    def delete_datasource(self, pk: int, expect_status: int = 200):
        """删除数据源"""
        resp = self.delete(f'/sys/datasources', params={'pks': pk})
        if resp.status_code != expect_status:
            log_error(f'删除数据源 {pk} 期望状态 {expect_status}，实际 {resp.status_code}')
            return False
        return resp.status_code == 200


def main():
    """主测试流程"""
    client = APITestClient(BASE_URL)

    # ── Step 1: Admin 登录 ──────────────────────────────────
    log_step('1. Admin 登录')
    if not client.login('admin', '123456'):
        log_error('Admin 登录失败，终止测试')
        return False
    log_success(f'Admin 用户ID: {client.user_id}, 超级管理员: {client.is_superuser}')

    # ── Step 2: 创建三个部门 ─────────────────────────────────
    log_step('2. 创建三个部门')
    dept_names = ['研发部', '市场部', '财务部']
    departments = {}
    for name in dept_names:
        dept = client.create_dept(name)
        if dept is None:
            log_error(f'创建部门 {name} 失败，终止测试')
            return False
        departments[name] = dept
        log(f'  部门 {name}: ID={dept["id"]}')

    # ── Step 3: 为每个部门创建角色和用户 ──────────────────────
    log_step('3. 创建部门角色和用户')

    # 获取已有角色列表（用于后续赋予正常用户角色）
    all_roles_resp = client.get('/sys/roles/all')
    existing_roles = all_roles_resp.json()['data'] if all_roles_resp.status_code == 200 else []

    # 为每个部门创建一个角色
    dept_users = {}
    for dept_name, dept_info in departments.items():
        role_name = f'{dept_name}角色'
        role = client.create_role(role_name)
        if role is None:
            log_error(f'创建角色 {role_name} 失败')
            return False
        departments[dept_name]['role_id'] = role['id']
        log(f'  角色 {role_name}: ID={role["id"]}')

        # 创建用户
        username = f'{dept_name.lower()}user'
        nickname = f'{dept_name}用户'
        user = client.create_user(
            username=username,
            password='123456',
            nickname=nickname,
            dept_id=dept_info['id'],
            role_ids=[role['id']],
        )
        if user is None:
            log_error(f'创建用户 {username} 失败')
            return False
        dept_users[dept_name] = user
        departments[dept_name]['username'] = username
        departments[dept_name]['password'] = '123456'
        log(f'  用户 {username}: ID={user["id"]}, 部门ID={user["dept_id"]}')

    # ── Step 4: Admin 为每个部门创建数据源和数据集 ───────────
    log_step('4. Admin 为各部门创建数据源')

    dept_datasources = {}
    for dept_name in departments:
        ds_name = f'{dept_name}数据源'
        ds = client.create_datasource(
            name=ds_name,
            db_type='mysql',
            description=f'{dept_name}的数据源',
            dept_id=departments[dept_name]['id'],
        )
        if ds is None:
            # 可能名称已存在，尝试唯一名称
            import random
            ds_name = f'{dept_name}数据源_{random.randint(1000,9999)}'
            ds = client.create_datasource(
                name=ds_name,
                db_type='mysql',
                description=f'{dept_name}的数据源',
                dept_id=departments[dept_name]['id'],
            )
            if ds is None:
                log_error(f'创建数据源 {ds_name} 失败')
                return False
        dept_datasources[dept_name] = ds
        log(f'  数据源 {ds_name}: ID={ds["id"]}, 部门ID={ds.get("dept_id")}')

    log_step('5. Admin 为各部门创建数据集')

    dept_datasets = {}
    for dept_name in departments:
        ds_name = f'{dept_name}数据集'
        dset = client.create_dataset(
            name=ds_name,
            description=f'{dept_name}的数据集',
            source_type='manual',
            dept_id=departments[dept_name]['id'],
        )
        if dset is None:
            import random
            ds_name = f'{dept_name}数据集_{random.randint(1000,9999)}'
            dset = client.create_dataset(
                name=ds_name,
                description=f'{dept_name}的数据集',
                source_type='manual',
                dept_id=departments[dept_name]['id'],
            )
            if dset is None:
                log_error(f'创建数据集 {ds_name} 失败')
                return False
        dept_datasets[dept_name] = dset
        log(f'  数据集 {ds_name}: ID={dset["id"]}, 部门ID={dset.get("dept_id")}')

    # ── Step 5: Admin 验证所有数据可见 ───────────────────────
    log_step('6. Admin 验证能看到所有数据源和数据集')
    all_ds = client.get_all_datasources()
    log(f'  Admin 看到 {len(all_ds)} 个数据源')
    assert len(all_ds) >= 3, f'Admin 应该至少看到3个数据源，实际 {len(all_ds)}'

    all_dset = client.get_all_datasets()
    log(f'  Admin 看到 {len(all_dset)} 个数据集')
    assert len(all_dset) >= 3, f'Admin 应该至少看到3个数据集，实际 {len(all_dset)}'

    # ── Step 6: 各部门用户验证数据隔离 ───────────────────────
    log_step('7. 各部门用户验证数据隔离')

    test_results = []

    for dept_name in dept_users:
        username = departments[dept_name]['username']
        password = departments[dept_name]['password']

        log(f'\n  --- 测试 {dept_name} ({username}) ---')

        # 使用部门用户登录
        dept_client = APITestClient(BASE_URL)
        if not dept_client.login(username, password):
            log_error(f'{username} 登录失败')
            continue

        user_info = dept_client.current_user
        log(f'  用户部门ID: {user_info.get("dept_id")}, 超级管理员: {user_info.get("is_superuser")}')

        # 验证能看到本部门数据源
        own_ds = dept_client.get_all_datasources()
        own_ds_ids = [ds['id'] for ds in own_ds]
        expected_ds_id = dept_datasources[dept_name]['id']
        log(f'  本部门数据源IDs: {own_ds_ids}, 期望ID: {expected_ds_id}')

        if expected_ds_id in own_ds_ids:
            log_success(f'{dept_name} 能访问本部门数据源 ✓')
            test_results.append(True)
        else:
            log_error(f'{dept_name} 不能访问本部门数据源 ✗')
            test_results.append(False)

        # 验证能看到本部门数据集
        own_dset = dept_client.get_all_datasets()
        own_dset_ids = [d['id'] for d in own_dset]
        expected_dset_id = dept_datasets[dept_name]['id']
        log(f'  本部门数据集IDs: {own_dset_ids}, 期望ID: {expected_dset_id}')

        if expected_dset_id in own_dset_ids:
            log_success(f'{dept_name} 能访问本部门数据集 ✓')
            test_results.append(True)
        else:
            log_error(f'{dept_name} 不能访问本部门数据集 ✗')
            test_results.append(False)

        # 验证跨部门数据源不可见（返回404）
        for other_dept in departments:
            if other_dept == dept_name:
                continue
            other_ds_id = dept_datasources[other_dept]['id']
            result = dept_client.get_datasource(other_ds_id, expect_status=404)
            if result is None:
                log_success(f'{dept_name} 访问 {other_dept} 数据源 {other_ds_id} 返回 404 ✓')
                test_results.append(True)
            else:
                log_error(f'{dept_name} 访问 {other_dept} 数据源 {other_ds_id} 没有返回 404 ✗')
                test_results.append(False)

            # 尝试获取详情
            other_dset_id = dept_datasets[other_dept]['id']
            result = dept_client.get_dataset(other_dset_id, expect_status=404)
            if result is None:
                log_success(f'{dept_name} 访问 {other_dept} 数据集 {other_dset_id} 返回 404 ✓')
                test_results.append(True)
            else:
                log_error(f'{dept_name} 访问 {other_dept} 数据集 {other_dset_id} 没有返回 404 ✗')
                test_results.append(False)

        # 验证跨部门数据源不在列表中
        for other_dept in departments:
            if other_dept == dept_name:
                continue
            other_ds_id = dept_datasources[other_dept]['id']
            if other_ds_id in own_ds_ids:
                log_error(f'{dept_name} 的列表包含 {other_dept} 数据源 {other_ds_id} ✗')
                test_results.append(False)
            else:
                log_success(f'{dept_name} 列表不包含 {other_dept} 数据源 ✓')

            other_dset_id = dept_datasets[other_dept]['id']
            if other_dset_id in own_dset_ids:
                log_error(f'{dept_name} 的列表包含 {other_dept} 数据集 {other_dset_id} ✗')
                test_results.append(False)
            else:
                log_success(f'{dept_name} 列表不包含 {other_dept} 数据集 ✓')

    # ── 结果汇总 ──────────────────────────────────────────
    log_step('测试结果汇总')
    passed = sum(1 for r in test_results if r)
    total = len(test_results)
    log(f'通过: {passed}/{total}')
    if passed == total:
        log_success('所有测试通过！')
    else:
        log_error(f'有 {total - passed} 个测试失败')

    # ── Step 7: 清理测试数据（可选）────────────────────────
    if '--keep-data' not in sys.argv:
        log_step('8. 清理测试数据')
        # 用 admin 删除创建的数据源、数据集、用户、角色、部门
        log('清理数据...')

        # 因项目中可能存在外键约束，按从下到上删除
        for dept_name in departments:
            # 删除数据源
            ds_id = dept_datasources[dept_name]['id']
            client.delete_datasource(ds_id)
            log(f'  删除数据源 {ds_id}')

            # 删除数据集
            dset_id = dept_datasets[dept_name]['id']
            client.delete(f'/sys/data-storage/datasets', params={'pks': dset_id})
            log(f'  删除数据集 {dset_id}')

        for dept_name in departments:
            # 删除用户
            user_id = dept_users[dept_name]['id']
            client.delete(f'/sys/users/{user_id}')
            log(f'  删除用户 {user_id}')

            # 删除角色
            role_id = departments[dept_name]['role_id']
            client.delete(f'/sys/roles', json={'pks': [role_id]})
            log(f'  删除角色 {role_id}')

        for dept_name in departments:
            # 删除部门
            dept_id = departments[dept_name]['id']
            client.delete(f'/sys/depts/{dept_id}')
            log(f'  删除部门 {dept_id}')

        log_success('清理完成')
    else:
        log_step('8. 清理测试数据')
        log('跳过清理（--keep-data 参数），保留测试数据')

    return passed == total


if __name__ == '__main__':
    success = main()
    if success:
        print('\n' + '='*60)
        print('  所有测试通过！部门数据隔离工作正常。')
        print('='*60)
        sys.exit(0)
    else:
        print('\n' + '='*60)
        print('  测试有失败项，请检查日志。')
        print('='*60)
        sys.exit(1)
