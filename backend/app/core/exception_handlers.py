"""
异常处理器模块 - 用于处理应用中的异常
"""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("defi_risk.exception_handlers")


def register_exception_handlers(app: FastAPI) -> None:
    """
    注册异常处理器

    Args:
        app: FastAPI应用实例
    """
    logger.info("注册异常处理器")

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """
        处理HTTP异常
        """
        logger.warning(f"HTTP异常: {exc.status_code} - {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"message": exc.detail, "code": exc.status_code},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """
        处理请求验证异常
        """
        errors = exc.errors()
        error_messages = [f"{error['loc'][-1]}: {error['msg']}" for error in errors]
        logger.warning(f"请求验证错误: {error_messages}")
        return JSONResponse(
            status_code=422,
            content={
                "message": "请求参数验证失败",
                "code": 422,
                "details": error_messages,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """
        处理一般异常
        """
        logger.error(f"未处理的异常: {str(exc)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"message": "服务器内部错误", "code": 500},
        )
