from starlette.testclient import TestClient


class TestTodoGoal:
    """任务目标测试"""

    def _create_task(self, client: TestClient, token_headers: dict[str, str]) -> int:
        """辅助方法: 创建任务并返回ID"""
        params = {'title': '目标测试任务'}
        response = client.post('/todos', json=params, headers=token_headers)
        return response.json()['data']['id']

    def test_create_goal(self, client: TestClient, token_headers: dict[str, str]) -> None:
        """测试创建目标"""
        task_id = self._create_task(client, token_headers)
        params = {
            'task_id': task_id,
            'title': '需求分析',
            'description': '分析功能需求',
            'stage_order': 0,
        }
        response = client.post('/todo-goals', json=params, headers=token_headers)
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 200
        assert data['data']['title'] == '需求分析'
        assert data['data']['stage_order'] == 0
        assert data['data']['status'] == 0  # PENDING

    def test_get_goals_by_task(self, client: TestClient, token_headers: dict[str, str]) -> None:
        """测试获取任务的所有目标"""
        task_id = self._create_task(client, token_headers)

        # 创建多个目标
        for i in range(3):
            client.post(
                '/todo-goals',
                json={'task_id': task_id, 'title': f'阶段{i}', 'stage_order': i},
                headers=token_headers,
            )

        response = client.get(f'/todo-goals/by-task/{task_id}', headers=token_headers)
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 200
        assert len(data['data']) == 3

    def test_get_goal(self, client: TestClient, token_headers: dict[str, str]) -> None:
        """测试获取目标详情"""
        task_id = self._create_task(client, token_headers)
        params = {'task_id': task_id, 'title': '单个目标', 'stage_order': 1}
        create_resp = client.post('/todo-goals', json=params, headers=token_headers)
        goal_id = create_resp.json()['data']['id']

        response = client.get(f'/todo-goals/{goal_id}', headers=token_headers)
        assert response.status_code == 200
        assert response.json()['data']['id'] == goal_id

    def test_update_goal_status(self, client: TestClient, token_headers: dict[str, str]) -> None:
        """测试更新目标状态"""
        task_id = self._create_task(client, token_headers)
        params = {'task_id': task_id, 'title': '状态测试目标'}
        create_resp = client.post('/todo-goals', json=params, headers=token_headers)
        goal_id = create_resp.json()['data']['id']

        # 更新为进行中
        response = client.put(
            f'/todo-goals/{goal_id}/status',
            json={'status': 1},
            headers=token_headers,
        )
        assert response.status_code == 200

        # 更新为已完成
        response = client.put(
            f'/todo-goals/{goal_id}/status',
            json={'status': 2},
            headers=token_headers,
        )
        assert response.status_code == 200
        get_resp = client.get(f'/todo-goals/{goal_id}', headers=token_headers)
        assert get_resp.json()['data']['status'] == 2

    def test_ai_generate_goals(self, client: TestClient, token_headers: dict[str, str]) -> None:
        """测试AI自动生成阶段性目标"""
        params = {
            'title': '开发用户管理模块',
            'description': '包括用户CRUD, 权限管理, 角色分配功能的前后端开发',
        }
        create_resp = client.post('/todos', json=params, headers=token_headers)
        task_id = create_resp.json()['data']['id']

        response = client.post(f'/todo-goals/ai-generate/{task_id}', headers=token_headers)
        assert response.status_code == 200
        data = response.json()
        assert data['code'] == 200
        assert len(data['data']) > 0
        # 验证目标包含标准软件开发阶段
        titles = [goal['title'] for goal in data['data']]
        assert '需求分析' in titles
        assert '方案设计' in titles
        assert '核心功能实现' in titles

    def test_delete_goal(self, client: TestClient, token_headers: dict[str, str]) -> None:
        """测试删除目标"""
        task_id = self._create_task(client, token_headers)
        params = {'task_id': task_id, 'title': '待删除目标'}
        create_resp = client.post('/todo-goals', json=params, headers=token_headers)
        goal_id = create_resp.json()['data']['id']

        response = client.delete(f'/todo-goals/{goal_id}', headers=token_headers)
        assert response.status_code == 200

        # 验证已删除
        get_resp = client.get(f'/todo-goals/{goal_id}', headers=token_headers)
        assert get_resp.json()['code'] != 200
