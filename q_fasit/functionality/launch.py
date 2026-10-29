from playwright.async_api import Page

from q_haderslev_vbo.playwright.faelles_kommunal_login_idp import (
    login_via_faelles_kommunal_idp,
)
from q_fasit.fselectors import FasitSelectors as S
from q_fasit.utils import wait_for_page_ready


FASIT_URL = "https://login.fasit.dk/haderslev/kombit"

FASIT_STARTSIDE_URL_PATTERN = (
    "**haderslev.schultzfasit.dk/**"
)

MESSAGE_CENTER_CLOSE_SELECTOR = (
    "button[data-vanguard='message-center-dismiss-button']"
)

MESSAGE_CENTER_DRAWER_SELECTOR = (
    ".MuiDrawer-paperAnchorRight"
)


async def _close_message_center(
    page: Page,
    session,
    timeout: int = 10_000,
) -> bool:
    """
    Lukker FASITs meddelelsescenter, hvis det vises efter login.

    Meddelelsescenteret er en højrestillet MUI Drawer. Funktionen
    bruger den stabile data-vanguard-attribut på lukkeknappen
    frem for de dynamiske MUI CSS-klasser.

    Args:
        page:
            Den aktive FASIT-side.

        session:
            BrowserSession, som bruges til screenshot ved fejl.

        timeout:
            Maksimal ventetid i millisekunder, når popupen findes.

    Returns:
        True:
            Meddelelsescenteret blev fundet og lukket.

        False:
            Meddelelsescenteret blev ikke vist.

    Raises:
        RuntimeError:
            Hvis meddelelsescenteret findes, men ikke kan lukkes.
    """

    if page.is_closed():
        raise RuntimeError(
            "FASIT-siden er lukket, så meddelelsescenteret "
            "kan ikke undersøges."
        )

    close_button = page.locator(
        MESSAGE_CENTER_CLOSE_SELECTOR
    ).first

    # Meddelelsescenteret bliver muligvis renderet lidt efter,
    # at resten af FASIT-siden er blevet synlig.
    try:
        await close_button.wait_for(
            state="visible",
            timeout=min(timeout, 5_000),
        )
    except Exception:
        print(
            "ℹ️ FASITs meddelelsescenter blev ikke vist."
        )
        return False

    print(
        "ℹ️ FASITs meddelelsescenter er åbent. "
        "Lukker det..."
    )

    # Kontrollér, at den fundne knap er den forventede knap.
    aria_label = await close_button.get_attribute(
        "aria-label"
    )
    title = await close_button.get_attribute(
        "title"
    )
    data_vanguard = await close_button.get_attribute(
        "data-vanguard"
    )

    if data_vanguard != "message-center-dismiss-button":
        raise RuntimeError(
            "Der blev fundet en uventet knap til lukning af "
            "meddelelsescenteret. "
            f"data-vanguard={data_vanguard!r}, "
            f"aria-label={aria_label!r}, "
            f"title={title!r}."
        )

    drawer = page.locator(
        MESSAGE_CENTER_DRAWER_SELECTOR
    ).filter(
        has=close_button
    ).first

    try:
        await close_button.scroll_into_view_if_needed()

        try:
            await close_button.click(
                timeout=5_000,
            )
        except Exception as normal_click_error:
            print(
                "⚠️ Normalt klik på 'Luk meddelelser' "
                "fejlede. Forsøger et tvunget klik. "
                f"Fejl: {normal_click_error}"
            )

            await close_button.click(
                force=True,
                timeout=5_000,
            )

        # MUI Drawer kan blive fjernet fra DOM'en eller blot
        # blive skjult efter sin lukkeanimation.
        if await drawer.count() > 0:
            try:
                await drawer.wait_for(
                    state="hidden",
                    timeout=timeout,
                )
            except Exception:
                # Ved nogle React-renderinger bliver drawerens
                # indhold genopbygget. Kontrollér derfor knappen
                # direkte som ekstra validering.
                await close_button.wait_for(
                    state="hidden",
                    timeout=timeout,
                )
        else:
            await close_button.wait_for(
                state="hidden",
                timeout=timeout,
            )

        # Ekstra kontrol efter animationen.
        await page.wait_for_timeout(300)

        if (
            await close_button.count() > 0
            and await close_button.is_visible()
        ):
            raise RuntimeError(
                "Knappen 'Luk meddelelser' er stadig synlig "
                "efter klik."
            )

        print(
            "✅ FASITs meddelelsescenter er lukket."
        )
        return True

    except Exception as error:
        try:
            await session.screenshot(
                page,
                "FEJL_meddelelsescenter_kunne_ikke_lukkes",
                always=True,
            )
        except Exception as screenshot_error:
            print(
                "⚠️ Screenshot af meddelelsescenteret "
                "kunne ikke gemmes: "
                f"{type(screenshot_error).__name__}: "
                f"{screenshot_error}"
            )

        raise RuntimeError(
            "FASITs meddelelsescenter blev fundet, "
            "men kunne ikke lukkes. "
            f"Fejltype: {type(error).__name__}. "
            f"Fejl: {error}"
        ) from error


async def launch_fasit(
    page: Page,
    session,
    credential_name: str,
) -> None:
    """
    Åbner FASIT og gennemfører login, hvis det er nødvendigt.

    Efter login:
    - ventes der på FASITs startside,
    - app-headeren valideres,
    - meddelelsescenteret lukkes, hvis det vises,
    - der tages screenshot af den færdige startside.

    Args:
        page:
            Den aktive Playwright-side.

        session:
            BrowserSession med context og screenshot-funktion.

        credential_name:
            Navnet på credentialen til fælleskommunalt login.

    Returns:
        Funktionen returnerer ikke en værdi. Ved succes står
        page på en klar FASIT-side uden åbent meddelelsescenter.
    """

    print("🌐 Går til FASIT...")

    try:
        # --------------------------------------------------
        # STEP 1: Gå til FASITs login/startside
        # --------------------------------------------------
        await page.goto(
            FASIT_URL,
            wait_until="domcontentloaded",
        )

        await session.screenshot(
            page,
            "STEP_1_startside",
        )

        # --------------------------------------------------
        # STEP 2: Gennemfør login, hvis loginvalget vises
        # --------------------------------------------------
        auth_dropdown = page.locator(
            S.AUTH_DROPDOWN
        )

        if await auth_dropdown.count() > 0:
            print(
                "🔐 Ikke logget ind – starter login"
            )

            await auth_dropdown.select_option(
                label=S.MUNICIPALITY,
            )

            await page.locator(
                S.OK_BUTTON
            ).click()

            await wait_for_page_ready(page)

            await session.screenshot(
                page,
                "STEP_2_kommune_valgt",
            )

            # ----------------------------------------------
            # STEP 3: Fælleskommunalt login
            # ----------------------------------------------
            await login_via_faelles_kommunal_idp(
                page=page,
                session=session,
                credential_name=credential_name,
            )

        else:
            print("✅ Allerede logget ind")

            await session.screenshot(
                page,
                "STEP_2_allerede_logget_ind",
            )

        # --------------------------------------------------
        # STEP 4: Vent på FASITs rigtige startside
        # --------------------------------------------------
        await page.wait_for_url(
            FASIT_STARTSIDE_URL_PATTERN,
            timeout=60_000,
        )

        await page.wait_for_load_state(
            "domcontentloaded",
        )

        # networkidle kan være nyttig i FASIT, men må ikke
        # få launch til at fejle permanent, hvis siden har
        # løbende baggrundskald.
        try:
            await page.wait_for_load_state(
                "networkidle",
                timeout=20_000,
            )
        except Exception:
            print(
                "ℹ️ FASIT nåede ikke networkidle, "
                "men launch fortsætter med UI-validering."
            )

        await page.locator(
            S.APP_HEADER
        ).wait_for(
            state="visible",
            timeout=30_000,
        )

        await wait_for_page_ready(page)

        # Giv React/MUI kort tid til at vise eventuelle
        # meddelelser efter resten af appen er klar.
        await page.wait_for_timeout(500)

        # --------------------------------------------------
        # STEP 5: Luk FASITs meddelelsescenter
        # --------------------------------------------------
        message_center_was_closed = (
            await _close_message_center(
                page=page,
                session=session,
                timeout=10_000,
            )
        )

        if message_center_was_closed:
            await session.screenshot(
                page,
                "STEP_5_meddelelsescenter_lukket",
            )

        # --------------------------------------------------
        # STEP 6: Endelig validering
        # --------------------------------------------------
        await page.locator(
            S.APP_HEADER
        ).wait_for(
            state="visible",
            timeout=10_000,
        )

        visible_close_button = page.locator(
            MESSAGE_CENTER_CLOSE_SELECTOR
        ).filter(
            visible=True
        )

        if await visible_close_button.count() > 0:
            raise RuntimeError(
                "FASITs meddelelsescenter er stadig åbent "
                "efter launch."
            )

        await session.screenshot(
            page,
            "STEP_6_fasit_klar",
        )

        print("✅ FASIT klar:", page.url)

    except Exception as error:
        try:
            await session.screenshot(
                page,
                "FEJL_launch_fasit",
                always=True,
            )
        except Exception as screenshot_error:
            print(
                "⚠️ Fejlscreenshot fra launch kunne ikke gemmes: "
                f"{type(screenshot_error).__name__}: "
                f"{screenshot_error}"
            )

        raise