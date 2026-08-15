import unittest
from collections import Counter

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base, Debate, Pool, Team
from season_2026 import (
    OFFICIAL_GROUP_STAGE_2026,
    OFFICIAL_POOLS_2026,
    fixture_details,
    sync_official_2026_tournament,
    validate_official_group_stage,
)


class OfficialTournamentDataTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        sync_official_2026_tournament(self.db)
        sync_official_2026_tournament(self.db)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_canonical_fixture_validation(self):
        validate_official_group_stage()
        self.assertEqual(len(OFFICIAL_GROUP_STAGE_2026), 12)

    def test_database_sync_is_complete_and_idempotent(self):
        pools = {pool.id: pool.name for pool in self.db.query(Pool).all()}
        teams = {team.id: team for team in self.db.query(Team).all()}
        debates = self.db.query(Debate).filter(Debate.stage == "pool").all()

        self.assertEqual(len(teams), 8)
        self.assertEqual(len(debates), 12)

        daily_counts = Counter()
        pool_counts = Counter()
        team_counts = Counter()
        pairings = set()
        for debate in debates:
            team1 = teams[debate.team1_id]
            team2 = teams[debate.team2_id]
            details = fixture_details(team1.name, team2.name)
            self.assertIsNotNone(details)
            self.assertEqual(team1.pool_id, team2.pool_id)
            daily_counts[details["date"]] += 1
            pool_counts[pools[team1.pool_id]] += 1
            team_counts.update((team1.name, team2.name))
            pairings.add(frozenset((team1.name, team2.name)))

        self.assertEqual(
            [daily_counts[fixture_date] for fixture_date in sorted(daily_counts)],
            [2, 2, 2, 3, 3],
        )
        self.assertEqual(pool_counts, {"Pool A": 6, "Pool B": 6})
        self.assertEqual(set(team_counts.values()), {3})
        self.assertEqual(len(pairings), 12)
        self.assertEqual(
            set(team_counts),
            {
                name
                for pool_teams in OFFICIAL_POOLS_2026.values()
                for name, _ in pool_teams
            },
        )


if __name__ == "__main__":
    unittest.main()
