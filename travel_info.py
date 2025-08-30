import argparse
import asyncio
import base64
import json
import os
import tempfile
from datetime import datetime
from typing import Dict, List, Optional

import openai
import uvicorn
from fastapi import FastAPI, HTTPException
from playwright.async_api import async_playwright
from pydantic import BaseModel

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("Please set OPENAI_API_KEY environment variable")

openai.api_key = OPENAI_API_KEY

app = FastAPI(title="Travel Planner API", version="1.0.0")


class TravelRequest(BaseModel):
    origin: str
    destination: str
    date: str  # YYYY-MM-DD format
    days: int = 3
    budget: str = "mid"  # budget, mid, luxury


class TravelResponse(BaseModel):
    flights: Dict
    hotels: Dict
    raw_analysis: List[str]


async def capture_screenshot(
    url: str, wait_selector: str = None, filename: str = None
) -> str:
    """Capture screenshot and return as base64 string"""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1200, "height": 800})

        # Set user agent and headers to look more like a real browser
        await page.set_extra_http_headers(
            {
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            }
        )

        try:
            # Try different wait strategies based on the URL type
            if "maps.google.com" in url:
                await page.goto(url, wait_until="domcontentloaded", timeout=45000)
                await page.wait_for_timeout(8000)  # Maps needs more time

                # Try to wait for map content specifically
                try:
                    await page.wait_for_selector('[role="main"]', timeout=10000)
                except:
                    print("Maps: Main content selector not found, continuing...")

            elif "google.com/travel" in url:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(4000)

                # Wait for travel content
                try:
                    await page.wait_for_selector(
                        "[data-sokoban-container]", timeout=5000
                    )
                except:
                    print("Travel: Travel content not found, continuing...")
            else:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(3000)

            # Wait for specific selector if provided
            if wait_selector:
                try:
                    await page.wait_for_selector(wait_selector, timeout=10000)
                except:
                    print(f"Custom selector {wait_selector} not found, continuing...")

            # Take screenshot
            screenshot = await page.screenshot(full_page=True)
            screenshot_b64 = base64.b64encode(screenshot).decode()

            # Save screenshot locally if filename provided
            if filename:
                os.makedirs("screenshots", exist_ok=True)
                screenshot_path = f"screenshots/{filename}"
                with open(screenshot_path, "wb") as f:
                    f.write(screenshot)
                print(f"📸 Screenshot saved: {screenshot_path}")

            return screenshot_b64

        except Exception as e:
            print(f"Error capturing screenshot for {url}: {e}")
            # Try a simpler approach for problematic URLs
            if "maps.google.com" in url:
                try:
                    print("Retrying with simpler Maps URL...")
                    simple_url = f"https://www.google.com/maps/dir/{url.split('/')[-3]}/{url.split('/')[-2]}"
                    await page.goto(
                        simple_url, wait_until="domcontentloaded", timeout=30000
                    )
                    await page.wait_for_timeout(5000)
                    screenshot = await page.screenshot(full_page=True)
                    screenshot_b64 = base64.b64encode(screenshot).decode()

                    if filename:
                        os.makedirs("screenshots", exist_ok=True)
                        screenshot_path = f"screenshots/{filename}"
                        with open(screenshot_path, "wb") as f:
                            f.write(screenshot)
                        print(f"📸 Screenshot saved (retry): {screenshot_path}")

                    return screenshot_b64
                except:
                    pass
            return None
        finally:
            await browser.close()


async def get_expanded_maps_url(origin: str, destination: str) -> str:
    """Get the expanded Google Maps URL by letting the page redirect naturally"""
    # This function is no longer used - keeping for potential future use
    pass


def build_urls(
    origin: str, destination: str, date: str, days: int, budget: str
) -> Dict[str, str]:
    """Build Google URLs for flights and hotels only"""

    # Calculate return date
    from datetime import datetime, timedelta

    start_date = datetime.strptime(date, "%Y-%m-%d")
    end_date = start_date + timedelta(days=days)

    # Build flight and hotel URLs (these work reliably)
    urls = {
        "flights": f"https://www.google.com/travel/flights?q=Flights%20from%20{origin.upper()}%20to%20{destination.upper()}%20on%20{date}",
        "hotels": f"https://www.google.com/travel/hotels?q=Hotels%20in%20{destination.upper()}%20checkin%20{date}%20checkout%20{end_date.strftime('%Y-%m-%d')}",
    }

    return urls


async def analyze_screenshot(screenshot_b64: str, context: str) -> str:
    """Send screenshot to GPT-4o-mini for analysis"""
    if not screenshot_b64:
        return f"Failed to capture {context} screenshot"

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""Analyze this {context} screenshot and extract key information in JSON format.

For FLIGHTS: Extract flight options with airline, departure/arrival times, duration, price, stops
For HOTELS: Extract hotel names, ratings, prices per night, location, amenities
For TRANSPORT: Extract transport options from airport to city with duration, cost, method

Return clean JSON only, no markdown formatting.""",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{screenshot_b64}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=1000,
            temperature=0.1,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Error analyzing {context}: {str(e)}"


async def get_travel_plan(request: TravelRequest) -> TravelResponse:
    """Main function to get complete travel plan"""

    # Build URLs for flights and hotels only
    urls = build_urls(
        request.origin, request.destination, request.date, request.days, request.budget
    )

    print(f"🔍 Capturing screenshots for {request.origin} → {request.destination}")
    print(
        "📝 Note: Transport info excluded due to complexity - focusing on flights + hotels"
    )

    # Capture screenshots concurrently
    tasks = []
    for context, url in urls.items():
        print(f"📸 Capturing {context}: {url}")
        filename = (
            f"{request.origin}_{request.destination}_{request.date}_{context}.png"
        )
        task = capture_screenshot(url, filename=filename)
        tasks.append((context, task))

    screenshots = {}
    for context, task in tasks:
        screenshot = await task
        screenshots[context] = screenshot
        status = "✅" if screenshot else "❌"
        print(f"{status} {context.title()} screenshot captured")

    # Analyze screenshots with Vision API
    print("🤖 Analyzing screenshots with GPT-4o-mini...")
    analyses = {}
    raw_analyses = []

    for context, screenshot in screenshots.items():
        if screenshot:
            analysis = await analyze_screenshot(screenshot, context)
            analyses[context] = analysis
            raw_analyses.append(f"{context.title()}: {analysis}")
            print(f"✅ {context.title()} analysis complete")
        else:
            analyses[context] = {"error": f"Failed to capture {context} screenshot"}
            raw_analyses.append(f"{context.title()}: Screenshot capture failed")

    # Parse JSON responses (with error handling)
    def safe_json_parse(text: str, fallback_key: str):
        try:
            # Try to find JSON in the response
            import re

            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"raw_text": text, "parsed": False}
        except:
            return {"raw_text": text, "error": "JSON parsing failed"}

    return TravelResponse(
        flights=safe_json_parse(analyses.get("flights", "{}"), "flights"),
        hotels=safe_json_parse(analyses.get("hotels", "{}"), "hotels"),
        raw_analysis=raw_analyses,
    )


# FastAPI endpoints
@app.post("/plan", response_model=TravelResponse)
async def plan_trip(request: TravelRequest):
    """Get complete travel plan"""
    try:
        result = await get_travel_plan(request)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Travel Planner API is running"}


# CLI Interface
async def main_cli():
    parser = argparse.ArgumentParser(description="Travel Planner CLI")
    parser.add_argument("origin", help="Origin airport code (e.g., SFO)")
    parser.add_argument("destination", help="Destination airport code (e.g., JFK)")
    parser.add_argument("date", help="Travel date (YYYY-MM-DD)")
    parser.add_argument(
        "--days", type=int, default=3, help="Number of days (default: 3)"
    )
    parser.add_argument(
        "--budget",
        choices=["budget", "mid", "luxury"],
        default="mid",
        help="Budget level",
    )
    parser.add_argument("--save", help="Save results to JSON file")

    args = parser.parse_args()

    request = TravelRequest(
        origin=args.origin,
        destination=args.destination,
        date=args.date,
        days=args.days,
        budget=args.budget,
    )

    print(
        f"🛫 Planning trip: {args.origin} → {args.destination} on {args.date} ({args.days} days)"
    )
    print(f"💰 Budget level: {args.budget}")
    print(f"📁 Screenshots will be saved to: screenshots/")
    print("-" * 60)

    result = await get_travel_plan(request)

    # Pretty print results
    print("\n🛫 FLIGHTS:")
    print(json.dumps(result.flights, indent=2))

    print("\n🏨 HOTELS:")
    print(json.dumps(result.hotels, indent=2))

    print("\n💡 NOTE: Transport info excluded due to complexity.")
    print("    Future versions may include simpler transport options.")

    # Save if requested
    if args.save:
        with open(args.save, "w") as f:
            json.dump(result.dict(), f, indent=2)
        print(f"\n💾 Results saved to {args.save}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # CLI mode
        asyncio.run(main_cli())
    else:
        # API server mode
        print("🚀 Starting Travel Planner API server...")
        print("📚 API docs: http://localhost:8000/docs")
        print("🏥 Health check: http://localhost:8000/health")
        uvicorn.run(app, host="0.0.0.0", port=8000)
