"""On-demand Grounded AI Academic Advisor service with PII stripping, DB caching, and fallback."""

import hashlib
import json
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.core.config import settings
from app.repositories import ai_advice_cache_repo

logger = logging.getLogger(__name__)

GEMINI_INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"


def _extract_gemini_text(data: dict[str, Any]) -> str | None:
    """Extract text from Interactions API (`steps` / `outputs`) or legacy `candidates`."""
    steps_text = "".join(
        content.get("text", "")
        for step in data.get("steps") or []
        if step.get("type") == "model_output"
        for content in step.get("content") or []
        if content.get("type") == "text"
    ).strip()
    if steps_text:
        return steps_text

    outputs_text = "".join(
        output.get("text", "")
        for output in data.get("outputs") or []
        if output.get("type") == "text" and output.get("text")
    ).strip()
    if outputs_text:
        return outputs_text

    candidates = data.get("candidates") or []
    if candidates:
        parts = (candidates[0].get("content") or {}).get("parts") or []
        legacy_text = "\n".join(part.get("text", "") for part in parts if part.get("text")).strip()
        if legacy_text:
            return legacy_text
    return None


class GeminiKeyRotator:
    """Thread-safe round-robin API key rotator with per-request failover across all keys."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._index = 0

    def reset(self) -> None:
        """Reset rotation cursor (useful for deterministic tests)."""
        with self._lock:
            self._index = 0

    def next_rotation(self, keys: list[str]) -> list[str]:
        """Return keys starting from the next round-robin position and advance cursor."""
        if not keys:
            return []
        with self._lock:
            start = self._index % len(keys)
            self._index = (start + 1) % len(keys)
        return keys[start:] + keys[:start]


key_rotator = GeminiKeyRotator()

SYSTEM_INSTRUCTION = (
    "Bạn là cố vấn học vụ thân thiện và chính xác cho sinh viên đại học. "
    "Hãy viết 3-4 gạch đầu dòng súc tích bằng tiếng Việt (Markdown) giải thích tình hình môn học "
    "và lộ trình cải thiện thực tế dựa HOÀN TOÀN vào JSON kỹ thuật được cung cấp. "
    "Quy tắc bắt buộc: chỉ sử dụng đúng các con số điểm, xác suất và trọng số có trong JSON, "
    "tuyệt đối không tự tính lại hoặc bịa thêm con số mới; diễn đạt tự nhiên, khích lệ, không lặp khuôn mẫu."
)


def compute_advice_input_hash(cf_result: dict[str, Any]) -> str:
    """Compute a deterministic SHA-256 hash of student course state and recourse plans."""
    baseline = cf_result.get("baseline") or {}
    recommendations = cf_result.get("recommendations") or []
    plans = cf_result.get("plans") or []

    canonical_payload = {
        "student_id": cf_result.get("student_id"),
        "course_code": cf_result.get("course_code"),
        "semester_code": cf_result.get("semester_code"),
        "target_goal": cf_result.get("target_goal"),
        "current_marks": baseline.get("current_marks") or {},
        "scenario_codes": [rec.get("scenario_code") for rec in recommendations],
        "top_plan_changes": [plan.get("changes") or {} for plan in plans[:3]],
    }
    serialized = json.dumps(canonical_payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_anonymized_prompt_payload(cf_result: dict[str, Any]) -> dict[str, Any]:
    """Strip all PII (student_id, names, emails) leaving only anonymous technical metrics."""
    baseline = cf_result.get("baseline") or {}
    recommendations = cf_result.get("recommendations") or []
    shap_factors = cf_result.get("top_shap_factors") or []

    return {
        "course_code": cf_result.get("course_code"),
        "target_goal": cf_result.get("target_goal"),
        "risk_level": baseline.get("risk_level"),
        "fail_probability": baseline.get("fail_probability"),
        "predicted_score10": baseline.get("predicted_score10"),
        "current_marks": baseline.get("current_marks") or {},
        "weights": baseline.get("weights") or {},
        "plans": cf_result.get("plans") or [],
        "final_exam_targets": cf_result.get("final_exam_targets") or {},
        "recommendations": [
            {
                "scenario_code": rec.get("scenario_code"),
                "targets": rec.get("targets") or {},
                "can_withdraw_hint": bool(rec.get("can_withdraw_hint", False)),
            }
            for rec in recommendations
        ],
        "top_shap_factors": [
            {
                "feature": f.get("feature"),
                "shap_value": f.get("shap_value"),
                "impact": f.get("impact"),
                "description": f.get("description"),
            }
            for f in shap_factors
        ],
    }


def build_fallback_advice_markdown(cf_result: dict[str, Any]) -> str:
    """Assemble deterministic Vietnamese Markdown advice from Model Service recommendations & plans."""
    lines: list[str] = []
    recommendations = cf_result.get("recommendations") or []
    plans = cf_result.get("plans") or []
    exam_targets = cf_result.get("final_exam_targets") or {}

    for rec in recommendations[:2]:
        title = rec.get("title") or rec.get("scenario_code")
        message = rec.get("message") or ""
        if title and message:
            lines.append(f"- **{title}**: {message}")
        elif message:
            lines.append(f"- {message}")

    if plans:
        best = plans[0]
        changes = best.get("changes") or {}
        target_parts = ", ".join(f"`{k}` = {v}" for k, v in changes.items() if v is not None)
        if target_parts:
            lines.append(
                f"- **Kế hoạch gợi ý ({best.get('title', 'Phương án 1')})**: "
                f"Mục tiêu {target_parts} để đạt điểm dự kiến **{best.get('projected_score10')}** "
                f"(xếp loại `{best.get('projected_letter_grade')}`)."
            )

    pass_score = exam_targets.get("pass_score")
    if pass_score is not None:
        lines.append(f"- **Mốc điểm thi cuối kỳ**: Cần tối thiểu **{pass_score}/10** để qua môn.")
    elif exam_targets.get("is_pass_feasible") is False:
        lines.append("- **Lưu ý điểm cuối kỳ**: Điểm số hiện tại khiến việc qua môn bằng thi cuối kỳ rất khó khăn; hãy trao đổi sớm với giảng viên/cố vấn học tập.")

    if not lines:
        baseline = cf_result.get("baseline") or {}
        lines.append(
            f"- Điểm dự kiến hiện tại là **{baseline.get('predicted_score10', 'N/A')}** "
            f"(mức rủi ro `{baseline.get('risk_level', 'UNKNOWN')}`). Hãy duy trì tiến độ học tập và liên hệ cố vấn nếu cần hỗ trợ."
        )

    return "\n".join(lines[:4])


async def call_gemini_api(anonymized_payload: dict[str, Any]) -> str | None:
    """Call Gemini Interactions API rotating across configured keys; return None if all fail."""
    rotated_keys = key_rotator.next_rotation(settings.gemini_api_keys)
    if not rotated_keys:
        return None

    prompt_body = {
        "model": settings.GEMINI_MODEL,
        "system_instruction": SYSTEM_INSTRUCTION,
        "input": (
            "Dưới đây là dữ liệu phân tích môn học (đã ẩn danh). "
            "Hãy đưa ra lời khuyên ngắn gọn theo đúng hướng dẫn:\n"
            + json.dumps(anonymized_payload, ensure_ascii=False)
        ),
        "generation_config": {
            "thinking_level": settings.GEMINI_THINKING_LEVEL,
        },
    }

    async with httpx.AsyncClient(timeout=settings.GEMINI_TIMEOUT_SECONDS) as client:
        for attempt, api_key in enumerate(rotated_keys, start=1):
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": api_key,
            }
            try:
                res = await client.post(
                    GEMINI_INTERACTIONS_URL,
                    json=prompt_body,
                    headers=headers,
                )
                if res.status_code != 200:
                    logger.warning(
                        "Gemini Interactions API key attempt %s/%s returned HTTP %s; rotating.",
                        attempt,
                        len(rotated_keys),
                        res.status_code,
                    )
                    continue
                text = _extract_gemini_text(res.json())
                if text:
                    return text
            except (httpx.RequestError, httpx.TimeoutException, ValueError, KeyError, TypeError) as exc:
                logger.warning(
                    "Gemini Interactions API key attempt %s/%s failed (%s); rotating.",
                    attempt,
                    len(rotated_keys),
                    type(exc).__name__,
                )
                continue

    return None


async def generate_grounded_advice(
    db: Session,
    cf_result: dict[str, Any],
    *,
    force_refresh: bool = False,
) -> dict[str, Any]:
    """Resolve advice via DB cache, anonymized Gemini call, or deterministic fallback."""
    recommendations = cf_result.get("recommendations") or []
    primary_scenario = (
        recommendations[0].get("scenario_code") if recommendations else None
    ) or "GENERAL"
    input_hash = compute_advice_input_hash(cf_result)
    now = datetime.now(timezone.utc)

    if not force_refresh:
        cached = await run_in_threadpool(
            ai_advice_cache_repo.get_valid_by_hash,
            db,
            input_hash,
            now=now,
        )
        if cached:
            return {
                "course_code": cf_result.get("course_code"),
                "course_name": cf_result.get("course_name"),
                "semester_code": cf_result.get("semester_code"),
                "target_goal": cf_result.get("target_goal"),
                "scenario_code": cached.scenario_code,
                "advice_markdown": cached.advice_markdown,
                "source": "cache",
                "model_name": cached.model_name,
                "cached_at": cached.created_at,
            }

    anonymized_payload = build_anonymized_prompt_payload(cf_result)
    advice_text = await call_gemini_api(anonymized_payload)

    if advice_text:
        expires_at = now + timedelta(days=settings.AI_ADVICE_CACHE_TTL_DAYS)
        saved = await run_in_threadpool(
            ai_advice_cache_repo.upsert,
            db,
            input_hash=input_hash,
            student_id=str(cf_result.get("student_id")),
            course_code=str(cf_result.get("course_code")),
            semester_code=str(cf_result.get("semester_code")),
            scenario_code=primary_scenario,
            advice_markdown=advice_text,
            model_name=settings.GEMINI_MODEL,
            expires_at=expires_at,
            now=now,
        )
        return {
            "course_code": cf_result.get("course_code"),
            "course_name": cf_result.get("course_name"),
            "semester_code": cf_result.get("semester_code"),
            "target_goal": cf_result.get("target_goal"),
            "scenario_code": primary_scenario,
            "advice_markdown": saved.advice_markdown,
            "source": "gemini",
            "model_name": settings.GEMINI_MODEL,
            "cached_at": saved.created_at,
        }

    return {
        "course_code": cf_result.get("course_code"),
        "course_name": cf_result.get("course_name"),
        "semester_code": cf_result.get("semester_code"),
        "target_goal": cf_result.get("target_goal"),
        "scenario_code": primary_scenario,
        "advice_markdown": build_fallback_advice_markdown(cf_result),
        "source": "fallback",
        "model_name": None,
        "cached_at": None,
    }
