from playwright.sync_api import Page, sync_playwright
import logging

from q_haderslev_vbo.playwright.faelles_kommunal_login_idp import (
    login_via_faelles_kommunal_idp
)


class FasitClient:

    FASIT_URL = "https://login.fasit.dk/haderslev/kombit"

    @property
    def page(self) -> Page:
        return self._page

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        self._playwright = sync_playwright().start()

        self._browser = self._playwright.chromium.launch(
            headless=False,
            args=["--window-size=1920,1080"]
        )

        self._context = self._browser.new_context(
            viewport={"width": 1920, "height": 1080},
            locale="da-DK",
            ignore_https_errors=True
        )

        self._page: Page = (
            self._context.pages[0]
            if self._context.pages
            else self._context.new_page()
        )

    # ✅ HER ER DIN LAUNCH
    def launch(self, credential_name: str) -> None:

        self.logger.info("🌐 Går til FASIT...")

        self._page.goto(self.FASIT_URL)
        self._page.wait_for_load_state("domcontentloaded")

        # ---------------------------------------------
        # ✅ Check om login er nødvendigt
        # ---------------------------------------------
        locator = self._page.locator("#SelectedAuthenticationUrl")

        if locator.count() > 0:
            self.logger.info("🔐 Ikke logget ind – starter login")

            locator.select_option(label="Haderslev Kommune")

            self._page.locator("#btnOK").click()
            self._page.wait_for_load_state("networkidle")

            # 🔥 vigtig: login wrapper skal være sync
            login_via_faelles_kommunal_idp(
                page=self._page,
                credential_name=credential_name,
            )

            # Reload efter login
            self._page.goto(self.FASIT_URL)
            self._page.wait_for_load_state("networkidle")

        else:
            self.logger.info("✅ Allerede logget ind i FASIT")

        self.logger.info(f"✅ FASIT klar: {self._page.url}")

    def close(self) -> None:
        self._context.close()
        self._browser.close()
        self._playwright.stop()
        