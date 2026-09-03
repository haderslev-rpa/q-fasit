import asyncio
import os

from dotenv import load_dotenv

from q_fasit.api.borger import hent_borger_id
from q_fasit.api.client import FasitApiClient
from q_fasit.api.token_manager import FasitTokenManager


async def main() -> None:
    """
    Tester hent_borger_id med ét borgersøgningskald.

    Testens flow:

    1. FASIT launches.
    2. Tokenet opsnappes passivt fra FASITs egne requests.
    3. Tokenet gemmes i hukommelsen.
    4. Der udføres ét API-kald for at hente borgerens id.

    Output:
    Testen udskriver, om borger-id'et blev fundet.

    CPR-nummer, token og borger-id bliver ikke udskrevet.
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
        print("🔎 Søger efter borger via FASIT API...")

        borger_id = await hent_borger_id(
            api_client=api_client,
            cpr=test_cpr,
        )

        if not borger_id:
            raise RuntimeError(
                "Borgersøgningen returnerede ikke et borger-id."
            )

        print("✅ Borger-id blev fundet.")
        print("✅ Testen gennemførte ét borgersøgningskald.")

    except Exception as error:
        print()
        print("❌ Testen stoppede med en fejl.")
        print(f"Fejltype: {type(error).__name__}")
        print(f"Fejltekst: {error}")

        if not headless:
            print()
            print(
                "Browseren holdes åben. Tryk Enter i terminalen, "
                "når browseren må lukkes."
            )

            await asyncio.to_thread(input)

        raise

    finally:
        await api_client.close()
        await token_manager.close()


if __name__ == "__main__":
    asyncio.run(main())