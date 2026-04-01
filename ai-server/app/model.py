import json
import re
from typing import Dict, Any

from openai import OpenAI
from openai import APIError, APITimeoutError, RateLimitError

from app.config import settings
from app.exceptions import ModelNotReadyError, ModelResponseError


class OpenAIJsonModel:
    def __init__(self) -> None:
        self.model_id = settings.OPENAI_MODEL
        self.client: OpenAI | None = None

    def load(self) -> None:
        if self.client is not None:
            return

        self.client = OpenAI(timeout=settings.OPENAI_TIMEOUT)
        print(f"[AI] OpenAI client ready: {self.model_id}")

    def _ensure_loaded(self) -> None:
        if self.client is None:
            raise ModelNotReadyError("OpenAI client is not initialized.")

    def _extract_json(self, text: str) -> Dict[str, Any]:
        text = text.strip()
        if not text:
            raise ModelResponseError("Empty model response.")

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError as e:
                raise ModelResponseError(f"Invalid JSON format: {e}") from e

        raise ModelResponseError("No JSON object found in model response.")

    def generate_json(self, system_prompt: str, user_text: str) -> Dict[str, Any]:
        self._ensure_loaded()

        try:
            response = self.client.responses.create(
                model=self.model_id,
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": system_prompt}],
                    },
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": user_text.strip()}],
                    },
                ],
                max_output_tokens=settings.OPENAI_MAX_OUTPUT_TOKENS,
            )
        except (APIError, APITimeoutError, RateLimitError) as e:
            raise ModelResponseError(f"OpenAI API call failed: {e}") from e
        except Exception as e:
            raise ModelResponseError(f"Unexpected model error: {e}") from e

        raw_text = (response.output_text or "").strip()
        parsed = self._extract_json(raw_text)

        return {
            "parsed": parsed,
            "raw_text": raw_text,
            "model_name": self.model_id,
        }
    def generate_json(self, system_prompt: str, user_text: str) -> Dict[str, Any]:
        self._ensure_loaded()

        try:
            response = self.client.responses.create(
                model=self.model_id,
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": system_prompt}],
                    },
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": user_text.strip()}],
                    },
                ],
                max_output_tokens=settings.OPENAI_MAX_OUTPUT_TOKENS,
                reasoning={"effort": "low"},
            )
        except (APIError, APITimeoutError, RateLimitError) as e:
            raise ModelResponseError(f"OpenAI API call failed: {e}") from e
        except Exception as e:
            raise ModelResponseError(f"Unexpected model error: {e}") from e

        print("[DEBUG] response.status =", getattr(response, "status", None))
        print("[DEBUG] response.output_text =", repr(getattr(response, "output_text", "")))
        print("[DEBUG] response =", response.model_dump_json(indent=2))

        raw_text = (response.output_text or "").strip()
        parsed = self._extract_json(raw_text)

        return {
            "parsed": parsed,
            "raw_text": raw_text,
            "model_name": self.model_id,
        }


model_instance = OpenAIJsonModel()