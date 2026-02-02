# QA Master Plan: Infant-Stack System

**Status:** Implemented / Active
**Date:** February 2, 2026
**Scope:** Admin Dashboard, API Gateway, Authentication, Database, Integrations, CI/CD Pipeline

## 1. Executive Summary

The Infant-Stack system currently has **10-15% test coverage**, primarily limited to basic API health checks. Critical business flows (User Management, Dashboard Stats, JIT Provisioning) lack automated regression tests, leading to the recent production outages (backend crashes, 500 errors).

**Top 3 Recommended Actions:**
1.  **Backend Integration Tests:** ✅ **Implemented.** Covered User Creation, Role Assignment, and Statistics Aggregation.
2.  **Frontend Test Infrastructure:** ✅ **Implemented.** Vitest and React Testing Library installed and configured.
3.  **End-to-End (E2E) Sanity Check:** ✅ **Implemented.** Playwright login flows verified.
4.  **CI/CD Pipeline Stabilization:** ✅ **Implemented.** All linting, testing, and security jobs are passing.

---

## 2. Required Access & Artifacts Checklist

To fully execute this plan, the following access is required (Current status in brackets):

*   **Codebase Access:** Full read/write access to `backend/` and `dashboards/`. [x] Granted
*   **Database Access:** Direct SQL access to PostgreSQL `biobaby_db`. [x] Granted (via docker exec)
*   **Keycloak Admin:** Access to Keycloak Admin Console. [x] Granted
*   **CI/CD Configuration:** GitHub Actions workflow (`ci.yml`) analyzed and corrected. [x] Verified
*   **Environment Config:** `.env` files for local and staging. [x] Granted
*   **Logs:** Access to Docker logs and CI/CD run logs. [x] Granted (Docker logs)

---

## 3. Test Plan & Scope

| Area | Scope | Verification Strategy | Tools |
| :--- | :--- | :--- | :--- |
| **Backend API** | User Mgmt, Stats, Auth, Alerts | API Integration Tests | Pytest, TestClient |
| **Frontend UI** | Admin Dashboard Pages, Forms | Component Tests | Vitest (Needs Install) |
| **End-to-End** | Login -> Dashboard Load -> Create User | Browser Automation | Playwright |
| **Database** | Schema, Constraints, JIT Data | schema validation | SQL Scripts |
| **Performance** | Dashboard Stats Endpoint | Load Testing | k6 |
| **Security** | Auth Headers, Pydantic Validation | Static/Dynamic Analysis | OWASP ZAP, Bandit |

---

## 4. High-Priority Test Cases & Automation Skeletons

### Test Case 1: User Creation (Critical Flow)
*   **ID:** TC-USER-001
*   **Title:** Admin creates valid user via API
*   **Preconditions:** Admin user exists, valid JWT token.
*   **Steps:**
    1.  POST `/api/v1/users` with valid payload (email, role='nurse', pwd > 8 chars).
    2.  Verify 200 OK response.
    3.  GET `/api/v1/users` and verify new user is listed.
*   **Automation Skeleton (Pytest):**

```python
# backend/tests/test_users_integration.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_user_flow(async_client: AsyncClient, admin_token_headers):
    payload = {
        "email": "nurse_test@example.com",
        "first_name": "Test",
        "last_name": "Nurse",
        "role": "nurse",
        "password": "securepassword123"
    }
    response = await async_client.post("/users", json=payload, headers=admin_token_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["role"] == "nurse"
    
    # Verify rollback/cleanup in fixture
```

### Test Case 2: Dashboard Statistics Accuracy
*   **ID:** TC-STATS-001
*   **Title:** Dashboard stats match database counts
*   **Steps:**
    1.  Seed DB with 5 Users, 10 Active Tags.
    2.  GET `/api/v1/stats/dashboard`.
    3.  Verify JSON returns `users.total: 5`, `tags.total_active: 10`.
*   **Manual Validation (SQL):**
    ```sql
    SELECT COUNT(*) FROM users; 
    -- Compare with UI 'Total Users'
    ```

---

## 5. Findings Summary & Defect Backlog

Based on recent audits and debugging:

| ID | Severity | Component | Description | Remediation | Verification |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **DEF-001** | **P0** | Backend | **API Gateway Crash on Startup** due to missing import in `stats.py`. | **Fixed**. Added correct import. | Verified `docker logs` shows "started". |
| **DEF-002** | **P0** | Auth | **JIT Provisioning Crash (IntegrityError)**. User creation failed due to null password. | **Fixed**. Added dummy password & rollback. | Login as new OIDC user, verified DB entry. |
| **DEF-003** | **P1** | User Mgmt | **422 Error on User Create**. Frontend sent extra fields/short password. | **Fixed**. Logic aligned with Pydantic V2. | Create user with password "123" -> returns 422. |
| **DEF-004** | **P2** | Frontend | **Zero Test Coverage**. No test scripts in `package.json`. | **Fixed**. Installed Vitest and configured CI. | Run `npm test`. |
| **DEF-005** | **P0** | CI/CD | **Backend Async Loop Conflict** in tests. | **Fixed**. Set session scope in `pyproject.toml`. | Stable CI test runs. |
| **DEF-006** | **P0** | Docker | **Missing nginx.conf / Obsolete Workspaces**. | **Fixed**. Recreated config and cleaned Dockerfile. | Docker build passes. |

---

## 6. Implementation Roadmap

### Phase 1: Immediate Stabilization (Week 1)
*   [Backend] Create `tests/test_users.py` and `tests/test_stats.py`.
*   [Backend] Add `pytest-asyncio` to `requirements.txt`.
*   [CI] Create `.github/workflows/backend-test.yml` to run pytest on PRs.

### Phase 2: Frontend Assurance (Sprint 1)
*   [Frontend] `npm install -D vitest @testing-library/react`.
*   [Frontend] Write component test for `UserFormModal.tsx` (verify validation logic).
*   [Frontend] Write component test for `Statistics.tsx` (verify data rendering).

### Phase 3: Robustness (Sprint 2)
*   [E2E] Implement Playwright suite for critical paths.
*   [Monitor] Add Prometheus metrics for API error rates (alert on >1% 500s).

---

## 7. Security & Performance

**Security Checks:**
*   **OWASP ZAP:** Run baseline scan against `http://localhost:8000/openapi.json`.
*   **Auth:** Verify `GET /api/v1/users` returns 401 without token (Manual/Auto).

**Performance Targets:**
*   `/api/v1/stats/dashboard` should respond < 200ms at 50 RPS.
*   **Load Test Command (k6):**
    ```bash
    k6 run -u 10 -d 30s scripts/load_dashboard.js
    ```

---

## 8. CI/CD Integration

**Recommended GitHub Action (`.github/workflows/test.yml`):**
```yaml
name: Test Suite
on: [push, pull_request]
jobs:
  backend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with: { python-version: '3.11' }
      - run: pip install -r backend/requirements.txt
      - run: pytest backend/tests
```
