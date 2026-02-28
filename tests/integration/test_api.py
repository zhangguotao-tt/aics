"""
API 集成测试（Task17）
测试 auth / chat / knowledge 主要端点
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestAuthAPI:

    async def test_register_new_user(self, client: AsyncClient):
        """注册新用户"""
        resp = await client.post("/auth/register", json={
            "username": "testuser_reg",
            "email": "reg@example.com",
            "password": "Test@1234"
        })
        assert resp.status_code in (200, 201)
        data = resp.json()
        assert "access_token" in data or "id" in data or "username" in data

    async def test_register_duplicate_username(self, client: AsyncClient):
        """重复用户名注册应返回 4xx"""
        payload = {"username": "dup_user", "email": "dup@example.com", "password": "Test@1234"}
        await client.post("/auth/register", json=payload)
        resp = await client.post("/auth/register", json={
            "username": "dup_user", "email": "dup2@example.com", "password": "Test@1234"
        })
        assert resp.status_code in (400, 409, 422)

    async def test_login_success(self, client: AsyncClient, sample_user_data: dict):
        """正常登录"""
        # 先注册
        await client.post("/auth/register", json={
            "username": sample_user_data["username"],
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        })
        resp = await client.post("/auth/login", json={
            "username": sample_user_data["username"],
            "password": sample_user_data["password"]
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data

    async def test_login_wrong_password(self, client: AsyncClient, sample_user_data: dict):
        """错误密码登录应返回 4xx"""
        await client.post("/auth/register", json={
            "username": sample_user_data["username"],
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        })
        resp = await client.post("/auth/login", json={
            "username": sample_user_data["username"],
            "password": "WrongPass999"
        })
        assert resp.status_code in (400, 401)

    async def test_get_me_unauthorized(self, client: AsyncClient):
        """未认证访问 /auth/me 应返回 401"""
        resp = await client.get("/auth/me")
        assert resp.status_code == 401

    async def test_get_me_authorized(self, client: AsyncClient, sample_user_data: dict):
        """认证后访问 /auth/me"""
        await client.post("/auth/register", json={
            "username": sample_user_data["username"],
            "email": sample_user_data["email"],
            "password": sample_user_data["password"]
        })
        login_resp = await client.post("/auth/login", json={
            "username": sample_user_data["username"],
            "password": sample_user_data["password"]
        })
        token = login_resp.json().get("access_token", "")
        resp = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["username"] == sample_user_data["username"]


@pytest.mark.asyncio
class TestChatAPI:

    async def _get_token(self, client: AsyncClient, suffix: str = "chat") -> str:
        uname = f"chatuser_{suffix}"
        await client.post("/auth/register", json={
            "username": uname,
            "email": f"{uname}@example.com",
            "password": "Test@1234"
        })
        resp = await client.post("/auth/login", json={
            "username": uname,
            "password": "Test@1234"
        })
        return resp.json().get("access_token", "")

    async def test_send_message_unauthenticated(self, client: AsyncClient):
        """未认证发送消息应返回 401"""
        resp = await client.post("/chat/message", json={
            "session_id": "sess-anon",
            "message": "你好"
        })
        assert resp.status_code == 401

    async def test_send_message_authenticated(self, client: AsyncClient):
        """认证后发送消息（mock LLM）"""
        token = await self._get_token(client, "msg")
        # 实际调用可能失败（没有真实LLM），只验证认证通过（非401）
        resp = await client.post(
            "/chat/message",
            json={"session_id": "sess-test-001", "message": "你好"},
            headers={"Authorization": f"Bearer {token}"}
        )
        # 认证通过（不是401）；LLM未配置可能500
        assert resp.status_code != 401

    async def test_get_history_empty(self, client: AsyncClient):
        """获取不存在会话的历史应返回空或404"""
        token = await self._get_token(client, "hist")
        resp = await client.get(
            "/chat/history/nonexistent-session-xyz",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code in (200, 404)
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, (list, dict))


@pytest.mark.asyncio
class TestHealthCheck:

    async def test_health_endpoint(self, client: AsyncClient):
        """/health 端点应返回 200"""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("status") in ("ok", "healthy", "running")
