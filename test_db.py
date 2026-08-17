import unittest
from collections import Counter

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import (
    AuctionTeam,
    Base,
    Debate,
    Pool,
    Round,
    Speaker,
    SpeakerPerformance,
    Team,
)
from season_2026 import (
    GROUP_STAGE_TIME_2026,
    OFFICIAL_DAY_1_RESULTS_2026,
    OFFICIAL_GROUP_STAGE_2026,
    OFFICIAL_POOLS_2026,
    TEAM_EMOJIS_2026,
    fixture_details,
    sync_official_2026_tournament,
    validate_official_group_stage,
)
from main import (
    calculate_pool_standings,
    debate_team_averages,
    get_debate_result,
    schedule_api,
    speaker_rankings,
    standings,
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
        self.assertEqual(self.db.query(Speaker).count(), 40)
        self.assertEqual(self.db.query(SpeakerPerformance).count(), 12)

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

    def test_official_day_one_results_use_existing_speakers(self):
        teams = {team.id: team for team in self.db.query(Team).all()}
        speakers = {
            speaker.id: speaker
            for speaker in self.db.query(Speaker).all()
        }
        debates = {
            round_number: debate
            for debate, round_number in self.db.query(
                Debate,
                Round.number,
            ).join(
                Round,
                Round.id == Debate.round_id,
            ).filter(
                Round.number.in_([1, 2])
            ).all()
        }

        self.assertEqual(set(debates), {1, 2})
        actual = {}
        for fixture_number, debate in debates.items():
            winner = teams[debate.winner_team_id]
            performances = self.db.query(SpeakerPerformance).filter(
                SpeakerPerformance.debate_id == debate.id
            ).all()
            self.assertEqual(len(performances), 6)
            self.assertEqual(
                len({performance.speaker_id for performance in performances}),
                6,
            )
            for performance in performances:
                speaker = speakers[performance.speaker_id]
                actual[
                    (
                        fixture_number,
                        teams[speaker.team_id].name,
                        speaker.name,
                        performance.role,
                    )
                ] = performance.score

            official = next(
                result
                for result in OFFICIAL_DAY_1_RESULTS_2026
                if result["fixture_number"] == fixture_number
            )
            self.assertEqual(winner.name, official["winner_team"])

        expected = {
            (result["fixture_number"], team, speaker, role): score
            for result in OFFICIAL_DAY_1_RESULTS_2026
            for team, speaker, role, score in result["performances"]
        }
        self.assertEqual(actual, expected)
        self.assertEqual(self.db.query(Speaker).count(), 40)

    def test_day_one_sides_averages_and_result_payloads(self):
        debate1 = self.db.query(Debate).join(Round).filter(Round.number == 1).one()
        debate2 = self.db.query(Debate).join(Round).filter(Round.number == 2).one()
        teams = {team.name: team for team in self.db.query(Team).all()}

        fixture1 = fixture_details(
            "Damsel Inflicting Distress",
            "Akali Dinosaurs",
        )
        self.assertEqual(fixture1["team1_side"], "Opposition")
        self.assertEqual(fixture1["team2_side"], "Government")
        fixture2 = fixture_details("Goodfellas", "Broken Orators")
        self.assertEqual(fixture2["team1_side"], "Opposition")
        self.assertEqual(fixture2["team2_side"], "Government")

        self.assertEqual(
            debate_team_averages(self.db, debate1),
            {
                teams["Damsel Inflicting Distress"].id: 73.67,
                teams["Akali Dinosaurs"].id: 72.67,
            },
        )
        self.assertEqual(
            debate_team_averages(self.db, debate2),
            {
                teams["Goodfellas"].id: 72.17,
                teams["Broken Orators"].id: 73.0,
            },
        )

        result1 = get_debate_result(debate1.id, db=self.db)
        self.assertEqual(
            result1["winner_team_id"],
            teams["Damsel Inflicting Distress"].id,
        )
        self.assertEqual(
            result1["opposition_team_id"],
            teams["Damsel Inflicting Distress"].id,
        )
        self.assertEqual(
            result1["government_team_id"],
            teams["Akali Dinosaurs"].id,
        )
        self.assertIn(73.5, [item["score"] for item in result1["performances"]])
        self.assertIn(74.5, [item["score"] for item in result1["performances"]])

        schedule = {
            item["debate_number"]: item
            for item in schedule_api(db=self.db)
            if item["debate_number"] in (1, 2)
        }
        self.assertEqual({item["status"] for item in schedule.values()}, {"Completed"})
        self.assertEqual(schedule[1]["team1"]["side"], "Opposition")
        self.assertEqual(schedule[1]["team2"]["side"], "Government")
        self.assertEqual(schedule[1]["team1"]["average_score"], 73.67)
        self.assertEqual(schedule[1]["team2"]["average_score"], 72.67)
        self.assertEqual(schedule[2]["team1"]["average_score"], 72.17)
        self.assertEqual(schedule[2]["team2"]["average_score"], 73.0)

    def test_day_one_standings_and_speaker_rankings_are_derived(self):
        pools = {pool.name: pool for pool in self.db.query(Pool).all()}
        pool_a = {
            row["team_name"]: row
            for row in calculate_pool_standings(self.db, pools["Pool A"].id)
        }
        pool_b = {
            row["team_name"]: row
            for row in calculate_pool_standings(self.db, pools["Pool B"].id)
        }

        self.assertEqual(
            (pool_a["Broken Orators"]["wins"], pool_a["Broken Orators"]["losses"]),
            (1, 0),
        )
        self.assertEqual(
            (pool_a["Goodfellas"]["wins"], pool_a["Goodfellas"]["losses"]),
            (0, 1),
        )
        self.assertEqual(pool_a["Broken Orators"]["average_team_score"], 73.0)
        self.assertEqual(pool_a["Goodfellas"]["average_team_score"], 72.17)
        self.assertEqual(
            (pool_b["Damsel Inflicting Distress"]["wins"], pool_b["Damsel Inflicting Distress"]["losses"]),
            (1, 0),
        )
        self.assertEqual(
            (pool_b["Akali Dinosaurs"]["wins"], pool_b["Akali Dinosaurs"]["losses"]),
            (0, 1),
        )
        self.assertEqual(pool_b["Damsel Inflicting Distress"]["average_team_score"], 73.67)
        self.assertEqual(pool_b["Akali Dinosaurs"]["average_team_score"], 72.67)

        for unaffected in (
            pool_a["Mechanised Yappers"],
            pool_a["Rhetoric Rebels"],
            pool_b["Fifth Amendment"],
            pool_b["Motion Granted"],
        ):
            self.assertEqual(
                (unaffected["played"], unaffected["wins"], unaffected["losses"]),
                (0, 0, 0),
            )
            self.assertEqual(unaffected["average_team_score"], 0.0)

        overall = {row["team_name"]: row for row in standings(db=self.db)}
        self.assertEqual(len(overall), 8)
        rankings = {
            row["speaker_name"]: row
            for row in speaker_rankings(db=self.db)
        }
        self.assertEqual(len(rankings), 12)
        self.assertEqual(rankings["Prabhleen"]["average_score"], 74.5)
        self.assertEqual(rankings["Mudit"]["average_score"], 73.5)
        self.assertEqual(rankings["Rahul Batra"]["average_score"], 71.5)
        self.assertTrue(
            all(row["debates"] == 1 for row in rankings.values())
        )

    def test_restart_repairs_day_one_duplicates_and_preserves_future_results(self):
        debate_ids = {
            number: debate.id
            for debate, number in self.db.query(Debate, Round.number).join(Round).all()
        }
        day_one_performance_ids = {
            performance.id
            for performance in self.db.query(SpeakerPerformance).all()
        }
        debate1 = self.db.get(Debate, debate_ids[1])
        rachel = self.db.query(Speaker).join(Team).filter(
            Team.name == "Damsel Inflicting Distress",
            Speaker.name == "Rachel",
        ).one()
        unused_damsel = self.db.query(Speaker).join(Team).filter(
            Team.name == "Damsel Inflicting Distress",
            Speaker.name == "Saksham",
        ).one()
        self.db.add_all([
            SpeakerPerformance(
                debate_id=debate1.id,
                speaker_id=rachel.id,
                role="Duplicate",
                score=1.0,
            ),
            SpeakerPerformance(
                debate_id=debate1.id,
                speaker_id=unused_damsel.id,
                role="Not in lineup",
                score=99.0,
            ),
        ])
        debate1.winner_team_id = debate1.team2_id

        future = self.db.get(Debate, debate_ids[3])
        future.winner_team_id = future.team1_id
        future_speaker = self.db.query(Speaker).filter(
            Speaker.team_id == future.team1_id
        ).first()
        future_performance = SpeakerPerformance(
            debate_id=future.id,
            speaker_id=future_speaker.id,
            role="Prime Minister",
            score=80.0,
        )
        self.db.add(future_performance)
        self.db.commit()
        future_performance_id = future_performance.id

        sync_official_2026_tournament(self.db)
        sync_official_2026_tournament(self.db)

        self.assertEqual(
            {
                number: debate.id
                for debate, number in self.db.query(Debate, Round.number).join(Round).all()
            },
            debate_ids,
        )
        self.assertEqual(
            {
                performance.id
                for performance in self.db.query(SpeakerPerformance).filter(
                    SpeakerPerformance.debate_id.in_([debate_ids[1], debate_ids[2]])
                )
            },
            day_one_performance_ids,
        )
        self.assertEqual(
            self.db.query(SpeakerPerformance).filter(
                SpeakerPerformance.debate_id == debate_ids[1]
            ).count(),
            6,
        )
        self.assertEqual(
            self.db.get(Debate, debate_ids[1]).winner_team_id,
            self.db.query(Team).filter(
                Team.name == "Damsel Inflicting Distress"
            ).one().id,
        )
        future = self.db.get(Debate, debate_ids[3])
        self.assertEqual(future.winner_team_id, future.team1_id)
        future_performance = self.db.get(SpeakerPerformance, future_performance_id)
        self.assertIsNotNone(future_performance)
        self.assertEqual(future_performance.score, 80.0)

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
        debates = self.db.query(Debate).join(Round).filter(
            ((Debate.team1_id == team.id) | (Debate.team2_id == team.id)),
            Round.number.in_([6, 8]),
        ).order_by(Round.number).all()
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
        self.assertEqual(len(performances), 3)
        self.assertEqual({performance.score for performance in performances}, {74, 75, 77})


if __name__ == "__main__":
    unittest.main()
