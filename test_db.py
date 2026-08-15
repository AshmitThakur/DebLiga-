import unittest
from collections import Counter

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import (
    AuctionTeam,
    Base,
    Debate,
    Pool,
    Speaker,
    SpeakerPerformance,
    Team,
)
from season_2026 import (
    GROUP_STAGE_TIME_2026,
    OFFICIAL_GROUP_STAGE_2026,
    OFFICIAL_POOLS_2026,
    TEAM_EMOJIS_2026,
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
        official_names = {
            name
            for pool_teams in OFFICIAL_POOLS_2026.values()
            for name, _ in pool_teams
        }
        self.assertEqual(set(TEAM_EMOJIS_2026), official_names)
        self.assertTrue(all(TEAM_EMOJIS_2026.values()))

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
            self.assertEqual(details["time_label"], GROUP_STAGE_TIME_2026)
            self.assertEqual(details["time_sort"], "18:30")
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

    def test_goodfellas_revised_auction_bids(self):
        team = self.db.query(AuctionTeam).filter(
            AuctionTeam.team_name == "Goodfellas"
        ).one()
        prices = {player.player_name: player.price for player in team.players}
        self.assertEqual(prices["Manroop Singh"], 25500)
        self.assertEqual(prices["Vallari"], 6000)
        self.assertEqual(sum(prices.values()), 44000)
        self.assertEqual(team.auction.purse - sum(prices.values()), 6000)

    def test_mohit_names_are_unambiguous(self):
        teams = {
            team.team_name: {player.player_name for player in team.players}
            for team in self.db.query(AuctionTeam).all()
        }
        self.assertIn("Mohit Sharma", teams["Broken Orators"])
        self.assertIn("Mohit Verma", teams["Fifth Amendment"])
        self.assertNotIn("Mohit", teams["Broken Orators"])
        self.assertNotIn("Mohit", teams["Fifth Amendment"])
        competition_teams = {
            team.name: team.id
            for team in self.db.query(Team).all()
        }
        for team_name, full_name in (
            ("Broken Orators", "Mohit Sharma"),
            ("Fifth Amendment", "Mohit Verma"),
        ):
            names = {
                speaker.name
                for speaker in self.db.query(Speaker).filter(
                    Speaker.team_id == competition_teams[team_name]
                )
            }
            self.assertIn(full_name, names)
            self.assertNotIn("Mohit", names)

    def test_guransh_duplicate_merge_preserves_performances(self):
        team = self.db.query(Team).filter(Team.name == "Akali Dinosaurs").one()
        canonical = self.db.query(Speaker).filter(
            Speaker.team_id == team.id,
            Speaker.name == "Guransh",
        ).one()
        duplicate = Speaker(name="Gurnash", team_id=team.id)
        self.db.add(duplicate)
        self.db.flush()
        debates = self.db.query(Debate).filter(
            (Debate.team1_id == team.id) | (Debate.team2_id == team.id)
        ).order_by(Debate.id).limit(2).all()
        self.db.add_all([
            SpeakerPerformance(
                debate_id=debates[0].id,
                speaker_id=canonical.id,
                role="Prime Minister",
                score=75,
            ),
            SpeakerPerformance(
                debate_id=debates[1].id,
                speaker_id=duplicate.id,
                role="Deputy Prime Minister",
                score=77,
            ),
        ])
        self.db.commit()

        sync_official_2026_tournament(self.db)

        speakers = self.db.query(Speaker).filter(Speaker.team_id == team.id).all()
        self.assertEqual(len(speakers), 5)
        self.assertEqual(sum(speaker.name == "Guransh" for speaker in speakers), 1)
        self.assertNotIn("Gurnash", {speaker.name for speaker in speakers})
        performances = self.db.query(SpeakerPerformance).filter(
            SpeakerPerformance.speaker_id == canonical.id
        ).all()
        self.assertEqual(len(performances), 2)
        self.assertEqual({performance.score for performance in performances}, {75, 77})


if __name__ == "__main__":
    unittest.main()
