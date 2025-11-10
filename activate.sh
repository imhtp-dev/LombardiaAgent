#!/bin/bash
# Healthcare Agent - Quick Environment Activation Script
#
# Usage:
#   source activate.sh          # Activate conda environment
#   ./activate.sh test          # Run orange_box test
#   ./activate.sh booking       # Run booking test
#   ./activate.sh greeting      # Run full flow

# Activate conda
eval "$(conda shell.bash hook)"
conda activate healthcare-agent

echo "✅ Conda environment 'healthcare-agent' activated"
echo "📂 Project: Healthcare Flow Bot (Pipecat Flows Italian)"
echo ""

# If script is sourced, just activate env and return
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    echo "💡 Quick commands:"
    echo "   python chat_test.py --start-node orange_box    # Test orange box flow"
    echo "   python chat_test.py --start-node booking       # Test booking flow"
    echo "   python chat_test.py                            # Full flow (greeting)"
    return
fi

# If script is executed, run tests based on argument
case "$1" in
    test|orange|orange_box)
        echo "🧪 Starting Orange Box flow test..."
        python chat_test.py --start-node orange_box
        ;;
    booking)
        echo "📅 Starting Booking flow test..."
        python chat_test.py --start-node booking
        ;;
    greeting|full)
        echo "👋 Starting full flow (greeting)..."
        python chat_test.py
        ;;
    *)
        echo "💡 Available commands:"
        echo "   source activate.sh          # Just activate environment"
        echo "   ./activate.sh test          # Run orange box test"
        echo "   ./activate.sh booking       # Run booking test"
        echo "   ./activate.sh greeting      # Run full flow"
        ;;
esac
