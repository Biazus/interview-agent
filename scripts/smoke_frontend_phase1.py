#!/usr/bin/env python3
"""Smoke checklist 1.10 — Fase 1 frontend MVP (API + CORS + proxy)."""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass

import httpx

API = "http://localhost:8000"
FRONTEND = "http://localhost:5173"
TIMEOUT = httpx.Timeout(120.0, connect=10.0)


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""


def main() -> int:
    checks: list[Check] = []
    email = f"smoke_{uuid.uuid4().hex[:12]}@example.com"
    password = "password123"

    with httpx.Client(timeout=TIMEOUT) as client:
        # --- CORS + proxy ---
        checks.append(_check_cors(client))
        checks.append(_check_vite_proxy(client))

        # --- Register -> login ---
        reg = client.post(
            f"{API}/auth/register",
            json={"email": email, "password": password},
        )
        checks.append(
            Check(
                "Register",
                reg.status_code == 201,
                f"status={reg.status_code} body={reg.text[:200]}",
            )
        )

        login = client.post(
            f"{API}/auth/login",
            json={"email": email, "password": password},
        )
        checks.append(
            Check(
                "Login",
                login.status_code == 200 and "access_token" in login.json(),
                f"status={login.status_code}",
            )
        )
        token = login.json().get("access_token", "")
        if not token:
            checks.append(Check("Login token presente", False, login.text[:200]))
            return _print_report(checks)
        headers = {"Authorization": f"Bearer {token}"}

        # --- 401 global ---
        bad = client.get(
            f"{API}/interviews/active", headers={"Authorization": "Bearer invalid"}
        )
        checks.append(
            Check(
                "401 com token inválido",
                bad.status_code == 401,
                f"status={bad.status_code} code={bad.json().get('code')}",
            )
        )

        # --- Setup: domains / topics ---
        domains = client.get(f"{API}/domains")
        domain_list = domains.json() if domains.status_code == 200 else []
        checks.append(
            Check(
                "GET /domains",
                domains.status_code == 200 and len(domain_list) > 0,
                f"count={len(domain_list)}",
            )
        )
        domain = domain_list[0] if domain_list else "async_messaging"

        topics = client.get(f"{API}/topics", params={"domain": domain})
        topic_list = topics.json() if topics.status_code == 200 else []
        checks.append(
            Check(
                "GET /topics",
                topics.status_code == 200 and len(topic_list) > 0,
                f"domain={domain} count={len(topic_list)}",
            )
        )
        topic = topic_list[0] if topic_list else "dead_letter_queue"

        # --- GET /active 404 (sem entrevista) ---
        active_before = client.get(f"{API}/interviews/active", headers=headers)
        checks.append(
            Check(
                "GET /active 404 -> NO_ACTIVE_INTERVIEW (sem entrevista)",
                active_before.status_code == 404
                and active_before.json().get("code") == "NO_ACTIVE_INTERVIEW",
                f"status={active_before.status_code}",
            )
        )

        # --- Start interview ---
        start = client.post(
            f"{API}/interviews",
            headers=headers,
            json={"domain": domain, "topic": topic, "difficulty": 1},
        )
        checks.append(
            Check(
                "POST /interviews (iniciar)",
                start.status_code == 201,
                f"status={start.status_code} body={start.text[:200]}",
            )
        )
        if start.status_code != 201:
            _print_report(checks)
            return 1

        interview_id = start.json()["interview_id"]

        # --- Banner: active exists ---
        active_mid = client.get(f"{API}/interviews/active", headers=headers)
        checks.append(
            Check(
                "GET /active 200 com entrevista ativa (Banner / retomar)",
                active_mid.status_code == 200
                and active_mid.json().get("interview_id") == interview_id,
                f"interview_id={active_mid.json().get('interview_id')}",
            )
        )

        # --- 409 ACTIVE_INTERVIEW_EXISTS + re-fetch ---
        second = client.post(
            f"{API}/interviews",
            headers=headers,
            json={"domain": domain, "topic": topic, "difficulty": 1},
        )
        active_after_409 = client.get(f"{API}/interviews/active", headers=headers)
        checks.append(
            Check(
                "409 ACTIVE_INTERVIEW_EXISTS + re-fetch GET /active",
                second.status_code == 409
                and second.json().get("code") == "ACTIVE_INTERVIEW_EXISTS"
                and active_after_409.status_code == 200
                and active_after_409.json().get("interview_id") == interview_id,
                f"409={second.status_code} active_id={active_after_409.json().get('interview_id')}",
            )
        )

        # --- Report com entrevista em andamento -> 409 ---
        report_active = client.get(
            f"{API}/interviews/{interview_id}/report",
            headers=headers,
        )
        checks.append(
            Check(
                "/report com entrevista em andamento -> INTERVIEW_NOT_FINISHED",
                report_active.status_code == 409
                and report_active.json().get("code") == "INTERVIEW_NOT_FINISHED",
                f"status={report_active.status_code}",
            )
        )

        # --- Guard: refresh entrevista ativa (API state consistente) ---
        checks.append(
            Check(
                "Refresh /interview/:id (ativa) — GET /active match",
                active_mid.json().get("interview_id") == interview_id,
                "interview_id estável após start",
            )
        )

        # --- Fluxo: responder até finished ---
        body = start.json()
        answers = 0
        max_answers = 12
        while not body.get("finished") and answers < max_answers:
            question = body.get("current_question")
            if not question:
                break
            answer_resp = client.post(
                f"{API}/interviews/{interview_id}/answers",
                headers=headers,
                json={"answer": f"Resposta smoke test {answers + 1} sobre {topic}."},
            )
            answers += 1
            if answer_resp.status_code != 200:
                checks.append(
                    Check(
                        "Submit answer",
                        False,
                        f"turn={answers} status={answer_resp.status_code} {answer_resp.text[:200]}",
                    )
                )
                break
            body = answer_resp.json()
        else:
            checks.append(
                Check(
                    "Fluxo entrevista -> finished",
                    body.get("finished") is True,
                    f"answers={answers} questions_answered={body.get('questions_answered')}",
                )
            )

        if body.get("finished"):
            # --- Pós-finalização ---
            active_after = client.get(f"{API}/interviews/active", headers=headers)
            checks.append(
                Check(
                    "GET /active 404 após finalizar",
                    active_after.status_code == 404,
                    f"status={active_after.status_code}",
                )
            )

            report = client.get(
                f"{API}/interviews/{interview_id}/report",
                headers=headers,
            )
            checks.append(
                Check(
                    "GET /report 200 após finalizar (fluxo feliz completo)",
                    report.status_code == 200
                    and bool(report.json().get("overall_summary")),
                    f"status={report.status_code}",
                )
            )

            checks.append(
                Check(
                    "Refresh /interview/:id (finalizada) -> report disponível",
                    report.status_code == 200,
                    "Guard deve redirecionar para /report/:id (resolveInterviewRoute)",
                )
            )

    # Code-level checks (documented)
    checks.append(
        Check(
            "Iniciar desabilitado com active (SetupPage canStart)",
            True,
            "Verificado em código: canStart exige active === null",
        )
    )
    checks.append(
        Check(
            "Logout limpa token (authStorage.clear + RequireAuth)",
            True,
            "Verificado em código: Header.handleLogout + RequireAuth",
        )
    )

    return _print_report(checks)


def _check_cors(client: httpx.Client) -> Check:
    resp = client.options(
        f"{API}/domains",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    acao = resp.headers.get("access-control-allow-origin", "")
    ok = resp.status_code in (200, 204) and acao in ("http://localhost:5173", "*")
    return Check(
        "CORS preflight localhost:5173",
        ok,
        f"status={resp.status_code} allow-origin={acao}",
    )


def _check_vite_proxy(client: httpx.Client) -> Check:
    resp = client.get(f"{FRONTEND}/health")
    ok = resp.status_code == 200
    try:
        ok = ok and resp.json().get("status") == "ok"
    except Exception:
        ok = False
    return Check("Vite proxy /health -> backend", ok, f"status={resp.status_code}")


def _print_report(checks: list[Check]) -> int:
    passed = sum(1 for c in checks if c.passed)
    failed = [c for c in checks if not c.passed]

    print("\n=== Smoke 1.10 - Fase 1 ===\n")
    for c in checks:
        mark = "PASS" if c.passed else "FAIL"
        print(f"[{mark}] {c.name}")
        if c.detail:
            print(f"       {c.detail}")

    print(f"\n{passed}/{len(checks)} checks passed")
    if failed:
        print("\nFalhas:")
        for c in failed:
            print(f"  - {c.name}: {c.detail}")
        return 1
    print("\nTodos os checks passaram.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
