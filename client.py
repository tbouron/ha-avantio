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
        data = '{"list":[{"id":30053975,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"CONFIRMADA","color":"#f44336"},"guests":{"numAdults":6,"numChildren":2,"numBabies":0,"childrenAges":[3,3]},"nightsCount":7,"dateAdd":"11 Dec 2025","bookingStart":"06 Jun 2026","bookingEnd":"13 Jun 2026","amount":"\u20ac 2,729.58","currency":"EUR","locator":"30053975-1694096339","comment":null,"agent":{"id":null,"name":"Travel Paradise","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":29671458,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"PROPIETARIO","color":"#4040d9"},"guests":{"numAdults":4,"numChildren":1,"numBabies":0,"childrenAges":[0]},"nightsCount":8,"dateAdd":"06 Nov 2025","bookingStart":"26 Dec 2025","bookingEnd":"03 Jan 2026","amount":"\u20ac 0.00","currency":"EUR","locator":"29671458-1694096339","comment":null,"agent":{"id":null,"name":"","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":29667701,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"CONFIRMADA","color":"#f44336"},"guests":{"numAdults":7,"numChildren":2,"numBabies":0,"childrenAges":[1,2]},"nightsCount":7,"dateAdd":"05 Nov 2025","bookingStart":"20 Jun 2026","bookingEnd":"27 Jun 2026","amount":"\u20ac 2,433.88","currency":"EUR","locator":"29667701-1694096339","comment":null,"agent":{"id":null,"name":"Travel Paradise","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":29528174,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"CONFIRMADA","color":"#f44336"},"guests":{"numAdults":8,"numChildren":2,"numBabies":1,"childrenAges":[12,12]},"nightsCount":7,"dateAdd":"24 Oct 2025","bookingStart":"04 Jul 2026","bookingEnd":"11 Jul 2026","amount":"\u20ac 4,581.90","currency":"EUR","locator":"A203-HM288NZXT4","comment":null,"agent":{"id":null,"name":"Airbnb.com","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":29470672,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"UNAVAILABLE","color":"#000000"},"guests":{"numAdults":1,"numChildren":0,"numBabies":0,"childrenAges":[0]},"nightsCount":33,"dateAdd":"20 Oct 2025","bookingStart":"16 Nov 2025","bookingEnd":"19 Dec 2025","amount":"\u20ac 0.00","currency":"EUR","locator":"29470672-1694096339","comment":null,"agent":{"id":null,"name":"","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":29359957,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"CONFIRMADA","color":"#f44336"},"guests":{"numAdults":2,"numChildren":0,"numBabies":0,"childrenAges":[0]},"nightsCount":7,"dateAdd":"11 Oct 2025","bookingStart":"09 May 2026","bookingEnd":"16 May 2026","amount":"\u20ac 1,909.92","currency":"EUR","locator":"29359957-1694096339","comment":null,"agent":{"id":null,"name":"Homeaway / VRBO / Abritel","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":29227984,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"PAID","color":"#6aa84f"},"guests":{"numAdults":6,"numChildren":0,"numBabies":3,"childrenAges":[0]},"nightsCount":7,"dateAdd":"29 Sep 2025","bookingStart":"13 Jun 2026","bookingEnd":"20 Jun 2026","amount":"\u20ac 2,327.40","currency":"EUR","locator":"A203-HMTXJFS5XC","comment":null,"agent":{"id":null,"name":"Airbnb.com","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":28978821,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"CONFIRMADA","color":"#f44336"},"guests":{"numAdults":8,"numChildren":0,"numBabies":0,"childrenAges":[0]},"nightsCount":8,"dateAdd":"08 Sep 2025","bookingStart":"22 May 2026","bookingEnd":"30 May 2026","amount":"\u20ac 2,857.55","currency":"EUR","locator":"28978821-1694096339","comment":null,"agent":{"id":null,"name":"Travel Paradise","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":28545687,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"UNAVAILABLE","color":"#000000"},"guests":{"numAdults":1,"numChildren":0,"numBabies":0,"childrenAges":[0]},"nightsCount":28,"dateAdd":"04 Aug 2025","bookingStart":"01 Aug 2026","bookingEnd":"29 Aug 2026","amount":"\u20ac 0.00","currency":"EUR","locator":"28545687-1694096339","comment":null,"agent":{"id":null,"name":"","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":28503983,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"PROPIETARIO","color":"#4040d9"},"guests":{"numAdults":9,"numChildren":1,"numBabies":0,"childrenAges":[0]},"nightsCount":3,"dateAdd":"31 Jul 2025","bookingStart":"02 Oct 2025","bookingEnd":"05 Oct 2025","amount":"\u20ac 0.00","currency":"EUR","locator":"28503983-1694096339","comment":null,"agent":{"id":null,"name":"","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":28298499,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"CONFIRMADA","color":"#f44336"},"guests":{"numAdults":6,"numChildren":4,"numBabies":0,"childrenAges":[7,7,7,7]},"nightsCount":14,"dateAdd":"16 Jul 2025","bookingStart":"18 Jul 2026","bookingEnd":"01 Aug 2026","amount":"\u20ac 12,241.62","currency":"EUR","locator":"28298499-1694096339","comment":null,"agent":{"id":null,"name":"Homeaway / VRBO / Abritel","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":27481942,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"PAID","color":"#6aa84f"},"guests":{"numAdults":6,"numChildren":0,"numBabies":0,"childrenAges":[0]},"nightsCount":7,"dateAdd":"19 May 2025","bookingStart":"13 Sep 2025","bookingEnd":"20 Sep 2025","amount":"\u20ac 2,797.25","currency":"EUR","locator":"27481942-1694096339","comment":null,"agent":{"id":null,"name":"Travel Paradise","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":27451878,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"PAID","color":"#6aa84f"},"guests":{"numAdults":6,"numChildren":1,"numBabies":0,"childrenAges":[3]},"nightsCount":7,"dateAdd":"16 May 2025","bookingStart":"21 Jun 2025","bookingEnd":"28 Jun 2025","amount":"\u20ac 2,258.89","currency":"EUR","locator":"27451878-1694096339","comment":null,"agent":{"id":null,"name":"Travel Paradise","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":27245319,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"PROPIETARIO","color":"#4040d9"},"guests":{"numAdults":1,"numChildren":0,"numBabies":0,"childrenAges":[0]},"nightsCount":7,"dateAdd":"03 May 2025","bookingStart":"14 Jun 2025","bookingEnd":"21 Jun 2025","amount":"\u20ac 0.00","currency":"EUR","locator":"27245319-1694096339","comment":null,"agent":{"id":null,"name":"","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":27079646,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"PAID","color":"#6aa84f"},"guests":{"numAdults":10,"numChildren":1,"numBabies":0,"childrenAges":[16]},"nightsCount":7,"dateAdd":"21 Apr 2025","bookingStart":"19 Jul 2025","bookingEnd":"26 Jul 2025","amount":"\u20ac 5,833.66","currency":"EUR","locator":"27079646-1694096339","comment":null,"agent":{"id":null,"name":"Travel Paradise","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":26627130,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"UNAVAILABLE","color":"#000000"},"guests":{"numAdults":0,"numChildren":0,"numBabies":0,"childrenAges":[0]},"nightsCount":7,"dateAdd":"21 Mar 2025","bookingStart":"29 Mar 2025","bookingEnd":"05 Apr 2025","amount":"\u20ac 0.00","currency":"EUR","locator":"26627130-1694096339","comment":null,"agent":{"id":null,"name":"","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":25727781,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"PAID","color":"#6aa84f"},"guests":{"numAdults":8,"numChildren":3,"numBabies":0,"childrenAges":[7,7,7]},"nightsCount":7,"dateAdd":"14 Jan 2025","bookingStart":"07 Jun 2025","bookingEnd":"14 Jun 2025","amount":"\u20ac 2,295.58","currency":"EUR","locator":"25727781-1694096339","comment":null,"agent":{"id":null,"name":"Homeaway / VRBO / Abritel","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":25624483,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"PAID","color":"#6aa84f"},"guests":{"numAdults":10,"numChildren":0,"numBabies":0,"childrenAges":[0]},"nightsCount":10,"dateAdd":"09 Jan 2025","bookingStart":"28 May 2025","bookingEnd":"07 Jun 2025","amount":"\u20ac 4,282.36","currency":"EUR","locator":"25624483-1694096339","comment":null,"agent":{"id":null,"name":"","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":25576336,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"PAID","color":"#6aa84f"},"guests":{"numAdults":7,"numChildren":2,"numBabies":1,"childrenAges":[3,5]},"nightsCount":7,"dateAdd":"06 Jan 2025","bookingStart":"12 Jul 2025","bookingEnd":"19 Jul 2025","amount":"\u20ac 5,167.10","currency":"EUR","locator":"25576336-1694096339","comment":null,"agent":{"id":null,"name":"","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":25163945,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"PAID","color":"#6aa84f"},"guests":{"numAdults":8,"numChildren":0,"numBabies":1,"childrenAges":[0]},"nightsCount":7,"dateAdd":"27 Nov 2024","bookingStart":"06 Sep 2025","bookingEnd":"13 Sep 2025","amount":"\u20ac 2,759.61","currency":"EUR","locator":"25163945-1694096339","comment":null,"agent":{"id":null,"name":"","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":25135201,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"PAID","color":"#6aa84f"},"guests":{"numAdults":5,"numChildren":2,"numBabies":0,"childrenAges":[7,9]},"nightsCount":7,"dateAdd":"24 Nov 2024","bookingStart":"03 May 2025","bookingEnd":"10 May 2025","amount":"\u20ac 2,024.31","currency":"EUR","locator":"25135201-1694096339","comment":null,"agent":{"id":null,"name":"Travel Paradise","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":25019700,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"PAID","color":"#6aa84f"},"guests":{"numAdults":6,"numChildren":6,"numBabies":0,"childrenAges":[5,5,6,7,7,8]},"nightsCount":7,"dateAdd":"13 Nov 2024","bookingStart":"05 Jul 2025","bookingEnd":"12 Jul 2025","amount":"\u20ac 5,768.70","currency":"EUR","locator":"25019700-1694096339","comment":null,"agent":{"id":null,"name":"Travel Paradise","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":24919757,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"PAID","color":"#6aa84f"},"guests":{"numAdults":8,"numChildren":0,"numBabies":0,"childrenAges":[0]},"nightsCount":7,"dateAdd":"04 Nov 2024","bookingStart":"30 Aug 2025","bookingEnd":"06 Sep 2025","amount":"\u20ac 2,714.96","currency":"EUR","locator":"24919757-443959","comment":null,"agent":{"id":null,"name":"","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":24623265,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"PROPIETARIO","color":"#4040d9"},"guests":{"numAdults":1,"numChildren":0,"numBabies":0,"childrenAges":[0]},"nightsCount":22,"dateAdd":"07 Oct 2024","bookingStart":"05 Apr 2025","bookingEnd":"27 Apr 2025","amount":"\u20ac 0.00","currency":"EUR","locator":"24623265-1694096339","comment":null,"agent":{"id":null,"name":"","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":24555695,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"PROPIETARIO","color":"#4040d9"},"guests":{"numAdults":1,"numChildren":0,"numBabies":0,"childrenAges":[0]},"nightsCount":35,"dateAdd":"01 Oct 2024","bookingStart":"26 Jul 2025","bookingEnd":"30 Aug 2025","amount":"\u20ac 0.00","currency":"EUR","locator":"24555695-1694096339","comment":null,"agent":{"id":null,"name":"","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":24481387,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"UNAVAILABLE","color":"#000000"},"guests":{"numAdults":1,"numChildren":0,"numBabies":0,"childrenAges":[0]},"nightsCount":58,"dateAdd":"24 Sep 2024","bookingStart":"03 Nov 2024","bookingEnd":"31 Dec 2024","amount":"\u20ac 0.00","currency":"EUR","locator":"24481387-1694096339","comment":null,"agent":{"id":null,"name":"","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":23935185,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"PAID","color":"#6aa84f"},"guests":{"numAdults":4,"numChildren":4,"numBabies":0,"childrenAges":[13,14,16,16]},"nightsCount":7,"dateAdd":"10 Aug 2024","bookingStart":"28 Jun 2025","bookingEnd":"05 Jul 2025","amount":"\u20ac 4,361.70","currency":"EUR","locator":"23935185-443959","comment":null,"agent":{"id":null,"name":"","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":23047936,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"PAID","color":"#6aa84f"},"guests":{"numAdults":9,"numChildren":0,"numBabies":0,"childrenAges":[0]},"nightsCount":7,"dateAdd":"07 Jun 2024","bookingStart":"07 Sep 2024","bookingEnd":"14 Sep 2024","amount":"\u20ac 2,539.30","currency":"EUR","locator":"23047936-1694096339","comment":null,"agent":{"id":null,"name":"","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":22556542,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"CONFIRMADA","color":"#f44336"},"guests":{"numAdults":5,"numChildren":5,"numBabies":0,"childrenAges":[1,12,12,12,12]},"nightsCount":4,"dateAdd":"01 May 2024","bookingStart":"08 May 2024","bookingEnd":"12 May 2024","amount":"\u20ac 1,458.39","currency":"EUR","locator":"A203-HM9ASFHWCZ","comment":null,"agent":{"id":null,"name":"Airbnb.com","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}},{"id":22464309,"propertyName":"Villa Terroirs","propertyId":443959,"status":{"name":"CONFIRMADA","color":"#f44336"},"guests":{"numAdults":5,"numChildren":5,"numBabies":0,"childrenAges":[1,1,12,12,12]},"nightsCount":7,"dateAdd":"25 Apr 2024","bookingStart":"01 Jun 2024","bookingEnd":"08 Jun 2024","amount":"\u20ac 1,565.78","currency":"EUR","locator":"A203-HMC4E95CWX","comment":null,"agent":{"id":null,"name":"Airbnb.com","image":"https://app.avantio.pro/images/faviconMundo.svg ","color":"#EB5745","integratorId":null}}],"pagination":{"hasNextPage":true,"totalFiltered":81,"total":132},"exportUrls":{"xls":"https://app.avantio.pro/index.php?estado%5B0%5D=UNPAID&estado%5B1%5D=CONFIRMADA&estado%5B2%5D=BAJOPETICION&estado%5B3%5D=PROPIETARIO&estado%5B4%5D=UNAVAILABLE&estado%5B5%5D=PAID&sortField=CREATION&sortOrder=DESC&module=Compromisos&action=ExportXlsPropietario&return_module=Compromisos&return_action=Ajax&avs=RTdRdzF2RGNublRZMDVYN0o1cGk1bzF1SlZ4K2lsL05lR3M1WEI2V1l6TXhnSk5KV3IrNGR2L1doaGd4VGZ1VmdNVi8rWGQ4dmJPV0V0S1BsRDErY3ZFMFpNZW1zNmZ3Y0J4ZVhaRkJYVkFiU2thMUlOT1l6Nk13aEI3ZCttU1lpMDE0V3QwNG1OK0g0dFJSaEVBbC9UaTAzY29aTFRBVzE1Yk4wVk85OXZMaFMrbWFmUldGMXplY0VLU3V5TU5RY3JSS0lvbytVS1BIU2p4YVBxWEc5SG9nMVpSdFZyZUw3c2ZBVzBVYmJNcTJKcUtYYW16am1HbnpCN1oyTm9RK3VKenV4bjY3a1F1QjZycUp5aGdGbHh4RVBmeURaYWRXTVBzeHVjbmp0Z2VpZjhDU0xFMzY2ZWphdmJmcHYvZzJFOFV3c0NWdGh2aGdid2U5dmhRUTVKWW5OUjAvRzhzeHJZb0FTRkZjdDNFPQ%253D%253D","csv":"https://app.avantio.pro/index.php?estado%5B0%5D=UNPAID&estado%5B1%5D=CONFIRMADA&estado%5B2%5D=BAJOPETICION&estado%5B3%5D=PROPIETARIO&estado%5B4%5D=UNAVAILABLE&estado%5B5%5D=PAID&sortField=CREATION&sortOrder=DESC&module=Compromisos&action=ExportCsvPropietario&return_module=Compromisos&return_action=Ajax&avs=RTdRdzF2RGNublRZMDVYN0o1cGk1bzF1SlZ4K2lsL05lR3M1WEI2V1l6TXhnSk5KV3IrNGR2L1doaGd4VGZ1VmdNVi8rWGQ4dmJPV0V0S1BsRDErY3ZFMFpNZW1zNmZ3Y0J4ZVhaRkJYVkFiU2thMUlOT1l6Nk13aEI3ZCttU1lpMDE0V3QwNG1OK0g0dFJSaEVBbC9UaTAzY29aTFRBVzE1Yk4wVk85OXZMaFMrbWFmUldGMXplY0VLU3V5TU5RY3JSS0lvbytVS1BIU2p4YVBxWEc5SG9nMVpSdFZyZUw3c2ZBVzBVYmJNcTJKcUtYYW16am1HbnpCN1oyTm9RK3VKenV4bjY3a1F1QjZycUp5aGdGbDBWZXBEcU9sNHdjb0d2OGRaSllVcmNmWkFzQitFZHJuN0g2NkxJdG1mOEpFL280TE5MT3FBc0lPME9XdWZnL01OaVQwZzZscEU1OWtCamR1Z0FVbmlBPQ%253D%253D"}}'
        return json.loads(data).get("list")

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
        data = '{"accommodations":[{"city":"La Couarde sur mer","id":443959,"image":{"alt":"Villa Terroirs","src":"https://app.avantio.pro/fotos/2/1694776215e7cda3bd141691de18dce7c2f56db077/big17168233833af4e0ba9b617079d6a96af7ba38ac75.jpg"},"name":"Villa Terroirs"}],"pagination":{"hasNextPage":false,"totalFiltered":1,"total":1}}'
        return json.loads(data).get("accommodations")

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
