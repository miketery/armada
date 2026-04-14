#!/bin/bash

uv run alembic downgrade -1
uv run alembic upgrade head
