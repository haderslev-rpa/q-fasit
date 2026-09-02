from datetime import date, datetime
from typing import Optional, Union

from playwright.async_api import Page

from q_fasit.fselectors import (
    BorgerOverblikSelectors as S,
    JournalSelectors as JS,
)
from q_fasit.models import JournalOgDokumenterRow
from q_fasit.utils import wait_for_page_ready


DatoType = Union[str, date, datetime]


def _formater_dato(dato: DatoType) -> str:
    if isinstance(dato, datetime):
        return dato.strftime("%d-%m-%Y")

    if isinstance(dato, date):
        return dato.strftime("%d-%m-%Y")

    return dato.strip()


async def hent_Journal_og_dokumenter_table(
    page,
    timeout: int = 20000,
) -> list:
    print("🚀 Henter Journal & Dokumenter tabel...")

    await wait_for_page_ready(page)

    rows = page.locator(JS.ROWS)

    await rows.first.wait_for(
        state="visible",
        timeout=timeout,
    )

    antal = await rows.count()

    resultater: list[JournalOgDokumenterRow] = []

    for i in range(antal):
        row = rows.nth(i)

        try:
            titel = (
                await row
                .locator(JS.TITLE)
                .inner_text()
            ).strip()

            notattype = (
                await row
                .locator(JS.CONTENT_TYPE)
                .inner_text()
            ).strip()

            haendelsestidspunkt = (
                await row
                .locator(JS.EVENT_DATE)
                .inner_text()
            ).strip()

            registreringstidspunkt = (
                await row
                .locator(JS.CREATED_AT)
                .inner_text()
            ).strip()

            sag = (
                await row
                .locator(JS.CASE_NAME)
                .inner_text()
            ).strip()

            kilde = (
                await row
                .locator(JS.SOURCE_NAME)
                .inner_text()
            ).strip()

            oprettet_af = (
                await row
                .locator(JS.CREATED_BY)
                .inner_text()
            ).strip()

            har_bilag = (
                await row
                .locator(JS.ATTACHMENTS)
                .inner_text()
            ).strip()

            resultater.append(
                JournalOgDokumenterRow(
                    titel=titel,
                    notattype=notattype,
                    haendelsestidspunkt=haendelsestidspunkt,
                    registreringstidspunkt=registreringstidspunkt,
                    sag=sag,
                    kilde=kilde,
                    oprettet_af=oprettet_af,
                    har_bilag=(
                        har_bilag.lower() == "ja"
                    ),
                )
            )

        except Exception as e:
            print(
                f"⚠️ Kunne ikke læse række {i}: {e}"
            )

    print(
        f"✅ Hentede {len(resultater)} journalposter"
    )

    return resultater


async def bo_kommunens_markeringer(
    page,
    session,
    tekst: str,
    timeout: int = 20000,
):
    print("🚀 Starter Kommunens markeringer...")

    try:
        # --------------------------------------------------
        # ✅ STEP 1: Klargør side
        # --------------------------------------------------
        await wait_for_page_ready(page)
        await page.wait_for_timeout(1000)

        await session.screenshot(page, "STEP_1_side_klar")

        # --------------------------------------------------
        # ✅ STEP 2: Åbn "Kommunens markeringer"
        # --------------------------------------------------
        container = page.locator(f"xpath={S.CONTAINER}").first
        await container.wait_for(state="visible", timeout=timeout)

        await container.scroll_into_view_if_needed()
        await container.click()
        await page.wait_for_timeout(1000)

        await session.screenshot(page, "STEP_2_container_aabnet")

        # --------------------------------------------------
        # ✅ STEP 3: Klik "Redigér"
        # --------------------------------------------------
        rediger = page.locator(f"xpath={S.REDIGER}").first
        await rediger.wait_for(state="visible", timeout=timeout)

        await rediger.click()
        await page.wait_for_timeout(1000)

        await session.screenshot(page, "STEP_3_rediger")

        # --------------------------------------------------
        # ✅ STEP 4: Indtast note
        # --------------------------------------------------
        note = page.locator(f"xpath={S.IMPORTANT_NOTE2}").first
        await note.wait_for(state="visible", timeout=timeout)
        await note.fill(tekst)

        await session.screenshot(page, "STEP_4_note_indtastet")

        # --------------------------------------------------
        # ✅ STEP 5: Gem ændringer
        # --------------------------------------------------
        gem = page.locator(f"xpath={S.GEM}").first
        await gem.wait_for(state="visible", timeout=timeout)

        await gem.click()
        await page.wait_for_timeout(1000)

        await wait_for_page_ready(page)

        await session.screenshot(page, "STEP_5_gemt")

    except Exception as e:
        # --------------------------------------------------
        # ❌ FEJL
        # --------------------------------------------------
        await session.screenshot(page, "FEJL_borgeroverblik")
        raise e


async def bo_opret_persongruppemarkering(
    page: Page,
    session,
    persongruppe: str,
    startdato: DatoType,
    slutdato: Optional[DatoType] = None,
    timeout: int = 20000,
):
    print("🚀 Starter oprettelse af persongruppemarkering...")

    try:
        # --------------------------------------------------
        # ✅ STEP 1: Klargør side
        # --------------------------------------------------
        await wait_for_page_ready(page)
        await page.wait_for_timeout(1000)

        await session.screenshot(
            page,
            "PERSONGRUPPE_STEP_1_side_klar",
        )

        # --------------------------------------------------
        # ✅ STEP 2: Find Persongruppemarkeringer
        # --------------------------------------------------
        container = page.locator(
            f"xpath={S.PERSONGRUPPEMARKERINGER_CONTAINER}"
        ).first

        await container.wait_for(
            state="visible",
            timeout=timeout,
        )

        await container.scroll_into_view_if_needed()

        # --------------------------------------------------
        # ✅ STEP 3: Åbn Persongruppemarkeringer
        # --------------------------------------------------
        ny_persongruppemarkering = container.locator(
            f"xpath={S.PERSONGRUPPEMARKERINGER_NY_CONTAINER}"
        ).first

        if not await ny_persongruppemarkering.is_visible():
            await container.click()
            await page.wait_for_timeout(1000)

        await ny_persongruppemarkering.wait_for(
            state="visible",
            timeout=timeout,
        )

        await session.screenshot(
            page,
            "PERSONGRUPPE_STEP_2_container_aabnet",
        )

        # --------------------------------------------------
        # ✅ STEP 4: Klik på ny persongruppemarkering
        # --------------------------------------------------
        await ny_persongruppemarkering.click()

        await page.wait_for_timeout(1000)

        await session.screenshot(
            page,
            "PERSONGRUPPE_STEP_3_formular_aabnet",
        )

        # --------------------------------------------------
        # ✅ STEP 5: Indtast persongruppe
        # --------------------------------------------------
        persongruppe_input = page.locator(
            f"xpath={S.PERSONGRUPPE_INPUT}"
        ).first

        await persongruppe_input.wait_for(
            state="visible",
            timeout=timeout,
        )

        await persongruppe_input.fill(
            persongruppe
        )

        # --------------------------------------------------
        # ✅ STEP 6: Vælg persongruppe fra listen
        # --------------------------------------------------
        persongruppe_mulighed = page.locator(
            f"xpath={S.persongruppe_mulighed(persongruppe)}"
        ).first

        await persongruppe_mulighed.wait_for(
            state="visible",
            timeout=timeout,
        )

        await persongruppe_mulighed.click()

        # --------------------------------------------------
        # ✅ STEP 7: Indtast startdato
        # --------------------------------------------------
        startdato_input = page.locator(
            f"xpath={S.PERSONGRUPPE_STARTDATO_INPUT}"
        ).first

        await startdato_input.wait_for(
            state="visible",
            timeout=timeout,
        )

        await startdato_input.fill(
            _formater_dato(startdato)
        )

        await startdato_input.press("Tab")

        # --------------------------------------------------
        # ✅ STEP 8: Indtast eventuel slutdato
        # --------------------------------------------------
        if slutdato is not None:
            slutdato_input = page.locator(
                f"xpath={S.PERSONGRUPPE_SLUTDATO_INPUT}"
            ).first

            await slutdato_input.wait_for(
                state="visible",
                timeout=timeout,
            )

            await slutdato_input.fill(
                _formater_dato(slutdato)
            )

            await slutdato_input.press("Tab")

        await session.screenshot(
            page,
            "PERSONGRUPPE_STEP_4_formular_udfyldt",
        )

        # --------------------------------------------------
        # ✅ STEP 9: Klik Gem og luk
        # --------------------------------------------------
        gem_og_luk = page.locator(
            f"xpath={S.PERSONGRUPPE_GEM_OG_LUK}"
        ).first

        await gem_og_luk.wait_for(
            state="visible",
            timeout=timeout,
        )

        await gem_og_luk.click()

        await page.wait_for_timeout(1000)

        await session.screenshot(
            page,
            "PERSONGRUPPE_STEP_5_gemt",
        )

        print(
            "✅ Persongruppemarkeringen er oprettet"
        )

    except Exception:
        await session.screenshot(
            page,
            "FEJL_opret_persongruppemarkering",
        )

        raise