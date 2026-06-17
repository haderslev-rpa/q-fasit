import asyncio
from dotenv import load_dotenv
import os
# ✅ Load env (fixer ATS_URL)
load_dotenv()
from q_fasit.launch import launch_fasit
from q_fasit.fremsoeg_borger import fremsoeg_borger
from q_fasit.borgeroverblik import bo_kommunens_markeringer
from q_haderslev_vbo.playwright.browser_session import BrowserSession


async def main():
    # -------------------------------------------------
    # 1. Opret browser-session (run-sandhed)
    # -------------------------------------------------
    session = BrowserSession(headless=False, debug=True, video=True)
    await session.start()
    page = await session.new_page()
 
    try:

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

        await session.screenshot(new_page, "DEBUG_efter_borger_aabnet")

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

        await session.screenshot(new_page, "FINAL_RESULT")

    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(test_kommunens_markeringer())

