import datetime
import json
import os
import random
import subprocess
import sys

STATE_FILE = ".commit_bot_state.json"
ACTIVITY_FILE = "activity.log"
MIN_COMMITS = 50
MAX_COMMITS = 85


def get_previous_count():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                data = json.load(f)
                return data.get("last_count", 0)
        except Exception:
            return 0
    return 0


def save_current_count(count):
    with open(STATE_FILE, "w") as f:
        json.dump({"last_count": count}, f)


def generate_commits(dry_run=False):
    previous_count = get_previous_count()

    # Generate a random count ensuring it's different from the previous one
    while True:
        count = random.randint(MIN_COMMITS, MAX_COMMITS)
        if count != previous_count:
            break

    print(f"Targeting {count} commits today. Previous count was {previous_count}.")

    if not dry_run:
        save_current_count(count)

    for i in range(count):
        timestamp = datetime.datetime.now().isoformat()

        if not dry_run:
            with open(ACTIVITY_FILE, "a") as f:
                f.write(f"Commit {i + 1}/{count} at {timestamp}\n")

            subprocess.run(["git", "add", "-f", ACTIVITY_FILE, STATE_FILE], check=True)
            subprocess.run(
                ["git", "commit", "-m", f"chore: daily activity {timestamp}"], check=True
            )

    print(f"Successfully generated {count} commits.")


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    generate_commits(dry_run=dry_run)
