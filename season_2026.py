"""Canonical data and idempotent database setup for Debate League 2026."""

from collections import Counter
from datetime import date
from itertools import combinations

from sqlalchemy.orm import Session

from models import (
    Auction,
    AuctionPlayer,
    AuctionTeam,
    Debate,
    Pool,
    Round,
    Speaker,
    SpeakerPerformance,
    Team,
)


TEAM_EMOJIS_2026 = {
    "Broken Orators": "🎙️",
    "Mechanised Yappers": "⚙️",
    "Fifth Amendment": "📜",
    "Akali Dinosaurs": "⚖️",
    "Motion Granted": "🔨",
    "Damsel Inflicting Stress": "🌪️",
    "Goodfellas": "🕶️",
    "Rhetoric Rebels": "🔥",
}

GROUP_STAGE_TIME_2026 = "6:30 PM"
GROUP_STAGE_TIME_SORT_2026 = "18:30"
GROUP_STAGE_TIME_OVERRIDES_2026 = {
    12: ("9:00 AM", "09:00"),
}


OFFICIAL_2026_AUCTION = (
    ("Broken Orators", "Akshat Agrawal", "#d6a62e", (
        ("Dhruv", 5000), ("Mohit Sharma", 25000), ("Akansh", 10000), ("Divsargun", 10000),
    )),
    ("Mechanised Yappers", "Ketan Kumar", "#4cb8e8", (
        ("Manav", 5000), ("Lakshit Chaudhary", 30500), ("Shayan", 5000), ("Bhavya Issarani", 9500),
    )),
    ("Goodfellas", "Rahul Batra", "#e08a45", (
        ("Priyanka", 7500), ("Manroop Singh", 25500), ("Pranay", 5000), ("Vallari", 6000),
    )),
    ("Rhetoric Rebels", "Priyanshi", "#4b91a7", (
        ("Prachi", 5000), ("Ramneet", 10000), ("Ashmita", 18500), ("Naman", 16500),
    )),
    ("Akali Dinosaurs", "Guransh", "#dc725f", (
        ("Harasees", 35000), ("Vikramjit", 5000), ("Sahil", 5000), ("Beerdavinder", 5000),
    )),
    ("Fifth Amendment", "Satyam", "#9b7bc2", (
        ("Hridya", 21500), ("Rahul", 8000), ("Mohit Verma", 15500), ("Ankit", 5000),
    )),
    ("Damsel Inflicting Stress", "Rachel", "#df8ab4", (
        ("Mudit", 6000), ("Prabhleen", 20000), ("Soumya", 6000), ("Saksham", 18000),
    )),
    ("Motion Granted", "Tvishaa Patnaik", "#58a879", (
        ("Agamjot", 20500), ("Keshav", 15500), ("Shaurya", 5000), ("Sanjeevan", 9000),
    )),
)


OFFICIAL_POOLS_2026 = {
    "Pool A": (
        ("Broken Orators", "Akshat's Team"),
        ("Mechanised Yappers", "Ketan's Team"),
        ("Goodfellas", "Rahul's Team"),
        ("Rhetoric Rebels", "Priyanshi's Team"),
    ),
    "Pool B": (
        ("Akali Dinosaurs", "Guransh's Team"),
        ("Fifth Amendment", "Satyam's Team"),
        ("Damsel Inflicting Stress", "Rachel's Team"),
        ("Motion Granted", "Tvishaa's Team"),
    ),
}


OFFICIAL_GROUP_STAGE_2026 = (
    (1, date(2026, 8, 17), "Pool B", "Damsel Inflicting Stress", "Akali Dinosaurs"),
    (2, date(2026, 8, 17), "Pool A", "Goodfellas", "Broken Orators"),
    (3, date(2026, 8, 18), "Pool A", "Mechanised Yappers", "Rhetoric Rebels"),
    (4, date(2026, 8, 18), "Pool B", "Fifth Amendment", "Motion Granted"),
    (5, date(2026, 8, 19), "Pool A", "Broken Orators", "Mechanised Yappers"),
    (6, date(2026, 8, 19), "Pool B", "Akali Dinosaurs", "Fifth Amendment"),
    (7, date(2026, 8, 20), "Pool A", "Goodfellas", "Rhetoric Rebels"),
    (8, date(2026, 8, 20), "Pool B", "Akali Dinosaurs", "Motion Granted"),
    (9, date(2026, 8, 20), "Pool B", "Damsel Inflicting Stress", "Fifth Amendment"),
    (10, date(2026, 8, 21), "Pool A", "Goodfellas", "Mechanised Yappers"),
    (11, date(2026, 8, 21), "Pool B", "Damsel Inflicting Stress", "Motion Granted"),
    (12, date(2026, 8, 22), "Pool A", "Broken Orators", "Rhetoric Rebels"),
)


# Speaker names here deliberately match the existing registered Speaker rows.
# The submitted lineup names "Sahil Pawar", "Akshat", and "Rahul" resolve to
# the already registered Sahil, Akshat Agrawal, and Rahul Batra respectively.
OFFICIAL_RESULTS_2026 = (
    {
        "fixture_number": 1,
        "government_team": "Akali Dinosaurs",
        "opposition_team": "Damsel Inflicting Stress",
        "winner_team": "Damsel Inflicting Stress",
        "government_reply_score": 37.0,
        "opposition_reply_score": 37.0,
        "performances": (
            ("Akali Dinosaurs", "Sahil", "Prime Minister", 71.0),
            ("Akali Dinosaurs", "Harasees", "Deputy Prime Minister", 73.0),
            ("Akali Dinosaurs", "Guransh", "Government Whip", 74.0),
            ("Damsel Inflicting Stress", "Rachel", "Leader of Opposition", 73.0),
            ("Damsel Inflicting Stress", "Mudit", "Deputy Leader of Opposition", 73.5),
            ("Damsel Inflicting Stress", "Prabhleen", "Opposition Whip", 74.5),
        ),
    },
    {
        "fixture_number": 2,
        "government_team": "Broken Orators",
        "opposition_team": "Goodfellas",
        "winner_team": "Broken Orators",
        "government_reply_score": 37.0,
        "opposition_reply_score": 37.0,
        "performances": (
            ("Broken Orators", "Akshat Agrawal", "Prime Minister", 73.0),
            ("Broken Orators", "Dhruv", "Deputy Prime Minister", 72.0),
            ("Broken Orators", "Mohit Sharma", "Government Whip", 74.0),
            ("Goodfellas", "Priyanka", "Leader of Opposition", 72.5),
            ("Goodfellas", "Rahul Batra", "Deputy Leader of Opposition", 71.5),
            ("Goodfellas", "Manroop Singh", "Opposition Whip", 72.5),
        ),
    },
    {
        "fixture_number": 3,
        "government_team": "Rhetoric Rebels",
        "opposition_team": "Mechanised Yappers",
        "winner_team": "Mechanised Yappers",
        "government_reply_score": 37.0,
        "opposition_reply_score": 37.0,
        "performances": (
            ("Rhetoric Rebels", "Ramneet", "Prime Minister", 73.0),
            ("Rhetoric Rebels", "Priyanshi", "Deputy Prime Minister", 72.0),
            ("Rhetoric Rebels", "Ashmita", "Government Whip", 73.0),
            ("Mechanised Yappers", "Manav", "Leader of Opposition", 72.0),
            ("Mechanised Yappers", "Ketan Kumar", "Deputy Leader of Opposition", 72.5),
            ("Mechanised Yappers", "Lakshit Chaudhary", "Opposition Whip", 74.0),
        ),
    },
    {
        "fixture_number": 4,
        "government_team": "Motion Granted",
        "opposition_team": "Fifth Amendment",
        "winner_team": "Fifth Amendment",
        "government_reply_score": 36.0,
        "opposition_reply_score": 37.0,
        "performances": (
            ("Motion Granted", "Tvishaa Patnaik", "Prime Minister", 73.0),
            ("Motion Granted", "Keshav", "Deputy Prime Minister", 72.5),
            ("Motion Granted", "Agamjot", "Government Whip", 72.5),
            ("Fifth Amendment", "Satyam", "Leader of Opposition", 73.0),
            ("Fifth Amendment", "Mohit Verma", "Deputy Leader of Opposition", 72.0),
            ("Fifth Amendment", "Hridya", "Opposition Whip", 72.5),
        ),
    },
    {
        "fixture_number": 5,
        "government_team": "Mechanised Yappers",
        "opposition_team": "Broken Orators",
        "winner_team": "Mechanised Yappers",
        "government_reply_score": 36.0,
        "opposition_reply_score": 36.0,
        "performances": (
            ("Mechanised Yappers", "Bhavya Issarani", "Prime Minister", 73.5),
            ("Mechanised Yappers", "Ketan Kumar", "Deputy Prime Minister", 72.5),
            ("Mechanised Yappers", "Lakshit Chaudhary", "Government Whip", 74.5),
            ("Broken Orators", "Akshat Agrawal", "Leader of Opposition", 73.0),
            ("Broken Orators", "Dhruv", "Deputy Leader of Opposition", 72.5),
            ("Broken Orators", "Mohit Sharma", "Opposition Whip", 74.0),
        ),
    },
    {
        "fixture_number": 6,
        "government_team": "Fifth Amendment",
        "opposition_team": "Akali Dinosaurs",
        "winner_team": "Fifth Amendment",
        "government_reply_score": 36.0,
        "opposition_reply_score": 37.0,
        "performances": (
            ("Fifth Amendment", "Ankit", "Prime Minister", 73.0),
            ("Fifth Amendment", "Mohit Verma", "Deputy Prime Minister", 73.5),
            ("Fifth Amendment", "Mohit Verma", "Government Whip", 72.0, True),
            ("Akali Dinosaurs", "Beerdavinder", "Leader of Opposition", 72.0),
            ("Akali Dinosaurs", "Harasees", "Deputy Leader of Opposition", 72.0),
            ("Akali Dinosaurs", "Guransh", "Opposition Whip", 72.5),
        ),
    },
    {
        "fixture_number": 7,
        "government_team": "Rhetoric Rebels",
        "opposition_team": "Goodfellas",
        "winner_team": "Rhetoric Rebels",
        "government_reply_score": 37.0,
        "opposition_reply_score": 36.0,
        "performances": (
            ("Rhetoric Rebels", "Naman", "Prime Minister", 73.0),
            ("Rhetoric Rebels", "Priyanshi", "Deputy Prime Minister", 74.5),
            ("Rhetoric Rebels", "Ashmita", "Government Whip", 73.5),
            ("Goodfellas", "Vallari", "Leader of Opposition", 72.5),
            ("Goodfellas", "Rahul Batra", "Deputy Leader of Opposition", 74.5),
            ("Goodfellas", "Manroop Singh", "Opposition Whip", 73.0),
        ),
    },
    {
        "fixture_number": 8,
        "government_team": "Motion Granted",
        "opposition_team": "Akali Dinosaurs",
        "winner_team": "Akali Dinosaurs",
        "government_reply_score": 35.0,
        "opposition_reply_score": 35.0,
        "performances": (
            ("Motion Granted", "Sanjeevan", "Prime Minister", 71.5),
            ("Motion Granted", "Keshav", "Deputy Prime Minister", 71.0),
            ("Motion Granted", "Agamjot", "Government Whip", 72.0),
            ("Akali Dinosaurs", "Sahil", "Leader of Opposition", 72.0),
            ("Akali Dinosaurs", "Vikramjit", "Deputy Leader of Opposition", 72.5),
            ("Akali Dinosaurs", "Guransh", "Opposition Whip", 73.5),
        ),
    },
    {
        "fixture_number": 9,
        "government_team": "Fifth Amendment",
        "opposition_team": "Damsel Inflicting Stress",
        "winner_team": "Damsel Inflicting Stress",
        "government_reply_score": 38.0,
        "opposition_reply_score": 37.0,
        "performances": (
            ("Fifth Amendment", "Rahul", "Prime Minister", 73.0),
            ("Fifth Amendment", "Satyam", "Deputy Prime Minister", 73.5),
            ("Fifth Amendment", "Hridya", "Government Whip", 72.5),
            ("Damsel Inflicting Stress", "Soumya", "Leader of Opposition", 72.0),
            ("Damsel Inflicting Stress", "Saksham", "Deputy Leader of Opposition", 74.5),
            ("Damsel Inflicting Stress", "Prabhleen", "Opposition Whip", 74.5),
        ),
    },
    {
        "fixture_number": 10,
        "government_team": "Goodfellas",
        "opposition_team": "Mechanised Yappers",
        "winner_team": "Goodfellas",
        "government_reply_score": 37.0,
        "opposition_reply_score": 36.0,
        "performances": (
            ("Goodfellas", "Pranay", "Prime Minister", 72.5),
            ("Goodfellas", "Vallari", "Deputy Prime Minister", 73.5),
            ("Goodfellas", "Rahul Batra", "Government Whip", 74.0),
            ("Mechanised Yappers", "Bhavya Issarani", "Leader of Opposition", 72.0),
            ("Mechanised Yappers", "Shayan", "Deputy Leader of Opposition", 73.0),
            ("Mechanised Yappers", "Lakshit Chaudhary", "Opposition Whip", 73.5),
        ),
    },
    {
        "fixture_number": 11,
        "government_team": "Damsel Inflicting Stress",
        "opposition_team": "Motion Granted",
        "winner_team": "Motion Granted",
        "government_reply_score": 37.0,
        "opposition_reply_score": 37.0,
        "performances": (
            ("Damsel Inflicting Stress", "Rachel", "Prime Minister", 72.5),
            ("Damsel Inflicting Stress", "Saksham", "Deputy Prime Minister", 72.0),
            ("Damsel Inflicting Stress", "Mudit", "Government Whip", 73.5),
            ("Motion Granted", "Shaurya", "Leader of Opposition", 73.5),
            ("Motion Granted", "Agamjot", "Deputy Leader of Opposition", 74.0),
            ("Motion Granted", "Tvishaa Patnaik", "Opposition Whip", 72.5),
        ),
    },
    {
        "fixture_number": 12,
        "government_team": "Broken Orators",
        "opposition_team": "Rhetoric Rebels",
        "winner_team": "Rhetoric Rebels",
        "government_reply_score": 37.0,
        "opposition_reply_score": 38.0,
        "performances": (
            ("Broken Orators", "Divsargun", "Prime Minister", 73.0),
            ("Broken Orators", "Akansh", "Deputy Prime Minister", 73.5),
            ("Broken Orators", "Mohit Sharma", "Government Whip", 74.5),
            ("Rhetoric Rebels", "Prachi", "Leader of Opposition", 73.5),
            ("Rhetoric Rebels", "Priyanshi", "Deputy Leader of Opposition", 75.0),
            ("Rhetoric Rebels", "Ashmita", "Opposition Whip", 73.5),
        ),
    },

)
OFFICIAL_DAY_1_RESULTS_2026 = OFFICIAL_RESULTS_2026[:2]

OFFICIAL_RESULTS_BY_FIXTURE_2026 = {
    result["fixture_number"]: result
    for result in OFFICIAL_RESULTS_2026
}


TEAM_NAME_ALIASES_2026 = {
    "Damsel Inflicting Distress": "Damsel Inflicting Stress",
}


def validate_official_group_stage() -> None:
    """Fail fast if the canonical fixture list stops satisfying the brief."""
    fixtures = OFFICIAL_GROUP_STAGE_2026
    official_by_pool = {
        pool: {team_name for team_name, _ in teams}
        for pool, teams in OFFICIAL_POOLS_2026.items()
    }
    official_teams = set().union(*official_by_pool.values())

    assert len(fixtures) == 12
    assert [fixture[0] for fixture in fixtures] == list(range(1, 13))
    assert fixtures[0][1:] == (
        date(2026, 8, 17),
        "Pool B",
        "Damsel Inflicting Stress",
        "Akali Dinosaurs",
    )
    assert fixtures[1][1:] == (
        date(2026, 8, 17),
        "Pool A",
        "Goodfellas",
        "Broken Orators",
    )

    team_counts = Counter()
    pool_counts = Counter()
    daily_counts = Counter()
    team_days = set()
    pairings = set()

    for _, fixture_date, pool, team1, team2 in fixtures:
        assert team1 in official_by_pool[pool]
        assert team2 in official_by_pool[pool]
        pairing = frozenset((team1, team2))
        assert pairing not in pairings
        pairings.add(pairing)
        for team in (team1, team2):
            assert (team, fixture_date) not in team_days
            team_days.add((team, fixture_date))
            team_counts[team] += 1
        pool_counts[pool] += 1
        daily_counts[fixture_date] += 1

    expected_pairings = {
        frozenset(pairing)
        for teams in official_by_pool.values()
        for pairing in combinations(teams, 2)
    }
    assert pairings == expected_pairings
    assert set(team_counts) == official_teams
    assert set(team_counts.values()) == {3}
    assert pool_counts == {"Pool A": 6, "Pool B": 6}
    assert [daily_counts[date(2026, 8, day)] for day in range(17, 23)] == [2, 2, 2, 3, 2, 1]
    expected_team_days = {
        "Broken Orators": {17, 19, 22},
        "Goodfellas": {17, 20, 21},
        "Mechanised Yappers": {18, 19, 21},
        "Rhetoric Rebels": {18, 20, 22},
        "Akali Dinosaurs": {17, 19, 20},
        "Damsel Inflicting Stress": {17, 20, 21},
        "Fifth Amendment": {18, 19, 20},
        "Motion Granted": {18, 20, 21},
    }
    assert {
        team: {fixture_date.day for scheduled_team, fixture_date in team_days if scheduled_team == team}
        for team in official_teams
    } == expected_team_days


def fixture_details(team1_name: str, team2_name: str):
    """Return canonical metadata for an official group-stage pairing."""
    pairing = frozenset((team1_name, team2_name))
    for number, fixture_date, pool, team1, team2 in OFFICIAL_GROUP_STAGE_2026:
        if pairing == frozenset((team1, team2)):
            official_result = OFFICIAL_RESULTS_BY_FIXTURE_2026.get(number)
            time_label, time_sort = GROUP_STAGE_TIME_OVERRIDES_2026.get(
                number,
                (GROUP_STAGE_TIME_2026, GROUP_STAGE_TIME_SORT_2026),
            )
            sides = {}
            if official_result:
                sides = {
                    official_result["government_team"]: "Government",
                    official_result["opposition_team"]: "Opposition",
                }
            return {
                "number": number,
                "date": fixture_date,
                "day": fixture_date.strftime("%A"),
                "date_label": fixture_date.strftime("%d %B %Y").lstrip("0"),
                "short_date_label": fixture_date.strftime("%a, %d %b").replace(", 0", ", "),
                "time_label": time_label,
                "time_sort": time_sort,
                "pool": pool,
                "team1_side": sides.get(team1_name),
                "team2_side": sides.get(team2_name),
                "government_team": (
                    official_result["government_team"]
                    if official_result else None
                ),
                "opposition_team": (
                    official_result["opposition_team"]
                    if official_result else None
                ),
            }
    return None


def seed_official_2026_auction(db: Session) -> bool:
    """Create the official auction once; never overwrite subsequent admin edits."""
    if db.query(Auction).filter(Auction.year == 2026).first() is not None:
        return False

    auction = Auction(year=2026, purse=50000)
    for team_name, leader_name, accent_color, players in OFFICIAL_2026_AUCTION:
        team = AuctionTeam(
            team_name=team_name,
            leader_name=leader_name,
            accent_color=accent_color,
        )
        team.players = [
            AuctionPlayer(player_name=player_name, price=price)
            for player_name, price in players
        ]
        auction.teams.append(team)

    db.add(auction)
    db.commit()
    return True


def _normalise_auction_teams(db: Session) -> None:
    auction = db.query(Auction).filter(Auction.year == 2026).first()
    if not auction:
        return

    old_name = "Damsel Inflicting Distress"
    new_name = "Damsel Inflicting Stress"
    old_team = next((team for team in auction.teams if team.team_name == old_name), None)
    new_team = next((team for team in auction.teams if team.team_name == new_name), None)
    if old_team and new_team and old_team.id != new_team.id:
        existing_players = {player.player_name.casefold() for player in old_team.players}
        for player in list(new_team.players):
            if player.player_name.casefold() not in existing_players:
                old_team.players.append(AuctionPlayer(
                    player_name=player.player_name,
                    price=player.price,
                ))
        db.delete(new_team)
        db.flush()
        old_team.team_name = new_name
    elif old_team:
        old_team.team_name = new_name

    official_names = {entry[0] for entry in OFFICIAL_2026_AUCTION}
    for team in list(auction.teams):
        canonical_name = TEAM_NAME_ALIASES_2026.get(team.team_name, team.team_name)
        if canonical_name not in official_names:
            db.delete(team)
            continue
        team.team_name = canonical_name
        if canonical_name == "Akali Dinosaurs":
            team.leader_name = "Guransh"
        if canonical_name == "Broken Orators":
            for player in team.players:
                if player.player_name == "Mohit":
                    player.player_name = "Mohit Sharma"
        if canonical_name == "Fifth Amendment":
            for player in team.players:
                if player.player_name == "Mohit":
                    player.player_name = "Mohit Verma"
        if canonical_name == "Goodfellas":
            revised_bids = {"Manroop Singh": 25500, "Vallari": 6000}
            for player in team.players:
                if player.player_name in revised_bids:
                    player.price = revised_bids[player.player_name]
        if canonical_name == "Motion Granted":
            sanjeevan = next(
                (player for player in team.players if player.player_name == "Sanjeevan"),
                None,
            )
            simran = next(
                (player for player in team.players if player.player_name == "Simran"),
                None,
            )
            if simran and sanjeevan:
                db.delete(simran)
            elif simran:
                simran.player_name = "Sanjeevan"


def _delete_debate(db: Session, debate: Debate) -> None:
    db.query(SpeakerPerformance).filter(
        SpeakerPerformance.debate_id == debate.id
    ).delete(synchronize_session=False)
    db.delete(debate)


def _canonical_team_name(name: str, official_names: set[str]) -> str:
    """Resolve legacy and case-only variants without creating a replacement row."""
    cleaned = name.strip()
    alias = next(
        (
            canonical
            for legacy, canonical in TEAM_NAME_ALIASES_2026.items()
            if legacy.casefold() == cleaned.casefold()
        ),
        None,
    )
    if alias:
        return alias
    return next(
        (
            official_name
            for official_name in official_names
            if official_name.casefold() == cleaned.casefold()
        ),
        cleaned,
    )


def _team_reference_score(db: Session, team: Team) -> tuple[int, ...]:
    """Prefer the row that already owns results, performances, and history."""
    debates = db.query(Debate).filter(
        (Debate.team1_id == team.id)
        | (Debate.team2_id == team.id)
        | (Debate.winner_team_id == team.id)
    ).all()
    completed_debates = sum(
        debate.winner_team_id is not None
        and team.id in (debate.team1_id, debate.team2_id)
        for debate in debates
    )
    wins = sum(debate.winner_team_id == team.id for debate in debates)
    performance_count = db.query(SpeakerPerformance).join(
        Speaker,
        Speaker.id == SpeakerPerformance.speaker_id,
    ).filter(
        Speaker.team_id == team.id
    ).count()
    speaker_count = db.query(Speaker).filter(Speaker.team_id == team.id).count()
    return (
        completed_debates,
        wins,
        performance_count,
        len(debates),
        speaker_count,
        -team.id,
    )


def _merge_team_into(db: Session, duplicate: Team, canonical: Team) -> None:
    """Move every real Team foreign key before deleting a duplicate row."""
    db.query(Speaker).filter(Speaker.team_id == duplicate.id).update(
        {Speaker.team_id: canonical.id}, synchronize_session="fetch"
    )
    db.query(Debate).filter(Debate.team1_id == duplicate.id).update(
        {Debate.team1_id: canonical.id}, synchronize_session="fetch"
    )
    db.query(Debate).filter(Debate.team2_id == duplicate.id).update(
        {Debate.team2_id: canonical.id}, synchronize_session="fetch"
    )
    db.query(Debate).filter(Debate.winner_team_id == duplicate.id).update(
        {Debate.winner_team_id: canonical.id}, synchronize_session="fetch"
    )
    db.delete(duplicate)


def _sync_pools_and_teams(db: Session):
    pools = {}
    for pool_name in OFFICIAL_POOLS_2026:
        pool = db.query(Pool).filter(Pool.name == pool_name).order_by(Pool.id).first()
        if not pool:
            pool = Pool(name=pool_name)
            db.add(pool)
            db.flush()
        pools[pool_name] = pool

    official_names = {
        team_name
        for pool_teams in OFFICIAL_POOLS_2026.values()
        for team_name, _ in pool_teams
    }
    teams = {}
    for pool_name, pool_teams in OFFICIAL_POOLS_2026.items():
        for team_name, _ in pool_teams:
            matches = [
                team
                for team in db.query(Team).order_by(Team.id).all()
                if _canonical_team_name(team.name, official_names) == team_name
            ]
            team = (
                max(matches, key=lambda candidate: _team_reference_score(db, candidate))
                if matches
                else Team(name=team_name, pool_id=pools[pool_name].id)
            )
            if not matches:
                db.add(team)
                db.flush()
            team.name = team_name
            team.pool_id = pools[pool_name].id
            teams[team_name] = team

            for duplicate in matches:
                if duplicate.id != team.id:
                    _merge_team_into(db, duplicate, team)
            db.flush()
    return teams, official_names


def _merge_speaker_aliases(
    db: Session,
    team: Team,
    canonical_name: str,
    aliases: set[str],
) -> Speaker | None:
    """Merge misspelled speaker rows without losing linked performances."""
    matches = db.query(Speaker).filter(
        Speaker.team_id == team.id,
        Speaker.name.in_({canonical_name, *aliases}),
    ).order_by(Speaker.id).all()
    if not matches:
        return None

    canonical = next(
        (speaker for speaker in matches if speaker.name == canonical_name),
        matches[0],
    )
    canonical.name = canonical_name

    for duplicate in matches:
        if duplicate.id == canonical.id:
            continue
        for performance in db.query(SpeakerPerformance).filter(
            SpeakerPerformance.speaker_id == duplicate.id
        ).all():
            existing = db.query(SpeakerPerformance).filter(
                SpeakerPerformance.speaker_id == canonical.id,
                SpeakerPerformance.debate_id == performance.debate_id,
                SpeakerPerformance.role == performance.role,
                SpeakerPerformance.is_swing == performance.is_swing,
            ).first()
            if existing:
                db.delete(performance)
            else:
                performance.speaker_id = canonical.id
        db.delete(duplicate)
    db.flush()
    return canonical


def _sync_registered_speakers(db: Session, teams) -> None:
    auction = db.query(Auction).filter(Auction.year == 2026).first()
    auction_by_name = {team.team_name: team for team in auction.teams} if auction else {}
    for team_name, team in teams.items():
        speakers_by_name = {}
        for speaker in db.query(Speaker).filter(
            Speaker.team_id == team.id
        ).order_by(Speaker.id).all():
            key = speaker.name.strip().casefold()
            canonical = speakers_by_name.get(key)
            if canonical is None:
                speakers_by_name[key] = speaker
                continue
            for performance in db.query(SpeakerPerformance).filter(
                SpeakerPerformance.speaker_id == speaker.id
            ).all():
                existing = db.query(SpeakerPerformance).filter(
                    SpeakerPerformance.speaker_id == canonical.id,
                    SpeakerPerformance.debate_id == performance.debate_id,
                    SpeakerPerformance.role == performance.role,
                    SpeakerPerformance.is_swing == performance.is_swing,
                ).first()
                if existing:
                    db.delete(performance)
                else:
                    performance.speaker_id = canonical.id
            db.delete(speaker)
        db.flush()

        auction_team = auction_by_name.get(team_name)
        if not auction_team:
            continue
        if team_name == "Motion Granted":
            simran = db.query(Speaker).filter(
                Speaker.team_id == team.id,
                Speaker.name == "Simran",
            ).one_or_none()
            sanjeevan = db.query(Speaker).filter(
                Speaker.team_id == team.id,
                Speaker.name == "Sanjeevan",
            ).one_or_none()
            if simran:
                has_history = db.query(SpeakerPerformance).filter(
                    SpeakerPerformance.speaker_id == simran.id
                ).first() is not None
                if has_history:
                    simran.active = False
                elif sanjeevan:
                    db.delete(simran)
                else:
                    simran.name = "Sanjeevan"
                    simran.active = True
                    sanjeevan = simran
            if sanjeevan:
                sanjeevan.active = True
        if team_name == "Akali Dinosaurs":
            _merge_speaker_aliases(
                db,
                team,
                canonical_name="Guransh",
                aliases={"Gurnash", "Guransh Singh"},
            )
        renamed_speaker = {
            "Broken Orators": "Mohit Sharma",
            "Fifth Amendment": "Mohit Verma",
        }.get(team_name)
        if renamed_speaker:
            for speaker in db.query(Speaker).filter(Speaker.team_id == team.id).all():
                if speaker.name == "Mohit":
                    speaker.name = renamed_speaker
        registered_names = [auction_team.leader_name]
        registered_names.extend(player.player_name for player in auction_team.players)
        existing_names = {
            speaker.name
            for speaker in db.query(Speaker).filter(Speaker.team_id == team.id).all()
        }
        for speaker_name in registered_names:
            if speaker_name not in existing_names:
                db.add(Speaker(name=speaker_name, team_id=team.id, active=True))
            else:
                db.query(Speaker).filter(
                    Speaker.team_id == team.id,
                    Speaker.name == speaker_name,
                ).update({Speaker.active: True}, synchronize_session=False)


def _sync_group_stage(db: Session, teams):
    official_pairs = {
        frozenset((team1, team2)): number
        for number, _, _, team1, team2 in OFFICIAL_GROUP_STAGE_2026
    }
    debates_by_pair = {}
    for debate in db.query(Debate).filter(Debate.stage == "pool").order_by(Debate.id).all():
        team1 = db.get(Team, debate.team1_id)
        team2 = db.get(Team, debate.team2_id)
        pairing = frozenset((team1.name, team2.name)) if team1 and team2 else None
        if pairing not in official_pairs or pairing in debates_by_pair:
            _delete_debate(db, debate)
        else:
            debates_by_pair[pairing] = debate

    rounds_by_number = {}
    for round_obj in db.query(Round).order_by(Round.id).all():
        rounds_by_number.setdefault(round_obj.number, round_obj)

    debates_by_number = {}
    for number, _, _, team1_name, team2_name in OFFICIAL_GROUP_STAGE_2026:
        round_obj = rounds_by_number.get(number)
        if not round_obj:
            round_obj = Round(number=number, motion=None)
            db.add(round_obj)
            db.flush()
            rounds_by_number[number] = round_obj

        pairing = frozenset((team1_name, team2_name))
        debate = debates_by_pair.get(pairing)
        if not debate:
            debate = Debate(stage="pool")
            db.add(debate)
        debate.round_id = round_obj.id
        debate.team1_id = teams[team1_name].id
        debate.team2_id = teams[team2_name].id
        if debate.winner_team_id not in (debate.team1_id, debate.team2_id):
            debate.winner_team_id = None
        debates_by_number[number] = debate

    db.flush()
    return debates_by_number


def _sync_official_results(db: Session, teams, debates_by_number) -> None:
    """Reconcile published results without creating speakers or duplicate scores."""
    for result in OFFICIAL_RESULTS_2026:
        debate = debates_by_number[result["fixture_number"]]
        debate.winner_team_id = teams[result["winner_team"]].id
        debate.government_reply_score = result["government_reply_score"]
        debate.opposition_reply_score = result["opposition_reply_score"]

        expected = {}
        for official_performance in result["performances"]:
            team_name, speaker_name, role, score = official_performance[:4]
            is_swing = bool(official_performance[4]) if len(official_performance) > 4 else False
            team = teams[team_name]
            speaker = db.query(Speaker).filter(
                Speaker.team_id == team.id,
                Speaker.name == speaker_name,
            ).one_or_none()
            if speaker is None:
                raise RuntimeError(
                    f"Registered speaker {speaker_name!r} is missing from {team_name!r}"
                )
            expected[(speaker.id, role, is_swing)] = score

        existing_by_key = {}
        for performance in db.query(SpeakerPerformance).filter(
            SpeakerPerformance.debate_id == debate.id
        ).order_by(SpeakerPerformance.id).all():
            key = (performance.speaker_id, performance.role, performance.is_swing)
            if (
                key not in expected
                or key in existing_by_key
            ):
                db.delete(performance)
                continue
            existing_by_key[key] = performance

        for (speaker_id, role, is_swing), score in expected.items():
            performance = existing_by_key.get((speaker_id, role, is_swing))
            if performance is None:
                performance = SpeakerPerformance(
                    debate_id=debate.id,
                    speaker_id=speaker_id,
                    role=role,
                    score=score,
                    is_swing=is_swing,
                )
                db.add(performance)
            else:
                performance.role = role
                performance.score = score
                performance.is_swing = is_swing


def _remove_unreferenced_placeholder_teams(db: Session, official_names) -> None:
    referenced_team_ids = {
        team_id
        for debate in db.query(Debate).all()
        for team_id in (debate.team1_id, debate.team2_id, debate.winner_team_id)
        if team_id is not None
    }
    for team in db.query(Team).all():
        if team.name in official_names or team.id in referenced_team_ids:
            continue
        speaker_ids = [
            speaker.id
            for speaker in db.query(Speaker).filter(Speaker.team_id == team.id)
        ]
        if speaker_ids:
            db.query(SpeakerPerformance).filter(
                SpeakerPerformance.speaker_id.in_(speaker_ids)
            ).delete(synchronize_session=False)
        db.query(Speaker).filter(Speaker.team_id == team.id).delete(synchronize_session=False)
        db.delete(team)


def sync_official_2026_tournament(db: Session) -> None:
    """Reuse current records while enforcing the final authoritative 2026 draw."""
    validate_official_group_stage()
    seed_official_2026_auction(db)
    _normalise_auction_teams(db)
    teams, official_names = _sync_pools_and_teams(db)
    _sync_registered_speakers(db, teams)
    debates_by_number = _sync_group_stage(db, teams)
    _sync_official_results(db, teams, debates_by_number)
    _remove_unreferenced_placeholder_teams(db, official_names)
    db.commit()


validate_official_group_stage()
