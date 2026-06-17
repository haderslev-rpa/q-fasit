from q_fasit.fselectors import FremsoegBorgerSelectors as S
from q_fasit.utils import (
    wait_for_page_ready,
    normalize_cpr,
    extract_cpr_from_text,
    click_and_handle_tabs_strict,
)


async def fremsoeg_borger(page, session, cpr: str):

    print("🚀 Starter fremsøg borger...")

    try:
        # --------------------------------------------------
        # ✅ STEP 1: Klargør side + CPR
        # --------------------------------------------------
        cpr = normalize_cpr(cpr)

        await wait_for_page_ready(page)
        await session.recorder.screenshot(page, "STEP_1_klar_til_soegning")

        # --------------------------------------------------
        # ✅ STEP 2: Åbn søgefelt
        # --------------------------------------------------
        target_btn = page.locator(f"xpath={S.TARGET_BUTTON}")
        await target_btn.wait_for(state="visible", timeout=15000)
        await target_btn.click()

        await page.wait_for_selector(
            S.SEARCH_INPUT,
            state="visible",
            timeout=15000
        )

        await session.recorder.screenshot(page, "STEP_2_soegefelt")

        # --------------------------------------------------
        # ✅ STEP 3: Indtast CPR og søg
        # --------------------------------------------------
        search_input = page.locator(f"xpath={S.SEARCH_INPUT}")
        await search_input.fill(cpr)
        await page.keyboard.press("Enter")

        await wait_for_page_ready(page)

        # --------------------------------------------------
        # ✅ STEP 4: Valider søgeresultat
        # --------------------------------------------------
        result = page.locator(f"xpath={S.RESULT_HEADER}")
        await result.wait_for(state="visible", timeout=15000)

        text = await result.inner_text()
        found_cpr = extract_cpr_from_text(text)

        if found_cpr != cpr:
            await session.recorder.screenshot(page, "FEJL_cpr")
            raise RuntimeError("❌ CPR matcher ikke")

        # --------------------------------------------------
        # ✅ STEP 5: Åbn borger
        # --------------------------------------------------
        result_button = page.locator(f"xpath={S.result_button(cpr)}")
        await result_button.wait_for(state="visible", timeout=15000)

        new_page = await click_and_handle_tabs_strict(
            page=page,
            session=session,
            locator=result_button,
        )

        # --------------------------------------------------
        # ✅ STEP 6: Luk andre faner
        # --------------------------------------------------
        await session.close_other_pages(new_page)

        # --------------------------------------------------
        # ✅ STEP 7: Stabiliser borger-side
        # --------------------------------------------------
        await wait_for_page_ready(new_page)
        await new_page.wait_for_timeout(1500)

        await session.recorder.screenshot(
            new_page,
            "STEP_3_borger_aabnet"
        )

        print(f"✅ page URL: {page.url}")
        print(f"✅ new_page URL: {new_page.url}")

        return new_page

    except Exception as e:
        # --------------------------------------------------
        # ❌ FEJL
        # --------------------------------------------------
        await session.recorder.screenshot(page, "FEJL_fremsoeg_borger")
        raise e
