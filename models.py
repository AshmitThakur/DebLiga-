from typing import Optional

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


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
    stage: Mapped[str] = mapped_column(
    String(30),
    nullable=False,
    default="pool"
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