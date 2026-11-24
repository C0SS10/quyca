import logging
import time

from quyca.repositories import search_work_filters_repository

logger = logging.getLogger(__name__)

"""Precomputes the filters of /search/works/filters without parameters (the whole works collection, ~7 min)
and stores them in the `filters` collection, so the endpoint answers with one read.

Run it after every ETL load and on deploy:
    make refresh-filters-dev | make refresh-filters-prod
    python -m quyca.jobs.refresh_filters
"""


def main() -> None:
    start = time.time()
    filters = search_work_filters_repository.compute_works_available_filters([])
    duration = time.time() - start
    search_work_filters_repository.save_global_works_filters(filters, duration)
    logger.info("works filters refreshed in %.0fs (%s)", duration, ", ".join(sorted(filters)))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    main()
