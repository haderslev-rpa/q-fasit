import asyncio
import json
from typing import Any

from q_fasit.api.borger import (
    AKTIVITETSPARATE_TARGET_GROUP_ID,
    hent_aktivitetsparate_kontanthjaelpsmodtagere_over_30,
)
from q_fasit.api.client import FasitApiClient
from q_fasit.api.token_manager import FasitTokenManager


FASIT_CREDENTIAL_NAME = "DIRXOPS"
FASIT_HEADLESS = False
PAGE_SIZE = 250
ANTAL_RAEKKER_TIL_UDSKRIFT = 5


def _validate_result(
    result: Any,
) -> list[dict[str, Any]]:
    """
    Validerer, at resultatet er en liste
    med dictionaries.
    """
    if not isinstance(result, list):
        raise RuntimeError(
            "Resultatet skal være en liste. "
            f"Modtog {type(result).__name__}."
        )

    for row_number, row in enumerate(
        result,
        start=1,
    ):
        if not isinstance(row, dict):
            raise RuntimeError(
                f"Række {row_number} skal være "
                "en dictionary. "
                f"Modtog {type(row).__name__}."
            )

    return result


def _print_result_summary(
    rows: list[dict[str, Any]],
) -> None:
    """
    Udskriver en kort opsummering.
    """
    print()
    print(
        "Udtrækket er færdigt."
    )
    print(
        "Antal hentede poster: "
        f"{len(rows)}"
    )

    if not rows:
        print(
            "Der blev ikke fundet nogen poster."
        )
        return

    print(
        "Felter i første resultat: "
        + ", ".join(
            sorted(
                str(key)
                for key in rows[0].keys()
            )
        )
    )


def _print_rows(
    rows: list[dict[str, Any]],
    antal: int = 5,
) -> None:
    """
    Udskriver maksimalt det angivne antal rækker.
    """
    rows_to_print = rows[
        :antal
    ]

    print()
    print("=" * 80)
    print(
        "AKTIVITETSPARATE "
        "KONTANTHJÆLPSMODTAGERE OVER 30"
    )
    print(
        f"VISER {len(rows_to_print)} "
        f"AF {len(rows)} RÆKKER"
    )
    print("=" * 80)

    for row_number, row in enumerate(
        rows_to_print,
        start=1,
    ):
        print()
        print("-" * 80)
        print(
            f"Række {row_number}"
        )
        print("-" * 80)

        print(
            json.dumps(
                row,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
        )

    print()
    print("=" * 80)
    print(
        f"{len(rows_to_print)} rækker er udskrevet."
    )
    print("=" * 80)


async def main() -> None:
    """
    Tester aktivitetsparate-listen og
    udskriver de første fem rækker.
    """
    token_manager = FasitTokenManager(
        credential_name=FASIT_CREDENTIAL_NAME,
        headless=FASIT_HEADLESS,
        fallback_lifetime_seconds=15 * 60,
        expiry_margin_seconds=60,
    )

    api_client = FasitApiClient(
        token_manager=token_manager,
    )

    try:
        print(
            "Henter aktivitetsparate "
            "kontanthjælpsmodtagere over 30 år..."
        )

        result = (
            await hent_aktivitetsparate_kontanthjaelpsmodtagere_over_30(
                api_client=api_client,
                target_group_id=(
                    AKTIVITETSPARATE_TARGET_GROUP_ID
                ),
                primary_case_statuses=[
                    "1",
                    "3",
                ],
                page_size=PAGE_SIZE,
            )
        )

        rows = _validate_result(
            result
        )

        _print_result_summary(
            rows
        )

        _print_rows(
            rows=rows,
            antal=ANTAL_RAEKKER_TIL_UDSKRIFT,
        )

        print()
        print(
            "Testen blev gennemført korrekt."
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

        if not FASIT_HEADLESS:
            print()
            print(
                "Browseren holdes åben for "
                "fejlsøgning."
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

        print()
        print(
            "API-klient og token manager er lukket."
        )


if __name__ == "__main__":
    asyncio.run(
        main()
    )