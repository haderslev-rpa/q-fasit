import asyncio
import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from q_fasit.api.borger import (
    OPLYSNINGSSKEMA_TARGET_GROUP_ID,
    hent_liste_oplysningsskemaer,
)
from q_fasit.api.client import FasitApiClient
from q_fasit.api.token_manager import FasitTokenManager


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


def _validate_result(
    result: Any,
) -> dict[str, Any]:
    """
    Validerer det samlede resultat fra
    hent_liste_oplysningsskemaer().

    Output:
    Det validerede resultat som en dictionary.
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
            f"men testen modtog kun {total_results}."
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
    results = result["results"]

    print()
    print("Udtrækket er færdigt.")
    print(
        "Antal hentede poster: "
        f"{result['totalResults']}"
    )
    print(
        "Antal udførte sidekald: "
        f"{result['pageCount']}"
    )
    print(
        "Antal sider oplyst af FASIT: "
        f"{result.get('reportedPageCount')}"
    )
    print(
        "Samlet antal oplyst af FASIT: "
        f"{result.get('reportedTotal')}"
    )

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
                sorted(first_result.keys())
            )
        )

def _print_rows(
    result: dict[str, Any],
) -> None:
    """
    Udskriver alle hentede rækker med rækkenummer.

    Hver række formateres som JSON, så indlejrede
    dictionaries og lister vises læsbart.
    """
    rows = result.get(
        "results",
        [],
    )

    if not isinstance(rows, list):
        raise RuntimeError(
            "Feltet 'results' er ikke en liste."
        )

    print()
    print("=" * 80)
    print(
        f"RÆKKER FRA FASIT, ANTAL: {len(rows)}"
    )
    print("=" * 80)

    if not rows:
        print(
            "Der blev ikke fundet nogen rækker."
        )
        return

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

        if isinstance(row, dict):
            print(
                json.dumps(
                    row,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
            )
        else:
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


def _write_results_to_file(
    result: dict[str, Any],
) -> None:
    """
    Gemmer de samlede resultater som JSON.

    Filen oprettes kun, hvis miljøvariablen
    OPLYSNINGSSKEMA_OUTPUT_FILE er angivet.
    """
    output_file_value = os.getenv(
        "OPLYSNINGSSKEMA_OUTPUT_FILE",
        "",
    ).strip()

    if not output_file_value:
        return

    output_path = Path(
        output_file_value
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            result["results"],
            file,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    print()
    print(
        "Resultatet blev gemt i: "
        f"{output_path.resolve()}"
    )


async def main() -> None:
    """
    Tester hentning af hele listen over
    oplysningsskemaer.

    Testens flow:
    1. Indlæser miljøvariabler.
    2. Opretter token-manager og API-klient.
    3. Kalder hent_liste_oplysningsskemaer én gang.
    4. Funktionen i borger.py henter alle sider.
    5. Det samlede resultat valideres.
    6. Resultatet gemmes eventuelt som JSON.
    """
    load_dotenv()

    headless = _get_headless_setting()

    created_after = os.getenv(
        "OPLYSNINGSSKEMA_CREATED_AFTER",
        "2025-06-16T22:00:00Z",
    ).strip()

    if not created_after:
        raise RuntimeError(
            "OPLYSNINGSSKEMA_CREATED_AFTER "
            "må ikke være tom."
        )

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
            "Henter hele listen over "
            "oplysningsskemaer..."
        )
        print(
            f"Oprettet efter: {created_after}"
        )
        print(
            "Target group-id: "
            f"{OPLYSNINGSSKEMA_TARGET_GROUP_ID}"
        )
        print(
            "Sagsstatusser: 1 og 3"
        )
        print(
            "Sidestørrelse: 250"
        )

        result = await hent_liste_oplysningsskemaer(
            api_client=api_client,
            created_after=created_after,
            target_group_id=(
                OPLYSNINGSSKEMA_TARGET_GROUP_ID
            ),
            case_statuses=[
                "1",
                "3",
            ],
            page_size=250,
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

        _write_results_to_file(
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

        if not headless:
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