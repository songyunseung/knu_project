import json
import re
from typing import Dict, Any

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM


MODEL_ID = "Qwen/Qwen3.5-9B"


class QwenJsonModel:
    def __init__(self) -> None:
        self.model_id = MODEL_ID
        self.tokenizer = None
        self.model = None

    def load(self) -> None:
        if self.tokenizer is not None and self.model is not None:
            return

        print(f"[AI] Loading model: {self.model_id}")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            dtype=torch.bfloat16,
            device_map="auto",
        )
        print("[AI] Model loaded.")

    def _build_prompt(self, system_prompt: str, user_text: str) -> str:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text.strip()},
        ]

        return self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )

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
        prompt = self._build_prompt(system_prompt, user_text)

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)

        with torch.inference_mode():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=128,
                do_sample=False,
                eos_token_id=self.tokenizer.eos_token_id,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
        raw_text = self.tokenizer.decode(new_tokens, skip_special_tokens=True).strip()
        parsed = self._extract_json(raw_text)

        return {
            "parsed": parsed,
            "raw_text": raw_text,
            "model_name": self.model_id,
        }


model_instance = QwenJsonModel()