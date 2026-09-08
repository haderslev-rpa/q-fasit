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


def _validate_result(
    result: Any,
) -> dict[str, Any]:
    """
    Validerer listeudtrækkets samlede resultat.
    """
    if not isinstance(result, dict):
        raise RuntimeError(
            "Resultatet skal være en dictionary. "
            f"Modtog {type(result).__name__}."
        )

    results = result.get(
        "results"
    )

    if not isinstance(results, list):
        raise RuntimeError(
            "Resultatet mangler en liste i "
            "feltet 'results'."
        )

    total_results = result.get(
        "totalResults"
    )

    if (
        not isinstance(total_results, int)
        or isinstance(total_results, bool)
    ):
        raise RuntimeError(
            "Resultatet mangler et heltal i "
            "feltet 'totalResults'."
        )

    page_count = result.get(
        "pageCount"
    )

    if (
        not isinstance(page_count, int)
        or isinstance(page_count, bool)
    ):
        raise RuntimeError(
            "Resultatet mangler et heltal i "
            "feltet 'pageCount'."
        )

    reported_total = result.get(
        "reportedTotal"
    )

    if (
        reported_total is not None
        and (
            not isinstance(reported_total, int)
            or isinstance(reported_total, bool)
        )
    ):
        raise RuntimeError(
            "Feltet 'reportedTotal' skal være "
            "et heltal eller None."
        )

    reported_page_count = result.get(
        "reportedPageCount"
    )

    if (
        reported_page_count is not None
        and (
            not isinstance(
                reported_page_count,
                int,
            )
            or isinstance(
                reported_page_count,
                bool,
            )
        )
    ):
        raise RuntimeError(
            "Feltet 'reportedPageCount' skal være "
            "et heltal eller None."
        )

    if total_results != len(results):
        raise RuntimeError(
            "totalResults matcher ikke antallet "
            "af poster i results. "
            f"totalResults={total_results}, "
            f"len(results)={len(results)}."
        )

    if (
        reported_total is not None
        and total_results != reported_total
    ):
        raise RuntimeError(
            "Ikke alle resultater blev hentet. "
            f"FASIT oplyste {reported_total} resultater, "
            f"men testen modtog {total_results}."
        )

    if (
        reported_page_count is not None
        and page_count != reported_page_count
    ):
        raise RuntimeError(
            "Antallet af udførte sidekald matcher "
            "ikke FASITs oplyste sideantal. "
            f"Udførte sidekald: {page_count}. "
            f"Oplyste sider: {reported_page_count}."
        )

    return result


def _print_result_summary(
    result: dict[str, Any],
) -> None:
    """
    Udskriver en kort opsummering af resultatet.
    """
    print()
    print(
        "Udtrækket er færdigt."
    )
    print(
        "Antal hentede poster: "
        f"{result['totalResults']}"
    )
    print(
        "Antal udførte sidekald: "
        f"{result['pageCount']}"
    )

    results = result["results"]

    if not results:
        print(
            "Der blev ikke fundet nogen poster."
        )
        return

    first_result = results[0]

    print()
    print(
        "Datatype for første resultat: "
        f"{type(first_result).__name__}"
    )

    if isinstance(first_result, dict):
        print(
            "Felter i første resultat: "
            + ", ".join(
                sorted(
                    str(key)
                    for key in first_result.keys()
                )
            )
        )


def _print_rows(
    result: dict[str, Any],
) -> None:
    """
    Udskriver alle hentede rækker med rækkenummer.
    """
    rows = result["results"]

    print()
    print("=" * 80)
    print(
        "AKTIVITETSPARATE "
        "KONTANTHJÆLPSMODTAGERE OVER 30"
    )
    print(
        f"ANTAL RÆKKER: {len(rows)}"
    )
    print("=" * 80)

    for row_number, row in enumerate(
        rows,
        start=1,
    ):
        print()
        print("-" * 80)
        print(
            f"Række {row_number} af {len(rows)}"
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
        f"Alle {len(rows)} rækker er udskrevet."
    )
    print("=" * 80)


async def main() -> None:
    """
    Tester hentning af hele listen over
    aktivitetsparate kontanthjælpsmodtagere
    over 30 år.

    Testens flow:
    1. Opretter token-manager og API-klient.
    2. Launcher FASIT ved første API-kald.
    3. Henter alle sider fra /api/search.
    4. Samler alle rækker i result["results"].
    5. Validerer resultatet.
    6. Udskriver rækkerne.
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
        print(
            "Target group-id: "
            f"{AKTIVITETSPARATE_TARGET_GROUP_ID}"
        )
        print(
            "Primære sagsstatusser: 1 og 3"
        )
        print(
            f"Sidestørrelse: {PAGE_SIZE}"
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

        validated_result = _validate_result(
            result
        )

        _print_result_summary(
            validated_result
        )

        _print_rows(
            validated_result
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