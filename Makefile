.PHONY: up down test lint seed migrate

COMPOSE = docker compose
SOLO = $(COMPOSE) run --rm --no-deps

up:
	@test -f .env || cp .env.example .env
	$(COMPOSE) up --build -d
	@echo "Frontend: http://localhost:5173  Backend: http://localhost:8000/docs  Chatbot: http://localhost:8001/docs"

down:
	$(COMPOSE) down

test:
	$(SOLO) backend pytest
	$(SOLO) chatbot pytest
	$(SOLO) frontend npm test

lint:
	$(SOLO) backend sh -c "ruff check . && ruff format --check ."
	$(SOLO) chatbot sh -c "ruff check . && ruff format --check ."
	$(SOLO) frontend npm run lint

migrate:
	$(COMPOSE) exec backend alembic upgrade head

seed:
	$(COMPOSE) exec backend python -m scripts.seed
