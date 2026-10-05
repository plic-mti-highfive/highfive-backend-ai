import time
import uuid

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.api.dependencies import get_current_tenant_id, get_current_user
from src.core.config import settings
from src.core.security import decode_jwt


def token(payload, secret=None, alg="HS256"):
    return jwt.encode(payload, secret or settings.JWT_SECRET, algorithm=alg)


def test_decode_valid_token():
    assert decode_jwt(token({"sub": "u1"}))["sub"] == "u1"


def test_decode_expired_token():
    with pytest.raises(HTTPException) as e:
        decode_jwt(token({"sub": "u", "exp": int(time.time()) - 10}))
    assert e.value.status_code == 401 and e.value.detail == "Expired token"


@pytest.mark.parametrize("bad", ["garbage", ""])
def test_decode_garbage(bad):
    with pytest.raises(HTTPException) as e:
        decode_jwt(bad)
    assert e.value.status_code == 401


def test_decode_wrong_secret():
    with pytest.raises(HTTPException) as e:
        decode_jwt(token({"sub": "u"}, secret="x" * 40))
    assert e.value.status_code == 401


async def test_get_current_user_requires_sub():
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token({"tenantId": "x"}))
    with pytest.raises(HTTPException) as e:
        await get_current_user(creds)
    assert e.value.status_code == 401


async def test_get_current_tenant_id():
    tid = uuid.uuid4()
    assert await get_current_tenant_id({"sub": "u", "tenantId": str(tid)}) == tid
    for payload in ({"sub": "u"}, {"sub": "u", "tenantId": "pas-un-uuid"}):
        with pytest.raises(HTTPException) as e:
            await get_current_tenant_id(payload)
        assert e.value.status_code == 401
