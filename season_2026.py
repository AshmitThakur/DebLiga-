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
    "Damsel Inflicting Distress": "🌪️",
    "Goodfellas": "🕶️",
    "Rhetoric Rebels": "🔥",
}


OFFICIAL_2026_AUCTION = (
    ("Broken Orators", "Akshat Agrawal", "#d6a62e", (
        ("Dhruv", 5000), ("Mohit", 25000), ("Akansh", 10000), ("Divsargun", 10000),
    )),
    ("Mechanised Yappers", "Ketan Kumar", "#4cb8e8", (
        ("Manav", 5000), ("Lakshit Chaudhary", 30500), ("Shayan", 5000), ("Bhavya Issarani", 9500),
    )),
    ("Goodfellas", "Rahul Batra", "#e08a45", (
        ("Priyanka", 7500), ("Manroop Singh", 29500), ("Pranay", 5000), ("Vallari", 8000),
    )),
    ("Rhetoric Rebels", "Priyanshi", "#4b91a7", (
        ("Prachi", 5000), ("Ramneet", 10000), ("Ashmita", 18500), ("Naman", 16500),
    )),
    ("Akali Dinosaurs", "Gurnash", "#dc725f", (
        ("Harasees", 35000), ("Vikramjit", 5000), ("Sahil", 5000), ("Beerdavinder", 5000),
    )),
    ("Fifth Amendment", "Satyam", "#9b7bc2", (
        ("Hridya", 21500), ("Rahul", 8000), ("Mohit", 15500), ("Ankit", 5000),
    )),
    ("Damsel Inflicting Distress", "Rachel", "#df8ab4", (
        ("Mudit", 6000), ("Prabhleen", 20000), ("Soumya", 6000), ("Saksham", 18000),
    )),
    ("Motion Granted", "Tvishaa Patnaik", "#58a879", (
        ("Agamjot", 20500), ("Keshav", 15500), ("Shaurya", 5000), ("Simran", 9000),
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
        ("Akali Dinosaurs", "Gurnash's Team"),
        ("Fifth Amendment", "Satyam's Team"),
        ("Damsel Inflicting Distress", "Rachel's Team"),
        ("Motion Granted", "Tvishaa's Team"),
    ),
}


OFFICIAL_GROUP_STAGE_2026 = (
    (1, date(2026, 8, 17), "Pool B", "Damsel Inflicting Distress", "Akali Dinosaurs"),
    (2, date(2026, 8, 17), "Pool A", "Goodfellas", "Broken Orators"),
    (3, date(2026, 8, 18), "Pool A", "Mechanised Yappers", "Rhetoric Rebels"),
    (4, date(2026, 8, 18), "Pool B", "Fifth Amendment", "Motion Granted"),
    (5, date(2026, 8, 19), "Pool A", "Broken Orators", "Mechanised Yappers"),
    (6, date(2026, 8, 19), "Pool B", "Akali Dinosaurs", "Fifth Amendment"),
    (7, date(2026, 8, 20), "Pool A", "Goodfellas", "Rhetoric Rebels"),
    (8, date(2026, 8, 20), "Pool B", "Akali Dinosaurs", "Motion Granted"),
    (9, date(2026, 8, 20), "Pool B", "Damsel Inflicting Distress", "Fifth Amendment"),
    (10, date(2026, 8, 21), "Pool A", "Broken Orators", "Rhetoric Rebels"),
    (11, date(2026, 8, 21), "Pool A", "Goodfellas", "Mechanised Yappers"),
    (12, date(2026, 8, 21), "Pool B", "Damsel Inflicting Distress", "Motion Granted"),
)


TEAM_NAME_ALIASES_2026 = {
    "Damsel Inflicting Stress": "Damsel Inflicting Distress",
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
        "Damsel Inflicting Distress",
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
    assert [daily_counts[date(2026, 8, day)] for day in range(17, 22)] == [2, 2, 2, 3, 3]
    expected_team_days = {
        "Broken Orators": {17, 19, 21},
        "Goodfellas": {17, 20, 21},
        "Mechanised Yappers": {18, 19, 21},
        "Rhetoric Rebels": {18, 20, 21},
        "Akali Dinosaurs": {17, 19, 20},
        "Damsel Inflicting Distress": {17, 20, 21},
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
            return {
                "number": number,
                "date": fixture_date,
                "day": fixture_date.strftime("%A"),
                "date_label": fixture_date.strftime("%d %B %Y").lstrip("0"),
                "pool": pool,
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

    official_names = {entry[0] for entry in OFFICIAL_2026_AUCTION}
    for team in list(auction.teams):
        canonical_name = TEAM_NAME_ALIASES_2026.get(team.team_name, team.team_name)
        if canonical_name not in official_names:
            db.delete(team)
            continue
        team.team_name = canonical_name
        if canonical_name == "Akali Dinosaurs" and team.leader_name == "Guransh Singh":
            team.leader_name = "Gurnash"


def _delete_debate(db: Session, debate: Debate) -> None:
    db.query(SpeakerPerformance).filter(
        SpeakerPerformance.debate_id == debate.id
    ).delete(synchronize_session=False)
    db.delete(debate)


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
    for team in db.query(Team).all():
        canonical_name = TEAM_NAME_ALIASES_2026.get(team.name, team.name)
        if canonical_name in official_names:
            team.name = canonical_name

    teams = {}
    for pool_name, pool_teams in OFFICIAL_POOLS_2026.items():
        for team_name, _ in pool_teams:
            matches = db.query(Team).filter(Team.name == team_name).order_by(Team.id).all()
            team = matches[0] if matches else Team(name=team_name, pool_id=pools[pool_name].id)
            if not matches:
                db.add(team)
                db.flush()
            team.pool_id = pools[pool_name].id
            teams[team_name] = team

            for duplicate in matches[1:]:
                db.query(Speaker).filter(Speaker.team_id == duplicate.id).update(
                    {Speaker.team_id: team.id}, synchronize_session=False
                )
                db.query(Debate).filter(Debate.team1_id == duplicate.id).update(
                    {Debate.team1_id: team.id}, synchronize_session=False
                )
                db.query(Debate).filter(Debate.team2_id == duplicate.id).update(
                    {Debate.team2_id: team.id}, synchronize_session=False
                )
                db.query(Debate).filter(Debate.winner_team_id == duplicate.id).update(
                    {Debate.winner_team_id: team.id}, synchronize_session=False
                )
                db.delete(duplicate)
    return teams, official_names


def _sync_registered_speakers(db: Session, teams) -> None:
    auction = db.query(Auction).filter(Auction.year == 2026).first()
    auction_by_name = {team.team_name: team for team in auction.teams} if auction else {}
    for team_name, team in teams.items():
        auction_team = auction_by_name.get(team_name)
        if not auction_team:
            continue
        registered_names = [auction_team.leader_name]
        registered_names.extend(player.player_name for player in auction_team.players)
        existing_names = {
            speaker.name
            for speaker in db.query(Speaker).filter(Speaker.team_id == team.id).all()
        }
        for speaker_name in registered_names:
            if speaker_name not in existing_names:
                db.add(Speaker(name=speaker_name, team_id=team.id))


def _sync_group_stage(db: Session, teams) -> None:
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
    _sync_group_stage(db, teams)
    _remove_unreferenced_placeholder_teams(db, official_names)
    db.commit()


validate_official_group_stage()
