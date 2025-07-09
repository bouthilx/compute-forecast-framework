#!/usr/bin/env python3
"""
Investigation script for scraper implementation planning
"""

import requests
import time
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json


class ScraperInvestigator:
    """Investigate website structure for scraper planning"""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (compatible; research-scraper-investigator/1.0)"
            }
        )

    def investigate_site(self, name: str, base_url: str, test_paths: list = None):
        """Investigate a website for scraping potential"""
        print(f"\n{'=' * 60}")
        print(f"INVESTIGATING: {name}")
        print(f"Base URL: {base_url}")
        print("=" * 60)

        results = {
            "name": name,
            "base_url": base_url,
            "accessible": False,
            "structure": {},
            "apis": [],
            "challenges": [],
            "recommendations": [],
        }

        try:
            # Test main page accessibility
            response = self.session.get(base_url, timeout=10)
            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                results["accessible"] = True
                soup = BeautifulSoup(response.content, "html.parser")

                # Check for JavaScript requirements
                if self._has_heavy_js(soup):
                    results["challenges"].append("Heavy JavaScript rendering required")

                # Check for APIs
                apis = self._find_apis(response.text, soup)
                results["apis"] = apis

                # Test specific paths if provided
                if test_paths:
                    for path in test_paths:
                        self._test_path(base_url, path, results)

                # General structure analysis
                self._analyze_structure(soup, results)

            else:
                results["challenges"].append(f"HTTP {response.status_code}")

        except Exception as e:
            print(f"Error: {e}")
            results["challenges"].append(f"Request failed: {str(e)}")

        self._generate_recommendations(results)
        self._print_summary(results)

        return results

    def _has_heavy_js(self, soup):
        """Check if site heavily relies on JavaScript"""
        script_tags = soup.find_all("script")
        js_frameworks = ["react", "angular", "vue", "ember", "backbone"]

        for script in script_tags:
            if script.get("src"):
                src = script["src"].lower()
                if any(fw in src for fw in js_frameworks):
                    return True
        return len(script_tags) > 10

    def _find_apis(self, text, soup):
        """Look for API endpoints or documentation"""
        apis = []

        # Look for API keywords in text
        api_indicators = ["api", "json", "xml", "rest", "graphql"]
        if any(indicator in text.lower() for indicator in api_indicators):
            apis.append("Potential API endpoints detected in page content")

        # Look for API links
        for link in soup.find_all("a", href=True):
            href = link["href"].lower()
            if "api" in href or "developer" in href:
                apis.append(f"API link found: {link['href']}")

        return apis

    def _test_path(self, base_url, path, results):
        """Test a specific path"""
        try:
            full_url = urljoin(base_url, path)
            response = self.session.get(full_url, timeout=10)

            path_info = {
                "path": path,
                "status": response.status_code,
                "content_type": response.headers.get("content-type", "unknown"),
                "size": len(response.content),
            }

            if "structure" not in results:
                results["structure"] = {}
            results["structure"][path] = path_info

            print(f"  {path}: {response.status_code} ({path_info['content_type']})")

        except Exception as e:
            print(f"  {path}: Error - {e}")

    def _analyze_structure(self, soup, results):
        """Analyze page structure"""
        structure = {}

        # Check for pagination
        pagination_indicators = ["next", "previous", "page", "pagination"]
        for indicator in pagination_indicators:
            if soup.find(attrs={"class": lambda x: x and indicator in x.lower()}):
                structure["pagination"] = f"Found {indicator} indicators"
                break

        # Check for search functionality
        search_forms = soup.find_all("form")
        if search_forms:
            structure["search_forms"] = len(search_forms)

        # Check for paper/article listings
        common_paper_indicators = ["paper", "article", "publication", "proceeding"]
        for indicator in common_paper_indicators:
            elements = soup.find_all(
                attrs={"class": lambda x: x and indicator in x.lower()}
            )
            if elements:
                structure[f"{indicator}_elements"] = len(elements)

        results["structure"].update(structure)

    def _generate_recommendations(self, results):
        """Generate scraping recommendations"""
        recommendations = []

        if not results["accessible"]:
            recommendations.append("Site not accessible - check connectivity/blocking")
            return

        if "Heavy JavaScript" in str(results["challenges"]):
            recommendations.append("Use Selenium/Playwright for JavaScript rendering")
        else:
            recommendations.append("Simple requests + BeautifulSoup should work")

        if results["apis"]:
            recommendations.append("API approach preferred over HTML scraping")

        if "pagination" in results.get("structure", {}):
            recommendations.append("Implement pagination handling")

        if results.get("structure", {}).get("search_forms"):
            recommendations.append("Use search forms for targeted queries")

        results["recommendations"] = recommendations

    def _print_summary(self, results):
        """Print investigation summary"""
        print("\nSUMMARY:")
        print(f"Accessible: {results['accessible']}")

        if results["apis"]:
            print("APIs found:")
            for api in results["apis"]:
                print(f"  - {api}")

        if results["challenges"]:
            print("Challenges:")
            for challenge in results["challenges"]:
                print(f"  - {challenge}")

        if results["recommendations"]:
            print("Recommendations:")
            for rec in results["recommendations"]:
                print(f"  - {rec}")


def main():
    """Investigate priority scraper targets"""
    investigator = ScraperInvestigator()

    # Define investigation targets
    targets = [
        {
            "name": "CVF (Computer Vision Foundation)",
            "base_url": "https://openaccess.thecvf.com/",
            "test_paths": ["CVPR2024", "ICCV2023", "ECCV2022"],
        },
        {
            "name": "AAAI Proceedings",
            "base_url": "https://aaai.org/library/aaai-publications/",
            "test_paths": ["aaai-24-proceedings/", "aaai-23-proceedings/"],
        },
        {
            "name": "ACL Anthology",
            "base_url": "https://aclanthology.org/",
            "test_paths": ["2024.acl-long.1/", "2024.emnlp-main.1/", "venues/acl/"],
        },
        {
            "name": "Nature Communications",
            "base_url": "https://www.nature.com/ncomms/",
            "test_paths": ["articles", "search?q=machine+learning"],
        },
        {
            "name": "IJCAI Proceedings",
            "base_url": "https://www.ijcai.org/",
            "test_paths": ["proceedings/2024/", "proceedings/2023/"],
        },
    ]

    results = []

    print("Starting scraper investigation for Priority 1 targets...")

    for target in targets:
        result = investigator.investigate_site(
            target["name"], target["base_url"], target.get("test_paths")
        )
        results.append(result)

        # Be polite - small delay between sites
        time.sleep(2)

    # Save results
    with open("data/scraper_investigation_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n{'=' * 60}")
    print("INVESTIGATION COMPLETE")
    print("Results saved to data/scraper_investigation_results.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
