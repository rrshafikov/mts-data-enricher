from app.config import settings
from app.enricher import run_enrichment
from app.logging_setup import setup_logging


def main() -> None:
    setup_logging(settings.log_level)
    run_enrichment()


if __name__ == "__main__":
    main()
