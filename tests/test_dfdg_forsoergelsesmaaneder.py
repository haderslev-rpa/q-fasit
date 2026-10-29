"""Tester sammenhængende måneder med kontanthjælp.

Testen:

1. Læser CPR-nummeret fra .env.
2. Søger efter borgeren i FASIT.
3. Henter og opretter borgeren via DFDG, hvis borgeren
   ikke allerede findes i FASIT.
4. Henter borgerens forsørgelseshistorik.
5. Tæller sammenhængende måneder bagud fra den aktuelle måned,
   hvor kategorien indeholder KTH, ATK-KTH eller kontanthjælp.

Det eneste normale konsoloutput er:

Antal måneder: <antal>
"""

import asyncio
import contextlib
import io
import logging
import os
from datetime import date
from typing import Any, Iterator

from dotenv import load_dotenv

from q_fasit.api.borger import (
    FORSOERGELSES_HISTORIK,
    hent_borger_id,
)
from q_fasit.api.client import FasitApiClient
from q_fasit.api.token_manager import FasitTokenManager


FORSOERGELSESKATEGORIER = frozenset(
    {
        "kth",
        "atk-kth",
        "kontanthjælp",
    }
)


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


def _walk(
    value: Any,
) -> Iterator[Any]:
    """Gennemløber dictionaries og lister rekursivt."""
    yield value

    if isinstance(value, dict):
        for child in value.values():
            yield from _walk(
                child
            )

    elif isinstance(value, list):
        for child in value:
            yield from _walk(
                child
            )


def _month_number(
    year: int,
    month: int,
) -> int:
    """Konverterer år og måned til et fortløbende månedsnummer."""
    return year * 12 + month


def _normalize_category(
    category: str,
) -> str:
    """Normaliserer en forsørgelseskategori."""
    return " ".join(
        category.split()
    ).casefold()


def _is_relevant_category(
    category: str,
) -> bool:
    """Kontrollerer om kategorien er KTH, ATK-KTH eller kontanthjælp."""
    normalized_category = _normalize_category(
        category
    )

    return any(
        search_value in normalized_category
        for search_value in FORSOERGELSESKATEGORIER
    )


def _has_relevant_category(
    categories: Any,
) -> bool:
    """Kontrollerer om kategorierne indeholder en relevant ydelse."""
    if isinstance(categories, str):
        categories = [
            categories
        ]

    if not isinstance(categories, list):
        return False

    return any(
        isinstance(category, str)
        and _is_relevant_category(category)
        for category in categories
    )


def _get_relevant_months(
    result: dict[str, Any],
) -> set[int]:
    """Finder unikke måneder med en relevant forsørgelseskategori."""
    relevant_months: set[int] = set()

    for value in _walk(
        result
    ):
        if not isinstance(value, dict):
            continue

        year = value.get(
            "year"
        )
        month = value.get(
            "month"
        )
        categories = value.get(
            "sustenanceHistoryCategoryName",
            [],
        )

        if (
            not isinstance(year, int)
            or isinstance(year, bool)
            or not isinstance(month, int)
            or isinstance(month, bool)
            or not 1 <= month <= 12
        ):
            continue

        if not _has_relevant_category(
            categories
        ):
            continue

        relevant_months.add(
            _month_number(
                year=year,
                month=month,
            )
        )

    return relevant_months


def _count_consecutive_months_backwards(
    relevant_months: set[int],
    current_date: date,
) -> int:
    """Tæller sammenhængende måneder bagud fra aktuel måned.

    Den aktuelle kalendermåned undersøges først.

    Optællingen fortsætter bagud én måned ad gangen og stopper
    ved den første måned, der ikke indeholder KTH, ATK-KTH
    eller kontanthjælp.
    """
    current_month = _month_number(
        year=current_date.year,
        month=current_date.month,
    )

    number_of_months = 0
    month_to_check = current_month

    while month_to_check in relevant_months:
        number_of_months += 1
        month_to_check -= 1

    return number_of_months


async def _run_test() -> int:
    """Kører testen og returnerer antal sammenhængende måneder."""
    load_dotenv()

    test_cpr = os.getenv(
        "test_cpr",
        "",
    ).strip()

    if not test_cpr:
        raise RuntimeError(
            "Variablen test_cpr mangler i .env-filen."
        )

    credential_name = os.getenv(
        "FASIT_CREDENTIAL_NAME",
        "DIRXOPS",
    ).strip()

    if not credential_name:
        raise RuntimeError(
            "FASIT_CREDENTIAL_NAME må ikke være tom."
        )

    token_manager = FasitTokenManager(
        credential_name=credential_name,
        headless=_get_headless_setting(),
        fallback_lifetime_seconds=15 * 60,
        expiry_margin_seconds=60,
    )

    api_client = FasitApiClient(
        token_manager=token_manager,
    )

    try:
        citizen_id = await hent_borger_id(
            api_client=api_client,
            cpr=test_cpr,
            opret_borger_hvis_ikke_findes=True,
        )

        result = await FORSOERGELSES_HISTORIK(
            api_client=api_client,
            citizen_id=citizen_id,
        )

        if not isinstance(result, dict):
            raise RuntimeError(
                "FORSOERGELSES_HISTORIK returnerede "
                "ikke en dictionary."
            )

        relevant_months = _get_relevant_months(
            result
        )

        return _count_consecutive_months_backwards(
            relevant_months=relevant_months,
            current_date=date.today(),
        )

    finally:
        await api_client.close()
        await token_manager.close()


async def main() -> None:
    """Kører testen og viser kun antallet af måneder."""
    logging.disable(
        logging.CRITICAL
    )

    internal_output = io.StringIO()

    with (
        contextlib.redirect_stdout(
            internal_output
        ),
        contextlib.redirect_stderr(
            internal_output
        ),
    ):
        number_of_months = await _run_test()

    print(
        f"Antal måneder: {number_of_months}"
    )


if __name__ == "__main__":
    asyncio.run(
        main()
    )