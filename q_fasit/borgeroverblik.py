from q_fasit.fselectors import BorgerOverblikSelectors as S
from q_fasit.utils import wait_for_page_ready


async def bo_kommunens_markeringer(page, session, tekst: str, timeout: int = 20000):

    print("🚀 Starter Kommunens markeringer...")

    try:
        # --------------------------------------------------
        # ✅ STEP 1: Klargør side
        # --------------------------------------------------
        await wait_for_page_ready(page)
        await page.wait_for_timeout(1000)

        await session.recorder.screenshot(page, "STEP_1_side_klar")

        # --------------------------------------------------
        # ✅ STEP 2: Åbn "Kommunens markeringer"
        # --------------------------------------------------
        container = page.locator(f"xpath={S.CONTAINER}").first
        await container.wait_for(state="visible", timeout=timeout)

        await container.scroll_into_view_if_needed()
        await container.click()
        await page.wait_for_timeout(1000)

        await session.recorder.screenshot(page, "STEP_2_container_aabnet")

        # --------------------------------------------------
        # ✅ STEP 3: Klik "Redigér"
        # --------------------------------------------------
        rediger = page.locator(f"xpath={S.REDIGER}").first
        await rediger.wait_for(state="visible", timeout=timeout)

        await rediger.click()
        await page.wait_for_timeout(1000)

        await session.recorder.screenshot(page, "STEP_3_rediger")

        # --------------------------------------------------
        # ✅ STEP 4: Indtast note
        # --------------------------------------------------
        note = page.locator(f"xpath={S.IMPORTANT_NOTE2}").first
        await note.wait_for(state="visible", timeout=timeout)
        await note.fill(tekst)

        await session.recorder.screenshot(page, "STEP_4_note_indtastet")

        # --------------------------------------------------
        # ✅ STEP 5: Gem ændringer
        # --------------------------------------------------
        gem = page.locator(f"xpath={S.GEM}").first
        await gem.wait_for(state="visible", timeout=timeout)

        await gem.click()
        await page.wait_for_timeout(1000)

        await wait_for_page_ready(page)

        await session.recorder.screenshot(page, "STEP_5_gemt")

    except Exception as e:
        # --------------------------------------------------
        # ❌ FEJL
        # --------------------------------------------------
        await session.recorder.screenshot(page, "FEJL_borgeroverblik")
        raise e