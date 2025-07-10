#!/usr/bin/env python3
"""Visualize venue platforms and consolidation opportunities."""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Rectangle
import numpy as np

# Platform data
platforms = {
    "PMLR": {
        "venues": ["ICML", "AISTATS", "UAI", "CoLLAs"],
        "papers": 280,
        "status": "exists",
        "scraper": "MLRScraper"
    },
    "OpenReview": {
        "venues": ["ICLR", "COLM", "TMLR", "RLC"],
        "papers": 500,
        "status": "exists",
        "scraper": "OpenReviewScraper"
    },
    "IEEE Xplore": {
        "venues": ["ICRA", "IROS", "ICASSP", "IEEE RA-L", "ICC", "IEEE Access", "IEEE TCNS", "IEEE TKDE"],
        "papers": 150,
        "status": "new",
        "scraper": "IEEEScraper"
    },
    "ACM DL": {
        "venues": ["SIGIR", "SIGGRAPH Asia", "ACM FAccT", "ACM Computing Surveys", "ACM TOSEM"],
        "papers": 50,
        "status": "new",
        "scraper": "ACMScraper"
    },
    "Nature Portfolio": {
        "venues": ["Nature", "Scientific Reports", "Communications Biology"],
        "papers": 150,
        "status": "new",
        "scraper": "NatureScraper"
    },
    "BMC": {
        "venues": ["Molecular Autism", "BMJ Open"],
        "papers": 20,
        "status": "new",
        "scraper": "BMCScraper"
    },
    "Individual": {
        "venues": ["NeurIPS", "ACL", "EMNLP", "CVPR", "AAAI", "JMLR", "AAMAS", "eLife", "Frontiers"],
        "papers": 600,
        "status": "mixed",
        "scraper": "Various"
    }
}

# Create figure with two subplots
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 10))

# First plot: Platform distribution
colors = {
    "exists": "#4CAF50",  # Green
    "new": "#2196F3",     # Blue
    "mixed": "#FFC107"    # Amber
}

# Calculate positions for treemap-style visualization
y_pos = 0
positions = []
for platform, data in platforms.items():
    height = len(data["venues"])
    positions.append({
        "platform": platform,
        "y": y_pos,
        "height": height,
        "venues": data["venues"],
        "status": data["status"],
        "papers": data["papers"]
    })
    y_pos += height + 0.5

# Draw rectangles for each platform
for pos in positions:
    # Main rectangle
    rect = Rectangle((0, pos["y"]), 8, pos["height"], 
                    facecolor=colors[pos["status"]], 
                    edgecolor='black', 
                    linewidth=2,
                    alpha=0.7)
    ax1.add_patch(rect)
    
    # Platform name
    ax1.text(4, pos["y"] + pos["height"]/2, pos["platform"], 
            ha='center', va='center', fontsize=14, fontweight='bold')
    
    # Venue count
    ax1.text(8.5, pos["y"] + pos["height"]/2, 
            f"{len(pos['venues'])} venues\n{pos['papers']} papers", 
            ha='left', va='center', fontsize=10)
    
    # List venues
    venue_text = "\n".join(pos["venues"][:4])
    if len(pos["venues"]) > 4:
        venue_text += f"\n+{len(pos['venues'])-4} more"
    ax1.text(-0.5, pos["y"] + pos["height"]/2, venue_text, 
            ha='right', va='center', fontsize=8, style='italic')

ax1.set_xlim(-5, 12)
ax1.set_ylim(-1, y_pos)
ax1.set_title("Venue Groupings by Platform", fontsize=16, fontweight='bold')
ax1.axis('off')

# Add legend
legend_elements = [
    mpatches.Patch(color=colors["exists"], label='Existing Scraper'),
    mpatches.Patch(color=colors["new"], label='New Scraper Needed'),
    mpatches.Patch(color=colors["mixed"], label='Mixed (Some Exist)')
]
ax1.legend(handles=legend_elements, loc='upper right')

# Second plot: Implementation timeline
implementation_phases = [
    {"name": "Phase 1: Extensions", "venues": 7, "hours": 8, "color": "#4CAF50"},
    {"name": "Phase 2: Major Platforms", "venues": 16, "hours": 30, "color": "#2196F3"},
    {"name": "Phase 3: Specialized", "venues": 7, "hours": 20, "color": "#03A9F4"},
    {"name": "Phase 4: Individual", "venues": 5, "hours": 15, "color": "#00BCD4"}
]

# Create stacked bar chart
phase_names = [p["name"] for p in implementation_phases]
venues = [p["venues"] for p in implementation_phases]
hours = [p["hours"] for p in implementation_phases]
colors_phases = [p["color"] for p in implementation_phases]

x = np.arange(len(phase_names))
width = 0.35

bars1 = ax2.bar(x - width/2, venues, width, label='Venues Covered', color=colors_phases, alpha=0.8)
bars2 = ax2.bar(x + width/2, hours, width, label='Implementation Hours', color='gray', alpha=0.6)

# Add value labels on bars
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height,
                f'{int(height)}', ha='center', va='bottom')

ax2.set_xlabel('Implementation Phase', fontsize=12)
ax2.set_ylabel('Count', fontsize=12)
ax2.set_title('Implementation Roadmap', fontsize=16, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(phase_names, rotation=45, ha='right')
ax2.legend()
ax2.grid(axis='y', alpha=0.3)

# Add cumulative coverage annotation
cumulative_venues = np.cumsum(venues)
cumulative_hours = np.cumsum(hours)
for i, (cv, ch) in enumerate(zip(cumulative_venues, cumulative_hours)):
    coverage_pct = (cv / 50) * 100
    ax2.annotate(f'{coverage_pct:.0f}% coverage\n({ch}h total)', 
                xy=(i, venues[i]), 
                xytext=(i, venues[i] + 5),
                ha='center', fontsize=9,
                bbox=dict(boxstyle="round,pad=0.3", facecolor='yellow', alpha=0.5))

plt.tight_layout()
plt.savefig('venue_platform_consolidation.png', dpi=300, bbox_inches='tight')
print("Visualization saved as 'venue_platform_consolidation.png'")

# Create summary statistics
print("\n=== CONSOLIDATION SUMMARY ===")
print(f"Total venues in top 50: 50")
print(f"Venues covered by platform scrapers: 35 (70%)")
print(f"Venues needing individual scrapers: 15 (30%)")
print(f"\nPlatform scraper breakdown:")
print(f"- Existing scrapers to extend: 2 (covering 11 venues)")
print(f"- New platform scrapers needed: 4 (covering 24 venues)")
print(f"- Total platform scrapers: 6 (covering 35 venues)")
print(f"\nImplementation estimate:")
print(f"- Total hours: {sum(hours)} hours")
print(f"- Total venues covered: {sum(venues)} venues")
print(f"- Coverage efficiency: {sum(venues)/sum(hours):.1f} venues per hour")
