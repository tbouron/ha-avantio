"""Tests for the Avantio client, run against a local fake Avantio server."""

import json

import aiohttp
import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from avantio_client import AvantioClient, CannotConnect, InvalidAuth

USERNAME = "owner@example.com"
PASSWORD = "secret"
CSRF_TOKEN = "test-csrf-token"

LOGIN_PAGE = f"""
<html><body>
<form method="post" action="index.php">
  <input type="text" name="user_name" />
  <input type="password" name="user_password" />
  <input type="hidden" name="csrftoken" value="{CSRF_TOKEN}" />
</form>
</body></html>
"""


class FakeAvantio:
    """Minimal imitation of the parts of app.avantio.pro the client uses."""

    def __init__(self):
        self.login_page_status = 200
        self.login_page_body = LOGIN_PAGE
        self.accommodations = [{"id": 1, "name": "Flat"}, {"id": 2, "name": "House"}]
        self.user_agents: list[str] = []
        self.login_posts: list[dict] = []
        self.logged_in = False

    def app(self) -> web.Application:
        app = web.Application()
        app.router.add_get("/index.php", self.get_index)
        app.router.add_post("/index.php", self.post_index)
        return app

    async def get_index(self, request: web.Request) -> web.StreamResponse:
        self.user_agents.append(request.headers.get("User-Agent", ""))
        if self.login_page_status != 200:
            return web.Response(
                status=self.login_page_status,
                text="Request blocked.",
                headers={"Server": "CloudFront"},
            )
        if request.query.get("module") == "Home":
            return web.Response(text="<html>Home</html>", content_type="text/html")
        return web.Response(text=self.login_page_body, content_type="text/html")

    async def post_index(self, request: web.Request) -> web.StreamResponse:
        self.user_agents.append(request.headers.get("User-Agent", ""))
        form = {}
        async for part in await request.multipart():
            form[part.name] = await part.text()

        if form.get("action") == "Login":
            self.login_posts.append(form)
            if (
                form.get("user_name") == USERNAME
                and form.get("user_password") == PASSWORD
                and form.get("csrftoken") == CSRF_TOKEN
            ):
                self.logged_in = True
                raise web.HTTPFound("/index.php?module=Home&action=index")
            raise web.HTTPFound("/index.php?module=Usuarios&action=Login")

        if not self.logged_in:
            raise web.HTTPFound("/index.php?module=Usuarios&action=Login")

        if form.get("functionName") == "fetchAccommodations":
            params = json.loads(form.get("params", "{}"))
            offset, limit = params["offset"], params["limit"]
            page = self.accommodations[offset : offset + limit]
            total = offset + len(page)
            return web.json_response(
                {
                    "accommodations": page,
                    "pagination": {
                        "total": total,
                        "hasNextPage": total < len(self.accommodations),
                    },
                }
            )

        return web.Response(status=404)


@pytest.fixture
async def fake():
    fake = FakeAvantio()
    server = TestServer(fake.app())
    await server.start_server()
    fake.base_url = str(server.make_url("")).rstrip("/")
    yield fake
    await server.close()


def make_client(fake: FakeAvantio, password: str = PASSWORD) -> AvantioClient:
    return AvantioClient(username=USERNAME, password=password, base_url=fake.base_url)


async def sign_in(client: AvantioClient) -> bool:
    async with aiohttp.ClientSession(headers=client._base_headers) as session:
        return await client.sign_in(session)


async def test_sign_in_succeeds_and_sends_csrf_token(fake):
    assert await sign_in(make_client(fake)) is True

    assert len(fake.login_posts) == 1
    post = fake.login_posts[0]
    assert post["csrftoken"] == CSRF_TOKEN
    assert post["user_name"] == USERNAME
    assert post["user_password"] == PASSWORD


async def test_sign_in_with_wrong_password_raises_invalid_auth(fake):
    with pytest.raises(InvalidAuth):
        await sign_in(make_client(fake, password="wrong"))


async def test_blocked_login_page_raises_cannot_connect_with_status(fake):
    fake.login_page_status = 403

    with pytest.raises(CannotConnect, match=r"HTTP 403 \(server: CloudFront\)"):
        await sign_in(make_client(fake))

    assert fake.login_posts == []


async def test_login_page_without_csrf_token_raises(fake):
    fake.login_page_body = "<html><body><form></form></body></html>"

    with pytest.raises(Exception, match="Could not find CSRF token"):
        await sign_in(make_client(fake))


async def test_requests_send_a_full_browser_user_agent(fake):
    """Avantio's CloudFront blocks the bare "Mozilla/5.0" User-Agent."""
    await make_client(fake).get_accommodations()

    assert fake.user_agents, "no requests reached the server"
    for user_agent in fake.user_agents:
        assert user_agent != "Mozilla/5.0"
        assert "Firefox/" in user_agent


async def test_get_accommodations_aggregates_all_pages(fake):
    fake.accommodations = [{"id": i} for i in range(5)]
    client = make_client(fake)

    async with aiohttp.ClientSession(headers=client._base_headers) as session:
        result = await client.pagination(
            session=session,
            booking_data={
                "module": "PlanningPropietarios",
                "action": "Ajax",
                "functionName": "fetchAccommodations",
            },
            data_path="accommodations",
            max_items=2,
        )

    assert result == fake.accommodations
