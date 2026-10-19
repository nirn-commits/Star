"""シミュレーションの時間を進めるエンジン。1ステップ＝1か月。"""

from galaxy.sim import demography, careers, politics, diplomacy, warfare, economy, technology, incidents


def step(world):
    world.rebuild_caches()
    economy.monthly(world)
    technology.monthly(world)
    demography.monthly(world)
    careers.monthly(world)
    politics.monthly(world)
    diplomacy.monthly(world)
    warfare.monthly(world)
    incidents.monthly(world)
    world.t += 1


def run(world, months, on_year=None):
    for _ in range(months):
        step(world)
        if on_year and world.t % 12 == 0:
            on_year(world, world.year - 1)
