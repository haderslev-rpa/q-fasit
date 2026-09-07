import asyncio
import json
import os
from typing import Any

from dotenv import load_dotenv

from q_fasit.api.borger import (
    opret_kommunens_markeringer,
)
from q_fasit.api.client import FasitApiClient
from q_fasit.api.token_manager import FasitTokenManager


DEFAULT_TEST_CITIZEN_ID = (
    "2a6c2537-3a1b-4f42-9c70-a1297ee3329c"
)

# ---------------------------------------------------------
# Testindstillinger
# ---------------------------------------------------------
#
# KUN_LAES = True:
#   Feltet importantNote2 læses kun.
#   TEST_TEKST bliver ikke anvendt.
#
# KUN_LAES = False og TEST_TEKST = "test123":
#   Feltet importantNote2 overskrives med "test123".
#
# KUN_LAES = False og TEST_TEKST = "":
#   Feltet importantNote2 slettes/ryddes.
#
KUN_LAES = False
TEST_TEKST = ""


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


def _get_kun_laes_setting() -> bool:
    """
    Læser KOMMUNENS_MARKERING_KUN_LAES fra .env.

    Hvis miljøvariablen ikke findes, anvendes
    konstanten KUN_LAES.
    """
    default_value = (
        "true"
        if KUN_LAES
        else "false"
    )

    return os.getenv(
        "KOMMUNENS_MARKERING_KUN_LAES",
        default_value,
    ).strip().lower() in {
        "1",
        "true",
        "yes",
        "ja",
    }


def _get_test_tekst() -> str:
    """
    Læser teksten, der skal skrives i importantNote2.

    En tom tekst er tilladt og betyder, at feltet
    skal ryddes, når kun_laes er False.
    """
    return os.getenv(
        "TEST_KOMMUNENS_MARKERING_TEKST",
        TEST_TEKST,
    ).strip()


def _validate_result(
    result: Any,
    kun_laes: bool,
    tekst: str | None,
) -> dict[str, Any]:
    """
    Validerer resultatet fra
    opret_kommunens_markeringer().
    """
    if not isinstance(result, dict):
        raise RuntimeError(
            "Resultatet skal være en dictionary. "
            f"Modtog {type(result).__name__}."
        )

    field_name = result.get(
        "field"
    )

    if field_name != "importantNote2":
        raise RuntimeError(
            "Resultatet havde et uventet feltnavn. "
            f"Modtog {field_name!r}."
        )

    updated = result.get(
        "updated"
    )

    if not isinstance(updated, bool):
        raise RuntimeError(
            "Resultatet mangler en boolsk værdi "
            "i feltet 'updated'."
        )

    if kun_laes:
        if updated:
            raise RuntimeError(
                "Feltet blev opdateret, selv om "
                "kun_laes var True."
            )

        value = result.get(
            "value"
        )

        if not isinstance(value, str):
            raise RuntimeError(
                "Resultatet fra læsekaldet mangler "
                "en tekstværdi i feltet 'value'."
            )

        is_empty = result.get(
            "isEmpty"
        )

        if not isinstance(is_empty, bool):
            raise RuntimeError(
                "Resultatet fra læsekaldet mangler "
                "en boolsk værdi i feltet 'isEmpty'."
            )

        return result

    if tekst is None:
        raise RuntimeError(
            "Testen mangler tekst til opdatering."
        )

    new_value = result.get(
        "newValue"
    )

    if not isinstance(new_value, str):
        raise RuntimeError(
            "Resultatet fra skrivekaldet mangler "
            "en tekstværdi i feltet 'newValue'."
        )

    if new_value != tekst.strip():
        raise RuntimeError(
            "Den returnerede newValue matcher ikke "
            "den ønskede testværdi. "
            f"Forventede {tekst.strip()!r}, "
            f"men modtog {new_value!r}."
        )

    is_deleted = result.get(
        "isDeleted"
    )

    if is_deleted is not None:
        if not isinstance(is_deleted, bool):
            raise RuntimeError(
                "Feltet 'isDeleted' skal være "
                "True eller False."
            )

        expected_is_deleted = (
            tekst.strip() == ""
        )

        if is_deleted != expected_is_deleted:
            raise RuntimeError(
                "Feltet 'isDeleted' matcher ikke "
                "den udførte handling."
            )

    return result


def _print_result_summary(
    result: dict[str, Any],
    kun_laes: bool,
    tekst: str | None,
) -> None:
    """
    Udskriver en kort status for testen.
    """
    print()

    if kun_laes:
        print(
            "importantNote2 blev læst."
        )
        print(
            "Værdi: "
            f"{result.get('value')!r}"
        )
        print(
            "Feltet er tomt: "
            f"{result.get('isEmpty')}"
        )
        print(
            "Der blev ikke foretaget nogen ændring."
        )
        return

    if tekst == "":
        operation = "sletning"
    else:
        operation = "opdatering"

    if result["updated"]:
        print(
            f"importantNote2 blev ændret ved {operation}."
        )
        print(
            "Tidligere værdi: "
            f"{result.get('previousValue')!r}"
        )
        print(
            "Ny værdi: "
            f"{result.get('newValue')!r}"
        )

        if tekst == "":
            print(
                "Feltet er nu ryddet."
            )

        return

    print(
        "importantNote2 blev ikke ændret."
    )
    print(
        "Eksisterende værdi: "
        f"{result.get('previousValue')!r}"
    )
    print(
        "Ønsket værdi: "
        f"{result.get('newValue')!r}"
    )

    reason = result.get(
        "reason"
    )

    if reason:
        print(
            "Årsag: "
            f"{reason}"
        )


async def main() -> None:
    """
    Tester opret_kommunens_markeringer.

    Testen understøtter:

    1. Læsning:
       KUN_LAES = True

    2. Skrivning eller overskrivning:
       KUN_LAES = False
       TEST_TEKST = "test123"

    3. Sletning:
       KUN_LAES = False
       TEST_TEKST = ""

    FASIT launches automatisk ved det første API-kald
    gennem FasitTokenManager.
    """
    load_dotenv()

    headless = _get_headless_setting()
    kun_laes = _get_kun_laes_setting()

    citizen_id = os.getenv(
        "TEST_CITIZEN_ID",
        DEFAULT_TEST_CITIZEN_ID,
    ).strip()

    if not citizen_id:
        raise RuntimeError(
            "TEST_CITIZEN_ID må ikke være tom."
        )

    tekst = _get_test_tekst()

    if kun_laes:
        tekst_til_funktion: str | None = None
    else:
        tekst_til_funktion = tekst

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
            "opret_kommunens_markeringer..."
        )

        if kun_laes:
            print(
                "Tilstand: Kun læsning."
            )
        elif tekst == "":
            print(
                "Tilstand: Sletning."
            )
            print(
                "importantNote2 bliver ryddet."
            )
        else:
            print(
                "Tilstand: Skrivning/overskrivning."
            )
            print(
                "Ny værdi: "
                f"{tekst!r}"
            )

        result = await opret_kommunens_markeringer(
            api_client=api_client,
            citizen_id=citizen_id,
            tekst=tekst_til_funktion,
            kun_laes=kun_laes,
        )

        validated_result = _validate_result(
            result=result,
            kun_laes=kun_laes,
            tekst=tekst_til_funktion,
        )

        _print_result_summary(
            result=validated_result,
            kun_laes=kun_laes,
            tekst=tekst_til_funktion,
        )

        print()
        print("Teknisk resultat:")
        print(
            json.dumps(
                validated_result,
                indent=2,
                ensure_ascii=False,
                default=str,
            )
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