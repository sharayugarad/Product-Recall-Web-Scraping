# test_scoutyourcase.py
from scoutyourcase_productrecall_scraper import ScoutYourCaseProductRecallScraper

if __name__ == "__main__":
    print("\n=== SCOUTYOURCASE PRODUCT RECALL TEST (INDEX + MORE CASES) ===")

    scraper = ScoutYourCaseProductRecallScraper(
        start_url="https://ld.scoutyourcase.com/index",
        headless=False,          
        max_clicks=15,           
        click_pause=1.0,
        debug=True
    )

    try:
        result = scraper.scrape()
        print("Success:", result.get("success"))
        print("Clicks:", result.get("clicks"))
        print("Matched URLs:", len(result.get("matched_urls", [])))
        print("New URLs:", len(result.get("new_urls", [])))

        for u in result.get("new_urls", [])[:20]:
            print("  -", u)
    finally:
        scraper.close()
