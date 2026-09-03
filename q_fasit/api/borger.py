from typing import Any
from uuid import UUID

from q_fasit.api.client import FasitApiClient
from q_fasit.utils import normalize_cpr


BORGER_SEARCH_ENDPOINT = (
    "/api/search/queries/rankedsearchquery"
)

BORGER_INFORMATION_ENDPOINT = (
    "/api/citizen/queries/"
    "getauthoritycitizencontext"
)

BORGER_ADRESSEHISTORIK_ENDPOINT = (
    "/api/citizen/citizenmasterdata/citizencore/queries/"
    "getcitizenaddresshistory"
)

BORGEROVERBLIK_BESKAEFTIGELSE_ENDPOINT = (
    "/api/citizen/citizenoverview/queries/"
    "getcitizenoverviewdataforbeskaeftigelse"
)

CITIZEN_TASKS_METADATA_ENDPOINT = (
    "/api/citizen/citizentask/queries/"
    "getcitizentasksmetadata"
)

JOURNAL_OG_DOKUMENTER_ENDPOINT = (
    "/api/citizen/journal/queries/"
    "getjournalnotesforcitizenid"
)

FORSOERGELSES_HISTORIK_ENDPOINT = (
    "/api/citizen/citizenmasterdata/"
    "sustenancehistory/queries/"
    "getsustenancehistoryyear"
)

SAGER_ENDPOINT = (
    "/api/citizen/case/queries/getcases"
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
    """
    normalized_cpr = normalize_cpr(cpr)

    payload = {
        "universe": "citizen",
        "queryString": normalized_cpr,
        "documentTypes": ["citizen"],
        "page": 0,
        "selectedFilters": [],
    }

    result = await api_client.post(
        endpoint=BORGER_SEARCH_ENDPOINT,
        json_body=payload,
    )

    return _validate_response(
        result=result,
        response_name="BORGER_SEARCH",
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


def _validate_citizen_id(
    citizen_id: str,
) -> str:
    """
    Validerer og normaliserer et citizenId.

    Parametre:
    - citizen_id: Borgerens FASIT-id.

    Output:
    Et citizenId i standardiseret UUID-format.

    Funktionen kaster ValueError, hvis værdien:
    - ikke er tekst,
    - er tom,
    - ikke har et gyldigt UUID-format.
    """
    if not isinstance(citizen_id, str):
        raise ValueError(
            "citizen_id skal være en tekstværdi."
        )

    normalized_citizen_id = citizen_id.strip()

    if not normalized_citizen_id:
        raise ValueError(
            "citizen_id må ikke være tom."
        )

    try:
        parsed_citizen_id = UUID(
            normalized_citizen_id
        )
    except ValueError as error:
        raise ValueError(
            "citizen_id havde ikke et gyldigt "
            "UUID-format."
        ) from error

    return str(parsed_citizen_id)


def _validate_response(
    result: Any,
    response_name: str,
) -> dict[str, Any]:
    """
    Kontrollerer, at et API-response er en dictionary.

    Parametre:
    - result: API-responsen, som skal valideres.
    - response_name: Navnet på API-kaldet til fejlbeskeden.

    Output:
    Det validerede API-response.
    """
    if not isinstance(result, dict):
        raise RuntimeError(
            f"{response_name} havde et uventet "
            "responseformat. Forventede en dictionary, "
            f"men modtog {type(result).__name__}."
        )

    return result


async def hent_borgeroverblik_beskaeftigelse(
    api_client: FasitApiClient,
    citizen_id: str,
) -> dict[str, Any]:
    """
    Henter borgeroverbliksdata for beskæftigelse.

    Parametre:
    - api_client: Den fælles FasitApiClient for processen.
    - citizen_id: Borgerens FASIT-id fra hent_borger_id().

    Output:
    Hele FASITs response som en dictionary.
    """
    validated_citizen_id = _validate_citizen_id(
        citizen_id
    )

    payload = {
        "citizenId": validated_citizen_id,
    }

    result = await api_client.post(
        endpoint=BORGEROVERBLIK_BESKAEFTIGELSE_ENDPOINT,
        json_body=payload,
    )

    return _validate_response(
        result=result,
        response_name="BORGEROVERBLIK_BESKAEFTIGELSE",
    )


async def hent_borgeropgaver_metadata(
    api_client: FasitApiClient,
    citizen_id: str,
) -> dict[str, Any]:
    """
    Henter metadata for alle borgerens opgaver.

    Parametre:
    - api_client: Den fælles FasitApiClient for processen.
    - citizen_id: Borgerens FASIT-id fra hent_borger_id().

    Output:
    Hele FASITs response som en dictionary.

    Filteret allTasks sættes til True, så metadata
    omfatter alle borgerens opgaver.
    """
    validated_citizen_id = _validate_citizen_id(
        citizen_id
    )

    payload = {
        "citizenId": validated_citizen_id,
        "filter": {
            "allTasks": True,
        },
    }

    result = await api_client.post(
        endpoint=CITIZEN_TASKS_METADATA_ENDPOINT,
        json_body=payload,
    )

    return _validate_response(
        result=result,
        response_name="CITIZEN_TASKS_METADATA",
    )


async def JOURNAL_OG_DOKUMENTER(
    api_client: FasitApiClient,
    citizen_id: str,
) -> dict[str, Any]:
    """
    Henter borgerens aktive journalnotater og dokumenter.

    Parametre:
    - api_client: Den fælles FasitApiClient for processen.
    - citizen_id: Borgerens FASIT-id fra hent_borger_id().

    Output:
    Hele FASITs response som en dictionary.

    Kaldet:
    - medtager kun aktive journalposter,
    - anvender ingen øvrige filtre,
    - henter op til 10.000 poster,
    - sorterer efter hændelsesdato faldende.
    """
    validated_citizen_id = _validate_citizen_id(
        citizen_id
    )

    payload = {
        "citizenId": validated_citizen_id,
        "filterRequest": {
            "filterStatus": "onlyActive",
            "contentTypes": [],
            "cases": [],
            "assignments": [],
            "createdBy": [],
            "sources": [],
            "hasAttachments": [],
        },
        "pageRequest": {
            "pageNumber": 0,
            "pageSize": 10000,
        },
        "sortRequest": {
            "sortBy": "eventDate",
            "sortOrder": "descending",
        },
    }

    result = await api_client.post(
        endpoint=JOURNAL_OG_DOKUMENTER_ENDPOINT,
        json_body=payload,
    )

    return _validate_response(
        result=result,
        response_name="JOURNAL_OG_DOKUMENTER",
    )


async def FORSOERGELSES_HISTORIK(
    api_client: FasitApiClient,
    citizen_id: str,
) -> dict[str, Any]:
    """
    Henter borgerens forsørgelseshistorik.

    Parametre:
    - api_client: Den fælles FasitApiClient for processen.
    - citizen_id: Borgerens FASIT-id fra hent_borger_id().

    Output:
    Hele FASITs response som en dictionary.
    """
    validated_citizen_id = _validate_citizen_id(
        citizen_id
    )

    payload = {
        "citizenId": validated_citizen_id,
    }

    result = await api_client.post(
        endpoint=FORSOERGELSES_HISTORIK_ENDPOINT,
        json_body=payload,
    )

    return _validate_response(
        result=result,
        response_name="FORSOERGELSES_HISTORIK",
    )


async def SAGER(
    api_client: FasitApiClient,
    citizen_id: str,
) -> dict[str, Any]:
    """
    Henter borgerens sager.

    Parametre:
    - api_client: Den fælles FasitApiClient for processen.
    - citizen_id: Borgerens FASIT-id fra hent_borger_id().

    Output:
    Hele FASITs response som en dictionary.
    """
    validated_citizen_id = _validate_citizen_id(
        citizen_id
    )

    payload = {
        "citizenId": validated_citizen_id,
    }

    result = await api_client.post(
        endpoint=SAGER_ENDPOINT,
        json_body=payload,
    )

    return _validate_response(
        result=result,
        response_name="SAGER",
    )


async def BORGER_INFORMATION(
    api_client: FasitApiClient,
    citizen_id: str,
) -> dict[str, Any]:
    """
    Henter borgerens grundlæggende information
    og myndighedskontekst.

    Parametre:
    - api_client: Den fælles FasitApiClient for processen.
    - citizen_id: Borgerens FASIT-id fra hent_borger_id().

    Output:
    Hele FASITs response som en dictionary.
    """
    validated_citizen_id = _validate_citizen_id(
        citizen_id
    )

    payload = {
        "citizenId": validated_citizen_id,
    }

    result = await api_client.post(
        endpoint=BORGER_INFORMATION_ENDPOINT,
        json_body=payload,
    )

    return _validate_response(
        result=result,
        response_name="BORGER_INFORMATION",
    )


async def hent_borger_adressehistorik(
    api_client: FasitApiClient,
    citizen_id: str,
) -> dict[str, Any]:
    """
    Henter borgerens adressehistorik.

    Parametre:
    - api_client: Den fælles FasitApiClient for processen.
    - citizen_id: Borgerens FASIT-id fra hent_borger_id().

    Output:
    Hele FASITs response som en dictionary.
    """
    validated_citizen_id = _validate_citizen_id(
        citizen_id
    )

    payload = {
        "citizenId": validated_citizen_id,
    }

    result = await api_client.post(
        endpoint=BORGER_ADRESSEHISTORIK_ENDPOINT,
        json_body=payload,
    )

    return _validate_response(
        result=result,
        response_name="BORGER_ADRESSEHISTORIK",
    )