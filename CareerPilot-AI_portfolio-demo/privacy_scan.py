"""Fail when known private artifacts or identity markers enter the demo tree."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SKIP_DIRS = {".git", "__pycache__", ".venv"}
SKIP_FILES = {"privacy_scan.py", ".DS_Store", "portfolio_demo.db", "portfolio_demo.db-shm", "portfolio_demo.db-wal"}
FORBIDDEN_FILES = {"personal_resume_private.py", "database.py", "careerpilot.db"}
FORBIDDEN_PATTERNS = {
    "private phone": re.compile(r"\b1[3-9]\d{9}\b"),
    "private email": re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    "private address": re.compile(r"北京市丰台区|花乡|张家路口", re.I),
    "private identity alias": re.compile(r"Nina Liu|dorafeii", re.I),
    "named research supervisor": re.compile(r"西楠|席楠|茅倬彦", re.I),
    "real application company": re.compile(r"京东|拼多多|小米集团|字节跳动"),
    "employer identity exposed": re.compile(r"水滴|Waterdrop|安永|\bEY\b|搜狐|Sohu|FESCO", re.I),
    "internal memory UI": re.compile(r"Internal Only|备注｜内容回忆卡|AI 使用"),
    "nonempty AI usage data": re.compile(r'"ai_usage"\s*:\s*"(?!")', re.I),
    "nonempty private memory data": re.compile(r'"interview_memory_notes"\s*:\s*"(?!")', re.I),
}


def main() -> int:
    findings = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in SKIP_DIRS for part in path.parts) or path.name in SKIP_FILES:
            continue
        if path.name in FORBIDDEN_FILES:
            findings.append(f"forbidden file: {path.relative_to(ROOT)}")
            continue
        if path.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".zip", ".pdf", ".docx"}:
            findings.append(f"unexpected binary/data file: {path.relative_to(ROOT)}")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            findings.append(f"unreviewed binary file: {path.relative_to(ROOT)}")
            continue
        for label, pattern in FORBIDDEN_PATTERNS.items():
            if pattern.search(text):
                findings.append(f"{label}: {path.relative_to(ROOT)}")
    if findings:
        print("Privacy scan failed:")
        for finding in sorted(set(findings)):
            print(f"- {finding}")
        return 1
    print("Privacy scan passed: public name and career history retained; protected private markers are absent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
