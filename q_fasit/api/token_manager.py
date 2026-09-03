import base64
import json
import time
from typing import Any

from q_fasit.api.token_capture import FasitApiTokenCapture
from q_fasit.functionality.launch import launch_fasit
from q_haderslev_vbo.playwright.browser_session import BrowserSession


class FasitTokenManager:
    """
    Holder FASIT-tokenet i hukommelsen og fornyer det efter behov.

    Klassen launcher kun FASIT, når:

    - der ikke findes et token,
    - tokenet er ved at udløbe,
    - eller tokenet er blevet ugyldiggjort efter HTTP 401.

    Output fra get_token():
    Tokenet som tekst uden ordet "Bearer".
    """

    def __init__(
        self,
        credential_name: str,
        headless: bool = True,
        fallback_lifetime_seconds: int = 15 * 60,
        expiry_margin_seconds: int = 60,
    ) -> None:
        self._credential_name = credential_name
        self._headless = headless

        # Bruges kun, hvis tokenet ikke indeholder et JWT exp-felt.
        self._fallback_lifetime_seconds = fallback_lifetime_seconds

        # Tokenet fornyes lidt før den formelle udløbstid.
        self._expiry_margin_seconds = expiry_margin_seconds

        self._token: str | None = None
        self._expires_at: float | None = None

        self._session: BrowserSession | None = None
        self._page: Any = None
        self._token_capture: FasitApiTokenCapture | None = None

    def _decode_jwt_payload(
        self,
        token: str,
    ) -> dict[str, Any] | None:
        """
        Forsøger at læse metadata fra et JWT-token.

        Funktionen validerer ikke JWT-signaturen. Formålet er kun
        at aflæse tokenets exp-felt.

        Output:
        - JWT-payloaden som dictionary.
        - None, hvis tokenet ikke kan aflæses som JWT.
        """
        token_parts = token.split(".")

        if len(token_parts) != 3:
            return None

        encoded_payload = token_parts[1]
        encoded_payload += "=" * (-len(encoded_payload) % 4)

        try:
            decoded_payload = base64.urlsafe_b64decode(
                encoded_payload.encode("ascii")
            )

            payload = json.loads(
                decoded_payload.decode("utf-8")
            )
        except (
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ):
            return None

        if not isinstance(payload, dict):
            return None

        return payload

    def _get_token_expiry(
        self,
        token: str,
    ) -> float:
        """
        Finder tokenets udløbstid.

        Output:
        Et Unix-tidsstempel.

        JWT-tokenets exp-felt anvendes, hvis det findes. Ellers
        anvendes fallback_lifetime_seconds fra det aktuelle tidspunkt.
        """
        jwt_payload = self._decode_jwt_payload(token)

        if jwt_payload:
            expires_at = jwt_payload.get("exp")

            if isinstance(expires_at, (int, float)):
                return float(expires_at)

        print(
            "Tokenet havde ikke et læsbart JWT exp-felt. "
            "Bruger fast reservelevetid."
        )

        return (
            time.time()
            + self._fallback_lifetime_seconds
        )

    def has_valid_token(self) -> bool:
        """
        Kontrollerer om tokenet stadig kan bruges.

        Output:
        - True, hvis tokenet findes og ikke er ved at udløbe.
        - False, hvis tokenet mangler eller bør fornyes.
        """
        if not self._token:
            return False

        if self._expires_at is None:
            return False

        refresh_at = (
            self._expires_at
            - self._expiry_margin_seconds
        )

        return time.time() < refresh_at

    async def _start_browser(self) -> None:
        """
        Starter en ny browser-session.

        Output:
        Funktionen gemmer BrowserSession og Page internt.
        Funktionen returnerer ikke en værdi.
        """
        await self._close_browser()

        self._session = BrowserSession(
            headless=self._headless,
            debug=not self._headless,
            video=False,
        )

        await self._session.start()
        self._page = await self._session.new_page()

    async def _close_browser(self) -> None:
        """
        Lukker den eksisterende browser-session.

        Output:
        Funktionen returnerer ikke en værdi.
        """
        if self._token_capture:
            self._token_capture.stop()
            self._token_capture = None

        if self._session:
            try:
                await self._session.close()
            finally:
                self._session = None
                self._page = None

    async def refresh_token(self) -> str:
        """
        Launcher FASIT og henter et nyt Jobcenter BFF-token.

        Output:
        Det nye token som tekst uden ordet "Bearer".
        """
        print("Fornyer FASIT-token...")

        await self._start_browser()

        self._token_capture = FasitApiTokenCapture(
            self._page
        )

        self._token_capture.start()

        try:
            await launch_fasit(
                page=self._page,
                session=self._session,
                credential_name=self._credential_name,
            )

            # Giv startsidens API-kald mulighed for at blive sendt.
            await self._page.wait_for_timeout(2_000)

            if not self._token_capture.has_token():
                print(
                    "Intet Jobcenter BFF-token blev set under "
                    "første load. Genindlæser startsiden."
                )

                await self._page.reload(
                    wait_until="domcontentloaded"
                )

                await self._page.wait_for_timeout(3_000)

            if not self._token_capture.has_token():
                raise RuntimeError(
                    "FASIT blev åbnet, men der blev ikke "
                    "fundet et Bearer-token til "
                    "jobcenter-bff.schultzfasit.dk."
                )

            new_token = self._token_capture.get_token()

            self._token = new_token
            self._expires_at = self._get_token_expiry(
                new_token
            )

            seconds_remaining = max(
                0,
                int(self._expires_at - time.time()),
            )

            print(
                "Nyt FASIT-token gemt i hukommelsen."
            )
            print(
                "Tokenfingeraftryk: "
                f"{self._token_capture.get_fingerprint()}"
            )
            print(
                "Forventet resterende levetid: "
                f"{seconds_remaining} sekunder"
            )

            return new_token

        except Exception:
            # Et mislykket login må ikke efterlade et gammelt
            # token som tilsyneladende gyldigt.
            self.invalidate()
            raise

    async def get_token(self) -> str:
        """
        Returnerer et gyldigt FASIT-token.

        Hvis det nuværende token stadig er gyldigt, returneres det
        direkte fra hukommelsen. Ellers åbnes FASIT, og et nyt token
        bliver hentet.

        Output:
        Tokenet som tekst uden ordet "Bearer".
        """
        if self.has_valid_token():
            return self._token  # type: ignore[return-value]

        return await self.refresh_token()

    def invalidate(self) -> None:
        """
        Markerer tokenet som ugyldigt.

        Bruges eksempelvis efter HTTP 401.

        Output:
        Funktionen returnerer ikke en værdi.
        """
        self._token = None
        self._expires_at = None

    async def close(self) -> None:
        """
        Lukker browser-sessionen og fjerner tokenet fra hukommelsen.

        Output:
        Funktionen returnerer ikke en værdi.
        """
        self.invalidate()
        await self._close_browser()