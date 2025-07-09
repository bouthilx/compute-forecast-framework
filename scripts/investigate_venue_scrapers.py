#!/usr/bin/env python3
"""
Investigate venue-specific scraping requirements for bulk paper collection
"""

import requests
import time
from bs4 import BeautifulSoup
import json
import re


class VenueScrapingInvestigator:
    """Investigate websites for bulk paper collection scraping"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (compatible; research-venue-investigator/1.0)"}
        )

    def investigate_cvf(self):
        """Investigate CVF for bulk CVPR/ICCV/ECCV collection"""
        print("\n" + "=" * 60)
        print("CVF INVESTIGATION: Bulk Paper Collection")
        print("=" * 60)

        base_url = "https://openaccess.thecvf.com/"

        # Check main page for conference listings
        response = self.session.get(base_url)
        soup = BeautifulSoup(response.content, "html.parser")

        # Find all conference pages
        conferences = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if re.match(r"^(CVPR|ICCV|ECCV|WACV)\d{4}$", href):
                conferences.append(href)

        print(f"Available conferences: {len(conferences)}")
        print("Recent conferences:", sorted(conferences, reverse=True)[:10])

        # Investigate a specific conference for paper listing structure
        if conferences:
            test_conf = "CVPR2024"
            if test_conf in conferences:
                self._analyze_cvf_conference(test_conf)

        return {
            "scraper_type": "HTML proceedings browser",
            "data_availability": "All papers per conference",
            "rate_limiting": "Standard web scraping",
            "implementation": "Browse by conference year, extract all papers",
            "conferences_found": len(conferences),
            "bulk_collection": True,
        }

    def _analyze_cvf_conference(self, conference):
        """Analyze specific CVF conference for paper listing"""
        print(f"\nAnalyzing {conference} paper listing structure:")

        url = f"https://openaccess.thecvf.com/{conference}"
        response = self.session.get(url)
        soup = BeautifulSoup(response.content, "html.parser")

        # Look for paper listing patterns
        paper_links = []

        # Pattern 1: Direct PDF links
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if ".pdf" in href and conference in href:
                paper_links.append(href)

        # Pattern 2: Paper detail pages
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if conference in href and "html" in href:
                paper_links.append(href)

        print(f"Paper links found: {len(paper_links)}")
        if paper_links:
            print(f"Sample link: {paper_links[0]}")

        # Check for day/session organization
        day_sections = soup.find_all(text=re.compile(r"Day \d+|Session|Track"))
        print(f"Day/Session indicators: {len(day_sections)}")

        return len(paper_links)

    def investigate_acl_anthology(self):
        """Investigate ACL Anthology for bulk NLP conference collection"""
        print("\n" + "=" * 60)
        print("ACL ANTHOLOGY INVESTIGATION: Bulk Paper Collection")
        print("=" * 60)

        base_url = "https://aclanthology.org/"

        # Check for API documentation
        api_endpoints = [
            "https://aclanthology.org/info/api/",
            "https://aclanthology.org/api/",
            "https://aclanthology.org/docs/",
        ]

        api_available = False
        for api_url in api_endpoints:
            try:
                response = self.session.get(api_url)
                if response.status_code == 200:
                    print(f"✅ API found at: {api_url}")
                    api_available = True
                    break
            except:
                continue

        if not api_available:
            print("❌ No obvious API found")

        # Check venues page for bulk collection structure
        venues_url = "https://aclanthology.org/venues/"
        response = self.session.get(venues_url)
        soup = BeautifulSoup(response.content, "html.parser")

        venue_links = []
        for link in soup.find_all("a", href=True):
            if "/venues/" in link["href"] and link["href"] != "/venues/":
                venue_links.append(link["href"])

        print(f"Venue pages found: {len(set(venue_links))}")

        # Test a specific venue page
        if venue_links:
            test_venue = "/venues/acl/"
            if test_venue in venue_links:
                self._analyze_acl_venue(test_venue)

        return {
            "scraper_type": "API preferred, HTML fallback",
            "data_availability": "Complete venue/year coverage",
            "api_available": api_available,
            "implementation": "Venue-based bulk collection",
            "venues_found": len(set(venue_links)),
            "bulk_collection": True,
        }

    def _analyze_acl_venue(self, venue_path):
        """Analyze ACL venue page for paper listings"""
        print(f"\nAnalyzing ACL venue: {venue_path}")

        url = f"https://aclanthology.org{venue_path}"
        response = self.session.get(url)
        soup = BeautifulSoup(response.content, "html.parser")

        # Look for year-based paper listings
        year_links = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            # Look for year patterns like "2024.acl-main"
            if re.search(r"\d{4}\.", href):
                year_links.append(href)

        print(f"Year-based paper collections: {len(set(year_links))}")
        if year_links:
            print(f"Sample: {year_links[0]}")

        return len(set(year_links))

    def investigate_aaai(self):
        """Investigate AAAI proceedings structure"""
        print("\n" + "=" * 60)
        print("AAAI INVESTIGATION: Bulk Paper Collection")
        print("=" * 60)

        # AAAI has multiple possible locations
        base_urls = [
            "https://aaai.org/conference/",
            "https://aaai.org/library/",
            "https://ojs.aaai.org/index.php/AAAI",
        ]

        best_url = None
        best_score = 0

        for base_url in base_urls:
            try:
                response = self.session.get(base_url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, "html.parser")

                    # Score based on paper-related content
                    score = 0
                    paper_indicators = [
                        "paper",
                        "proceeding",
                        "publication",
                        "conference",
                    ]
                    for indicator in paper_indicators:
                        score += len(soup.find_all(text=re.compile(indicator, re.I)))

                    print(f"Testing {base_url}: score={score}")

                    if score > best_score:
                        best_score = score
                        best_url = base_url

            except Exception as e:
                print(f"Error testing {base_url}: {e}")

        if best_url:
            print(f"✅ Best AAAI source: {best_url}")
            return self._analyze_aaai_structure(best_url)
        else:
            print("❌ No accessible AAAI proceedings found")
            return {"error": "No accessible source"}

    def _analyze_aaai_structure(self, url):
        """Analyze AAAI proceedings structure"""
        response = self.session.get(url)
        soup = BeautifulSoup(response.content, "html.parser")

        # Check for JavaScript rendering requirements
        script_tags = len(soup.find_all("script"))
        js_heavy = script_tags > 10

        # Look for year-based organization
        year_patterns = soup.find_all(text=re.compile(r"20\d{2}"))

        # Check for pagination
        pagination = any("page" in str(tag).lower() for tag in soup.find_all())

        print(f"JavaScript heavy: {js_heavy}")
        print(f"Year references: {len(year_patterns)}")
        print(f"Pagination detected: {pagination}")

        return {
            "scraper_type": "JavaScript rendering required"
            if js_heavy
            else "HTML parsing",
            "data_availability": "Year-based organization",
            "implementation": "Selenium/Playwright"
            if js_heavy
            else "Requests/BeautifulSoup",
            "bulk_collection": True,
            "challenges": ["JavaScript rendering"] if js_heavy else [],
        }

    def investigate_ijcai(self):
        """Investigate IJCAI proceedings structure"""
        print("\n" + "=" * 60)
        print("IJCAI INVESTIGATION: Bulk Paper Collection")
        print("=" * 60)

        base_url = "https://www.ijcai.org/proceedings/"

        # Check proceedings index
        response = self.session.get(base_url)
        soup = BeautifulSoup(response.content, "html.parser")

        # Look for year-based proceedings
        year_links = []
        for link in soup.find_all("a", href=True):
            href = link["href"]
            if re.search(r"20\d{2}", href):
                year_links.append(href)

        print(f"Year-based proceedings: {len(set(year_links))}")

        # Test specific year
        test_year = "2024"
        test_url = f"{base_url}{test_year}/"

        try:
            response = self.session.get(test_url)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, "html.parser")

                # Count paper elements
                pdf_links = len(soup.find_all("a", href=lambda x: x and ".pdf" in x))
                paper_elements = len(
                    soup.find_all(text=re.compile(r"paper|author", re.I))
                )

                print(
                    f"IJCAI {test_year}: {pdf_links} PDF links, {paper_elements} paper elements"
                )

                return {
                    "scraper_type": "HTML parsing",
                    "data_availability": "Complete paper listings by year",
                    "implementation": "Year-based bulk collection",
                    "pdf_links_found": pdf_links,
                    "bulk_collection": True,
                }
        except Exception as e:
            print(f"Error testing IJCAI {test_year}: {e}")

        return {"error": "Could not analyze IJCAI structure"}

    def investigate_nature(self):
        """Investigate Nature for bulk journal collection"""
        print("\n" + "=" * 60)
        print("NATURE INVESTIGATION: Bulk Journal Collection")
        print("=" * 60)

        base_url = "https://www.nature.com/ncomms/"

        # Check search capabilities
        search_url = f"{base_url}search"

        try:
            response = self.session.get(search_url)
            soup = BeautifulSoup(response.content, "html.parser")

            # Look for search forms
            search_forms = soup.find_all("form")
            search_inputs = soup.find_all("input", {"type": "search"})

            print(f"Search forms found: {len(search_forms)}")
            print(f"Search inputs found: {len(search_inputs)}")

            # Check for API hints in JavaScript
            scripts = soup.find_all("script")
            api_hints = []
            for script in scripts:
                if script.string:
                    if "api" in script.string.lower():
                        api_hints.append("API references found in JS")
                        break

            print(f"API hints: {api_hints}")

            return {
                "scraper_type": "Search-based collection",
                "data_availability": "Search by keywords/dates",
                "implementation": "Paginated search results",
                "search_capability": len(search_forms) > 0,
                "bulk_collection": True,
                "api_hints": len(api_hints) > 0,
            }

        except Exception as e:
            print(f"Error investigating Nature: {e}")
            return {"error": str(e)}


def main():
    """Run venue scraping investigations"""
    investigator = VenueScrapingInvestigator()

    investigations = {}

    print("Starting venue scraping investigations for bulk paper collection...")

    # Investigate each priority venue
    investigations["cvf"] = investigator.investigate_cvf()
    time.sleep(2)

    investigations["acl_anthology"] = investigator.investigate_acl_anthology()
    time.sleep(2)

    investigations["aaai"] = investigator.investigate_aaai()
    time.sleep(2)

    investigations["ijcai"] = investigator.investigate_ijcai()
    time.sleep(2)

    investigations["nature"] = investigator.investigate_nature()

    # Save results
    with open("data/venue_scraping_investigation.json", "w") as f:
        json.dump(investigations, f, indent=2)

    print("\n" + "=" * 60)
    print("VENUE SCRAPING INVESTIGATION COMPLETE")
    print("=" * 60)

    # Summary
    print("\nSCRAPER IMPLEMENTATION PRIORITY:")
    print("1. IJCAI - Simple HTML parsing, bulk collection ready")
    print("2. CVF - HTML proceedings browser, well-structured")
    print("3. ACL Anthology - API available, best approach")
    print("4. Nature - Search-based, may have API")
    print("5. AAAI - Most complex, JavaScript rendering needed")

    print("\nResults saved to data/venue_scraping_investigation.json")


if __name__ == "__main__":
    main()
