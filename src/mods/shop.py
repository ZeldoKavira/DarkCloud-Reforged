"""Shop price modifications. Ported from Shop.cs."""

import logging
from mods.base import ModBase

log = logging.getLogger(__name__)


class ShopMod(ModBase):
    name = "Shop Prices"

    def run(self):
        self.apply_once()

    def apply_once(self):
        mem = self.mem
        log.info("Applying shop price changes...")

        # Treasure Key (halved)
        mem.write_short(0x20291D10, 400)
        mem.write_short(0x20291D12, 200)

        # Anti-Curse Amulet
        mem.write_short(0x20291C50, 400)
        mem.write_short(0x20291C52, 200)

        # Anti-Goo Amulet
        mem.write_short(0x20291C54, 400)
        mem.write_short(0x20291C56, 200)

        # Reduce bait selling prices to 1/4
        bait_addrs = [
            0x20291D24, 0x20291D28, 0x20291D2C, 0x20291D30,
            0x20291D34, 0x20291D40, 0x20291D50, 0x20291D58,
        ]
        for base in bait_addrs:
            buy = mem.read_short(base)
            mem.write_short(base + 2, buy // 4)

        # Backfloor key prices
        keys = [
            (0x20291DBC, 600, 300),   # Tram Oil
            (0x20291DC0, 750, 375),   # Sundew
            (0x20291DC4, 300, 150),   # Flapping Fish
            (0x20291DCC, 900, 450),   # Secret Path Key
            (0x20291DD0, 1200, 600),  # Bravery Launch
            (0x20291DD4, 1500, 750),  # Flapping Duster
        ]
        for base, buy, sell in keys:
            mem.write_short(base, buy)
            mem.write_short(base + 2, sell)

        # Weapon prices (full table from C# mod)
        buy_prices = [
            2, 2, 500, 650, 2500, 900, 5000, 1800, 3000, 4500, 9000, 3000, 5500, 1250,
            12000, 7888, 3642, 9500, 12726, 18000, 2, 12000, 18000, 30000, 9021, 4500,
            1900, 2250, 11500, 2500, 5000, 6000, 8000, 1001, 2150, 9507, 5300, 10000,
            23331, 37035, 40011, 45000, 2, 2, 900, 4200, 1999, 750, 2800, 3100, 5525,
            9015, 18000, 2552, 6666, 14000, 33333, 2, 2, 1700, 7035, 6000, 2704, 3250,
            1701, 8000, 12000, 21816, 19998, 2, 2600, 2300, 33027, 2, 2, 2, 3800, 4300,
            2500, 8000, 5000, 9000, 8000, 16314, 24000, 2, 2007, 3500, 36000, 2, 2, 2,
            3400, 4000, 4700, 6000, 5000, 7000, 13500, 21036, 35823, 2, 5555, 6500, 2,
            2, 2, 2, 4000, 3200, 3300, 6000, 10450, 11943, 12018, 24000, 24000, 3000, 9000,
        ]
        sell_prices = [
            1, 1, 167, 217, 833, 300, 1667, 600, 1000, 1500, 3000, 1000, 1833, 417,
            4000, 2629, 1214, 3167, 4242, 6000, 1, 4000, 6000, 10000, 3007, 1500, 633,
            750, 3833, 833, 1667, 2000, 2667, 334, 717, 3169, 1767, 3333, 7777, 12345,
            13337, 15000, 1, 1, 300, 1400, 666, 250, 933, 1033, 1842, 3005, 6000, 851,
            2222, 4667, 11111, 1, 1, 567, 2345, 2000, 901, 1083, 567, 2667, 4000, 7272,
            6666, 1, 867, 767, 11009, 1, 1, 1, 1267, 1433, 833, 2667, 1667, 3000, 2667,
            5438, 8000, 1, 669, 1167, 12000, 1, 1, 1, 1133, 1333, 1567, 2000, 1667, 2333,
            4500, 7012, 11941, 1, 1852, 2167, 1, 1, 1, 1, 1333, 800, 825, 2000, 3483,
            3981, 4006, 8000, 8000, 1000, 3000,
        ]
        base_buy = 0x20291E40
        base_sell = 0x20291E42
        for i, (b, s) in enumerate(zip(buy_prices, sell_prices)):
            mem.write_short(base_buy + (i * 4), b)
            mem.write_short(base_sell + (i * 4), s)

        self._applied = True
        log.info("Shop prices applied (%d weapons repriced)", len(buy_prices))
