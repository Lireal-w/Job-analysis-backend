import asyncio
import io

from collections.abc import Sequence
from typing import Any

import paramiko

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from backend.app.admin.crud.crud_ssh import ssh_dao
from backend.app.admin.model import ServerSSH
from backend.app.admin.schema.ssh import CreateSSHParam, SSHTestConnectionParam, UpdateSSHParam
from backend.common.exception import errors
from backend.common.pagination import paging_data


class SSHService:
    """SSH 服务器服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> ServerSSH:
        """
        获取服务器详情

        :param db: 数据库会话
        :param pk: 服务器 ID
        :return:
        """
        server = await ssh_dao.get(db, pk)
        if not server:
            raise errors.NotFoundError(msg='SSH 服务器不存在')
        return server

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[ServerSSH]:
        """
        获取所有服务器

        :param db: 数据库会话
        :return:
        """
        return await ssh_dao.get_all(db)

    @staticmethod
    async def get_list(*, db: AsyncSession, name: str | None) -> dict[str, Any]:
        """
        获取服务器列表

        :param db: 数据库会话
        :param name: 服务器名称
        :return:
        """
        select = await ssh_dao.get_select(name=name)
        return await paging_data(db, select)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateSSHParam) -> None:
        """
        创建服务器

        :param db: 数据库会话
        :param obj: 创建服务器参数
        :return:
        """
        server = await ssh_dao.get_by_name(db, obj.name)
        if server:
            raise errors.ConflictError(msg='SSH 服务器名称已存在')
        await ssh_dao.create(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateSSHParam) -> int:
        """
        更新服务器

        :param db: 数据库会话
        :param pk: 服务器 ID
        :param obj: 更新服务器参数
        :return:
        """
        server = await ssh_dao.get(db, pk)
        if not server:
            raise errors.NotFoundError(msg='SSH 服务器不存在')
        return await ssh_dao.update(db, pk, obj)

    @staticmethod
    async def update_status(*, db: AsyncSession, pk: int, status: int) -> int:
        """
        更新服务器状态

        :param db: 数据库会话
        :param pk: 服务器 ID
        :param status: 状态
        :return:
        """
        server = await ssh_dao.get(db, pk)
        if not server:
            raise errors.NotFoundError(msg='SSH 服务器不存在')
        return await ssh_dao.update_status(db, pk, status)

    @staticmethod
    async def delete(*, db: AsyncSession, pks: list[int]) -> int:
        """
        批量删除服务器

        :param db: 数据库会话
        :param pks: 服务器 ID 列表
        :return:
        """
        return await ssh_dao.delete(db, pks)

    @staticmethod
    async def test_connection(*, obj: SSHTestConnectionParam) -> dict[str, Any]:
        """
        测试 SSH 服务器连接

        通过 paramiko 建立 SSH 连接并执行简单的 uname 命令验证连通性

        :param obj: 测试连接参数
        :return: 连接结果
        """
        try:
            result = await run_in_threadpool(_sync_test_connection, obj)
            return result
        except Exception as e:
            return {
                'success': False,
                'message': f'连接失败: {str(e)}',
            }


def _sync_test_connection(obj: SSHTestConnectionParam) -> dict[str, Any]:
    """
    同步执行 SSH 连接测试（在线程池中运行）

    :param obj: 测试连接参数
    :return: 连接结果
    """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs: dict[str, Any] = {
        'hostname': obj.host,
        'port': obj.port,
        'username': obj.username,
        'timeout': 10,
        'allow_agent': False,
        'look_for_keys': False,
    }

    if obj.password:
        connect_kwargs['password'] = obj.password
    elif obj.ssh_key:
        key_file = io.StringIO(obj.ssh_key)
        try:
            connect_kwargs['pkey'] = paramiko.RSAKey.from_private_key(key_file)
        except paramiko.SSHException:
            try:
                key_file.seek(0)
                connect_kwargs['pkey'] = paramiko.Ed25519Key.from_private_key(key_file)
            except paramiko.SSHException:
                raise errors.RequestError(msg='SSH 密钥格式无效，请使用 RSA 或 Ed25519 格式')

    try:
        client.connect(**connect_kwargs)
        transport = client.get_transport()
        if not transport or not transport.is_active():
            return {'success': False, 'message': '连接失败: 无法建立 SSH 传输通道'}

        # 执行简单命令验证
        stdin, stdout, stderr = client.exec_command('uname -a', timeout=5)
        output = stdout.read().decode('utf-8').strip()
        error = stderr.read().decode('utf-8').strip()

        client.close()

        if error:
            return {
                'success': True,
                'message': '连接成功',
                'data': {
                    'os_info': output,
                    'warning': error,
                },
            }

        return {
            'success': True,
            'message': '连接成功',
            'data': {
                'os_info': output,
            },
        }
    except paramiko.AuthenticationException:
        return {'success': False, 'message': '认证失败: 用户名或密码错误'}
    except paramiko.SSHException as e:
        return {'success': False, 'message': f'SSH 连接异常: {str(e)}'}
    except TimeoutError:
        return {'success': False, 'message': '连接超时: 无法在 10 秒内建立连接'}
    except OSError as e:
        return {'success': False, 'message': f'网络错误: {str(e)}'}


ssh_service: SSHService = SSHService()
