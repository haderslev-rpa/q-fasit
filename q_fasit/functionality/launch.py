from q_haderslev_vbo.playwright.faelles_kommunal_login_idp import (
    login_via_faelles_kommunal_idp
)

from q_fasit.fselectors import FasitSelectors as S
from q_fasit.utils import wait_for_page_ready


async def launch_fasit(page, session, credential_name):

    FASIT_URL = "https://login.fasit.dk/haderslev/kombit"
    FASIT_STARTSIDE_URL = "https://haderslev.schultzfasit.dk/"

    print("🌐 Går til FASIT...")

    try:
        # --------------------------------------------------
        # ✅ STEP 1: Gå til startside
        # --------------------------------------------------
        await page.goto(FASIT_URL)
        await page.wait_for_load_state("domcontentloaded")

        # Screenshot før login-check
        await session.screenshot(page, "STEP_1_startside")

        # --------------------------------------------------
        # ✅ STEP 2: Tjek login
        # --------------------------------------------------
        if await page.locator(S.AUTH_DROPDOWN).count() > 0:

            print("🔐 Ikke logget ind – starter login")

            # Vælg kommune
            await page.locator(S.AUTH_DROPDOWN).select_option(
                label=S.MUNICIPALITY
            )

            # Klik OK
            await page.locator(S.OK_BUTTON).click()
            await wait_for_page_ready(page)

            # Screenshot efter kommunevalg
            await session.screenshot(page, "STEP_2_kommune_valgt")

            # --------------------------------------------------
            # ✅ STEP 3: Login via fælles kommunal IDP
            # --------------------------------------------------
            await login_via_faelles_kommunal_idp(
                page=page,
                session=session,
                credential_name=credential_name,
            )

            # --------------------------------------------------
            # ✅ STEP 4: Reload efter login og vent på startside
            # --------------------------------------------------

            # 1. Vent på korrekt URL (adresse)
            await page.wait_for_url("**haderslev.schultzfasit.dk/**")

            # 2. Vent på netværk er færdigt
            await page.wait_for_load_state("networkidle")

            # 3. Vent på header (UI klar)
            await page.locator(S.APP_HEADER).wait_for(state="visible")

            # 4. Ekstra stabilisering (lille buffer)
            await page.wait_for_timeout(1000)

            # 5. Din egen helper
            await wait_for_page_ready(page)

            await session.screenshot(page, "STEP_4_startside_klar")

        else:
            print("✅ Allerede logget ind")

            # Screenshot hvis allerede logget ind
            await session.screenshot(page, "STEP_2_allerede_logget_ind")

        print("✅ FASIT klar:", page.url)

    except Exception as e:
        # --------------------------------------------------
        # ❌ FEJL
        # --------------------------------------------------
        await session.screenshot(page, "FEJL_launch_fasit")
        raise e