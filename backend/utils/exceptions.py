from rest_framework import status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.views import exception_handler as drf_exception_handler


class BusinessError(APIException):
    """
    业务错误：HTTP 状态码为 400，响应体 code 为自定义的非 0 值。

        raise BusinessError("考试尚未开始", code=40301)
    """

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "请求无法完成"

    def __init__(self, message=None, code=1, data=None):
        super().__init__(message or self.default_detail)
        self.business_code = code
        self.data = data


def _first_message(detail):
    if isinstance(detail, dict):
        for field, value in detail.items():
            message = _first_message(value)
            return message if field in ("non_field_errors", "detail") else f"{field}: {message}"
    if isinstance(detail, list) and detail:
        return _first_message(detail[0])
    return str(detail)


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, BusinessError):
        code, message, data = exc.business_code, str(exc.detail), exc.data
    elif isinstance(exc, ValidationError):
        code, message, data = response.status_code, _first_message(exc.detail), exc.detail
    else:
        code, message, data = response.status_code, _first_message(response.data), None

    response.data = {"code": code, "message": message, "data": data}
    return response
