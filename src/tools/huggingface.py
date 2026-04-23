"""Hugging Face LLM integration."""

import os
import json
from typing import Optional, Dict, Any
import httpx

from ..config.settings import HF_TOKEN, HF_MODEL


class HFLLM:
    """Hugging Face Inference API LLM."""

    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        temperature: float = 0.2,
        max_tokens: int = 2048
    ):
        self.model = model or HF_MODEL
        self.api_key = api_key or HF_TOKEN
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.base_url = "https://api-inference.huggingface.co/models/{model}"

    def _call(self, prompt: str, system_prompt: str = None) -> str:
        """Make inference request."""
        if not self.api_key:
            raise ValueError("HF_TOKEN not configured")

        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}\nAssistant:"

        url = self.base_url.format(model=self.model)
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "inputs": full_prompt,
            "parameters": {
                "temperature": self.temperature,
                "max_new_tokens": self.max_tokens,
                "return_full_text": False
            }
        }

        with httpx.Client(timeout=120.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()

            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", "")

        return ""

    def generate(self, prompt: str, system_prompt: str = None) -> str:
        """Generate text."""
        return self._call(prompt, system_prompt)

    async def agenerate(self, prompt: str, system_prompt: str = None) -> str:
        """Async generate text."""
        return self._call(prompt, system_prompt)


def create_hf_llm(temperature: float = 0.2, max_tokens: int = 2048) -> HFLLM:
    """Create Hugging Face LLM instance."""
    return HFLLM(
        model=HF_MODEL,
        api_key=HF_TOKEN,
        temperature=temperature,
        max_tokens=max_tokens
    )


def query_to_json(prompt: str, system_prompt: str = None) -> Dict[str, Any]:
    """Parse query using HF model and return JSON."""
    llm = create_hf_llm()

    default_system = """You are a job search query parser. Convert user input to JSON with:
- keywords: array of job titles/roles
- location: string or null
- remote: boolean
- experience: "fresher" | "junior" | "mid" | "senior" | null
- salary_min: number or null

Return only valid JSON, no explanation."""

    response = llm.generate(prompt, system_prompt or default_system)

    try:
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        return json.loads(response.strip())
    except json.JSONDecodeError:
        import re
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        raise


if __name__ == "__main__":
    test = "Python developer remote fresher in India"
    result = query_to_json(test)
    print(f"Input: {test}")
    print(f"Output: {result}")