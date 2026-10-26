#!/bin/bash
# Test runner script: unit + integration tests with coverage.
# E2E tests need the app and a browser, so they run in Docker:
#   docker compose --profile e2e run --rm e2e

echo "🧪 Running MCP Server Tests"
echo "=========================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo "Running unit and integration tests with coverage..."
pytest tests/unit tests/integration --cov=app --cov-report=term-missing --cov-report=html

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed! Coverage report generated in htmlcov/${NC}"
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi

echo ""
echo "=========================="
echo "✨ Test run complete!"
echo "💡 E2E: docker compose --profile e2e run --rm e2e"
