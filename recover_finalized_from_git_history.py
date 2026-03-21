#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import subprocess
import datetime as dt
from pathlib import Path

SOURCE_JSON = "vacancy_price_cache.json"
CURRENT_ARCHIVE = "finalized_daily_data.json"
PREVIEW_OUTPUT = "finalized_daily_data_recovered_preview.json"
BACKUP_OUTPUT = "finalized_daily_data_backup_before_recovery.json"

# 運用開始時期に合わせる
RECOVERY_START_DATE = dt.date(2025, 4, 24)

JST = dt.timezone(dt.timedelta(hours=9))


def run_git(args):
    return subprocess.check_output(["git"] + args, text=True, encoding="utf-8", errors="ignore")


def load_json(path: str):
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_json(path: str, data: dict):
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


def parse_date(s: str):
    try:
        return dt.date.fromisoformat(s)
    except Exception:
        return None


def main():
    today_jst = dt.datetime.now(JST).date()

    print("=== recover_finalized_from_git_history.py start ===")
    print(f"RECOVERY_START_DATE: {RECOVERY_START_DATE}")
    print(f"TODAY(JST): {today_jst}")

    # 念のためバックアップ
    current_archive = load_json(CURRENT_ARCHIVE)
    if current_archive:
        save_json(BACKUP_OUTPUT, current_archive)
        print(f"backup saved: {BACKUP_OUTPUT}")

    # 履歴取得（古い順）
    log_text = run_git(["log", "--reverse", "--format=%H|%cI", "--", SOURCE_JSON])
    lines = [line.strip() for line in log_text.splitlines() if line.strip()]

    if not lines:
        print("No git history found for vacancy_price_cache.json")
        return

    print(f"commit count: {len(lines)}")

    recovered = {}
    commit_counter = 0
    hit_counter = 0

    for line in lines:
        commit_counter += 1
        sha, commit_iso = line.split("|", 1)

        try:
            raw = run_git(["show", f"{sha}:{SOURCE_JSON}"])
            snap = json.loads(raw)
        except Exception:
            continue

        changed_in_this_commit = 0

        for k, v in snap.items():
            d = parse_date(k)
            if d is None:
                continue
            if d < RECOVERY_START_DATE:
                continue
            if d >= today_jst:
                continue

            if not isinstance(v, dict):
                continue

            vacancy = v.get("vacancy")
            avg_price = v.get("avg_price")

            if vacancy is None or avg_price is None:
                continue

            try:
                vacancy_i = int(vacancy)
                avg_price_i = int(round(float(avg_price)))
            except Exception:
                continue

            # 履歴を古い順に舐めて最後の値で上書き
            recovered[k] = {
                "vacancy": vacancy_i,
                "avg_price": avg_price_i
            }
            changed_in_this_commit += 1

        if changed_in_this_commit:
            hit_counter += 1

        if commit_counter % 50 == 0:
            print(f"... processed {commit_counter}/{len(lines)} commits")

    # 既存archiveを優先してマージ
    merged = dict(recovered)
    merged.update(current_archive)
    merged = dict(sorted(merged.items()))

    save_json(PREVIEW_OUTPUT, merged)

    keys = list(merged.keys())
    print("=== recovery summary ===")
    print(f"recovered_preview_count: {len(merged)}")
    print(f"commits_with_hits: {hit_counter}")
    if keys:
        print(f"earliest_date: {keys[0]}")
        print(f"latest_date: {keys[-1]}")
    print(f"preview saved: {PREVIEW_OUTPUT}")
    print("=== done ===")


if __name__ == "__main__":
    main()
