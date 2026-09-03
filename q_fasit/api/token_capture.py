import hashlib
from urllib.parse import urlparse

from playwright.async_api import Page, Request


JOB_CENTER_BFF_HOST = "jobcenter-bff.schultzfasit.dk"


def create_token_fingerprint(token: str) -> str:
    """
    Opretter et kort og ikke-reversibelt fingeraftryk af et token.

    Output:
    En tekststreng på 12 tegn, eksempelvis:
    "4098c589445d"

    Funktionen returnerer ikke selve tokenet.
    """
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()[:12]


def extract_bearer_token(request: Request) -> str | None:
    """
    Udtrækker Bearer-tokenet fra en Playwright-request.

    Output:
    - Tokenet som tekst uden ordet "Bearer", hvis requesten
      indeholder Authorization-headeren.
    - None, hvis requesten ikke indeholder et Bearer-token.
    """
    authorization = request.headers.get(
        "authorization",
        "",
    ).strip()

    prefix = "bearer "

    if not authorization.lower().startswith(prefix):
        return None

    token = authorization[len(prefix):].strip()

    if not token:
        return None

    return token


class FasitApiTokenCapture:
    """
    Opsnapper Bearer-tokenet til FASITs Jobcenter BFF.

    Klassen accepterer kun tokens fra:

    jobcenter-bff.schultzfasit.dk

    Tokens fra FASITs øvrige API-hosts bliver ignoreret.
    """

    def __init__(
        self,
        page: Page,
        target_host: str = JOB_CENTER_BFF_HOST,
    ) -> None:
        """
        Opretter en tokenopsamler til en Playwright-side.

        Parametre:
        - page: Den Playwright-side, hvor FASIT bliver åbnet.
        - target_host: Den API-host, tokenet skal opsnappes fra.

        Output:
        Der returneres ikke noget. Objektet skal efterfølgende
        startes med start().
        """
        self._page = page
        self._target_host = target_host.lower()

        self._token: str | None = None
        self._captured_url: str | None = None
        self._is_started = False

    def start(self) -> None:
        """
        Starter overvågningen af browserens requests.

        Funktionen skal kaldes før launch_fasit(), så requests fra
        FASITs startside bliver registreret.

        Output:
        Funktionen returnerer ikke en værdi.
        """
        if self._is_started:
            return

        self._page.on(
            "request",
            self._handle_request,
        )

        self._is_started = True

    def stop(self) -> None:
        """
        Stopper overvågningen af browserens requests.

        Det senest opsnappede token beholdes i hukommelsen og kan
        fortsat hentes med get_token().

        Output:
        Funktionen returnerer ikke en værdi.
        """
        if not self._is_started:
            return

        self._page.remove_listener(
            "request",
            self._handle_request,
        )

        self._is_started = False

    def _handle_request(
        self,
        request: Request,
    ) -> None:
        """
        Behandler en request fra browseren.

        Kun requests til target_host med en Bearer-header accepteres.
        Hvis flere matchende requests observeres, gemmes det senest
        observerede token.

        Funktionen er intern og skal ikke kaldes direkte.
        """
        parsed_url = urlparse(request.url)

        request_host = (
            parsed_url.hostname or ""
        ).lower()

        if request_host != self._target_host:
            return

        token = extract_bearer_token(request)

        if not token:
            return

        self._token = token
        self._captured_url = request.url

    def has_token(self) -> bool:
        """
        Kontrollerer, om der er fundet et token.

        Output:
        - True, hvis et token er opsnappet.
        - False, hvis intet token er opsnappet endnu.
        """
        return self._token is not None

    def get_token(self) -> str:
        """
        Returnerer det senest opsnappede Bearer-token.

        Output:
        Tokenet som tekst uden ordet "Bearer".

        Funktionen kaster RuntimeError, hvis der endnu ikke er
        fundet et token.
        """
        if not self._token:
            raise RuntimeError(
                "Der blev ikke fundet et Bearer-token til "
                f"{self._target_host}."
            )

        return self._token

    def get_fingerprint(self) -> str:
        """
        Returnerer et sikkert fingeraftryk af det fundne token.

        Output:
        En tekststreng på 12 tegn, eksempelvis:
        "4098c589445d"

        Funktionen viser ikke selve tokenet.
        """
        token = self.get_token()

        return create_token_fingerprint(token)

    def get_captured_url(self) -> str | None:
        """
        Returnerer URL'en, hvor tokenet senest blev observeret.

        Output:
        - Den fulde request-URL som tekst.
        - None, hvis der endnu ikke er fundet et token.
        """
        return self._captured_url