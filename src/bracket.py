#!/usr/bin/env python3
"""
Calculate knockout bracket pairings for FIFA World Cup 2026.
Note: Current source data doesn't provide true group info (standings are combined).
This creates a simplified 32-team bracket from top 32 teams by points.
When real group/knockout data is available, this will be replaced.
"""

import json
import sys
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

DATA_DIR = Path(__file__).parent.parent / "data"


@dataclass
class Standing:
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
    form: str = ""
    group: Optional[str] = None


@dataclass
class BracketMatch:
    round: str  # "32", "16", "8", "4", "2", "final", "3rd"
    match_num: int
    team_a_id: Optional[int] = None
    team_b_id: Optional[int] = None
    score_a: Optional[int] = None
    score_b: Optional[int] = None
    winner_slot: Optional[str] = None  # e.g., "W1" for winner of match 1
    status: str = "scheduled"  # "scheduled", "final"


def load_standings() -> list[Standing]:
    with open(DATA_DIR / "standings.json") as f:
        data = json.load(f)
    standings = [Standing(**s) for s in data]
    return standings


def load_teams() -> dict[int, dict]:
    with open(DATA_DIR / "teams.json") as f:
        return {t["id"]: t for t in json.load(f)}


def get_qualified_teams(standings: list[Standing]) -> list[Standing]:
    """Get top 32 teams by points (simplified qualification)."""
    # Sort by pts, gd, gf
    sorted_teams = sorted(standings, key=lambda x: (-x.pts, -x.gd, -x.gf))
    return sorted_teams[:32]


def generate_bracket(qualified: list[Standing]) -> list[BracketMatch]:
    """
    Generate a standard 32-team knockout bracket.
    Seeds 1-32 based on qualification ranking.
    """
    bracket = []
    
    # Round of 32: 16 matches (1v32, 2v31, 3v30, ..., 16v17)
    for i in range(16):
        team_a = qualified[i]
        team_b = qualified[31 - i]
        bracket.append(BracketMatch(
            round="32",
            match_num=i + 1,
            team_a_id=team_a.team_id,
            team_b_id=team_b.team_id,
            winner_slot=f"W{i + 1}",
            status="final",  # Group stage done, these are the knockout matches
        ))
    
    # Round of 16: 8 matches (W1vW16, W2vW15, ...)
    for i in range(8):
        bracket.append(BracketMatch(
            round="16",
            match_num=i + 1,
            winner_slot=f"W{i + 17}",
            status="scheduled",
        ))
    
    # Quarterfinals: 4 matches
    for i in range(4):
        bracket.append(BracketMatch(
            round="8",
            match_num=i + 1,
            winner_slot=f"W{i + 25}",
            status="scheduled",
        ))
    
    # Semifinals: 2 matches
    for i in range(2):
        bracket.append(BracketMatch(
            round="4",
            match_num=i + 1,
            winner_slot=f"W{i + 29}",
            status="scheduled",
        ))
    
    # Final
    bracket.append(BracketMatch(
        round="final",
        match_num=1,
        winner_slot="CHAMPION",
        status="scheduled",
    ))
    
    # 3rd place match
    bracket.append(BracketMatch(
        round="3rd",
        match_num=1,
        winner_slot="3RD_PLACE",
        status="scheduled",
    ))
    
    return bracket


def main() -> int:
    try:
        standings = load_standings()
        print(f"Loaded {len(standings)} standings")
        
        qualified = get_qualified_teams(standings)
        print(f"Qualified teams (top 32): {len(qualified)}")
        for i, t in enumerate(qualified, 1):
            print(f"  {i}. Team {t.team_id} (pts={t.pts}, gd={t.gd})")
        
        bracket = generate_bracket(qualified)
        print(f"Bracket matches: {len(bracket)}")
        
        # Save
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        with open(DATA_DIR / "bracket.json", "w") as f:
            json.dump([asdict(b) for b in bracket], f, indent=2, ensure_ascii=False)
        
        print("Saved bracket.json")
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())