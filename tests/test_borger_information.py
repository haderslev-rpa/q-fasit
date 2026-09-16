import asyncio
import json
import os

from dotenv import load_dotenv

from q_fasit.api.borger import BORGER_INFORMATION
from q_fasit.api.client import FasitApiClient
from q_fasit.api.token_manager import FasitTokenManager


async def main() -> None:
    """
    Tester API-funktionen BORGER_INFORMATION.

    Flow:
    1. Læser TEST_CITIZEN_ID fra .env.
    2. Henter borgerens information og myndighedskontekst.
    3. Gemmer API-svaret i variablen result.
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
            "Henter BORGER_INFORMATION "
            "med citizenId..."
        )

        result = await BORGER_INFORMATION(
            api_client=api_client,
            citizen_id=citizen_id,
        )

        if not isinstance(result, dict):
            raise RuntimeError(
                "BORGER_INFORMATION returnerede "
                "et uventet format."
            )

        print(
            "BORGER_INFORMATION blev hentet."
        )
        print()
        print(
            "Result fra BORGER_INFORMATION:"
        )
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
                "Browseren holdes åben for fejlsøgning. "
                "Tryk Enter, når browseren må lukkes."
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