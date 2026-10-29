from __future__ import annotations

from collections.abc import Collection
from datetime import datetime
from pathlib import Path
from typing import Any


from playwright.async_api import Locator, Page, expect

from q_fasit.utils import wait_for_page_ready


FASIT_BASE_URL = "https://haderslev.schultzfasit.dk"
# Ret kun denne streng, hvis den konkrete FASIT-route i jeres miljø er anderledes.
JOURNAL_URL_TEMPLATE = (
    FASIT_BASE_URL
    + "/citizen/authority/{citizen_id}/journal/note/create?opticId=beskaeftigelse-standard"
)


def _required_text(value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} skal være tekst.")
    value = " ".join(value.split())
    if not value:
        raise ValueError(f"{field_name} må ikke være tom.")
    return value


def _validate_date(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    value = _required_text(value, field_name)
    try:
        datetime.strptime(value, "%d-%m-%Y")
    except ValueError as error:
        raise ValueError(f"{field_name} skal have formatet dd-mm-yyyy.") from error
    return value


def _validate_time(value: str, field_name: str) -> str:
    value = _required_text(value, field_name)
    try:
        datetime.strptime(value, "%H:%M")
    except ValueError as error:
        raise ValueError(f"{field_name} skal have formatet HH:MM, fx 11:00.") from error
    return value


def _normalise_documents(
    documents: Collection[str | Path] | None,
) -> list[Path]:
    """
    Validerer og normaliserer dokumentstier.

    None eller en tom collection betyder, at journalnotatet
    skal behandles uden bilag.

    Hver angivet fil:
    - skal være angivet som str eller Path,
    - konverteres til en absolut Path,
    - skal eksistere som en almindelig fil,
    - skal indeholde mindst én byte.

    Args:
        documents:
            En collection af filstier eller None.

    Returns:
        En liste med absolutte, validerede filstier.
        Listen er tom, hvis documents er None eller tom.

    Raises:
        TypeError:
            Hvis documents er én enkelt str, bytes eller Path,
            eller hvis et element ikke er str eller Path.

        FileNotFoundError:
            Hvis en angivet fil ikke findes eller ikke er en fil.

        ValueError:
            Hvis en angivet fil har en størrelse på 0 bytes.
    """

    # Bilag er valgfrit.
    if documents is None:
        return []

    # En tom collection er også tilladt og giver ingen bilag.
    if not documents:
        return []

    # En tekststreng er teknisk set en collection af tegn.
    # Derfor skal den afvises, så hvert tegn ikke behandles
    # som en separat filsti.
    if isinstance(documents, (str, bytes, Path)):
        raise TypeError(
            "documents skal være en collection af filstier "
            "eller None. Modtog én enkelt str, bytes eller Path."
        )

    result: list[Path] = []

    for index, document in enumerate(documents):
        if not isinstance(document, (str, Path)):
            raise TypeError(
                "Hvert dokument skal være angivet som str eller Path. "
                f"Element nummer {index + 1} har typen "
                f"{type(document).__name__!r}."
            )

        path = Path(document).expanduser().resolve()

        if not path.is_file():
            raise FileNotFoundError(
                "Bilaget findes ikke eller er ikke en almindelig fil: "
                f"{path}"
            )

        try:
            file_size = path.stat().st_size
        except OSError as error:
            raise OSError(
                f"Kunne ikke læse oplysninger om bilaget: {path}"
            ) from error

        if file_size == 0:
            raise ValueError(
                f"Bilaget er tomt og kan ikke vedhæftes: {path}"
            )

        result.append(path)

    return result


async def _visible(page: Page, selectors: list[str], timeout: int) -> Locator:
    """Returnerer den første synlige locator blandt flere robuste alternativer."""
    last_error: Exception | None = None
    for selector in selectors:
        locator = page.locator(selector).first
        try:
            await locator.wait_for(state="visible", timeout=min(timeout, 3_000))
            return locator
        except Exception as error:
            last_error = error
    raise RuntimeError(f"Kunne ikke finde et synligt element. Selectors: {selectors}") from last_error


async def _field(
    page: Page,
    label: str,
    timeout: int,
) -> Locator:
    """
    Finder et almindeligt tekstfelt ud fra feltets label.

    Funktionen returnerer kun:
    - inputfelter, som ikke er comboboxes
    - textarea-felter

    Det forhindrer eksempelvis, at feltet "Notat" fejlagtigt
    matcher comboboxen "Notattype".
    """

    normalized_label = " ".join(label.split()).casefold()

    async def is_correct_text_field(locator: Locator) -> bool:
        """
        Kontrollerer, at locatoren er et almindeligt tekstfelt
        og ikke eksempelvis en autocomplete/combobox.
        """
        try:
            if await locator.count() == 0:
                return False

            if not await locator.is_visible():
                return False

            tag_name = await locator.evaluate(
                "(element) => element.tagName.toLowerCase()"
            )
            role = (
                await locator.get_attribute("role")
                or ""
            ).casefold()
            input_type = (
                await locator.get_attribute("type")
                or ""
            ).casefold()

            if tag_name not in {"input", "textarea"}:
                return False

            # Notattype, Sag og Kilde er comboboxes og må ikke
            # returneres af denne hjælpefunktion.
            if role == "combobox":
                return False

            if input_type in {
                "button",
                "checkbox",
                "file",
                "hidden",
                "radio",
                "reset",
                "submit",
            }:
                return False

            return True

        except Exception:
            return False

    async def accessible_name_matches(locator: Locator) -> bool:
        """
        Kontrollerer feltets tilgængelige navn.

        Det præcise navn "Notat" må matche.
        Navnet "Notattype" må ikke matche.
        """
        try:
            accessible_name = await locator.evaluate(
                """
                (element) => {
                    const ariaLabel =
                        element.getAttribute("aria-label");

                    if (ariaLabel) {
                        return ariaLabel;
                    }

                    const labelledBy =
                        element.getAttribute("aria-labelledby");

                    if (labelledBy) {
                        const text = labelledBy
                            .split(/\\s+/)
                            .map((id) => {
                                const labelElement =
                                    document.getElementById(id);

                                return labelElement
                                    ? labelElement.textContent
                                    : "";
                            })
                            .join(" ")
                            .trim();

                        if (text) {
                            return text;
                        }
                    }

                    if (element.labels && element.labels.length) {
                        return Array.from(element.labels)
                            .map((labelElement) =>
                                labelElement.textContent || ""
                            )
                            .join(" ")
                            .trim();
                    }

                    return "";
                }
                """
            )

            normalized_name = " ".join(
                str(accessible_name or "").split()
            ).casefold()

            # Fjern almindelig markering af obligatoriske felter.
            normalized_name = normalized_name.removesuffix("*").strip()

            return normalized_name == normalized_label

        except Exception:
            return False

    async def first_valid(
        candidates: list[Locator],
        *,
        require_exact_name: bool = False,
    ) -> Locator | None:
        """
        Returnerer den første synlige og gyldige locator.
        """
        for candidate in candidates:
            try:
                count = await candidate.count()
            except Exception:
                continue

            for index in range(count):
                locator = candidate.nth(index)

                if not await is_correct_text_field(locator):
                    continue

                if (
                    require_exact_name
                    and not await accessible_name_matches(locator)
                ):
                    continue

                await locator.scroll_into_view_if_needed()
                return locator

        return None

    # Søg i hovedsiden og i eventuelle child frames.
    search_contexts = [page, *page.frames[1:]]

    # Vent på forsinket rendering, men brug højst den timeout,
    # som kalderen har angivet.
    attempts = max(1, timeout // 250)

    for _ in range(attempts):
        for context in search_contexts:
            # For Notat prioriteres textarea, fordi et længere notat
            # normalt ikke bør udfyldes i et autocomplete-input.
            if normalized_label == "notat":
                candidates = [
                    context.locator(
                        'textarea[aria-label="Notat"]'
                    ),
                    context.get_by_role(
                        "textbox",
                        name="Notat",
                        exact=True,
                    ).locator("textarea"),
                    context.locator(
                        'label:has-text("Notat")'
                    ).locator(
                        "xpath=following::textarea[1]"
                    ),
                    context.locator(
                        '.MuiFormControl-root:has-text("Notat") '
                        "textarea"
                    ),
                    context.locator(
                        "textarea"
                    ),
                ]
            else:
                candidates = [
                    # Korrekt sammenknyttet HTML-label eller ARIA-label.
                    context.get_by_label(
                        label,
                        exact=True,
                    ),

                    # Præcist accessible name.
                    context.get_by_role(
                        "textbox",
                        name=label,
                        exact=True,
                    ),

                    # Direkte ARIA-label.
                    context.locator(
                        f'input[aria-label="{label}"], '
                        f'textarea[aria-label="{label}"]'
                    ),

                    # Klassisk label efterfulgt af input/textarea.
                    context.locator(
                        f'label:has-text("{label}")'
                    ).locator(
                        "xpath=following::input[1] "
                        "| following::textarea[1]"
                    ),

                    # MUI TextField/FormControl.
                    context.locator(
                        f'.MuiFormControl-root:has-text("{label}")'
                    ).locator(
                        "input:not([role='combobox']), textarea"
                    ),

                    context.locator(
                        f'.MuiTextField-root:has-text("{label}")'
                    ).locator(
                        "input:not([role='combobox']), textarea"
                    ),
                ]

            found = await first_valid(candidates)

            if found is not None:
                return found

            # Bred fallback må kun returnere et felt, hvis elementets
            # tilgængelige navn er præcis det ønskede feltnavn.
            broad_candidates = [
                context.get_by_label(
                    label,
                    exact=False,
                ),
                context.get_by_role(
                    "textbox",
                    name=label,
                    exact=False,
                ),
            ]

            found = await first_valid(
                broad_candidates,
                require_exact_name=True,
            )

            if found is not None:
                return found

        await page.wait_for_timeout(250)

    visible_fields: list[dict[str, str | None]] = []

    for frame_index, frame in enumerate(page.frames):
        fields = frame.locator(
            "input:visible, textarea:visible"
        )

        try:
            field_count = await fields.count()
        except Exception:
            continue

        for field_index in range(min(field_count, 30)):
            field = fields.nth(field_index)

            try:
                visible_fields.append(
                    {
                        "frame": str(frame_index),
                        "tag": await field.evaluate(
                            "(element) => "
                            "element.tagName.toLowerCase()"
                        ),
                        "role": await field.get_attribute("role"),
                        "id": await field.get_attribute("id"),
                        "name": await field.get_attribute("name"),
                        "aria_label": await field.get_attribute(
                            "aria-label"
                        ),
                        "placeholder": await field.get_attribute(
                            "placeholder"
                        ),
                        "value": await field.input_value(),
                    }
                )
            except Exception:
                continue

    raise RuntimeError(
        f"Kunne ikke finde tekstfeltet {label!r}. "
        f"Aktuel URL: {page.url!r}. "
        f"Synlige felter: {visible_fields!r}"
    )



async def _fill_and_validate(
    locator: Locator,
    value: str,
    field_name: str,
) -> None:
    """
    Udfylder og validerer et almindeligt input- eller textarea-felt.

    Funktionen afviser comboboxes, så eksempelvis feltet "Notat"
    ikke ved en fejl udfylder comboboxen "Notattype".
    """

    tag_name = await locator.evaluate(
        "(element) => element.tagName.toLowerCase()"
    )
    role = (
        await locator.get_attribute("role")
        or ""
    ).casefold()
    element_id = await locator.get_attribute("id")
    aria_label = await locator.get_attribute("aria-label")

    if tag_name not in {"input", "textarea"}:
        raise RuntimeError(
            f"{field_name} peger ikke på et input- eller textarea-felt. "
            f"Element: tag={tag_name!r}, role={role!r}, "
            f"id={element_id!r}, aria-label={aria_label!r}."
        )

    if role == "combobox":
        raise RuntimeError(
            f"{field_name} peger fejlagtigt på en combobox. "
            f"Element: tag={tag_name!r}, role={role!r}, "
            f"id={element_id!r}, aria-label={aria_label!r}."
        )

    await locator.scroll_into_view_if_needed()
    await locator.fill(value)
    await locator.press("Tab")

    try:
        await expect(locator).to_have_value(
            value,
            timeout=5_000,
        )
    except AssertionError as error:
        actual = await locator.input_value()

        raise RuntimeError(
            f"{field_name} blev ikke udfyldt korrekt. "
            f"Forventede {value!r}, fik {actual!r}. "
            f"Element: tag={tag_name!r}, role={role!r}, "
            f"id={element_id!r}, aria-label={aria_label!r}."
        ) from error


async def _select_combobox(
    page: Page,
    label: str,
    value: str,
    timeout: int,
    *,
    starts_with: bool = False,
) -> str:
    """
    Udfylder en MUI Autocomplete og vælger den første mulighed.

    Flow:
    1. Finder comboboxen ud fra feltets label.
    2. Rydder den eksisterende værdi.
    3. Udfylder søgeteksten.
    4. Venter på dropdown-listen.
    5. Finder og validerer option-0.
    6. Klikker på option-0.
    7. Kontrollerer, at den valgte værdi står i inputfeltet.

    Returnerer den endelige valgte tekst fra comboboxen.
    """

    value = _required_text(value, label)

    combobox = await _visible(
        page,
        [
            (
                f"//label[contains(normalize-space(.), '{label}')]"
                "/following::input[@role='combobox'][1]"
            ),
            (
                f"fieldset:has(legend:has-text('{label}')) "
                "input[role='combobox']"
            ),
            f"input[role='combobox'][aria-label*='{label}']",
        ],
        timeout,
    )

    await expect(combobox).to_be_visible()
    await expect(combobox).to_be_enabled()

    # Ryd den nuværende værdi via MUI-knappen, hvis den findes.
    clear_button = combobox.locator(
        "xpath=following-sibling::*"
        "//button[@aria-label='Ryd' or @title='Ryd']"
    ).first

    if await clear_button.count() and await clear_button.is_visible():
        await clear_button.click()
    else:
        await combobox.click()
        await combobox.press("Control+A")
        await combobox.press("Backspace")

    # Udfyld søgeteksten.
    await combobox.fill(value)
    await expect(combobox).to_have_value(value)

    # aria-controls peger på den listbox, der hører til comboboxen.
    listbox_id = await combobox.get_attribute("aria-controls")

    if listbox_id:
        listbox = page.locator(
            f"[id='{listbox_id}'][role='listbox'], "
            f"[id='{listbox_id}']"
        ).first
    else:
        # Reserve hvis FASIT ikke har nået at sætte aria-controls.
        listbox = page.locator(
            "[role='listbox']:visible"
        ).last

    await listbox.wait_for(
        state="visible",
        timeout=timeout,
    )

    # I MUI hedder den første mulighed normalt:
    # <listbox-id>-option-0
    first_option = listbox.locator(
        "[role='option'][id$='-option-0']"
    ).first

    # Reserve hvis id-formatet ændres, men rækkefølgen bevares.
    if not await first_option.count():
        first_option = listbox.locator(
            "[role='option']"
        ).first

    await first_option.wait_for(
        state="visible",
        timeout=timeout,
    )

    option_text = " ".join(
        (await first_option.inner_text()).split()
    )

    if not option_text:
        raise RuntimeError(
            f"Den første mulighed i dropdown-feltet "
            f"{label!r} havde ingen tekst."
        )

    if starts_with:
        option_matches = option_text.casefold().startswith(
            value.casefold()
        )
    else:
        option_matches = (
            option_text.casefold() == value.casefold()
        )

    if not option_matches:
        raise RuntimeError(
            f"Option 0 i feltet {label!r} matcher ikke inputtet. "
            f"Input={value!r}, option 0={option_text!r}."
        )

    print(
        f"✅ {label}: option 0 er valideret: "
        f"{option_text!r}"
    )

    # Vælg option 0 ved klik.
    await first_option.scroll_into_view_if_needed()
    await first_option.click()

    # Dropdownen skal lukke efter valget.
    await expect(listbox).to_be_hidden(
        timeout=timeout,
    )

    # Kontroller inputfeltets endelige valgte værdi.
    await expect(combobox).to_have_value(
        option_text,
        timeout=timeout,
    )

    selected_value = " ".join(
        (await combobox.input_value()).split()
    )

    if selected_value.casefold() != option_text.casefold():
        raise RuntimeError(
            f"{label} blev ikke valgt korrekt. "
            f"Forventede {option_text!r}, "
            f"fik {selected_value!r}."
        )

    print(
        f"✅ {label}: valgt værdi er bekræftet: "
        f"{selected_value!r}"
    )

    return selected_value


async def _close_initial_popup(
    page: Page,
    session,
    timeout: int,
) -> bool:
    """
    Finder og lukker FASITs separate journal-popup.

    Popup'en er ikke en HTML-dialog på den oprindelige side.
    Popup'en er en selvstændig Playwright Page i browser-contexten.

    Returnerer:
        True, hvis popup-vinduet blev fundet og lukket.
        False, hvis popup-vinduet ikke blev åbnet.
    """

    context = session.context
    original_page = page

    print("⏳ Venter på FASITs journal-popup...")

    popup_page: Page | None = None
    deadline = original_page.context.pages[0]
    del deadline

    # Vent på, at den nye Page bliver oprettet.
    elapsed = 0
    poll_interval = 250

    while elapsed < timeout:
        for candidate in context.pages:
            if candidate == original_page:
                continue

            if candidate.is_closed():
                continue

            candidate_url = candidate.url.casefold()

            # Den synlige popup på billedet åbnes på xrmweb-domænet
            # og bruger siden NewJournalNoteCitizen.
            if (
                "xrmweb.schultzfasit.dk" in candidate_url
                or "newjournalnotecitizen" in candidate_url
                or "/journalnotes/" in candidate_url
            ):
                popup_page = candidate
                break

        if popup_page is not None:
            break

        await original_page.wait_for_timeout(poll_interval)
        elapsed += poll_interval

    if popup_page is None:
        print("ℹ️ Der blev ikke åbnet et separat journal-popupvindue.")
        return False

    print(f"✅ Journal-popup fundet: {popup_page.url}")

    try:
        await popup_page.wait_for_load_state(
            "domcontentloaded",
            timeout=timeout,
        )
    except Exception:
        # Popup'en kan allerede være færdig med at indlæse.
        pass

    await popup_page.wait_for_timeout(500)

    await session.screenshot(
        popup_page,
        "journal_popup_foer_lukning",
        always=True,
    )

    # På billedet er “Luk vindue” en almindelig knap på popup-siden.
    close_button_selectors = [
        "button:has-text('Luk vindue')",
        "input[type='button'][value='Luk vindue']",
        "input[type='submit'][value='Luk vindue']",
        "input[value='Luk vindue']",
        "[role='button']:has-text('Luk vindue')",
        "text='Luk vindue'",
    ]

    close_button: Locator | None = None

    for selector in close_button_selectors:
        candidate = popup_page.locator(selector).first

        try:
            if (
                await candidate.count()
                and await candidate.is_visible()
            ):
                close_button = candidate
                print(
                    "✅ Knappen 'Luk vindue' blev fundet med selector:",
                    selector,
                )
                break
        except Exception:
            continue

    if close_button is None:
        await session.screenshot(
            popup_page,
            "FEJL_luk_vindue_knap_ikke_fundet",
            always=True,
        )

        raise RuntimeError(
            "Journal-popup'en blev fundet, men knappen "
            "'Luk vindue' kunne ikke findes. "
            "Se screenshot 'FEJL_luk_vindue_knap_ikke_fundet'."
        )

    try:
        # Klikket forventes at lukke hele popup-siden.
        async with popup_page.expect_event(
            "close",
            timeout=timeout,
        ):
            await close_button.click()

    except Exception as error:
        # Hvis siden allerede er lukket, er handlingen lykkedes,
        # selv om expect_event nåede at give en fejl.
        if popup_page.is_closed():
            print("✅ Journal-popup'en blev lukket.")
            return True

        await session.screenshot(
            popup_page,
            "FEJL_journal_popup_blev_ikke_lukket",
            always=True,
        )

        raise RuntimeError(
            "Der blev klikket på 'Luk vindue', men "
            "journal-popup'en blev ikke lukket."
        ) from error

    if not popup_page.is_closed():
        raise RuntimeError(
            "Klikket på 'Luk vindue' blev gennemført, men "
            "Playwright registrerer stadig popup-siden som åben."
        )

    print("✅ Journal-popup'en er lukket.")

    # Sørg for, at den oprindelige side igen er aktiv.
    await original_page.bring_to_front()
    await original_page.wait_for_timeout(500)

    return True


async def _attach_document(
    page: Page,
    document: Path,
    timeout: int,
) -> dict[str, Any]:
    """
    Vedhæfter ét dokument til journalnotatet.

    Uploadformularen åbnes i en separat browser-page. Filen
    sendes direkte til det skjulte input[type='file'], så
    Linux-filvælgeren ikke åbnes.

    Funktionen validerer:
    - at filen stadig findes,
    - at filen ikke er tom,
    - at upload-page åbner,
    - at upload-page har den forventede URL,
    - at filinputtet findes og er aktivt,
    - FileList, hvis uploadformularen stadig eksponerer den,
    - at uploadformularen reagerer på filvalget,
    - at bilagstitlen kan udfyldes,
    - at Vedhæft-knappen kan anvendes,
    - at uploadvinduet lukker,
    - at bilaget bagefter vises på journalnotatsiden.

    FileList er kun en supplerende validering. Schultz-formularen
    kan nulstille eller udskifte input[type='file'], efter at den
    har modtaget filen. Derfor er en tom FileList ikke i sig selv
    en fejl, hvis formularen efterfølgende går videre til den
    forventede tilstand.

    Returns:
        En dictionary med:
        - path: absolut filsti
        - file_name: filnavn med filendelse
        - title: bilagstitel uden FASITs faste præfiks
        - file_size: filstørrelse i bytes
        - file_list_validated: om FileList kunne valideres direkte
    """

    document = document.expanduser().resolve()

    # --------------------------------------------------
    # 1. Kontrollér filen igen umiddelbart før upload
    # --------------------------------------------------
    if not document.is_file():
        raise FileNotFoundError(
            f"Bilaget findes ikke længere: {document}"
        )

    try:
        expected_file_size = document.stat().st_size
    except OSError as error:
        raise OSError(
            f"Kunne ikke læse oplysninger om bilaget: {document}"
        ) from error

    if expected_file_size == 0:
        raise ValueError(
            f"Bilaget er tomt og kan ikke vedhæftes: {document}"
        )

    print(
        f"📎 Vedhæfter fil: {document.name} "
        f"({expected_file_size} bytes)"
    )

    # --------------------------------------------------
    # 2. Find og kontrollér knappen Tilføj
    # --------------------------------------------------
    add_button = page.get_by_role(
        "button",
        name="Tilføj",
        exact=True,
    )

    await expect(add_button).to_be_visible(
        timeout=timeout,
    )
    await expect(add_button).to_be_enabled(
        timeout=timeout,
    )

    # --------------------------------------------------
    # 3. Åbn den separate upload-page
    # --------------------------------------------------
    async with page.context.expect_page(
        timeout=timeout,
    ) as upload_page_info:
        await add_button.click()

    upload_page = await upload_page_info.value

    print(
        "ℹ️ Uploadformular åbnet:",
        upload_page.url,
    )

    # Uploadformularen tilføjer selv præfikset "Bilag -".
    title = document.stem
    file_list_validated = False

    try:
        # --------------------------------------------------
        # 4. Vent på den korrekte uploadformular
        # --------------------------------------------------
        await upload_page.wait_for_load_state(
            "domcontentloaded",
            timeout=timeout,
        )

        await upload_page.wait_for_url(
            "**/DocumentArchive/UploadForm?**",
            timeout=timeout,
        )

        # --------------------------------------------------
        # 5. Find det skjulte filinput
        # --------------------------------------------------
        file_input = upload_page.locator(
            "#uploadbutton"
        ).first

        if await file_input.count() == 0:
            file_input = upload_page.locator(
                "input[type='file']"
            ).first

        await file_input.wait_for(
            state="attached",
            timeout=timeout,
        )

        if not await file_input.is_enabled():
            raise RuntimeError(
                "Filfeltet blev fundet, men det er deaktiveret."
            )

        # --------------------------------------------------
        # 6. Send filen direkte til browseren
        # --------------------------------------------------
        print(
            "ℹ️ Sender filen direkte til uploadfeltet "
            "uden at åbne Linux-filvælgeren..."
        )

        await file_input.set_input_files(
            str(document)
        )

        print(
            "✅ Playwright har sendt filen til uploadfeltet."
        )

        # --------------------------------------------------
        # 7. Supplerende FileList-validering
        # --------------------------------------------------
        #
        # Schultz-formularen kan behandle filen og derefter
        # nulstille eller udskifte input[type='file'].
        #
        # Derfor validerer vi FileList, hvis den stadig findes,
        # men en tom FileList er ikke automatisk en fejl.
        try:
            file_input_after_selection = upload_page.locator(
                "#uploadbutton"
            ).first

            file_list_data = await file_input_after_selection.evaluate(
                """
                (element) => {
                    const files = Array.from(element.files || []);

                    return files.map((file) => ({
                        name: file.name,
                        size: file.size,
                        type: file.type,
                    }));
                }
                """
            )

            if not isinstance(file_list_data, list):
                raise RuntimeError(
                    "Browserens filfelt returnerede ikke en "
                    "gyldig FileList. "
                    f"Modtog: {file_list_data!r}"
                )

            if len(file_list_data) == 1:
                selected_file = file_list_data[0]

                selected_file_name = selected_file.get("name")
                selected_file_size = selected_file.get("size")
                selected_file_type = selected_file.get("type")

                if selected_file_name != document.name:
                    raise RuntimeError(
                        "Browserens filfelt indeholder et forkert "
                        "filnavn. "
                        f"Forventede {document.name!r}, "
                        f"fik {selected_file_name!r}."
                    )

                if not isinstance(selected_file_size, int):
                    raise RuntimeError(
                        "Browserens filfelt returnerede ikke en "
                        "gyldig filstørrelse. "
                        f"Modtog: {selected_file_size!r}."
                    )

                if selected_file_size == 0:
                    raise RuntimeError(
                        "Browserens filfelt indeholder en fil på "
                        "0 bytes. "
                        f"Fil: {selected_file_name!r}."
                    )

                if selected_file_size != expected_file_size:
                    raise RuntimeError(
                        "Filstørrelsen i browserens filfelt svarer "
                        "ikke til filstørrelsen på Ubuntu-serveren. "
                        f"Forventede {expected_file_size} bytes, "
                        f"fik {selected_file_size} bytes."
                    )

                file_list_validated = True

                print(
                    "✅ Browserens FileList er valideret:",
                    {
                        "name": selected_file_name,
                        "size": selected_file_size,
                        "type": selected_file_type,
                    },
                )

            elif len(file_list_data) == 0:
                print(
                    "ℹ️ Uploadformularens FileList er tom efter "
                    "filvalget. Formularen kan have behandlet filen "
                    "og nulstillet filinputtet. Fortsætter med "
                    "validering af formularens næste tilstand."
                )

            else:
                raise RuntimeError(
                    "Filfeltet indeholder mere end én fil, selv om "
                    "der kun blev sendt én fil. "
                    f"Antal filer: {len(file_list_data)}. "
                    f"Indhold: {file_list_data!r}"
                )

        except RuntimeError:
            # Egne valideringsfejl skal fortsat stoppe uploaden.
            raise

        except Exception as file_list_error:
            # Hvis inputelementet blev udskiftet eller fjernet af
            # uploadformularens JavaScript, fortsætter vi med den
            # stærkere efterfølgende formularvalidering.
            print(
                "ℹ️ FileList kunne ikke læses efter filvalget. "
                "Uploadformularen kan have udskiftet filinputtet. "
                "Fortsætter med validering af bilagstitlen. "
                f"Detalje: {type(file_list_error).__name__}: "
                f"{file_list_error}"
            )

        # --------------------------------------------------
        # 8. Validér, at formularen reagerede på filvalget
        # --------------------------------------------------
        title_input = upload_page.locator(
            "#title"
        ).first

        if await title_input.count() == 0:
            title_input = upload_page.locator(
                "input[name='title']"
            ).first

        await title_input.wait_for(
            state="visible",
            timeout=timeout,
        )

        # Diagnostikken viste, at titelfeltet er låst, før
        # der vælges en fil. Når feltet bliver redigerbart,
        # har uploadformularen registreret filvalget.
        await expect(title_input).to_be_editable(
            timeout=timeout,
        )

        print(
            "✅ Uploadformularen har registreret filvalget. "
            "Bilagstitlen er nu redigerbar."
        )

        # --------------------------------------------------
        # 9. Udfyld og validér bilagstitlen
        # --------------------------------------------------
        await title_input.fill(title)

        await expect(title_input).to_have_value(
            title,
            timeout=timeout,
        )

        actual_title = await title_input.input_value()

        if actual_title != title:
            raise RuntimeError(
                "Bilagstitlen blev ikke udfyldt korrekt. "
                f"Forventede {title!r}, fik {actual_title!r}."
            )

        print(
            f"✅ Bilagstitel udfyldt: Bilag - {title}"
        )

        # --------------------------------------------------
        # 10. Find og validér Vedhæft-knappen
        # --------------------------------------------------
        attach_button = upload_page.get_by_role(
            "button",
            name="Vedhæft",
            exact=True,
        )

        await expect(attach_button).to_be_visible(
            timeout=timeout,
        )
        await expect(attach_button).to_be_enabled(
            timeout=timeout,
        )

        # Kontrollér, om uploadsiden viser en synlig fejl,
        # inden der klikkes.
        visible_errors = upload_page.locator(
            ".field-validation-error:visible, "
            ".validation-summary-errors:visible, "
            "[role='alert']:visible"
        )

        if await visible_errors.count() > 0:
            error_messages: list[str] = []

            for index in range(await visible_errors.count()):
                error_element = visible_errors.nth(index)

                try:
                    text = (
                        await error_element.inner_text()
                    ).strip()

                    if text:
                        error_messages.append(text)
                except Exception:
                    continue

            if error_messages:
                raise RuntimeError(
                    "Uploadformularen viser en fejl før upload: "
                    + " | ".join(error_messages)
                )

        # --------------------------------------------------
        # 11. Gennemfør uploaden
        # --------------------------------------------------
        print("ℹ️ Klikker på Vedhæft...")

        async with upload_page.expect_event(
            "close",
            timeout=timeout,
        ):
            await attach_button.click()

        print("✅ Uploadvinduet blev lukket.")

    except Exception as error:
        # --------------------------------------------------
        # 12. Fejldokumentation
        # --------------------------------------------------
        try:
            if not upload_page.is_closed():
                await upload_page.screenshot(
                    path="FEJL_upload_bilag.png",
                    full_page=True,
                )

                print(
                    "📸 Fejlscreenshot gemt: "
                    "FEJL_upload_bilag.png"
                )

        except Exception as screenshot_error:
            print(
                "⚠️ Fejlscreenshot kunne ikke gemmes: "
                f"{type(screenshot_error).__name__}: "
                f"{screenshot_error}"
            )

        raise RuntimeError(
            f"Kunne ikke vedhæfte filen {document.name!r}: "
            f"{type(error).__name__}: {error}"
        ) from error

    # --------------------------------------------------
    # 13. Gå tilbage til journalnotatsiden
    # --------------------------------------------------
    await page.bring_to_front()
    await page.wait_for_timeout(1_000)

    # --------------------------------------------------
    # 14. Validér bilaget på journalnotatsiden
    # --------------------------------------------------
    attachment_row = page.get_by_role(
        "row"
    ).filter(
        has_text=document.name
    ).first

    try:
        await attachment_row.wait_for(
            state="visible",
            timeout=timeout,
        )

        await expect(attachment_row).to_contain_text(
            document.name,
            timeout=timeout,
        )

        print(
            "✅ Bilaget kan ses på journalnotatet:",
            document.name,
        )

    except Exception:
        # Nogle visninger viser bilagstitlen i stedet for
        # det oprindelige filnavn.
        attachment_row = page.get_by_role(
            "row"
        ).filter(
            has_text=title
        ).first

        await attachment_row.wait_for(
            state="visible",
            timeout=timeout,
        )

        await expect(attachment_row).to_contain_text(
            title,
            timeout=timeout,
        )

        print(
            "✅ Bilaget kan ses via bilagstitlen:",
            title,
        )

    return {
        "path": str(document),
        "file_name": document.name,
        "title": title,
        "file_size": expected_file_size,
        "file_list_validated": file_list_validated,
    }


async def nyt_journalnotat(
    page: Page,
    session,
    *,
    documents: Collection[str | Path] | None = None,
    titel: str,
    sag: str,
    notattype: str,
    kilde: str,
    notat: str,
    haendelsesdato: str,
    haendelsestidspunkt: str,
    citizen_id: str,
    brevets_datering: str | None = None,
    opret_advis: bool = False,
    timeout: int = 20_000,
) -> dict[str, Any]:
    """Opretter et nyt journalnotat og vedhæfter alle angivne dokumenter."""
    titel = _required_text(titel, "titel")
    sag = _required_text(sag, "sag")
    notattype = _required_text(notattype, "notattype")
    kilde = _required_text(kilde, "kilde")
    notat = _required_text(notat, "notat")
    citizen_id = _required_text(citizen_id, "citizen_id")
    haendelsesdato = _validate_date(haendelsesdato, "haendelsesdato")
    haendelsestidspunkt = _validate_time(haendelsestidspunkt, "haendelsestidspunkt")
    brevets_datering = _validate_date(brevets_datering, "brevets_datering")
    if not isinstance(opret_advis, bool):
        raise TypeError("opret_advis skal være True eller False.")
    document_paths = _normalise_documents(documents)

    url = JOURNAL_URL_TEMPLATE.format(citizen_id=citizen_id)

    await page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=timeout,
    )

    await wait_for_page_ready(page)

    popup_closed = await _close_initial_popup(
        page=page,
        session=session,
        timeout=timeout,
    )

    print(f"Popup lukket: {popup_closed}")

    await page.bring_to_front()
    await wait_for_page_ready(page)

    await _fill_and_validate(await _field(page, "Titel", timeout), titel, "Titel")
    selected_case = await _select_combobox(page, "Sag", sag, timeout, starts_with=True)
    selected_note_type = await _select_combobox(page, "Notattype", notattype, timeout)
    selected_source = await _select_combobox(page, "Kilde", kilde, timeout)
    await _fill_and_validate(await _field(page, "Notat", timeout), notat, "Notat")
    await _fill_and_validate(
        await _field(page, "Hændelsesdato", timeout), haendelsesdato, "Hændelsesdato"
    )
    await _fill_and_validate(
        await _field(page, "Hændelsestidspunkt", timeout),
        haendelsestidspunkt,
        "Hændelsestidspunkt",
    )
    if brevets_datering is not None:
        await _fill_and_validate(
            await _field(page, "Brevets datering", timeout),
            brevets_datering,
            "Brevets datering",
        )

    expected_advis = "Ja" if opret_advis else "Nej"
    advis = page.get_by_role("radio", name=expected_advis, exact=True)
    if not await advis.count():
        advis = page.get_by_label(expected_advis, exact=True)
    if not await advis.is_checked():
        await advis.check()
    await expect(advis).to_be_checked()

    attachments = []
    for document in document_paths:
        attachments.append(await _attach_document(page, document, timeout))

    await session.screenshot(page, "journalnotat_klar_til_oprettelse", always=True)
    # Funktionen stopper før den endelige Opret-notat-knap, fordi brugerens beskrevne
    # flow slutter efter bilagsvalideringen. Tilføj først klik, når knapteksten er
    # verificeret i det konkrete FASIT-miljø.
    return {
        "status": "ready_to_create",
        "journal_created": False,
        "attachment_count": len(attachments),
    }
