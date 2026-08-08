from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import engine, get_db

from models import (
    Base,
    Debate,
    Pool,
    Round,
    Speaker,
    SpeakerPerformance,
    Team,
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


# --------------------------------------------------
# HOMEPAGE
# --------------------------------------------------

@app.get(
    "/",
    response_class=HTMLResponse
)
def home(
    request: Request
):
    hall_of_fame = [
        {"year": "2021", "team": "Nirvana", "winner": "Shreya"},
        {"year": "2022", "team": "The Mavens", "winner": "Chhawinder"},
        {"year": "2023", "team": "The Raging Raccoons", "winner": "Preeti"},
        {"year": "2024", "team": "Coffee Tea Spikers", "winner": "Adesh"},
        {"year": "2025", "team": "Panel Pls Understand", "winner": "Sukhman"},
        {"year": "2026", "team": "???", "winner": "???"},
    ]

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "tournament_name": "LADC Debate League 2026",
            "edition": "6th Edition",
            "club_name": "Literary and Debating Club",
            "hall_of_fame": hall_of_fame,
        },
    )


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
        "pool_id": team.pool_id
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
            "pool_id": team.pool_id
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
    used_speakers = set()

    for performance in data.performances:

        if performance.speaker_id in used_speakers:
            raise HTTPException(
                status_code=400,
                detail="Same speaker entered more than once"
            )

        used_speakers.add(
            performance.speaker_id
        )

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
                score=performance.score
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

    teams = db.query(Team).all()
    speakers = db.query(Speaker).all()

    team_data = []

    for team in teams:

        team_speakers = [
            speaker
            for speaker in speakers
            if speaker.team_id == team.id
        ]

        team_data.append({
            "id": team.id,
            "name": team.name,
            "pool_id": team.pool_id,
            "speakers": team_speakers
        })

    return templates.TemplateResponse(
        request=request,
        name="teams.html",
        context={
            "teams": team_data
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
            "status": (
                "Completed"
                if winner
                else "Pending"
            )
        })

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
        Speaker.team_id == team.id
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

        history.append({
            "debate": debate,
            "round": round_obj,
            "opponent": opponent,
            "result": result,
            "team_average_score":
                team_average,
            "opponent_average_score":
                opponent_average
        })

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
        == speaker.id
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
        "pool_id": team.pool_id
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

    return {
        "debate_id": debate.id,
        "winner_team_id": debate.winner_team_id,
        "performances": [
            {
                "speaker_id": performance.speaker_id,
                "role": performance.role,
                "score": performance.score
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

        schedule.append({
            "debate_id": debate.id,
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
                "name": team1.name
            } if team1 else None,
            "team2": {
                "id": team2.id,
                "name": team2.name
            } if team2 else None,
            "room": debate.room,
            "winner": {
                "id": winner.id,
                "name": winner.name
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
            debate["round_number"] or 99,
            debate["debate_id"]
        )
    )

    return schedule