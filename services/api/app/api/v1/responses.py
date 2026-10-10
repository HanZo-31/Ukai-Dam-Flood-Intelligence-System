from typing import Any

from services.api.app.api_schemas.problem import Problem


def problem_spec(description: str) -> dict[str, Any]:
    return {"description": description, "content": {
        "application/problem+json": {"schema": Problem.model_json_schema()},
    }}


ERRORS: dict[int | str, dict[str, Any]] = {
    404: problem_spec("Not found or not published"),
    422: problem_spec("Invalid request"),
    500: problem_spec("Unexpected internal failure"),
    503: problem_spec("Service unavailable"),
}
