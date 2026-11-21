#!/bin/bash
# PhotoParser API Migration Script
# 
# Usage:
#   ./scripts/migrate.sh <command> [options]
#
# Commands:
#   upgrade [revision]  - Upgrade database to specified revision (default: head)
#   downgrade [n]       - Downgrade database by n revisions (default: 1)
#   current             - Show current database revision
#   history             - Show migration history
#   check               - Check database schema against models
#   generate <message>  - Generate new migration (requires DATABASE_URL)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
MIGRATION_DIR="$PROJECT_DIR/migrations"

# Check if running in nix-shell or use nix-shell wrapper
if command -v alembic &> /dev/null; then
    ALEMBIC_CMD="alembic"
else
    echo "⚠️  Alembic not found in PATH. Using nix-shell..."
    ALEMBIC_CMD="nix-shell -p python3Packages.alembic python3Packages.sqlalchemy python3Packages.psycopg2 python3Packages.pg8000 --run 'alembic'"
fi

cd "$PROJECT_DIR"

case "${1:-upgrade}" in
    upgrade)
        REVISION="${2:-head}"
        echo "🔄 Upgrading database to revision: $REVISION"
        if [[ "$ALEMBIC_CMD" == "nix-shell"* ]]; then
            eval "$ALEMBIC_CMD upgrade $REVISION"
        else
            eval "$ALEMBIC_CMD upgrade $REVISION"
        fi
        echo "✅ Database upgraded successfully"
        ;;
    
    downgrade)
        REVISION="${2:-1}"
        echo "⬇️  Downgrading database by $REVISION revision(s)"
        if [[ "$ALEMBIC_CMD" == "nix-shell"* ]]; then
            eval "$ALEMBIC_CMD downgrade $REVISION"
        else
            eval "$ALEMBIC_CMD downgrade $REVISION"
        fi
        echo "✅ Database downgraded successfully"
        ;;
    
    current)
        echo "📍 Current database revision:"
        if [[ "$ALEMBIC_CMD" == "nix-shell"* ]]; then
            eval "$ALEMBIC_CMD current"
        else
            eval "$ALEMBIC_CMD current"
        fi
        ;;
    
    history)
        echo "📜 Migration history:"
        if [[ "$ALEMBIC_CMD" == "nix-shell"* ]]; then
            eval "$ALEMBIC_CMD history --verbose"
        else
            eval "$ALEMBIC_CMD history --verbose"
        fi
        ;;
    
    check)
        echo "🔍 Checking database schema against models..."
        if [[ "$ALEMBIC_CMD" == "nix-shell"* ]]; then
            eval "$ALEMBIC_CMD upgrade head"
            eval "$ALEMBIC_CMD downgrade -1"
        else
            eval "$ALEMBIC_CMD upgrade head"
            eval "$ALEMBIC_CMD downgrade -1"
        fi
        echo "✅ Schema check completed"
        ;;
    
    generate)
        MESSAGE="${2:-}"
        if [ -z "$MESSAGE" ]; then
            echo "❌ Please provide a migration message: ./scripts/migrate.sh generate 'your message'"
            exit 1
        fi
        
        # Check if DATABASE_URL is set
        if [ -z "$DATABASE_URL" ]; then
            echo "⚠️  DATABASE_URL not set. Generating migration without autogenerate."
            echo "   Set DATABASE_URL to use: alembic revision --autogenerate -m '$MESSAGE'"
            eval "$ALEMBIC_CMD revision -m \"$MESSAGE\""
        else
            echo "📝 Generating migration with autogenerate for: '$MESSAGE'"
            eval "$ALEMBIC_CMD revision --autogenerate -m \"$MESSAGE\""
        fi
        echo "✅ Migration generated successfully"
        ;;
    
    help|--help|-h)
        echo "PhotoParser API Migration Script"
        echo ""
        echo "Usage: $0 <command> [options]"
        echo ""
        echo "Commands:"
        echo "  upgrade [revision]  - Upgrade database to specified revision (default: head)"
        echo "  downgrade [n]       - Downgrade database by n revisions (default: 1)"
        echo "  current             - Show current database revision"
        echo "  history             - Show migration history"
        echo "  check               - Check database schema against models"
        echo "  generate <message>  - Generate new migration (requires DATABASE_URL for autogenerate)"
        echo ""
        echo "Environment Variables:"
        echo "  DATABASE_URL - PostgreSQL connection string (e.g., postgresql+pg8000://user:pass@host:port/db)"
        echo ""
        echo "Examples:"
        echo "  $0 upgrade"
        echo "  $0 downgrade 1"
        echo "  $0 generate 'add user table'"
        echo "  DATABASE_URL=... $0 generate 'add user table'"
        ;;
    
    *)
        echo "❌ Unknown command: $1"
        echo "Run '$0 help' for usage information."
        exit 1
        ;;
esac
