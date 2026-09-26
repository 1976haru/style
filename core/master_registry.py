from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY_PATH = ROOT / "user_data" / "master_registry.json"
GENRE_PROFILES_PATH = ROOT / "data" / "genre_master_profiles.json"

CHANNEL_IDS = ("senior", "chili_male", "chili_female", "chili_dual", "custom")
CHANNEL_LABELS = {
    "senior": "시니어",
    "chili_male": "CHILI LAB 남성",
    "chili_female": "CHILI LAB 여성",
    "chili_dual": "CHILI LAB 두사람",
    "custom": "Custom",
}


def default_registry() -> Dict[str, Any]:
    return {"channelMasters": {key: {"path": ""} for key in CHANNEL_IDS}}


def load_master_registry(path: str | Path = DEFAULT_REGISTRY_PATH) -> Dict[str, Any]:
    p = Path(path)
    data = default_registry()
    if p.exists():
        try:
            loaded = json.loads(p.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"마스터 registry를 읽을 수 없습니다: {exc}") from exc
        masters = loaded.get("channelMasters") if isinstance(loaded, dict) else None
        if not isinstance(masters, dict):
            raise ValueError("master_registry.json에 channelMasters object가 필요합니다.")
        for key in CHANNEL_IDS:
            entry = masters.get(key)
            if isinstance(entry, dict):
                data["channelMasters"][key]["path"] = str(entry.get("path") or "")
    return data


def save_master_registry(registry: Dict[str, Any], path: str | Path = DEFAULT_REGISTRY_PATH) -> None:
    p = Path(path)
    normalized = default_registry()
    masters = registry.get("channelMasters") if isinstance(registry, dict) else {}
    for key in CHANNEL_IDS:
        entry = masters.get(key) if isinstance(masters, dict) else None
        normalized["channelMasters"][key]["path"] = str(entry.get("path") or "") if isinstance(entry, dict) else ""
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")


def register_master(channel_id: str, master_path: str | Path, registry_path: str | Path = DEFAULT_REGISTRY_PATH) -> Dict[str, Any]:
    if channel_id not in CHANNEL_IDS:
        raise ValueError(f"지원하지 않는 채널 타입입니다: {channel_id}")
    p = Path(master_path).resolve()
    if not p.is_file():
        raise ValueError(f"마스터 파일을 찾을 수 없습니다: {p}")
    registry = load_master_registry(registry_path)
    registry["channelMasters"][channel_id]["path"] = str(p)
    save_master_registry(registry, registry_path)
    return registry


def registered_master_path(channel_id: str, registry_path: str | Path = DEFAULT_REGISTRY_PATH) -> Path | None:
    registry = load_master_registry(registry_path)
    raw = registry["channelMasters"].get(channel_id, {}).get("path", "")
    if not raw:
        return None
    p = Path(raw)
    return p if p.is_file() else None


def read_registered_master(channel_id: str, registry_path: str | Path = DEFAULT_REGISTRY_PATH) -> tuple[str, Path | None]:
    p = registered_master_path(channel_id, registry_path)
    return (p.read_text(encoding="utf-8-sig"), p) if p else ("", None)


def load_genre_profiles(path: str | Path = GENRE_PROFILES_PATH) -> Dict[str, Dict[str, Any]]:
    p = Path(path)
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Genre Master Profiles를 읽을 수 없습니다: {exc}") from exc
    profiles = data.get("genreMasterProfiles") if isinstance(data, dict) else None
    if not isinstance(profiles, dict):
        raise ValueError("genre_master_profiles.json에 genreMasterProfiles object가 필요합니다.")
    return deepcopy(profiles)


def build_active_master(channel_master_text: str, genre_profile: Dict[str, Any], source_profile: Dict[str, Any]) -> str:
    if not channel_master_text.strip():
        raise ValueError("Channel Master가 비어 있습니다.")
    required = {
        "id", "label", "dominantGenre", "bpm", "groove", "drums", "bass",
        "instrumentation", "harmony", "vocalBehavior", "structure", "bridge",
        "final", "stylePromptRules", "excludeRules",
    }
    missing = sorted(required - set(genre_profile))
    if missing:
        raise ValueError(f"Genre Master 필드 누락: {missing}")
    genre_text = json.dumps(genre_profile, ensure_ascii=False, indent=2)
    source_text = json.dumps(source_profile, ensure_ascii=False, indent=2)
    return f"""[CHANNEL / VOCAL MASTER]
{channel_master_text.strip()}

[SELECTED GENRE MASTER]
{genre_text}

[SOURCE PROFILE]
{source_text}

[PRECEDENCE]
Channel vocal identity and hard locks override genre defaults.
Selected genre controls BPM/groove/instrumentation/harmony/structure/Bridge/Final/stylePrompt/excludes.
If the Channel Master declares a more specific BPM hard lock, use it instead of the Genre Master BPM range.
Story/title/hook/lyrics remain immutable."""
