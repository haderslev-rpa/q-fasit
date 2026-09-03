import asyncio
import json
import logging
import os
from typing import Any

from dotenv import load_dotenv

from q_fasit.api.borger import (
    hent_borger_adressehistorik,
    hent_borger_id,
)
from q_fasit.api.client import FasitApiClient
from q_fasit.api.token_manager import FasitTokenManager


logger = logging.getLogger(__name__)


def _configure_logging() -> None:
    """
    Konfigurerer logging til integrationstesten.
    """
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )


def _print_result(
    result: dict[str, Any],
) -> None:
    """
    Udskriver adressehistorikken som formateret JSON.

    Resultatet kan indeholde personoplysninger og bør
    derfor ikke gemmes i permanente logs.
    """
    print()
    print("=" * 80)
    print("BORGER_ADRESSEHISTORIK")
    print("=" * 80)

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
    Tester hentning af borgerens adressehistorik.

    Testflow:
    1. Indlæser test_cpr fra .env.
    2. Finder borgerens citizenId via CPR.
    3. Henter borgerens adressehistorik.
    4. Gemmer API-svaret i variablen result.
    """
    _configure_logging()
    load_dotenv()

    test_cpr = os.getenv(
        "test_cpr",
        "",
    ).strip()

    if not test_cpr:
        raise RuntimeError(
            "Variablen test_cpr mangler i .env-filen."
        )

    headless = os.getenv(
        "FASIT_HEADLESS",
        "false",
    ).strip().lower() in {
        "1",
        "true",
        "yes",
        "ja",
    }

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
            "Søger efter borger via CPR-nummer."
        )

        citizen_id = await hent_borger_id(
            api_client=api_client,
            cpr=test_cpr,
        )

        logger.info(
            "Borgeren blev fundet. "
            "Henter adressehistorik."
        )

        result = await hent_borger_adressehistorik(
            api_client=api_client,
            citizen_id=citizen_id,
        )

        if not isinstance(result, dict):
            raise RuntimeError(
                "BORGER_ADRESSEHISTORIK havde et "
                "uventet responseformat."
            )

        logger.info(
            "Borgerens adressehistorik blev hentet."
        )

        _print_result(
            result=result,
        )

    except Exception:
        logger.exception(
            "Testen af BORGER_ADRESSEHISTORIK fejlede."
        )

        if not headless:
            print()
            print(
                "Tryk Enter, når browseren må lukkes."
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
    asyncio.run(main())