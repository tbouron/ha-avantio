"""Unofficial client to Avantio, which reverse-engineer the API calls of the platform app.avantio.com."""

import json
import logging

import aiohttp
from bs4 import BeautifulSoup

from homeassistant.exceptions import HomeAssistantError

# Create a logger instance
_LOGGER = logging.getLogger(__name__)


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
        self._session = None
        self._base_headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://app.avantio.pro/index.php?firstAcces=1&module=Compromisos&action=ListViewPropietarios&return_module=Compromisos&return_action=index&avs=aExPNzV4UHhxTE85aTUxRStYd2diUUlVVmZvRUw1YXpGMk1QWTg0dmo4eHJSZE00OUtmK2RhWSs3akJ2UW4zYnlsTkdobm1saE5KWjNMUFoyVXU2aHFBN3k5RVZmK2ZYSXFFU3daZVJ5VkpWNVNnV0tjU3RCdW9WeEhIWFpBVzliNmJUKzdiOTZwNUthd3d1eE05clhBPT0%253D",
            "Origin": "https://app.avantio.pro",
        }

    async def sign_in(self) -> bool:
        """Sign in a user and store cookies into the embedded session."""
        if self._session is None:
            self._session = aiohttp.ClientSession(headers=self._base_headers)

        _LOGGER.debug("Signing in to %s", self._base_url)
        async with self._session.get(self._login_url) as init_response:
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
            async with self._session.post(
                f"{self._base_url}/index.php", data=mp, headers=self._base_headers
            ) as login_response:
                if "module=Home" in str(login_response.url):
                    _LOGGER.info("Successfully logged to %s", self._base_url)
                    return True

                _LOGGER.info("Failed to logged to %s", self._base_url)
                raise InvalidAuth

        _LOGGER.info("Failed to logged to %s", self._base_url)
        return False

    async def get_bookings(self):
        """Get the bookings for the currently logged user."""
        if self._session is None:
            if await self.sign_in() is False:
                _LOGGER.error("Failed to fetch booking: not signed in")
                return None

        _LOGGER.debug("Fetching bookings from %s", self._base_url)
        booking_data = {
            "module": "Compromisos",
            "action": "Ajax",
            "functionName": "fetchOwnerBookings",
            "params": '{"dateCheckType":"CHECKIN","dateRequest":"12MONTHS","sort":"RECENT_TO_OLDEST_CHECKIN","status":["UNPAID","CONFIRMADA","BAJOPETICION","PROPIETARIO","PAID"]}',
        }

        with aiohttp.MultipartWriter("form-data") as mp:
            for key, value in booking_data.items():
                part = mp.append(value)
                part.set_content_disposition("form-data", name=key)
            async with self._session.post(
                f"{self._base_url}/index.php",
                data=mp,
            ) as bookings_response:
                if bookings_response.status == 200:
                    text = await bookings_response.text()
                    _LOGGER.info(
                        "Successfully fetched bookings from %s", self._base_url
                    )
                    _LOGGER.info(text)
                    return json.loads(text).get("list")

                _LOGGER.error(
                    "Failed to fetch bookings: unexpected response received => status code: %s",
                    bookings_response.status,
                )

                if bookings_response.status == 403:
                    raise InvalidAuth

        return None

    async def get_accommodations(self):
        """Get all accommodation for the currently logged user."""
        if self._session is None:
            if await self.sign_in() is False:
                _LOGGER.error("Failed to fetch accommodations: not signed in")
                return None

        _LOGGER.debug("Fetching accommodations from %s", self._base_url)
        booking_data = {
            "module": "PlanningPropietarios",
            "action": "Ajax",
            "functionName": "fetchAccommodations",
            "params": '{"offset":0,"limit":50}',
        }

        with aiohttp.MultipartWriter("form-data") as mp:
            for key, value in booking_data.items():
                part = mp.append(value)
                part.set_content_disposition("form-data", name=key)
            async with self._session.post(
                f"{self._base_url}/index.php",
                data=mp,
            ) as accommodations_response:
                if accommodations_response.status == 200:
                    text = await accommodations_response.text()
                    _LOGGER.info(
                        "Successfully fetched accommodations from %s", self._base_url
                    )
                    _LOGGER.info(text)
                    return json.loads(text).get("accommodations")

                _LOGGER.error(
                    "Failed to fetch accommodations: unexpected response received => status code: %s",
                    accommodations_response.status,
                )

                if accommodations_response.status == 403:
                    raise InvalidAuth

        return None

    async def close(self):
        """Close the client session."""
        if self._session:
            await self._session.close()
            self._session = None


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
