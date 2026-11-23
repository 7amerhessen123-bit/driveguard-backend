from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError


class AppError(Exception):
    def __init__(self, status, code, message, field=None):
        self.status = status
        self.code = code
        self.message = message
        self.field = field


def error_body(code, message, field=None):
    err = {"code": code, "message": message}
    if field:
        err["field"] = field
    return {"error": err}


def register_handlers(app):
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, e: AppError):
        return JSONResponse(error_body(e.code, e.message, e.field), status_code=e.status)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, e: RequestValidationError):
        first = e.errors()[0]
        field = str(first["loc"][-1]) if first["loc"] else None
        return JSONResponse(error_body("ERROR_VALIDATION", first["msg"], field), status_code=422)