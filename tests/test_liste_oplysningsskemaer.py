import asyncio
import os
from typing import Any

from dotenv import load_dotenv

from q_fasit.api.borger import (
    OPLYSNINGSSKEMA_TARGET_GROUP_ID,
    hent_liste_oplysningsskemaer,
)
from q_fasit.api.client import FasitApiClient
from q_fasit.api.token_manager import FasitTokenManager


async def main() -> None:
    """
    Tester at alle oplysningsskemaer returneres
    direkte som en liste med rækker.
    """
    load_dotenv()

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
        raekker = await hent_liste_oplysningsskemaer(
            api_client=api_client,
            created_after="2025-06-16T22:00:00Z",
            target_group_id=(
                OPLYSNINGSSKEMA_TARGET_GROUP_ID
            ),
            case_statuses=[
                "1",
                "3",
            ],
            page_size=250,
        )

        if not isinstance(raekker, list):
            raise RuntimeError(
                "Resultatet skal være en liste."
            )

        for index, raekke in enumerate(
            raekker,
            start=1,
        ):
            if not isinstance(raekke, dict):
                raise RuntimeError(
                    f"Række {index} er ikke "
                    "en dictionary."
                )

        print()
        print(
            "Testen blev gennemført korrekt."
        )
        print(
            "Antal hentede rækker: "
            f"{len(raekker)}"
        )

        if raekker:
            print(
                "Felter i første række: "
                + ", ".join(
                    sorted(raekker[0].keys())
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
        raise

    finally:
        await api_client.close()
        await token_manager.close()


if __name__ == "__main__":
    asyncio.run(
        main()
    )