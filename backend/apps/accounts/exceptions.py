from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.views import exception_handler


class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Operation conflicts with existing data."
    default_code = "conflict"


def api_exception_handler(exc, context):
    """Consistent error envelope: {"error": {"code", "status", "message", "details"}}."""
    response = exception_handler(exc, context)
    if response is None:
        return None
    data = response.data
    code = getattr(exc, "default_code", "error")
    if isinstance(data, dict) and "detail" in data and len(data) == 1:
        message, details = str(data["detail"]), {}
    else:
        message = "Validation failed." if response.status_code == 400 else "Request failed."
        details = data
    response.data = {"error": {"code": code, "status": response.status_code, "message": message, "details": details}}
    return response
