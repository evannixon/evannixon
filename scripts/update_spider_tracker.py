import os
import json
import urllib.request
from datetime import datetime

USERNAME = os.environ.get("GITHUB_USER", "evannixon")
TOKEN = os.environ.get("GITHUB_TOKEN", "")

WIDTH = 860
HEIGHT = 240
START_X = 40
START_Y = 65
BOX_SIZE = 11
BOX_GAP = 4
COLS = 52
ROWS = 7

PALETTE = [
    "#161b22", # empty / dark slate
    "#4c0519", # 1-2 commits
    "#881337", # 3-5 commits
    "#be123c", # 6-9 commits
    "#e11d48", # 10-14 commits (spider crimson)
    "#fb7185", # 15+ commits (bright glow crimson)
]

def fetch_contributions_graphql(username, token):
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
                weekday
              }
            }
          }
        }
      }
    }
    """
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": username}}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "Spider-Tracker-Bot",
            "Content-Type": "application/json"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", {}).get("user", {}).get("contributionsCollection", {}).get("contributionCalendar")
    except Exception as e:
        print(f"GraphQL request failed: {e}")
        return None

def fetch_contributions_public(username):
    url = f"https://github-contributions-api.jogruber.de/v4/{username}?y=last"
    req = urllib.request.Request(url, headers={"User-Agent": "Spider-Tracker-Bot"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            total = data.get("total", {}).get("lastYear", 0)
            contributions = data.get("contributions", [])
            weeks = []
            curr_week = []
            for item in contributions:
                curr_week.append({
                    "contributionCount": item.get("count", 0),
                    "date": item.get("date"),
                    "weekday": len(curr_week)
                })
                if len(curr_week) == 7:
                    weeks.append({"contributionDays": curr_week})
                    curr_week = []
            if curr_week:
                weeks.append({"contributionDays": curr_week})
            return {"totalContributions": total, "weeks": weeks[-52:]}
    except Exception as e:
        print(f"Public API fetch failed: {e}")
        return None

def get_color(count):
    if count == 0:
        return PALETTE[0]
    elif count <= 2:
        return PALETTE[1]
    elif count <= 5:
        return PALETTE[2]
    elif count <= 9:
        return PALETTE[3]
    elif count <= 14:
        return PALETTE[4]
    else:
        return PALETTE[5]

def generate_svg(calendar_data, output_path):
    total_contributions = 0
    weeks = []
    
    if calendar_data:
        total_contributions = calendar_data.get("totalContributions", 0)
        weeks = calendar_data.get("weeks", [])
    
    if len(weeks) > 52:
        weeks = weeks[-52:]
    while len(weeks) < 52:
        weeks.insert(0, {"contributionDays": [{"contributionCount": 0} for _ in range(7)]})

    grid_rects = []
    active_points = []

    for c, week in enumerate(weeks):
        days = week.get("contributionDays", [])
        for r in range(7):
            count = days[r].get("contributionCount", 0) if r < len(days) else 0
            color = get_color(count)
            x = START_X + c * (BOX_SIZE + BOX_GAP)
            y = START_Y + r * (BOX_SIZE + BOX_GAP)
            grid_rects.append(f'<rect x="{x}" y="{y}" width="{BOX_SIZE}" height="{BOX_SIZE}" rx="2" fill="{color}" />')
            
            if count > 0:
                active_points.append((x + BOX_SIZE // 2, y + BOX_SIZE // 2))

    # Spider crawl waypoints
    if len(active_points) >= 6:
        step = max(1, len(active_points) // 8)
        selected_waypoints = [active_points[i] for i in range(0, len(active_points), step)][:8]
    else:
        selected_waypoints = [
            (START_X + 5 * 15, START_Y + 1 * 15),
            (START_X + 15 * 15, START_Y + 4 * 15),
            (START_X + 25 * 15, START_Y + 2 * 15),
            (START_X + 35 * 15, START_Y + 5 * 15),
            (START_X + 45 * 15, START_Y + 1 * 15),
            (START_X + 50 * 15, START_Y + 4 * 15),
            (START_X + 30 * 15, START_Y + 6 * 15),
        ]

    spider_path_d = f"M {selected_waypoints[0][0]},{selected_waypoints[0][1]} " + " ".join([f"L {x},{y}" for x, y in selected_waypoints[1:]]) + " Z"
    grid_svg = "\n    ".join(grid_rects)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="100%" height="100%" style="background: transparent; cursor: pointer;">
  <a href="https://github.com/evannixon?tab=overview" target="_blank" style="text-decoration: none;">
  <defs>
    <!-- Background Gradient -->
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0b0e14" />
      <stop offset="50%" stop-color="#0f141c" />
      <stop offset="100%" stop-color="#090b10" />
    </linearGradient>

    <!-- Crimson Glow Filter -->
    <filter id="crimsonGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>

    <!-- Radar Beam Gradient -->
    <linearGradient id="radarBeam" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#e11d48" stop-opacity="0" />
      <stop offset="50%" stop-color="#e11d48" stop-opacity="0.25" />
      <stop offset="100%" stop-color="#fb7185" stop-opacity="0.8" />
    </linearGradient>

    <!-- Spider Drone Sprite -->
    <g id="spiderBot">
      <ellipse cx="0" cy="0" rx="4" ry="5.5" fill="#e11d48" filter="url(#crimsonGlow)" />
      <circle cx="0" cy="-4" r="2.5" fill="#ffffff" />
      <circle cx="-1" cy="-4.5" r="0.8" fill="#e11d48" />
      <circle cx="1" cy="-4.5" r="0.8" fill="#e11d48" />
      <!-- Left Legs -->
      <path d="M -3,-2 Q -8,-5 -9,-1" stroke="#e11d48" stroke-width="1.2" fill="none" stroke-linecap="round" />
      <path d="M -3,0 Q -10,0 -10,4" stroke="#e11d48" stroke-width="1.2" fill="none" stroke-linecap="round" />
      <path d="M -3,2 Q -9,5 -8,8" stroke="#e11d48" stroke-width="1.2" fill="none" stroke-linecap="round" />
      <path d="M -2,4 Q -6,8 -5,11" stroke="#e11d48" stroke-width="1" fill="none" stroke-linecap="round" />
      <!-- Right Legs -->
      <path d="M 3,-2 Q 8,-5 9,-1" stroke="#e11d48" stroke-width="1.2" fill="none" stroke-linecap="round" />
      <path d="M 3,0 Q 10,0 10,4" stroke="#e11d48" stroke-width="1.2" fill="none" stroke-linecap="round" />
      <path d="M 3,2 Q 9,5 8,8" stroke="#e11d48" stroke-width="1.2" fill="none" stroke-linecap="round" />
      <path d="M 2,4 Q 6,8 5,11" stroke="#e11d48" stroke-width="1" fill="none" stroke-linecap="round" />
      <!-- Pulsing Core -->
      <circle cx="0" cy="0" r="1.5" fill="#ffffff">
        <animate attributeName="opacity" values="0.4;1;0.4" dur="0.8s" repeatCount="indefinite" />
      </circle>
    </g>
  </defs>

  <style>
    @keyframes radarSweep {{
      0% {{ transform: translateX(-150px); opacity: 0; }}
      20% {{ opacity: 0.8; }}
      80% {{ opacity: 0.8; }}
      100% {{ transform: translateX(850px); opacity: 0; }}
    }}
    @keyframes hudBlink {{
      0%, 100% {{ opacity: 1; }}
      50% {{ opacity: 0.3; }}
    }}
    .radar-beam {{
      animation: radarSweep 7s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    }}
    .live-dot {{
      animation: hudBlink 1.5s ease-in-out infinite;
    }}
    .tech-font {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, monospace;
    }}
    .web-trail {{
      stroke-dasharray: 6 3;
      animation: dash 15s linear infinite;
    }}
    @keyframes dash {{
      to {{
        stroke-dashoffset: -100;
      }}
    }}
    .hover-border {{
      transition: stroke 0.3s ease;
    }}
    svg:hover .hover-border {{
      stroke: #e11d48;
    }}
  </style>

  <!-- Container Box -->
  <rect x="2" y="2" width="{WIDTH - 4}" height="{HEIGHT - 4}" rx="10" fill="url(#bgGrad)" stroke="#272f3d" stroke-width="1.5" class="hover-border" />
  
  <!-- Corner Accents (Spidey HUD Styling) -->
  <path d="M 2 20 L 2 2 L 20 2" stroke="#e11d48" stroke-width="2.5" fill="none" />
  <path d="M {WIDTH - 20} 2 L {WIDTH - 2} 2 L {WIDTH - 2} 20" stroke="#e11d48" stroke-width="2.5" fill="none" />
  <path d="M 2 {HEIGHT - 20} L 2 {HEIGHT - 2} L 20 {HEIGHT - 2}" stroke="#e11d48" stroke-width="2.5" fill="none" />
  <path d="M {WIDTH - 20} {HEIGHT - 2} L {WIDTH - 2} {HEIGHT - 2} L {WIDTH - 2} {HEIGHT - 20}" stroke="#e11d48" stroke-width="2.5" fill="none" />

  <!-- Top Header HUD -->
  <g transform="translate(40, 32)">
    <circle cx="8" cy="8" r="7" fill="none" stroke="#e11d48" stroke-width="1.2" />
    <circle cx="8" cy="8" r="3" fill="#e11d48" />
    <line x1="8" y1="1" x2="8" y2="15" stroke="#e11d48" stroke-width="1" stroke-opacity="0.5" />
    <line x1="1" y1="8" x2="15" y2="8" stroke="#e11d48" stroke-width="1" stroke-opacity="0.5" />

    <text x="24" y="9" fill="#f1f5f9" font-size="13" font-weight="700" letter-spacing="1.5" class="tech-font">SPIDER-TRACKER // REALTIME RADAR PATROL MATRIX</text>
    <text x="24" y="22" fill="#64748b" font-size="9" letter-spacing="1" class="tech-font">LIVE SYNC • CLICK ANYWHERE TO VIEW GITHUB ACTIVITY TIMELINE</text>

    <!-- Live Indicator Pill -->
    <rect x="{WIDTH - 240}" y="-2" width="150" height="24" rx="4" fill="#161b22" stroke="#334155" stroke-width="1" />
    <circle cx="{WIDTH - 228}" cy="10" r="3.5" fill="#e11d48" class="live-dot" />
    <text x="{WIDTH - 216}" y="14" fill="#cbd5e1" font-size="10" font-weight="600" letter-spacing="0.8" class="tech-font">API: SYNCED LIVE</text>
  </g>

  <!-- Contribution Heatmap Grid -->
  <g>
    {grid_svg}
  </g>

  <!-- Days of week indicators -->
  <g fill="#475569" font-size="8" class="tech-font" text-anchor="middle">
    <text x="26" y="{START_Y + 1 * (BOX_SIZE + BOX_GAP) + 8}">M</text>
    <text x="26" y="{START_Y + 3 * (BOX_SIZE + BOX_GAP) + 8}">W</text>
    <text x="26" y="{START_Y + 5 * (BOX_SIZE + BOX_GAP) + 8}">F</text>
  </g>

  <!-- Laser Radar Scanning Sweep -->
  <g clip-path="url(#gridClip)">
    <clipPath id="gridClip">
      <rect x="{START_X}" y="{START_Y}" width="{COLS * (BOX_SIZE + BOX_GAP)}" height="{ROWS * (BOX_SIZE + BOX_GAP)}" />
    </clipPath>
    <rect x="0" y="{START_Y - 10}" width="70" height="{ROWS * (BOX_SIZE + BOX_GAP) + 20}" fill="url(#radarBeam)" class="radar-beam" />
  </g>

  <!-- Realtime Web Trail along actual nodes -->
  <path d="{spider_path_d}" fill="none" stroke="#e11d48" stroke-width="1.2" stroke-opacity="0.4" class="web-trail" />

  <!-- Spider Bot Crawling across user's real commits -->
  <g>
    <use href="#spiderBot">
      <animateMotion path="{spider_path_d}" dur="20s" repeatCount="indefinite" rotate="auto" />
    </use>
  </g>

  <!-- Bottom Legend & Telemetry Bar -->
  <g transform="translate(40, {HEIGHT - 24})">
    <text x="0" y="9" fill="#64748b" font-size="9" letter-spacing="0.8" class="tech-font">RADAR COMMITS: <tspan fill="#e11d48" font-weight="700">{total_contributions}+ LOGGED</tspan> | SYSTEM: <tspan fill="#e11d48" font-weight="700">ONLINE</tspan></text>

    <!-- Legend -->
    <g transform="translate({WIDTH - 230}, 0)">
      <text x="-28" y="9" fill="#475569" font-size="8" class="tech-font">Less</text>
      <rect x="0" y="1" width="9" height="9" rx="2" fill="{PALETTE[0]}" />
      <rect x="13" y="1" width="9" height="9" rx="2" fill="{PALETTE[1]}" />
      <rect x="26" y="1" width="9" height="9" rx="2" fill="{PALETTE[2]}" />
      <rect x="39" y="1" width="9" height="9" rx="2" fill="{PALETTE[3]}" />
      <rect x="52" y="1" width="9" height="9" rx="2" fill="{PALETTE[4]}" />
      <rect x="65" y="1" width="9" height="9" rx="2" fill="{PALETTE[5]}" />
      <text x="80" y="9" fill="#475569" font-size="8" class="tech-font">More</text>
    </g>
  </g>
  </a>
</svg>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"Generated real-time Spider-Tracker SVG at: {output_path} (Total contributions: {total_contributions})")

if __name__ == "__main__":
    calendar = None
    if TOKEN:
        print("Fetching via GitHub GraphQL API...")
        calendar = fetch_contributions_graphql(USERNAME, TOKEN)
    
    if not calendar:
        print("Fetching via public fallback API...")
        calendar = fetch_contributions_public(USERNAME)

    out_file = os.path.join(os.path.dirname(__file__), "..", "assets", "spider_tracker.svg")
    generate_svg(calendar, out_file)
