from typing import Optional

from sqlalchemy import Boolean, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# --------------------
# POOL
# --------------------

class Pool(Base):
    __tablename__ = "pools"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )


# --------------------
# TEAM
# --------------------

class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    pool_id: Mapped[int] = mapped_column(
        ForeignKey("pools.id"),
        nullable=False
    )


# --------------------
# SPEAKER
# --------------------

class Speaker(Base):
    __tablename__ = "speakers"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"),
        nullable=False
    )

    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )


# --------------------
# ROUND
# --------------------

class Round(Base):
    __tablename__ = "rounds"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    number: Mapped[int] = mapped_column(
        nullable=False
    )

    motion: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )


# --------------------
# DEBATE
# --------------------

class Debate(Base):
    __tablename__ = "debates"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    round_id: Mapped[int] = mapped_column(
        ForeignKey("rounds.id"),
        nullable=False
    )

    team1_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"),
        nullable=False
    )

    team2_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"),
        nullable=False
    )

    room: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True
    )

    winner_team_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("teams.id"),
        nullable=True
    )

    government_reply_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    opposition_reply_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )
    stage: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pool"
    )


# --------------------
# SPEAKER PERFORMANCE
# --------------------

class SpeakerPerformance(Base):
    __tablename__ = "speaker_performances"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    debate_id: Mapped[int] = mapped_column(
        ForeignKey("debates.id"),
        nullable=False
    )

    speaker_id: Mapped[int] = mapped_column(
        ForeignKey("speakers.id"),
        nullable=False
    )

    role: Mapped[str] = mapped_column(
        String(30),
        nullable=False
    )

    score: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )

    is_swing: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )


class Auction(Base):
    __tablename__ = "auctions"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(nullable=False, unique=True)
    purse: Mapped[int] = mapped_column(nullable=False, default=50000)
    teams: Mapped[list["AuctionTeam"]] = relationship(
        back_populates="auction", cascade="all, delete-orphan", order_by="AuctionTeam.id"
    )


class AuctionTeam(Base):
    __tablename__ = "auction_teams"
    __table_args__ = (UniqueConstraint("auction_id", "team_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    auction_id: Mapped[int] = mapped_column(ForeignKey("auctions.id"), nullable=False)
    team_name: Mapped[str] = mapped_column(String(100), nullable=False)
    leader_name: Mapped[str] = mapped_column(String(100), nullable=False)
    accent_color: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    auction: Mapped["Auction"] = relationship(back_populates="teams")
    players: Mapped[list["AuctionPlayer"]] = relationship(
        back_populates="team", cascade="all, delete-orphan", order_by="AuctionPlayer.id"
    )


class AuctionPlayer(Base):
    __tablename__ = "auction_players"

    id: Mapped[int] = mapped_column(primary_key=True)
    auction_team_id: Mapped[int] = mapped_column(
        ForeignKey("auction_teams.id"), nullable=False
    )
    player_name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[int] = mapped_column(nullable=False)
    team: Mapped["AuctionTeam"] = relationship(back_populates="players")
