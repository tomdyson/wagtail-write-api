.PHONY: migrate seed run

migrate:
	uv run python manage.py migrate

seed: migrate
	uv run python manage.py seed_demo

run: migrate
	uv run python manage.py runserver
