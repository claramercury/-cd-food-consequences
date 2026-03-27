# Averno — Food Consequences v0.1
### A Crimson Desert mod by claramercury

Activates food consequence mechanics that Pearl Abyss built into the BlackSpace engine but disabled at launch.

**v0.1 — Umbrella Mushroom now poisons you.**

---

## What this mod does

- **Umbrella_Mushroom** now applies `Food_Poison` (DoT — damage over time) when consumed
- The game's native poison UI activates automatically — no new assets
- All effects use vanilla engine mechanics. Nothing was invented, only reconnected.

## What this mod does NOT do

- Does not modify food item stats, recipes, or any other consumable
- Does not affect combat balance, enemies, or loot
- Does not install any DLL or code into the game process

## Why it exists

Crimson Desert shipped with a complete food consequence system — freshness decay, poisoning, confusion, morale penalties, temperature effects — fully implemented in the engine but with the negative effects switched off at launch. This mod turns on a small part of that system.

The Reddit community was asking for survival mechanics. They were already there.

## Installation

**Requires:** [CDModManager](https://www.nexusmods.com/crimsondesert/mods/114)

1. Download CDModManager and extract it
2. Drop `AvernoFoodConsequences.cdmod` into the `mods/` folder
3. Open CDModManager, check the mod, click **Apply Checked Mods**
4. Launch Crimson Desert

To uninstall: click **Restore All** in CDModManager.

## Technical notes

- Modifies: `0008/skill.pabgb` (skill definitions table)
- Patch: `Item_Active_UmbrellaMushroomDrug` skill — buff changed from `BuffLevel_Food_AttackSpeedRate` to `BuffLevel_Food_Poison`
- Compatible with CDCamera, StaminaManager, and other CDModManager mods
- Tested on game version 1.3

## Roadmap

| Version | What |
|---------|------|
| v0.1 | Umbrella Mushroom → Food_Poison |
| v0.2 | Food_CookFailed → Drunken effect |
| v0.3 | All mushroom teas → appropriate effects |
| v0.4 | Boss combat consumable limits (configurable) |

## Credits

- **claramercury** — mod author, reverse engineering
- **Lazorr** — cracked the ChaCha20 encryption that made this possible
- **CDModManager team** — the infrastructure that makes distributing mods viable
- Pearl Abyss engineers who built the system in the first place

---

*Part of the [Averno](https://github.com/claramercury) project.*
