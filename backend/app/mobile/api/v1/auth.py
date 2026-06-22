"""移动端认证 API"""

from fastapi import APIRouter, Depends, Request, Response
from starlette.background import BackgroundTasks

from backend.app.mobile.schema.auth import MobileLoginParam, MobileLoginToken, MobileNewToken, MobileRefreshTokenParam
from backend.app.mobile.service.auth_service import mobile_auth_service
from backend.common.response.response_schema import ResponseModel, ResponseSchemaModel, response_base
from backend.common.security.jwt import DependsJwtAuth
from backend.database.db import CurrentSession, CurrentSessionTransaction

router = APIRouter(prefix='/mobile/auth')


@router.post(
    '/login',
    summary='移动端用户登录',
    description='移动端用户使用用户名和密码登录，返回 access_token 和 refresh_token',
)
async def mobile_login(
    db: CurrentSessionTransaction,
    obj: MobileLoginParam,
    background_tasks: BackgroundTasks,
) -> ResponseSchemaModel[MobileLoginToken]:
    data = await mobile_auth_service.login(db=db, obj=obj, background_tasks=background_tasks)
    return response_base.success(data=data)


@router.post(
    '/refresh',
    summary='移动端刷新 Token',
    description='移动端使用 refresh_token 刷新 access_token',
)
async def mobile_refresh_token(
    db: CurrentSession,
    request: Request,
    obj: MobileRefreshTokenParam,
) -> ResponseSchemaModel[MobileNewToken]:
    data = await mobile_auth_service.refresh_token(db=db, request=request, obj=obj)
    return response_base.success(data=data)


@router.post(
    '/logout',
    summary='移动端用户登出',
    description='移动端用户登出，清除服务端 Token 记录',
    dependencies=[DependsJwtAuth],
)
async def mobile_logout(
    request: Request,
    response: Response,
) -> ResponseModel:
    await mobile_auth_service.logout(request=request, response=response)
    return response_base.success()
