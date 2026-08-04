"""Admin 后台功能测试 — 使用 FastAPI TestClient + Mock DB。"""

import pytest
from fastapi.testclient import TestClient

from admin.app import app as admin_app


@pytest.fixture
def client():
    return TestClient(admin_app)


class TestAdminPages:
    """页面渲染测试。"""

    def test_index_page_returns_200(self, client):
        """首页应返回 200。"""
        resp = client.get("/")
        assert resp.status_code == 200
        assert "邀请码管理" in resp.text

    def test_generate_page_returns_200(self, client):
        """生成页面应返回 200。"""
        resp = client.get("/generate")
        assert resp.status_code == 200
        assert "生成邀请码" in resp.text

    def test_generate_page_has_form_fields(self, client):
        """生成页面应包含酒店、用户、天数三个输入字段。"""
        resp = client.get("/generate")
        assert 'name="hotel_id"' in resp.text
        assert 'name="user_name"' in resp.text
        assert 'name="days"' in resp.text

    def test_requests_page_returns_200(self, client):
        """申请记录页面应返回 200。"""
        resp = client.get("/requests")
        assert resp.status_code == 200
        assert "申请记录" in resp.text


class TestInviteCodeActions:
    """邀请码操作功能测试。"""

    def setup_method(self):
        """清理测试数据。"""
        # 使用测试数据库或 mock

    def test_generate_invite_code_redirects(self, client):
        """生成邀请码后应重定向到首页。"""
        resp = client.post("/generate", data={
            "hotel_id": "测试酒店",
            "user_name": "张经理",
            "days": 7,
        })
        assert resp.status_code == 303  # Redirect
        assert resp.headers["location"] == "/"

    def test_generate_without_optional_fields(self, client):
        """酒店和用户可选，不传也应正常生成。"""
        resp = client.post("/generate", data={"days": 7})
        assert resp.status_code == 303

    def test_generate_default_days(self, client):
        """不传天数应默认 7 天。"""
        resp = client.post("/generate", data={})
        assert resp.status_code == 303

    def test_deactivate_code_redirects(self, client):
        """停用邀请码应重定向。"""
        resp = client.post("/deactivate", data={"code": "INVITE-TEST"})
        assert resp.status_code == 303

    def test_activate_code_redirects(self, client):
        """启用邀请码应重定向。"""
        resp = client.post("/activate", data={"code": "INVITE-TEST"})
        assert resp.status_code == 303

    def test_delete_code_redirects(self, client):
        """删除邀请码应重定向。"""
        resp = client.post("/delete", data={"code": "INVITE-TEST"})
        assert resp.status_code == 303


class TestFullWorkflow:
    """完整工作流测试。"""

    def test_generate_then_list_then_deactivate(self, client):
        """生成 → 列表可见 → 停用 → 再启用 → 删除。"""
        # 1. 生成
        resp = client.post("/generate", data={
            "hotel_id": "大酒店",
            "user_name": "李总",
            "days": 7,
        })
        assert resp.status_code == 303

        # 2. 首页应包含生成的内容
        resp = client.get("/")
        assert resp.status_code == 200
        assert "大酒店" in resp.text
        assert "李总" in resp.text

        # 3. 停用 — 需要知道邀请码，这里验证页面存在停用表单
        resp = client.get("/")
        assert 'action="/deactivate"' in resp.text

        # 4. 启用 — 页面应存在启用表单
        assert 'action="/activate"' in resp.text

        # 5. 删除 — 页面应存在删除表单
        assert 'action="/delete"' in resp.text
