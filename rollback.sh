#!/bin/bash
# Rollback to previous deployment
# Usage: ./rollback.sh [backend|frontend|all]

COMPONENT=${1:-all}

echo "🔄 Rolling back: $COMPONENT"

case $COMPONENT in
  backend)
    echo "Rolling back backend to :backup tag..."
    docker tag rudyimhtpdev/voicebooking_piemo1:backup rudyimhtpdev/voicebooking_piemo1:latest
    docker-compose up -d --no-deps info-agent
    ;;
  frontend)
    echo "Rolling back frontend to :backup tag..."
    docker tag rudyimhtpdev/dashboard-frontend:backup rudyimhtpdev/dashboard-frontend:latest
    docker-compose up -d --no-deps dashboard-frontend
    ;;
  all)
    echo "Rolling back all services..."
    docker tag rudyimhtpdev/voicebooking_piemo1:backup rudyimhtpdev/voicebooking_piemo1:latest
    docker tag rudyimhtpdev/dashboard-frontend:backup rudyimhtpdev/dashboard-frontend:latest
    docker-compose up -d --no-deps info-agent dashboard-frontend
    ;;
  *)
    echo "Usage: ./rollback.sh [backend|frontend|all]"
    exit 1
    ;;
esac

echo "✅ Rollback complete"
echo "Checking status..."
docker-compose ps
