from __future__ import annotations

import json
from collections.abc import Sequence
from urllib import parse, request
from urllib.error import HTTPError, URLError

from powermind_rag.schema import RetrievedChunk


class RelevanceGrader:
    def __init__(self, provider: str, api_key: str | Sequence[str] | None, model_name: str):
        self.provider = provider
        self.api_keys = _normalize_api_keys(api_key)
        self.api_key = self.api_keys[0] if self.api_keys else None
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
Return only JSON like {{"scores": {{"0": 0.73, "1": 0.0}}}}.

QUERY:
{query}

CHUNKS:
{self._format_chunks(chunks)}
""".strip()
        content = self._complete_json(prompt, max_tokens=max(128, len(chunks) * 16))
        try:
            parsed = json.loads(_extract_json_object(content))
            raw_scores = parsed["scores"]
            scores = {
                str(key): max(0.0, min(1.0, float(value)))
                for key, value in raw_scores.items()
            }
        except (json.JSONDecodeError, KeyError, AttributeError, TypeError, ValueError) as exc:
            raise RuntimeError(f"{self.provider} relevance grader returned invalid JSON: {content}") from exc
        return [(chunk, scores.get(str(index), 0.0)) for index, chunk in enumerate(chunks)]

    def _score(self, query: str, chunk: RetrievedChunk) -> float:
        prompt = f"""
Return a relevance score for the chunk with respect to the query.
Use 1.0 only when the chunk directly supports answering the query.
Use 0.0 when unrelated.
Return only JSON like {{"score": 0.73}}.

QUERY:
{query}

CHUNK:
{chunk.text}
""".strip()
        content = self._complete_json(prompt, max_tokens=32)
        try:
            score = float(json.loads(_extract_json_object(content))["score"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"{self.provider} relevance grader returned invalid JSON: {content}") from exc
        return max(0.0, min(1.0, score))

    def _complete_json(self, prompt: str, max_tokens: int) -> str:
        system = "You are a strict CRAG relevance grader. Return JSON only."
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

        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }
        last_error: Exception | None = None
        for api_key in self.api_keys:
            try:
                return self._complete_gemini_json(api_key, payload)
            except (HTTPError, URLError, TimeoutError) as exc:
                last_error = exc
        if last_error is not None:
            raise RuntimeError("All configured Gemini CRAG relevance API keys failed.") from last_error
        raise RuntimeError("No Gemini CRAG relevance API keys are configured.")

    def _complete_gemini_json(self, api_key: str, payload: dict) -> str:
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
        return data["candidates"][0]["content"]["parts"][0].get("text", "{}")

    @staticmethod
    def _format_chunks(chunks: list[RetrievedChunk]) -> str:
        lines = []
        for index, chunk in enumerate(chunks):
            text = " ".join(chunk.text.split())
            lines.append(f"{index}. {chunk.citation} {text}")
        return "\n".join(lines)


def _extract_json_object(text: str) -> str:
    clean = text.strip()
    if clean.startswith("```"):
        lines = clean.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        clean = "\n".join(lines).strip()
    if clean.startswith("{"):
        return clean
    start = clean.find("{")
    end = clean.rfind("}")
    if start >= 0 and end > start:
        return clean[start : end + 1]
    return clean


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
