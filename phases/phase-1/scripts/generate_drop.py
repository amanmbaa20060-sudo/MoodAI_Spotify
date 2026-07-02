"""Batch worker for generating daily Discovery Drops."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
PHASE1_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(PHASE1_ROOT) not in sys.path:
    sys.path.insert(0, str(PHASE1_ROOT))

from phases.common.config import get_settings  # noqa: E402
from app.explanations import ExplanationService  # noqa: E402
from app.mood_state import MoodStateService  # noqa: E402
from app.novelty import NoveltyFilterService  # noqa: E402
from app.orchestrator import DiscoveryOrchestrator  # noqa: E402
from app.ranker import MoodAwareRanker  # noqa: E402
from app.repository import Phase1Repository  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate daily Discovery Drops")
    parser.add_argument("--user-id", help="Generate a drop for a single user")
    parser.add_argument("--date", default=str(date.today()), help="Drop date (YYYY-MM-DD)")
    args = parser.parse_args()

    settings = get_settings()
    repository = Phase1Repository(settings.database_url)
    mood_state = MoodStateService(repository, settings.default_mood)
    orchestrator = DiscoveryOrchestrator(
        repository=repository,
        ranker=MoodAwareRanker(),
        novelty_filter=NoveltyFilterService(repository),
        explanations=ExplanationService(repository, settings),
        drop_size=settings.drop_size,
    )

    users = [args.user_id] if args.user_id else repository.list_known_users()
    run_date = date.fromisoformat(args.date)

    for user_id in users:
        mood = mood_state.get_active_mood(user_id)
        drop = orchestrator.generate_drop(user_id=user_id, mood=mood, drop_date=run_date)
        print(
            f"user={user_id} date={run_date} mood={mood} status={drop['status']} "
            f"tracks={len(drop['tracks'])}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
