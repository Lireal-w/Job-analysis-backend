from collections.abc import Sequence
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.admin.crud.crud_report import report_dao, report_widget_dao
from backend.app.admin.model import Report, ReportWidget
from backend.app.admin.schema.report import (
    CreateReportParam,
    CreateReportWidgetParam,
    GetReportWidgetDetail,
    UpdateReportParam,
    UpdateReportWidgetParam,
)
from backend.common.exception import errors
from backend.common.pagination import paging_data


class ReportService:
    """报表服务类"""

    @staticmethod
    async def get(*, db: AsyncSession, pk: int) -> Report:
        report = await report_dao.get(db, pk)
        if not report:
            raise errors.NotFoundError(msg='报表不存在')
        return report

    @staticmethod
    async def get_all(*, db: AsyncSession) -> Sequence[Report]:
        return await report_dao.get_all(db)

    @staticmethod
    async def get_list(
        *, db: AsyncSession, name: str | None = None, status: int | None = None, is_public: bool | None = None
    ) -> dict[str, Any]:
        select = await report_dao.get_select(name=name, status=status, is_public=is_public)
        page_data = await paging_data(db, select)
        return page_data

    @staticmethod
    async def create(*, db: AsyncSession, obj: CreateReportParam) -> Report:
        existing = await report_dao.get_by_name(db, obj.name)
        if existing:
            raise errors.ConflictError(msg='报表名称已存在')
        return await report_dao.create(db, obj)

    @staticmethod
    async def update(*, db: AsyncSession, pk: int, obj: UpdateReportParam) -> int:
        report = await report_dao.get(db, pk)
        if not report:
            raise errors.NotFoundError(msg='报表不存在')
        if obj.name is not None:
            existing = await report_dao.get_by_name(db, obj.name)
            if existing and existing.id != pk:
                raise errors.ConflictError(msg='报表名称已存在')
        return await report_dao.update(db, pk, obj)

    @staticmethod
    async def delete(*, db: AsyncSession, pks: list[int]) -> int:
        return await report_dao.delete(db, pks)

    @staticmethod
    async def get_widgets(*, db: AsyncSession, report_id: int) -> Sequence[ReportWidget]:
        """获取报表的所有组件"""
        return await report_widget_dao.get_by_report(db, report_id)

    @staticmethod
    async def create_widget(*, db: AsyncSession, obj: CreateReportWidgetParam) -> ReportWidget:
        """为报表添加组件"""
        report = await report_dao.get(db, obj.report_id)
        if not report:
            raise errors.NotFoundError(msg='报表不存在')
        return await report_widget_dao.create(db, obj)

    @staticmethod
    async def update_widget(*, db: AsyncSession, widget_id: int, obj: UpdateReportWidgetParam) -> int:
        """更新报表组件"""
        widget = await report_widget_dao.get(db, widget_id)
        if not widget:
            raise errors.NotFoundError(msg='报表组件不存在')
        return await report_widget_dao.update(db, widget_id, obj)

    @staticmethod
    async def delete_widget(*, db: AsyncSession, widget_id: int) -> int:
        """删除报表组件"""
        return await report_widget_dao.delete(db, [widget_id])

    @staticmethod
    async def preview_report(*, db: AsyncSession, pk: int) -> dict[str, Any]:
        """预览报表（返回报表信息及所有组件数据）"""
        report = await report_dao.get(db, pk)
        if not report:
            raise errors.NotFoundError(msg='报表不存在')
        widgets = await report_widget_dao.get_by_report(db, pk)
        # 为每个组件填充模拟数据
        widget_list = []
        for widget in widgets:
            widget_list.append({
                'id': widget.id,
                'widget_type': widget.widget_type,
                'title': widget.title,
                'query_id': widget.query_id,
                'query_sql': widget.query_sql,
                'config': widget.config,
                'position': widget.position,
                'sort': widget.sort,
                # 模拟数据
                'data': _generate_mock_widget_data(widget.widget_type),
            })
        return {
            'id': report.id,
            'name': report.name,
            'description': report.description,
            'layout': report.layout,
            'theme': report.theme,
            'refresh_interval': report.refresh_interval,
            'is_public': report.is_public,
            'status': report.status,
            'widgets': widget_list,
        }


def _generate_mock_widget_data(widget_type: str) -> dict[str, Any]:
    """生成模拟组件数据"""
    mock_data = {
        'bar': {
            'categories': ['一月', '二月', '三月', '四月', '五月', '六月'],
            'series': [{'name': '销售额', 'data': [120, 200, 150, 80, 70, 110]}],
        },
        'line': {
            'categories': ['Q1', 'Q2', 'Q3', 'Q4'],
            'series': [{'name': '趋势', 'data': [30, 45, 38, 52]}],
        },
        'pie': {
            'series': [
                {'name': '分类A', 'value': 35},
                {'name': '分类B', 'value': 25},
                {'name': '分类C', 'value': 20},
                {'name': '分类D', 'value': 20},
            ],
        },
        'scatter': {
            'series': [{'name': '分布', 'data': [[10, 30], [20, 45], [30, 38], [40, 52], [50, 48]]}],
        },
        'area': {
            'categories': ['周一', '周二', '周三', '周四', '周五', '周六', '周日'],
            'series': [{'name': '访问量', 'data': [820, 932, 901, 934, 1290, 1330, 1320]}],
        },
        'table': {
            'columns': ['序号', '名称', '数值', '状态'],
            'rows': [
                [1, '项目A', 100, '已完成'],
                [2, '项目B', 200, '进行中'],
                [3, '项目C', 150, '已取消'],
            ],
        },
        'stat': {
            'value': 12345,
            'unit': '次',
            'change': 12.5,
            'changeType': 'up',
        },
        'map': {
            'series': [
                {'name': '北京', 'value': 480},
                {'name': '上海', 'value': 320},
                {'name': '广州', 'value': 280},
            ],
        },
        'heatmap': {
            'categories': ['周一', '周二', '周三'],
            'series': ['上午', '下午', '晚上'],
            'data': [
                [10, 15, 8],
                [20, 25, 12],
                [15, 18, 6],
            ],
        },
        'radar': {
            'indicators': [
                {'name': '效率', 'max': 100},
                {'name': '质量', 'max': 100},
                {'name': '成本', 'max': 100},
                {'name': '速度', 'max': 100},
                {'name': '安全', 'max': 100},
            ],
            'series': [{'name': '当前', 'data': [85, 92, 78, 88, 95]}],
        },
        'funnel': {
            'series': [
                {'name': '曝光', 'value': 1000},
                {'name': '点击', 'value': 600},
                {'name': '转化', 'value': 300},
                {'name': '成交', 'value': 100},
            ],
        },
        'gauge': {
            'value': 75,
            'max': 100,
            'unit': '%',
        },
    }
    return mock_data.get(widget_type, {})


report_service: ReportService = ReportService()
