
# ==================================================
# ✅ FASIT
# ==================================================

class FasitSelectors:
    AUTH_DROPDOWN = "#SelectedAuthenticationUrl"
    OK_BUTTON = "#btnOK"

    MUNICIPALITY = "Haderslev Kommune"
    APP_HEADER = ".layout__app-header"


# ==================================================
# ✅ BORGEROVERBLIK
# ==================================================

class BorgerOverblikSelectors:

    BORGEROVERBLIK = ("[.//h3[normalize-space()='Borgeroverblik']]")


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

# --------------------------------------------------
    # ✅ Persongruppemarkeringer
    # --------------------------------------------------
    PERSONGRUPPEMARKERINGER_CONTAINER = (
        "//div[contains(@class,'MuiAccordion-root')]"
        "[.//*[normalize-space()='Persongruppemarkeringer']]"
    )

    # Relativ selector.
    # Skal bruges via PERSONGRUPPEMARKERINGER_CONTAINER.
    PERSONGRUPPEMARKERINGER_NY_CONTAINER = (
        ".//button["
        ".//*[name()='svg' and @data-icon='circle-plus']"
        "]"
    )

    # --------------------------------------------------
    # ✅ Persongruppe
    # --------------------------------------------------
    PERSONGRUPPE_INPUT = (
        "//fieldset"
        "[.//legend//span[contains(normalize-space(.), 'Persongruppe')]]"
        "/preceding-sibling::input[@role='combobox'][1]"
    )

    PERSONGRUPPE_DROPDOWN_KNAP = (
        "//fieldset"
        "[.//legend//span[contains(normalize-space(.), 'Persongruppe')]]"
        "/preceding-sibling::div"
        "//button[@aria-label='Åben']"
    )

    PERSONGRUPPE_LISTBOX = (
        "//ul[@role='listbox']"
    )

    PERSONGRUPPE_MULIGHEDER = (
        "//ul[@role='listbox']"
        "//*[@role='option']"
    )

    # --------------------------------------------------
    # ✅ Startdato og slutdato
    # --------------------------------------------------
    PERSONGRUPPE_STARTDATO_INPUT = (
        "//input[@name='startDate' "
        "and @placeholder='dd-MM-yyyy']"
    )

    PERSONGRUPPE_SLUTDATO_INPUT = (
        "//input[@name='endDate' "
        "and @placeholder='dd-MM-yyyy']"
    )

    # --------------------------------------------------
    # ✅ Gem persongruppemarkering
    # --------------------------------------------------
    PERSONGRUPPE_GEM_OG_LUK = (
        "//button"
        "[@type='button' "
        "and @data-testid='button' "
        "and normalize-space(.)='Gem og luk']"
        )