"""米游社 API 客户端

封装米游社 BBS 的 HTTP API 调用，包括：
- 帖子列表、帖子详情
- 用户信息
- DS 签名生成
- Cookie 管理
"""

from __future__ import annotations

import hashlib
import random
import time
from typing import Any


class MiHoYoApiError(Exception):
    """米游社 API 错误"""


class MiHoYoApiClient:
    """米游社 API 客户端

    职责纯粹: 封装 API 层面的调用，不关心采集逻辑。
    反爬策略（频率限制、重试）由 BaseCrawler 统一处理。

    使用方式:
        client = MiHoYoApiClient(cookies='...', game_id=2)
        posts = await client.get_forum_posts(forum_id=49, page=1)
    """

    # 米游社 BBS API 基础地址
    BASE_URL = 'https://bbs-api.miyoushe.com'

    # API 路径
    API_POST_LIST = '/post/api/getForumPostList'
    API_POST_DETAIL = '/post/api/getPostFull'
    API_USER_INFO = '/user/api/getUserFullInfo'
    API_GAME_RECORD = '/game_record/app/api/'

    # DS Salt (不同版本可能有变动)
    # 当前 BBS API v2.70.1 的 salt
    # 如失效请更新: 从米游社 Web 页面抓取
    _DS_SALT = 'xV8v4Qu54lUKrEYFZkJhB8QOhmF6s3Sn'

    def __init__(
        self,
        cookies: str | dict[str, str],
        game_id: int = 2,
    ):
        self.cookies = self._parse_cookies(cookies)
        self.game_id = game_id

    # ── 公开 API ──

    async def get_forum_posts(
        self,
        forum_id: int = 0,
        page: int = 1,
        page_size: int = 20,
        sort_type: int = 1,
    ) -> dict[str, Any]:
        """获取版块帖子列表

        Args:
            forum_id: 版块 ID (0=综合, 49=官方, 56=同人)
            page: 页码
            page_size: 每页条数 (1-50)
            sort_type: 排序 (1=最新, 2=热门)

        Returns:
            米游社 API 原始响应数据
        """
        params = {
            'gids': self.game_id,
            'page_size': page_size,
            'page_num': page,
            'sort_type': sort_type,
        }
        if forum_id > 0:
            params['fid'] = forum_id

        return await self._get(self.API_POST_LIST, params)

    async def get_post_detail(self, post_id: str) -> dict[str, Any]:
        """获取帖子详情"""
        return await self._get(self.API_POST_DETAIL, {'post_id': post_id})

    async def get_user_info(self, uid: str) -> dict[str, Any]:
        """获取用户信息"""
        return await self._get(self.API_USER_INFO, {'uid': uid})

    # ── 内部请求 ──

    async def _get(self, path: str, params: dict) -> dict[str, Any]:
        """发送 GET 请求到米游社 API（由采集器调用）

        本方法不直接发起 HTTP，而是返回请求参数，
        由 BaseCrawler 的 fetch_json 统一执行。
        """
        # 这个方法设计为被爬虫 reader 调用，
        # reader 再通过 base 的 fetch_json 发出请求
        raise NotImplementedError(
            '请通过 BaseCrawler 子类的 fetch_json 方法调用\n'
            '示例:\n'
            '  headers = client.get_headers()\n'
            '  data = await self.fetch_json(\n'
            '      f"{client.BASE_URL}{path}",\n'
            '      params=params, headers=headers, cookies=client.cookies,\n'
            '  )'
        )

    # ── 请求头 / 签名 ──

    def get_headers(self) -> dict[str, str]:
        """构造米游社 API 请求头（含 DS 签名）"""
        timestamp = int(time.time())
        random_str = self._random_hex(6)
        ds = self._generate_ds(timestamp, random_str)

        return {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            ),
            'Referer': 'https://www.miyoushe.com/',
            'Origin': 'https://www.miyoushe.com',
            'x-rpc-client_type': '4',
            'x-rpc-app_version': '2.70.1',
            'x-rpc-sdk_version': '2.0.0',
            'x-rpc-device_id': self._random_hex(32),
            'x-rpc-sys_info': 'Windows 10.0.19045',
            'x-rpc-device_name': self._random_text(8),
            'x-rpc-device_model': 'PC',
            'DS': ds,
        }

    def get_cookies_dict(self) -> dict[str, str]:
        """获取 Cookie 字典（可直接传给 httpx/AsyncFetcher）"""
        return self.cookies

    # ── 辅助方法 ──

    def _generate_ds(self, timestamp: int, random_str: str) -> str:
        """生成米游社 DS 签名

        算法: MD5(f'salt={salt}&t={timestamp}&r={random_str}')
        """
        sign_text = f'salt={self._DS_SALT}&t={timestamp}&r={random_str}'
        sign = hashlib.md5(sign_text.encode()).hexdigest()
        return f'{timestamp},{random_str},{sign}'

    @staticmethod
    def _parse_cookies(cookies: str | dict[str, str]) -> dict[str, str]:
        if isinstance(cookies, dict):
            return cookies
        result = {}
        for item in cookies.split(';'):
            item = item.strip()
            if '=' in item:
                key, value = item.split('=', 1)
                result[key.strip()] = value.strip()
        return result

    @staticmethod
    def _random_hex(length: int) -> str:
        return ''.join(random.choices('0123456789abcdef', k=length))

    @staticmethod
    def _random_text(length: int) -> str:
        return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=length))

    @staticmethod
    def extract_posts(data: dict[str, Any]) -> list[dict[str, Any]]:
        """从 API 响应中提取帖子列表，统一字段名"""
        post_list = data.get('data', {}).get('list', [])
        results = []
        for item in post_list:
            post = item.get('post', {})
            user = item.get('user', {})
            stat = item.get('stat', {})
            forum = item.get('forum', {})
            results.append({
                # 帖子信息
                'post_id': str(post.get('post_id', '')),
                'title': post.get('subject', '') or '',
                'content': post.get('content', '') or '',
                'cover': post.get('cover_url', '') or '',
                'created_at': post.get('created_at', 0),
                'view_count': stat.get('view_num', 0),
                'like_count': stat.get('like_num', 0),
                'reply_count': stat.get('reply_num', 0),
                'bookmark_count': stat.get('bookmark_num', 0),
                'share_count': stat.get('share_num', 0),
                # 用户信息
                'uid': str(user.get('uid', '')),
                'nickname': user.get('nickname', '') or '',
                'avatar': user.get('avatar_url', '') or '',
                'level': user.get('level', 0),
                # 版块信息
                'forum_id': forum.get('id', 0),
                'forum_name': forum.get('name', '') or '',
                # 游戏信息
                'game_id': data.get('data', {}).get('gids', 0),
            })
        return results

    @staticmethod
    def check_response(data: dict[str, Any]) -> None:
        """检查 API 响应状态码

        Raises:
            MiHoYoApiError: 当 retcode != 0 时
        """
        retcode = data.get('retcode', -1)
        if retcode != 0:
            msg = data.get('message', '未知错误')
            if retcode == 1008:
                raise MiHoYoApiError('登录失效，请更新 Cookie')
            elif retcode == 10101:
                raise MiHoYoApiError('请求太频繁，请降低采集频率')
            elif retcode == -100:
                raise MiHoYoApiError('请求签名错误 (DS invalid)')
            else:
                raise MiHoYoApiError(f'API 错误 [{retcode}]: {msg}')
