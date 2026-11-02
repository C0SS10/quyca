up-dev:
	docker compose up -d --build dev
down-dev:
	docker compose rm -sf dev; docker rmi colav/quyca-dev:dev
logs-dev:
	docker compose logs -f dev
shell-dev:
	docker compose exec dev bash
build-dev:
	docker compose build dev
tests-dev: tests-unit-dev tests-feature-dev
tests-unit-dev:
	docker compose exec dev pytest tests/unit
tests-feature-dev:
	docker compose exec dev pytest tests/feature
coverage-dev:
	docker compose exec -e COVERAGE_FILE=/tmp/.coverage dev sh -c "pytest tests/unit --cov --cov-report= && pytest tests/feature --cov --cov-append --cov-report=term"
refresh-filters-dev:
	docker compose exec dev python -m quyca.jobs.refresh_filters

up-prod:
	docker compose up -d --build prod
down-prod:
	docker compose rm -sf prod; docker rmi colav/quyca-prod:latest
logs-prod:
	docker compose logs -f prod
shell-prod:
	docker compose exec prod bash
build-prod:
	docker compose build prod
tests-prod:
	docker compose exec prod pytest tests/unit
	docker compose exec prod pytest tests/feature
refresh-filters-prod:
	docker compose exec prod python -m quyca.jobs.refresh_filters
