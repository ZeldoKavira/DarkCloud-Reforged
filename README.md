# Dark Cloud Reforged

A cross-platform rewrite of the [Dark Cloud Enhanced Mod](https://github.com/Gundorada-Workshop/DarkCloud-Enhanced), originally built in C# with direct Windows process memory access. This version uses **PINE IPC** to communicate with PCSX2, making it compatible with modern PCSX2 builds (v1.7+ and Nightly) on **Windows, Linux, and macOS** — including Steam Deck.

## Steam Deck — One-Line Install

Open a terminal (Desktop Mode → Konsole) and run:

```bash
curl -fsSL https://raw.githubusercontent.com/ZeldoKavira/DarkCloud-Enhanced-Python/main/scripts/steamdeck-setup.sh | bash
```

This will:
1. Download PCSX2 and the latest mod build
2. Prompt you to place your `Dark Cloud (USA).iso` in `~/.dark-cloud-enhanced/`
3. Install the required PNACH and game settings files
4. Prompt you to place your PS2 BIOS in `~/.config/PCSX2/bios/`
5. Launch the mod and PCSX2

The script auto-updates itself and the mod on every run.

### Adding to your Steam Library

After the first run, a shortcut is automatically created. To add it to your library:

1. In Desktop Mode, open Steam
2. Click **Add a Game** (bottom-left) → **Add a Non-Steam Game**
3. Check **Dark Cloud Enhanced** from the list
4. Click **Add Selected Programs**

It will now appear in your library and work in Gaming Mode.

## What changed from the original

The original mod required Windows and used `ReadProcessMemory`/`WriteProcessMemory` to manipulate the emulator's address space directly. This approach broke with newer PCSX2 versions and couldn't run on Linux or macOS.

This rewrite:

- **Uses PINE IPC** — PCSX2's built-in socket protocol for memory read/write, no OS-level process hacking
- **Supports latest PCSX2** — works with current Nightly builds and the Qt frontend
- **Runs on Linux/macOS/Windows** — Python + tkinter, no .NET dependency
- **Same feature set** — 100% logic parity with the C# version
- **Thread-safe IPC** — all memory operations go through a locked socket with auto-reconnect

## Requirements

- **PCSX2** (v1.7+ or Nightly) with PINE IPC enabled (Settings → Advanced → Enable PINE)
- **Dark Cloud (NTSC-U)** — SCUS-97111
- **The Reforged PNACH file** — placed in PCSX2's cheats folder with cheats enabled
- **Python 3.10+** (if running from source) or a pre-built binary from Releases

This mod does not include the game. You must own a legal copy of Dark Cloud.

## Running

From source:

```bash
cd src
python main.py
```

Or download a pre-built binary from [Releases](../../releases) and run it alongside PCSX2.

## Configuration

The mod window has toggleable options that persist to your save file:

- Disable Weapon Beeps
- Disable Battle Music
- Mute All Music
- Widescreen Mode
- Graphics Enhancements
- Disable Attack Sounds

Options are unavailable until you load into the game. They save automatically — the next time you save in-game, your preferences are included.

---

## Detailed Mod Changes

### Ally System

- **Play as any ally in town** — switch to Xiao, Goro, Ruby, Ungaga, or Osmond in the overworld via the ally menu
- **Custom NPC dialogues** — every town NPC has unique dialogue for each ally character (500+ custom dialogue strings across all 5 allies and 8 town areas)
- **Dark Heaven Castle dialogues** — ally-specific dialogue for the final area
- **Fairy King dialogue** — custom text explaining the ally summoning system
- **Intro cutscene text** — "Reforged journey" message when starting a new game
- **Character name substitution** — NPC dialogues dynamically insert the player's character name

### Dungeon Changes

- **Mini-boss spawns** — rare powerful enemies can appear on dungeon floors with scaling difficulty
- **Randomized chest loot** — dungeon chest contents are randomized from curated loot tables per dungeon
- **Randomized clown loot** — clown enemy drops pulled from separate loot tables
- **Back-floor access** — revisit previously cleared dungeon floors
- **Monster kill quest tracking** — tracks kills for Samba's challenge quests
- **Mayor quest HP scaling** — mayor quest enemies get boosted max HP (250)
- **Ungaga door fix** — fixes a vanilla bug with Ungaga and locked doors
- **Escape/Repair powder in dungeon** — escape and repair powders are usable and stackable

### Custom Weapon Effects

Each weapon has a unique passive effect while equipped in dungeon:

- **Bone Rapier** — open bone doors without a key
- **Angel Gear** — heals all allies by 1 HP every 5 seconds
- **Hercules Wrath** — 30% chance on taking damage to gain Stamina status for 30 seconds
- **Babel Spear** — 6% chance on hit to freeze all enemies for 5 seconds
- **Supernova** — 10% chance on hit to apply a random status effect to enemies
- **Star Breaker** — 2% chance on kill to receive an empty Synth Sphere
- **Secret Armlet** — all magic circle effects become positive while equipped
- **Inferno** — Goro's attack scales with missing HP and thirst level
- **Seventh Heaven** — duplicates non-gem attachments on pickup (50% chance for gems)
- **Chronicle Sword** — displays floating damage numbers; damage scales with weapon WHP
- **Tall Hammer** — unique combat effect
- **Mobius Ring** — unique combat effect
- **Sword of Zeus** — max attack increases with thunder element level; persists across saves

### Weapon Rebalancing

- **Synth Sphere reroll** — weapon special attributes are periodically rerolled for variety
- **Shop price adjustments** — weapon buy/sell prices rebalanced across all shops
- **Weapon stat changes** — various weapons have adjusted base stats for better progression

### Shop & Economy

- **Daily shop rotation** — each shop (Gaffer, Wise Owl, Jack, Joker, Brooke, Ledan, Fairy King) has a rotating daily item
- **Base shop inventory changes** — expanded shop inventories
- **Hardening Powder** — costs 1 Gilda (down from original price)
- **Matador fishing rod** — costs 2,000 Gilda

### Item Changes

- **Shell Ring** — now discardable
- **Magical Lamp** — now discardable
- **Map** — reordered in inventory
- **Magical Crystal** — reordered in inventory
- **Escape Powder** — equippable, stackable, points to active item slots
- **Revival Powder** — stackable
- **Repair Powder** — equippable and stackable
- **Auto-Repair Powder** — stackable

### Side Quests

- **Fishing quests** — 4 fishing areas (Norune, Matataki, Queens, Muska) with catch-count and size-based quests
- **Mardan Sword bonus** — fishing point multiplier when using the Mardan Sword
- **Master fish collection** — reward for catching all fish types (Saving Book)
- **NPC side quests** — per-area quest NPCs with dialogue and completion tracking
- **Brownboo Pickle** — 100% collection tracker NPC that scans your inventory, storage, weapons, and attachments
- **Quest dialogue options** — "Do you have any sidequests?" and "It's finished!" added to NPC dialogue menus

### Ruby Element Texture Swap

- **Dynamic element display** — Ruby's element HUD icon changes color based on equipped element (Fire/Ice/Thunder/Wind/Holy)
- **Pre-baked textures** — 5 element texture blobs (50–80 KB each) written to VRAM via dynamic pointer

### Cheat Codes

Button sequences entered while paused in a dungeon:

- **Godmode** — invincibility toggle
- **Broken Dagger** — receive a Broken Dagger weapon
- **Powerup Powders** — receive stat-boosting powders
- **Max Money** — set Gilda to maximum

### Demon Shaft

- **Unlocked after credits** — beating the game properly unlocks the Demon Shaft bonus dungeon
- **Save menu fix** — the post-credits save screen works correctly with the mod active

### Save State Protection

- **Detection** — the mod monitors the frame counter and detects save state loads
- **Warning** — save states are not compatible with the mod and will trigger a warning

### Matador Model Fix

- Fixes the Matador's chest loot model display values

---

## Weapon & Economy Rebalance Details

### Toan's Swords

| Weapon         | Changes                                                                                                 |
| -------------- | ------------------------------------------------------------------------------------------------------- |
| Baselard       | Endurance → 30                                                                                          |
| Antique Sword  | Speed → 70, Fire → 15                                                                                   |
| Kitchen Knife  | WHP → 50, Attack → 25, Endurance → 30, Ice → 0, Thunder → 8, Sea → 90, removed synth slot               |
| Tsukikage      | Endurance → 33, Speed → 80                                                                              |
| Macho Sword    | Added secondary effect (32)                                                                             |
| Heaven's Cloud | Opened synth slot 3                                                                                     |
| Lamb's Sword   | Opened synth slot 3, transform threshold → 50%, stat threshold → 50%                                    |
| Brave Ark      | Opened synth slot 3                                                                                     |
| Big Bang       | Speed → 70                                                                                              |
| Small Sword    | WHP → 35, Magic → 17, Sea → 0, Metal → 10                                                               |
| Sand Breaker   | WHP → 45, Endurance → 25, opened synth slot 3                                                           |
| Drain Seeker   | WHP → 60                                                                                                |
| Chopper        | Speed → 60                                                                                              |
| Choora         | WHP → 57, Attack → 45, Speed → 70, Ice → 10, Thunder → 15, Undead/Beast/Metal → 15, opened synth slot 3 |
| Claymore       | Undead → 10, Beast → 10, Mage → 10                                                                      |
| Maneater       | Endurance → 44, Speed → 70, Magic → 45, Ice/Thunder/Holy/Undead/Beast/Metal → 15, Mimic → 10            |
| Bone Rapier    | WHP → 38, Magic → 26                                                                                    |
| Sax            | Speed → 60, Fire → 6, Sky → 10                                                                          |
| 7 Branch Sword | WHP → 47, Endurance → 47, Magic → 37, all anti-type stats → 7–10                                        |
| Cross Hinder   | Endurance → 50, Speed → 70, Magic → 32                                                                  |
| Chronicle 2    | Max Attack → 999                                                                                        |

### Xiao's Slingshots

| Weapon           | Changes                         |
| ---------------- | ------------------------------- |
| Wooden Slingshot | Attack → 6, Magic → 2, Fire → 4 |
| Bandit Slingshot | Buildup → 128                   |
| Bone Slingshot   | Attack → 11, Endurance → 30     |
| Hardshooter      | Speed → 60                      |
| Matador          | Added secondary effect (16)     |

### Goro's Hammers

| Weapon           | Changes                     |
| ---------------- | --------------------------- |
| Turtle Shell     | Magic → 10                  |
| Big Bucks Hammer | Buildup → 8                 |
| Frozen Tuna      | WHP → 65                    |
| Gaia Hammer      | Endurance → 25              |
| Trial Hammer     | Attack → 30, Endurance → 25 |

### Ruby's Rings

| Weapon          | Changes                                                  |
| --------------- | -------------------------------------------------------- |
| Gold Ring       | Attack → 15, Magic → 30                                  |
| Bandit's Ring   | Attack → 30, Max Attack → 50, Magic → 20, Buildup → 8200 |
| Platinum Ring   | Attack → 23                                              |
| Pocklekul       | Attack → 28, Magic → 28, Holy → 0, Buildup → 8256        |
| Thorn Armlet    | Max Magic → 65, Buildup → 128                            |
| Athena's Armlet | Added secondary effect (32)                              |

### Ungaga's Spears

All of Ungaga's weapons (except Babel's Spear) receive a flat buff:

- Attack +10
- Max Attack +10
- Endurance +15

Babel's Spear additionally gets synth slot 4 opened.

### Osmond's Guns

All of Osmond's weapons receive a flat buff:

- Attack +15
- Max Attack +15

Skunk's buildup is set to 386.

### Shop Price Changes

| Item              | Buy    | Sell |
| ----------------- | ------ | ---- |
| Treasure Key      | 400g   | 200g |
| Anti-Curse Amulet | 400g   | 200g |
| Anti-Goo Amulet   | 400g   | 200g |
| Tram Oil          | 600g   | 300g |
| Sundew            | 750g   | 375g |
| Flapping Fish     | 300g   | 150g |
| Secret Path Key   | 900g   | 450g |
| Bravery Launch    | 1,200g | 600g |
| Flapping Duster   | 1,500g | 750g |
| Hardening Powder  | 1g     | —    |
| Matador (fishing) | 2,000g | —    |

All bait sell prices reduced to 25% of buy price. All 119 weapons have individually set buy/sell prices (sell price is roughly 1/3 of buy price).
