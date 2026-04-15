#!/usr/bin/env python3
"""CLI entry point — run a search once, on a schedule, start the API, or health-check."""

import argparse
import logging
import signal
import sys
import time

from src import agent, api
from src.config import settings, setup_logging

logger = logging.getLogger(__name__)


def run_once() -> bool:
    logger.info("Running single job search cycle")
    try:
        output = agent.run_cycle()
        if output:
            logger.info(f"Cycle completed — output: {output}")
            return True
        logger.error("Cycle completed with errors")
        return False
    except Exception as e:
        logger.error(f"Cycle failed: {e}")
        return False


def run_scheduled(schedule_time: str):
    import schedule

    logger.info(f"Scheduling daily runs at {schedule_time}")
    schedule.every().day.at(schedule_time).do(run_once)

    stopped = False

    def handle_signal(_signum, _frame):
        nonlocal stopped
        stopped = True
        logger.info("Shutdown signal received")

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    run_once()  # run immediately on startup
    while not stopped:
        try:
            schedule.run_pending()
            time.sleep(60)
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            time.sleep(60)

    logger.info("Job agent stopped")


def print_health() -> bool:
    logger.info("Performing health check...")
    health = agent.health_check()

    print("\n=== Health Check ===")
    print(f"Overall: {'HEALTHY' if health['overall'] else 'UNHEALTHY'}\n")
    for service, info in health["services"].items():
        icon = "OK" if info["healthy"] else "FAIL"
        print(f"  [{icon}] {service}: {info['status']}")
    print()
    return health["overall"]


def main():
    parser = argparse.ArgumentParser(
        description="Job Search AI Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m src.main --run-once
  python -m src.main --schedule 07:00
  python -m src.main --health-check
  python -m src.main --api --port 8000
  python -m src.main --api --debug
        """,
    )
    parser.add_argument("--run-once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--schedule", type=str, default="07:00", help="Daily schedule time HH:MM (default 07:00)")
    parser.add_argument("--health-check", action="store_true", help="Run health check and exit")
    parser.add_argument("--api", action="store_true", help="Start the REST API server")
    parser.add_argument("--port", type=int, default=8000, help="API server port (default 8000)")
    parser.add_argument("--debug", action="store_true", help="Enable API debug/reload")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose or args.debug:
        settings.log_level = "DEBUG"
        setup_logging()

    if args.api:
        api.run(host="0.0.0.0", port=args.port, debug=args.debug)
        return

    if args.health_check:
        sys.exit(0 if print_health() else 1)

    if args.run_once:
        sys.exit(0 if run_once() else 1)

    run_scheduled(args.schedule)


if __name__ == "__main__":
    main()
