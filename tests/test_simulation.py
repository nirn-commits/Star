"""シミュレーションの整合性テスト。

python -m unittest discover -s tests
"""

import unittest
from collections import Counter

from galaxy.worldgen import generate
from galaxy.sim import engine, careers
from galaxy.narrative import chronicle
from galaxy.minds import AIMind, PlayerMind, set_mind, mind_of
from galaxy.narrative import voice


def _run(seed, years, planets=60):
    world = generate(seed=seed, n_planets=planets)
    engine.run(world, years * 12)
    return world


class SimulationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.world = _run(seed=11, years=25)

    def test_world_is_alive(self):
        w = self.world
        self.assertGreater(len(w.alive_factions()), 1)
        self.assertGreater(len(w.alive_persons()), 100)
        self.assertGreater(len(w.log), 100)

    def test_planet_ownership_consistent(self):
        w = self.world
        for pl in w.planets:
            if pl.owner is not None:
                self.assertTrue(w.faction(pl.owner).alive, pl.name)
                self.assertIn(pl.id, w.faction(pl.owner).planets)
        for f in w.factions.values():
            for pid in f.planets:
                self.assertEqual(w.planet(pid).owner, f.id)
            if not f.alive:
                self.assertFalse(f.planets)

    def test_every_living_faction_has_a_living_leader(self):
        w = self.world
        for f in w.alive_factions():
            leader = w.person(f.leader)
            self.assertIsNotNone(leader, f.name)
            self.assertTrue(leader.alive, f.name)
            self.assertEqual(leader.job.track, "government")
            self.assertEqual(leader.job.rank, careers.top_rank("government"))

    def test_marriages_are_mutual(self):
        w = self.world
        for p in w.alive_persons():
            if p.spouse is not None:
                s = w.person(p.spouse)
                self.assertTrue(s.alive)
                self.assertEqual(s.spouse, p.id)

    def test_the_dead_hold_no_office(self):
        w = self.world
        for p in w.persons.values():
            if not p.alive:
                self.assertIsNone(p.job, p.name)
                self.assertIsNotNone(p.death_t)

    def test_rank_counts_match_reality(self):
        w = self.world
        actual = Counter()
        for p in w.alive_persons():
            if p.job:
                actual[(p.job.track, p.job.org_id, p.job.rank)] += 1
        for key, n in w.rank_count.items():
            self.assertEqual(n, actual.get(key, 0), key)

    def test_npcs_live_full_lives(self):
        w = self.world
        born = [p for p in w.persons.values() if p.birth_t >= 0]
        self.assertTrue(born, "シミュレーション中に誰も生まれていない")
        working = [p for p in born if p.job or p.career_history]
        self.assertTrue(working, "生まれた者が誰も就職していない")
        promoted = [p for p in w.alive_persons() if p.job and p.job.rank > 0 and p.job.since > 0]
        self.assertTrue(promoted)
        self.assertTrue(any(p.former_spouses for p in w.persons.values()))

    def test_reports_render(self):
        w = self.world
        self.assertIn("ヴェルカ銀河", chronicle.prologue(w))
        chronicle.overview(w)
        chronicle.famous(w)
        chronicle.tech_report(w)
        for f in list(w.factions.values())[:5]:
            self.assertIn(f.name, chronicle.faction_report(w, f.id))
        for p in list(w.persons.values())[:30]:
            self.assertIn(p.name, chronicle.biography(w, p.id))
        for pl in w.planets[:5]:
            chronicle.planet_report(w, pl.id)
        for wid in list(w.wars)[:5]:
            chronicle.war_report(w, wid)
        for y in range(w.year_of(0), w.year):
            chronicle.year_chronicle(w, y, 1)
        self.assertEqual(voice.MISSING, set(), "埋められていないプレースホルダがある")


class DeterminismTest(unittest.TestCase):
    def test_same_seed_same_history(self):
        a = _run(seed=5, years=5, planets=40)
        b = _run(seed=5, years=5, planets=40)
        self.assertEqual([e.text for e in a.log], [e.text for e in b.log])


class MindTest(unittest.TestCase):
    def test_player_mind_can_replace_ai(self):
        w = generate(seed=3, n_planets=30)
        p = w.alive_persons()[0]
        self.assertIsInstance(mind_of(w, p), AIMind)
        set_mind(p.id, PlayerMind())
        self.assertIsInstance(mind_of(w, p), PlayerMind)
        # プレイヤー用の心でも同じ人生の仕組みに乗れる
        engine.run(w, 24)


if __name__ == "__main__":
    unittest.main()
