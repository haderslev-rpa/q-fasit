import asyncio
import json
import os

from dotenv import load_dotenv

from q_fasit.api.borger import (
    hent_borger_id,
    hent_borgeropgaver_metadata,
    hent_borgeroverblik_beskaeftigelse,
)
from q_fasit.api.client import FasitApiClient
from q_fasit.api.token_manager import FasitTokenManager


async def main() -> None:
    """
    Tester hentning af borgerdata fra FASIT.

    Flow:
    1. Borgeren søges frem via CPR.
    2. documentId hentes som citizenId.
    3. Borgeroverblik for beskæftigelse hentes.
    4. Metadata for alle borgerens opgaver hentes.
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
        print("Søger efter borger via CPR...")

        citizen_id = await hent_borger_id(
            api_client=api_client,
            cpr=test_cpr,
        )

        print("Borgerens citizenId blev fundet.")

        print()
        print(
            "Henter borgeroverbliksdata "
            "for beskæftigelse..."
        )

        result = await hent_borgeroverblik_beskaeftigelse(
            api_client=api_client,
            citizen_id=citizen_id,
        )

        if not isinstance(result, dict):
            raise RuntimeError(
                "FASIT returnerede borgeroverblikket "
                "i et uventet format."
            )

        print(
            "Borgeroverbliksdata blev hentet."
        )
        print()
        print("Result fra beskæftigelsesoverblik:")
        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        )

        print()
        print(
            "Henter metadata for borgerens opgaver..."
        )

        tasks_result = await hent_borgeropgaver_metadata(
            api_client=api_client,
            citizen_id=citizen_id,
        )

        if not isinstance(tasks_result, dict):
            raise RuntimeError(
                "FASIT returnerede opgavemetadata "
                "i et uventet format."
            )

        print(
            "Metadata for borgerens opgaver blev hentet."
        )
        print()
        print("Result fra opgavemetadata:")
        print(
            json.dumps(
                tasks_result,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        )

    except Exception as error:
        print()
        print("Testen stoppede med en fejl.")
        print(
            f"Fejltype: {type(error).__name__}"
        )
        print(f"Fejltekst: {error}")
        raise

    finally:
        await api_client.close()
        await token_manager.close()


if __name__ == "__main__":
    asyncio.run(main())