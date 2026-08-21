import unittest
from collections import Counter

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
from starlette.requests import Request

from database import migrate_existing_schema

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
    OFFICIAL_RESULTS_2026,
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
    official_2026_semifinal_bracket,
    rankings_page,
    schedule_page,
    schedule_api,
    speaker_rankings,
    speaker_detail_page,
    standings,
    standings_page,
    sync_official_2026_semifinals,
    team_detail_page,
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

    def test_reply_column_migration_is_idempotent_for_existing_sqlite_database(self):
        legacy_engine = create_engine("sqlite:///:memory:")
        with legacy_engine.begin() as connection:
            connection.execute(text(
                "CREATE TABLE debates (id INTEGER PRIMARY KEY, stage VARCHAR(30))"
            ))
            connection.execute(text(
                "CREATE TABLE speaker_performances (id INTEGER PRIMARY KEY)"
            ))
            connection.execute(text(
                "CREATE TABLE speakers (id INTEGER PRIMARY KEY)"
            ))

        migrate_existing_schema(legacy_engine)
        migrate_existing_schema(legacy_engine)

        column_names = {
            column["name"]
            for column in inspect(legacy_engine).get_columns("debates")
        }
        self.assertIn("government_reply_score", column_names)
        self.assertIn("opposition_reply_score", column_names)
        performance_column_names = {
            column["name"]
            for column in inspect(legacy_engine).get_columns("speaker_performances")
        }
        self.assertIn("is_swing", performance_column_names)
        speaker_column_names = {
            column["name"]
            for column in inspect(legacy_engine).get_columns("speakers")
        }
        self.assertIn("active", speaker_column_names)
        legacy_engine.dispose()

    def test_database_sync_is_complete_and_idempotent(self):
        pools = {pool.id: pool.name for pool in self.db.query(Pool).all()}
        teams = {team.id: team for team in self.db.query(Team).all()}
        debates = self.db.query(Debate).filter(Debate.stage == "pool").all()

        self.assertEqual(len(teams), 8)
        self.assertEqual(len(debates), 12)
        self.assertEqual(self.db.query(Speaker).count(), 40)
        self.assertEqual(self.db.query(SpeakerPerformance).count(), 66)

        daily_counts = Counter()
        pool_counts = Counter()
        team_counts = Counter()
        pairings = set()
        for debate in debates:
            team1 = teams[debate.team1_id]
            team2 = teams[debate.team2_id]
            details = fixture_details(team1.name, team2.name)
            self.assertIsNotNone(details)
            expected_time = "9:00 AM" if details["number"] == 12 else GROUP_STAGE_TIME_2026
            expected_time_sort = "09:00" if details["number"] == 12 else "18:30"
            self.assertEqual(details["time_label"], expected_time)
            self.assertEqual(details["time_sort"], expected_time_sort)
            self.assertEqual(team1.pool_id, team2.pool_id)
            daily_counts[details["date"]] += 1
            pool_counts[pools[team1.pool_id]] += 1
            team_counts.update((team1.name, team2.name))
            pairings.add(frozenset((team1.name, team2.name)))

        self.assertEqual(
            [daily_counts[fixture_date] for fixture_date in sorted(daily_counts)],
            [2, 2, 2, 3, 2, 1],
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
            "Damsel Inflicting Stress",
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
                teams["Damsel Inflicting Stress"].id: 73.67,
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
            teams["Damsel Inflicting Stress"].id,
        )
        self.assertEqual(
            result1["opposition_team_id"],
            teams["Damsel Inflicting Stress"].id,
        )
        self.assertEqual(
            result1["government_team_id"],
            teams["Akali Dinosaurs"].id,
        )
        self.assertIn(73.5, [item["score"] for item in result1["performances"]])
        self.assertIn(74.5, [item["score"] for item in result1["performances"]])
        self.assertEqual(result1["government_reply_score"], 37.0)
        self.assertEqual(result1["opposition_reply_score"], 37.0)
        result2 = get_debate_result(debate2.id, db=self.db)
        self.assertEqual(result2["government_reply_score"], 37.0)
        self.assertEqual(result2["opposition_reply_score"], 37.0)

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

    def test_day_two_results_use_official_winners_and_separate_reply_scores(self):
        debates = {
            number: debate
            for debate, number in self.db.query(Debate, Round.number).join(Round).filter(
                Round.number.in_([3, 4])
            ).all()
        }
        teams = {team.name: team for team in self.db.query(Team).all()}

        self.assertEqual(
            self.db.get(Team, debates[3].winner_team_id).name,
            "Mechanised Yappers",
        )
        self.assertEqual(
            self.db.get(Team, debates[4].winner_team_id).name,
            "Fifth Amendment",
        )
        self.assertEqual(
            debate_team_averages(self.db, debates[3]),
            {
                teams["Mechanised Yappers"].id: 72.83,
                teams["Rhetoric Rebels"].id: 72.67,
            },
        )
        self.assertEqual(
            debate_team_averages(self.db, debates[4]),
            {
                teams["Fifth Amendment"].id: 72.5,
                teams["Motion Granted"].id: 72.67,
            },
        )

        result3 = get_debate_result(debates[3].id, db=self.db)
        result4 = get_debate_result(debates[4].id, db=self.db)
        self.assertEqual(
            (result3["government_reply_score"], result3["opposition_reply_score"]),
            (37.0, 37.0),
        )
        self.assertEqual(
            (result4["government_reply_score"], result4["opposition_reply_score"]),
            (36.0, 37.0),
        )
        self.assertEqual(
            result3["team_total_scores"],
            {
                str(teams["Mechanised Yappers"].id): 255.5,
                str(teams["Rhetoric Rebels"].id): 255.0,
            },
        )
        self.assertEqual(
            result4["team_total_scores"],
            {
                str(teams["Fifth Amendment"].id): 254.5,
                str(teams["Motion Granted"].id): 254.0,
            },
        )
        expected_day_two = {
            (team, speaker, role): score
            for result in OFFICIAL_RESULTS_2026[2:4]
            for team, speaker, role, score in (entry[:4] for entry in result["performances"])
        }
        actual_day_two = {}
        for debate in debates.values():
            for performance, speaker, team in self.db.query(
                SpeakerPerformance, Speaker, Team
            ).join(
                Speaker,
                Speaker.id == SpeakerPerformance.speaker_id,
            ).join(
                Team,
                Team.id == Speaker.team_id,
            ).filter(
                SpeakerPerformance.debate_id == debate.id
            ).all():
                actual_day_two[(team.name, speaker.name, performance.role)] = performance.score
        self.assertEqual(actual_day_two, expected_day_two)

    def test_day_three_results_scores_replies_swing_and_idempotency(self):
        debates = {
            number: debate
            for debate, number in self.db.query(Debate, Round.number).join(Round).filter(
                Round.number.in_([5, 6])
            ).all()
        }
        teams = {team.name: team for team in self.db.query(Team).all()}

        self.assertEqual(
            self.db.get(Team, debates[5].winner_team_id).name,
            "Mechanised Yappers",
        )
        self.assertEqual(
            self.db.get(Team, debates[6].winner_team_id).name,
            "Fifth Amendment",
        )

        expected = Counter({
            (5, "Mechanised Yappers", "Bhavya Issarani", "Prime Minister", 73.5, False): 1,
            (5, "Mechanised Yappers", "Ketan Kumar", "Deputy Prime Minister", 72.5, False): 1,
            (5, "Mechanised Yappers", "Lakshit Chaudhary", "Government Whip", 74.5, False): 1,
            (5, "Broken Orators", "Akshat Agrawal", "Leader of Opposition", 73.0, False): 1,
            (5, "Broken Orators", "Dhruv", "Deputy Leader of Opposition", 72.5, False): 1,
            (5, "Broken Orators", "Mohit Sharma", "Opposition Whip", 74.0, False): 1,
            (6, "Fifth Amendment", "Ankit", "Prime Minister", 73.0, False): 1,
            (6, "Fifth Amendment", "Mohit Verma", "Deputy Prime Minister", 73.5, False): 1,
            (6, "Fifth Amendment", "Mohit Verma", "Government Whip", 72.0, True): 1,
            (6, "Akali Dinosaurs", "Beerdavinder", "Leader of Opposition", 72.0, False): 1,
            (6, "Akali Dinosaurs", "Harasees", "Deputy Leader of Opposition", 72.0, False): 1,
            (6, "Akali Dinosaurs", "Guransh", "Opposition Whip", 72.5, False): 1,
        })
        actual = Counter()
        for fixture_number, debate in debates.items():
            rows = self.db.query(SpeakerPerformance, Speaker, Team).join(
                Speaker,
                Speaker.id == SpeakerPerformance.speaker_id,
            ).join(
                Team,
                Team.id == Speaker.team_id,
            ).filter(
                SpeakerPerformance.debate_id == debate.id
            ).all()
            self.assertEqual(len(rows), 6)
            for performance, speaker, team in rows:
                actual[(
                    fixture_number,
                    team.name,
                    speaker.name,
                    performance.role,
                    performance.score,
                    performance.is_swing,
                )] += 1
        self.assertEqual(actual, expected)

        mohit = self.db.query(Speaker).join(Team).filter(
            Team.name == "Fifth Amendment",
            Speaker.name == "Mohit Verma",
        ).one()
        self.assertEqual(
            self.db.query(Speaker).filter(Speaker.name.in_(["Swing", "Mohit Verma (Swing)"])).count(),
            0,
        )
        mohit_day_three = self.db.query(SpeakerPerformance).filter(
            SpeakerPerformance.debate_id == debates[6].id,
            SpeakerPerformance.speaker_id == mohit.id,
        ).all()
        self.assertEqual(len(mohit_day_three), 2)
        self.assertEqual(
            {(row.score, row.is_swing) for row in mohit_day_three},
            {(73.5, False), (72.0, True)},
        )

        self.assertEqual(
            debate_team_averages(self.db, debates[5]),
            {
                teams["Mechanised Yappers"].id: 73.5,
                teams["Broken Orators"].id: 73.17,
            },
        )
        self.assertEqual(
            debate_team_averages(self.db, debates[6]),
            {
                teams["Fifth Amendment"].id: 72.83,
                teams["Akali Dinosaurs"].id: 72.17,
            },
        )

        result5 = get_debate_result(debates[5].id, db=self.db)
        result6 = get_debate_result(debates[6].id, db=self.db)
        self.assertEqual(
            (result5["government_reply_score"], result5["opposition_reply_score"]),
            (36.0, 36.0),
        )
        self.assertEqual(
            (result6["government_reply_score"], result6["opposition_reply_score"]),
            (36.0, 37.0),
        )
        self.assertEqual(
            result5["team_total_scores"],
            {
                str(teams["Mechanised Yappers"].id): 256.5,
                str(teams["Broken Orators"].id): 255.5,
            },
        )
        self.assertEqual(
            result6["team_total_scores"],
            {
                str(teams["Fifth Amendment"].id): 254.5,
                str(teams["Akali Dinosaurs"].id): 253.5,
            },
        )
        self.assertEqual(
            sum(
                performance["score"]
                for performance in result6["performances"]
                if performance["is_swing"]
            ),
            72.0,
        )

        rankings = {row["speaker_name"]: row for row in speaker_rankings(db=self.db)}
        self.assertEqual(rankings["Mohit Verma"]["total_score"], 145.5)
        self.assertEqual(rankings["Mohit Verma"]["debates"], 2)
        self.assertEqual(rankings["Mohit Verma"]["average_score"], 72.75)

        day_three_ids = {
            performance.id
            for performance in self.db.query(SpeakerPerformance).filter(
                SpeakerPerformance.debate_id.in_([debates[5].id, debates[6].id])
            )
        }
        speaker_count = self.db.query(Speaker).count()
        sync_official_2026_tournament(self.db)
        sync_official_2026_tournament(self.db)
        self.assertEqual(
            {
                performance.id
                for performance in self.db.query(SpeakerPerformance).filter(
                    SpeakerPerformance.debate_id.in_([debates[5].id, debates[6].id])
                )
            },
            day_three_ids,
        )
        self.assertEqual(self.db.query(Speaker).count(), speaker_count)

    def test_day_four_results_roster_and_idempotency(self):
        debates = {
            number: debate
            for debate, number in self.db.query(Debate, Round.number).join(Round).filter(
                Round.number.in_([7, 8, 9])
            ).all()
        }
        teams = {team.name: team for team in self.db.query(Team).all()}
        expected = Counter({
            (7, "Rhetoric Rebels", "Naman", "Prime Minister", 73.0): 1,
            (7, "Rhetoric Rebels", "Priyanshi", "Deputy Prime Minister", 74.5): 1,
            (7, "Rhetoric Rebels", "Ashmita", "Government Whip", 73.5): 1,
            (7, "Goodfellas", "Vallari", "Leader of Opposition", 72.5): 1,
            (7, "Goodfellas", "Rahul Batra", "Deputy Leader of Opposition", 74.5): 1,
            (7, "Goodfellas", "Manroop Singh", "Opposition Whip", 73.0): 1,
            (8, "Motion Granted", "Sanjeevan", "Prime Minister", 71.5): 1,
            (8, "Motion Granted", "Keshav", "Deputy Prime Minister", 71.0): 1,
            (8, "Motion Granted", "Agamjot", "Government Whip", 72.0): 1,
            (8, "Akali Dinosaurs", "Sahil", "Leader of Opposition", 72.0): 1,
            (8, "Akali Dinosaurs", "Vikramjit", "Deputy Leader of Opposition", 72.5): 1,
            (8, "Akali Dinosaurs", "Guransh", "Opposition Whip", 73.5): 1,
            (9, "Fifth Amendment", "Rahul", "Prime Minister", 73.0): 1,
            (9, "Fifth Amendment", "Satyam", "Deputy Prime Minister", 73.5): 1,
            (9, "Fifth Amendment", "Hridya", "Government Whip", 72.5): 1,
            (9, "Damsel Inflicting Stress", "Soumya", "Leader of Opposition", 72.0): 1,
            (9, "Damsel Inflicting Stress", "Saksham", "Deputy Leader of Opposition", 74.5): 1,
            (9, "Damsel Inflicting Stress", "Prabhleen", "Opposition Whip", 74.5): 1,
        })
        actual = Counter()
        for fixture_number, debate in debates.items():
            for performance, speaker, team in self.db.query(
                SpeakerPerformance, Speaker, Team
            ).join(
                Speaker, Speaker.id == SpeakerPerformance.speaker_id
            ).join(
                Team, Team.id == Speaker.team_id
            ).filter(SpeakerPerformance.debate_id == debate.id):
                self.assertFalse(performance.is_swing)
                actual[(
                    fixture_number,
                    team.name,
                    speaker.name,
                    performance.role,
                    performance.score,
                )] += 1
        self.assertEqual(actual, expected)

        expected_results = {
            7: ("Rhetoric Rebels", "Rhetoric Rebels", "Goodfellas", 37.0, 36.0,
                {"Rhetoric Rebels": 258.0, "Goodfellas": 256.0}),
            8: ("Akali Dinosaurs", "Motion Granted", "Akali Dinosaurs", 35.0, 35.0,
                {"Motion Granted": 249.5, "Akali Dinosaurs": 253.0}),
            9: ("Damsel Inflicting Stress", "Fifth Amendment", "Damsel Inflicting Stress", 38.0, 37.0,
                {"Fifth Amendment": 257.0, "Damsel Inflicting Stress": 258.0}),
        }
        for fixture_number, expected_result in expected_results.items():
            winner, government, opposition, government_reply, opposition_reply, totals = expected_result
            payload = get_debate_result(debates[fixture_number].id, db=self.db)
            self.assertEqual(self.db.get(Team, payload["winner_team_id"]).name, winner)
            self.assertEqual(self.db.get(Team, payload["government_team_id"]).name, government)
            self.assertEqual(self.db.get(Team, payload["opposition_team_id"]).name, opposition)
            self.assertEqual(payload["government_reply_score"], government_reply)
            self.assertEqual(payload["opposition_reply_score"], opposition_reply)
            self.assertEqual(
                {teams[name].id: score for name, score in totals.items()},
                {int(team_id): score for team_id, score in payload["team_total_scores"].items()},
            )

        motion_granted = teams["Motion Granted"]
        sanjeevan = self.db.query(Speaker).filter(
            Speaker.team_id == motion_granted.id,
            Speaker.name == "Sanjeevan",
        ).one()
        self.assertTrue(sanjeevan.active)
        self.assertEqual(self.db.query(Speaker).filter(
            Speaker.team_id == motion_granted.id,
            Speaker.name == "Simran",
            Speaker.active.is_(True),
        ).count(), 0)
        auction_roster = self.db.query(AuctionTeam).filter(
            AuctionTeam.team_name == "Motion Granted"
        ).one()
        self.assertIn("Sanjeevan", {player.player_name for player in auction_roster.players})
        self.assertNotIn("Simran", {player.player_name for player in auction_roster.players})
        rankings = {row["speaker_name"]: row for row in speaker_rankings(db=self.db)}
        self.assertEqual(
            (rankings["Sanjeevan"]["average_score"], rankings["Sanjeevan"]["debates"]),
            (71.5, 1),
        )

        future_debates = self.db.query(Debate).join(Round).filter(
            Round.number == 12
        ).all()
        self.assertTrue(all(debate.winner_team_id is None for debate in future_debates))
        self.assertEqual(self.db.query(SpeakerPerformance).filter(
            SpeakerPerformance.debate_id.in_([debate.id for debate in future_debates])
        ).count(), 0)
        self.assertEqual(self.db.query(Debate).filter(Debate.stage == "pool").count(), 12)
        self.assertEqual(self.db.query(Team).filter(
            Team.name == "Damsel Inflicting Stress"
        ).count(), 1)

        day_four_ids = {
            performance.id
            for performance in self.db.query(SpeakerPerformance).filter(
                SpeakerPerformance.debate_id.in_([debate.id for debate in debates.values()])
            )
        }
        sync_official_2026_tournament(self.db)
        sync_official_2026_tournament(self.db)
        self.assertEqual(day_four_ids, {
            performance.id
            for performance in self.db.query(SpeakerPerformance).filter(
                SpeakerPerformance.debate_id.in_([debate.id for debate in debates.values()])
            )
        })

    def test_day_five_results_and_reschedule_are_idempotent(self):
        teams = {team.name: team for team in self.db.query(Team).all()}
        debates = {
            number: debate
            for debate, number in self.db.query(Debate, Round.number).join(Round).filter(
                Round.number.in_([10, 11, 12])
            ).all()
        }
        debate_ids = {number: debate.id for number, debate in debates.items()}

        expected_results = {
            10: (
                "Goodfellas",
                "Goodfellas",
                "Mechanised Yappers",
                37.0,
                36.0,
                {"Goodfellas": 257.0, "Mechanised Yappers": 254.5},
            ),
            11: (
                "Motion Granted",
                "Damsel Inflicting Stress",
                "Motion Granted",
                37.0,
                37.0,
                {"Damsel Inflicting Stress": 255.0, "Motion Granted": 257.0},
            ),
        }
        for fixture_number, expected_result in expected_results.items():
            winner, government, opposition, government_reply, opposition_reply, totals = expected_result
            debate = debates[fixture_number]
            payload = get_debate_result(debate.id, db=self.db)
            self.assertEqual(self.db.get(Team, payload["winner_team_id"]).name, winner)
            self.assertEqual(self.db.get(Team, payload["government_team_id"]).name, government)
            self.assertEqual(self.db.get(Team, payload["opposition_team_id"]).name, opposition)
            self.assertEqual(payload["government_reply_score"], government_reply)
            self.assertEqual(payload["opposition_reply_score"], opposition_reply)
            self.assertEqual(len(payload["performances"]), 6)
            self.assertEqual(
                {teams[name].id: score for name, score in totals.items()},
                {int(team_id): score for team_id, score in payload["team_total_scores"].items()},
            )

        self.assertEqual(
            debate_team_averages(self.db, debates[10]),
            {
                teams["Goodfellas"].id: 73.33,
                teams["Mechanised Yappers"].id: 72.83,
            },
        )
        self.assertEqual(
            debate_team_averages(self.db, debates[11]),
            {
                teams["Damsel Inflicting Stress"].id: 72.67,
                teams["Motion Granted"].id: 73.33,
            },
        )

        rankings = {row["speaker_name"]: row for row in speaker_rankings(db=self.db)}
        self.assertEqual(
            (rankings["Vallari"]["total_score"], rankings["Vallari"]["debates"]),
            (146.0, 2),
        )
        self.assertEqual(
            (rankings["Shayan"]["total_score"], rankings["Shayan"]["debates"]),
            (73.0, 1),
        )

        postponed = debates[12]
        self.assertIsNone(postponed.winner_team_id)
        self.assertEqual(
            {self.db.get(Team, postponed.team1_id).name, self.db.get(Team, postponed.team2_id).name},
            {"Broken Orators", "Rhetoric Rebels"},
        )
        self.assertEqual(
            self.db.query(SpeakerPerformance).filter(
                SpeakerPerformance.debate_id == postponed.id
            ).count(),
            0,
        )

        fixture12 = fixture_details("Rhetoric Rebels", "Broken Orators")
        self.assertEqual(fixture12["number"], 12)
        self.assertEqual(fixture12["date"].isoformat(), "2026-08-22")
        self.assertEqual(fixture12["day"], "Saturday")
        self.assertEqual(fixture12["time_label"], "9:00 AM")
        self.assertEqual(fixture12["time_sort"], "09:00")

        schedule = {item["debate_number"]: item for item in schedule_api(db=self.db)}
        self.assertEqual(schedule[10]["status"], "Completed")
        self.assertEqual(schedule[11]["status"], "Completed")
        self.assertEqual(schedule[12]["status"], "Pending")

        performance_ids = {
            performance.id
            for performance in self.db.query(SpeakerPerformance).filter(
                SpeakerPerformance.debate_id.in_([debates[10].id, debates[11].id])
            )
        }
        sync_official_2026_tournament(self.db)
        sync_official_2026_tournament(self.db)
        self.assertEqual(
            {
                number: debate.id
                for debate, number in self.db.query(Debate, Round.number).join(Round).filter(
                    Round.number.in_([10, 11, 12])
                ).all()
            },
            debate_ids,
        )
        self.assertEqual(
            {
                performance.id
                for performance in self.db.query(SpeakerPerformance).filter(
                    SpeakerPerformance.debate_id.in_([debates[10].id, debates[11].id])
                )
            },
            performance_ids,
        )

    def test_semifinal_placeholders_and_finalized_pool_sync(self):
        teams = {team.name: team for team in self.db.query(Team).all()}
        self.assertEqual(
            self.db.query(Debate).filter(Debate.stage == "semifinal").count(),
            0,
        )

        bracket = official_2026_semifinal_bracket(self.db)
        self.assertEqual([item["label"] for item in bracket], ["Semifinal 1", "Semifinal 2"])
        self.assertIsNone(bracket[0]["team1"])
        self.assertEqual(bracket[0]["team1_placeholder"], "Pool A #1 (TBD)")
        self.assertEqual(bracket[0]["team2"].name, "Fifth Amendment")
        self.assertEqual(bracket[1]["team1"].name, "Damsel Inflicting Stress")
        self.assertIsNone(bracket[1]["team2"])
        self.assertEqual(bracket[1]["team2_placeholder"], "Pool A #2 (TBD)")
        self.assertEqual({item["status"] for item in bracket}, {"Pending"})
        self.assertEqual({item["date"] for item in bracket}, {"2026-08-22"})
        self.assertEqual({item["time"] for item in bracket}, {"10:00 AM onwards"})

        request = Request({
            "type": "http",
            "method": "GET",
            "path": "/schedule",
            "raw_path": b"/schedule",
            "query_string": b"",
            "headers": [],
            "client": ("test", 50000),
            "server": ("test", 80),
            "scheme": "http",
            "root_path": "",
        })
        schedule_html = schedule_page(request, db=self.db).body.decode()
        self.assertIn("Semifinal 1", schedule_html)
        self.assertIn("Semifinal 2", schedule_html)
        self.assertIn("Pool A #1 (TBD)", schedule_html)
        self.assertIn("Pool A #2 (TBD)", schedule_html)
        self.assertIn("Fifth Amendment", schedule_html)
        self.assertIn("Damsel Inflicting Stress", schedule_html)
        self.assertIn("10:00 AM onwards", schedule_html)

        debate12 = self.db.query(Debate).join(Round).filter(Round.number == 12).one()
        broken = teams["Broken Orators"]
        rhetoric = teams["Rhetoric Rebels"]
        debate12.winner_team_id = broken.id
        roles = ("Prime Minister", "Deputy Prime Minister", "Government Whip")
        for team, score in ((broken, 75.0), (rhetoric, 70.0)):
            speakers = self.db.query(Speaker).filter(
                Speaker.team_id == team.id
            ).order_by(Speaker.id).limit(3).all()
            for speaker, role in zip(speakers, roles):
                self.db.add(SpeakerPerformance(
                    debate_id=debate12.id,
                    speaker_id=speaker.id,
                    role=role,
                    score=score,
                ))
        self.db.flush()

        pools = {pool.name: pool for pool in self.db.query(Pool).all()}
        standings_a = calculate_pool_standings(self.db, pools["Pool A"].id)
        before_semifinals = {
            row["team_name"]: (row["played"], row["wins"], row["losses"], row["average_team_score"])
            for row in standings_a
        }
        first_sync = sync_official_2026_semifinals(self.db)
        self.db.flush()
        first_ids = [debate.id for debate in first_sync]
        second_sync = sync_official_2026_semifinals(self.db)
        self.db.flush()

        self.assertEqual(len(first_sync), 2)
        self.assertEqual([debate.id for debate in second_sync], first_ids)
        self.assertEqual(
            self.db.query(Debate).filter(Debate.stage == "semifinal").count(),
            2,
        )
        self.assertEqual(
            (teams["Fifth Amendment"].id, teams["Damsel Inflicting Stress"].id),
            (first_sync[0].team2_id, first_sync[1].team1_id),
        )
        self.assertEqual(first_sync[0].team1_id, standings_a[0]["team_id"])
        self.assertEqual(first_sync[1].team2_id, standings_a[1]["team_id"])
        self.assertTrue(all(debate.winner_team_id is None for debate in first_sync))

        api_semifinals = [item for item in schedule_api(db=self.db) if item["stage"] == "semifinal"]
        self.assertEqual([item["stage_name"] for item in api_semifinals], ["Semifinal 1", "Semifinal 2"])
        self.assertEqual({item["date"] for item in api_semifinals}, {"2026-08-22"})
        self.assertEqual({item["time"] for item in api_semifinals}, {"10:00 AM onwards"})
        self.assertEqual({item["status"] for item in api_semifinals}, {"Pending"})

        first_sync[0].winner_team_id = first_sync[0].team1_id
        self.db.flush()
        sync_official_2026_semifinals(self.db)
        self.assertEqual(first_sync[0].winner_team_id, first_sync[0].team1_id)
        after_semifinals = {
            row["team_name"]: (row["played"], row["wins"], row["losses"], row["average_team_score"])
            for row in calculate_pool_standings(self.db, pools["Pool A"].id)
        }
        self.assertEqual(after_semifinals, before_semifinals)

    def test_completed_result_ui_classes_are_data_driven(self):
        def request_for(path):
            return Request({
                "type": "http",
                "method": "GET",
                "path": path,
                "raw_path": path.encode(),
                "query_string": b"",
                "headers": [],
                "client": ("test", 50000),
                "server": ("test", 80),
                "scheme": "http",
                "root_path": "",
            })

        schedule_html = schedule_page(
            request_for("/schedule"),
            db=self.db,
        ).body.decode()
        self.assertEqual(schedule_html.count("matchup-team-winner"), 11)
        self.assertEqual(schedule_html.count("matchup-team-loser"), 11)
        self.assertEqual(schedule_html.count(">Winner</span>"), 11)
        self.assertEqual(schedule_html.count(">Lost</span>"), 11)
        self.assertEqual(schedule_html.count('class="reply-score"'), 22)
        self.assertIn("Total debate points", schedule_html)
        self.assertIn('class="swing-label">Swing</span>', schedule_html)
        self.assertIn("Mohit Verma", schedule_html)

        pending_start = schedule_html.index("Debate 12")
        pending_end = schedule_html.index("</article>", pending_start)
        pending_card = schedule_html[pending_start:pending_end]
        self.assertNotIn("matchup-team-winner", pending_card)
        self.assertNotIn("matchup-team-loser", pending_card)
        self.assertNotIn("matchup-outcome-badge", pending_card)

        teams = {team.name: team for team in self.db.query(Team).all()}
        damsel_html = team_detail_page(
            teams["Damsel Inflicting Stress"].id,
            request_for(f"/teams/{teams['Damsel Inflicting Stress'].id}"),
            db=self.db,
        ).body.decode()
        akali_html = team_detail_page(
            teams["Akali Dinosaurs"].id,
            request_for(f"/teams/{teams['Akali Dinosaurs'].id}"),
            db=self.db,
        ).body.decode()
        self.assertIn("fixture-row result-won", damsel_html)
        self.assertIn("fixture-row result-lost", akali_html)
        self.assertNotIn("fixture-row result-pending", damsel_html)
        self.assertNotIn("fixture-row result-pending", akali_html)

        standings_html = standings_page(
            request_for("/standings"),
            db=self.db,
        ).body.decode()
        self.assertIn('class="standings-wins"', standings_html)
        self.assertIn('class="standings-losses"', standings_html)
        self.assertEqual(
            standings_html.count("qualification-status qualification-status-q"),
            4,
        )
        self.assertEqual(
            standings_html.count("qualification-status qualification-status-e"),
            4,
        )
        self.assertEqual(
            standings_html.count("qualification-status qualification-status-pending"),
            3,
        )
        self.assertEqual(standings_html.count('data-label="Qualification"'), 8)
        self.assertIn("Qualified for Semifinals", standings_html)
        self.assertIn("Still undecided", standings_html)

    def test_mobile_table_markup_keeps_priority_labels(self):
        def request_for(path):
            return Request({
                "type": "http",
                "method": "GET",
                "path": path,
                "raw_path": path.encode(),
                "query_string": b"",
                "headers": [],
                "client": ("test", 50000),
                "server": ("test", 80),
                "scheme": "http",
                "root_path": "",
            })

        rankings_html = rankings_page(
            request_for("/speaker-rankings"),
            db=self.db,
        ).body.decode()
        self.assertIn('class="speaker-rankings-table"', rankings_html)
        self.assertIn('data-label="Speaker"', rankings_html)
        self.assertIn('data-label="Team"', rankings_html)
        self.assertIn('data-label="Speeches"', rankings_html)
        self.assertIn('data-label="Average"', rankings_html)

        speaker = self.db.query(Speaker).join(Team).filter(
            Team.name == "Damsel Inflicting Stress",
            Speaker.name == "Rachel",
        ).one()
        speaker_html = speaker_detail_page(
            speaker.id,
            request_for(f"/speakers/{speaker.id}"),
            db=self.db,
        ).body.decode()
        self.assertIn('class="speaker-history-table"', speaker_html)
        for label in ("Stage", "Round", "Opponent", "Side", "Result", "Role", "Score"):
            self.assertIn(f'data-label="{label}"', speaker_html)

        standings_html = standings_page(
            request_for("/standings"),
            db=self.db,
        ).body.decode()
        self.assertIn('data-label="Avg team score"', standings_html)

    def test_day_five_standings_and_speaker_rankings_are_derived(self):
        pools = {pool.name: pool for pool in self.db.query(Pool).all()}
        pool_a = {
            row["team_name"]: row
            for row in calculate_pool_standings(self.db, pools["Pool A"].id)
        }
        pool_b = {
            row["team_name"]: row
            for row in calculate_pool_standings(self.db, pools["Pool B"].id)
        }

        expected_records = {
            "Mechanised Yappers": (3, 2, 1),
            "Broken Orators": (2, 1, 1),
            "Goodfellas": (3, 1, 2),
            "Rhetoric Rebels": (2, 1, 1),
            "Fifth Amendment": (3, 2, 1),
            "Damsel Inflicting Stress": (3, 2, 1),
            "Akali Dinosaurs": (3, 1, 2),
            "Motion Granted": (3, 1, 2),
        }
        for team_name, expected in expected_records.items():
            pool_table = pool_a if team_name in pool_a else pool_b
            row = pool_table[team_name]
            self.assertEqual(
                (row["played"], row["wins"], row["losses"]),
                expected,
            )

        expected_qualification = {
            "Mechanised Yappers": "Q",
            "Broken Orators": "—",
            "Rhetoric Rebels": "—",
            "Goodfellas": "E",
            "Damsel Inflicting Stress": "Q",
            "Fifth Amendment": "Q",
            "Akali Dinosaurs": "E",
            "Motion Granted": "E",
        }
        for team_name, expected in expected_qualification.items():
            pool_table = pool_a if team_name in pool_a else pool_b
            self.assertEqual(pool_table[team_name]["qualification_status"], expected)

        self.assertEqual(pool_a["Mechanised Yappers"]["average_team_score"], 73.06)
        self.assertEqual(pool_a["Broken Orators"]["average_team_score"], 73.08)
        self.assertEqual(pool_b["Fifth Amendment"]["average_team_score"], 72.78)
        self.assertEqual(pool_b["Akali Dinosaurs"]["average_team_score"], 72.5)

        overall = {row["team_name"]: row for row in standings(db=self.db)}
        self.assertEqual(len(overall), 8)
        rankings = {
            row["speaker_name"]: row
            for row in speaker_rankings(db=self.db)
        }
        self.assertEqual(len(rankings), 37)
        self.assertEqual(rankings["Prabhleen"]["average_score"], 74.5)
        self.assertEqual(rankings["Mudit"]["average_score"], 73.5)
        self.assertEqual(rankings["Rahul Batra"]["average_score"], 73.33)
        expected_day_five_rankings = {
            "Bhavya Issarani": (72.75, 2),
            "Ketan Kumar": (72.5, 2),
            "Lakshit Chaudhary": (74.0, 3),
            "Akshat Agrawal": (73.0, 2),
            "Dhruv": (72.25, 2),
            "Mohit Sharma": (74.0, 2),
            "Ankit": (73.0, 1),
            "Mohit Verma": (72.75, 2),
            "Beerdavinder": (72.0, 1),
            "Harasees": (72.5, 2),
            "Guransh": (73.33, 3),
            "Sanjeevan": (71.5, 1),
            "Vikramjit": (72.5, 1),
            "Saksham": (73.25, 2),
            "Soumya": (72.0, 1),
        }
        for speaker_name, (average, debates) in expected_day_five_rankings.items():
            self.assertEqual(rankings[speaker_name]["average_score"], average)
            self.assertEqual(rankings[speaker_name]["debates"], debates)

        for debate in self.db.query(Debate).filter(Debate.stage == "pool"):
            debate.winner_team_id = None
        early_pool_a = calculate_pool_standings(self.db, pools["Pool A"].id)
        early_pool_b = calculate_pool_standings(self.db, pools["Pool B"].id)
        self.assertEqual(
            {row["qualification_status"] for row in early_pool_a + early_pool_b},
            {"—"},
        )

    def test_team_rename_preserves_record_and_all_references(self):
        team = self.db.query(Team).filter(
            Team.name == "Damsel Inflicting Stress"
        ).one()
        auction_team = self.db.query(AuctionTeam).filter(
            AuctionTeam.team_name == "Damsel Inflicting Stress"
        ).one()
        team_id = team.id
        auction_team_id = auction_team.id
        speaker_ids = {
            speaker.id
            for speaker in self.db.query(Speaker).filter(Speaker.team_id == team.id)
        }
        debate_ids = {
            debate.id
            for debate in self.db.query(Debate).filter(
                (Debate.team1_id == team.id) | (Debate.team2_id == team.id)
            )
        }
        team.name = "Damsel Inflicting Distress"
        auction_team.team_name = "Damsel Inflicting Distress"
        self.db.commit()

        sync_official_2026_tournament(self.db)
        sync_official_2026_tournament(self.db)

        self.assertEqual(
            self.db.query(Team).filter(Team.name == "Damsel Inflicting Distress").count(),
            0,
        )
        renamed = self.db.query(Team).filter(
            Team.name == "Damsel Inflicting Stress"
        ).one()
        self.assertEqual(renamed.id, team_id)
        self.assertEqual(
            {speaker.id for speaker in self.db.query(Speaker).filter(Speaker.team_id == renamed.id)},
            speaker_ids,
        )
        self.assertEqual(
            {
                debate.id
                for debate in self.db.query(Debate).filter(
                    (Debate.team1_id == renamed.id) | (Debate.team2_id == renamed.id)
                )
            },
            debate_ids,
        )
        renamed_auction = self.db.query(AuctionTeam).filter(
            AuctionTeam.team_name == "Damsel Inflicting Stress"
        ).one()
        self.assertEqual(renamed_auction.id, auction_team_id)

    def test_old_and_new_duplicate_teams_merge_into_historical_record(self):
        historical = self.db.query(Team).filter(
            Team.name == "Damsel Inflicting Stress"
        ).one()
        historical_id = historical.id
        historical_speaker_ids = {
            speaker.id
            for speaker in self.db.query(Speaker).filter(
                Speaker.team_id == historical.id
            )
        }
        day_one = self.db.query(Debate).join(Round).filter(Round.number == 1).one()
        self.assertEqual(day_one.winner_team_id, historical.id)

        historical.name = "Damsel Inflicting Distress"
        duplicate = Team(name="Damsel Inflicting Stress", pool_id=historical.pool_id)
        self.db.add(duplicate)
        self.db.flush()
        duplicate_id = duplicate.id
        migrated_speaker = Speaker(name="Duplicate-era Member", team_id=duplicate.id)
        self.db.add(migrated_speaker)
        self.db.flush()

        future_round = Round(number=99, motion="Future motion")
        self.db.add(future_round)
        self.db.flush()
        future = Debate(
            round_id=future_round.id,
            team1_id=duplicate.id,
            team2_id=self.db.query(Team).filter(Team.name == "Motion Granted").one().id,
            stage="semifinal",
        )
        self.db.add(future)
        self.db.flush()
        migrated_performance = SpeakerPerformance(
            debate_id=future.id,
            speaker_id=migrated_speaker.id,
            role="Prime Minister",
            score=76.0,
        )
        self.db.add(migrated_performance)

        auction_team = self.db.query(AuctionTeam).filter(
            AuctionTeam.team_name == "Damsel Inflicting Stress"
        ).one()
        auction_team.team_name = "Damsel Inflicting Distress"
        self.db.add(AuctionTeam(
            auction_id=auction_team.auction_id,
            team_name="Damsel Inflicting Stress",
            leader_name="Duplicate",
            accent_color="#000000",
        ))
        self.db.commit()
        migrated_speaker_id = migrated_speaker.id
        migrated_performance_id = migrated_performance.id

        sync_official_2026_tournament(self.db)
        sync_official_2026_tournament(self.db)

        self.assertEqual(
            self.db.query(Team).filter(Team.name == "Damsel Inflicting Distress").count(),
            0,
        )
        canonical = self.db.query(Team).filter(
            Team.name == "Damsel Inflicting Stress"
        ).one()
        self.assertEqual(canonical.id, historical_id)
        self.assertIsNone(self.db.get(Team, duplicate_id))
        self.assertEqual(self.db.get(Speaker, migrated_speaker_id).team_id, canonical.id)
        self.assertTrue(
            historical_speaker_ids.issubset({
                speaker.id
                for speaker in self.db.query(Speaker).filter(
                    Speaker.team_id == canonical.id
                )
            })
        )
        self.assertEqual(
            self.db.get(SpeakerPerformance, migrated_performance_id).speaker_id,
            migrated_speaker_id,
        )
        self.assertEqual(day_one.winner_team_id, canonical.id)
        self.assertEqual(
            debate_team_averages(self.db, day_one)[canonical.id],
            73.67,
        )

        pool_b = self.db.query(Pool).filter(Pool.name == "Pool B").one()
        pool_b_teams = self.db.query(Team).filter(Team.pool_id == pool_b.id).all()
        self.assertEqual(
            {team.name for team in pool_b_teams},
            {
                "Damsel Inflicting Stress",
                "Fifth Amendment",
                "Akali Dinosaurs",
                "Motion Granted",
            },
        )
        self.assertEqual(len(pool_b_teams), 4)
        standings_by_team = {
            row["team_name"]: row
            for row in calculate_pool_standings(self.db, pool_b.id)
        }
        self.assertEqual(
            (
                standings_by_team["Damsel Inflicting Stress"]["played"],
                standings_by_team["Damsel Inflicting Stress"]["wins"],
                standings_by_team["Damsel Inflicting Stress"]["losses"],
                standings_by_team["Damsel Inflicting Stress"]["average_team_score"],
            ),
            (3, 2, 1, 73.33),
        )
        self.assertEqual(
            self.db.query(AuctionTeam).filter(
                AuctionTeam.team_name == "Damsel Inflicting Stress"
            ).count(),
            1,
        )

    def test_restart_repairs_official_duplicates_and_preserves_future_results(self):
        debate_ids = {
            number: debate.id
            for debate, number in self.db.query(Debate, Round.number).join(Round).all()
        }
        official_performance_ids = {
            performance.id
            for performance in self.db.query(SpeakerPerformance).filter(
                SpeakerPerformance.debate_id.in_(
                    [debate_ids[number] for number in range(1, 12)]
                )
            )
        }
        debate1 = self.db.get(Debate, debate_ids[1])
        rachel = self.db.query(Speaker).join(Team).filter(
            Team.name == "Damsel Inflicting Stress",
            Speaker.name == "Rachel",
        ).one()
        unused_damsel = self.db.query(Speaker).join(Team).filter(
            Team.name == "Damsel Inflicting Stress",
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

        future = self.db.get(Debate, debate_ids[12])
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
                    SpeakerPerformance.debate_id.in_(
                        [debate_ids[number] for number in range(1, 12)]
                    )
                )
            },
            official_performance_ids,
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
                Team.name == "Damsel Inflicting Stress"
            ).one().id,
        )
        future = self.db.get(Debate, debate_ids[12])
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

    def test_sanjeevan_replacement_preserves_historical_simran_data(self):
        team = self.db.query(Team).filter(Team.name == "Motion Granted").one()
        sanjeevan = self.db.query(Speaker).filter(
            Speaker.team_id == team.id,
            Speaker.name == "Sanjeevan",
        ).one()
        sanjeevan.name = "Simran"
        auction_team = self.db.query(AuctionTeam).filter(
            AuctionTeam.team_name == "Motion Granted"
        ).one()
        auction_sanjeevan = next(
            player for player in auction_team.players if player.player_name == "Sanjeevan"
        )
        auction_sanjeevan.player_name = "Simran"
        future_round = Round(number=99, motion="Future motion")
        self.db.add(future_round)
        self.db.flush()
        future = Debate(
            round_id=future_round.id,
            team1_id=team.id,
            team2_id=self.db.query(Team).filter(Team.name == "Fifth Amendment").one().id,
            stage="semifinal",
        )
        self.db.add(future)
        self.db.flush()
        historical = SpeakerPerformance(
            debate_id=future.id,
            speaker_id=sanjeevan.id,
            role="Historical reserve appearance",
            score=70.0,
        )
        self.db.add(historical)
        self.db.commit()
        historical_id = historical.id
        simran_id = sanjeevan.id

        sync_official_2026_tournament(self.db)
        sync_official_2026_tournament(self.db)

        simran = self.db.get(Speaker, simran_id)
        self.assertEqual(simran.name, "Simran")
        self.assertFalse(simran.active)
        self.assertEqual(
            self.db.get(SpeakerPerformance, historical_id).speaker_id,
            simran.id,
        )
        current_sanjeevan = self.db.query(Speaker).filter(
            Speaker.team_id == team.id,
            Speaker.name == "Sanjeevan",
        ).one()
        self.assertTrue(current_sanjeevan.active)
        self.assertNotEqual(current_sanjeevan.id, simran.id)
        self.assertEqual(self.db.query(Speaker).filter(
            Speaker.team_id == team.id,
            Speaker.name == "Sanjeevan",
        ).count(), 1)
        self.assertEqual(
            {player.player_name for player in auction_team.players},
            {"Agamjot", "Keshav", "Shaurya", "Sanjeevan"},
        )

    def test_guransh_duplicate_merge_preserves_performances(self):
        team = self.db.query(Team).filter(Team.name == "Akali Dinosaurs").one()
        canonical = self.db.query(Speaker).filter(
            Speaker.team_id == team.id,
            Speaker.name == "Guransh",
        ).one()
        duplicate = Speaker(name="Gurnash", team_id=team.id)
        self.db.add(duplicate)
        self.db.flush()
        official_debate = self.db.query(Debate).join(Round).filter(
            Round.number == 6
        ).one()
        extra_round = Round(number=99, motion="Historical exhibition")
        self.db.add(extra_round)
        self.db.flush()
        extra_debate = Debate(
            round_id=extra_round.id,
            team1_id=team.id,
            team2_id=self.db.query(Team).filter(Team.id != team.id).first().id,
            stage="semifinal",
        )
        self.db.add(extra_debate)
        self.db.flush()
        self.db.add_all([
            SpeakerPerformance(
                debate_id=official_debate.id,
                speaker_id=canonical.id,
                role="Prime Minister",
                score=75,
            ),
            SpeakerPerformance(
                debate_id=extra_debate.id,
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
        self.assertEqual(len(performances), 4)
        self.assertEqual({performance.score for performance in performances}, {72.5, 73.5, 74, 77})


if __name__ == "__main__":
    unittest.main()
