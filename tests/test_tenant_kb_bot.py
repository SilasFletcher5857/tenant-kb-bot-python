from src.tenant_kb_bot import TenantQuestion, lifecycle_decision


def test_suspended_tenant_is_sent_to_admin_review():
    question = TenantQuestion("acme", "Can I export our audit log?", "suspended")
    assert lifecycle_decision(question) == "route_to_admin"


def test_active_tenant_can_search_documents():
    question = TenantQuestion("acme", "How do I invite an administrator?", "active")
    assert lifecycle_decision(question) == "search_knowledge_base"
