class TestClientSanity:
    def test_app_starts_and_serves_root(self, client):
        """验证 TestClient 能启动并返回 helpdesk 表单。"""
        response = client.get("/")
        assert response.status_code == 200
        assert "helpdesk" in response.text.lower()
