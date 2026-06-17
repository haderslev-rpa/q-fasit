import asyncio
from dotenv import load_dotenv
import os
from playwright.async_api import async_playwright
# ✅ Load env (fixer ATS_URL)
load_dotenv()
from q_fasit.launch import launch_fasit
from q_fasit.fremsoeg_borger import fremsoeg_borger
from q_fasit.borgeroverblik import bo_kommunens_markeringer


async def test_kommunens_markeringer():

    print("🚀 Starter test af Kommunens markeringer...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,  # ✅ kan sættes til False ved debugging
            args=["--start-maximized"],
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            ignore_https_errors=True,
            locale="da-DK",
        )

        page = await context.new_page()

        # --------------------------------------------------
        # ✅ Session (samme setup som dine andre tests)
        # --------------------------------------------------
        class Session:
            def __init__(self, context):
                self.context = context

            async def close_other_pages(self, keep_page):
                for p in self.context.pages:
                    if p != keep_page:
                        await p.close()

            class Recorder:
                async def screenshot(self, page, name):
                    try:
                        await page.screenshot(path=f"{name}.png")
                    except Exception:
                        print(f"⚠️ Screenshot fejlede: {name}")

            recorder = Recorder()

        session = Session(context)

        # --------------------------------------------------
        # ✅ 1) Launch FASIT
        # --------------------------------------------------
        await launch_fasit(
            page=page,
            session=session,
            credential_name="DIRXOPS",  # ✅ tilpas hvis nødvendigt
        )

        # --------------------------------------------------
        # ✅ 2) Fremsøg borger
        # --------------------------------------------------
        new_page = await fremsoeg_borger(
            page=page,
            session=session,
            cpr=os.getenv("test_cpr"),  # ✅ brug en gyldig testborger
        )

        # --------------------------------------------------
        # ✅ 🔥 KRITISK: Stabilisering før UI handling
        # --------------------------------------------------
        print("⏳ Venter på at borger-side bliver stabil...")

        await new_page.wait_for_load_state("domcontentloaded")
        await new_page.wait_for_load_state("networkidle")

        # ekstra buffer (React/MUI rendering)
        await new_page.wait_for_timeout(2000)

        await session.recorder.screenshot(new_page, "DEBUG_efter_borger_aabnet")

        # --------------------------------------------------
        # ✅ 3) Indsæt Kommunens markering
        # --------------------------------------------------
        print("✏️ Indsætter Kommunens markering...")

        await bo_kommunens_markeringer(
            page=new_page,
            session=session,
            tekst="123testtest",
        )

        # --------------------------------------------------
        # ✅ Done
        # --------------------------------------------------
        print("✅ Test færdig - tekst indsat!")

        await session.recorder.screenshot(new_page, "FINAL_RESULT")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_kommunens_markeringer())

