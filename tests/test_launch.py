import asyncio
from playwright.async_api import async_playwright
from dotenv import load_dotenv
load_dotenv()
import os
from q_fasit.functionality.launch import launch_fasit
from q_fasit.functionality.fremsoeg_borger import fremsoeg_borger
from q_haderslev_vbo.playwright.browser_session import BrowserSession


load_dotenv()

async def main():
    # -------------------------------------------------
    # 1. Opret browser-session (run-sandhed)
    # -------------------------------------------------
    session = BrowserSession(headless=False, debug=True, video=False)
    await session.start()
    page = await session.new_page()
 
    try:
 
        # -------------------------------------------------
        # 4. Kør launch_cura (login-flow)
        # -------------------------------------------------
        await launch_fasit(
            page=page,
            session=session,
            credential_name="DIRXOPS",
        )
 
        print("✅ Fasit klar:", page.url)
 
        # -------------------------------------------------
        # 5. Tag print-screen (HER oprettes mappen)
        # -------------------------------------------------
        await session.screenshot(
            page=page,
            name="STEP_1_fasit_efter_login"
        )
 
        # --------------------------------------------------
        # ✅ TEST 2: Fremsøg borger
        # --------------------------------------------------
        new_page = await fremsoeg_borger(
            page=page,
            session=session,
            cpr = os.getenv("test_cpr"),  # ← test CPR
        )

        # --------------------------------------------------
        # ✅ Final check
        # --------------------------------------------------
        print("✅ Test færdig")
        print("🌐 Aktiv URL:", new_page.url)
    
    finally:
        await session.close()

if __name__ == "__main__":
    asyncio.run(main())
