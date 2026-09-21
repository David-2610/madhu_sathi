"""
Gemini AI Provider for Honey Chain / Madhu Sathi.

Calls Google Gemini API (with candidate model fallbacks) to provide apicultural
telemetry analysis, anomaly explanations, and beekeeper assistance.
Safely falls back to deterministic rule-based mock provider if credentials
are unconfigured or external network requests fail.
"""

import json
import logging
from typing import Any, Dict, List, Optional
import requests

from app.core.config import get_settings
from app.services.ai.base import AIExplanation, AIProvider
from app.services.ai.mock_provider import MockAIProvider

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiAIProvider(AIProvider):
    """Google Gemini AI assistance provider with multi-model fallback and safe degradation."""

    def __init__(self) -> None:
        self.api_key: Optional[str] = settings.GEMINI_API_KEY
        self.primary_model: str = getattr(settings, "GEMINI_MODEL", "gemini-3.1-flash-lite")
        self.candidate_models: List[str] = [
            self.primary_model,
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash-lite",
            "gemini-3-flash-preview",
            "gemini-flash-latest",
        ]
        # Deduplicate preserving order
        self.candidate_models = list(dict.fromkeys(self.candidate_models))
        self.provider_name: str = "GEMINI_AI"
        self._fallback_provider: MockAIProvider = MockAIProvider()

    def _build_prompt(
        self,
        hive_code: str,
        metrics_summary: Dict[str, Any],
        anomalies: List[str],
        query: Optional[str] = None,
    ) -> str:
        """Construct a structured prompt with biological rules and JSON schema constraints."""
        system_instruction = (
            "You are an expert apiculturist and beekeeping AI advisor for the Madhu Sathi "
            "(Honey Chain) smart apiculture platform. Analyze the telemetry data and provide "
            "clear, practical, and biologically sound advice for the beekeeper.\n"
            "STRICT INVARIANTS:\n"
            "1. Never declare disease certainty (telemetry anomalies reflect environmental or behavioral variations).\n"
            "2. Always emphasize practical, physical hive inspection.\n"
            "3. Provide actionable, step-by-step guidance.\n"
            "4. Respond strictly with a JSON object in this exact schema:\n"
            "{\n"
            '  "condition_summary": "Concise 1-2 sentence condition overview",\n'
            '  "explanation": "Clear explanation addressing telemetry, anomalies, or the beekeeper\'s question",\n'
            '  "recommended_steps": ["step 1", "step 2", "step 3"]\n'
            "}"
        )

        user_context = (
            f"Hive Identifier: {hive_code}\n"
            f"Telemetry Metrics: {json.dumps(metrics_summary)}\n"
            f"Detected Anomalies: {', '.join(anomalies) if anomalies else 'None'}\n"
        )
        if query:
            user_context += f"Beekeeper Question: {query}\n"

        return f"{system_instruction}\n\n{user_context}"

    def generate_explanation(
        self,
        hive_id: int,
        hive_code: str,
        metrics_summary: Dict[str, Any],
        anomalies: List[str],
        query: Optional[str] = None,
    ) -> AIExplanation:
        """Generate structured explanation using Gemini API, or fallback gracefully."""
        if not self.api_key:
            logger.warning("GEMINI_API_KEY is not configured; using deterministic fallback provider.")
            return self._fallback_provider.generate_explanation(
                hive_id=hive_id,
                hive_code=hive_code,
                metrics_summary=metrics_summary,
                anomalies=anomalies,
                query=query,
            )

        prompt = self._build_prompt(
            hive_code=hive_code,
            metrics_summary=metrics_summary,
            anomalies=anomalies,
            query=query,
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "topP": 0.85,
            },
        }

        last_error = None
        for model in self.candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
            try:
                logger.info("Calling Gemini API (model: %s) for hive %s", model, hive_code)
                response = requests.post(url, json=payload, timeout=8)

                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            raw_text = parts[0].get("text", "").strip()
                            clean_text = raw_text
                            if clean_text.startswith("```json"):
                                clean_text = clean_text[7:]
                            elif clean_text.startswith("```"):
                                clean_text = clean_text[3:]
                            if clean_text.endswith("```"):
                                clean_text = clean_text[:-3]
                            clean_text = clean_text.strip()

                            try:
                                parsed = json.loads(clean_text)
                                condition_summary = parsed.get("condition_summary") or f"Telemetry evaluation for Hive {hive_code}"
                                explanation = parsed.get("explanation") or clean_text
                                recommended_steps = parsed.get("recommended_steps") or [
                                    "Perform standard physical hive inspection.",
                                    "Verify water availability and entrance ventilation.",
                                ]
                                if isinstance(recommended_steps, str):
                                    recommended_steps = [recommended_steps]

                                return AIExplanation(
                                    condition_summary=condition_summary,
                                    explanation=explanation,
                                    recommended_steps=recommended_steps,
                                    disclaimer=(
                                        "Possible abnormal hive condition detected. Note: Telemetry anomalies indicate "
                                        "environmental or behavioral variations and do NOT constitute a confirmed disease diagnosis. "
                                        "Physical hive inspection is required."
                                    ),
                                    is_mock=False,
                                    provider="GEMINI_AI",
                                )
                            except json.JSONDecodeError:
                                logger.info("Gemini raw text was not strict JSON; using directly as explanation.")
                                return AIExplanation(
                                    condition_summary=f"Telemetry evaluation for Hive {hive_code}",
                                    explanation=clean_text,
                                    recommended_steps=[
                                        "Perform standard visual hive inspection.",
                                        "Verify ventilation and water sources.",
                                    ],
                                    disclaimer=(
                                        "Possible abnormal hive condition detected. Note: Telemetry anomalies indicate "
                                        "environmental or behavioral variations and do NOT constitute a confirmed disease diagnosis. "
                                        "Physical hive inspection is required."
                                    ),
                                    is_mock=False,
                                    provider="GEMINI_AI",
                                )
                else:
                    last_error = f"HTTP {response.status_code}: {response.text[:150]}"
                    logger.warning("Gemini model %s returned error: %s", model, last_error)

            except Exception as exc:
                last_error = str(exc)
                logger.warning("Gemini model %s call exception: %s", model, exc)

        logger.error("All Gemini API candidate models failed (last error: %s). Using fallback provider.", last_error)
        fallback = self._fallback_provider.generate_explanation(
            hive_id=hive_id,
            hive_code=hive_code,
            metrics_summary=metrics_summary,
            anomalies=anomalies,
            query=query,
        )
        return fallback

