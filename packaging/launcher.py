"""Windowed release entry point. Internal checks never change the production UI."""
import sys

from app.config.settings import APP_DATA_DIR
from app.utils.logging import configure_logging


if __name__ == "__main__":
    logger = configure_logging(APP_DATA_DIR / "logs")
    try:
        if len(sys.argv) == 3 and sys.argv[1] == "--release-check":
            from app.release_check import run
            raise SystemExit(run(sys.argv[2]))
        from app.main import main
        raise SystemExit(main())
    except Exception:
        logger.exception("Release startup failed")
        raise SystemExit(1)
