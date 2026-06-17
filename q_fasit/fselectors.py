
# ==================================================
# ✅ FASIT
# ==================================================

class FasitSelectors:
    AUTH_DROPDOWN = "#SelectedAuthenticationUrl"
    OK_BUTTON = "#btnOK"

    MUNICIPALITY = "Haderslev Kommune"


# ==================================================
# ✅ BORGEROVERBLIK
# ==================================================

class BorgerOverblikSelectors:
    CONTAINER = (
        "//div[contains(@class,'MuiAccordion-root')]"
        "[.//span[normalize-space()='Kommunens markeringer']]"
    )

    REDIGER = "//button[normalize-space()='Redigér']"

    IMPORTANT_NOTE2 = (
        "//label[normalize-space()='OBS-note 2']"
        "/following::input[@name='importantNote2'][1]"
    )

    DATO_INPUT = (
        "//label[normalize-space()='OBS-note 2: Vises indtil']"
        "/following::input[@placeholder='dd-MM-yyyy'][1]"
    )

    GEM = "//button[contains(normalize-space(), 'Gem')]"


# ==================================================
# ✅ FREMSØG BORGER
# ==================================================

class FremsoegBorgerSelectors:
    SEARCH_INPUT = "//input[@type='text' and @placeholder='Hvad søger du?']"
    TARGET_BUTTON = "/html/body/div[1]/span[2]/div[1]/button"
    RESULT_HEADER = (
        "//h6[contains(normalize-space(.),'(') "
        "and contains(normalize-space(.),'-') "
        "and contains(normalize-space(.),')')]"
    )

    @staticmethod
    def result_button(cpr: str) -> str:
        return (
            f"//div[@id='scrollableDiv']//h6"
            f"[contains(normalize-space(.),'({cpr})')]"
            "/ancestor::div[@role='button']"
        )