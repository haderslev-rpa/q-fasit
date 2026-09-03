import asyncio
from typing import Any

import requests

from q_fasit.api.token_manager import FasitTokenManager


class FasitApiClient:
    """
    Generel HTTP-klient til FASITs Jobcenter BFF.

    Klassen håndterer:

    - Bearer-token
    - fælles HTTP-headers
    - GET-requests
    - POST-requests
    - automatisk fornyelse af token ved HTTP 401

    Klienten indeholder ikke borgerspecifik eller sagspecifik logik.
    """

    BASE_URL = "https://jobcenter-bff.schultzfasit.dk"

    def __init__(
        self,
        token_manager: FasitTokenManager,
    ) -> None:
        """
        Opretter en generel FASIT API-klient.

        Parametre:
        - token_manager: Processens fælles token-manager.

        Output:
        Et FasitApiClient-objekt, som kan bruges af eksempelvis
        funktionerne i borger.py.
        """
        self._token_manager = token_manager
        self._session = requests.Session()

    def _create_headers(
        self,
        token: str,
    ) -> dict[str, str]:
        """
        Opretter de fælles headers til FASIT.

        Output:
        En dictionary med HTTP-headers.
        """
        return {
            "Accept": "application/json",
            "Accept-Language": (
                "da,en;q=0.9,en-GB;q=0.8,en-US;q=0.7,"
                "af;q=0.6,da-DK;q=0.5"
            ),
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Origin": "https://haderslev.schultzfasit.dk",
            "Referer": "https://haderslev.schultzfasit.dk/",
            "X-Tenant": "haderslev",
        }

    def _create_url(
        self,
        endpoint: str,
    ) -> str:
        """
        Samler base-URL og endpoint.

        Output:
        En fuld URL som tekst.

        Eksempel:
        endpoint "/api/search" bliver til
        "https://jobcenter-bff.schultzfasit.dk/api/search".
        """
        normalized_endpoint = endpoint.strip()

        if not normalized_endpoint.startswith("/"):
            normalized_endpoint = (
                f"/{normalized_endpoint}"
            )

        return f"{self.BASE_URL}{normalized_endpoint}"

    def _send_request(
        self,
        method: str,
        endpoint: str,
        token: str,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> requests.Response:
        """
        Sender selve HTTP-requesten synkront.

        Funktionen er intern og køres via asyncio.to_thread().

        Output:
        Et requests.Response-objekt.
        """
        return self._session.request(
            method=method,
            url=self._create_url(endpoint),
            headers=self._create_headers(token),
            json=json_body,
            params=params,
            timeout=30,
        )

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Udfører et generelt FASIT API-kald.

        Ved HTTP 401 bliver tokenet fornyet, og requesten forsøges
        én gang mere.

        Output:
        FASITs JSON-response som en dictionary.
        """
        token = await self._token_manager.get_token()

        response = await asyncio.to_thread(
            self._send_request,
            method,
            endpoint,
            token,
            json_body,
            params,
        )

        if response.status_code == 401:
            print(
                "⚠️ FASIT-tokenet blev afvist med HTTP 401. "
                "Henter et nyt token og prøver igen."
            )

            self._token_manager.invalidate()

            token = await self._token_manager.get_token()

            response = await asyncio.to_thread(
                self._send_request,
                method,
                endpoint,
                token,
                json_body,
                params,
            )

        try:
            response_body = response.json()
        except requests.exceptions.JSONDecodeError as error:
            raise RuntimeError(
                "FASIT returnerede et svar, som ikke var JSON. "
                f"HTTP-status: {response.status_code}."
            ) from error

        if not isinstance(response_body, dict):
            raise RuntimeError(
                "FASIT returnerede JSON i et uventet format. "
                f"HTTP-status: {response.status_code}."
            )

        if not response.ok:
            correlation_identifier = (
                response.headers.get(
                    "X-CorrelationIdentifier"
                )
                or response.headers.get(
                    "x-correlationidentifier"
                )
                or response_body.get(
                    "correlationIdentifier"
                )
            )

            detail = (
                response_body.get("detail")
                or response_body.get("title")
                or response_body.get("messageTitle")
            )

            error_message = (
                "FASIT API-kaldet fejlede. "
                f"Metode: {method}. "
                f"Endpoint: {endpoint}. "
                f"HTTP-status: {response.status_code}."
            )

            if detail:
                error_message += f" Fejl: {detail}."

            if correlation_identifier:
                error_message += (
                    " Correlation identifier: "
                    f"{correlation_identifier}."
                )

            raise RuntimeError(error_message)

        return response_body

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Sender en GET-request til FASIT.

        Parametre:
        - endpoint: API-stien, eksempelvis "/api/citizens/123".
        - params: Eventuelle query-parametre.

        Output:
        FASITs JSON-response som en dictionary.
        """
        return await self._request(
            method="GET",
            endpoint=endpoint,
            params=params,
        )

    async def post(
        self,
        endpoint: str,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Sender en POST-request til FASIT.

        Parametre:
        - endpoint: API-stien.
        - json_body: Requestens JSON-payload.

        Output:
        FASITs JSON-response som en dictionary.
        """
        return await self._request(
            method="POST",
            endpoint=endpoint,
            json_body=json_body,
        )

    async def close(self) -> None:
        """
        Lukker HTTP-sessionen.

        Token-manageren lukkes ikke her, fordi token-manageren kan
        være delt med andre API-klienter eller dele af processen.

        Output:
        Funktionen returnerer ikke en værdi.
        """
        await asyncio.to_thread(
            self._session.close
        )