import re


CPR_REGEX = r"\((\d{6}-\d{4})\)"


def normalize_cpr(cpr: str) -> str:
    raw = cpr.replace("-", "").strip()

    if not re.fullmatch(r"\d{10}", raw):
        raise ValueError(f"❌ Ugyldigt CPR-format: {cpr}")

    return f"{raw[:6]}-{raw[6:]}"


async def wait_for_page_ready(page):
    if page.is_closed():
        raise Exception("❌ Page er lukket")

    await page.wait_for_load_state("domcontentloaded")
    await page.wait_for_load_state("networkidle")


async def safe_click(locator):
    try:
        await locator.click()
    except:
        await locator.click(force=True)


async def screenshot(session, page, name: str):
    if not page.is_closed():
        await session.recorder.screenshot(page, name)


async def click_and_handle_tabs_strict(page, session, locator, timeout_ms=5000):
    context = session.context
    existing_pages = context.pages  # liste (samling af faner)

    # klik først
    await locator.click()

    # vent på ny fane
    new_page = None

    for _ in range(10):  # prøv flere gange (robusthed)
        await page.wait_for_timeout(500)

        if len(context.pages) > len(existing_pages):
            # find ny side
            new_page = [p for p in context.pages if p not in existing_pages][0]
            break

    # hvis ingen ny fane → brug samme page
    if new_page is None:
        print("⚠️ Ingen ny fane åbnet – bruger samme page")
        return page

    # vent på den er klar
    await wait_for_page_ready(new_page)
    await new_page.bring_to_front()

    return new_page



def extract_cpr_from_text(text: str):
    match = re.search(CPR_REGEX, text)
    return match.group(1) if match else None

async def element_exists(page, selector: str) -> bool:
    return await page.locator(selector).count() > 0
