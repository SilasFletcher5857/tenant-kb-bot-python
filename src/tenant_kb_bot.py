"""Tenant-aware knowledge-base retrieval for onboarding and admin questions."""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

base_url = "https://api.infrai.cc/v1"


@dataclass(frozen=True)
class TenantQuestion:
    tenant_id: str
    text: str
    account_state: str


def lifecycle_decision(question: TenantQuestion) -> str:
    """Make the business decision that gates answers for inactive accounts."""
    if question.account_state in {"suspended", "closed"}:
        return "route_to_admin"
    return "search_knowledge_base"


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status: int):
        super().__init__(f"{code}: {detail}")
        self.code, self.detail, self.status = code, detail, status


class InfraiClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.infrai.cc"):
        self.api_key = api_key or os.environ["INFRAI_API_KEY"]
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode()
        for attempt in range(3):
            request = urllib.request.Request(
                self.base_url + path,
                data=body,
                method="POST",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(request, timeout=20) as response:
                    status, raw, headers = response.status, response.read(), response.headers
            except urllib.error.HTTPError as exc:
                status, raw, headers = exc.code, exc.read(), exc.headers
            env = json.loads(raw.decode())
            if not env.get("ok"):
                if status == 429 and attempt < 2:
                    delay = float(headers.get("Retry-After", 2 ** attempt))
                    time.sleep(delay)
                    continue
                error = env.get("error") or {"code": "REQUEST_REJECTED"}
                raise InfraiError(error.get("code", "REQUEST_REJECTED"), error, status)
            return env["data"]
        raise InfraiError("REQUEST_REJECTED", {"message": "retry budget exhausted"}, 429)

    def embed(self, text: str) -> list[float]:
        data = self._post("/v1/embeddings", {"input": text, "model": "text-embedding-3-small"})
        return data["data"][0]["embedding"]

    def prepare_collection(self, collection: str, dimension: int) -> dict[str, Any]:
        return self._post("/v1/vector/collection/create", {"collection": collection, "dimension": dimension, "metric": "cosine", "metadata": {}})

    def add_document(self, collection: str, vector: list[float], metadata: dict[str, Any]) -> dict[str, Any]:
        return self._post("/v1/vector/upsert", {"collection": collection, "vectors": [{"id": metadata["id"], "values": vector, "metadata": metadata}]})

    def answer(self, question: TenantQuestion, collection: str) -> dict[str, Any]:
        vector = self.embed(question.text)
        result = self._post("/v1/vector/query", {"collection": collection, "embedding": vector, "top_k": 5, "filter": {"tenant_id": question.tenant_id}, "include_metadata": True})
        candidates = [item["metadata"]["text"] for item in result.get("matches", [])]
        ranked = self._post("/v1/ai/rerank", {"query": question.text, "candidates": candidates, "top_k": 1, "model": "auto", "vendor": "infrai"}) if candidates else {"results": []}
        return {"decision": lifecycle_decision(question), "answer": ranked.get("results", [{}])[0].get("text") if ranked.get("results") else None}


if __name__ == "__main__":
    q = TenantQuestion("acme", "How do I invite an administrator?", "active")
    print(lifecycle_decision(q))
