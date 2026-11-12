"""로그인 시도 제한 (auth.too_many_attempts 429): 이메일당 15분 5회 실패, IP당 15분 20회 실패, 성공하면 이메일 기록 초기화.
탈퇴 비밀번호 확인도 같은 이메일 기록을 씀. 이메일·비밀번호는 가상 값만."""

import pytest

from modules.auth import attempts

from test_auth_patient import EMAIL, PASSWORD, auth, login, signup, withdraw


@pytest.fixture
def clock(monkeypatch):
    t = {"now": 1000.0}
    for limiter in (attempts.by_email, attempts.by_ip):
        monkeypatch.setattr(limiter, "clock", lambda: t["now"])
    return t


def fail(client, n, email=EMAIL):
    for _ in range(n):
        assert login(client, email=email, password="wrong-password").status_code == 401


def test_locked_after_five_failures_even_with_right_password(client, clock):
    signup(client)
    fail(client, 5)
    r = login(client)
    assert r.status_code == 429 and r.json()["code"] == "auth.too_many_attempts"
    assert 0 < r.json()["detail"]["retry_after"] <= 15 * 60
    assert login(client, email="  PATIENT1@example.com ").status_code == 429  # 같은 이메일(정규화)


def test_unknown_email_locks_the_same_way(client, clock):
    """없는 이메일도 똑같이 막힘 → 응답으로 가입 여부를 알 수 없음."""
    fail(client, 5, email="nobody@example.com")
    r = login(client, email="nobody@example.com")
    assert r.status_code == 429 and r.json()["code"] == "auth.too_many_attempts"


def test_unlocks_after_window(client, clock):
    signup(client)
    fail(client, 5)
    clock["now"] += 15 * 60 + 1
    assert login(client).status_code == 200


def test_success_resets_email_failures(client, clock):
    signup(client)
    fail(client, 4)
    assert login(client).status_code == 200
    fail(client, 4)
    assert login(client).status_code == 200


def test_other_email_not_affected(client, clock):
    signup(client)
    signup(client, email="patient2@example.com")
    fail(client, 5)
    assert login(client, email="patient2@example.com").status_code == 200


def test_ip_limit_across_emails(client, clock):
    signup(client)
    for i in range(4):  # 이메일 4개 × 5회 = 같은 IP에서 20회
        fail(client, 5, email=f"guess{i}@example.com")
    r = login(client)
    assert r.status_code == 429 and r.json()["code"] == "auth.too_many_attempts"


def test_withdraw_password_check_is_limited(client, clock):
    token = signup(client)
    for _ in range(5):
        assert withdraw(client, token, password="wrong-password").status_code == 401
    r = withdraw(client, token)
    assert r.status_code == 429 and r.json()["code"] == "auth.too_many_attempts"
    assert client.get("/api/v1/me", headers=auth(token)).status_code == 200  # 계정 그대로
    assert login(client).status_code == 429  # 같은 이메일 기록


def test_limiter_unit():
    t = {"now": 0.0}
    lim = attempts.AttemptLimiter(max_failures=2, window_seconds=10, clock=lambda: t["now"])
    assert lim.retry_after("k") is None
    lim.fail("k")
    t["now"] = 3
    lim.fail("k")
    assert lim.retry_after("k") == 7  # 첫 실패가 창에서 빠질 때까지
    t["now"] = 10
    assert lim.retry_after("k") is None
    lim.fail("k")
    lim.reset("k")
    assert lim.retry_after("k") is None
