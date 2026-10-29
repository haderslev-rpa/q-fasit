import asyncio
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# .env bruges kun af Automation Server-klienten til ATS_URL og ATS_TOKEN.
# Selve testdataene nedenfor er hardkodede i denne testfil.
load_dotenv()

from q_fasit.functionality.journal_og_dokumenter_opret import nyt_journalnotat
from q_fasit.functionality.launch import launch_fasit
from q_haderslev_vbo.playwright.browser_session import BrowserSession


CITIZEN_ID = "14179f7c-4997-42a1-9a78-86b7d48953de"
CREDENTIAL_NAME = "DIRXOPS"

TITEL = "Test af nyt journalnotat"
SAG = "Dagpenge - 02-07-2026"
NOTATTYPE = "Dokument"
KILDE = "Ikke angivet"
NOTAT = "Dette er et testnotat oprettet via Playwright-testen."
OPRET_ADVIS = False

# True:
# Browseren bliver stående ved fejl, indtil du trykker Enter.
#
# False:
# Browseren lukkes straks ved fejl.
BEHOLD_BROWSER_VED_FEJL = True

# Testfilen ligger i samme mappe som denne Python-test.
PDF_PATH = Path(__file__).resolve().parent / "Robot test.pdf"


async def vent_paa_enter_foer_browser_lukkes() -> None:
    """
    Holder testen og browseren åbne, indtil brugeren trykker Enter.

    input() er en blokkerende funktion. asyncio.to_thread() sørger for,
    at den køres uden at blokere asyncio event loop direkte.
    """
    print()
    print("=" * 70)
    print("⏸️  Browseren bliver stående åben, så du kan undersøge fejlen.")
    print("    Tryk Enter i terminalen, når browseren må lukkes.")
    print("=" * 70)

    try:
        await asyncio.to_thread(
            input,
            "\nTryk Enter for at lukke browseren: ",
        )
    except (EOFError, KeyboardInterrupt):
        print()
        print("⚠️ Input blev afbrudt. Browseren lukkes nu.")


async def main() -> None:
    """Kører en rigtig Playwright-integrationstest af nyt_journalnotat."""
    if not PDF_PATH.is_file():
        raise FileNotFoundError(
            "Test-PDF'en blev ikke fundet. Forventet placering: "
            f"{PDF_PATH}"
        )

    session = BrowserSession(
        headless=False,
        debug=True,
        video=True,
    )

    test_error: BaseException | None = None
    session_started = False
    page = None

    try:
        await session.start()
        session_started = True

        page = await session.new_page()

        print("1. Launcher FASIT og logger ind...")
        await launch_fasit(
            page=page,
            session=session,
            credential_name=CREDENTIAL_NAME,
        )

        await session.screenshot(
            page,
            "01_fasit_launch_gennemfoert",
            always=True,
        )

        print("2. Kontrollerer den hardkodede test-PDF...")
        print(f"   PDF: {PDF_PATH}")

        now = datetime.now()

        print("3. Opretter og udfylder nyt journalnotat...")
        result = await nyt_journalnotat(
            page=page,
            session=session,
            documents=[PDF_PATH],
            titel=TITEL,
            sag=SAG,
            notattype=NOTATTYPE,
            kilde=KILDE,
            notat=NOTAT,
            haendelsesdato=now.strftime("%d-%m-%Y"),
            haendelsestidspunkt=now.strftime("%H:%M"),
            citizen_id=CITIZEN_ID,
            brevets_datering=None,
            opret_advis=OPRET_ADVIS,
        )

        if result.get("ready_to_create") is not True:
            raise AssertionError(
                "Journalnotatet blev ikke meldt klar til oprettelse."
            )

        attachments = result.get("attachments")

        if not isinstance(attachments, list) or len(attachments) != 1:
            raise AssertionError(
                "Testen forventede præcis ét valideret bilag."
            )

        print("✅ Testen blev gennemført.")
        print(f"   Klar til oprettelse: {result['ready_to_create']}")
        print(f"   Antal bilag: {len(attachments)}")
        print(f"   Bilag: {PDF_PATH.name}")

        await session.screenshot(
            page,
            "02_nyt_journalnotat_klar",
            always=True,
        )

    except BaseException as error:
        # Gem fejlen, så browseren kan forblive åben, før fejlen genkastes.
        test_error = error

        print()
        print("❌ Testen fejlede.")
        print(f"   Fejltype: {type(error).__name__}")
        print(f"   Fejltekst: {error}")

        try:
            if page is not None and not page.is_closed():
                await session.screenshot(
                    page,
                    "FEJL_nyt_journalnotat",
                    always=True,
                )
                print("📸 Fejlscreenshot er gemt.")
        except Exception as screenshot_error:
            print(
                "⚠️ Fejlscreenshot kunne ikke gemmes: "
                f"{screenshot_error}"
            )

        # Browser-sessionen er stadig aktiv på dette tidspunkt.
        if (
            BEHOLD_BROWSER_VED_FEJL
            and session_started
            and page is not None
            and not page.is_closed()
        ):
            await vent_paa_enter_foer_browser_lukkes()

    finally:
        if session_started:
            print("Lukker browser-sessionen...")
            await session.close()
            print("Browser-sessionen er lukket.")

    # Genkast først fejlen, efter browseren er undersøgt og lukket.
    if test_error is not None:
        raise test_error


if __name__ == "__main__":
    asyncio.run(main())