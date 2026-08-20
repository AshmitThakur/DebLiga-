from pathlib import Path

from fastapi import Body, Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import SessionLocal, engine, get_db, migrate_existing_schema

from models import (
    Base,
    Debate,
    Pool,
    Round,
    Speaker,
    SpeakerPerformance,
    Team,
    Auction,
    AuctionTeam,
    AuctionPlayer,
)

from schemas import (
    DebateCreate,
    PoolCreate,
    ResultCreate,
    RoundCreate,
    SpeakerCreate,
    SpeakerUpdate,
    TeamCreate,
    TeamUpdate,
    DebateUpdate,
    PoolUpdate,
    RoundUpdate,
)
from season_2026 import (
    OFFICIAL_POOLS_2026,
    TEAM_EMOJIS_2026,
    fixture_details,
    sync_official_2026_tournament,
)


# --------------------------------------------------
# BASIC SETUP
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="DebLiga"
)

# Create database tables that do not already exist
Base.metadata.create_all(
    bind=engine
)
migrate_existing_schema(engine)

# Reuse current rows while enforcing the published 2026 pools and group draw.
with SessionLocal() as seed_db:
    sync_official_2026_tournament(seed_db)


# --------------------------------------------------
# STATIC FILES + HTML TEMPLATES
# --------------------------------------------------

app.mount(
    "/static",
    StaticFiles(
        directory=BASE_DIR / "static"
    ),
    name="static"
)

templates = Jinja2Templates(
    directory=BASE_DIR / "templates"
)
templates.env.globals["team_emoji"] = TEAM_EMOJIS_2026.get


# Shared champions list (used by homepage and history archive)
HALL_OF_FAME = [
    {"year": "2021", "team": "Nirvana", "winner": "Shreya"},
    {"year": "2022", "team": "The Mavens", "winner": "Chhawinder"},
    {"year": "2023", "team": "The Raging Raccoons", "winner": "Preeti"},
    {"year": "2024", "team": "Coffee Tea Spikers", "winner": "Adesh"},
    {"year": "2025", "team": "Panel Pls Understand", "winner": "Sukhman"},
    {"year": "2026", "team": "???", "winner": "???", "current": True},
]


# --------------------------------------------------
# HOMEPAGE
# --------------------------------------------------

@app.get(
    "/",
    response_class=HTMLResponse
)
def home(
    request: Request,
    db: Session = Depends(get_db),
):
    hall_of_fame = HALL_OF_FAME

    latest_champion = None
    # Prefer the most recent declared champion (exclude 2026/current edition)
    for entry in reversed(hall_of_fame):
        if entry.get("year") != "2026":
            latest_champion = entry
            break

    auction = db.query(Auction).filter(Auction.year == 2026).first()
    auction_names = {team.team_name for team in auction.teams} if auction else set()
    current_team_names = [
        team_name
        for pool_teams in OFFICIAL_POOLS_2026.values()
        for team_name, _ in pool_teams
        if team_name in auction_names
    ]

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "tournament_name": "LADC Debate League 2026",
            "edition": "6th Edition",
            "club_name": "Literary and Debating Club",
            "hall_of_fame": hall_of_fame,
            "latest_champion": latest_champion,
            "current_team_names": current_team_names,
        },
    )


@app.get(
    "/history",
    response_class=HTMLResponse
)
def history_page(
    request: Request
):
    return templates.TemplateResponse(
        request=request,
        name="history.html",
        context={
            "tournament_name": "LADC Debate League",
            "hall_of_fame": HALL_OF_FAME,
        },
    )


def auction_team_json(team):
    players = [{"id": p.id, "name": p.player_name, "price": p.price} for p in team.players]
    total = sum(player["price"] for player in players)
    return {
        "id": team.id, "team_name": team.team_name, "leader_name": team.leader_name,
        "accent_color": team.accent_color, "display_emoji": TEAM_EMOJIS_2026.get(team.team_name),
        "players": players, "total_spent": total,
        "remaining_purse": team.auction.purse - total, "purse": team.auction.purse,
    }


@app.get("/auctions", response_class=HTMLResponse)
def auctions_page(request: Request, year: int = 2026, db: Session = Depends(get_db)):
    if year not in (2025, 2026):
        raise HTTPException(status_code=404, detail="Auction year not found")
    teams = []
    top_purchases = []
    purse = 50000
    if year == 2026:
        auction = db.query(Auction).filter(Auction.year == year).first()
        if auction:
            purse = auction.purse
            teams = [auction_team_json(team) for team in auction.teams]
            top_purchases = sorted(
                (
                    {"name": player["name"], "price": player["price"], "team_name": team["team_name"]}
                    for team in teams
                    for player in team["players"]
                ),
                key=lambda purchase: purchase["price"],
                reverse=True,
            )[:5]
    return templates.TemplateResponse(
        request=request, name="auctions.html",
        context={"year": year, "teams": teams, "purse": purse, "top_purchases": top_purchases},
    )


def require_admin(request: Request):
    if request.cookies.get("admin_access") != "allowed":
        raise HTTPException(status_code=401, detail="Admin login required")


@app.get("/api/admin/auctions/2026/teams")
def get_auction_teams(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    auction = db.query(Auction).filter(Auction.year == 2026).first()
    return [] if not auction else [auction_team_json(team) for team in auction.teams]


def validate_auction_payload(data, purse):
    team_name = str(data.get("team_name", "")).strip()
    leader_name = str(data.get("leader_name", "")).strip()
    players = data.get("players") or []
    if not team_name or not leader_name:
        raise HTTPException(422, "Team name and leader are required")
    if not players:
        raise HTTPException(422, "Add at least one player")
    cleaned = []
    for player in players:
        name = str(player.get("name", "")).strip()
        try:
            price = int(player.get("price"))
        except (TypeError, ValueError):
            raise HTTPException(422, "Every player needs a valid price")
        if not name or price < 0:
            raise HTTPException(422, "Player names are required and prices cannot be negative")
        cleaned.append((name, price))
    if sum(price for _, price in cleaned) > purse:
        raise HTTPException(422, f"Total spending cannot exceed {purse:,} points")
    return team_name, leader_name, cleaned


@app.post("/api/admin/auctions/2026/teams")
def create_auction_team(request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    require_admin(request)
    auction = db.query(Auction).filter(Auction.year == 2026).first()
    if not auction:
        auction = Auction(year=2026, purse=50000)
        db.add(auction); db.flush()
    if len(auction.teams) >= 8:
        raise HTTPException(422, "The 2026 auction is limited to 8 teams")
    team_name, leader_name, players = validate_auction_payload(data, auction.purse)
    if db.query(AuctionTeam).filter(
        AuctionTeam.auction_id == auction.id, AuctionTeam.team_name == team_name
    ).first():
        raise HTTPException(422, "A 2026 auction team with this name already exists")
    team = AuctionTeam(auction=auction, team_name=team_name, leader_name=leader_name,
                       accent_color=data.get("accent_color") or None)
    team.players = [AuctionPlayer(player_name=name, price=price) for name, price in players]
    db.add(team); db.commit(); db.refresh(team)
    return auction_team_json(team)


@app.put("/api/admin/auctions/2026/teams/{team_id}")
def update_auction_team(team_id: int, request: Request, data: dict = Body(...), db: Session = Depends(get_db)):
    require_admin(request)
    team = db.get(AuctionTeam, team_id)
    if not team or team.auction.year != 2026:
        raise HTTPException(404, "Auction team not found")
    team_name, leader_name, players = validate_auction_payload(data, team.auction.purse)
    if db.query(AuctionTeam).filter(
        AuctionTeam.auction_id == team.auction_id,
        AuctionTeam.team_name == team_name,
        AuctionTeam.id != team.id,
    ).first():
        raise HTTPException(422, "A 2026 auction team with this name already exists")
    team.team_name, team.leader_name = team_name, leader_name
    team.accent_color = data.get("accent_color") or None
    team.players.clear()
    team.players.extend(AuctionPlayer(player_name=name, price=price) for name, price in players)
    db.commit(); db.refresh(team)
    return auction_team_json(team)


@app.delete("/api/admin/auctions/2026/teams/{team_id}")
def delete_auction_team(team_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    team = db.get(AuctionTeam, team_id)
    if not team or team.auction.year != 2026:
        raise HTTPException(404, "Auction team not found")
    db.delete(team); db.commit()
    return {"message": "Auction team deleted"}


# ==================================================
# POOLS
# ==================================================

@app.post("/api/pools")
def create_pool(
    data: PoolCreate,
    db: Session = Depends(get_db)
):

    pool = Pool(
        name=data.name
    )

    db.add(pool)
    db.commit()
    db.refresh(pool)

    return {
        "id": pool.id,
        "name": pool.name
    }


@app.get("/api/pools")
def get_pools(
    db: Session = Depends(get_db)
):

    pools = db.query(
        Pool
    ).all()

    return [
        {
            "id": pool.id,
            "name": pool.name
        }
        for pool in pools
    ]


# ==================================================
# TEAMS
# ==================================================

@app.post("/api/teams")
def create_team(
    data: TeamCreate,
    db: Session = Depends(get_db)
):

    pool = db.get(
        Pool,
        data.pool_id
    )

    if not pool:
        raise HTTPException(
            status_code=404,
            detail="Pool not found"
        )

    team = Team(
        name=data.name,
        pool_id=data.pool_id
    )

    db.add(team)
    db.commit()
    db.refresh(team)

    return {
        "id": team.id,
        "name": team.name,
        "pool_id": team.pool_id,
        "emoji": TEAM_EMOJIS_2026.get(team.name),
    }


@app.get("/api/teams")
def get_teams(
    db: Session = Depends(get_db)
):

    teams = db.query(
        Team
    ).all()

    return [
        {
            "id": team.id,
            "name": team.name,
            "pool_id": team.pool_id,
            "emoji": TEAM_EMOJIS_2026.get(team.name),
        }
        for team in teams
    ]


# ==================================================
# SPEAKERS
# ==================================================

@app.post("/api/speakers")
def create_speaker(
    data: SpeakerCreate,
    db: Session = Depends(get_db)
):

    team = db.get(
        Team,
        data.team_id
    )

    if not team:
        raise HTTPException(
            status_code=404,
            detail="Team not found"
        )

    speaker = Speaker(
        name=data.name,
        team_id=data.team_id
    )

    db.add(speaker)
    db.commit()
    db.refresh(speaker)

    return {
        "id": speaker.id,
        "name": speaker.name,
        "team_id": speaker.team_id
    }


@app.get("/api/speakers")
def get_speakers(
    db: Session = Depends(get_db)
):

    speakers = db.query(
        Speaker
    ).filter(
        Speaker.active.is_(True)
    ).all()

    return [
        {
            "id": speaker.id,
            "name": speaker.name,
            "team_id": speaker.team_id
        }
        for speaker in speakers
    ]


# ==================================================
# ROUNDS
# ==================================================

@app.post("/api/rounds")
def create_round(
    data: RoundCreate,
    db: Session = Depends(get_db)
):

    round_obj = Round(
        number=data.number,
        motion=data.motion
    )

    db.add(round_obj)
    db.commit()
    db.refresh(round_obj)

    return {
        "id": round_obj.id,
        "number": round_obj.number,
        "motion": round_obj.motion
    }


@app.get("/api/rounds")
def get_rounds(
    db: Session = Depends(get_db)
):

    rounds = db.query(
        Round
    ).all()

    return [
        {
            "id": round_obj.id,
            "number": round_obj.number,
            "motion": round_obj.motion
        }
        for round_obj in rounds
    ]


# ==================================================
# DEBATES
# ==================================================

@app.post("/api/debates")
def create_debate(
    data: DebateCreate,
    db: Session = Depends(get_db)
):

    round_obj = db.get(
        Round,
        data.round_id
    )

    if not round_obj:
        raise HTTPException(
            status_code=404,
            detail="Round not found"
        )

    team1 = db.get(
        Team,
        data.team1_id
    )

    team2 = db.get(
        Team,
        data.team2_id
    )

    if not team1 or not team2:
        raise HTTPException(
            status_code=404,
            detail="Team not found"
        )

    if team1.id == team2.id:
        raise HTTPException(
            status_code=400,
            detail="A team cannot debate itself"
        )

    stage = data.stage.lower()

    if stage not in ALLOWED_STAGES:
        raise HTTPException(
            status_code=400,
            detail="Invalid debate stage"
        )

    # Pool debates must happen inside the same pool
    if (
        stage == "pool"
        and
        team1.pool_id != team2.pool_id
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Pool-stage teams must belong "
                "to the same pool"
            )
        )

    # Once knockouts begin, pool schedule is locked
    if (
        stage == "pool"
        and
        knockouts_exist(db)
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot add pool debates after "
                "knockouts have been generated"
            )
        )

    if stage == "semifinal":

        semifinal_count = db.query(
            Debate
        ).filter(
            Debate.stage == "semifinal"
        ).count()

        if semifinal_count >= 2:
            raise HTTPException(
                status_code=400,
                detail="Two semifinals already exist"
            )

    if stage in [
        "final",
        "third_place"
    ]:

        existing = db.query(
            Debate
        ).filter(
            Debate.stage == stage
        ).first()

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"{stage} already exists"
            )

    debate = Debate(
        round_id=data.round_id,
        team1_id=data.team1_id,
        team2_id=data.team2_id,
        room=data.room,
        stage=stage
    )

    db.add(debate)
    db.commit()
    db.refresh(debate)

    return {
        "id": debate.id,
        "round_id": debate.round_id,
        "team1_id": debate.team1_id,
        "team2_id": debate.team2_id,
        "room": debate.room,
        "stage": debate.stage
    }


@app.get("/api/debates")
def get_debates(
    db: Session = Depends(get_db)
):

    debates = db.query(
        Debate
    ).all()

    return [
        {
            "id": debate.id,
            "round_id": debate.round_id,
            "team1_id": debate.team1_id,
            "team2_id": debate.team2_id,
            "room": debate.room,
            "winner_team_id": debate.winner_team_id,
            "stage": debate.stage
        }
        for debate in debates
    ]


# ==================================================
# SUBMIT / EDIT RESULT
# ==================================================

@app.post(
    "/api/debates/{debate_id}/result"
)
def submit_result(
    debate_id: int,
    data: ResultCreate,
    db: Session = Depends(get_db)
):

    debate = db.get(
        Debate,
        debate_id
    )

    if not debate:
        raise HTTPException(
            status_code=404,
            detail="Debate not found"
        )

    if data.winner_team_id not in [
        debate.team1_id,
        debate.team2_id
    ]:
        raise HTTPException(
            status_code=400,
            detail=(
                "Winner must be one of "
                "the debating teams"
            )
        )

    old_winner = debate.winner_team_id

    # Don't silently change qualifiers after knockouts exist.
    if (
        debate.stage == "pool"
        and
        knockouts_exist(db)
        and
        old_winner is not None
        and
        old_winner != data.winner_team_id
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Pool winner cannot be changed "
                "after knockouts were generated. "
                "Reset knockouts first."
            )
        )

    if len(data.performances) == 0:
        raise HTTPException(
            status_code=400,
            detail="Enter at least one speaker performance"
        )

    validated = []
    normal_speakers = set()
    performance_keys = set()

    for performance in data.performances:

        performance_key = (
            performance.speaker_id,
            performance.role.strip().casefold(),
            performance.is_swing,
        )
        if performance_key in performance_keys:
            raise HTTPException(
                status_code=400,
                detail="Duplicate speaker performance entered"
            )
        if not performance.is_swing and performance.speaker_id in normal_speakers:
            raise HTTPException(
                status_code=400,
                detail="Same speaker entered more than once as a normal performance"
            )

        performance_keys.add(performance_key)
        if not performance.is_swing:
            normal_speakers.add(performance.speaker_id)

        speaker = db.get(
            Speaker,
            performance.speaker_id
        )

        if not speaker:
            raise HTTPException(
                status_code=404,
                detail="Speaker not found"
            )

        if speaker.team_id not in [
            debate.team1_id,
            debate.team2_id
        ]:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{speaker.name} is not "
                    "part of this debate"
                )
            )

        validated.append(
            (
                speaker,
                performance
            )
        )

    scored_team_ids = {
        speaker.team_id
        for speaker, performance in validated
    }

    if debate.team1_id not in scored_team_ids:
        raise HTTPException(
            status_code=400,
            detail=(
                "Enter at least one speaker score "
                "for Team 1"
            )
        )

    if debate.team2_id not in scored_team_ids:
        raise HTTPException(
            status_code=400,
            detail=(
                "Enter at least one speaker score "
                "for Team 2"
            )
        )

    debate.winner_team_id = (
        data.winner_team_id
    )
    debate.government_reply_score = data.government_reply_score
    debate.opposition_reply_score = data.opposition_reply_score

    db.query(
        SpeakerPerformance
    ).filter(
        SpeakerPerformance.debate_id == debate.id
    ).delete(
        synchronize_session=False
    )

    for speaker, performance in validated:

        db.add(
            SpeakerPerformance(
                debate_id=debate.id,
                speaker_id=speaker.id,
                role=performance.role,
                score=performance.score,
                is_swing=performance.is_swing,
            )
        )

    # Both semifinals completed -> Final + Third Place appear.
    if debate.stage == "semifinal":
        sync_knockout_after_semifinals(
            db
        )

    db.commit()

    return {
        "message": "Result saved successfully"
    }


# ==================================================
# SPEAKER RANKINGS
# ==================================================

@app.get("/api/speaker-rankings")
def speaker_rankings(
    db: Session = Depends(get_db)
):

    performances = db.query(
        SpeakerPerformance
    ).filter(
        SpeakerPerformance.is_swing.is_(False)
    ).all()

    ranking_data = {}

    # Collect scores for every speaker
    for performance in performances:

        speaker_id = (
            performance.speaker_id
        )

        if speaker_id not in ranking_data:
            ranking_data[speaker_id] = {
                "total": 0,
                "debates": 0
            }

        ranking_data[
            speaker_id
        ]["total"] += performance.score

        ranking_data[
            speaker_id
        ]["debates"] += 1

    rankings = []

    # Calculate averages
    for speaker_id, stats in ranking_data.items():

        speaker = db.get(
            Speaker,
            speaker_id
        )

        average = (
            stats["total"]
            / stats["debates"]
        )

        rankings.append({
            "speaker_id": speaker.id,
            "speaker_name": speaker.name,
            "team_id": speaker.team_id,
            "total_score": stats["total"],
            "debates": stats["debates"],
            "average_score": round(
                average,
                2
            )
        })

    # Highest average first
    rankings.sort(
        key=lambda speaker:
        speaker["average_score"],
        reverse=True
    )

    return rankings


# ==================================================
# TEAM / POOL STANDINGS
# ==================================================

@app.get("/api/standings")
def standings(
    db: Session = Depends(get_db)
):

    pools = db.query(
        Pool
    ).order_by(
        Pool.id
    ).all()

    table = []

    for pool in pools:

        pool_table = calculate_pool_standings(
            db,
            pool.id
        )

        for team in pool_table:

            team["pool_name"] = pool.name

            table.append(
                team
            )

    return table


def debate_team_averages(db: Session, debate: Debate):
    """Calculate each team's average directly from canonical performances."""
    scores_by_team = {}
    rows = db.query(
        SpeakerPerformance,
        Speaker.team_id,
    ).join(
        Speaker,
        Speaker.id == SpeakerPerformance.speaker_id,
    ).filter(
        SpeakerPerformance.debate_id == debate.id
    ).all()

    for performance, team_id in rows:
        scores_by_team.setdefault(team_id, []).append(performance.score)

    return {
        team_id: round(sum(scores) / len(scores), 2)
        for team_id, scores in scores_by_team.items()
        if scores
    }


def debate_side_team_ids(db: Session, debate: Debate, fixture=None):
    """Resolve Government/Opposition from official metadata or entered roles."""
    side_ids = {"Government": None, "Opposition": None}
    teams = {
        team.id: team
        for team in db.query(Team).filter(
            Team.id.in_((debate.team1_id, debate.team2_id))
        )
    }
    if fixture:
        for team_id, team in teams.items():
            if team.name == fixture.get("government_team"):
                side_ids["Government"] = team_id
            elif team.name == fixture.get("opposition_team"):
                side_ids["Opposition"] = team_id

    if None in side_ids.values():
        government_roles = {"Prime Minister", "Deputy Prime Minister", "Government Whip"}
        opposition_roles = {
            "Leader of Opposition",
            "Deputy Leader of Opposition",
            "Opposition Whip",
        }
        rows = db.query(SpeakerPerformance.role, Speaker.team_id).join(
            Speaker,
            Speaker.id == SpeakerPerformance.speaker_id,
        ).filter(
            SpeakerPerformance.debate_id == debate.id
        ).all()
        for role, team_id in rows:
            if role in government_roles:
                side_ids["Government"] = team_id
            elif role in opposition_roles:
                side_ids["Opposition"] = team_id
    return side_ids


def debate_result_breakdown(db: Session, debate: Debate, fixture=None):
    """Return constructive and reply scores separately, grouped by team."""
    role_order = {
        "Prime Minister": 0,
        "Leader of Opposition": 0,
        "Deputy Prime Minister": 1,
        "Deputy Leader of Opposition": 1,
        "Government Whip": 2,
        "Opposition Whip": 2,
    }
    breakdown = {
        debate.team1_id: {"performances": [], "reply_score": None, "total_score": None},
        debate.team2_id: {"performances": [], "reply_score": None, "total_score": None},
    }
    rows = db.query(SpeakerPerformance, Speaker).join(
        Speaker,
        Speaker.id == SpeakerPerformance.speaker_id,
    ).filter(
        SpeakerPerformance.debate_id == debate.id
    ).all()
    for performance, speaker in rows:
        if speaker.team_id not in breakdown:
            continue
        breakdown[speaker.team_id]["performances"].append({
            "speaker_id": speaker.id,
            "speaker_name": speaker.name,
            "role": performance.role,
            "score": performance.score,
            "is_swing": performance.is_swing,
        })

    for details in breakdown.values():
        details["performances"].sort(
            key=lambda item: (role_order.get(item["role"], 99), item["speaker_name"].casefold())
        )

    side_ids = debate_side_team_ids(db, debate, fixture)
    if side_ids["Government"] in breakdown:
        breakdown[side_ids["Government"]]["reply_score"] = debate.government_reply_score
    if side_ids["Opposition"] in breakdown:
        breakdown[side_ids["Opposition"]]["reply_score"] = debate.opposition_reply_score

    for details in breakdown.values():
        reply_score = details["reply_score"]
        if details["performances"] and reply_score is not None:
            details["total_score"] = round(
                sum(item["score"] for item in details["performances"]) + reply_score,
                2,
            )
    return breakdown


# ==================================================
# PUBLIC WEBSITE PAGES
# ==================================================

@app.get(
    "/teams",
    response_class=HTMLResponse
)
def teams_page(
    request: Request,
    db: Session = Depends(get_db)
):

    auction = db.query(Auction).filter(Auction.year == 2026).first()
    auction_teams = {
        team.team_name: auction_team_json(team)
        for team in auction.teams
    } if auction else {}
    team_pools = []
    for pool_name, pool_teams in OFFICIAL_POOLS_2026.items():
        teams_in_pool = []
        for team_name, owner_label in pool_teams:
            if team_name not in auction_teams:
                continue
            team_data = auction_teams[team_name]
            team_data["owner_label"] = owner_label
            team_data["pool_name"] = pool_name
            teams_in_pool.append(team_data)
        team_pools.append({"name": pool_name, "teams": teams_in_pool})

    return templates.TemplateResponse(
        request=request,
        name="teams.html",
        context={
            "team_pools": team_pools
        }
    )


@app.get(
    "/schedule",
    response_class=HTMLResponse
)
def schedule_page(
    request: Request,
    db: Session = Depends(get_db)
):

    debates = db.query(
        Debate
    ).order_by(
        Debate.round_id,
        Debate.id
    ).all()

    rounds = {
        round_obj.id: round_obj
        for round_obj in db.query(Round).all()
    }

    teams = {
        team.id: team
        for team in db.query(Team).all()
    }

    pools = {
        pool.id: pool
        for pool in db.query(Pool).all()
    }

    stage_names = {
        "pool": "Pool Stage",
        "semifinal": "Semifinal",
        "third_place": "Third Place Match",
        "final": "Final"
    }

    schedule = []

    for debate in debates:

        round_obj = rounds.get(
            debate.round_id
        )

        team1 = teams.get(
            debate.team1_id
        )

        team2 = teams.get(
            debate.team2_id
        )

        winner = None

        if debate.winner_team_id:
            winner = teams.get(
                debate.winner_team_id
            )

        pool = None

        if (
            debate.stage == "pool"
            and
            team1
        ):
            pool = pools.get(
                team1.pool_id
            )

        fixture = (
            fixture_details(team1.name, team2.name)
            if debate.stage == "pool" and team1 and team2
            else None
        )
        team_averages = debate_team_averages(db, debate)
        result_breakdown = debate_result_breakdown(db, debate, fixture)
        side_ids = debate_side_team_ids(db, debate, fixture)
        team1_side = next(
            (side for side, team_id in side_ids.items() if team_id == debate.team1_id),
            None,
        )
        team2_side = next(
            (side for side, team_id in side_ids.items() if team_id == debate.team2_id),
            None,
        )

        schedule.append({
            "id": debate.id,
            "round": round_obj,
            "team1": team1,
            "team2": team2,
            "room": debate.room,
            "winner": winner,
            "stage": debate.stage,
            "stage_name": stage_names.get(
                debate.stage,
                debate.stage
            ),
            "pool": pool,
            "fixture": fixture,
            "team1_side": team1_side,
            "team2_side": team2_side,
            "team1_average_score": team_averages.get(debate.team1_id),
            "team2_average_score": team_averages.get(debate.team2_id),
            "team1_result": result_breakdown[debate.team1_id],
            "team2_result": result_breakdown[debate.team2_id],
            "status": (
                "Completed"
                if winner
                else "Pending"
            )
        })

    schedule.sort(key=lambda item: (
        0,
        item["fixture"]["number"],
    ) if item["fixture"] else (
        1,
        item["round"].number if item["round"] else item["id"],
    ))

    return templates.TemplateResponse(
        request=request,
        name="schedule.html",
        context={
            "schedule": schedule
        }
    )

@app.get(
    "/standings",
    response_class=HTMLResponse
)
def standings_page(
    request: Request,
    db: Session = Depends(get_db)
):

    table = standings(db)

    pools = {
        pool.id: pool
        for pool in db.query(Pool).all()
    }

    return templates.TemplateResponse(
        request=request,
        name="standings.html",
        context={
            "table": table,
            "pools": pools
        }
    )


@app.get(
    "/speaker-rankings",
    response_class=HTMLResponse
)
def rankings_page(
    request: Request,
    db: Session = Depends(get_db)
):

    rankings = speaker_rankings(db)

    teams = {
        team.id: team
        for team in db.query(Team).all()
    }

    return templates.TemplateResponse(
        request=request,
        name="rankings.html",
        context={
            "rankings": rankings,
            "teams": teams
        }
    )


@app.get(
    "/teams/{team_id}",
    response_class=HTMLResponse
)
def team_detail_page(
    team_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    team = db.get(
        Team,
        team_id
    )

    if not team:
        raise HTTPException(
            status_code=404,
            detail="Team not found"
        )

    speakers = db.query(
        Speaker
    ).filter(
        Speaker.team_id == team.id,
        Speaker.active.is_(True),
    ).all()

    pool = db.get(
        Pool,
        team.pool_id
    )

    debates = db.query(
        Debate
    ).filter(
        (Debate.team1_id == team.id)
        |
        (Debate.team2_id == team.id)
    ).order_by(
        Debate.round_id,
        Debate.id
    ).all()

    history = []

    for debate in debates:

        round_obj = db.get(
            Round,
            debate.round_id
        )

        opponent_id = (
            debate.team2_id
            if debate.team1_id == team.id
            else debate.team1_id
        )

        opponent = db.get(
            Team,
            opponent_id
        )

        performances = db.query(
            SpeakerPerformance
        ).filter(
            SpeakerPerformance.debate_id
            == debate.id
        ).all()

        team_scores = []
        opponent_scores = []

        for performance in performances:

            speaker = db.get(
                Speaker,
                performance.speaker_id
            )

            if not speaker:
                continue

            if speaker.team_id == team.id:
                team_scores.append(
                    performance.score
                )

            elif (
                opponent
                and
                speaker.team_id == opponent.id
            ):
                opponent_scores.append(
                    performance.score
                )

        team_average = (
            round(
                sum(team_scores) / len(team_scores),
                2
            )
            if team_scores
            else None
        )

        opponent_average = (
            round(
                sum(opponent_scores)
                / len(opponent_scores),
                2
            )
            if opponent_scores
            else None
        )

        if debate.winner_team_id is None:
            result = "Pending"

        elif debate.winner_team_id == team.id:
            result = "Won"

        else:
            result = "Lost"

        fixture = (
            fixture_details(team.name, opponent.name)
            if debate.stage == "pool" and opponent
            else None
        )
        result_breakdown = debate_result_breakdown(db, debate, fixture)
        side_ids = debate_side_team_ids(db, debate, fixture)
        debate_number = (
            fixture["number"]
            if fixture
            else round_obj.number if round_obj else None
        )

        history.append({
            "debate": debate,
            "round": round_obj,
            "opponent": opponent,
            "stage_name": (
                "Group Stage"
                if debate.stage == "pool"
                else debate.stage.replace("_", " ").title()
            ),
            "fixture": fixture,
            "side": next(
                (side for side, side_team_id in side_ids.items() if side_team_id == team.id),
                None,
            ),
            "debate_number": debate_number,
            "scheduled_time": (
                fixture.get("time_label")
                if fixture
                else None
            ),
            "scheduled_time_sort": (
                str(
                    fixture.get("time_sort")
                    or fixture.get("time")
                    or "99:99"
                )
                if fixture
                else "99:99"
            ),
            "venue": debate.room,
            "result": result,
            "team_average_score":
                team_average,
            "opponent_average_score":
                opponent_average,
            "team_reply_score": result_breakdown[team.id]["reply_score"],
            "opponent_reply_score": (
                result_breakdown[opponent.id]["reply_score"] if opponent else None
            ),
            "team_total_score": result_breakdown[team.id]["total_score"],
            "opponent_total_score": (
                result_breakdown[opponent.id]["total_score"] if opponent else None
            ),
        })

    history.sort(key=lambda item: (
        (
            item["fixture"]["date"].isoformat()
            if item["fixture"]
            else "9999-12-31"
        ),
        item["scheduled_time_sort"],
        item["debate_number"] or 9999,
    ))

    wins = sum(
        1
        for item in history
        if item["result"] == "Won"
    )

    losses = sum(
        1
        for item in history
        if item["result"] == "Lost"
    )

    return templates.TemplateResponse(
        request=request,
        name="team_detail.html",
        context={
            "team": team,
            "pool": pool,
            "speakers": speakers,
            "history": history,
            "wins": wins,
            "losses": losses
        }
    )

@app.get(
    "/speakers/{speaker_id}",
    response_class=HTMLResponse
)
def speaker_detail_page(
    speaker_id: int,
    request: Request,
    db: Session = Depends(get_db)
):

    speaker = db.get(
        Speaker,
        speaker_id
    )

    if not speaker:
        raise HTTPException(
            status_code=404,
            detail="Speaker not found"
        )

    team = db.get(
        Team,
        speaker.team_id
    )

    performances = db.query(
        SpeakerPerformance
    ).filter(
        SpeakerPerformance.speaker_id
        == speaker.id,
        SpeakerPerformance.is_swing.is_(False),
    ).all()

    history = []

    for performance in performances:

        debate = db.get(
            Debate,
            performance.debate_id
        )

        if not debate:
            continue

        round_obj = db.get(
            Round,
            debate.round_id
        )

        opponent_id = (
            debate.team2_id
            if debate.team1_id == team.id
            else debate.team1_id
        )

        opponent = db.get(
            Team,
            opponent_id
        )
        fixture = (
            fixture_details(team.name, opponent.name)
            if debate.stage == "pool" and opponent
            else None
        )

        if debate.winner_team_id is None:
            result = "Pending"

        elif debate.winner_team_id == team.id:
            result = "Won"

        else:
            result = "Lost"

        history.append({
            "round": round_obj,
            "role": performance.role,
            "score": performance.score,
            "debate": debate,
            "opponent": opponent,
            "side": fixture.get("team1_side") if fixture else None,
            "result": result
        })

    history.sort(
        key=lambda item: (
            item["round"].number
            if item["round"]
            else 999,
            item["debate"].id
        )
    )

    average_score = None

    if performances:
        average_score = round(
            sum(
                performance.score
                for performance in performances
            )
            / len(performances),
            2
        )

    return templates.TemplateResponse(
        request=request,
        name="speaker_detail.html",
        context={
            "speaker": speaker,
            "team": team,
            "history": history,
            "average_score": average_score,
            "debates_played": len(history)
        }
    )


@app.get(
    "/about/ladc",
    response_class=HTMLResponse
)
def about_ladc(
    request: Request
):
    return templates.TemplateResponse(
        request=request,
        name="about_ladc.html",
        context={
            "request": request
        }
    )


@app.get(
    "/about/debate-league",
    response_class=HTMLResponse
)
def about_debate_league(
    request: Request
):
    return templates.TemplateResponse(
        request=request,
        name="about_debate_league.html",
        context={
            "request": request
        }
    )


# ==================================================
# EDIT TEAM / SPEAKER
# ==================================================

@app.put("/api/teams/{team_id}")
def update_team(
    team_id: int,
    data: TeamUpdate,
    db: Session = Depends(get_db)
):

    team = db.get(Team, team_id)

    if not team:
        raise HTTPException(
            status_code=404,
            detail="Team not found"
        )

    pool = db.get(Pool, data.pool_id)

    if not pool:
        raise HTTPException(
            status_code=404,
            detail="Pool not found"
        )

    team.name = data.name
    team.pool_id = data.pool_id

    db.commit()
    db.refresh(team)

    return {
        "id": team.id,
        "name": team.name,
        "pool_id": team.pool_id,
        "emoji": TEAM_EMOJIS_2026.get(team.name),
    }


@app.put("/api/speakers/{speaker_id}")
def update_speaker(
    speaker_id: int,
    data: SpeakerUpdate,
    db: Session = Depends(get_db)
):

    speaker = db.get(Speaker, speaker_id)

    if not speaker:
        raise HTTPException(
            status_code=404,
            detail="Speaker not found"
        )

    team = db.get(Team, data.team_id)

    if not team:
        raise HTTPException(
            status_code=404,
            detail="Team not found"
        )

    speaker.name = data.name
    speaker.team_id = data.team_id

    db.commit()
    db.refresh(speaker)

    return {
        "id": speaker.id,
        "name": speaker.name,
        "team_id": speaker.team_id
    }

@app.delete("/api/speakers/{speaker_id}")
def delete_speaker(
    speaker_id: int,
    db: Session = Depends(get_db)
):

    speaker = db.get(
        Speaker,
        speaker_id
    )

    if not speaker:
        raise HTTPException(
            status_code=404,
            detail="Speaker not found"
        )

    # Don't delete a speaker if they already
    # have recorded debate scores
    performance = db.query(
        SpeakerPerformance
    ).filter(
        SpeakerPerformance.speaker_id
        == speaker_id
    ).first()

    if performance:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete speaker with recorded debate performances"
        )

    db.delete(speaker)
    db.commit()

    return {
        "message": "Speaker deleted successfully"
    }

# ==================================================
# ADMIN PAGE
# ==================================================

ADMIN_PASSKEY = "LADC@BestDebLitClub2026"


@app.get(
    "/admin",
    response_class=HTMLResponse
)
def admin_page(
    request: Request
):
    return templates.TemplateResponse(
        request=request,
        name="admin_login.html",
        context={}
    )


@app.post("/admin")
def admin_login(
    request: Request,
    passkey: str = Form(...)
):
    if passkey != ADMIN_PASSKEY:
        return templates.TemplateResponse(
            request=request,
            name="admin_login.html",
            context={"error": "Incorrect passkey. Please try again."},
        )

    response = RedirectResponse(url="/admin/dashboard", status_code=303)
    response.set_cookie(key="admin_access", value="allowed", httponly=True)
    return response


@app.get(
    "/admin/dashboard",
    response_class=HTMLResponse
)
def admin_dashboard(
    request: Request
):
    access = request.cookies.get("admin_access")
    if access != "allowed":
        return RedirectResponse(url="/admin", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context={}
    )

# ==================================================
# TOURNAMENT HELPERS
# ==================================================

ALLOWED_STAGES = {
    "pool",
    "semifinal",
    "third_place",
    "final"
}


def clear_debate_result(
    db: Session,
    debate: Debate
):
    db.query(
        SpeakerPerformance
    ).filter(
        SpeakerPerformance.debate_id == debate.id
    ).delete(
        synchronize_session=False
    )

    debate.winner_team_id = None
    debate.government_reply_score = None
    debate.opposition_reply_score = None


def knockouts_exist(
    db: Session
):
    return db.query(
        Debate
    ).filter(
        Debate.stage != "pool"
    ).first() is not None


def calculate_pool_standings(
    db: Session,
    pool_id: int
):

    teams = db.query(
        Team
    ).filter(
        Team.pool_id == pool_id
    ).all()

    debates = db.query(
        Debate
    ).filter(
        Debate.stage == "pool"
    ).all()

    speakers = {
        speaker.id: speaker
        for speaker in db.query(
            Speaker
        ).all()
    }

    performances = db.query(
        SpeakerPerformance
    ).all()

    performances_by_debate = {}

    for performance in performances:

        performances_by_debate.setdefault(
            performance.debate_id,
            []
        ).append(
            performance
        )

    table = []

    for team in teams:

        played = 0
        wins = 0
        losses = 0
        debate_averages = []

        for debate in debates:

            if debate.winner_team_id is None:
                continue

            if team.id not in [
                debate.team1_id,
                debate.team2_id
            ]:
                continue

            played += 1

            if debate.winner_team_id == team.id:
                wins += 1
            else:
                losses += 1

            team_scores = []

            for performance in performances_by_debate.get(
                debate.id,
                []
            ):

                speaker = speakers.get(
                    performance.speaker_id
                )

                if (
                    speaker
                    and
                    speaker.team_id == team.id
                ):
                    team_scores.append(
                        performance.score
                    )

            if team_scores:

                debate_averages.append(
                    sum(team_scores)
                    / len(team_scores)
                )

        average_team_score = 0.0

        if debate_averages:

            average_team_score = round(
                sum(debate_averages)
                / len(debate_averages),
                2
            )

        table.append({
            "team_id": team.id,
            "team_name": team.name,
            "team_emoji": TEAM_EMOJIS_2026.get(team.name),
            "pool_id": team.pool_id,
            "played": played,
            "wins": wins,
            "losses": losses,
            "points": wins,
            "average_team_score":
                average_team_score,
            "scored_debates":
                len(debate_averages)
        })

    table.sort(
        key=lambda team: (
            -team["points"],
            -team["average_team_score"],
            team["team_name"].lower()
        )
    )

    team_ids = {team["team_id"] for team in table}
    remaining_debates = [
        debate
        for debate in debates
        if debate.winner_team_id is None
        and debate.team1_id in team_ids
        and debate.team2_id in team_ids
    ]

    if remaining_debates:
        possible_win_totals = [{team["team_id"]: team["wins"] for team in table}]
        for debate in remaining_debates:
            next_totals = []
            for totals in possible_win_totals:
                for winner_id in (debate.team1_id, debate.team2_id):
                    outcome = totals.copy()
                    outcome[winner_id] += 1
                    next_totals.append(outcome)
            possible_win_totals = next_totals

        for team in table:
            team_id = team["team_id"]
            is_qualified = all(
                sum(
                    other_id != team_id and other_wins >= totals[team_id]
                    for other_id, other_wins in totals.items()
                ) <= 1
                for totals in possible_win_totals
            )
            is_eliminated = all(
                sum(
                    other_id != team_id and other_wins > totals[team_id]
                    for other_id, other_wins in totals.items()
                ) >= 2
                for totals in possible_win_totals
            )
            team["qualification_status"] = (
                "Q" if is_qualified else "E" if is_eliminated else "—"
            )
    else:
        for position, team in enumerate(table, start=1):
            team["qualification_status"] = "Q" if position <= 2 else "E"

    for position, team in enumerate(
        table,
        start=1
    ):
        team["rank"] = position

    return table

def validate_pool_complete(
    db: Session,
    pool: Pool
):

    teams = db.query(
        Team
    ).filter(
        Team.pool_id == pool.id
    ).all()

    if len(teams) < 2:
        raise HTTPException(
            status_code=400,
            detail=f"{pool.name} does not have enough teams"
        )

    team_ids = {
        team.id
        for team in teams
    }

    # Every team must debate every other team once
    expected_pairs = set()

    ids = list(team_ids)

    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):

            expected_pairs.add(
                tuple(
                    sorted([
                        ids[i],
                        ids[j]
                    ])
                )
            )

    debates = db.query(
        Debate
    ).filter(
        Debate.stage == "pool"
    ).all()

    pool_debates = []

    for debate in debates:

        if (
            debate.team1_id in team_ids
            and
            debate.team2_id in team_ids
        ):
            pool_debates.append(
                debate
            )

    actual_pairs = [
        tuple(
            sorted([
                debate.team1_id,
                debate.team2_id
            ])
        )
        for debate in pool_debates
    ]

    if (
        set(actual_pairs) != expected_pairs
        or
        len(actual_pairs) != len(expected_pairs)
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                f"{pool.name} round robin is not complete"
            )
        )

    for debate in pool_debates:

        if debate.winner_team_id is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"{pool.name} still has pending results"
                )
            )

    standings = calculate_pool_standings(
        db,
        pool.id
    )

    # Qualification / seeding rule:
    # 1. Points / wins
    # 2. Average team score
    #
    # If teams are still exactly tied on both,
    # do not randomly decide qualification.

    def still_tied(
        team_a,
        team_b
    ):

        return (
            team_a["points"]
            == team_b["points"]
            and
            team_a["average_team_score"]
            == team_b["average_team_score"]
        )

    if (
        len(standings) >= 2
        and
        still_tied(
            standings[0],
            standings[1]
        )
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                f"{pool.name}: 1st and 2nd are "
                "still tied on points and "
                "average team score. "
                "Resolve the tie before "
                "generating knockouts."
            )
        )

    if (
        len(standings) >= 3
        and
        still_tied(
            standings[1],
            standings[2]
        )
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                f"{pool.name}: 2nd and 3rd are "
                "still tied on points and "
                "average team score. "
                "Resolve the tie before "
                "generating knockouts."
            )
        )

    return standings


def get_or_create_round(
    db: Session,
    number: int
):

    round_obj = db.query(
        Round
    ).filter(
        Round.number == number
    ).first()

    if not round_obj:

        round_obj = Round(
            number=number,
            motion=None
        )

        db.add(
            round_obj
        )

        db.flush()

    return round_obj


def semifinal_loser(
    debate: Debate
):

    if debate.winner_team_id == debate.team1_id:
        return debate.team2_id

    return debate.team1_id


def sync_knockout_after_semifinals(
    db: Session
):

    semifinals = db.query(
        Debate
    ).filter(
        Debate.stage == "semifinal"
    ).order_by(
        Debate.id
    ).all()

    downstream = db.query(
        Debate
    ).filter(
        Debate.stage.in_([
            "final",
            "third_place"
        ])
    ).all()

    # If both semifinals do not exist or are not finished,
    # Final / Third Place should not exist yet.

    if (
        len(semifinals) != 2
        or
        any(
            debate.winner_team_id is None
            for debate in semifinals
        )
    ):

        for debate in downstream:

            clear_debate_result(
                db,
                debate
            )

            db.delete(
                debate
            )

        return

    sf1 = semifinals[0]
    sf2 = semifinals[1]

    final_team1 = sf1.winner_team_id
    final_team2 = sf2.winner_team_id

    third_team1 = semifinal_loser(
        sf1
    )

    third_team2 = semifinal_loser(
        sf2
    )

    final_round = get_or_create_round(
        db,
        7
    )

    final = db.query(
        Debate
    ).filter(
        Debate.stage == "final"
    ).first()

    if not final:

        final = Debate(
            round_id=final_round.id,
            team1_id=final_team1,
            team2_id=final_team2,
            room=None,
            winner_team_id=None,
            stage="final"
        )

        db.add(
            final
        )

    else:

        teams_changed = (
            final.team1_id != final_team1
            or
            final.team2_id != final_team2
        )

        if teams_changed:

            clear_debate_result(
                db,
                final
            )

            final.team1_id = final_team1
            final.team2_id = final_team2

    third = db.query(
        Debate
    ).filter(
        Debate.stage == "third_place"
    ).first()

    if not third:

        third = Debate(
            round_id=final_round.id,
            team1_id=third_team1,
            team2_id=third_team2,
            room=None,
            winner_team_id=None,
            stage="third_place"
        )

        db.add(
            third
        )

    else:

        teams_changed = (
            third.team1_id != third_team1
            or
            third.team2_id != third_team2
        )

        if teams_changed:

            clear_debate_result(
                db,
                third
            )

            third.team1_id = third_team1
            third.team2_id = third_team2




# ==================================================
# GET DEBATE RESULT
# ==================================================

@app.get("/api/debates/{debate_id}/result")
def get_debate_result(
    debate_id: int,
    db: Session = Depends(get_db)
):

    debate = db.get(
        Debate,
        debate_id
    )

    if not debate:
        raise HTTPException(
            status_code=404,
            detail="Debate not found"
        )

    performances = db.query(
        SpeakerPerformance
    ).filter(
        SpeakerPerformance.debate_id == debate.id
    ).all()
    team1 = db.get(Team, debate.team1_id)
    team2 = db.get(Team, debate.team2_id)
    fixture = (
        fixture_details(team1.name, team2.name)
        if debate.stage == "pool" and team1 and team2
        else None
    )
    team_averages = debate_team_averages(db, debate)
    result_breakdown = debate_result_breakdown(db, debate, fixture)
    side_ids = debate_side_team_ids(db, debate, fixture)

    return {
        "debate_id": debate.id,
        "winner_team_id": debate.winner_team_id,
        "government_reply_score": debate.government_reply_score,
        "opposition_reply_score": debate.opposition_reply_score,
        "government_team_id": side_ids["Government"],
        "opposition_team_id": side_ids["Opposition"],
        "team_averages": {
            str(team_id): average
            for team_id, average in team_averages.items()
        },
        "team_total_scores": {
            str(team_id): details["total_score"]
            for team_id, details in result_breakdown.items()
        },
        "performances": [
            {
                "speaker_id": performance.speaker_id,
                "role": performance.role,
                "score": performance.score,
                "is_swing": performance.is_swing,
            }
            for performance in performances
        ]
    }


# ==================================================
# CLEAR DEBATE RESULT
# ==================================================

@app.delete("/api/debates/{debate_id}/result")
def clear_result(
    debate_id: int,
    db: Session = Depends(get_db)
):

    debate = db.get(
        Debate,
        debate_id
    )

    if not debate:
        raise HTTPException(
            status_code=404,
            detail="Debate not found"
        )

    if (
        debate.stage == "pool"
        and
        knockouts_exist(db)
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Reset knockouts before clearing "
                "a pool-stage result"
            )
        )

    clear_debate_result(
        db,
        debate
    )

    if debate.stage == "semifinal":
        sync_knockout_after_semifinals(
            db
        )

    db.commit()

    return {
        "message": "Result cleared successfully"
    }


# ==================================================
# POOL EDIT / DELETE
# ==================================================

@app.put("/api/pools/{pool_id}")
def update_pool(
    pool_id: int,
    data: PoolUpdate,
    db: Session = Depends(get_db)
):

    pool = db.get(
        Pool,
        pool_id
    )

    if not pool:
        raise HTTPException(
            status_code=404,
            detail="Pool not found"
        )

    pool.name = data.name

    db.commit()
    db.refresh(pool)

    return {
        "id": pool.id,
        "name": pool.name
    }


@app.delete("/api/pools/{pool_id}")
def delete_pool(
    pool_id: int,
    db: Session = Depends(get_db)
):

    pool = db.get(
        Pool,
        pool_id
    )

    if not pool:
        raise HTTPException(
            status_code=404,
            detail="Pool not found"
        )

    team = db.query(
        Team
    ).filter(
        Team.pool_id == pool.id
    ).first()

    if team:
        raise HTTPException(
            status_code=400,
            detail="Delete or move teams in this pool first"
        )

    db.delete(pool)
    db.commit()

    return {
        "message": "Pool deleted successfully"
    }


# ==================================================
# TEAM DELETE
# ==================================================

@app.delete("/api/teams/{team_id}")
def delete_team(
    team_id: int,
    db: Session = Depends(get_db)
):

    team = db.get(
        Team,
        team_id
    )

    if not team:
        raise HTTPException(
            status_code=404,
            detail="Team not found"
        )

    speaker = db.query(
        Speaker
    ).filter(
        Speaker.team_id == team.id
    ).first()

    if speaker:
        raise HTTPException(
            status_code=400,
            detail="Delete or move this team's speakers first"
        )

    debate = db.query(
        Debate
    ).filter(
        (Debate.team1_id == team.id)
        |
        (Debate.team2_id == team.id)
    ).first()

    if debate:
        raise HTTPException(
            status_code=400,
            detail=(
                "Cannot delete team because it "
                "already appears in debates"
            )
        )

    db.delete(team)
    db.commit()

    return {
        "message": "Team deleted successfully"
    }


# ==================================================
# ROUND EDIT / DELETE
# ==================================================

@app.put("/api/rounds/{round_id}")
def update_round(
    round_id: int,
    data: RoundUpdate,
    db: Session = Depends(get_db)
):

    round_obj = db.get(
        Round,
        round_id
    )

    if not round_obj:
        raise HTTPException(
            status_code=404,
            detail="Round not found"
        )

    round_obj.number = data.number
    round_obj.motion = data.motion

    db.commit()
    db.refresh(round_obj)

    return {
        "id": round_obj.id,
        "number": round_obj.number,
        "motion": round_obj.motion
    }


@app.delete("/api/rounds/{round_id}")
def delete_round(
    round_id: int,
    db: Session = Depends(get_db)
):

    round_obj = db.get(
        Round,
        round_id
    )

    if not round_obj:
        raise HTTPException(
            status_code=404,
            detail="Round not found"
        )

    debate = db.query(
        Debate
    ).filter(
        Debate.round_id == round_obj.id
    ).first()

    if debate:
        raise HTTPException(
            status_code=400,
            detail="Delete debates in this round first"
        )

    db.delete(round_obj)
    db.commit()

    return {
        "message": "Round deleted successfully"
    }


# ==================================================
# DEBATE EDIT / DELETE
# ==================================================

@app.put("/api/debates/{debate_id}")
def update_debate(
    debate_id: int,
    data: DebateUpdate,
    db: Session = Depends(get_db)
):

    debate = db.get(
        Debate,
        debate_id
    )

    if not debate:
        raise HTTPException(
            status_code=404,
            detail="Debate not found"
        )

    round_obj = db.get(
        Round,
        data.round_id
    )

    team1 = db.get(
        Team,
        data.team1_id
    )

    team2 = db.get(
        Team,
        data.team2_id
    )

    if not round_obj:
        raise HTTPException(
            status_code=404,
            detail="Round not found"
        )

    if not team1 or not team2:
        raise HTTPException(
            status_code=404,
            detail="Team not found"
        )

    if team1.id == team2.id:
        raise HTTPException(
            status_code=400,
            detail="A team cannot debate itself"
        )

    stage = data.stage.lower()

    if stage not in ALLOWED_STAGES:
        raise HTTPException(
            status_code=400,
            detail="Invalid debate stage"
        )

    if (
        stage == "pool"
        and
        team1.pool_id != team2.pool_id
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Pool-stage teams must be "
                "from the same pool"
            )
        )

    old_stage = debate.stage

    important_change = (
        debate.team1_id != team1.id
        or
        debate.team2_id != team2.id
        or
        debate.stage != stage
    )

    if important_change:
        clear_debate_result(
            db,
            debate
        )

    debate.round_id = round_obj.id
    debate.team1_id = team1.id
    debate.team2_id = team2.id
    debate.room = data.room
    debate.stage = stage

    if (
        old_stage == "semifinal"
        or
        stage == "semifinal"
    ):
        sync_knockout_after_semifinals(
            db
        )

    db.commit()
    db.refresh(debate)

    return {
        "id": debate.id,
        "round_id": debate.round_id,
        "team1_id": debate.team1_id,
        "team2_id": debate.team2_id,
        "room": debate.room,
        "winner_team_id": debate.winner_team_id,
        "stage": debate.stage
    }


@app.delete("/api/debates/{debate_id}")
def delete_debate(
    debate_id: int,
    db: Session = Depends(get_db)
):

    debate = db.get(
        Debate,
        debate_id
    )

    if not debate:
        raise HTTPException(
            status_code=404,
            detail="Debate not found"
        )

    if (
        debate.stage == "pool"
        and
        knockouts_exist(db)
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Reset knockouts before deleting "
                "pool-stage debates"
            )
        )

    old_stage = debate.stage

    clear_debate_result(
        db,
        debate
    )

    db.delete(debate)
    db.flush()

    if old_stage == "semifinal":
        sync_knockout_after_semifinals(
            db
        )

    db.commit()

    return {
        "message": "Debate deleted successfully"
    }


# ==================================================
# KNOCKOUTS
# ==================================================

@app.post("/api/knockouts/generate")
def generate_knockouts(
    db: Session = Depends(get_db)
):

    if knockouts_exist(db):
        raise HTTPException(
            status_code=400,
            detail="Knockout stage already exists"
        )

    pools = db.query(
        Pool
    ).all()

    pool_a = next(
        (
            pool
            for pool in pools
            if pool.name.strip().lower() == "pool a"
        ),
        None
    )

    pool_b = next(
        (
            pool
            for pool in pools
            if pool.name.strip().lower() == "pool b"
        ),
        None
    )

    if not pool_a or not pool_b:
        raise HTTPException(
            status_code=400,
            detail="Pool A and Pool B must both exist"
        )

    standings_a = validate_pool_complete(
        db,
        pool_a
    )

    standings_b = validate_pool_complete(
        db,
        pool_b
    )

    a1 = standings_a[0]["team_id"]
    a2 = standings_a[1]["team_id"]

    b1 = standings_b[0]["team_id"]
    b2 = standings_b[1]["team_id"]

    semifinal_round = get_or_create_round(
        db,
        6
    )

    semifinal1 = Debate(
        round_id=semifinal_round.id,
        team1_id=a1,
        team2_id=b2,
        room=None,
        winner_team_id=None,
        stage="semifinal"
    )

    semifinal2 = Debate(
        round_id=semifinal_round.id,
        team1_id=b1,
        team2_id=a2,
        room=None,
        winner_team_id=None,
        stage="semifinal"
    )

    db.add_all([
        semifinal1,
        semifinal2
    ])

    db.commit()

    db.refresh(semifinal1)
    db.refresh(semifinal2)

    return {
        "message": "Semifinals generated successfully",
        "semifinal_1": {
            "debate_id": semifinal1.id,
            "team1_id": a1,
            "team2_id": b2
        },
        "semifinal_2": {
            "debate_id": semifinal2.id,
            "team1_id": b1,
            "team2_id": a2
        }
    }


@app.delete("/api/knockouts")
def reset_knockouts(
    db: Session = Depends(get_db)
):

    knockouts = db.query(
        Debate
    ).filter(
        Debate.stage != "pool"
    ).all()

    for debate in knockouts:

        clear_debate_result(
            db,
            debate
        )

        db.delete(
            debate
        )

    db.commit()

    return {
        "message": "Knockout stage reset successfully"
    }


# ==================================================
# CLEAN PUBLIC SCHEDULE API
# ==================================================

@app.get("/api/schedule")
def schedule_api(
    db: Session = Depends(get_db)
):

    debates = db.query(
        Debate
    ).all()

    rounds = {
        round_obj.id: round_obj
        for round_obj in db.query(Round).all()
    }

    teams = {
        team.id: team
        for team in db.query(Team).all()
    }

    pools = {
        pool.id: pool
        for pool in db.query(Pool).all()
    }

    stage_names = {
        "pool": "Pool Stage",
        "semifinal": "Semifinal",
        "third_place": "Third Place Match",
        "final": "Final"
    }

    stage_order = {
        "pool": 0,
        "semifinal": 1,
        "third_place": 2,
        "final": 3
    }

    schedule = []

    for debate in debates:

        team1 = teams.get(
            debate.team1_id
        )

        team2 = teams.get(
            debate.team2_id
        )

        round_obj = rounds.get(
            debate.round_id
        )

        pool_name = None

        if (
            debate.stage == "pool"
            and
            team1
        ):
            pool = pools.get(
                team1.pool_id
            )

            if pool:
                pool_name = pool.name

        winner = (
            teams.get(debate.winner_team_id)
            if debate.winner_team_id
            else None
        )
        fixture = (
            fixture_details(team1.name, team2.name)
            if debate.stage == "pool" and team1 and team2
            else None
        )
        team_averages = debate_team_averages(db, debate)
        result_breakdown = debate_result_breakdown(db, debate, fixture)
        side_ids = debate_side_team_ids(db, debate, fixture)
        team1_side = next(
            (side for side, team_id in side_ids.items() if team_id == debate.team1_id),
            None,
        )
        team2_side = next(
            (side for side, team_id in side_ids.items() if team_id == debate.team2_id),
            None,
        )

        schedule.append({
            "debate_id": debate.id,
            "debate_number": fixture["number"] if fixture else None,
            "date": fixture["date"].isoformat() if fixture else None,
            "date_label": fixture["date_label"] if fixture else None,
            "day": fixture["day"] if fixture else None,
            "time": fixture["time_label"] if fixture else None,
            "stage": debate.stage,
            "stage_name": stage_names.get(
                debate.stage,
                debate.stage
            ),
            "round_number": (
                round_obj.number
                if round_obj
                else None
            ),
            "motion": (
                round_obj.motion
                if round_obj
                else None
            ),
            "pool": pool_name,
            "team1": {
                "id": team1.id,
                "name": team1.name,
                "emoji": TEAM_EMOJIS_2026.get(team1.name),
                "side": team1_side,
                "average_score": team_averages.get(team1.id),
                "reply_score": result_breakdown[team1.id]["reply_score"],
                "total_score": result_breakdown[team1.id]["total_score"],
                "performances": result_breakdown[team1.id]["performances"],
            } if team1 else None,
            "team2": {
                "id": team2.id,
                "name": team2.name,
                "emoji": TEAM_EMOJIS_2026.get(team2.name),
                "side": team2_side,
                "average_score": team_averages.get(team2.id),
                "reply_score": result_breakdown[team2.id]["reply_score"],
                "total_score": result_breakdown[team2.id]["total_score"],
                "performances": result_breakdown[team2.id]["performances"],
            } if team2 else None,
            "room": debate.room,
            "winner": {
                "id": winner.id,
                "name": winner.name,
                "emoji": TEAM_EMOJIS_2026.get(winner.name),
            } if winner else None,
            "status": (
                "Completed"
                if winner
                else "Pending"
            )
        })

    schedule.sort(
        key=lambda debate: (
            stage_order.get(
                debate["stage"],
                99
            ),
            debate["debate_number"] or debate["round_number"] or 99,
            debate["debate_id"]
        )
    )

    return schedule
