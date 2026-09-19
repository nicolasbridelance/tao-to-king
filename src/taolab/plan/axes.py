"""Validated, versioned axis definitions and declarative compatibility rules."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml


AXIS_TYPES = {"selector", "transformer", "constraint", "instantiator"}
IDENTIFIER = re.compile(r"^[a-z][a-z0-9_]*$")


def fingerprint(value: object) -> str:
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Axis:
    id: str
    type: str
    description: str
    values: tuple[dict, ...]

    def definition(self) -> dict:
        return {
            "id": self.id, "type": self.type, "description": self.description,
            "values": list(self.values),
        }


@dataclass(frozen=True)
class Rule:
    id: str
    when: dict[str, str]
    requires: dict[str, int]
    reason: str

    def definition(self) -> dict:
        return {"id": self.id, "when": self.when, "requires": self.requires,
                "reason": self.reason}


@dataclass(frozen=True)
class Catalogue:
    axes: tuple[Axis, ...]
    rules: tuple[Rule, ...]

    @property
    def axes_hash(self) -> str:
        return fingerprint([axis.definition() for axis in self.axes])

    @property
    def rules_hash(self) -> str:
        return fingerprint([rule.definition() for rule in self.rules])


def load_catalogue(directory: Path) -> Catalogue:
    axes: list[Axis] = []
    for path in sorted(directory.glob("*.yaml")):
        if path.name == "compat.yaml":
            continue
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(document, dict) or not isinstance(document.get("axes"), list):
            raise ValueError(f"{path}: expected an axes list")
        for item in document["axes"]:
            axis_id = item.get("id")
            axis_type = item.get("type")
            values = item.get("values")
            if not isinstance(axis_id, str) or not IDENTIFIER.fullmatch(axis_id):
                raise ValueError(f"{path}: invalid axis ID")
            if axis_type not in AXIS_TYPES:
                raise ValueError(f"{path}: invalid type for {axis_id}")
            if not isinstance(values, list) or not values:
                raise ValueError(f"{path}: {axis_id} has no values")
            seen = set()
            for value in values:
                value_id = value.get("id")
                if not isinstance(value_id, str) or not IDENTIFIER.fullmatch(value_id):
                    raise ValueError(f"{path}: invalid value ID in {axis_id}")
                if value_id in seen:
                    raise ValueError(f"{path}: duplicate {axis_id}.{value_id}")
                seen.add(value_id)
                if not all(value.get(key) for key in ("label", "instruction", "introduced")):
                    raise ValueError(f"{path}: incomplete {axis_id}.{value_id}")
            axes.append(Axis(axis_id, axis_type, item.get("description", ""), tuple(values)))
    if not axes or len({axis.id for axis in axes}) != len(axes):
        raise ValueError("axes must be present and have unique IDs")
    axes.sort(key=lambda axis: axis.id)
    compat_path = directory / "compat.yaml"
    document = yaml.safe_load(compat_path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("rules"), list):
        raise ValueError(f"{compat_path}: expected a rules list")
    value_ids = {axis.id: {value["id"] for value in axis.values} for axis in axes}
    rules: list[Rule] = []
    for item in document["rules"]:
        rule_id = item.get("id")
        when = item.get("when")
        requires = item.get("requires")
        if not isinstance(rule_id, str) or not IDENTIFIER.fullmatch(rule_id):
            raise ValueError(f"{compat_path}: invalid rule ID")
        if not isinstance(when, dict) or not when:
            raise ValueError(f"{compat_path}: {rule_id} has no condition")
        if any(value not in value_ids.get(axis, set()) for axis, value in when.items()):
            raise ValueError(f"{compat_path}: {rule_id} uses unknown axis value")
        if not isinstance(requires, dict) or not requires:
            raise ValueError(f"{compat_path}: {rule_id} has no requirement")
        if set(requires) - {"min_translations", "min_source_characters"}:
            raise ValueError(f"{compat_path}: {rule_id} has unknown requirement")
        if any(not isinstance(value, int) or value < 0 for value in requires.values()):
            raise ValueError(f"{compat_path}: {rule_id} has invalid threshold")
        rules.append(Rule(rule_id, when, requires, item.get("reason", "")))
    if len({rule.id for rule in rules}) != len(rules):
        raise ValueError("duplicate compatibility rule ID")
    rules.sort(key=lambda rule: rule.id)
    return Catalogue(tuple(axes), tuple(rules))


def rejected_by(
    catalogue: Catalogue, coordinates: dict[str, str], *,
    translation_count: int, source_characters: int,
) -> tuple[str, ...]:
    rejected = []
    for rule in catalogue.rules:
        if any(coordinates.get(axis) != value for axis, value in rule.when.items()):
            continue
        if "min_translations" in rule.requires:
            if translation_count < rule.requires["min_translations"]:
                rejected.append(rule.id)
        if "min_source_characters" in rule.requires:
            if source_characters < rule.requires["min_source_characters"]:
                rejected.append(rule.id)
    return tuple(rejected)
