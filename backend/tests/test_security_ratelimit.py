import uuid

from app.core.rate_limit import SlidingWindowLimiter
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_roundtrip():
    h = hash_password("correct horse battery")
    assert h != "correct horse battery"
    assert verify_password("correct horse battery", h)
    assert not verify_password("wrong", h)


def test_unknown_user_never_verifies():
    assert not verify_password("anything", None)


def test_jwt_roundtrip_and_tamper_detection():
    uid, oid = uuid.uuid4(), uuid.uuid4()
    token = create_access_token(uid, oid, "owner")
    payload = decode_access_token(token)
    assert payload and payload["sub"] == str(uid) and payload["role"] == "owner"
    assert decode_access_token(token[:-2] + "xx") is None
    assert decode_access_token("garbage") is None


def test_rate_limiter_blocks_after_limit_and_isolates_keys():
    lim = SlidingWindowLimiter()
    assert all(lim.allow("a", 3) for _ in range(3))
    assert not lim.allow("a", 3)
    assert lim.allow("b", 3)
