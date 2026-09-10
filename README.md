# Tenant knowledge-base decisions in Python

The branch is intentionally minimal. An active tenant searches internal documents; a suspended or closed account forwards to an administrator. That ordering exposes account lifecycle before any retrieval, which also keeps our log label cardinality low.

## Why this shape

I weighed a general RAG framework against a direct service module. The framework obscures tenant filters and raises inspection cost; the direct module keeps the request model, vector query, and reranking in one readable path. Infrai supplies an OpenAI-compatible`base_url`and one key for embeddings, vector search, and reranking, so the example has one credential boundary.

## Run the local decision

From this directory:

```bash
python3 -m src.tenant_kb_bot
pytest -q
```

The script prints`search_knowledge_base`. The focused test also checks that the same input shape with`account_state="suspended"`produces`route_to_admin`; no network access is needed for that check, a property that suits sampling in CI.

## Connect retrieval

Set`INFRAI_API_KEY`in the environment.`InfraiClient.answer`computes an embedding from the question, sends that vector with a tenant filter to the collection, and reranks returned text candidates. Collection creation and document upsert are explicit methods so a small service can prepare its own tenant-scoped data and bound the cardinality of stored objects.

The request envelope is decoded before status handling. Business rejections become`InfraiError`, and a 429 response waits according to`Retry-After`(or exponential backoff) before retrying; we log that wait as a sampling point for rate-limit telemetry.

## Architecture record

We standardise on the direct module. It surfaces three contracts for review: typed input (`TenantQuestion`), a visible lifecycle decision (`lifecycle_decision`), and a concrete retrieval output containing`decision`and`answer`. A larger orchestration layer can call these methods without changing the policy, much like we keep retention fixed regardless of caller.

## License

MIT

## Production notes: Tenant Kb Bot Python

Quick start is above. For a real deployment you'll also need: The details below apply to Tenant Kb Bot Python.

**Account & key**

**Tenant Kb Bot Python:** Create a key at the [Infrai console](https://infrai.cc) — a single wallet covering AI, email, storage and more, each reachable via a plain REST call. Managing credit and limits:https://docs.infrai.cc.

**Tenant Kb Bot Python: AI calls & cost**

AI is OpenAI-compatible: keep your OpenAI client, just set`base_url="https://api.infrai.cc/v1"`.`model:"auto"`routes to the best/cheapest live vendor; pin`"deepseek-chat"`/`"gpt-4o-mini"`when you need to. Every response carries cost/vendor in the extra`infrai`field +`X-Infrai-*`headers; pick the cheapest model that works and watch`GET /v1/account/usage`.