"""
Terminal utility to test the Gemini API integration directly.
Can be executed from terminal:
    python test_gemini_terminal.py
    python test_gemini_terminal.py --query "How to protect hives from summer heat?"
"""

import argparse
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import requests

# Load environment from .env
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")


def call_gemini_api(
    hive_code: str = "HIVE-001",
    metrics: dict = None,
    anomalies: list = None,
    query: str = None,
    model: str = MODEL,
):
    if not GEMINI_API_KEY:
        print("[ERROR] GEMINI_API_KEY not found in environment or .env file!")
        return None

    if metrics is None:
        metrics = {
            "temperature_c": 38.6,
            "humidity_percent": 68.0,
            "weight_kg": 24.5,
            "sound_level": 65.0,
            "vibration_level": 1.5,
        }

    if anomalies is None:
        anomalies = ["HIGH_TEMPERATURE (brood nest above 37°C)"]

    system_instruction = (
        "You are an expert apiculturist and beekeeping AI advisor for the Madhu Sathi "
        "(Honey Chain) smart apiculture platform. Analyze telemetry and answer beekeeper queries. "
        "IMPORTANT RULES:\n"
        "1. Never declare disease certainty (anomalies indicate environmental/behavioral variations).\n"
        "2. Always emphasize practical, physical hive inspection.\n"
        "3. Provide realistic, scientifically sound apicultural advice.\n"
        "4. Respond strictly with a JSON object in this exact structure:\n"
        "{\n"
        '  "condition_summary": "Concise 1-2 sentence condition overview",\n'
        '  "explanation": "Clear, detailed explanation of the metrics, anomalies, or user question",\n'
        '  "recommended_steps": ["step 1", "step 2", "step 3"]\n'
        "}"
    )

    user_content = (
        f"Hive Identifier: {hive_code}\n"
        f"Telemetry Metrics: {json.dumps(metrics)}\n"
        f"Detected Anomalies: {', '.join(anomalies) if anomalies else 'None'}\n"
    )
    if query:
        user_content += f"Beekeeper Question: {query}\n"

    prompt = f"{system_instruction}\n\n{user_content}"

    # Candidate models in priority order
    candidate_models = [model, "gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3-flash-preview", "gemini-flash-latest"]
    # Deduplicate preserving order
    candidate_models = list(dict.fromkeys(candidate_models))

    last_error = None
    for candidate in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{candidate}:generateContent?key={GEMINI_API_KEY}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "topP": 0.85,
            },
        }

        try:
            print(f"[*] Calling Gemini API (model: {candidate})...")
            response = requests.post(url, json=payload, timeout=8)
            if response.status_code == 200:
                result_json = response.json()
                raw_text = (
                    result_json.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                clean_text = raw_text.strip()
                if clean_text.startswith("```json"):
                    clean_text = clean_text[7:]
                elif clean_text.startswith("```"):
                    clean_text = clean_text[3:]
                if clean_text.endswith("```"):
                    clean_text = clean_text[:-3]
                clean_text = clean_text.strip()

                try:
                    parsed = json.loads(clean_text)
                    return parsed
                except json.JSONDecodeError:
                    return {
                        "condition_summary": f"Telemetry evaluation for Hive {hive_code}",
                        "explanation": clean_text,
                        "recommended_steps": [
                            "Perform standard visual hive inspection.",
                            "Verify ventilation and water sources.",
                        ],
                    }
            else:
                last_error = f"HTTP {response.status_code}: {response.text[:200]}"
                print(f"[-] Model {candidate} returned: {last_error}")
        except Exception as exc:
            last_error = str(exc)
            print(f"[-] Request to {candidate} failed: {last_error}")

    print(f"[ERROR] All candidate models failed. Last error: {last_error}")
    return None


def main():
    parser = argparse.ArgumentParser(description="Test Gemini API in terminal for Madhu Sathi")
    parser.add_argument("--query", "-q", type=str, default="Why is the hive temperature high and what should I do?", help="Custom question for the assistant")
    parser.add_argument("--hive", type=str, default="HIVE-001", help="Hive Code")
    parser.add_argument("--temp", type=float, default=38.6, help="Temperature in C")
    parser.add_argument("--humidity", type=float, default=68.0, help="Humidity percentage")
    args = parser.parse_args()

    print("=" * 60)
    print("  MADHU SATHI - GEMINI API TERMINAL TEST")
    print("=" * 60)
    print(f"Model: {MODEL}")
    print(f"AI Provider: {AI_PROVIDER}")
    print(f"Query: {args.query}")
    print("-" * 60)

    metrics = {
        "temperature_c": args.temp,
        "humidity_percent": args.humidity,
        "weight_kg": 25.0,
        "sound_level": 64.0,
        "vibration_level": 1.2,
    }
    anomalies = []
    if args.temp > 37.0:
        anomalies.append(f"HIGH_TEMPERATURE ({args.temp}°C > 37.0°C)")
    if args.humidity > 75.0 or args.humidity < 40.0:
        anomalies.append(f"ABNORMAL_HUMIDITY ({args.humidity}%)")

    result = call_gemini_api(
        hive_code=args.hive,
        metrics=metrics,
        anomalies=anomalies,
        query=args.query,
    )

    if result:
        print("\n[SUCCESS] Response from Gemini API:")
        print("+" + "-" * 58 + "+")
        print(f"Condition Summary: {result.get('condition_summary')}")
        print("\nExplanation:")
        print(result.get("explanation"))
        print("\nRecommended Steps:")
        for idx, step in enumerate(result.get("recommended_steps", []), 1):
            print(f"  {idx}. {step}")
        print("+" + "-" * 58 + "+")
    else:
        print("\n[FAIL] Could not get a response from Gemini API.")
        sys.exit(1)


if __name__ == "__main__":
    main()
