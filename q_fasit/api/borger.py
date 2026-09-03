from typing import Any

from q_fasit.api.client import FasitApiClient
from q_fasit.utils import normalize_cpr


BORGER_SEARCH_ENDPOINT = (
    "/api/search/queries/rankedsearchquery"
)


async def search_citizen(
    api_client: FasitApiClient,
    cpr: str,
) -> dict[str, Any]:
    """
    Søger efter en borger i FASIT via CPR-nummer.

    Parametre:
    - api_client: Den fælles FasitApiClient for processen.
    - cpr: CPR-nummer med eller uden bindestreg.

    Output:
    Hele FASITs søgeresultat som en dictionary.

    Eksempel:

    {
        "rankedSearchResult": [
            {
                "title": "...",
                "description": "",
                "documentId": "...",
                "documentType": "citizen"
            }
        ],
        "totalHits": 1,
        "hasMoreResults": False
    }
    """
    normalized_cpr = normalize_cpr(cpr)

    payload = {
        "universe": "citizen",
        "queryString": normalized_cpr,
        "documentTypes": ["citizen"],
        "page": 0,
        "selectedFilters": [],
    }

    return await api_client.post(
        endpoint=BORGER_SEARCH_ENDPOINT,
        json_body=payload,
    )


async def hent_borger_id(
    api_client: FasitApiClient,
    cpr: str,
) -> str:
    """
    Søger efter en borger og returnerer borgerens documentId.

    Parametre:
    - api_client: Den fælles FasitApiClient for processen.
    - cpr: CPR-nummer med eller uden bindestreg.

    Output:
    Borgerens FASIT-id som tekst.

    Eksempel:

    "9714f3f2-75ac-4fc6-a936-15d5f3cc3f51"

    Funktionen kaster RuntimeError, hvis:

    - ingen borger bliver fundet,
    - flere borgere bliver fundet,
    - resultatet ikke har documentId.
    """
    search_result = await search_citizen(
        api_client=api_client,
        cpr=cpr,
    )

    ranked_results = search_result.get(
        "rankedSearchResult",
        [],
    )

    if not isinstance(ranked_results, list):
        raise RuntimeError(
            "FASITs rankedSearchResult havde et "
            "uventet format."
        )

    citizen_results = [
        result
        for result in ranked_results
        if (
            isinstance(result, dict)
            and result.get("documentType") == "citizen"
        )
    ]

    if not citizen_results:
        raise RuntimeError(
            "Der blev ikke fundet en borger med det "
            "angivne CPR-nummer."
        )

    if len(citizen_results) > 1:
        raise RuntimeError(
            "FASIT returnerede flere borgere for det "
            "angivne CPR-nummer."
        )

    borger_id = citizen_results[0].get(
        "documentId"
    )

    if (
        not isinstance(borger_id, str)
        or not borger_id.strip()
    ):
        raise RuntimeError(
            "Borgeren blev fundet, men resultatet "
            "manglede documentId."
        )

    return borger_id.strip()