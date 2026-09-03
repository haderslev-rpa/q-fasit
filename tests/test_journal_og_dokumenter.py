import asyncio
import json
import logging
import os
from typing import Any

from dotenv import load_dotenv

from q_fasit.api.borger import (
    JOURNAL_OG_DOKUMENTER,
    hent_borger_id,
)
from q_fasit.api.client import FasitApiClient
from q_fasit.api.token_manager import FasitTokenManager


logger = logging.getLogger(__name__)


def _get_headless_setting() -> bool:
    """
    Læser FASIT_HEADLESS fra miljøvariabler.

    Følgende værdier aktiverer headless:
    - 1
    - true
    - yes
    - ja
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


def _print_result(
    result: dict[str, Any],
) -> None:
    """
    Udskriver API-resultatet som formateret JSON.

    Bemærk:
    Resultatet kan indeholde personoplysninger og bør
    derfor kun udskrives i et godkendt testmiljø.
    """
    print()
    print("Result fra JOURNAL_OG_DOKUMENTER:")
    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )


async def main() -> None:
    """
    Tester API-funktionen JOURNAL_OG_DOKUMENTER.

    Testens flow:
    1. Indlæser test_cpr fra .env.
    2. Starter FASIT og opsnapper Bearer-token.
    3. Søger efter borgeren via CPR.
    4. Henter borgerens citizenId.
    5. Henter aktive journalnotater og dokumenter.
    6. Gemmer API-svaret i variablen result.
    """
    load_dotenv()

    test_cpr = os.getenv(
        "test_cpr",
        "",
    ).strip()

    if not test_cpr:
        raise RuntimeError(
            "Variablen test_cpr mangler i .env-filen."
        )

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
        logger.info(
            "Søger efter borger via FASIT API."
        )
        print("Søger efter borger via CPR...")

        citizen_id = await hent_borger_id(
            api_client=api_client,
            cpr=test_cpr,
        )

        if not citizen_id:
            raise RuntimeError(
                "Borgersøgningen returnerede ikke "
                "et citizenId."
            )

        print("Borgerens citizenId blev fundet.")
        print(
            "Henter JOURNAL_OG_DOKUMENTER..."
        )

        result = await JOURNAL_OG_DOKUMENTER(
            api_client=api_client,
            citizen_id=citizen_id,
        )

        if not isinstance(result, dict):
            raise RuntimeError(
                "JOURNAL_OG_DOKUMENTER returnerede "
                "et uventet format."
            )

        print(
            "JOURNAL_OG_DOKUMENTER blev hentet."
        )

        print(
            "Felter i API-resultatet:",
            ", ".join(sorted(result.keys())),
        )

        _print_result(result)

        logger.info(
            "Test af JOURNAL_OG_DOKUMENTER "
            "blev gennemført."
        )

    except Exception as error:
        logger.exception(
            "Test af JOURNAL_OG_DOKUMENTER fejlede."
        )

        print()
        print("Testen stoppede med en fejl.")
        print(
            f"Fejltype: {type(error).__name__}"
        )
        print(f"Fejltekst: {error}")

        if not headless:
            print()
            print(
                "Browseren holdes åben for fejlsøgning."
            )
            print(
                "Tryk Enter i terminalen, når "
                "browseren må lukkes."
            )
            await asyncio.to_thread(input)

        raise

    finally:
        await api_client.close()
        await token_manager.close()

        logger.info(
            "API-klient og token manager er lukket."
        )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )

    asyncio.run(main())