from database import SessionLocal
from models import Team, Speaker


db = SessionLocal()

# Find Team Phoenix
team = db.query(Team).filter(
    Team.name == "Team Phoenix"
).first()

# Find all speakers in that team
speakers = db.query(Speaker).filter(
    Speaker.team_id == team.id
).all()

print("Team:", team.name)
print("Speakers:")

for speaker in speakers:
    print("-", speaker.name)

db.close()