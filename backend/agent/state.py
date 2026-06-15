"""Worker Node 全局状态"""
from __future__ import annotations

_globals: dict = {
    'worker_id': None,
    'api_key': None,
    'running_tasks': 0,
}


def get_worker_id() -> int | None:
    return _globals.get('worker_id')


def get_api_key() -> str | None:
    return _globals.get('api_key')


def set_worker_id(worker_id: int) -> None:
    _globals['worker_id'] = worker_id


def set_api_key(api_key: str) -> None:
    _globals['api_key'] = api_key


def increment_tasks() -> None:
    _globals['running_tasks'] = _globals.get('running_tasks', 0) + 1


def decrement_tasks() -> None:
    _globals['running_tasks'] = max(0, _globals.get('running_tasks', 0) - 1)


def get_globals() -> dict:
    return _globals
