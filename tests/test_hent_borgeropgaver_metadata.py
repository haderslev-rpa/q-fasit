import asyncio
import json
import os
from typing import Any

from dotenv import load_dotenv

from q_fasit.api.borger import (
    hent_borgeropgaver_metadata,
)
from q_fasit.api.client import FasitApiClient
from q_fasit.api.token_manager import FasitTokenManager


def print_result(
    result: dict[str, Any],
) -> None:
    """
    Udskriver API-resultatet som formateret JSON.
    """
    print()
    print("=" * 80)
    print("ALLE OPGAVER")
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
    Tester hentning af metadata for alle borgerens opgaver.

    Flow:
    1. Indlæser TEST_CITIZEN_ID fra .env.
    2. Opretter token-manager og API-klient.
    3. Henter metadata for alle borgerens opgaver
       direkte via citizenId.
    4. Gemmer API-svaret i variablen result.
    """
    load_dotenv()

    citizen_id = os.getenv(
        "TEST_CITIZEN_ID",
        "",
    ).strip()

    if not citizen_id:
        raise RuntimeError(
            "Variablen TEST_CITIZEN_ID mangler "
            "i .env-filen."
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
        print(
            "Henter metadata for alle borgerens "
            "opgaver via citizenId..."
        )

        result = await hent_borgeropgaver_metadata(
            api_client=api_client,
            citizen_id=citizen_id,
        )

        if not isinstance(result, dict):
            raise RuntimeError(
                "FASIT returnerede opgavemetadata i et "
                "uventet format. Forventede en dictionary, "
                f"men modtog {type(result).__name__}."
            )

        print(
            "Metadata for alle borgerens opgaver blev hentet."
        )

        print_result(
            result=result,
        )

    except Exception as error:
        print()
        print("=" * 80)
        print("TESTEN STOPPEDE MED EN FEJL")
        print("=" * 80)
        print(
            f"Fejltype: {type(error).__name__}"
        )
        print(
            f"Fejltekst: {error}"
        )

        if not headless:
            print()
            print(
                "Browseren holdes åben, så fejlen "
                "kan undersøges."
            )
            print(
                "Tryk Enter i terminalen, når "
                "browseren må lukkes."
            )

            await asyncio.to_thread(
                input
            )

        raise

    finally:
        await api_client.close()
        await token_manager.close()


if __name__ == "__main__":
    asyncio.run(
        main()
    )