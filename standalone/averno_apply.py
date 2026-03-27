#!/usr/bin/env python3
"""
Averno Food Consequences — Standalone Installer
https://github.com/claramercury/-cd-food-consequences

Applies the mod directly to your Crimson Desert installation.
No external mod manager required.

Usage:
    python averno_apply.py                    # interactive mode
    python averno_apply.py --preset survival  # direct apply
    python averno_apply.py --restore          # restore vanilla
    python averno_apply.py --status           # check current state
"""

import argparse
import ctypes
import json
import os
import shutil
import struct
import sys
import lz4.block

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE  = os.path.join(SCRIPT_DIR, "config.json")
BACKUP_DIR   = os.path.join(SCRIPT_DIR, "backup")
OVERLAY_DIR  = os.path.join(SCRIPT_DIR, "overlay")

PRESETS = {
    "adventure": {
        "name":        "Adventure",
        "description": "Poison DoT + nutritional benefit. Ambiguous consequence.",
    },
    "survival": {
        "name":        "Survival",
        "description": "Double poison stack. No benefit. Clearly dangerous.",
    },
    "iron_gut": {
        "name":        "Iron Gut",
        "description": "Poison + Drunken simultaneously. You asked for it.",
    },
}

TARGET_ARCHIVE = "0008"
TARGET_FILE    = "skill.pabgb"
OVERLAY_FOLDER = "0036"
DECOMP_SIZE    = 1_128_500
COMP_TARGET    = 177_466


# ── Config ────────────────────────────────────────────────────────────

def load_config():
    defaults = {
        "game_dir": "",
        "active_preset": None,
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                defaults.update(saved)
        except Exception:
            pass
    return defaults


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def find_game_dir():
    candidates = [
        r"C:\Program Files (x86)\Steam\steamapps\common\Crimson Desert",
        r"C:\Program Files\Steam\steamapps\common\Crimson Desert",
        r"D:\Steam\steamapps\common\Crimson Desert",
        r"D:\SteamLibrary\steamapps\common\Crimson Desert",
        r"E:\Steam\steamapps\common\Crimson Desert",
        r"E:\SteamLibrary\steamapps\common\Crimson Desert",
    ]
    for path in candidates:
        if os.path.isdir(path) and os.path.isdir(os.path.join(path, "0008")):
            return path
    return None


# ── Timestamps (Windows) ──────────────────────────────────────────────

def save_timestamps(path):
    if sys.platform != "win32":
        return lambda: None
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class FILETIME(ctypes.Structure):
        _fields_ = [("lo", ctypes.c_uint32), ("hi", ctypes.c_uint32)]

    OPEN_EXISTING = 3
    GR = 0x80000000
    GW = 0x40000000
    FLAGS = 0x80 | 0x02000000

    h = kernel32.CreateFileW(path, GR, 1, None, OPEN_EXISTING, FLAGS, None)
    if h == -1:
        return lambda: None
    ct, at, mt = FILETIME(), FILETIME(), FILETIME()
    kernel32.GetFileTime(h, ctypes.byref(ct), ctypes.byref(at), ctypes.byref(mt))
    kernel32.CloseHandle(h)

    def restore():
        h2 = kernel32.CreateFileW(path, GW, 0, None, OPEN_EXISTING, FLAGS, None)
        if h2 != -1:
            kernel32.SetFileTime(h2, ctypes.byref(ct), ctypes.byref(at), ctypes.byref(mt))
            kernel32.CloseHandle(h2)

    return restore


# ── PAMT parsing ──────────────────────────────────────────────────────

class _VFS:
    def __init__(self, nb):
        self._nb = nb

    def path(self, o):
        if o == 0xFFFFFFFF or o >= len(self._nb):
            return ""
        parts = []
        cur = o
        while cur != 0xFFFFFFFF and len(parts) < 64:
            if cur + 5 > len(self._nb):
                break
            par = struct.unpack_from("<I", self._nb, cur)[0]
            pl  = self._nb[cur + 4]
            parts.append(self._nb[cur + 5: cur + 5 + pl].decode("utf-8", errors="replace"))
            cur = par
        parts.reverse()
        return "".join(parts)


def _parse_pamt(pamt_path):
    with open(pamt_path, "rb") as f:
        d = f.read()
    o = 0
    _, pc, _ = struct.unpack_from("<III", d, o); o += 12
    for _ in range(pc): o += 12
    dsz = struct.unpack_from("<I", d, o)[0]; o += 4; o += dsz
    fsz = struct.unpack_from("<I", d, o)[0]; o += 4
    fn  = d[o: o + fsz]; o += fsz
    hc  = struct.unpack_from("<I", d, o)[0]; o += 4; o += hc * 16
    fc  = struct.unpack_from("<I", d, o)[0]; o += 4
    entries = []
    for _ in range(fc):
        no, off, cs, ds, pi, fl = struct.unpack_from("<IIIIHH", d, o); o += 20
        entries.append((no, off, cs, ds, pi, fl))
    return _VFS(fn), entries


def _find_entry(game_dir, archive, filename):
    pamt = os.path.join(game_dir, archive, "0.pamt")
    vfs, entries = _parse_pamt(pamt)
    for no, off, cs, ds, pi, fl in entries:
        if vfs.path(no).lower() == filename.lower():
            paz = os.path.join(game_dir, archive, f"{pi}.paz")
            return paz, off, cs, ds, pi
    return None, None, None, None, None


# ── Patch building ────────────────────────────────────────────────────

def _extract_skill(game_dir):
    paz, off, cs, ds, pi, = _find_entry(game_dir, TARGET_ARCHIVE, TARGET_FILE)
    if paz is None:
        raise FileNotFoundError(f"Could not find {TARGET_FILE} in archive {TARGET_ARCHIVE}")
    with open(paz, "rb") as f:
        f.seek(off); raw = f.read(cs)
    return lz4.block.decompress(raw, uncompressed_size=ds)


def _patch_data(vanilla, preset):
    SLOT1 = bytes([0xa5, 0x42, 0x0f, 0x00])  # Food_Poison
    SLOT2 = {
        "adventure": bytes([0x72, 0x42, 0x0f, 0x00]),  # Food_MaxHP
        "survival":  bytes([0xa5, 0x42, 0x0f, 0x00]),  # Food_Poison x2
        "iron_gut":  bytes([0x6a, 0x42, 0x0f, 0x00]),  # Drunken
    }[preset]

    data = bytearray(vanilla)
    data[869381] = 0x00
    data[869506: 869510] = SLOT1
    data[869656: 869660] = SLOT2
    return bytes(data)


def _compress_exact(data, target_size):
    blob = lz4.block.compress(data, store_size=False)
    if len(blob) == target_size:
        return blob
    # Search for single-byte fix to hit target size
    for off in range(len(data) - 4):
        if data[off] == 0:
            continue
        trial = bytearray(data)
        trial[off] = 0x00
        c = lz4.block.compress(bytes(trial), store_size=False)
        if len(c) == target_size:
            return c
    raise RuntimeError(
        f"Could not compress to exactly {target_size} bytes. "
        "Your game version may differ from the one this mod was built for."
    )


# ── Overlay PAZ / PAMT ────────────────────────────────────────────────

def _build_overlay_pamt(blob_size, template_pamt_path):
    with open(template_pamt_path, "rb") as f:
        pamt = bytearray(f.read())
    paz_total = blob_size + 7
    struct.pack_into("<I", pamt, 0x14, paz_total)
    struct.pack_into("<I", pamt, 0x80, blob_size)
    struct.pack_into("<I", pamt, 0x84, DECOMP_SIZE)
    return bytes(pamt)


def _write_overlay(game_dir, blob, pamt_bytes, preset):
    overlay_root = os.path.join(game_dir, OVERLAY_FOLDER)
    os.makedirs(overlay_root, exist_ok=True)

    paz_path  = os.path.join(overlay_root, "0.paz")
    pamt_path = os.path.join(overlay_root, "0.pamt")

    restore_ts_paz  = save_timestamps(paz_path)  if os.path.exists(paz_path)  else lambda: None
    restore_ts_pamt = save_timestamps(pamt_path) if os.path.exists(pamt_path) else lambda: None

    with open(paz_path, "wb") as f:
        f.write(blob + bytes(7))
    with open(pamt_path, "wb") as f:
        f.write(pamt_bytes)

    restore_ts_paz()
    restore_ts_pamt()


# ── Apply / Restore ───────────────────────────────────────────────────

def apply_preset(game_dir, preset, cfg, verbose=True):
    if verbose:
        print(f"Extracting {TARGET_FILE}...")
    vanilla = _extract_skill(game_dir)

    if verbose:
        print(f"Applying preset: {PRESETS[preset]['name']}...")
    patched = _patch_data(vanilla, preset)

    if verbose:
        print("Compressing...")
    blob = _compress_exact(patched, COMP_TARGET)

    # Build PAMT using the bundled template
    template_pamt = os.path.join(OVERLAY_DIR, "template_0.pamt")
    pamt_bytes = _build_overlay_pamt(len(blob), template_pamt)

    if verbose:
        print("Writing overlay files...")
    _write_overlay(game_dir, blob, pamt_bytes, preset)

    cfg["active_preset"] = preset
    save_config(cfg)

    if verbose:
        print(f"\nDone. Preset '{PRESETS[preset]['name']}' applied.")
        print("Launch Crimson Desert to see the changes.")


def restore_vanilla(game_dir, cfg, verbose=True):
    overlay_root = os.path.join(game_dir, OVERLAY_FOLDER)
    if not os.path.isdir(overlay_root):
        if verbose:
            print("No overlay found — game is already vanilla.")
        return

    shutil.rmtree(overlay_root)
    cfg["active_preset"] = None
    save_config(cfg)

    if verbose:
        print("Vanilla restored. Overlay folder removed.")


def show_status(game_dir, cfg):
    preset = cfg.get("active_preset")
    overlay = os.path.join(game_dir, OVERLAY_FOLDER)
    overlay_exists = os.path.isdir(overlay)

    print(f"Game dir:      {game_dir}")
    print(f"Overlay:       {'present' if overlay_exists else 'not found'}")
    if preset and overlay_exists:
        p = PRESETS.get(preset, {})
        print(f"Active preset: {p.get('name', preset)} — {p.get('description', '')}")
    else:
        print("Active preset: none (vanilla)")


# ── Interactive mode ──────────────────────────────────────────────────

def interactive(cfg):
    print("\nAverno — Food Consequences")
    print("Standalone Installer\n")

    game_dir = cfg.get("game_dir", "")
    if not game_dir or not os.path.isdir(game_dir):
        detected = find_game_dir()
        if detected:
            print(f"Game found at: {detected}")
            ans = input("Use this path? [Y/n]: ").strip().lower()
            game_dir = detected if ans in ("", "y") else ""
        if not game_dir:
            game_dir = input("Enter Crimson Desert path: ").strip().strip('"')
        if not os.path.isdir(game_dir):
            print(f"Error: path not found — {game_dir}")
            sys.exit(1)
        cfg["game_dir"] = game_dir
        save_config(cfg)

    print("\nPresets:")
    keys = list(PRESETS.keys())
    for i, k in enumerate(keys, 1):
        p = PRESETS[k]
        print(f"  {i}. {p['name']} — {p['description']}")
    print("  R. Restore vanilla")
    print("  S. Show status")
    print("  Q. Quit\n")

    choice = input("Choose [1/2/3/R/S/Q]: ").strip().upper()
    if choice == "Q":
        sys.exit(0)
    elif choice == "S":
        show_status(game_dir, cfg)
    elif choice == "R":
        restore_vanilla(game_dir, cfg)
    elif choice in ("1", "2", "3"):
        apply_preset(game_dir, keys[int(choice) - 1], cfg)
    else:
        print("Invalid choice.")


# ── CLI ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Averno Food Consequences — Standalone Installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(
            [f"  --preset {k}  {v['name']} — {v['description']}" for k, v in PRESETS.items()]
        ),
    )
    parser.add_argument("--preset",  choices=list(PRESETS.keys()), help="Apply a preset directly")
    parser.add_argument("--restore", action="store_true",           help="Restore vanilla")
    parser.add_argument("--status",  action="store_true",           help="Show current state")
    parser.add_argument("--game-dir", metavar="PATH",               help="Override game directory")
    args = parser.parse_args()

    cfg = load_config()

    if args.game_dir:
        cfg["game_dir"] = args.game_dir
        save_config(cfg)

    game_dir = cfg.get("game_dir", "")
    if not game_dir or not os.path.isdir(game_dir):
        game_dir = find_game_dir()
        if game_dir:
            cfg["game_dir"] = game_dir
            save_config(cfg)
        else:
            print("Error: Crimson Desert not found. Run without arguments for interactive mode.")
            sys.exit(1)

    if args.status:
        show_status(game_dir, cfg)
    elif args.restore:
        restore_vanilla(game_dir, cfg)
    elif args.preset:
        apply_preset(game_dir, args.preset, cfg)
    else:
        interactive(cfg)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled.")
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)
