"""Integrationstest af oprettelse og efterkontrol af borgeropgave.

Testen:

1. Indlæser testdata fra .env.
2. Finder borgerens citizenId via CPR.
3. Opretter en reel opgave på borgeren.
4. Lader opret_borgeropgave vente og kontrollere opgaven.
5. Modtager den bekræftede opgave fra funktionen.
6. Udskriver testresultatet.

Vigtigt:
Testen udfører en reel skrivehandling i FASIT.
Hver kørsel kan oprette en ny opgave.
"""

import asyncio
import json
import os
from datetime import date, datetime
from typing import Any

from dotenv import load_dotenv

from q_fasit.api.borger import (
    hent_borger_id,
    opret_borgeropgave,
)
from q_fasit.api.client import FasitApiClient
from q_fasit.api.token_manager import FasitTokenManager


DEFAULT_TASK_TITLE = (
    "TEST - Vurdering ift. afklaringsretten"
)
DEFAULT_TASK_DESCRIPTION = ""
DEFAULT_TASK_STATUS = "Planlagt"
DEFAULT_CASE_TYPE = "Kontanthjælp"
DEFAULT_VERIFICATION_DELAY_SECONDS = 1.0


def _get_headless_setting() -> bool:
    """Læser FASIT_HEADLESS fra miljøvariabler."""
    return os.getenv(
        "FASIT_HEADLESS",
        "false",
    ).strip().casefold() in {
        "1",
        "true",
        "yes",
        "ja",
    }


def _get_required_environment_value(
    name: str,
) -> str:
    """Henter og validerer en påkrævet miljøvariabel."""
    value = os.getenv(
        name,
        "",
    ).strip()

    if not value:
        raise RuntimeError(
            f"Miljøvariablen {name} mangler eller er tom."
        )

    return value


def _get_optional_environment_value(
    name: str,
    default: str,
) -> str:
    """Henter en valgfri miljøvariabel."""
    value = os.getenv(
        name,
        default,
    ).strip()

    if not value:
        return default

    return value


def _get_optional_float_environment_value(
    name: str,
    default: float,
) -> float:
    """Henter en valgfri miljøvariabel som decimaltal."""
    value = os.getenv(
        name,
        "",
    ).strip()

    if not value:
        return default

    try:
        parsed_value = float(
            value.replace(
                ",",
                ".",
            )
        )

    except ValueError as error:
        raise RuntimeError(
            f"Miljøvariablen {name} skal være et tal."
        ) from error

    if parsed_value < 0:
        raise RuntimeError(
            f"Miljøvariablen {name} må ikke være negativ."
        )

    return parsed_value


def _create_unique_test_title(
    base_title: str,
) -> str:
    """Opretter en unik titel til testopgaven."""
    timestamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )

    return (
        f"{base_title} - "
        f"{timestamp}"
    )


def _get_test_due_date() -> str:
    """Returnerer testens forfaldsdato.

    Datoen kan angives via TEST_TASK_DUE_DATE i .env.

    Hvis værdien ikke er angivet, anvendes dags dato.
    """
    configured_due_date = os.getenv(
        "TEST_TASK_DUE_DATE",
        "",
    ).strip()

    if configured_due_date:
        return configured_due_date

    return date.today().isoformat()


def _validate_verified_task(
    value: Any,
) -> dict[str, Any]:
    """Validerer den opgave, oprettelsesfunktionen returnerer."""
    if not isinstance(value, dict):
        raise RuntimeError(
            "opret_borgeropgave returnerede ikke "
            "en dictionary."
        )

    required_fields = (
        "id",
        "title",
        "dueDate",
        "taskStatus",
        "caseType",
    )

    missing_fields = [
        field_name
        for field_name in required_fields
        if value.get(field_name) in (None, "")
    ]

    if missing_fields:
        raise RuntimeError(
            "Den bekræftede opgave mangler følgende felter: "
            + ", ".join(missing_fields)
        )

    return value


def _print_json_result(
    heading: str,
    result: dict[str, Any],
) -> None:
    """Udskriver et resultat som formateret JSON."""
    print()
    print("=" * 80)
    print(heading)
    print("=" * 80)

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
    )

    print("=" * 80)


async def main() -> None:
    """Opretter og efterkontrollerer en borgeropgave."""
    load_dotenv()

    test_cpr = _get_required_environment_value(
        "test_cpr"
    )

    category_id = _get_required_environment_value(
        "TEST_TASK_CATEGORY_ID"
    )

    case_id = _get_required_environment_value(
        "TEST_TASK_CASE_ID"
    )

    responsible_case_worker_id = (
        _get_required_environment_value(
            "TEST_TASK_RESPONSIBLE_CASE_WORKER_ID"
        )
    )

    responsible_team_id = (
        _get_required_environment_value(
            "TEST_TASK_RESPONSIBLE_TEAM_ID"
        )
    )

    base_title = _get_optional_environment_value(
        "TEST_TASK_TITLE",
        DEFAULT_TASK_TITLE,
    )

    description = _get_optional_environment_value(
        "TEST_TASK_DESCRIPTION",
        DEFAULT_TASK_DESCRIPTION,
    )

    expected_task_status = (
        _get_optional_environment_value(
            "TEST_TASK_EXPECTED_STATUS",
            DEFAULT_TASK_STATUS,
        )
    )

    expected_case_type = (
        _get_optional_environment_value(
            "TEST_TASK_EXPECTED_CASE_TYPE",
            DEFAULT_CASE_TYPE,
        )
    )

    verification_delay_seconds = (
        _get_optional_float_environment_value(
            "TEST_TASK_VERIFICATION_DELAY_SECONDS",
            DEFAULT_VERIFICATION_DELAY_SECONDS,
        )
    )

    credential_name = (
        _get_optional_environment_value(
            "FASIT_CREDENTIAL_NAME",
            "DIRXOPS",
        )
    )

    headless = _get_headless_setting()

    test_title = _create_unique_test_title(
        base_title
    )

    test_due_date = _get_test_due_date()

    print()
    print("=" * 80)
    print("TEST AF OPRETTELSE OG EFTERKONTROL AF BORGEROPGAVE")
    print("=" * 80)
    print(f"Titel: {test_title}")
    print(f"Forfaldsdato: {test_due_date}")
    print(f"Forventet status: {expected_task_status}")
    print(f"Forventet sagstype: {expected_case_type}")
    print(
        "Ventetid før kontrol: "
        f"{verification_delay_seconds} sekund(er)"
    )
    print("=" * 80)

    token_manager = FasitTokenManager(
        credential_name=credential_name,
        headless=headless,
        fallback_lifetime_seconds=15 * 60,
        expiry_margin_seconds=60,
    )

    api_client = FasitApiClient(
        token_manager=token_manager,
    )

    try:
        print()
        print(
            "1. Søger efter testborgeren i FASIT."
        )

        citizen_id = await hent_borger_id(
            api_client=api_client,
            cpr=test_cpr,
            opret_borger_hvis_ikke_findes=False,
        )

        print(
            "2. Borgeren blev fundet."
        )

        print(
            "3. Opretter og efterkontrollerer borgeropgaven."
        )

        verified_task = await opret_borgeropgave(
            api_client=api_client,
            citizen_id=citizen_id,
            forfaldsdato=test_due_date,
            titel=test_title,
            beskrivelse=description,
            category_id=category_id,
            case_id=case_id,
            responsible_case_worker_id=(
                responsible_case_worker_id
            ),
            responsible_team_id=(
                responsible_team_id
            ),
            case_type=expected_case_type,
            task_status=expected_task_status,
            ventetid_sekunder=(
                verification_delay_seconds
            ),
        )

        validated_task = _validate_verified_task(
            verified_task
        )

        print(
            "4. Opgaven blev oprettet og bekræftet."
        )

        _print_json_result(
            heading="BEKRÆFTET BORGEROPGAVE",
            result=validated_task,
        )

        task_id = validated_task.get(
            "id"
        )

        actual_title = validated_task.get(
            "title"
        )

        actual_due_date = validated_task.get(
            "dueDate"
        )

        actual_task_status = validated_task.get(
            "taskStatus"
        )

        actual_case_type = validated_task.get(
            "caseType"
        )

        actual_case_id = validated_task.get(
            "caseId"
        )

        actual_task_category = validated_task.get(
            "taskCategory"
        )

        print()
        print("=" * 80)
        print("TESTRESULTAT")
        print("=" * 80)
        print("Resultat: GODKENDT")
        print(f"Opgave-id: {task_id}")
        print(f"Titel: {actual_title}")
        print(f"Forfaldsdato: {actual_due_date}")
        print(f"Status: {actual_task_status}")
        print(f"Sagstype: {actual_case_type}")
        print(f"Sags-id: {actual_case_id}")
        print(f"Opgavekategori: {actual_task_category}")
        print()
        print(
            "Opgaven blev oprettet og bekræftet via "
            "hent_borgeropgaver_metadata."
        )
        print("=" * 80)

    except Exception as error:
        print()
        print("=" * 80)
        print("TESTRESULTAT")
        print("=" * 80)
        print("Resultat: FEJL")
        print(
            f"Fejltype: {type(error).__name__}"
        )
        print(
            f"Fejltekst: {error}"
        )
        print()
        print(
            "Bemærk: Opgaven kan være blevet oprettet, "
            "selv om efterkontrollen fejlede."
        )
        print(
            "Kontrollér borgerens opgaveliste, før testen "
            "køres igen."
        )
        print("=" * 80)

        if not headless:
            print()
            print(
                "Tryk Enter, når browseren og testen må lukkes."
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