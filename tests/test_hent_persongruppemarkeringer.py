import asyncio
import json
import os
from typing import Any

from dotenv import load_dotenv

from q_fasit.api.borger import (
    hent_persongruppemarkeringer,
)
from q_fasit.api.client import FasitApiClient
from q_fasit.api.token_manager import FasitTokenManager


TEST_CITIZEN_ID = (
    "2a6c2537-3a1b-4f42-9c70-a1297ee3329c"
)


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
    Validerer API-resultatet.

    Output:
    Det validerede resultat som en dictionary.
    """
    if not isinstance(result, dict):
        raise RuntimeError(
            "Resultatet fra "
            "hent_persongruppemarkeringer "
            "skal være en dictionary. "
            f"Modtog {type(result).__name__}."
        )

    return result


def _find_markeringer(
    result: dict[str, Any],
) -> list[Any] | None:
    """
    Finder listen med persongruppemarkeringer
    i API-resultatet.

    Funktionen understøtter almindelige feltnavne,
    men kræver ikke en bestemt responsstruktur for,
    at selve testen kan gennemføres.
    """
    possible_fields = (
        "personGroupMarkings",
        "personGroupMarking",
        "markings",
        "items",
        "results",
        "data",
    )

    for field_name in possible_fields:
        candidate = result.get(
            field_name
        )

        if isinstance(candidate, list):
            return candidate

    return None


def _print_result_summary(
    result: dict[str, Any],
) -> None:
    """
    Udskriver en kort opsummering af API-resultatet.
    """
    print()
    print(
        "Persongruppemarkeringer blev hentet."
    )
    print(
        "Felter i API-resultatet: "
        + ", ".join(
            sorted(result.keys())
        )
    )

    markeringer = _find_markeringer(
        result
    )

    if markeringer is not None:
        print(
            "Antal persongruppemarkeringer: "
            f"{len(markeringer)}"
        )
    else:
        print(
            "API-resultatet indeholdt ikke en liste "
            "under et kendt feltnavn."
        )


def _print_result(
    result: dict[str, Any],
) -> None:
    """
    Udskriver hele API-resultatet som JSON.

    Resultatet kan indeholde personoplysninger.
    """
    print()
    print("Result:")
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
    Tester hent_persongruppemarkeringer.

    Testens flow:
    1. Indlæser miljøvariabler.
    2. Starter token-manageren.
    3. Launcher FASIT i en browser.
    4. Opsnapper et gyldigt Bearer-token.
    5. Henter borgerens persongruppemarkeringer.
    6. Validerer og udskriver API-resultatet.
    7. Lukker API-klient og browser-session.
    """
    load_dotenv()

    headless = _get_headless_setting()

    citizen_id = os.getenv(
        "TEST_CITIZEN_ID",
        TEST_CITIZEN_ID,
    ).strip()

    if not citizen_id:
        raise RuntimeError(
            "TEST_CITIZEN_ID må ikke være tom."
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
            "Starter test af "
            "hent_persongruppemarkeringer..."
        )
        print(
            "Launcher FASIT og henter token..."
        )

        result = await hent_persongruppemarkeringer(
            api_client=api_client,
            citizen_id=citizen_id,
        )

        validated_result = _validate_result(
            result
        )

        _print_result_summary(
            validated_result
        )

        _print_result(
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