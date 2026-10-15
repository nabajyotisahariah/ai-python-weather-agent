
from fastapi.responses import JSONResponse


def generic_api_response(status_code: int, status: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"status": status, "message": message},
    )
