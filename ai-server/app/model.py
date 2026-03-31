import json
import re
from typing import Dict, Any

from openai import OpenAI


MODEL_ID = "gpt-5-mini"


class OpenAIJsonModel:
    def __init__(self) -> None:
        self.model_id = MODEL_ID
        self.client = None

    def load(self) -> None:
        if self.client is not None:
            return

        self.client = OpenAI()
        print(f"[AI] OpenAI client ready: {self.model_id}")

    def _extract_json(self, text: str) -> Dict[str, Any]:
        text = text.strip()

        try:
            return json.loads(text)
        except Exception:
            pass

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass

        return {}

    def generate_json(self, system_prompt: str, user_text: str) -> Dict[str, Any]:
        response = self.client.responses.create(
            model=self.model_id,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": system_prompt
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": user_text.strip()
                        }
                    ],
                },
            ],
        )

        raw_text = response.output_text.strip()
        parsed = self._extract_json(raw_text)

        return {
            "parsed": parsed,
            "raw_text": raw_text,
            "model_name": self.model_id,
        }


model_instance = OpenAIJsonModel()