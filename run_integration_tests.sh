#!/bin/bash

# Script to run integration tests with PostgreSQL

set -e

echo "Starting PostgreSQL test database..."
docker-compose -f docker-compose.test.yml up -d

echo "Waiting for PostgreSQL to be ready..."
until docker exec ivd_middleware_test_db pg_isready -U postgres > /dev/null 2>&1; do
  echo "  Waiting..."
  sleep 2
done

echo "PostgreSQL is ready!"
echo ""
echo "Running integration tests..."
python3 -m pytest tests/integration/ -v --tb=short

echo ""
echo "Tests complete!"
echo ""
echo "To stop the test database, run:"
echo "  docker-compose -f docker-compose.test.yml down"
