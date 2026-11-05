import json
import subprocess
import sys
import xml.etree.ElementTree as ET

import yaml


def parse_json(path):
    with open(path, encoding="utf-8") as f:
        json.load(f)


def parse_yaml(path):
    with open(path, encoding="utf-8") as f:
        list(yaml.safe_load_all(f))


PARSERS = {".json": parse_json, ".xml": ET.parse, ".yml": parse_yaml, ".yaml": parse_yaml}

files = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout.split("\n")
errors = 0
for path in files:
    parser = next((p for ext, p in PARSERS.items() if path.endswith(ext)), None)
    if parser is None:
        continue
    try:
        parser(path)
        print(f"OK    {path}")
    except Exception as exc:
        errors += 1
        print(f"ERROR {path}: {exc}")
sys.exit(1 if errors else 0)
