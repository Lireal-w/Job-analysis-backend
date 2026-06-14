from starlette.testclient import TestClient


class TestTodoTask:
    """待办任务测试"""

    def test_create_task(self, client: TestClient, token_headers: dict[str, str]) -> None:
        """测试创建任务"""
        params = {
            'title': '实现用户登录功能',
            'description': '实现JWT用户登录接口',
            'task_type': 0,
            'priority': 2,
            'source': 0,
        }
        response = client.post('/todos', json=params, headers=token_headers)
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 200
        assert data['data']['title'] == '实现用户登录功能'
        assert data['data']['task_type'] == 0
        assert data['data']['priority'] == 2
        assert data['data']['source'] == 0
        assert data['data']['status'] == 0  # TODO

    def test_create_task_with_all_fields(self, client: TestClient, token_headers: dict[str, str]) -> None:
        """测试创建完整任务"""
        params = {
            'title': '数据库设计',
            'description': '设计待办事项功能的数据库表结构',
            'task_type': 1,
            'priority': 3,
            'source': 1,
            'due_date': '2026-06-20T18:00:00+08:00',
            'tags': ['数据库', '设计'],
            'remark': '需要评审',
        }
        response = client.post('/todos', json=params, headers=token_headers)
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 200
        assert data['data']['title'] == '数据库设计'
        assert data['data']['tags'] == ['数据库', '设计']

    def test_get_today_tasks(self, client: TestClient, token_headers: dict[str, str]) -> None:
        """测试获取今日待完成任务"""
        response = client.get('/todos/today', headers=token_headers)
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 200

    def test_get_task(self, client: TestClient, token_headers: dict[str, str]) -> None:
        """测试获取任务详情"""
        # 先创建一个任务
        params = {'title': '测试任务详情'}
        create_resp = client.post('/todos', json=params, headers=token_headers)
        task_id = create_resp.json()['data']['id']

        response = client.get(f'/todos/{task_id}', headers=token_headers)
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 200
        assert data['data']['id'] == task_id
        assert data['data']['title'] == '测试任务详情'

    def test_update_task(self, client: TestClient, token_headers: dict[str, str]) -> None:
        """测试更新任务"""
        params = {'title': '更新前的任务'}
        create_resp = client.post('/todos', json=params, headers=token_headers)
        task_id = create_resp.json()['data']['id']

        update_params = {
            'title': '更新后的任务',
            'priority': 1,
            'remark': '已更新备注',
        }
        response = client.put(f'/todos/{task_id}', json=update_params, headers=token_headers)
        assert response.status_code == 200
        assert response.json()['code'] == 200

        # 验证更新结果
        get_resp = client.get(f'/todos/{task_id}', headers=token_headers)
        assert get_resp.json()['data']['title'] == '更新后的任务'

    def test_update_task_status(self, client: TestClient, token_headers: dict[str, str]) -> None:
        """测试更新任务状态"""
        params = {'title': '状态测试任务'}
        create_resp = client.post('/todos', json=params, headers=token_headers)
        task_id = create_resp.json()['data']['id']

        # 更新为进行中
        response = client.put(f'/todos/{task_id}/status?status=1', headers=token_headers)
        assert response.status_code == 200

        get_resp = client.get(f'/todos/{task_id}', headers=token_headers)
        assert get_resp.json()['data']['status'] == 1

        # 更新为已完成
        response = client.put(f'/todos/{task_id}/status?status=2', headers=token_headers)
        assert response.status_code == 200

        get_resp = client.get(f'/todos/{task_id}', headers=token_headers)
        assert get_resp.json()['data']['status'] == 2

    def test_update_task_progress(self, client: TestClient, token_headers: dict[str, str]) -> None:
        """测试更新任务进度"""
        params = {'title': '进度测试任务'}
        create_resp = client.post('/todos', json=params, headers=token_headers)
        task_id = create_resp.json()['data']['id']

        response = client.put(
            f'/todos/{task_id}/progress',
            json={'progress': 50},
            headers=token_headers,
        )
        assert response.status_code == 200

        get_resp = client.get(f'/todos/{task_id}', headers=token_headers)
        assert get_resp.json()['data']['progress'] == 50

    def test_get_tasks_paginated(self, client: TestClient, token_headers: dict[str, str]) -> None:
        """测试分页获取任务列表"""
        # 先创建几个任务
        for i in range(3):
            client.post('/todos', json={'title': f'分页测试任务{i}'}, headers=token_headers)

        response = client.get('/todos?page=1&size=10', headers=token_headers)
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 200
        assert len(data['data']['items']) >= 3

    def test_delete_task(self, client: TestClient, token_headers: dict[str, str]) -> None:
        """测试删除任务"""
        params = {'title': '待删除任务'}
        create_resp = client.post('/todos', json=params, headers=token_headers)
        task_id = create_resp.json()['data']['id']

        response = client.delete(f'/todos/{task_id}', headers=token_headers)
        assert response.status_code == 200
        assert response.json()['code'] == 200

        # 验证已删除
        get_resp = client.get(f'/todos/{task_id}', headers=token_headers)
        assert get_resp.status_code == 200
        assert get_resp.json()['code'] != 200  # 404
