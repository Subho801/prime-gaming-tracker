import json
import re
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

URL = "https://isthereanydeal.com/subscriptions/1-prime-gaming/"


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


items = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 2200})

    page.goto(URL, wait_until="networkidle", timeout=90000)
    page.wait_for_timeout(5000)

    for _ in range(8):
        page.mouse.wheel(0, 1800)
        page.wait_for_timeout(700)

    page.screenshot(path="prime-debug.png", full_page=True)

    games = page.evaluate("""
    () => {
      const rows = [...document.querySelectorAll("tr, [class*='game'], [class*='item'], [class*='row']")];
      const results = [];

      for (const row of rows) {
        const text = row.innerText || "";
        const img = row.querySelector("img");

        if (!img) continue;
        if (!text.includes("LEAVING")) continue;

        const lines = text.split("\\n").map(x => x.trim()).filter(Boolean);

        const title = lines.find(line =>
          line.length > 2 &&
          line.length < 100 &&
          !line.includes("LEAVING") &&
          !line.includes("TRACKED SINCE") &&
          !line.match(/^\\d{2}\\s[A-Za-z]{3}\\s\\d{4}$/)
        );

        const leavingIndex = lines.findIndex(line => line.includes("LEAVING"));
        let leaving = "";

        for (const line of lines) {
          if (line.match(/^\\d{2}\\s[A-Za-z]{3}\\s\\d{4}$/)) {
            leaving = line;
            break;
          }
        }

        const platform = lines.includes("Epic")
          ? "Epic"
          : lines.includes("GOG")
          ? "GOG"
          : "Prime Gaming";

        if (title) {
          results.push({
            title,
            platform,
            leaving,
            image: img.src || ""
          });
        }
      }

      return results;
    }
    """)

    seen = set()

    for game in games:
        title = clean(game.get("title", ""))

        if not title:
            continue

        key = title.lower()
        if key in seen:
            continue

        seen.add(key)

        items.append({
            "title": title,
            "platform": game.get("platform", "Prime Gaming"),
            "status": "claimable",
            "url": URL,
            "image": game.get("image", ""),
            "leaving": game.get("leaving", ""),
            "source": "IsThereAnyDeal"
        })

    browser.close()

output = {
    "updatedAt": datetime.now(timezone.utc).isoformat(),
    "count": len(items),
    "items": items,
}

with open("data/prime-gaming.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"Saved {len(items)} Prime Gaming games")
