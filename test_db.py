from database import SessionLocal
from models import Team, Speaker


db = SessionLocal()

# Find Team Phoenix
team = db.query(Team).filter(
    Team.name == "Team Phoenix"
).first()

# Create speaker
speaker = Speaker(
    name="Ashmit",
    team_id=team.id
)

db.add(speaker)
db.commit()
db.refresh(speaker)

print("Speaker:", speaker.name)
print("Team ID:", speaker.team_id)

db.close()