"""移动端版本管理 API"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from backend.app.mobile.schema.app_version import (
    CreateAppVersionParam,
    GetAppVersionDetail,
    UpdateAppVersionParam,
)
from backend.app.mobile.service.app_version_service import app_version_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.common.security.permission import RequestPermission
from backend.common.security.rbac import DependsRBAC
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


@router.get('/latest', summary='获取最新版本信息', description='根据平台获取最新已发布版本，客户端检查更新用')
async def get_latest_version(
    db: CurrentSession,
    platform: Annotated[int, Query(description='平台(0安卓 1iOS 2鸿蒙)')] = 0,
) -> ResponseSchemaModel[GetAppVersionDetail | None]:
    data = await app_version_service.get_latest(db=db, platform=platform)
    return response_base.success(data=data)


@router.get('/all', summary='获取所有版本', dependencies=[DependsJwtAuth])
async def get_all_versions(
    db: CurrentSession,
) -> ResponseSchemaModel[list[GetAppVersionDetail]]:
    data = await app_version_service.get_all(db=db)
    return response_base.success(data=data)


@router.get('/{pk}', summary='获取版本详情', dependencies=[DependsJwtAuth])
async def get_version(
    db: CurrentSession,
    pk: Annotated[int, Path(description='版本 ID')],
) -> ResponseSchemaModel[GetAppVersionDetail]:
    data = await app_version_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.get(
    '',
    summary='分页获取版本列表',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_versions_paginated(
    db: CurrentSession,
    app_name: Annotated[str | None, Query(description='应用名称')] = None,
    platform: Annotated[int | None, Query(description='平台(0安卓 1iOS 2鸿蒙)')] = None,
    status: Annotated[int | None, Query(description='状态(0停用 1正常)')] = None,
    publish_status: Annotated[int | None, Query(description='发布状态(0草稿 1已发布 2已归档)')] = None,
) -> ResponseSchemaModel[PageData[GetAppVersionDetail]]:
    page_data = await app_version_service.get_list(
        db=db, app_name=app_name, platform=platform,
        status=status, publish_status=publish_status,
    )
    return response_base.success(data=page_data)


@router.post(
    '',
    summary='创建版本',
    dependencies=[
        Depends(RequestPermission('mobile:version:add')),
        DependsRBAC,
    ],
)
async def create_version(
    db: CurrentSessionTransaction,
    request: Request,
    obj: CreateAppVersionParam,
) -> ResponseSchemaModel[GetAppVersionDetail]:
    data = await app_version_service.create(db=db, obj=obj)
    return response_base.success(data=data)


@router.put(
    '/{pk}',
    summary='更新版本',
    dependencies=[
        Depends(RequestPermission('mobile:version:edit')),
        DependsRBAC,
    ],
)
async def update_version(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='版本 ID')],
    obj: UpdateAppVersionParam,
) -> ResponseModel:
    count = await app_version_service.update(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.put(
    '/{pk}/status',
    summary='更新版本状态',
    dependencies=[
        Depends(RequestPermission('mobile:version:edit')),
        DependsRBAC,
    ],
)
async def update_version_status(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='版本 ID')],
    status: Annotated[int, Query(description='状态(0停用 1正常)')],
) -> ResponseModel:
    count = await app_version_service.update(db=db, pk=pk, obj=UpdateAppVersionParam(status=status))
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete(
    '',
    summary='批量删除版本',
    dependencies=[
        Depends(RequestPermission('mobile:version:del')),
        DependsRBAC,
    ],
)
async def delete_versions(
    db: CurrentSessionTransaction,
    pks: Annotated[list[int], Query(description='版本 ID 列表')],
) -> ResponseModel:
    count = await app_version_service.delete(db=db, pks=pks)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.post('/{pk}/download', summary='记录下载次数（客户端回调）')
async def record_download(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='版本 ID')],
) -> ResponseSchemaModel[GetAppVersionDetail]:
    data = await app_version_service.record_download(db=db, pk=pk)
    return response_base.success(data=data)
