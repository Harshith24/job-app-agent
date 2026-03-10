#!/usr/bin/env python3
"""Job Search AI Agent - Main entry point"""

import argparse
import logging
import signal
import sys
import time
from datetime import datetime

from src.config.settings import config
from src.core.agent import JobSearchAgent
from src.api.server import JobAgentAPI

logger = logging.getLogger(__name__)

class JobAgentApp:
    """Main application class"""

    def __init__(self):
        self.agent = JobSearchAgent()
        self.running = False
        self.setup_signal_handlers()

    def setup_signal_handlers(self):
        """Setup graceful shutdown handlers"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False

    def run_once(self):
        """Run a single job search cycle"""
        logger.info("Running single job search cycle")
        try:
            result = self.agent.run_search_cycle()
            if result:
                logger.info(f"Cycle completed successfully. Output: {result}")
                return True
            else:
                logger.error("Cycle completed with errors")
                return False
        except Exception as e:
            logger.error(f"Cycle failed: {e}")
            return False

    def run_scheduled(self, schedule_time: str = "07:00"):
        """Run scheduled job search cycles"""
        import schedule

        logger.info(f"Starting scheduled runs at {schedule_time} daily")

        # Schedule the job
        schedule.every().day.at(schedule_time).do(self._scheduled_run)

        self.running = True
        logger.info("Job agent running. Press Ctrl+C to stop.")

        # Run immediately on startup
        self._scheduled_run()

        # Main loop
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                time.sleep(60)

        logger.info("Job agent stopped")

    def _scheduled_run(self):
        """Wrapper for scheduled runs"""
        try:
            logger.info("Starting scheduled job search cycle")
            result = self.agent.run_search_cycle()
            if result:
                logger.info(f"Scheduled cycle completed. Output: {result}")
            else:
                logger.warning("Scheduled cycle completed with warnings")
        except Exception as e:
            logger.error(f"Scheduled cycle failed: {e}")

    def health_check(self):
        """Perform and display health check"""
        logger.info("Performing health check...")
        health = self.agent.health_check()

        print("\n=== Health Check Results ===")
        print(f"Overall Status: {'HEALTHY' if health['overall'] else 'UNHEALTHY'}")

        print("\nService Status:")
        for service, status in health['services'].items():
            status_icon = "✅" if status['healthy'] else "❌"
            print(f"  {status_icon} {service}: {status['status']}")

        print()
        return health['overall']

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Job Search AI Agent',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run once and exit
  python -m src.main --run-once

  # Run scheduled daily at 7 AM
  python -m src.main --schedule 07:00

  # Health check
  python -m src.main --health-check

  # Start API server
  python -m src.main --api --port 8000

  # Start API server with debug
  python -m src.main --api --debug
        """
    )

    parser.add_argument(
        '--run-once',
        action='store_true',
        help='Run one job search cycle and exit'
    )

    parser.add_argument(
        '--schedule',
        type=str,
        default='07:00',
        help='Daily schedule time (HH:MM format, default: 07:00)'
    )

    parser.add_argument(
        '--health-check',
        action='store_true',
        help='Perform health check and exit'
    )

    parser.add_argument(
        '--api',
        action='store_true',
        help='Start REST API server'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='API server port (default: 8000)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug mode for API server'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    # Configure logging level
    if args.verbose or args.debug:
        config.app.log_level = 'DEBUG'
        config._setup_logging()

    # Run API server
    if args.api:
        api = JobAgentAPI()
        api.run(port=args.port, debug=args.debug)
        return

    # Run CLI app
    app = JobAgentApp()

    if args.health_check:
        healthy = app.health_check()
        sys.exit(0 if healthy else 1)

    elif args.run_once:
        success = app.run_once()
        sys.exit(0 if success else 1)

    else:
        app.run_scheduled(args.schedule)

if __name__ == '__main__':
    main()