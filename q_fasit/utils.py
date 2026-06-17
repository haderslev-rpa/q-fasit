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

    try:
        async with context.expect_page(timeout=timeout_ms) as page_event:
            await locator.click()

        new_page = await page_event.value

    except TimeoutError:
        return page

    await wait_for_page_ready(new_page)
    await new_page.bring_to_front()

    return new_page


def extract_cpr_from_text(text: str):
    match = re.search(CPR_REGEX, text)
    return match.group(1) if match else None

async def element_exists(page, selector: str) -> bool:
    return await page.locator(selector).count() > 0
