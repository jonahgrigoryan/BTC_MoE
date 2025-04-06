import asyncio
import logging
import re
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import pandas as pd
from datetime import datetime
import json
import calendar
import time
import random
import os

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def scrape_x_tweets():
    # Create screenshots directory if it doesn't exist
    os.makedirs("screenshots", exist_ok=True)
    
    async with async_playwright() as p:
        # Use Firefox instead of Chrome (less likely to be detected)
        browser = await p.firefox.launch(
            headless=False,
            slow_mo=100
        )
        
        # Create a context with a more realistic user agent and viewport
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
            locale="en-US",
            timezone_id="America/Los_Angeles",
            # Commented out proxy for debugging - uncomment and fix if needed
            proxy={"server": "gate2.proxyfuel.com:2000", "username": "jonah.kesoyan.gmail.com", "password": "w6z7yq"}
        )
        
        # Create the page from this context
        page = await context.new_page()
        
        # Apply stealth to the page to evade detection
        await stealth_async(page)
        
        # Add extensive anti-detection scripts
        await page.add_init_script("""
        // Hide automation
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        
        // Add some randomization to make it look more human
        const originalQuery = document.querySelector;
        document.querySelector = function(...args) {
            const result = originalQuery.apply(this, args);
            if (Math.random() > 0.9) {
                setTimeout(() => {}, Math.floor(Math.random() * 100));
            }
            return result;
        }
        
        // Add fake WebGL to appear as a normal browser
        if (!window.WebGLRenderingContext) {
            window.WebGLRenderingContext = function() {};
        }
        """)
        
        # Set cookies to appear more like a real user with Python timestamp
        import math
        import time
        await context.add_cookies([
            {
                "name": "guest_id",
                "value": f"v1%3A{math.floor(time.time())}",
                "domain": ".x.com",
                "path": "/"
            }
        ])
        
        # Use a simpler approach with fewer URLs to test first
        base_urls = [
            # Use Nitter as an alternative frontend that's more scraper-friendly
            "https://nitter.net/search?f=tweets&q=%23Bitcoin&since=2022-01-01&until=2022-01-31",
            "https://nitter.net/search?f=tweets&q=%23Bitcoin&since=2022-02-01&until=2022-02-28",
            "https://nitter.net/search?f=tweets&q=%23Bitcoin&since=2022-03-01&until=2022-03-31",
            
            # Fallback to X.com with a more specific query that might work better
            "https://x.com/search?q=%23Bitcoin%20lang%3Aen%20since%3A2022-01-01%20until%3A2022-01-31&src=typed_query",
            "https://x.com/search?q=%23Bitcoin%20lang%3Aen%20since%3A2022-02-01%20until%3A2022-02-28&src=typed_query",
            "https://x.com/search?q=%23Bitcoin%20lang%3Aen%20since%3A2022-03-01%20until%3A2022-03-31&src=typed_query"
        ]
        
        all_tweets = []
        for url_index, url in enumerate(base_urls):
            logger.info(f"Navigating to: {url} ({url_index+1}/{len(base_urls)})")
            
            # Initialize tweets variable for this iteration
            tweets = []
            
            try:
                # Add a random delay between requests to mimic human behavior
                await asyncio.sleep(random.uniform(2, 5))
                
                # Navigate with a longer timeout
                logger.info(f"Loading {url}")
                try:
                    # Set a shorter initial timeout for Nitter to fail faster if needed
                    timeout = 30000 if "nitter" in url else 60000
                    await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
                except Exception as nav_error:
                    logger.error(f"Navigation error: {nav_error}")
                    # If it's a Nitter URL that failed, skip to the next URL
                    if "nitter" in url:
                        logger.info("Skipping Nitter URL after error")
                        continue
                    # Otherwise, refresh the page and try again for X.com
                    logger.info("Refreshing page...")
                    await page.reload(wait_until="domcontentloaded", timeout=60000)
                
                # Wait longer for content to load
                await asyncio.sleep(8)
                
                # Take a screenshot before handling any popups
                await page.screenshot(path=f"screenshots/before_popups_{url_index}.png")
                
                # Handle login popup if it appears (X.com)
                for selector in ['div[aria-label="Close"]', 'div[data-testid="app-bar-close"]', 'div[role="button"][aria-label="Close"]']:
                    try:
                        close_button = page.locator(selector)
                        if await close_button.count() > 0:
                            logger.info(f"Found close button with selector: {selector}")
                            await close_button.click()
                            logger.info("Closed popup")
                            await asyncio.sleep(1)
                    except Exception as e:
                        logger.debug(f"No popup to close with selector {selector}: {e}")
                
                # Advanced scrolling with pagination and more aggressive loading
                async def scroll_and_paginate():
                    last_count = 0
                    last_height = 0
                    no_change_count = 0
                    max_no_change = 3  # Stop after 3 scrolls with no new content
                    
                    for i in range(20):  # Increase max scrolls to 20
                        logger.info(f"Scroll {i+1}/20")
                        
                        # Random scroll amount to seem more human-like
                        scroll_amount = random.randint(500, 1000)
                        await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                        
                        # Random pause between scrolls
                        await asyncio.sleep(random.uniform(1.0, 3.0))
                        
                        # Occasionally move mouse to appear more human-like
                        if random.random() < 0.3:
                            await page.mouse.move(
                                random.randint(100, 1200),
                                random.randint(100, 600)
                            )
                            
                        # Take occasional screenshot to monitor progress
                        if i % 5 == 0:
                            await page.screenshot(path=f"screenshots/scrolling_{url_index}_{i}.png")
                        
                        # Check if we've loaded new content
                        if "nitter" in url:
                            current_count = await page.locator(".timeline-item").count()
                            logger.info(f"Current tweet count: {current_count} (was {last_count})")
                            
                            # Try to find and click "More" button on Nitter if no new tweets
                            if current_count == last_count:
                                for more_selector in [".show-more a", "a:has-text('Load more')", "a:has-text('More')"]:
                                    more_button = page.locator(more_selector)
                                    if await more_button.count() > 0:
                                        logger.info(f"Clicking 'More' button with selector: {more_selector}")
                                        try:
                                            await more_button.click()
                                            await asyncio.sleep(3)  # Wait for new content to load
                                            break
                                        except Exception as e:
                                            logger.error(f"Error clicking More button: {e}")
                        else:  # X.com
                            # Check page height to see if we've loaded new content
                            current_height = await page.evaluate("document.body.scrollHeight")
                            logger.info(f"Current page height: {current_height} (was {last_height})")
                            
                            # Click "Show more" button on X.com if available
                            if current_height == last_height:
                                for more_selector in ["div[role='button']:has-text('Show more')", "span:has-text('Show more replies')"]:
                                    more_button = page.locator(more_selector)
                                    if await more_button.count() > 0:
                                        logger.info(f"Clicking 'Show more' button with selector: {more_selector}")
                                        try:
                                            await more_button.click()
                                            await asyncio.sleep(3)  # Wait for new content to load
                                            break
                                        except Exception as e:
                                            logger.error(f"Error clicking Show more button: {e}")
                            
                            # Count tweets to log progress
                            current_count = await page.locator("article").count()
                            logger.info(f"Current tweet count: {current_count} (was {last_count})")
                            
                            # Stop if no new content after multiple attempts
                            if current_height == last_height and current_count == last_count:
                                no_change_count += 1
                                if no_change_count >= max_no_change:
                                    logger.info(f"No new content after {max_no_change} attempts, stopping pagination")
                                    break
                            else:
                                no_change_count = 0
                            
                            last_height = current_height
                            
                        last_count = current_count
                
                # Execute the advanced scrolling function
                await scroll_and_paginate()
            
                # Take a screenshot to see what we have after scrolling
                timestamp = int(time.time())
                await page.screenshot(path=f"screenshots/after_scrolling_{url_index}_{timestamp}.png")
                
                # Different selectors for Nitter vs X
                if "nitter" in url:
                    logger.info("Using Nitter selectors")
                    tweet_selectors = [
                        ".timeline-item", 
                        ".tweet-card",
                        ".tweet"
                    ]
                else:
                    logger.info("Using X.com selectors")
                    tweet_selectors = [
                        "article[data-testid='tweet']",
                        "div[data-testid='cellInnerDiv']",
                        "article",
                        "div[data-testid='tweet']"
                    ]
                
                # Try different selectors
                found_selector = None
                for selector in tweet_selectors:
                    try:
                        logger.info(f"Trying selector: {selector}")
                        count = await page.locator(selector).count()
                        if count > 0:
                            found_selector = selector
                            logger.info(f"Found {count} elements with selector: {selector}")
                            break
                    except Exception as e:
                        logger.warning(f"Error with selector {selector}: {e}")
                
                # Save HTML if we can't find tweets
                if not found_selector:
                    logger.warning("No viable tweet selector found. Taking HTML snapshot...")
                    html_content = await page.content()
                    with open(f"page_content_{url_index}_{timestamp}.html", "w", encoding="utf-8") as f:
                        f.write(html_content)
                    logger.info(f"Page content saved to page_content_{url_index}_{timestamp}.html")
                    continue
                
                # Extract tweets using the found selector
                tweets = await page.locator(found_selector).element_handles()
                logger.info(f"Found {len(tweets)} tweet elements with selector '{found_selector}'")
                
                # Process tweets based on the site (no limit)
                for i, tweet in enumerate(tweets):
                    try:
                        # Process all tweets (removed limit)
                            
                        tweet_data = {}
                        
                        # Different parsing logic for Nitter
                        if "nitter" in url:
                            # Nitter parsing
                            try:
                                # Get timestamp
                                time_element = await tweet.query_selector(".tweet-date a")
                                if time_element:
                                    date_str = await time_element.get_attribute("title")
                                    if date_str:
                                        try:
                                            # Parse Nitter's date format (e.g. "Jan 1, 2022, 12:00 PM")
                                            dt = datetime.strptime(date_str, "%b %d, %Y · %I:%M %p")
                                            tweet_data["timestamp"] = dt.isoformat()
                                        except ValueError:
                                            tweet_data["timestamp"] = date_str
                                
                                # Get tweet text
                                text_element = await tweet.query_selector(".tweet-content")
                                tweet_data["text"] = await text_element.inner_text() if text_element else ""
                                
                                # Get username
                                username_element = await tweet.query_selector(".username")
                                tweet_data["username"] = await username_element.inner_text() if username_element else ""
                                
                                # Get retweets
                                retweets_element = await tweet.query_selector(".retweet-count")
                                tweet_data["retweets"] = await retweets_element.inner_text() if retweets_element else "0"
                            except Exception as nitter_error:
                                logger.error(f"Nitter parsing error: {nitter_error}")
                        else:
                            # X.com parsing
                            # Get timestamp (try multiple possible selectors)
                            time_element = await tweet.query_selector("time")
                            tweet_data["timestamp"] = await time_element.get_attribute("datetime") if time_element else None
                            
                            # Get tweet text (trying multiple selectors)
                            text = ""
                            for text_selector in ["[data-testid='tweetText']", "div[lang]", "div[dir='auto']"]:
                                try:
                                    text_elem = await tweet.query_selector(text_selector)
                                    if text_elem:
                                        text = await text_elem.inner_text()
                                        if text:
                                            break
                                except Exception:
                                    continue
                            tweet_data["text"] = text
                            
                            # Get username
                            username = ""
                            for username_selector in ["[data-testid='User-Name'] span", "a[role=link] span", "div[data-testid='User-Name']"]:
                                try:
                                    username_elem = await tweet.query_selector(username_selector)
                                    if username_elem:
                                        username = await username_elem.inner_text()
                                        if username:
                                            break
                                except Exception:
                                    continue
                            tweet_data["username"] = username
                            
                            # Get retweet count
                            retweets_elem = await tweet.query_selector("[data-testid='retweet']")
                            tweet_data["retweets"] = await retweets_elem.inner_text() if retweets_elem else "0"
                        
                        # Skip empty tweets
                        if not tweet_data.get("text"):
                            continue
                        
                        # Verify tweet date if available
                        timestamp = tweet_data.get("timestamp")
                        expected_year_month = None
                        
                        if "since" in url and "until" in url:
                            # Extract date range from URL
                            date_match = re.search(r'since=(\d{4}-\d{2}-\d{2}).*?until=(\d{4}-\d{2}-\d{2})', url)
                            if date_match:
                                start_date = date_match.group(1)
                                end_date = date_match.group(2)
                                expected_year_month = start_date[:7]  # Get YYYY-MM
                                logger.info(f"Expecting tweets from time period: {start_date} to {end_date}")
                        
                        # For X.com URLs, extract differently
                        if "since%3A" in url and "until%3A" in url:
                            date_match = re.search(r'since%3A(\d{4}-\d{2}-\d{2}).*?until%3A(\d{4}-\d{2}-\d{2})', url)
                            if date_match:
                                start_date = date_match.group(1)
                                end_date = date_match.group(2)
                                expected_year_month = start_date[:7]  # Get YYYY-MM
                                logger.info(f"Expecting tweets from time period: {start_date} to {end_date}")
                        
                        # Verify timestamp is in expected range if we have that info
                        if timestamp and expected_year_month:
                            is_valid_date = False
                            # Different timestamp formats from different sources
                            try:
                                if isinstance(timestamp, str):
                                    if "T" in timestamp:  # ISO format from X.com
                                        dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                        tweet_year_month = f"{dt.year}-{dt.month:02d}"
                                        is_valid_date = tweet_year_month == expected_year_month
                                    elif "·" in timestamp:  # Nitter format
                                        # Extract just the date part (e.g., "Jan 30, 2022")
                                        date_part = timestamp.split('·')[0].strip()
                                        dt = datetime.strptime(date_part, "%b %d, %Y")
                                        tweet_year_month = f"{dt.year}-{dt.month:02d}"
                                        is_valid_date = tweet_year_month == expected_year_month
                            except Exception as e:
                                logger.warning(f"Failed to parse timestamp: {timestamp}. Error: {e}")
                                # If parsing fails, we'll keep the tweet anyway
                                is_valid_date = True
                            
                            if not is_valid_date:
                                logger.warning(f"Tweet date {timestamp} outside expected range {expected_year_month}, skipping")
                                continue
                            
                        logger.info(f"Found tweet: {tweet_data.get('username')} - {tweet_data.get('text', '')[:30]}... ({tweet_data.get('timestamp')})")
                
                        # Filter spam
                        if not tweet_data["text"] or "free btc" in tweet_data["text"].lower() or "win bitcoin" in tweet_data["text"].lower():
                            continue
                            
                        all_tweets.append(tweet_data)
                        
                    except Exception as e:
                        logger.error(f"Error processing tweet {i}: {str(e)}")
                
            except Exception as e:
                logger.error(f"Error processing URL {url}: {str(e)}")
            
            # Always report how many tweets we found
            logger.info(f"Scraped {len(tweets)} tweets from {url}")
            
            # Take a final screenshot before moving to next URL
            await page.screenshot(path=f"screenshots/final_{url_index}_{timestamp}.png")
            
            # Continue to next URL even if we found tweets (to collect from all months)
            if len(all_tweets) > 0:
                logger.info(f"Successfully found {len(all_tweets)} tweets so far, continuing to next URL")
                # Short break between URLs
                await asyncio.sleep(random.uniform(5.0, 10.0))
        
        await browser.close()
        
        # Save to JSONL
        with open("posts.jsonl", "w", encoding="utf-8") as f:
            for tweet in all_tweets:
                f.write(json.dumps(tweet) + "\n")
        
        logger.info(f"Saved {len(all_tweets)} tweets to posts.jsonl")
        return all_tweets

# Run the scraper
if __name__ == "__main__":
    tweets = asyncio.run(scrape_x_tweets())
    print(f"Total tweets scraped: {len(tweets)}")
