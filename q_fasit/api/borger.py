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
# Aktivitetsparate kontanthjælpsmodtagere over 30 - afklaringsretten.
# ---------------------------------------------------------------------------

AKTIVITETSPARATE_KONTANTHJAELPSMODTAGERE_OVER_30 = (
    "AKTIVITETSPARATE_KONTANTHJAELPSMODTAGERE_OVER_30"
)

AKTIVITETSPARATE_TARGET_GROUP_ID = (
    "a65c6a8e-1b27-e111-9ada-005056a823a6"
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

def _create_aktivitetsparate_over_30_payload(
    *,
    target_group_id: str,
    primary_case_statuses: list[str],
    page_number: int,
    page_size: int,
) -> dict[str, Any]:
    """
    Opretter payloaden til listen over aktivitetsparate
    kontanthjælpsmodtagere over 30 år.

    Søgekriterier:
    - Primær sagsstatus skal være 1 eller 3.
    - Borgeren skal have en sag i den angivne målgruppe.
    - Sagen skal være aktiv på dags dato eller uden slutdato.
    - Borgerens alder skal være over 29 år.
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
                        "value": primary_case_statuses,
                        "field": (
                            "PrimaryCase."
                            "PrimaryCaseStatus"
                        ),
                        "operator": "in",
                    },
                    {
                        "rules": [
                            {
                                "field": (
                                    "Cases.TargetGroup"
                                ),
                                "operator": "eq",
                                "value": [
                                    target_group_id,
                                ],
                            },
                            {
                                "rules": [
                                    {
                                        "field": (
                                            "Cases.CaseEndDate"
                                        ),
                                        "operator": "ge",
                                        "value": "@dd",
                                    },
                                    {
                                        "field": (
                                            "Cases.CaseEndDate"
                                        ),
                                        "operator": "empty",
                                    },
                                ],
                                "condition": "or",
                            },
                        ],
                        "condition": "and",
                        "cardinality": "any",
                        "type": "Cases",
                    },
                    {
                        "field": "CitizenAge",
                        "operator": "gt",
                        "value": "29",
                    },
                ],
            },
            "dslVersion": "1.0.0",
            "columns": [
                {
                    "name": "CitizenFullName",
                },
                {
                    "name": "CitizenCprFormatted",
                },
                {
                    "name": (
                        "PrimaryCase."
                        "CitizenCurrentTargetGroup"
                    ),
                },
                {
                    "name": (
                        "PrimaryCase."
                        "PrimaryCaseStartDate"
                    ),
                },
                {
                    "name": (
                        "PrimaryCase."
                        "PrimaryCaseEndDate"
                    ),
                },
                {
                    "name": "CitizenAge",
                },
            ],
            "sortColumns": [
                {
                    "desc": False,
                    "name": "CitizenFullName",
                },
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
) -> list[dict[str, Any]]:
    """
    Henter alle oplysningsskemaer som individuelle rækker.

    Funktionen håndterer automatisk paginering ved at kalde
    FASIT med pageNumber 0, 1, 2 osv.

    Feltet "id" omdøbes til "citizenid" i hver række.

    Parametre:
    - api_client: Den fælles FasitApiClient.
    - created_after: Medtag sager oprettet efter tidspunktet.
    - target_group_id: Målgruppe-id for oplysningsskemaer.
    - case_statuses: Sagsstatusser, eksempelvis ["1", "3"].
    - page_size: Antal resultater pr. API-kald, maksimalt 250.

    Output:
    En liste med alle normaliserede rækker fra samtlige sider.

    Eksempel:
    [
        {
            "citizenid": "...",
            "CitizenCprFormatted": "...",
            "Cases.CreatedOn": "...",
        }
    ]
    """
    if not isinstance(created_after, str):
        raise ValueError(
            "created_after skal være en tekstværdi."
        )

    normalized_created_after = (
        created_after.strip()
    )

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

        normalized_case_statuses: list[str] = []

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

    if (
        not isinstance(page_size, int)
        or isinstance(page_size, bool)
    ):
        raise ValueError(
            "page_size skal være et heltal."
        )

    if page_size < 1 or page_size > 250:
        raise ValueError(
            "page_size skal være mellem 1 og 250."
        )

    page_number = 0
    page_count = 0

    alle_raekker: list[dict[str, Any]] = []

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
            page_count_value = search_result.get(
                "resultsPagesCount"
            )

            if (
                isinstance(page_count_value, int)
                and not isinstance(
                    page_count_value,
                    bool,
                )
            ):
                reported_page_count = (
                    page_count_value
                )

        normaliserede_raekker: list[
            dict[str, Any]
        ] = []

        for row_number, row in enumerate(
            rows,
            start=1,
        ):
            if not isinstance(row, dict):
                raise RuntimeError(
                    f"Række {row_number} på side "
                    f"{page_number + 1} var ikke "
                    "en dictionary."
                )

            normaliseret_raekke = dict(
                row
            )

            if "id" in normaliseret_raekke:
                original_id = (
                    normaliseret_raekke.pop("id")
                )

                existing_citizen_id = (
                    normaliseret_raekke.get(
                        "citizenid"
                    )
                )

                if (
                    existing_citizen_id is not None
                    and existing_citizen_id
                    != original_id
                ):
                    raise RuntimeError(
                        "Rækken indeholdt både 'id' "
                        "og 'citizenid' med forskellige "
                        "værdier."
                    )

                normaliseret_raekke[
                    "citizenid"
                ] = original_id

            normaliserede_raekker.append(
                normaliseret_raekke
            )

        alle_raekker.extend(
            normaliserede_raekker
        )

        page_count += 1
        number_of_rows = len(rows)

        print(
            f"Side {page_number + 1}: "
            f"{number_of_rows} poster. "
            f"Samlet hentet: {len(alle_raekker)}."
        )

        if number_of_rows == 0:
            break

        if (
            reported_total is not None
            and len(alle_raekker) >= reported_total
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
        and len(alle_raekker) < reported_total
    ):
        raise RuntimeError(
            "Ikke alle oplysningsskemaer blev hentet. "
            f"FASIT oplyste {reported_total}, men "
            f"funktionen hentede {len(alle_raekker)}."
        )

    if (
        reported_total is not None
        and len(alle_raekker) > reported_total
    ):
        alle_raekker = alle_raekker[
            :reported_total
        ]

    print()
    print(
        "LISTE_OPLYSNINGSSKEMAER er hentet."
    )
    print(
        "Antal hentede rækker: "
        f"{len(alle_raekker)}"
    )
    print(
        "Antal udførte sidekald: "
        f"{page_count}"
    )

    return alle_raekker

#Hent Aktivitetsparate kontanthjælpsmodtagere over 30 - afklaringsretten.

async def hent_aktivitetsparate_kontanthjaelpsmodtagere_over_30(
    api_client: FasitApiClient,
    *,
    target_group_id: str = AKTIVITETSPARATE_TARGET_GROUP_ID,
    primary_case_statuses: list[str] | None = None,
    page_size: int = 250,
) -> list[dict[str, Any]]:
    """
    Henter alle aktivitetsparate kontanthjælpsmodtagere
    over 30 år som individuelle rækker.

    Funktionen håndterer automatisk paginering ved at
    kalde FASIT med pageNumber 0, 1, 2 osv.

    Feltet "id" omdøbes til "citizenid" i hver række.

    Søgekriterier:
    - Primær sagsstatus er 1 eller 3.
    - Sagens målgruppe matcher target_group_id.
    - Sagens slutdato er dags dato eller senere,
      eller sagens slutdato er tom.
    - Borgerens alder er over 29 år.

    Parametre:
    - api_client: Den fælles FasitApiClient.
    - target_group_id: Målgruppe-id for søgningen.
    - primary_case_statuses: Primære sagsstatusser.
    - page_size: Antal resultater pr. API-kald,
      maksimalt 250.

    Output:
    En liste med alle normaliserede rækker fra
    samtlige sider.
    """
    validated_target_group_id = (
        _validate_target_group_id(
            target_group_id
        )
    )

    if primary_case_statuses is None:
        normalized_primary_case_statuses = [
            "1",
            "3",
        ]
    else:
        if not isinstance(
            primary_case_statuses,
            list,
        ):
            raise ValueError(
                "primary_case_statuses skal være "
                "en liste."
            )

        normalized_primary_case_statuses: list[str] = []

        for status in primary_case_statuses:
            if not isinstance(status, str):
                raise ValueError(
                    "Alle værdier i "
                    "primary_case_statuses skal "
                    "være tekstværdier."
                )

            normalized_status = status.strip()

            if not normalized_status:
                raise ValueError(
                    "primary_case_statuses må ikke "
                    "indeholde tomme værdier."
                )

            normalized_primary_case_statuses.append(
                normalized_status
            )

    if not normalized_primary_case_statuses:
        raise ValueError(
            "primary_case_statuses må ikke være tom."
        )

    if (
        not isinstance(page_size, int)
        or isinstance(page_size, bool)
    ):
        raise ValueError(
            "page_size skal være et heltal."
        )

    if page_size < 1 or page_size > 250:
        raise ValueError(
            "page_size skal være mellem 1 og 250."
        )

    page_number = 0
    page_count = 0

    alle_raekker: list[dict[str, Any]] = []

    reported_total: int | None = None
    reported_page_count: int | None = None

    while True:
        payload = (
            _create_aktivitetsparate_over_30_payload(
                target_group_id=(
                    validated_target_group_id
                ),
                primary_case_statuses=(
                    normalized_primary_case_statuses
                ),
                page_number=page_number,
                page_size=page_size,
            )
        )

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
                f"{AKTIVITETSPARATE_KONTANTHJAELPSMODTAGERE_OVER_30} "
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
                "Felter i searchResult: "
                f"{list(search_result.keys())}"
            )

        if reported_total is None:
            total_value = search_result.get(
                "totalResultsCount"
            )

            if (
                isinstance(total_value, int)
                and not isinstance(
                    total_value,
                    bool,
                )
            ):
                reported_total = total_value

        if reported_page_count is None:
            page_count_value = search_result.get(
                "resultsPagesCount"
            )

            if (
                isinstance(page_count_value, int)
                and not isinstance(
                    page_count_value,
                    bool,
                )
            ):
                reported_page_count = (
                    page_count_value
                )

        normaliserede_raekker: list[
            dict[str, Any]
        ] = []

        for row_number, row in enumerate(
            rows,
            start=1,
        ):
            if not isinstance(row, dict):
                raise RuntimeError(
                    f"Række {row_number} på side "
                    f"{page_number + 1} var ikke "
                    "en dictionary."
                )

            normaliseret_raekke = dict(
                row
            )

            if "id" in normaliseret_raekke:
                original_id = (
                    normaliseret_raekke.pop(
                        "id"
                    )
                )

                existing_citizen_id = (
                    normaliseret_raekke.get(
                        "citizenid"
                    )
                )

                if (
                    existing_citizen_id is not None
                    and existing_citizen_id
                    != original_id
                ):
                    raise RuntimeError(
                        f"Række {row_number} på side "
                        f"{page_number + 1} indeholdt "
                        "både 'id' og 'citizenid' med "
                        "forskellige værdier."
                    )

                normaliseret_raekke[
                    "citizenid"
                ] = original_id

            normaliserede_raekker.append(
                normaliseret_raekke
            )

        alle_raekker.extend(
            normaliserede_raekker
        )

        page_count += 1
        number_of_rows = len(rows)

        print(
            f"Side {page_number + 1}: "
            f"{number_of_rows} poster. "
            f"Samlet hentet: {len(alle_raekker)}."
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
            and len(alle_raekker) >= reported_total
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
        and len(alle_raekker) < reported_total
    ):
        raise RuntimeError(
            "Ikke alle aktivitetsparate "
            "kontanthjælpsmodtagere blev hentet. "
            f"FASIT oplyste {reported_total}, men "
            f"funktionen hentede {len(alle_raekker)}."
        )

    if (
        reported_total is not None
        and len(alle_raekker) > reported_total
    ):
        alle_raekker = alle_raekker[
            :reported_total
        ]

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
    print(
        "AKTIVITETSPARATE_"
        "KONTANTHJAELPSMODTAGERE_OVER_30 "
        "er hentet."
    )
    print(
        "Antal hentede rækker: "
        f"{len(alle_raekker)}"
    )
    print(
        "Antal udførte sidekald: "
        f"{page_count}"
    )

    return alle_raekker

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