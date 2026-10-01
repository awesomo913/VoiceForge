import json
import logging
import os
import re

from params import VoiceParams

log = logging.getLogger(__name__)

CATEGORIES = ["My Voices", "Reel Personas", "Assistants", "Characters"]


def _slug(name: str) -> str:
    return re.sub(r"[^\w\-]", "_", name.lower())


class PresetManager:
    def __init__(
        self,
        user_dir: str = "presets/user",
        builtin_dir: str = "presets/builtin",
    ) -> None:
        self.user_dir = user_dir
        self.builtin_dir = builtin_dir
        os.makedirs(user_dir, exist_ok=True)
        for cat in CATEGORIES:
            os.makedirs(os.path.join(user_dir, _slug(cat)), exist_ok=True)

    def _user_path(self, name: str, category: str) -> str:
        return os.path.join(self.user_dir, _slug(category), f"{_slug(name)}.json")

    def _builtin_path(self, name: str) -> str:
        return os.path.join(self.builtin_dir, f"{_slug(name)}.json")

    def save(self, name: str, category: str, params: VoiceParams) -> None:
        path = self._user_path(name, category)
        data = {"name": name, "category": category, "params": params.to_dict()}
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError as exc:
            log.warning("Failed to save preset %r: %s", name, exc)
            raise

    def load(self, name: str, category: str) -> VoiceParams:
        path = self._user_path(name, category)
        if not os.path.exists(path):
            path = self._builtin_path(name)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Preset not found: {name!r} in {category!r}")
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            log.warning("Failed to load preset %r: %s", name, exc)
            raise
        return VoiceParams.from_dict(data.get("params", data))

    def list_presets(self) -> dict[str, list[str]]:
        result: dict[str, list[str]] = {cat: [] for cat in CATEGORIES}

        # Builtin presets
        if os.path.exists(self.builtin_dir):
            for fname in sorted(os.listdir(self.builtin_dir)):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(self.builtin_dir, fname)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        data = json.load(f)
                    cat = data.get("category", "Characters")
                    pname = data.get("name", fname[:-5])
                    if cat in result:
                        result[cat].append(pname)
                except Exception as exc:
                    log.warning("Skipping builtin preset %r: %s", fname, exc)

        # User presets
        for cat in CATEGORIES:
            cat_dir = os.path.join(self.user_dir, _slug(cat))
            if not os.path.exists(cat_dir):
                continue
            for fname in sorted(os.listdir(cat_dir)):
                if not fname.endswith(".json"):
                    continue
                fpath = os.path.join(cat_dir, fname)
                try:
                    with open(fpath, encoding="utf-8") as f:
                        data = json.load(f)
                    pname = data.get("name", fname[:-5])
                    if pname not in result[cat]:
                        result[cat].append(pname)
                except Exception as exc:
                    log.warning("Skipping user preset %r: %s", fname, exc)

        return result

    def delete(self, name: str, category: str) -> None:
        path = self._user_path(name, category)
        if os.path.exists(path):
            try:
                os.unlink(path)
            except OSError as exc:
                log.warning("Failed to delete preset %r: %s", name, exc)
                raise

    def rename(self, old_name: str, new_name: str, category: str) -> None:
        params = self.load(old_name, category)
        self.save(new_name, category, params)
        self.delete(old_name, category)
