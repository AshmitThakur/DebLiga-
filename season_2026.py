"""Official one-time seed data for the completed 2026 player auction."""

from sqlalchemy.orm import Session

from models import Auction, AuctionPlayer, AuctionTeam


OFFICIAL_2026_AUCTION = (
    ("Broken Orators", "Akshat Agrawal", "#d6a62e", (
        ("Dhruv", 5000), ("Mohit", 25000), ("Akansh", 10000), ("Divsargun", 10000),
    )),
    ("Mechanised Yappers", "Ketan Kumar", "#4cb8e8", (
        ("Manav", 5000), ("Lakshit Chaudhary", 30500), ("Shayan", 5000), ("Bhavya Issarani", 9500),
    )),
    ("Fifth Amendment", "Satyam", "#9b7bc2", (
        ("Hridya", 21500), ("Rahul", 8000), ("Mohit", 15500), ("Ankit", 5000),
    )),
    ("Akali Dinosaurs", "Guransh Singh", "#dc725f", (
        ("Harasees", 35000), ("Vikramjit", 5000), ("Sahil", 5000), ("Beerdavinder", 5000),
    )),
    ("Motion Granted", "Tvishaa Patnaik", "#58a879", (
        ("Agamjot", 20500), ("Keshav", 15500), ("Shaurya", 5000), ("Simran", 9000),
    )),
    ("Damsel Inflicting Stress", "Rachel", "#df8ab4", (
        ("Mudit", 6000), ("Prabhleen", 20000), ("Soumya", 6000), ("Saksham", 18000),
    )),
    ("Goodfellas", "Rahul Batra", "#e08a45", (
        ("Priyanka", 7500), ("Manroop Singh", 29500), ("Pranay", 5000), ("Vallari", 8000),
    )),
    ("Rhetoric Rebels", "Priyanshi", "#4b91a7", (
        ("Prachi", 5000), ("Ramneet", 10000), ("Ashmita", 18500), ("Naman", 16500),
    )),
)


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
