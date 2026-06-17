from playwright.sync_api import Page
from utils import fremsoeg_borger


class BorgereClient:
    def __init__(self, client):
        self._page: Page = client.page

    def åbn_borger(self, cpr: str):
        fremsoeg_borger(self._page, cpr)
