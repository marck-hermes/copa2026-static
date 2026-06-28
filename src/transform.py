#!/usr/bin/env python3
"""
Parse raw HTML from native-stats.org → normalized JSON (teams, matches, standings, scorers).
Validates with pydantic schemas.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from bs4 import BeautifulSoup
from pydantic import BaseModel, Field, computed_field

# Paths
RAW_DIR = Path(__file__).parent.parent / "raw"
DATA_DIR = Path(__file__).parent.parent / "data"

# --- Pydantic Models ---

class Team(BaseModel):
    id: int
    name: str
    fifa_code: str
    flag_url: str
    group: Optional[str] = None

    @computed_field
    @property
    def flag_emoji(self) -> str:
        # FIFA 3-letter code -> ISO 2-letter code mapping for flag emoji
        fifa_to_iso = {
            "FRA": "FR", "MEX": "MX", "NED": "NL", "BRA": "BR", "ESP": "ES",
            "SUI": "CH", "MAR": "MA", "GER": "DE", "ARG": "AR", "USA": "US",
            "COL": "CO", "CIV": "CI", "ENG": "GB", "URU": "UY", "TUN": "TN",
            "NLD": "NL", "POR": "PT", "CRO": "HR", "DEN": "DK", "BEL": "BE",
            "JPN": "JP", "GHA": "GH", "CMR": "CM", "SRB": "RS", "POL": "PL",
            "KOR": "KR", "IRN": "IR", "KSA": "SA", "AUS": "AU", "CAN": "CA",
            "MAR": "MA", "SEN": "SN", "ECU": "EC", "WAL": "GB", "CMR": "CM",
            "QAT": "QA", "CRC": "CR", "NZL": "NZ", "PAN": "PA", "TUN": "TN",
            "CIV": "CI", "CMR": "CM", "GHA": "GH", "IRN": "IR", "IRQ": "IQ",
            "UZB": "UZ", "HAI": "HT", "BIH": "BA", "SCO": "GB", "CPV": "CV",
            "COD": "CD", "NOR": "NO", "CZE": "CZ", "SVK": "SK", "SVN": "SI",
            "ROU": "RO", "HUN": "HU", "AUT": "AT", "SWE": "SE", "NOR": "NO",
            "FIN": "FI", "ISL": "IS", "IRL": "IE", "NIR": "GB", "WAL": "GB",
            "FRO": "FO", "GIB": "GI", "AND": "AD", "LIE": "LI", "SMR": "SM",
            "VAT": "VA", "MCO": "MC", "MLT": "MT", "CYP": "CY",
        }
        iso = fifa_to_iso.get(self.fifa_code.upper(), self.fifa_code.upper()[:2])
        if len(iso) == 2:
            return "".join(chr(0x1F1E6 + ord(c) - ord('A')) for c in iso)
        return ""


class Match(BaseModel):
    id: int
    date_utc: str  # ISO format
    team_a_id: int
    team_b_id: int
    score_a: Optional[int] = None
    score_b: Optional[int] = None
    stage: str  # "group" | "knockout"
    group: Optional[str] = None
    status: str  # "scheduled" | "live" | "final"
    odds: Optional[str] = None


class Standing(BaseModel):
    team_id: int
    pos: int
    mp: int
    w: int
    d: int
    l: int
    gf: int
    ga: int
    gd: int
    pts: int
    form: str = ""  # e.g. "WDL"


class Scorer(BaseModel):
    rank: int
    player: str
    team_id: int
    goals: int
    assists: int
    shots: Optional[int] = None
    minutes_per_goal: Optional[float] = None


class CompetitionData(BaseModel):
    fetched_at: str
    source_url: str
    teams: list[Team]
    matches: list[Match]
    standings: list[Standing]
    scorers: list[Scorer]


# --- Parsing Functions ---

def find_latest_raw() -> Path:
    files = sorted(RAW_DIR.glob("wc_*.html"))
    if not files:
        raise FileNotFoundError("No raw HTML files found in raw/")
    return files[-1]


def parse_teams(soup: BeautifulSoup) -> list[Team]:
    """Extract teams from standings table and match rows."""
    teams = {}
    
    def extract_team_from_span(span) -> Optional[Team]:
        """Extract team from a span with phx-click attribute."""
        phx_click = span.get("phx-click", "")
        match = re.search(r'/team/(\d+)', phx_click)
        if not match:
            return None
        team_id = int(match.group(1))
        
        img = span.find("img", class_="crest-img")
        flag_url = img["src"] if img else ""
        
        name_span = span.find("span", class_=lambda x: x and "inline-block" in x and ("md:inline-block" in x or "sm:inline-block" in x))
        name = name_span.get_text(strip=True) if name_span else ""
        
        fifa_span = span.find("span", class_=lambda x: x and "sm:hidden" in x and "inline-block" in x)
        fifa_code = fifa_span.get_text(strip=True) if fifa_span else ""
        
        if name and fifa_code:
            return Team(
                id=team_id,
                name=name,
                fifa_code=fifa_code,
                flag_url=flag_url,
            )
        return None
    
    # From standings table (the main source - has all 48 teams)
    standings_heading = soup.find("h4", string="Standings:")
    if standings_heading:
        standings_table = standings_heading.find_next("table", class_="table")
        if standings_table:
            for row in standings_table.find_all("tr"):
                tds = row.find_all("td")
                if len(tds) < 2:
                    continue
                team_cell = tds[1]  # Second column is Team
                for span in team_cell.find_all("span", attrs={"phx-click": True}):
                    team = extract_team_from_span(span)
                    if team and team.id not in teams:
                        teams[team.id] = team
    
    # Also from match rows (covers teams not in standings yet)
    for table_id in ["last_matches", "next_matches"]:
        table = soup.find("tbody", id=table_id)
        if table:
            for row in table.find_all("tr"):
                for team_div in row.find_all("div", style=lambda x: x and "width: 120px" in x):
                    for span in team_div.find_all("span", attrs={"phx-click": True}):
                        team = extract_team_from_span(span)
                        if team and team.id not in teams:
                            teams[team.id] = team
    
    return list(teams.values())


def parse_matches(soup: BeautifulSoup) -> list[Match]:
    matches = []
    
    def get_team_id_from_div(team_div) -> int:
        for span in team_div.find_all("span", attrs={"phx-click": True}):
            phx_click = span.get("phx-click", "")
            match = re.search(r'/team/(\d+)', phx_click)
            if match:
                return int(match.group(1))
        return 0
    
    for table_id, status in [("last_matches", "final"), ("next_matches", "scheduled")]:
        table = soup.find("tbody", id=table_id)
        if not table:
            continue
        
        for row in table.find_all("tr"):
            th = row.find("th")
            if not th:
                continue
            date_str = th.get_text(strip=True)  # "2026/06/27, 05h00"
            
            # Parse date
            try:
                # Format: "2026/06/27, 05h00"
                date_part, time_part = date_str.split(", ")
                year, month, day = map(int, date_part.split("/"))
                hour, minute = map(int, time_part.replace("h", ":").split(":"))
                dt = datetime(year, month, day, hour, minute)
                date_utc = dt.isoformat() + "Z"
            except Exception:
                date_utc = ""
            
            # Team A
            team_divs = row.find_all("div", style=lambda x: x and "width: 120px" in x)
            team_a_id = get_team_id_from_div(team_divs[0]) if len(team_divs) > 0 else 0
            team_b_id = get_team_id_from_div(team_divs[1]) if len(team_divs) > 1 else 0
            
            # Score
            score_td = row.find("td", class_="whitespace-nowrap")
            score_a = score_b = None
            if score_td:
                # Score is in span with class "hover:cursor-pointer" or "animate-pulse"
                score_span = score_td.find("span", class_=lambda x: x and ("hover:cursor-pointer" in x or "animate-pulse" in x))
                if score_span:
                    score_text = score_span.get_text(strip=True)  # "1:5" or "0:0"
                    if ":" in score_text:
                        try:
                            score_a, score_b = map(int, score_text.split(":"))
                        except ValueError:
                            pass
            
            # Odds
            odds_td = row.find_all("td", class_="whitespace-nowrap")
            odds = odds_td[-1].get_text(strip=True) if len(odds_td) > 1 else None
            
            # Match ID from phx-click in score column
            match_id = 0
            if score_td:
                for elem in score_td.find_all(attrs={"phx-click": True}):
                    phx = elem.get("phx-click", "")
                    match = re.search(r'/match/(\d+)', phx)
                    if match:
                        match_id = int(match.group(1))
                        break
            
            matches.append(Match(
                id=match_id,
                date_utc=date_utc,
                team_a_id=team_a_id,
                team_b_id=team_b_id,
                score_a=score_a,
                score_b=score_b,
                stage="group",  # All current matches are group stage
                group=None,  # Would need group info from elsewhere
                status=status,
                odds=odds,
            ))
    
    return matches


def parse_standings(soup: BeautifulSoup) -> list[Standing]:
    standings = []
    # Find the standings table - it's after "Standings:" heading
    standings_heading = soup.find("h4", string="Standings:")
    if not standings_heading:
        return standings
    
    table = standings_heading.find_next("table", class_="table")
    if not table:
        return standings
    
    for row in table.find_all("tr"):
        tds = row.find_all("td")
        if len(tds) < 6:
            continue
        
        # Position
        pos_text = tds[0].get_text(strip=True).rstrip(".")
        if not pos_text.isdigit():
            continue
        pos = int(pos_text)
        
        # Team - find span with phx-click
        team_cell = tds[1]
        team_id = 0
        for span in team_cell.find_all("span", attrs={"phx-click": True}):
            phx_click = span.get("phx-click", "")
            match = re.search(r'/team/(\d+)', phx_click)
            if match:
                team_id = int(match.group(1))
                break
        if not team_id:
            continue
        
        # Stats
        mp = int(tds[2].get_text(strip=True))
        pts = int(tds[3].get_text(strip=True))
        gd = int(tds[4].get_text(strip=True))
        goals = tds[5].get_text(strip=True)  # "10:2"
        gf, ga = map(int, goals.split(":"))
        
        # Derive W/D/L from MP, PTS, GD
        # This is approximate - real data would need explicit W/D/L
        w = pts // 3
        remaining = pts % 3
        d = remaining
        l = mp - w - d
        
        standings.append(Standing(
            team_id=team_id,
            pos=pos,
            mp=mp,
            w=w,
            d=d,
            l=l,
            gf=gf,
            ga=ga,
            gd=gd,
            pts=pts,
        ))
    
    return standings


def parse_scorers(soup: BeautifulSoup) -> list[Scorer]:
    scorers = []
    table = soup.find("table", id="top_scorer_table")
    if not table:
        return scorers
    
    tbody = table.find("tbody")
    if not tbody:
        return scorers
    
    for row in tbody.find_all("tr"):
        tds = row.find_all("td")
        if len(tds) < 8:
            continue
        
        rank = int(tds[0].get_text(strip=True).rstrip("."))
        
        # Player name and team - inside div with phx-click
        player_cell = tds[1]
        player_div = player_cell = player_div = player_cell.find("div", attrs={"phx-click": True})
        player_name = ""
        team_id = 0
        if player_div:
            name_span = player_div.find("span", class_=lambda x: x and "pl-2" in x)
            player_name = name_span.get_text(strip=True) if name_span else ""
            team_img = player_div.find("img")
            if team_img and team_img.get("src"):
                src = team_img["src"]
                match = re.search(r"/(\d+)\.(?:svg|png)", src)
                if match:
                    team_id = int(match.group(1))
        
        goals = int(tds[3].get_text(strip=True))
        assists = int(tds[4].get_text(strip=True))
        shots = None
        try:
            shots = int(tds[5].get_text(strip=True))
        except ValueError:
            pass
        
        min_per_goal = None
        try:
            min_per_goal = float(tds[7].get_text(strip=True))
        except ValueError:
            pass
        
        scorers.append(Scorer(
            rank=rank,
            player=player_name,
            team_id=team_id,
            goals=goals,
            assists=assists,
            shots=shots,
            minutes_per_goal=min_per_goal,
        ))
    
    return scorers


def main() -> int:
    try:
        raw_file = find_latest_raw()
        print(f"Parsing {raw_file}")
        
        html = raw_file.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")
        
        teams = parse_teams(soup)
        matches = parse_matches(soup)
        standings = parse_standings(soup)
        scorers = parse_scorers(soup)
        
        data = CompetitionData(
            fetched_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            source_url="https://native-stats.org/competition/WC/",
            teams=teams,
            matches=matches,
            standings=standings,
            scorers=scorers,
        )
        
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Save individual files
        (DATA_DIR / "teams.json").write_text(json.dumps([t.model_dump() for t in teams], indent=2, ensure_ascii=False))
        (DATA_DIR / "matches.json").write_text(json.dumps([m.model_dump() for m in matches], indent=2, ensure_ascii=False))
        (DATA_DIR / "standings.json").write_text(json.dumps([s.model_dump() for s in standings], indent=2, ensure_ascii=False))
        (DATA_DIR / "scorers.json").write_text(json.dumps([s.model_dump() for s in scorers], indent=2, ensure_ascii=False))
        
        # Save combined
        (DATA_DIR / "competition.json").write_text(data.model_dump_json(indent=2, ensure_ascii=False))
        
        print(f"Teams: {len(teams)}")
        print(f"Matches: {len(matches)}")
        print(f"Standings: {len(standings)}")
        print(f"Scorers: {len(scorers)}")
        print("Done.")
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())