"""Pre-seeded registry (X6): parent phone -> CHU -> CHP, CHA, facility."""
from pathlib import Path

import yaml

GSM7 = set("@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà")


class Registry:
    def __init__(self, path):
        cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        self.lines = cfg["lines"]
        self.role_of_line = {v: k for k, v in self.lines.items()}
        self.facility = cfg["facility"]
        name = self.facility["name"]
        if len(name) > 28 or not set(name) <= GSM7:
            raise ValueError("facility name must be at most 28 GSM-7 characters")
        self.cha = {c["id"]: c for c in cfg["cha"]}
        self.chu = {c["n"]: c for c in cfg["chus"]}
        self.chps = {c["id"]: c for c in cfg["chps"]}
        self.chp_by_phone = {c["phone"]: c for c in cfg["chps"]}
        self.parents = {p["phone"]: p for p in cfg["parents"]}
        self.default_cha = cfg["cha"][0]

    def role(self, to):
        return self.role_of_line.get(to)

    def parent(self, phone):
        return self.parents.get(phone)

    def chp_of_parent(self, phone):
        p = self.parents.get(phone)
        return self.chps.get(p["chp"]) if p and p.get("chp") else None

    def cha_of_chp(self, chp):
        return self.cha[self.chu[chp["chu"]]["cha"]]
