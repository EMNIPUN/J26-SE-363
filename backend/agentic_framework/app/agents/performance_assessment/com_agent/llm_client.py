import os
import json
import time
import logging
import threading
from typing import Dict, Any, List, Optional, Tuple
import httpx
from dotenv import load_dotenv

# Ensure environment variables from .env are loaded
load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "openai/gpt-oss-120b"
FALLBACK_MODEL = "qwen/qwen3.8-27b"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqMultiKeyClient:
    def __init__(
        self,
        api_keys: Optional[List[str]] = None,
        primary_model: str = DEFAULT_MODEL,
        fallback_model: str = FALLBACK_MODEL,
        timeout: float = 45.0,
    ):
        raw_env_keys = os.getenv("GROQ_API_KEYS") or os.getenv("GROQ_API_KEY", "")
        if raw_env_keys:
            self.api_keys = [k.strip() for k in raw_env_keys.split(",") if k.strip()]
        else:
            self.api_keys = api_keys or []

        self.primary_model = os.getenv('GROQ_MODEL', primary_model)
        self.fallback_model = os.getenv('GROQ_FALLBACK_MODEL', fallback_model)
        self.timeout = timeout
        self._key_index = 0
        self._lock = threading.Lock()
        self.call_history: List[Dict[str, Any]] = []

    @property
    def current_key(self) -> str:
        with self._lock:
            return self.api_keys[self._key_index]


    def rotate_key(self, reason: str = 'rate_limit') -> Tuple[int, str]:
        with self._lock:
            old_idx = self._key_index
            self._key_index = (self._key_index + 1) % len(self.api_keys)
            new_idx = self._key_index
            logger.warning(
                f'[KEY ROTATION] Key {old_idx + 1} ({reason}). Rotated to Key {new_idx + 1}/{len(self.api_keys)}'
            )
            return new_idx, self.api_keys[new_idx]


    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
    ) -> Dict[str, Any]:
        target_model = model or self.primary_model
        max_attempts = len(self.api_keys) * 2
        last_error = None

        for attempt in range(max_attempts):
            key = self.current_key
            key_idx = self._key_index
            headers = {
                'Authorization': f'Bearer {key}',
                'Content-Type': 'application/json',
            }
            payload = {
                'model': target_model,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                'temperature': temperature,
                'max_tokens': max_tokens,
            }

            start_t = time.perf_counter()
            try:
                response = httpx.post(
                    GROQ_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )

                if response.status_code == 200:
                    data = response.json()
                    choice = data['choices'][0]
                    content = choice['message'].get('content', '')
                    reasoning = choice['message'].get('reasoning')
                    usage = data.get('usage', {})
                    elapsed = time.perf_counter() - start_t

                    record = {
                        'timestamp': time.time(),
                        'model': target_model,
                        'key_index': key_idx + 1,
                        'system_prompt': system_prompt,
                        'user_prompt': user_prompt,
                        'content': content,
                        'reasoning': reasoning,
                        'usage': usage,
                        'latency_seconds': round(elapsed, 3),
                        'status': 'SUCCESS',
                    }
                    self.call_history.append(record)
                    return record

                elif response.status_code in (429, 401, 503):
                    err_msg = response.text[:200]
                    logger.warning(
                        f'Groq API error HTTP {response.status_code} on key {key_idx + 1}: {err_msg}'
                    )
                    self.rotate_key(f'HTTP {response.status_code}')
                    time.sleep(0.5)
                    continue

                elif response.status_code == 404:
                    logger.warning(f'Model {target_model} not found. Falling back to {self.fallback_model}')
                    target_model = self.fallback_model
                    continue

                else:
                    last_error = f'HTTP {response.status_code}: {response.text}'
                    logger.warning(f'Groq API failed on key {key_idx + 1}: {last_error}')
                    self.rotate_key(f'HTTP {response.status_code}')

            except Exception as exc:
                last_error = str(exc)
                logger.warning(f'Network exception on key {key_idx + 1}: {exc}')
                self.rotate_key(f'Exception: {exc}')
                time.sleep(1.0)

        raise RuntimeError(f'All Groq API keys failed. Last error: {last_error}')

groq_client = GroqMultiKeyClient()
