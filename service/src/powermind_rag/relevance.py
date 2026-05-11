from __future__ import annotations

import json
import re
from collections.abc import Sequence
from urllib import parse, request
from urllib.error import HTTPError, URLError

from powermind_rag.schema import RetrievedChunk


class RelevanceGrader:
    def __init__(self, provider: str, api_key: str | Sequence[str] | None, model_name: str):
        self.provider = provider
        self.api_keys = _normalize_api_keys(api_key)
        self.api_key = self.api_keys[0] if self.api_keys else None
        self._next_key = 0
        self.model_name = model_name
        self.client = None
        if provider == "groq":
            if not self.api_key:
                raise RuntimeError("GROQ_API_KEY is required for Groq CRAG relevance grading.")
            try:
                from groq import Groq
            except ImportError as exc:
                raise RuntimeError("Install groq to use Groq relevance grading.") from exc
            self.client = Groq(api_key=self.api_key)
        elif provider == "gemini":
            if not self.api_keys:
                raise RuntimeError(
                    "GEMINI_API_KEY, GEMINI_API_KEY_2, or GOOGLE_API_KEY is required for Gemini CRAG relevance grading."
                )
        else:
            raise RuntimeError("Unsupported POWERMIND_RELEVANCE_PROVIDER. Use 'groq' or 'gemini'.")

    def grade(self, query: str, chunks: list[RetrievedChunk]) -> list[tuple[RetrievedChunk, float]]:
        if not chunks:
            return []
        prompt = f"""
Return relevance scores for each chunk with respect to the query.
Use 1.0 only when the chunk directly supports answering the query.
Use 0.0 when unrelated.
Return a single minified JSON object only. Do not use markdown fences, comments, preambles, or explanations.
The object must match exactly this shape: {{"scores": {{"0": 0.73, "1": 0.0}}}}.
Include one score key for every chunk index from 0 to {len(chunks) - 1}.

QUERY:
{query}

CHUNKS:
{self._format_chunks(chunks)}
""".strip()
        content = self._complete_json(prompt, max_tokens=max(512, len(chunks) * 48))
        try:
            parsed = _parse_scores_payload(content)
            raw_scores = parsed["scores"]
            scores = {
                str(key): max(0.0, min(1.0, float(value)))
                for key, value in raw_scores.items()
            }
        except (json.JSONDecodeError, KeyError, AttributeError, TypeError, ValueError) as exc:
            raise RuntimeError(f"{self.provider} relevance grader returned invalid JSON: {content}") from exc
        return [(chunk, scores.get(str(index), 0.0)) for index, chunk in enumerate(chunks)]

    def _complete_json(self, prompt: str, max_tokens: int) -> str:
        system = (
            "You are a strict CRAG relevance grader. "
            "Return only valid JSON. No markdown, no prose, no code fences."
        )
        if self.provider == "groq":
            assert self.client is not None
            response = self.client.chat.completions.create(
                model=self.model_name,
                temperature=0,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
            )
            return response.choices[0].message.content or "{}"

        system_instruction = system
        user_prompt = prompt
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }
        errors: list[str] = []
        for api_key in self._rotated_api_keys():
            try:
                content = self._complete_gemini_json(
                    api_key=api_key,
                    payload=payload,
                    system_instruction=system_instruction,
                    user_prompt=user_prompt,
                    max_tokens=max_tokens,
                )
                _parse_scores_payload(content)
                return content
            except HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                errors.append(f"HTTP {exc.code}: {body}")
            except RuntimeError as exc:
                errors.append(str(exc))
            except (KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
                errors.append(f"malformed response: {exc}")
            except (URLError, TimeoutError) as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
        if errors:
            raise RuntimeError("All configured Gemini CRAG relevance API keys failed. " + " | ".join(errors))
        raise RuntimeError("No Gemini CRAG relevance API keys are configured.")

    def _rotated_api_keys(self) -> list[str]:
        if not self.api_keys:
            return []
        start = self._next_key
        self._next_key = (self._next_key + 1) % len(self.api_keys)
        return self.api_keys[start:] + self.api_keys[:start]

    def _complete_gemini_json(
        self,
        *,
        api_key: str,
        payload: dict,
        system_instruction: str,
        user_prompt: str,
        max_tokens: int,
    ) -> str:
        try:
            return self._complete_gemini_json_sdk(
                api_key=api_key,
                system_instruction=system_instruction,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
            )
        except ImportError:
            return self._complete_gemini_json_rest(api_key=api_key, payload=payload)

    def _complete_gemini_json_sdk(
        self,
        *,
        api_key: str,
        system_instruction: str,
        user_prompt: str,
        max_tokens: int,
    ) -> str:
        import google.generativeai as genai  # type: ignore[import-untyped]
        from google.generativeai.types import GenerationConfig  # type: ignore[import-untyped]

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            self.model_name,
            system_instruction=system_instruction,
        )
        response = model.generate_content(
            user_prompt,
            generation_config=GenerationConfig(
                temperature=0,
                max_output_tokens=max_tokens,
                response_mime_type="application/json",
            ),
        )
        return getattr(response, "text", "") or "{}"

    def _complete_gemini_json_rest(self, *, api_key: str, payload: dict) -> str:
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{parse.quote(self.model_name, safe='')}:generateContent"
            f"?key={parse.quote(api_key, safe='')}"
        )
        req = request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=60) as response:
            data = json.loads(response.read().decode("utf-8"))
        candidates = data.get("candidates") or []
        if not candidates:
            raise RuntimeError(f"Gemini {self.model_name} returned no candidates: {data}")
        content = candidates[0].get("content") or {}
        parts = content.get("parts") or []
        if not parts:
            raise RuntimeError(f"Gemini {self.model_name} returned no content parts: {data}")
        return parts[0].get("text", "{}")

    @staticmethod
    def _format_chunks(chunks: list[RetrievedChunk]) -> str:
        lines = []
        for index, chunk in enumerate(chunks):
            text = " ".join(chunk.text.split())
            if len(text) > 900:
                text = text[:897].rstrip() + "..."
            lines.append(f"{index}. {chunk.citation} {text}")
        return "\n".join(lines)


def _parse_scores_payload(text: str) -> dict:
    raw = _extract_json_object(text)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        repaired = _repair_scores_json(raw)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            scores = _extract_score_pairs(raw)
            if scores:
                return {"scores": scores}
            raise


def _extract_json_object(text: str) -> str:
    clean = text.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)\s*```", clean, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        clean = fenced.group(1).strip()
    if clean.startswith("{"):
        return clean
    start = clean.find("{")
    end = clean.rfind("}")
    if start >= 0 and end > start:
        return clean[start : end + 1]
    return clean


def _repair_scores_json(text: str) -> str:
    """
    Gemini JSON mode can still occasionally emit JavaScript-like numeric keys
    inside the scores object, e.g. {"scores": {0: 0.9, 1: 0.2}}.
    Repair only that narrow, deterministic shape.
    """
    clean = text.strip()
    clean = re.sub(r"([,{]\s*)(\d+)\s*:", r'\1"\2":', clean)
    clean = re.sub(r",\s*([}\]])", r"\1", clean)
    clean = re.sub(r"(:\s*[01](?:\.\d+)?)\s+(?=\"?\d+\"?\s*:)", r"\1, ", clean)
    return clean


def _extract_score_pairs(text: str) -> dict[str, float]:
    pairs = re.findall(
        r'["\']?(\d+)["\']?\s*:\s*([01](?:\.\d+)?)',
        text,
    )
    scores: dict[str, float] = {}
    for key, value in pairs:
        try:
            scores[str(key)] = max(0.0, min(1.0, float(value)))
        except ValueError:
            continue
    return scores


def _normalize_api_keys(api_key: str | Sequence[str] | None) -> list[str]:
    if api_key is None:
        return []
    if isinstance(api_key, str):
        candidates = [api_key]
    else:
        candidates = list(api_key)
    keys = []
    for candidate in candidates:
        if not candidate:
            continue
        key = candidate.strip()
        if key and key not in keys:
            keys.append(key)
    return keys
