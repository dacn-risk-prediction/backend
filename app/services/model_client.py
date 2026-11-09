"""HTTP client for communicating with the external AI/ML Model Service.

Adheres strictly to .agent/rules/fastapi-backend.md (Rule 1 & Rule 6):
- Uses async def and httpx.AsyncClient for non-blocking network calls.
- Enforces explicit timeouts and standard 503 Service Unavailable handling on failures.
"""

from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import settings


class ModelServiceClient:
    """Async client managing HTTP communication with the ML Inference Service (serve.py)."""

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.MODEL_SERVICE_URL).rstrip("/")

    async def check_health(self) -> dict[str, Any]:
        """Query the Model Service /health endpoint."""
        url = f"{self.base_url}/health"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(url)
                res.raise_for_status()
                return res.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Model Service error: {e.response.text}",
            )
        except (httpx.RequestError, httpx.TimeoutException):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI Model Service is currently unavailable. Please verify it is running on port 8001.",
            )

    async def predict_course(
        self,
        student_id: str,
        course_code: str,
        semester_code: str | None = None,
    ) -> dict[str, Any]:
        """Call POST /predict/course on Model Service."""
        url = f"{self.base_url}/predict/course"
        payload: dict[str, Any] = {
            "student_id": str(student_id).strip(),
            "course_code": str(course_code).strip(),
        }
        if semester_code:
            payload["semester_code"] = str(semester_code).strip()

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == status.HTTP_404_NOT_FOUND:
                    detail = res.json().get("detail", "Student or course not found in model records.")
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
                if res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
                    detail = res.json().get("detail", "Models not yet loaded into memory.")
                    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
                res.raise_for_status()
                return res.json()
        except HTTPException:
            raise
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Model Service error: {e.response.text}",
            )
        except (httpx.RequestError, httpx.TimeoutException):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI Model Service is unreachable or timed out. Please check if serve.py is running.",
            )

    async def predict_student(
        self,
        student_id: str,
        semester_code: str | None = None,
    ) -> dict[str, Any]:
        """Call POST /predict/student on Model Service."""
        url = f"{self.base_url}/predict/student"
        payload: dict[str, Any] = {
            "student_id": str(student_id).strip(),
        }
        if semester_code:
            payload["semester_code"] = str(semester_code).strip()

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == status.HTTP_404_NOT_FOUND:
                    detail = res.json().get("detail", f"Student '{student_id}' has no registered courses in target semester.")
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
                if res.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
                    detail = res.json().get("detail", "Models not yet loaded into memory.")
                    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
                res.raise_for_status()
                return res.json()
        except HTTPException:
            raise
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Model Service error: {e.response.text}",
            )
        except (httpx.RequestError, httpx.TimeoutException):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="AI Model Service is unreachable or timed out. Please check if serve.py is running.",
            )


model_client = ModelServiceClient()
