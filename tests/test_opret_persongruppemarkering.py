import asyncio
import json
import os

from dotenv import load_dotenv

from q_fasit.api.borger import (
    opret_persongruppemarkering,
)
from q_fasit.api.client import FasitApiClient
from q_fasit.api.token_manager import FasitTokenManager


TEST_STARTDATO = "04-09-2026"
TEST_SLUTDATO = "05-09-2026"
TEST_PERSONGRUPPE = "automatiseringsteamet"
TEST_CITIZEN_ID = (
    "2a6c2537-3a1b-4f42-9c70-a1297ee3329c"
)


def _get_headless_setting() -> bool:
    """
    Læser FASIT_HEADLESS fra miljøvariabler.
    """
    return os.getenv(
        "FASIT_HEADLESS",
        "false",
    ).strip().lower() in {
        "1",
        "true",
        "yes",
        "ja",
    }


async def main() -> None:
    """
    Tester oprettelse af en persongruppemarkering.

    Testværdier:
    - Startdato: 04/09/2026
    - Slutdato: 05/09/2026
    - Persongruppe: automatiseringsteamet
    - CitizenId: TEST_CITIZEN_ID
    """
    load_dotenv()

    headless = _get_headless_setting()

    token_manager = FasitTokenManager(
        credential_name="DIRXOPS",
        headless=headless,
        fallback_lifetime_seconds=15 * 60,
        expiry_margin_seconds=60,
    )

    api_client = FasitApiClient(
        token_manager=token_manager,
    )

    try:
        print(
            "Starter test af "
            "opret_persongruppemarkering..."
        )
        print(
            f"Startdato: {TEST_STARTDATO}"
        )
        print(
            f"Slutdato: {TEST_SLUTDATO}"
        )
        print(
            f"Persongruppe: {TEST_PERSONGRUPPE}"
        )

        result = await opret_persongruppemarkering(
            api_client=api_client,
            startdato=TEST_STARTDATO,
            slutdato=TEST_SLUTDATO,
            citizen_id=TEST_CITIZEN_ID,
            persongruppenavn=TEST_PERSONGRUPPE,
        )

        if not isinstance(result, dict):
            raise RuntimeError(
                "Oprettelsen returnerede et "
                "uventet format."
            )

        print()
        print(
            "Persongruppemarkeringen blev oprettet."
        )
        print(
            "Felter i resultatet: "
            + ", ".join(
                sorted(result.keys())
            )
        )

        print()
        print("Result:")
        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        )

    except Exception as error:
        print()
        print(
            "Testen stoppede med en fejl."
        )
        print(
            f"Fejltype: {type(error).__name__}"
        )
        print(
            f"Fejltekst: {error}"
        )

        if not headless:
            print()
            print(
                "Browseren holdes åben. "
                "Tryk Enter, når den må lukkes."
            )

            await asyncio.to_thread(
                input
            )

        raise

    finally:
        await api_client.close()
        await token_manager.close()

        print()
        print(
            "API-klient og token manager er lukket."
        )


if __name__ == "__main__":
    asyncio.run(
        main()
    )