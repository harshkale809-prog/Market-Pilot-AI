import os
import uuid
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import settings
from app.core.database import Base, get_db
from app.models.user import User
from app.models.organization import Organization
from app.models.plan import Plan
from app.agents.tools.chroma_tool import create_secure_search_tool
from app.agents.tools.html_tool import convert_markdown_to_html

client = TestClient(app)

# Helper to generate unique identifiers
def get_unique_suffix():
    return str(uuid.uuid4())[:8]

def test_health_endpoints():
    res1 = client.get("/")
    assert res1.status_code == 200
    assert res1.json()["status"] == "ok"
    assert "MarketPilot" in res1.json()["app"] or "MARKET PILOT" in res1.json()["app"]

    res2 = client.get("/health")
    assert res2.status_code == 200
    assert res2.json()["status"] == "healthy"

def test_cors_preflight():
    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        }
    )
    assert response.status_code in [200, 204]
    assert response.headers.get("access-control-allow-origin") in ["http://localhost:5173", "*"]

def test_registration_and_login_flow():
    suffix = get_unique_suffix()
    email = f"user_{suffix}@marketpilot.ai"
    org_name = f"Org_{suffix}"
    password = "StrongPassword123!"

    # 1. Register User & Org
    reg_res = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "org_name": org_name
    })
    assert reg_res.status_code == 201, reg_res.text
    token_data = reg_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # 2. Duplicate Registration should fail
    dup_res = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": password,
        "org_name": f"Other_{suffix}"
    })
    assert dup_res.status_code == 400
    assert "already registered" in dup_res.json()["detail"].lower()

    # 3. Login with correct credentials
    login_res = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": password
    })
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()

    # 4. Login with wrong password should fail with 401
    bad_login = client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "WrongPassword999"
    })
    assert bad_login.status_code == 401

def test_multi_tenant_isolation_plans():
    suffix_a = get_unique_suffix()
    suffix_b = get_unique_suffix()

    # Register Org A
    reg_a = client.post("/api/v1/auth/register", json={
        "email": f"alice_{suffix_a}@pilot.ai",
        "password": "Password123!",
        "org_name": f"Acme_{suffix_a}"
    })
    token_a = reg_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register Org B
    reg_b = client.post("/api/v1/auth/register", json={
        "email": f"bob_{suffix_b}@pilot.ai",
        "password": "Password123!",
        "org_name": f"Beta_{suffix_b}"
    })
    token_b = reg_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Create a Plan for Org A directly through db session
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        user_a = db.query(User).filter(User.email == f"alice_{suffix_a}@pilot.ai").first()
        plan_a = Plan(
            title="Q4 Campaign Plan",
            content="<article>Secret Acme strategy</article>",
            organization_id=user_a.organization_id
        )
        db.add(plan_a)
        db.commit()
        db.refresh(plan_a)
        plan_a_id = plan_a.id
    finally:
        db.close()

    # 1. Org A can see the plan
    list_a = client.get("/api/v1/plans", headers=headers_a)
    assert list_a.status_code == 200
    plans_a = list_a.json()
    assert any(p["id"] == plan_a_id for p in plans_a)

    # 2. Org B CANNOT see Org A's plan in list
    list_b = client.get("/api/v1/plans", headers=headers_b)
    assert list_b.status_code == 200
    plans_b = list_b.json()
    assert not any(p["id"] == plan_a_id for p in plans_b)

    # 3. Org B CANNOT get Org A's plan by ID (404)
    get_b = client.get(f"/api/v1/plans/{plan_a_id}", headers=headers_b)
    assert get_b.status_code == 404

    # 4. Org B CANNOT rename Org A's plan (404)
    rename_b = client.put(f"/api/v1/plans/{plan_a_id}", headers=headers_b, json={"title": "Hacked Title"})
    assert rename_b.status_code == 404

    # 5. Org B CANNOT delete Org A's plan (404)
    del_b = client.delete(f"/api/v1/plans/{plan_a_id}", headers=headers_b)
    assert del_b.status_code == 404

    # 6. Org A CAN rename their own plan
    rename_a = client.put(f"/api/v1/plans/{plan_a_id}", headers=headers_a, json={"title": "Renamed Q4 Campaign"})
    assert rename_a.status_code == 200
    assert rename_a.json()["title"] == "Renamed Q4 Campaign"

    # 7. Org A CAN delete their own plan
    del_a = client.delete(f"/api/v1/plans/{plan_a_id}", headers=headers_a)
    assert del_a.status_code == 204

def test_document_upload_validation():
    suffix = get_unique_suffix()
    reg = client.post("/api/v1/auth/register", json={
        "email": f"doc_{suffix}@pilot.ai",
        "password": "Password123!",
        "org_name": f"DocOrg_{suffix}"
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Non-pdf rejected
    res_txt = client.post(
        "/api/v1/documents/upload/pdf",
        headers=headers,
        files={"file": ("notes.txt", b"some notes", "text/plain")}
    )
    assert res_txt.status_code == 400

    # 2. Empty PDF rejected
    res_empty = client.post(
        "/api/v1/documents/upload/pdf",
        headers=headers,
        files={"file": ("empty.pdf", b"", "application/pdf")}
    )
    assert res_empty.status_code == 400

    # 3. Invalid PDF header rejected
    res_fake = client.post(
        "/api/v1/documents/upload/pdf",
        headers=headers,
        files={"file": ("fake.pdf", b"not a real pdf content", "application/pdf")}
    )
    assert res_fake.status_code == 400

def test_markdown_to_html_converter():
    md = "# Heading 1\n\n- Task 1\n- Task 2\n\n| Day | Channel |\n|---|---|\n| Mon | Email |"
    from app.agents.tools.html_tool import render_markdown_to_html
    html = render_markdown_to_html(md)
    assert "<article class='markdown-body'>" in html
    assert "<h1>Heading 1</h1>" in html
    assert "<li>Task 1</li>" in html
    assert "<table>" in html
    assert "</article>" in html

    # Verify tool execution via .run()
    tool_result = convert_markdown_to_html.run(md)
    assert "<article class='markdown-body'>" in str(tool_result)

def test_agent_plan_mocked_execution():
    suffix = get_unique_suffix()
    reg = client.post("/api/v1/auth/register", json={
        "email": f"agent_{suffix}@pilot.ai",
        "password": "Password123!",
        "org_name": f"AgentOrg_{suffix}"
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    mock_html = "<article class='markdown-body'><h2>Productivity App Launch</h2><p>Week 1: Social Campaign</p></article>"

    with patch("app.api.agent_router.run_marketing_planner", return_value=mock_html):
        response = client.post(
            "/api/v1/agent/plan",
            headers=headers,
            json={"goal": "Launch productivity app for college students with daily schedule"}
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "success"
        assert "plan_id" in data
        assert "<article" in data["plan"]

        # Verify auto-saved plan is in history
        history_res = client.get("/api/v1/plans", headers=headers)
        assert history_res.status_code == 200
        saved_plans = history_res.json()
        assert any(p["id"] == data["plan_id"] for p in saved_plans)

def test_agent_plan_missing_keys_graceful():
    suffix = get_unique_suffix()
    reg = client.post("/api/v1/auth/register", json={
        "email": f"nokey_{suffix}@pilot.ai",
        "password": "Password123!",
        "org_name": f"NoKeyOrg_{suffix}"
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # When no keys configured and real run_marketing_planner called
    with patch.dict(os.environ, {"GROQ_API_KEY": "", "OPENROUTER_API_KEY": ""}):
        with patch("app.core.config.settings.GROQ_API_KEY", ""):
            with patch("app.core.config.settings.OPENROUTER_API_KEY", ""):
                response = client.post(
                    "/api/v1/agent/plan",
                    headers=headers,
                    json={"goal": "Launch brand new marketing campaign"}
                )
                assert response.status_code == 400
                assert "Missing AI API key" in response.json()["detail"]

def test_rag_vector_tenant_isolation():
    from app.core.vector_store import get_chroma_collection, get_embedding_model
    collection = get_chroma_collection()
    model = get_embedding_model()

    org_1_id = 99901
    org_2_id = 99902

    text_org_1 = "Confidential Acme strategy: discount pricing by 25% in Q4."
    embed_1 = model.embed_documents([text_org_1])

    # Add Org 1 doc
    collection.add(
        documents=[text_org_1],
        embeddings=embed_1,
        metadatas=[{"source": "acme_secrets.txt", "org_id": org_1_id}],
        ids=["test_doc_acme_1"]
    )

    # Org 2 search tool
    tool_org_2 = create_secure_search_tool(org_id=org_2_id)
    search_result_org_2 = tool_org_2.run("discount pricing")
    # Org 2 must NOT find Org 1's document
    assert "No relevant information found" in search_result_org_2 or "Confidential Acme strategy" not in search_result_org_2

    # Org 1 search tool
    tool_org_1 = create_secure_search_tool(org_id=org_1_id)
    search_result_org_1 = tool_org_1.run("discount pricing")
    assert "discount pricing" in search_result_org_1

