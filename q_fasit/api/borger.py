from datetime import date, datetime, time
import json
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from q_fasit.api.client import FasitApiClient
from q_fasit.utils import normalize_cpr


# ---------------------------------------------------------------------------
# Borgeropslag og borgerdata
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Forskellige udtræk
# ---------------------------------------------------------------------------

LISTE_SEARCH_ENDPOINT = (
    "/api/search"
)

LISTE_OPLYSNINGSSKEMAER = (
    "LISTE_OPLYSNINGSSKEMAER"
)

OPLYSNINGSSKEMA_TARGET_GROUP_ID = (
    "aa5c6a8e-1b27-e111-9ada-005056a823a6"
)


# ---------------------------------------------------------------------------
# Persongrupper
# ---------------------------------------------------------------------------

PERSONGRUPPE_ENDPOINT = (
    "/api/citizen/citizenmasterdata/persongroup/queries/"
    "getpersongroups"
)

PERSONGRUPPEMARKERINGER_ENDPOINT = (
    "/api/citizen/citizenmasterdata/persongroup/queries/"
    "getpersongroupmarkingsforcitizen"
)

OPRET_PERSONGRUPPEMARKERING_ENDPOINT = (
    "/api/citizen/citizenmasterdata/persongroup/queries/"
    "createpersongroupmarking"
)


# ---------------------------------------------------------------------------
# Kommunens markeringer
# ---------------------------------------------------------------------------

KOMMUNENS_MARKERINGER_NOTER_ENDPOINT = (
    "/api/citizen/citizenmasterdata/citizencore/queries/"
    "getnotesforcitizen"
)

OPDATER_KOMMUNENS_MARKERINGER_ENDPOINT = (
    "/api/citizen/citizenmasterdata/citizencore/commands/"
    "updatenotes"
)


# ---------------------------------------------------------------------------
# Typer
# ---------------------------------------------------------------------------

DatoType = str | date | datetime


# ---------------------------------------------------------------------------
# Generelle hjælpefunktioner
# ---------------------------------------------------------------------------

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


def _validate_target_group_id(
    target_group_id: str,
) -> str:
    """
    Validerer og normaliserer et target group-id.

    Output:
    Target group-id'et i standardiseret UUID-format.
    """
    if not isinstance(target_group_id, str):
        raise ValueError(
            "target_group_id skal være en tekstværdi."
        )

    normalized_target_group_id = (
        target_group_id.strip()
    )

    if not normalized_target_group_id:
        raise ValueError(
            "target_group_id må ikke være tom."
        )

    try:
        parsed_target_group_id = UUID(
            normalized_target_group_id
        )
    except ValueError as error:
        raise ValueError(
            "target_group_id havde ikke et "
            "gyldigt UUID-format."
        ) from error

    return str(parsed_target_group_id)


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


# ---------------------------------------------------------------------------
# Hjælpefunktioner til oplysningsskemaer
# ---------------------------------------------------------------------------

def _find_search_result_list(
    value: Any,
) -> list[Any] | None:
    """
    Finder den relevante resultatliste rekursivt
    i FASITs searchResult.

    Tomme lister ignoreres først, fordi searchResult
    kan indeholde tomme metadata- og filterlister.
    """
    if isinstance(value, list):
        if value:
            return value

        return None

    if not isinstance(value, dict):
        return None

    preferred_keys = (
        "rows",
        "results",
        "items",
        "documents",
        "records",
        "hits",
        "cases",
        "data",
        "values",
        "searchResults",
        "result",
    )

    for key in preferred_keys:
        candidate = value.get(key)

        if (
            isinstance(candidate, list)
            and candidate
        ):
            return candidate

    for key in preferred_keys:
        candidate = value.get(key)

        if isinstance(candidate, dict):
            nested_result = _find_search_result_list(
                candidate
            )

            if nested_result is not None:
                return nested_result

    largest_list: list[Any] | None = None

    for candidate in value.values():
        if isinstance(candidate, list):
            if (
                candidate
                and (
                    largest_list is None
                    or len(candidate) > len(largest_list)
                )
            ):
                largest_list = candidate

        elif isinstance(candidate, dict):
            nested_result = _find_search_result_list(
                candidate
            )

            if (
                nested_result is not None
                and (
                    largest_list is None
                    or len(nested_result)
                    > len(largest_list)
                )
            ):
                largest_list = nested_result

    return largest_list


def _find_search_total(
    value: Any,
) -> int | None:
    """
    Finder FASITs oplyste samlede antal rekursivt.
    """
    if not isinstance(value, dict):
        return None

    total_keys = (
        "totalHits",
        "totalCount",
        "totalResults",
        "numberOfResults",
        "totalNumberOfResults",
        "rowCount",
        "recordCount",
        "hitsCount",
    )

    for key in total_keys:
        candidate = value.get(key)

        if (
            isinstance(candidate, int)
            and not isinstance(candidate, bool)
            and candidate >= 0
        ):
            return candidate

    for candidate in value.values():
        if isinstance(candidate, dict):
            nested_total = _find_search_total(
                candidate
            )

            if nested_total is not None:
                return nested_total

    return None


def _create_oplysningsskema_payload(
    *,
    created_after: str,
    target_group_id: str,
    case_statuses: list[str],
    page_number: int,
    page_size: int,
) -> dict[str, Any]:
    """
    Opretter den dokumenterede payload til
    listen over oplysningsskemaer.
    """
    return {
        "body": {
            "universe": "citizen",
            "usePreviewVersion": False,
            "queryType": "fasitDsl",
            "query": {
                "condition": "and",
                "rules": [
                    {
                        "rules": [
                            {
                                "field": (
                                    "Cases.CaseStatus"
                                ),
                                "operator": "in",
                                "value": case_statuses,
                            },
                            {
                                "field": (
                                    "Cases.TargetGroup"
                                ),
                                "operator": "eq",
                                "value": [
                                    target_group_id
                                ],
                            },
                            {
                                "field": (
                                    "Cases.CreatedOn"
                                ),
                                "operator": "gt",
                                "value": created_after,
                            },
                        ],
                        "condition": "and",
                        "cardinality": "any",
                        "type": "Cases",
                    }
                ],
            },
            "dslVersion": "1.0.0",
            "resultType": "Cases",
            "columns": [
                {
                    "name": "CitizenCprFormatted",
                },
                {
                    "name": "Cases.CreatedOn",
                },
            ],
            "sortColumns": [
                {
                    "desc": False,
                    "name": "CitizenFullName",
                }
            ],
            "columnFilters": [],
            "embeddedSortColumns": [],
        },
        "pageNumber": page_number,
        "pageSize": page_size,
        "embeddedPageNumber": 0,
        "embeddedPageSize": 100,
    }


# ---------------------------------------------------------------------------
# Hjælpefunktioner til persongrupper
# ---------------------------------------------------------------------------

def _normaliser_persongruppenavn(
    navn: str,
) -> str:
    """
    Normaliserer et persongruppenavn til sammenligning.
    """
    if not isinstance(navn, str):
        raise ValueError(
            "persongruppenavn skal være en tekstværdi."
        )

    normaliseret_navn = " ".join(
        navn.split()
    ).casefold()

    if not normaliseret_navn:
        raise ValueError(
            "persongruppenavn må ikke være tomt."
        )

    return normaliseret_navn


def _parse_dansk_dato(
    dato: DatoType,
    feltnavn: str,
) -> date:
    """
    Konverterer en dato til et date-objekt.

    Understøttede tekstformater:
    - dd/mm/yyyy
    - dd-mm-yyyy
    - yyyy-mm-dd
    """
    if isinstance(dato, datetime):
        return dato.date()

    if isinstance(dato, date):
        return dato

    if not isinstance(dato, str):
        raise ValueError(
            f"{feltnavn} skal være tekst, date "
            "eller datetime."
        )

    normaliseret_dato = dato.strip()

    if not normaliseret_dato:
        raise ValueError(
            f"{feltnavn} må ikke være tom."
        )

    datoformater = (
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y-%m-%d",
    )

    for datoformat in datoformater:
        try:
            return datetime.strptime(
                normaliseret_dato,
                datoformat,
            ).date()
        except ValueError:
            continue

    raise ValueError(
        f"{feltnavn} havde et ugyldigt datoformat. "
        "Brug dd/mm/yyyy, dd-mm-yyyy eller yyyy-mm-dd."
    )


def _dato_til_fasit_utc(
    dato: DatoType,
    feltnavn: str,
) -> str:
    """
    Konverterer dansk lokal midnat til UTC-formatet,
    som FASIT anvender.

    Eksempel:
    04/09/2026 bliver 2026-09-03T22:00:00.000Z,
    fordi Danmark er UTC+2 den 4. september 2026.
    """
    parsed_dato = _parse_dansk_dato(
        dato=dato,
        feltnavn=feltnavn,
    )

    dansk_tidszone = ZoneInfo(
        "Europe/Copenhagen"
    )

    lokal_midnat = datetime.combine(
        parsed_dato,
        time.min,
        tzinfo=dansk_tidszone,
    )

    utc_tidspunkt = lokal_midnat.astimezone(
        ZoneInfo("UTC")
    )

    return (
        utc_tidspunkt.strftime(
            "%Y-%m-%dT%H:%M:%S"
        )
        + ".000Z"
    )


def _find_person_group_id(
    person_groups: list[Any],
    persongruppenavn: str,
) -> str:
    """
    Finder et aktivt personGroupId ud fra navnet.

    Navnet sammenlignes uden forskel på store og små
    bogstaver og med normaliserede mellemrum.
    """
    soegt_navn = _normaliser_persongruppenavn(
        persongruppenavn
    )

    navnematches: list[dict[str, Any]] = []

    for person_group in person_groups:
        if not isinstance(person_group, dict):
            continue

        navn = person_group.get(
            "name"
        )

        if not isinstance(navn, str):
            continue

        if (
            _normaliser_persongruppenavn(navn)
            == soegt_navn
        ):
            navnematches.append(
                person_group
            )

    if not navnematches:
        raise RuntimeError(
            "Der blev ikke fundet en persongruppe "
            f"med navnet '{persongruppenavn}'."
        )

    aktive_matches = [
        person_group
        for person_group in navnematches
        if person_group.get("isActive") is True
    ]

    if not aktive_matches:
        raise RuntimeError(
            "Persongruppen blev fundet, men ingen "
            "matchende persongruppe er aktiv. "
            f"Navn: '{persongruppenavn}'."
        )

    if len(aktive_matches) > 1:
        raise RuntimeError(
            "Der blev fundet flere aktive "
            "persongrupper med samme navn. "
            f"Navn: '{persongruppenavn}'."
        )

    person_group_id = aktive_matches[0].get(
        "id"
    )

    if (
        not isinstance(person_group_id, str)
        or not person_group_id.strip()
    ):
        raise RuntimeError(
            "Persongruppen blev fundet, men "
            "resultatet manglede feltet 'id'."
        )

    try:
        return str(
            UUID(person_group_id.strip())
        )
    except ValueError as error:
        raise RuntimeError(
            "Persongruppens id havde ikke et "
            "gyldigt UUID-format."
        ) from error


# ---------------------------------------------------------------------------
# Borgeropslag
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Borgerdata og overblik
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Oplysningsskemaer
# ---------------------------------------------------------------------------

async def hent_liste_oplysningsskemaer(
    api_client: FasitApiClient,
    *,
    created_after: str = "2025-06-16T22:00:00Z",
    target_group_id: str = OPLYSNINGSSKEMA_TARGET_GROUP_ID,
    case_statuses: list[str] | None = None,
    page_size: int = 250,
) -> dict[str, Any]:
    """
    Henter hele listen over oplysningsskemaer.

    Funktionen håndterer selv paginering ved at kalde
    FASIT med pageNumber 0, 1, 2 osv.

    Parametre:
    - api_client: Den fælles FasitApiClient.
    - created_after: Medtag sager oprettet efter tidspunktet.
    - target_group_id: Målgruppe-id for oplysningsskemaer.
    - case_statuses: Sagsstatusser, eksempelvis ["1", "3"].
    - page_size: Antal resultater pr. API-kald, maksimalt 250.

    Output:
    En dictionary med:
    - results: Alle rækker samlet i én liste.
    - totalResults: Antal hentede rækker.
    - reportedTotal: Det samlede antal oplyst af FASIT.
    - pageCount: Antal API-sidekald.
    - reportedPageCount: Antal sider oplyst af FASIT.
    """
    if not isinstance(created_after, str):
        raise ValueError(
            "created_after skal være en tekstværdi."
        )

    normalized_created_after = created_after.strip()

    if not normalized_created_after:
        raise ValueError(
            "created_after må ikke være tom."
        )

    validated_target_group_id = (
        _validate_target_group_id(
            target_group_id
        )
    )

    if case_statuses is None:
        normalized_case_statuses = [
            "1",
            "3",
        ]
    else:
        if not isinstance(case_statuses, list):
            raise ValueError(
                "case_statuses skal være en liste."
            )

        normalized_case_statuses = []

        for status in case_statuses:
            if not isinstance(status, str):
                raise ValueError(
                    "Alle værdier i case_statuses "
                    "skal være tekstværdier."
                )

            normalized_status = status.strip()

            if not normalized_status:
                raise ValueError(
                    "case_statuses må ikke indeholde "
                    "tomme værdier."
                )

            normalized_case_statuses.append(
                normalized_status
            )

    if not isinstance(page_size, int):
        raise ValueError(
            "page_size skal være et heltal."
        )

    if page_size < 1 or page_size > 250:
        raise ValueError(
            "page_size skal være mellem 1 og 250."
        )

    page_number = 0
    page_count = 0

    all_results: list[Any] = []

    reported_total: int | None = None
    reported_page_count: int | None = None

    while True:
        payload = {
            "body": {
                "universe": "citizen",
                "usePreviewVersion": False,
                "queryType": "fasitDsl",
                "query": {
                    "condition": "and",
                    "rules": [
                        {
                            "rules": [
                                {
                                    "field": (
                                        "Cases.CaseStatus"
                                    ),
                                    "operator": "in",
                                    "value": (
                                        normalized_case_statuses
                                    ),
                                },
                                {
                                    "field": (
                                        "Cases.TargetGroup"
                                    ),
                                    "operator": "eq",
                                    "value": [
                                        validated_target_group_id
                                    ],
                                },
                                {
                                    "field": (
                                        "Cases.CreatedOn"
                                    ),
                                    "operator": "gt",
                                    "value": (
                                        normalized_created_after
                                    ),
                                },
                            ],
                            "condition": "and",
                            "cardinality": "any",
                            "type": "Cases",
                        }
                    ],
                },
                "dslVersion": "1.0.0",
                "resultType": "Cases",
                "columns": [
                    {
                        "name": "CitizenCprFormatted",
                    },
                    {
                        "name": "Cases.CreatedOn",
                    },
                ],
                "sortColumns": [
                    {
                        "desc": False,
                        "name": "CitizenFullName",
                    }
                ],
                "columnFilters": [],
                "embeddedSortColumns": [],
            },
            "pageNumber": page_number,
            "pageSize": page_size,
            "embeddedPageNumber": 0,
            "embeddedPageSize": 100,
        }

        print(
            f"Henter side {page_number + 1}: "
            f"pageNumber={page_number}, "
            f"pageSize={page_size}"
        )

        page_result = await api_client.post(
            endpoint=LISTE_SEARCH_ENDPOINT,
            json_body=payload,
        )

        page_result = _validate_response(
            result=page_result,
            response_name=(
                f"{LISTE_OPLYSNINGSSKEMAER} "
                f"side {page_number + 1}"
            ),
        )

        search_result = page_result.get(
            "searchResult"
        )

        if not isinstance(search_result, dict):
            raise RuntimeError(
                "FASIT-responsen manglede en "
                "dictionary i feltet 'searchResult'."
            )

        rows = search_result.get(
            "rows"
        )

        if not isinstance(rows, list):
            raise RuntimeError(
                "FASIT-responsens searchResult "
                "manglede en liste i feltet 'rows'. "
                f"Felter i searchResult: "
                f"{list(search_result.keys())}"
            )

        if reported_total is None:
            total_value = search_result.get(
                "totalResultsCount"
            )

            if (
                isinstance(total_value, int)
                and not isinstance(total_value, bool)
            ):
                reported_total = total_value

        if reported_page_count is None:
            pages_value = search_result.get(
                "resultsPagesCount"
            )

            if (
                isinstance(pages_value, int)
                and not isinstance(pages_value, bool)
            ):
                reported_page_count = pages_value

        page_count += 1
        number_of_rows = len(rows)

        all_results.extend(
            rows
        )

        print(
            f"Side {page_number + 1}: "
            f"{number_of_rows} poster. "
            f"Samlet hentet: {len(all_results)}."
        )

        if reported_total is not None:
            print(
                "Samlet antal oplyst af FASIT: "
                f"{reported_total}"
            )

        if reported_page_count is not None:
            print(
                "Antal sider oplyst af FASIT: "
                f"{reported_page_count}"
            )

        if number_of_rows == 0:
            break

        if (
            reported_total is not None
            and len(all_results) >= reported_total
        ):
            break

        if (
            reported_page_count is not None
            and page_count >= reported_page_count
        ):
            break

        if (
            reported_total is None
            and reported_page_count is None
            and number_of_rows < page_size
        ):
            break

        page_number += 1

    if (
        reported_total is not None
        and len(all_results) > reported_total
    ):
        all_results = all_results[
            :reported_total
        ]

    return {
        "results": all_results,
        "totalResults": len(all_results),
        "reportedTotal": reported_total,
        "pageCount": page_count,
        "reportedPageCount": reported_page_count,
    }


async def TEST_LISTE_OPLYSNINGSSKEMAER(
    api_client: FasitApiClient,
    *,
    created_after: str = "2025-06-16T22:00:00Z",
    target_group_id: str = OPLYSNINGSSKEMA_TARGET_GROUP_ID,
    case_statuses: list[str] | None = None,
    page_size: int = 250,
    output_file: str | None = None,
) -> dict[str, Any]:
    """
    Tester og validerer hentning af hele listen over
    oplysningsskemaer.

    Funktionen:
    - kalder hent_liste_oplysningsskemaer én gang,
    - validerer det samlede resultat,
    - kontrollerer at alle oplyste poster er hentet,
    - printer kun antal poster og sidekald,
    - gemmer eventuelt rækkerne i en JSON-fil,
    - returnerer hele det validerede resultat.

    Parametre:
    - api_client: Den fælles FasitApiClient.
    - created_after: Medtag sager oprettet efter tidspunktet.
    - target_group_id: Målgruppe-id for oplysningsskemaer.
    - case_statuses: Sagsstatusser, eksempelvis ["1", "3"].
    - page_size: Antal resultater pr. API-kald, maksimalt 250.
    - output_file: Valgfri sti til en JSON-fil.

    Output:
    En dictionary med:
    - results: Alle hentede rækker.
    - totalResults: Faktisk antal hentede rækker.
    - reportedTotal: Antal resultater oplyst af FASIT.
    - pageCount: Antal udførte sidekald.
    - reportedPageCount: Antal sider oplyst af FASIT.
    """
    normalized_case_statuses = (
        case_statuses
        if case_statuses is not None
        else [
            "1",
            "3",
        ]
    )

    result = await hent_liste_oplysningsskemaer(
        api_client=api_client,
        created_after=created_after,
        target_group_id=target_group_id,
        case_statuses=normalized_case_statuses,
        page_size=page_size,
    )

    result = _validate_response(
        result=result,
        response_name="TEST_LISTE_OPLYSNINGSSKEMAER",
    )

    results = result.get(
        "results"
    )

    if not isinstance(results, list):
        raise RuntimeError(
            "TEST_LISTE_OPLYSNINGSSKEMAER manglede "
            "en liste i feltet 'results'."
        )

    total_results = result.get(
        "totalResults"
    )

    if (
        not isinstance(total_results, int)
        or isinstance(total_results, bool)
    ):
        raise RuntimeError(
            "TEST_LISTE_OPLYSNINGSSKEMAER manglede "
            "et heltal i feltet 'totalResults'."
        )

    page_count = result.get(
        "pageCount"
    )

    if (
        not isinstance(page_count, int)
        or isinstance(page_count, bool)
    ):
        raise RuntimeError(
            "TEST_LISTE_OPLYSNINGSSKEMAER manglede "
            "et heltal i feltet 'pageCount'."
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
            not isinstance(reported_page_count, int)
            or isinstance(reported_page_count, bool)
        )
    ):
        raise RuntimeError(
            "Feltet 'reportedPageCount' skal være "
            "et heltal eller None."
        )

    if total_results != len(results):
        raise RuntimeError(
            "totalResults matcher ikke antallet "
            "af rækker i results. "
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
            f"men funktionen hentede {total_results}."
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

    print()
    print("LISTE_OPLYSNINGSSKEMAER er hentet.")
    print(
        "Antal hentede poster: "
        f"{total_results}"
    )
    print(
        "Antal udførte sidekald: "
        f"{page_count}"
    )

    if output_file is not None:
        if not isinstance(output_file, str):
            raise ValueError(
                "output_file skal være en tekstværdi "
                "eller None."
            )

        normalized_output_file = output_file.strip()

        if not normalized_output_file:
            raise ValueError(
                "output_file må ikke være tom, når "
                "parameteren er angivet."
            )

        with open(
            normalized_output_file,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                results,
                file,
                indent=2,
                ensure_ascii=False,
                default=str,
            )

        print(
            "Resultatet blev gemt i: "
            f"{normalized_output_file}"
        )

    return result


# ---------------------------------------------------------------------------
# Persongrupper og persongruppemarkeringer
# ---------------------------------------------------------------------------

async def PERSONGRUPPE(
    api_client: FasitApiClient,
) -> dict[str, Any]:
    """
    Henter listen over tilgængelige persongrupper.

    Output:
    Hele FASITs response som en dictionary.

    Responsen forventes at indeholde:
    {
        "personGroups": [...]
    }
    """
    result = await api_client.get(
        endpoint=PERSONGRUPPE_ENDPOINT,
    )

    result = _validate_response(
        result=result,
        response_name="PERSONGRUPPE",
    )

    person_groups = result.get(
        "personGroups"
    )

    if not isinstance(person_groups, list):
        raise RuntimeError(
            "PERSONGRUPPE-responsen manglede "
            "en liste i feltet 'personGroups'."
        )

    return result


async def hent_persongruppemarkeringer(
    api_client: FasitApiClient,
    citizen_id: str,
) -> dict[str, Any]:
    """
    Henter borgerens eksisterende persongruppemarkeringer.

    Parametre:
    - api_client: Den fælles FasitApiClient.
    - citizen_id: Borgerens FASIT-id.

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
        endpoint=PERSONGRUPPEMARKERINGER_ENDPOINT,
        json_body=payload,
    )

    return _validate_response(
        result=result,
        response_name="PERSONGRUPPEMARKERINGER",
    )


async def opret_persongruppemarkering(
    api_client: FasitApiClient,
    *,
    startdato: DatoType,
    slutdato: DatoType,
    citizen_id: str,
    persongruppenavn: str,
) -> dict[str, Any]:
    """
    Opretter en persongruppemarkering på en borger.

    Funktionen:
    1. Validerer citizenId.
    2. Validerer start- og slutdato.
    3. Henter alle persongrupper via PERSONGRUPPE.
    4. Finder en aktiv persongruppe ud fra navnet.
    5. Anvender persongruppens id i oprettelseskaldet.

    Parametre:
    - api_client: Den fælles FasitApiClient.
    - startdato: Markeringens startdato.
    - slutdato: Markeringens slutdato.
    - citizen_id: Borgerens FASIT-id.
    - persongruppenavn: Det præcise navn på persongruppen.

    Output:
    Hele FASITs response fra oprettelsen.
    """
    validated_citizen_id = _validate_citizen_id(
        citizen_id
    )

    parsed_startdato = _parse_dansk_dato(
        dato=startdato,
        feltnavn="startdato",
    )

    parsed_slutdato = _parse_dansk_dato(
        dato=slutdato,
        feltnavn="slutdato",
    )

    if parsed_slutdato < parsed_startdato:
        raise ValueError(
            "slutdato må ikke ligge før startdato."
        )

    formatted_startdato = _dato_til_fasit_utc(
        dato=parsed_startdato,
        feltnavn="startdato",
    )

    formatted_slutdato = _dato_til_fasit_utc(
        dato=parsed_slutdato,
        feltnavn="slutdato",
    )

    person_group_result = await PERSONGRUPPE(
        api_client=api_client,
    )

    person_groups = person_group_result.get(
        "personGroups"
    )

    if not isinstance(person_groups, list):
        raise RuntimeError(
            "PERSONGRUPPE-responsen manglede "
            "en liste i feltet 'personGroups'."
        )

    person_group_id = _find_person_group_id(
        person_groups=person_groups,
        persongruppenavn=persongruppenavn,
    )

    payload = {
        "startDate": formatted_startdato,
        "endDate": formatted_slutdato,
        "citizenId": validated_citizen_id,
        "personGroupId": person_group_id,
    }

    result = await api_client.post(
        endpoint=OPRET_PERSONGRUPPEMARKERING_ENDPOINT,
        json_body=payload,
    )

    return _validate_response(
        result=result,
        response_name="OPRET_PERSONGRUPPEMARKERING",
    )


# ---------------------------------------------------------------------------
# Kommunens markeringer
# ---------------------------------------------------------------------------

async def opret_kommunens_markeringer(
    api_client: FasitApiClient,
    citizen_id: str,
    tekst: str | None = None,
    kun_laes: bool = True,
) -> dict[str, Any]:
    """
    Læser, opdaterer eller sletter importantNote2.

    Parametre:
    - api_client: Den fælles FasitApiClient.
    - citizen_id: Borgerens FASIT-id.
    - tekst:
      - Tekstværdi: Feltet opdateres med teksten.
      - Tom tekst "": Feltets indhold slettes.
      - None: Kun tilladt, når kun_laes er True.
    - kun_laes:
      - True: Feltet læses uden ændringer.
      - False: Feltet opdateres eller slettes.

    Output ved læsning:
    {
        "updated": False,
        "field": "importantNote2",
        "value": "...",
        "isEmpty": False
    }

    Output ved opdatering eller sletning:
    {
        "updated": True,
        "field": "importantNote2",
        "previousValue": "...",
        "newValue": "",
        "deleted": True,
        "result": {...}
    }
    """
    validated_citizen_id = _validate_citizen_id(
        citizen_id
    )

    if not isinstance(kun_laes, bool):
        raise ValueError(
            "kun_laes skal være True eller False."
        )

    notes_result = await api_client.post(
        endpoint=KOMMUNENS_MARKERINGER_NOTER_ENDPOINT,
        json_body={
            "citizenId": validated_citizen_id,
        },
    )

    notes_result = _validate_response(
        result=notes_result,
        response_name="HENT_KOMMUNENS_MARKERINGER",
    )

    notes = notes_result.get(
        "notes"
    )

    if not isinstance(notes, dict):
        raise RuntimeError(
            "Responsen fra getnotesforcitizen "
            "manglede en dictionary i feltet 'notes'."
        )

    current_value = notes.get(
        "importantNote2"
    )

    if current_value is None:
        current_value = ""

    if not isinstance(current_value, str):
        raise RuntimeError(
            "Feltet 'importantNote2' havde et "
            "uventet format. Forventede tekst eller null."
        )

    if kun_laes:
        return {
            "updated": False,
            "field": "importantNote2",
            "value": current_value,
            "isEmpty": not current_value.strip(),
        }

    if tekst is None:
        raise ValueError(
            "tekst skal angives, når kun_laes er False. "
            "Brug en tom tekstværdi \"\" for at slette "
            "indholdet."
        )

    if not isinstance(tekst, str):
        raise ValueError(
            "tekst skal være en tekstværdi."
        )

    new_value = tekst.strip()

    if current_value == new_value:
        return {
            "updated": False,
            "field": "importantNote2",
            "previousValue": current_value,
            "newValue": new_value,
            "deleted": new_value == "",
            "reason": (
                "Feltet indeholder allerede "
                "den ønskede værdi."
            ),
        }

    updated_notes = dict(
        notes
    )

    updated_notes["importantNote2"] = (
        new_value
    )

    payload = {
        "citizenId": validated_citizen_id,
        "notes": updated_notes,
    }

    update_result = await api_client.post(
        endpoint=OPDATER_KOMMUNENS_MARKERINGER_ENDPOINT,
        json_body=payload,
    )

    update_result = _validate_response(
        result=update_result,
        response_name="OPDATER_KOMMUNENS_MARKERINGER",
    )

    return {
        "updated": True,
        "field": "importantNote2",
        "previousValue": current_value,
        "newValue": new_value,
        "deleted": new_value == "",
        "result": update_result,
    }