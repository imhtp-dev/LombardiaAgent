#!/bin/bash

# VM Setup Script for Pipecat Healthcare Agent
# Run this script on your Azure VM to set up the environment

echo "🚀 Setting up Pipecat Healthcare Agent on Azure VM..."

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install required system packages
echo "📦 Installing system dependencies..."
sudo apt install -y python3 python3-pip python3-venv git curl htop tree ffmpeg libsndfile1 portaudio19-dev

# Create application directory
APP_DIR="/home/$(whoami)/voilavoicebooking"
echo "📁 Application directory: $APP_DIR"

# Clone repository if not exists
if [ ! -d "$APP_DIR" ]; then
    echo "📥 Cloning repository..."
    git clone https://github.com/YOUR_USERNAME/voilavoicebooking.git $APP_DIR
else
    echo "📂 Directory already exists, updating..."
    cd $APP_DIR
    git pull origin main
fi

cd $APP_DIR

# Create virtual environment
echo "🐍 Setting up Python virtual environment..."
python3 -m venv env
source env/bin/activate

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Create logs directory
mkdir -p logs

# Create environment file (you'll need to add your API keys)
if [ ! -f ".env" ]; then
    echo "📝 Creating .env template..."
    cat > .env << 'EOL'
# Add your API keys here
CARTESIA_API_KEY=your_cartesia_key
DAILY_API_KEY=your_daily_key
OPENAI_API_KEY=your_openai_key
DEEPGRAM_API_KEY=your_deepgram_key
ELEVENLABS_API_KEY=your_elevenlabs_key
CERBA_CLIENT_ID=your_cerba_client_id
CERBA_CLIENT_SECRET=your_cerba_client_secret
CERBA_TOKEN_URL=https://cerbahc.auth.eu-central-1.amazoncognito.com/oauth2/token
CERBA_BASE_URL=https://3z0xh9v1f4.execute-api.eu-south-1.amazonaws.com/prod
SERVER_URL=http://YOUR_VM_IP:8000
EOL
    echo "⚠️  Please edit .env file and add your API keys!"
fi

# Create service management script
echo "🔧 Creating service management script..."
cat > manage-agent.sh << 'EOL'
#!/bin/bash

APP_DIR="/home/$(whoami)/voilavoicebooking"
cd $APP_DIR

case "$1" in
    start)
        echo "🚀 Starting Pipecat Healthcare Agent..."
        source env/bin/activate
        nohup python bot.py > logs/bot.log 2>&1 &
        echo $! > logs/bot.pid
        echo "✅ Agent started! PID: $(cat logs/bot.pid)"
        ;;
    stop)
        echo "🛑 Stopping Pipecat Healthcare Agent..."
        if [ -f logs/bot.pid ]; then
            kill $(cat logs/bot.pid) 2>/dev/null || echo "Process already stopped"
            rm logs/bot.pid
        fi
        pkill -f "python.*bot.py" || echo "No running processes found"
        echo "✅ Agent stopped"
        ;;
    restart)
        echo "🔄 Restarting Pipecat Healthcare Agent..."
        $0 stop
        sleep 3
        $0 start
        ;;
    status)
        echo "📊 Checking agent status..."
        if pgrep -f "python.*bot.py"; then
            echo "✅ Agent is running"
            ps aux | grep "python.*bot.py" | grep -v grep
            echo ""
            echo "📋 Recent logs:"
            tail -10 logs/bot.log 2>/dev/null || echo "No logs found"
        else
            echo "❌ Agent is not running"
        fi
        ;;
    logs)
        echo "📋 Showing recent logs..."
        tail -f logs/bot.log
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
EOL

chmod +x manage-agent.sh

echo ""
echo "🎉 Setup completed!"
echo ""
echo "Next steps:"
echo "1. Edit .env file and add your API keys"
echo "2. Update SERVER_URL in .env to your VM's public IP"
echo "3. Test the agent: ./manage-agent.sh start"
echo "4. Check status: ./manage-agent.sh status"
echo "5. View logs: ./manage-agent.sh logs"
echo ""
echo "Service management commands:"
echo "  ./manage-agent.sh start    - Start the agent"
echo "  ./manage-agent.sh stop     - Stop the agent"
echo "  ./manage-agent.sh restart  - Restart the agent"
echo "  ./manage-agent.sh status   - Check agent status"
echo "  ./manage-agent.sh logs     - View live logs"
echo ""