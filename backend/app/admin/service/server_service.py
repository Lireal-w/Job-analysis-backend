import asyncio
import io
import socket
from collections.abc import Sequence
from typing import Any
from urllib import request as urllib_request
from urllib.error import URLError

import paramiko

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from backend.app.admin.crud.crud_server import server_dao
from backend.app.admin.model import Server
from backend.app.admin.schema.server import CreateServerParam, TestConnectionParam, UpdateServerParam
from backend.common.enums import ProtocolType
from backend.common.exception import errors
from backend.common.pagination import paging_data


class ServerService:
    """服务器管理服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> Server:
        server = await server_dao.get(db, pk)
        if not server:
            raise errors.NotFoundError(msg='服务器不存在')
        return server

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[Server]:
        return await server_dao.get_all(db)

    @staticmethod
    async def get_list(
        *, db: AsyncSession, name: str | None = None, protocol: str | None = None
    ) -> dict[str, Any]:
        select = await server_dao.get_select(name=name, protocol=protocol)
        return await paging_data(db, select)

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateServerParam) -> None:
        server = await server_dao.get_by_name(db, obj.name)
        if server:
            raise errors.ConflictError(msg='服务器名称已存在')
        await server_dao.create(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateServerParam) -> int:
        server = await server_dao.get(db, pk)
        if not server:
            raise errors.NotFoundError(msg='服务器不存在')
        return await server_dao.update(db, pk, obj)

    @staticmethod
    async def update_status(*, db: AsyncSession, pk: int, status: int) -> int:
        server = await server_dao.get(db, pk)
        if not server:
            raise errors.NotFoundError(msg='服务器不存在')
        return await server_dao.update_status(db, pk, status)

    @staticmethod
    async def delete(*, db: AsyncSession, pks: list[int]) -> int:
        return await server_dao.delete(db, pks)

    @staticmethod
    async def test_connection(*, obj: TestConnectionParam) -> dict[str, Any]:
        """
        测试服务器连接

        根据不同的协议类型，采用对应的连接测试方式：
        - SSH / SFTP: paramiko
        - Telnet: socket 连接测试
        - RDP / VNC: socket 端口检测
        - HTTP / HTTPS: HTTP HEAD 请求
        """
        protocol_testers = {
            ProtocolType.SSH: _test_ssh,
            ProtocolType.SFTP: _test_sftp,
            ProtocolType.TELNET: _test_telnet,
            ProtocolType.RDP: _test_socket,
            ProtocolType.VNC: _test_socket,
            ProtocolType.HTTP: _test_http,
            ProtocolType.HTTPS: _test_http,
        }

        tester = protocol_testers.get(obj.protocol)
        if not tester:
            return {'success': False, 'message': f'不支持的协议类型: {obj.protocol}'}

        try:
            result = await run_in_threadpool(tester, obj)
            return result
        except Exception as e:
            return {'success': False, 'message': f'连接失败: {str(e)}'}


# ── 各协议连接测试函数 ──────────────────────────────────────────


def _test_ssh(obj: TestConnectionParam) -> dict[str, Any]:
    """测试 SSH 连接"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs: dict[str, Any] = {
        'hostname': obj.host,
        'port': obj.port,
        'username': obj.username or 'root',
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
                return {'success': False, 'message': 'SSH 密钥格式无效，请使用 RSA 或 Ed25519 格式'}

    try:
        client.connect(**connect_kwargs)
        transport = client.get_transport()
        if not transport or not transport.is_active():
            return {'success': False, 'message': '连接失败: 无法建立 SSH 传输通道'}

        stdin, stdout, stderr = client.exec_command('uname -a', timeout=5)
        output = stdout.read().decode('utf-8').strip()
        error = stderr.read().decode('utf-8').strip()
        client.close()

        result = {'success': True, 'message': 'SSH 连接成功', 'data': {'os_info': output}}
        if error:
            result['data']['warning'] = error
        return result
    except paramiko.AuthenticationException:
        return {'success': False, 'message': 'SSH 认证失败: 用户名或密码错误'}
    except paramiko.SSHException as e:
        return {'success': False, 'message': f'SSH 连接异常: {str(e)}'}
    except OSError as e:
        return {'success': False, 'message': f'SSH 网络错误: {str(e)}'}
    finally:
        client.close()


def _test_sftp(obj: TestConnectionParam) -> dict[str, Any]:
    """测试 SFTP 连接（基于 SSH，额外验证 SFTP 协议可用）"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    connect_kwargs: dict[str, Any] = {
        'hostname': obj.host,
        'port': obj.port,
        'username': obj.username or 'root',
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
                return {'success': False, 'message': 'SSH 密钥格式无效'}

    try:
        client.connect(**connect_kwargs)
        sftp = client.open_sftp()
        cwd = sftp.getcwd()
        sftp.close()
        client.close()
        return {'success': True, 'message': 'SFTP 连接成功', 'data': {'cwd': cwd or '/'}}
    except paramiko.AuthenticationException:
        return {'success': False, 'message': 'SFTP 认证失败: 用户名或密码错误'}
    except PermissionError:
        return {'success': False, 'message': 'SFTP 权限不足'}
    except Exception as e:
        return {'success': False, 'message': f'SFTP 连接失败: {str(e)}'}
    finally:
        client.close()


def _test_telnet(obj: TestConnectionParam) -> dict[str, Any]:
    """测试 Telnet 连接（基于 socket）"""
    protocol_name = obj.protocol.upper()
    try:
        sock = socket.create_connection((obj.host, obj.port), timeout=10)
        # 读取 banner 信息
        sock.settimeout(3)
        banner = b''
        try:
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                banner += chunk
        except socket.timeout:
            pass
        sock.close()
        decoded = banner.decode('utf-8', errors='ignore')[:500]
        return {
            'success': True,
            'message': f'{protocol_name} 连接成功',
            'data': {'banner': decoded} if decoded else {},
        }
    except ConnectionRefusedError:
        return {'success': False, 'message': f'{protocol_name} 连接被拒绝'}
    except TimeoutError:
        return {'success': False, 'message': f'{protocol_name} 连接超时'}
    except OSError as e:
        return {'success': False, 'message': f'{protocol_name} 连接失败: {str(e)}'}


def _test_socket(obj: TestConnectionParam) -> dict[str, Any]:
    """通过 Socket 端口检测测试连接（用于 RDP / VNC）"""
    protocol_name = obj.protocol.upper()
    try:
        sock = socket.create_connection((obj.host, obj.port), timeout=10)
        sock.close()
        return {'success': True, 'message': f'{protocol_name} 端口连接成功'}
    except ConnectionRefusedError:
        return {'success': False, 'message': f'{protocol_name} 连接被拒绝'}
    except TimeoutError:
        return {'success': False, 'message': f'{protocol_name} 连接超时'}
    except OSError as e:
        return {'success': False, 'message': f'{protocol_name} 连接失败: {str(e)}'}


def _test_http(obj: TestConnectionParam) -> dict[str, Any]:
    """测试 HTTP/HTTPS 连接"""
    protocol = obj.protocol.value
    url = f'{protocol}://{obj.host}:{obj.port}'
    try:
        req = urllib_request.Request(url, method='HEAD')
        with urllib_request.urlopen(req, timeout=10) as resp:
            status = resp.status
            headers = dict(resp.headers.items())
        return {
            'success': 200 <= status < 500,
            'message': f'HTTP 连接成功 (状态码: {status})' if 200 <= status < 500 else f'HTTP 返回异常状态码: {status}',
            'data': {'status_code': status, 'headers': headers},
        }
    except URLError as e:
        return {'success': False, 'message': f'HTTP 请求失败: {str(e.reason)}'}
    except TimeoutError:
        return {'success': False, 'message': 'HTTP 连接超时'}
    except Exception as e:
        return {'success': False, 'message': f'HTTP 连接失败: {str(e)}'}


server_service: ServerService = ServerService()
