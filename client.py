"""Unofficial client to Avantio, which reverse-engineer the API calls of the platform app.avantio.com."""

import aiohttp
import json
import logging
from bs4 import BeautifulSoup
from homeassistant.exceptions import HomeAssistantError

# Create a logger instance
_LOGGER = logging.getLogger(__name__)

MAX_RETRIES = 3


class AvantioClient:
    """Utility class to communicate with avantio "API"."""

    def __init__(
            self, username: str, password: str, base_url: str = "https://app.avantio.pro"
    ) -> None:
        """Initialise the client."""
        self._username = username
        self._password = password
        self._base_url = base_url
        self._login_url = f"{self._base_url}/index.php"
        self._base_headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://app.avantio.pro/index.php?firstAcces=1&module=Compromisos&action=ListViewPropietarios&return_module=Compromisos&return_action=index&avs=aExPNzV4UHhxTE85aTUxRStYd2diUUlVVmZvRUw1YXpGMk1QWTg0dmo4eHJSZE00OUtmK2RhWSs3akJ2UW4zYnlsTkdobm1saE5KWjNMUFoyVXU2aHFBN3k5RVZmK2ZYSXFFU3daZVJ5VkpWNVNnV0tjU3RCdW9WeEhIWFpBVzliNmJUKzdiOTZwNUthd3d1eE05clhBPT0%253D",
            "Origin": " ",
        }

    def is_logged_out(self, response_url) -> bool:
        return True if "action=Login" in str(response_url) else False

    async def sign_in(self, session) -> bool:
        """Sign in a user and store cookies into the embedded session."""
        _LOGGER.debug("Signing in to %s", self._base_url)
        async with session.get(self._login_url) as init_response:
            soup = BeautifulSoup(await init_response.text(), features="html.parser")
            tag = soup.find(
                "input", attrs={"name": "csrftoken", "type": "hidden"}
            )
            if tag is None or tag["value"] is None:
                raise Exception("Could not find CSRF token on login page")
            csrftoken = tag["value"]

        login_data = {
            "module": "Usuarios",
            "user_name": self._username,
            "user_password": self._password,
            "action": "Login",
            "Login": "Login",
            "login_language": "en_gb",
            "resolucion": "",
            "token": "",
            "hashDevice": "",
            "csrftoken": csrftoken,
        }

        with aiohttp.MultipartWriter("form-data") as mp:
            for key, value in login_data.items():
                part = mp.append(value)
                part.set_content_disposition("form-data", name=key)
            async with session.post(
                    f"{self._base_url}/index.php", data=mp, headers=self._base_headers
            ) as login_response:
                if "module=Home" in str(login_response.url):
                    _LOGGER.info("Successfully logged to %s", self._base_url)
                    return True

                _LOGGER.info("Failed to logged to %s", self._base_url)
                raise InvalidAuth

        _LOGGER.info("Failed to logged to %s", self._base_url)
        return False

    async def pagination(self, session, booking_data: dict, data_path: str = "list", max_items: int = 50,
                         retries: int = 0) -> list | None:
        """Paginate an Avantio Ajax endpoint.

        booking_data: dict containing keys like `module`, `action`, `functionName`, and `params` (JSON string).
        data_path: dot-separated path to the items in the JSON response (default: "list").

        Returns the aggregated list of items or None on failure.
        """
        if await self.sign_in(session) is False:
            _LOGGER.error("Failed to paginate: not signed in")
            return None

        def _extract_path(obj: dict, path: str):
            if not path:
                return obj
            cur = obj
            for part in path.split("."):
                if not isinstance(cur, dict):
                    return None
                cur = cur.get(part)
                if cur is None:
                    return None
            return cur

        # parse initial params
        try:
            params_obj = json.loads(booking_data.get("params", "{}"))
        except Exception:
            params_obj = {}

        offset = int(params_obj.get("offset", 0))
        limit = int(params_obj.get("limit", max_items))
        results: list = []

        has_next = True

        while has_next:
            params_obj["offset"] = offset
            params_obj["limit"] = limit
            booking_data["params"] = json.dumps(params_obj)

            with aiohttp.MultipartWriter("form-data") as mp:
                for key, value in booking_data.items():
                    part = mp.append(value)
                    part.set_content_disposition("form-data", name=key)
                async with session.post(
                        f"{self._base_url}/index.php",
                        data=mp,
                ) as response:
                    if self.is_logged_out(response.url) and retries < MAX_RETRIES:
                        _LOGGER.warning(
                            f"Logged-out of avantio. Closing session and retrying (retry #{retries + 1})...")
                        return await self.pagination(session=session, booking_data=booking_data, data_path=data_path,
                                                     max_items=max_items, retries=retries + 1)

                    if response.status != 200:
                        _LOGGER.error(
                            "Failed to paginate: unexpected response status %s",
                            response.status,
                        )
                        if response.status == 403:
                            raise InvalidAuth
                        return None

                    text = await response.text()
                    try:
                        data = json.loads(text)
                    except Exception:
                        _LOGGER.error("Failed to decode paginated JSON response")
                        return None

                    items = _extract_path(data, data_path) or []
                    if not isinstance(items, list):
                        _LOGGER.error("Paginated data at path %s is not a list", data_path)
                        return None

                    results.extend(items)

                    pagination_obj = data.get("pagination")
                    has_next = False if not pagination_obj else bool(pagination_obj.get("hasNextPage", False))
                    # use total as next offset per request
                    offset = int(pagination_obj.get("total", 0))

        # unreachable
        return results

    async def get_bookings(self):
        _LOGGER.debug("Fetching bookings from %s", self._base_url)
        booking_data = {
            "module": "Compromisos",
            "action": "Ajax",
            "functionName": "fetchOwnerBookings",
            "params": '{"dateCheckType":"CHECKIN","sort":"RECENT_TO_OLDEST_CHECKIN","status":["UNPAID","CONFIRMADA","BAJOPETICION","PROPIETARIO","PAID"]}',
        }

        async with aiohttp.ClientSession(headers=self._base_headers) as session:
            # use shared pagination helper to aggregate all pages
            return await self.pagination(session=session, booking_data=booking_data, data_path="list")

    async def get_accommodations(self):
        _LOGGER.debug("Fetching accommodations from %s", self._base_url)
        booking_data = {
            "module": "PlanningPropietarios",
            "action": "Ajax",
            "functionName": "fetchAccommodations"
        }

        async with aiohttp.ClientSession(headers=self._base_headers) as session:
            # use shared pagination helper to aggregate all pages
            return await self.pagination(session=session, booking_data=booking_data, data_path="accommodations")


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
