"""OpenReview venue mappings for different conferences and years."""

from typing import Dict, Any


OPENREVIEW_VENUES: Dict[str, Dict[str, Any]] = {
    "ICLR": {
        "venue_id": "ICLR.cc",
        "years": {
            2024: {"invitation": "ICLR.cc/2024/Conference/-/Submission"},
            2023: {"invitation": "ICLR.cc/2023/Conference/-/Submission"},
            2022: {"invitation": "ICLR.cc/2022/Conference/-/Submission"},
            2021: {"invitation": "ICLR.cc/2021/Conference/-/Submission"},
            2020: {"invitation": "ICLR.cc/2020/Conference/-/Submission"},
            2019: {"invitation": "ICLR.cc/2019/Conference/-/Submission"},
            2018: {"invitation": "ICLR.cc/2018/Conference/-/Submission"},
            2017: {"invitation": "ICLR.cc/2017/Conference/-/Submission"},
            2016: {"invitation": "ICLR.cc/2016/Conference/-/Submission"},
            2015: {"invitation": "ICLR.cc/2015/Conference/-/Submission"},
            2014: {"invitation": "ICLR.cc/2014/Conference/-/Submission"},
            2013: {"invitation": "ICLR.cc/2013/Conference/-/Submission"},
        },
        "default_invitation": "ICLR.cc/{year}/Conference/-/Submission",
    },
    "NeurIPS": {
        "venue_id": "NeurIPS.cc",
        "years": {
            2024: {"invitation": "NeurIPS.cc/2024/Conference/-/Submission"},
            2023: {"invitation": "NeurIPS.cc/2023/Conference/-/Submission"},
        },
        "default_invitation": "NeurIPS.cc/{year}/Conference/-/Submission",
        "min_year": 2023,  # Only 2023+ on OpenReview
    },
    "COLM": {
        "venue_id": "colmweb.org/COLM",
        "years": {
            2024: {"invitation": "colmweb.org/COLM/2024/Conference/-/Submission"},
        },
        "default_invitation": "colmweb.org/COLM/{year}/Conference/-/Submission",
        "min_year": 2024,
    },
    "RLC": {
        "venue_id": "rl-conference.cc",
        "years": {
            2024: {"invitation": "rl-conference.cc/RLC/2024/Conference/-/Submission"},
        },
        "default_invitation": "rl-conference.cc/RLC/{year}/Conference/-/Submission",
    },
    "GDM": {
        "venue_id": "geometricdeeplearning.com",
        "default_invitation": "geometricdeeplearning.com/ICLR{year}_Workshop/-/Submission",
    },
}


def get_venue_invitation(venue: str, year: int) -> str:
    """Get the OpenReview invitation string for a venue and year.

    Args:
        venue: Conference name (e.g., 'ICLR', 'NeurIPS')
        year: Conference year

    Returns:
        OpenReview invitation string

    Raises:
        ValueError: If venue is not supported or year is out of range
    """
    if venue not in OPENREVIEW_VENUES:
        raise ValueError(f"Unsupported venue: {venue}")

    venue_config = OPENREVIEW_VENUES[venue]

    # Check minimum year if specified
    if "min_year" in venue_config and year < venue_config["min_year"]:
        raise ValueError(
            f"{venue} papers are only available on OpenReview from "
            f"{venue_config['min_year']} onwards"
        )

    # Check for specific year configuration
    if "years" in venue_config and year in venue_config["years"]:
        return venue_config["years"][year]["invitation"]

    # Use default template if available
    if "default_invitation" in venue_config:
        return venue_config["default_invitation"].format(year=year)

    raise ValueError(f"No invitation template for {venue} {year}")


def is_venue_supported(venue: str, year: int) -> bool:
    """Check if a venue/year combination is supported on OpenReview.

    Args:
        venue: Conference name
        year: Conference year

    Returns:
        True if supported, False otherwise
    """
    try:
        get_venue_invitation(venue, year)
        return True
    except ValueError:
        return False
