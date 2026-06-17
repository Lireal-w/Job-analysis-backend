from typing import Annotated

from fastapi import APIRouter, Path, Query

from backend.app.admin.schema.report import (
    CreateReportParam,
    CreateReportWidgetParam,
    GetReportDetail,
    GetReportWidgetDetail,
    UpdateReportParam,
    UpdateReportWidgetParam,
)
from backend.app.admin.service.report_service import report_service
from backend.common.pagination import DependsPagination, PageData
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter()


# ── 报表接口 ──────────────────────────────────────────────────


@router.get('/all', summary='获取所有报表', dependencies=[DependsJwtAuth])
async def get_all_reports(db: CurrentSession) -> ResponseSchemaModel[list[GetReportDetail]]:
    data = await report_service.get_all(db=db)
    return response_base.success(data=data)


@router.get('/{pk}', summary='获取报表详情', dependencies=[DependsJwtAuth])
async def get_report(
    db: CurrentSession,
    pk: Annotated[int, Path(description='报表 ID')],
) -> ResponseSchemaModel[GetReportDetail]:
    data = await report_service.get(db=db, pk=pk)
    return response_base.success(data=data)


@router.get(
    '',
    summary='分页获取报表列表',
    dependencies=[DependsJwtAuth, DependsPagination],
)
async def get_reports_paginated(
    db: CurrentSession,
    name: Annotated[str | None, Query(description='报表名称')] = None,
    status: Annotated[int | None, Query(description='状态(0停用 1正常)')] = None,
    is_public: Annotated[bool | None, Query(description='是否公开')] = None,
) -> ResponseSchemaModel[PageData[GetReportDetail]]:
    page_data = await report_service.get_list(db=db, name=name, status=status, is_public=is_public)
    return response_base.success(data=page_data)


@router.post('', summary='创建报表', dependencies=[DependsJwtAuth])
async def create_report(
    db: CurrentSessionTransaction,
    obj: CreateReportParam,
) -> ResponseSchemaModel[GetReportDetail]:
    data = await report_service.create(db=db, obj=obj)
    return response_base.success(data=data)


@router.put('/{pk}', summary='更新报表', dependencies=[DependsJwtAuth])
async def update_report(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='报表 ID')],
    obj: UpdateReportParam,
) -> ResponseModel:
    count = await report_service.update(db=db, pk=pk, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('', summary='批量删除报表', dependencies=[DependsJwtAuth])
async def delete_reports(
    db: CurrentSessionTransaction,
    pks: Annotated[list[int], Query(description='报表 ID 列表')],
) -> ResponseModel:
    count = await report_service.delete(db=db, pks=pks)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.get('/{pk}/preview', summary='预览报表', dependencies=[DependsJwtAuth])
async def preview_report(
    db: CurrentSession,
    pk: Annotated[int, Path(description='报表 ID')],
) -> ResponseSchemaModel[dict]:
    data = await report_service.preview_report(db=db, pk=pk)
    return response_base.success(data=data)


# ── 组件接口 ──────────────────────────────────────────────────


@router.get('/{pk}/widgets', summary='获取报表的所有组件', dependencies=[DependsJwtAuth])
async def get_report_widgets(
    db: CurrentSession,
    pk: Annotated[int, Path(description='报表 ID')],
) -> ResponseSchemaModel[list[GetReportWidgetDetail]]:
    data = await report_service.get_widgets(db=db, report_id=pk)
    return response_base.success(data=data)


@router.post('/{pk}/widgets', summary='添加组件到报表', dependencies=[DependsJwtAuth])
async def create_report_widget(
    db: CurrentSessionTransaction,
    pk: Annotated[int, Path(description='报表 ID')],
    obj: CreateReportWidgetParam,
) -> ResponseSchemaModel[GetReportWidgetDetail]:
    obj.report_id = pk
    data = await report_service.create_widget(db=db, obj=obj)
    return response_base.success(data=data)


@router.put('/widgets/{widget_id}', summary='更新报表组件', dependencies=[DependsJwtAuth])
async def update_report_widget(
    db: CurrentSessionTransaction,
    widget_id: Annotated[int, Path(description='组件 ID')],
    obj: UpdateReportWidgetParam,
) -> ResponseModel:
    count = await report_service.update_widget(db=db, widget_id=widget_id, obj=obj)
    if count > 0:
        return response_base.success()
    return response_base.fail()


@router.delete('/widgets/{widget_id}', summary='删除报表组件', dependencies=[DependsJwtAuth])
async def delete_report_widget(
    db: CurrentSessionTransaction,
    widget_id: Annotated[int, Path(description='组件 ID')],
) -> ResponseModel:
    count = await report_service.delete_widget(db=db, widget_id=widget_id)
    if count > 0:
        return response_base.success()
    return response_base.fail()
