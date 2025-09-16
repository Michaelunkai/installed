# michael fedro's backup & restore tool (Web Version)

This is a complete web remake of the original PyQt5 desktop application, preserving all functionality while providing a modern web interface.

## 🚀 Quick Start

### Option 1: Auto-install and run
```bash
python main.py --install-deps
python main.py
```

### Option 2: Manual setup
```bash
# Install dependencies
pip install fastapi uvicorn[standard] requests websockets python-multipart

# Run the application
python main.py
```

The application will:
1. Start the backend server on `http://localhost:8000`
2. Start the frontend server on `http://localhost:3000`
3. Automatically open in your web browser

## 📁 Files Structure

- **`backend.py`** - FastAPI backend server with all original functionality
- **`frontend.html`** - Complete React frontend (single-file application)
- **`main.py`** - Launcher script that runs both servers

## ✨ Features Preserved

### 🔐 User Management
- Login system with username/password
- Admin privileges (username: "misha")
- User banning and session management
- Real-time user dashboard

### 🐳 Docker Integration
- Full Docker Hub integration
- Container management and operations
- Real-time sync progress
- Docker image pulling and running

### 🎮 Game Management
- Game library with images and metadata
- Tag-based organization system
- Search and filtering
- Bulk operations
- Game time integration (HowLongToBeat)

### 📂 Tab System
- Customizable tabs for organization
- Drag & drop support
- Tab exclusion settings
- Bulk move operations

### ⚙️ Advanced Features
- Custom command buttons
- Terminal integration
- File path browsing
- Recent destinations
- Missing image detection
- Real-time WebSocket updates

### 🎨 User Interface
- Responsive design
- Game background images
- Context menus
- Modal dialogs
- Real-time notifications
- Progress indicators

## 🖥️ Original vs Web Version

| Feature | Original (PyQt5) | Web Version |
|---------|------------------|-------------|
| User Interface | Desktop GUI | Modern Web UI |
| Cross-platform | Windows/Linux/Mac | Any Browser |
| Real-time Updates | Qt Signals | WebSockets |
| File Operations | Native dialogs | Web-based |
| Docker Integration | Direct WSL calls | API endpoints |
| Session Management | Local files | Web sessions |

## 🔧 Configuration

The application uses the same configuration files as the original:
- `user_session.json` - User session data
- `tag_settings.json` - Tag preferences and aliases
- `tabs_config.json` - Tab configuration
- `banned_users.json` - Banned users list
- `active_users.json` - Currently active users
- `custom_buttons.json` - Custom command buttons
- `recent_destinations.json` - Recent destination paths

## 🌐 Browser Compatibility

- ✅ Chrome/Chromium (Recommended)
- ✅ Firefox
- ✅ Edge
- ✅ Safari
- ⚠️ Internet Explorer (Limited support)

## 🚨 Requirements

- Python 3.7+
- Modern web browser
- WSL (for Docker operations on Windows)
- Docker (for container operations)

## 🛠️ Development

The application is built with:
- **Backend**: FastAPI + Python
- **Frontend**: React (via CDN) + TypeScript (Babel)
- **Real-time**: WebSockets
- **Styling**: Custom CSS with responsive design

## 📱 Mobile Support

The interface is responsive and works on mobile devices, though some features may have limited functionality on smaller screens.

## 🔒 Security Notes

- Admin functions require proper authentication
- Docker operations are restricted to authenticated users
- Session management includes automatic cleanup
- WebSocket connections are monitored

## ❓ Help

Run with `--help` for additional options:
```bash
python main.py --help
```

## 🐛 Troubleshooting

### Backend won't start
- Check if port 8000 is available
- Ensure all dependencies are installed
- Verify Python version (3.7+)

### Frontend won't load
- Check if port 3000 is available
- Ensure `frontend.html` exists
- Try refreshing the browser

### Docker operations fail
- Ensure WSL is installed and running
- Check Docker daemon status
- Verify network connectivity

---

**Note**: This web version maintains 100% feature parity with the original desktop application while providing the convenience and accessibility of a web interface.