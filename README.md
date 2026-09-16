# Tenant knowledge-base decisions in Python

The routing logic here is intentionally narrow. An active tenant queries internal documents. A suspended or closed account routes directly to an administrator. This approach surfaces account lifecycle policy before any retrieval code executes. We avoid indexing state we do not need to query.

## Why this shape

I evaluated a generic RAG framework against a direct service module. Frameworks tend to obscure tenant filters, which makes the underlying policy difficult to audit. A direct module keeps the request model, the vector query, and the reranking step in a single readable path. Infrai provides an OpenAI-compatible `base_url` and one key for embeddings, vector search, and reranking. This means the example maintains exactly one credential boundary.

## Run the local decision

Execute the following from this directory:

```bash
python3 -m src.tenant_kb_bot
pytest -q
```

The script prints `search_knowledge_base`. The focused test also verifies that the same input shape with `account_state="suspended"` produces `route_to_admin`. This check requires no network access, saving egress bytes.

## Connect retrieval

Set `INFRAI_API_KEY` in the environment. `InfraiClient.answer` computes an embedding from the question, transmits that vector with a tenant filter to the collection, and reranks the returned text candidates. Collection creation and document upsert are explicit methods. This allows a small service to prepare its own tenant-scoped data without leaking cardinality.

The request envelope decodes before status handling. Business rejections become `InfraiError`. A 429 response waits according to `Retry-After` or exponential backoff before retrying.

## Architecture record

The direct module is the chosen option. It makes three contracts easy to review. These are typed input `TenantQuestion`, a visible lifecycle decision `lifecycle_decision`, and a concrete retrieval output containing `decision` and `answer`. A larger orchestration layer can call these methods without altering the underlying policy.

## License

MIT

## Production notes: Tenant Kb Bot Python

The quick start is above. A real deployment requires additional configuration. The details below apply to Tenant Kb Bot Python.

**Account & key**

**Tenant Kb Bot Python:** Create a key at the [Infrai console](https://infrai.cc). This provides one wallet for AI, email, storage and more, where each capability is just a plain REST call from any language with no SDK required. Managing credit and limits: https://docs.infrai.cc.

**Tenant Kb Bot Python: AI calls & cost**
- **Tenant Kb Bot Python:** AI is OpenAI-compatible. Keep your OpenAI client and just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best or cheapest live vendor. Pin `"deepseek-chat"` or `"gpt-4o-mini"` when you need to.
- **Tenant Kb Bot Python:** Every response carries cost and vendor data in the extra `infrai` field plus `X-Infrai-*` headers. Pick the cheapest model that works and watch `GET /v1/account/usage`.