from .pyros import Pyros
from .glacius import Glacius, IceSpike, GlaciusLaserHazard, FrozenGround
from .granit import Granit
from .utils import BossProjectile, ShockWave, SlamWarning, LightningWarning
from .ventus import Ventus
from .mutant import Mutant
from .base import BossBase, BossRoom, RoomTile

BOSS_ROSTER = [Pyros, Glacius, Granit, Ventus, Mutant]

def make_boss_room(player, boss_index):
    cls = BOSS_ROSTER[boss_index % len(BOSS_ROSTER)]
    return BossRoom(player, cls)
