# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DeepSOC is an AI-powered Security Operations Center (SOC) that uses a multi-agent architecture to automate security incident response. The system combines advanced AI technology with traditional security operations tools to handle security events automatically.

## Architecture

### Multi-Agent System
The system uses a distributed multi-agent architecture with specialized roles:

- **Captain** (`_captain`): Strategic decision-making and overall coordination
- **Manager** (`_manager`): Task assignment and coordination  
- **Operator** (`_operator`): Execution of specific security operations
- **Executor** (`_executor`): Integration with external tools and systems
- **Expert** (`_expert`): Specialized security expertise and recommendations

### Core Components

- **Web Application**: Flask-based web interface with real-time WebSocket communication
- **Database Models**: SQLAlchemy models for events, tasks, users, messages, and execution tracking
- **Message Queue**: RabbitMQ for inter-agent communication
- **SOAR Integration**: Connects to Security Orchestration, Automation and Response platforms
- **AI Services**: OpenAI integration for intelligent decision-making
- **Engineer Chat System**: Async AI assistant for human engineers with real-time messaging

### Key Directories

- `app/`: Main application code
  - `controllers/`: Web controllers for different endpoints
  - `models/`: Database models and schemas
  - `services/`: Business logic for each agent role
  - `templates/`: HTML templates for web interface
  - `static/`: Frontend assets (CSS, JS, images)
  - `utils/`: Utility functions and helpers
- `migrations/`: Database migration files
- `tools/`: Administrative and utility scripts
- `docs/`: Documentation and configuration guides

## Development Commands

### Environment Setup
```bash
# Create virtual environment
virtualenv venv
source venv/bin/activate  # Linux/Mac
# .\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp sample.env .env
# Edit .env with your configuration
```

### Database Operations
```bash
# Initialize database (WARNING: This will delete all existing data)
python main.py -init

# Run database migrations
flask db upgrade
```

### Starting Services
```bash
# Start main web service
python main.py

# Start individual agents (use separate terminals)
python main.py -role _captain
python main.py -role _manager
python main.py -role _operator
python main.py -role _executor
python main.py -role _expert

# Start all agents at once
python tools/run_all_agents.py
```

### Administrative Tasks
```bash
# Create admin user
python tools/create_admin.py

# List all users
python tools/list_users.py

# Reset admin password
python tools/reset_admin_password.py

# Initialize default prompts
python tools/init_prompts.py
```

## Development Guidelines

### File Modification Best Practices
- For major functionality changes, create new files instead of modifying large existing files to reduce merge conflicts
- Record all changes in `changelog.md`
- Update `DeepSOC Architecture.md` for architectural changes
- Sync `.env` changes with `sample.env`

### Frontend Development
- Use separate CSS files to avoid style conflicts during multi-developer work
- Maintain consistency with existing UI elements and styling
- Follow the existing Bootstrap-based design system

### Testing and Tools
- Create test files in the `test/` directory
- Place temporary tools in the `tools/` directory
- Include functional descriptions and execution methods in test programs

## Database Schema

Key models include:
- `User`: User management with roles and authentication
- `Event`: Security events with status tracking and round-based processing
- `Task`: Individual tasks assigned to agents
- `Message`: Inter-agent communication messages and engineer chat conversations
- `Execution`: Task execution tracking and results
- `Summary`: Round-based processing summaries
- `Prompt`: AI prompt templates
- `GlobalSettings`: System configuration

### Message Table Extensions
The unified Message table supports both agent communications and engineer chat:

#### Agent Messages (Default)
- `message_category = 'agent'`
- `message_from`: Agent role (`_captain`, `_manager`, etc.)
- `message_type`: Communication type (`llm_request`, `task_assignment`, etc.)

#### Engineer Chat Messages
- `message_category = 'engineer_chat'`
- `chat_session_id`: Session identifier for conversation grouping
- `sender_type`: Message sender (`'user'`, `'ai'`, `'system'`)
- `event_summary_version`: Hash of event summary for context tracking

## API Endpoints

### Core System APIs
- `/api/event/create`: Create new security events
- `/api/auth/login`: User authentication
- WebSocket endpoints for real-time communication
- Various management endpoints for users, prompts, and system state

### Engineer Chat APIs
- `/api/engineer-chat/send`: Send message to AI assistant (async processing)
- `/api/engineer-chat/history`: Retrieve conversation history for current session
- `/api/engineer-chat/new-session`: Create new chat session when round limit reached
- `/api/engineer-chat/status`: Get current session status and metadata

## External Dependencies

### Required Services
- **MySQL**: Primary database (SQLite for development)
- **RabbitMQ**: Message queue for agent communication
- **OpenAI API**: AI capabilities
- **SOAR Platform**: Security orchestration (optional, OctoMation recommended)

### Key Python Libraries
- Flask: Web framework
- SQLAlchemy: Database ORM
- Flask-SocketIO: WebSocket support
- Pika: RabbitMQ client
- OpenAI: AI integration
- Alembic: Database migrations

## Configuration

The system uses environment variables for configuration. Key settings include:
- Database connection strings
- RabbitMQ connection parameters
- OpenAI API keys
- SOAR integration settings
- Security and authentication settings

Always update `sample.env` when adding new configuration options.

## Engineer Chat System

### Overview
The Engineer Chat System provides an AI assistant for human security engineers working on security events. It operates independently from the multi-agent system and uses an asynchronous messaging architecture for optimal user experience.

### Architecture Design

#### System Isolation
- **Complete separation** from Agent workflows to prevent interference
- **Independent AI context** built from event summaries and chat history
- **Unified Message table** for storage while maintaining logical separation

#### Asynchronous Processing Model
```
User Input (@AI message)
    ↓
HTTP API (immediate response ~10ms)
    ├→ Save user message to database
    ├→ WebSocket broadcast user message
    ├→ Start background AI processing thread
    └→ Return success immediately
    
Background Thread (3-5 seconds)
    ├→ Build conversation context
    ├→ Call AI service
    ├→ Save AI response to database
    └→ WebSocket broadcast AI response
```

### Key Features

#### User Experience Optimizations
- **Instant Response**: Button releases immediately after sending
- **Real-time Display**: User messages appear instantly via WebSocket
- **AI Status Indicator**: Animated "thinking" indicator during AI processing
- **Continuous Interaction**: Users can send multiple messages without waiting
- **Error Recovery**: Graceful handling of AI service failures

#### Technical Implementation

##### Database Schema Extensions
```sql
-- Extended Message table fields for engineer chat
message_category VARCHAR(32) DEFAULT 'agent'  -- 'agent' or 'engineer_chat'
chat_session_id VARCHAR(64)                   -- Engineer chat session ID
sender_type VARCHAR(32)                       -- 'user', 'ai', 'agent'
event_summary_version VARCHAR(64)             -- Event summary version hash
```

##### API Endpoints
- `POST /api/engineer-chat/send`: Send message to AI assistant
- `GET /api/engineer-chat/history`: Get conversation history
- `POST /api/engineer-chat/new-session`: Create new chat session
- `GET /api/engineer-chat/status`: Get current chat status

##### Frontend Integration
- **Trigger Pattern**: Messages starting with `@AI` activate engineer chat mode
- **Visual Distinction**: Engineer chat messages have unique styling
- **State Management**: Thinking indicators and message status tracking
- **WebSocket Handling**: Real-time message updates and status changes

### Session Management

#### Session Creation
- Sessions are created per event-user combination
- Session IDs use format: `chat_{hash}_{uuid}` (max 64 chars)
- Automatic session detection for continuing conversations

#### Round Limiting
- Maximum 10 conversation rounds per session
- Automatic prompt for new session when limit reached
- Context preservation across session boundaries

#### Context Building
- Includes latest event summary and updates
- Maintains conversation history (last 20 messages)
- Provides event metadata and current status

### Development Guidelines

#### Adding Engineer Chat Features
1. **Extend Controller**: Add methods to `EngineerChatController`
2. **Update API**: Add routes to `engineer_chat_api.py`
3. **Frontend Integration**: Update `warroom.js` for UI interactions
4. **WebSocket Events**: Handle real-time message broadcasting via RabbitMQ

#### Performance Considerations
- **Async Processing**: Never block main thread for AI calls
- **Database Optimization**: Index chat_session_id and message_category
- **Memory Management**: Daemon threads for background processing
- **Error Handling**: Graceful degradation when AI services unavailable
- **RabbitMQ Connections**: Use connection pooling for high-volume scenarios

#### Testing Engineer Chat
```bash
# Test API endpoints
python tools/test_engineer_chat.py

# Test frontend integration
# 1. Login to warroom interface
# 2. Send message with @AI prefix
# 3. Verify immediate button response
# 4. Observe AI thinking indicator
# 5. Confirm AI response via WebSocket (should be instant)

# Test RabbitMQ message flow
# 1. Monitor server logs for RabbitMQ publish/consume messages
# 2. Check browser console for WebSocket message reception
# 3. Verify message fields: id, message_id, message_from, message_type
```

#### Implementation Success Criteria ✅
**Real-time Engineer Chat (Completed 2025-07-05)**:
1. ✅ **Unified Architecture**: Engineer chat uses same RabbitMQ flow as Agent system
2. ✅ **Instant Delivery**: AI responses appear immediately via WebSocket
3. ✅ **Field Compatibility**: All required message fields properly mapped
4. ✅ **Error Resolution**: Fixed undefined values in frontend message processing
5. ✅ **Architecture Documentation**: Complete technical implementation guide

### Message Flow Architecture

#### Unified Real-time Messaging Architecture
**CRITICAL**: Both Agent messages and Engineer Chat messages now use the same unified architecture for real-time WebSocket delivery.

#### Standard Agent Messages
```
Agent Service → RabbitMQ Publisher → RabbitMQ Exchange → main.py Consumer → WebSocket → Frontend
```

#### Engineer Chat Messages (Unified Architecture)
```
User Input → API (immediate) → Database → WebSocket → Frontend
                ↓
Background Thread → AI Service → Database → RabbitMQ Publisher → RabbitMQ Exchange → main.py Consumer → WebSocket → Frontend
```

#### Key Architectural Components

**RabbitMQ Integration**:
- **Exchange**: `deepsoc_notifications_exchange` (topic type)
- **Queue**: `deepsoc_frontend_notifications_queue`
- **Routing Key Pattern**: `notifications.frontend.{event_id}.{message_from}.{message_type}`

**Message Flow Details**:
1. **Agent/Engineer Chat** creates message in database
2. **RabbitMQPublisher** publishes message to exchange with routing key
3. **main.py Consumer** (`handle_mq_message_to_socketio`) receives message
4. **Consumer** emits message via WebSocket to event room
5. **Frontend** receives real-time message update

**Implementation Location**:
- **Publisher**: `app/utils/mq_utils.py` - `RabbitMQPublisher` class
- **Consumer**: `main.py` - `handle_mq_message_to_socketio()` function
- **Engineer Chat Integration**: `app/controllers/engineer_chat_controller.py` - `_broadcast_message_via_websocket()` method

### Security Considerations
- **Authentication**: JWT-based user verification
- **Session Isolation**: Users can only access their own chat sessions
- **Content Filtering**: AI responses are logged and auditable
- **Rate Limiting**: Session round limits prevent abuse

### Troubleshooting

#### Common Issues
1. **Button stuck "sending"**: Check WebSocket connection and API response handling
2. **AI not responding**: Verify background thread processing and AI service availability
3. **Messages not displaying**: Check WebSocket event handlers and message deduplication
4. **Session errors**: Verify database schema and session ID generation

#### Debug Commands
```bash
# Check engineer chat database records
SELECT * FROM messages WHERE message_category = 'engineer_chat';

# Monitor WebSocket events
# Check browser console for WebSocket event logs

# Test AI service integration
python -c "from app.services.llm_service import call_llm; print(call_llm('test', 'hello'))"

# Test RabbitMQ connectivity (critical for real-time messaging)
python -c "from app.utils.mq_utils import RabbitMQPublisher; p = RabbitMQPublisher(); print('RabbitMQ connection successful')"

# Monitor RabbitMQ message flow
# Check server logs for: "MQ Consumer: Relaying message" and "工程师对话] 使用RabbitMQ发送消息"
```

#### Critical Architecture Notes
**Real-time Message Delivery Requirements**:
1. **RabbitMQ Service**: Must be running and accessible
2. **main.py Consumer**: Must be active to relay messages from RabbitMQ to WebSocket
3. **Network Connectivity**: RabbitMQ, Database, and WebSocket connections all required
4. **Message Format**: Engineer chat messages use same `message.to_dict()` format as Agent messages

**Message Field Requirements** (Critical for Frontend Compatibility):
- **Database ID**: `id` field (auto-increment primary key)
- **Unique Identifier**: `message_id` field (UUID string)
- **Message Source**: `message_from` field (sender identification)
- **Message Type**: `message_type` field (e.g., 'chat', 'llm_request')
- **Category**: `message_category` field ('agent' or 'engineer_chat')

**Frontend JavaScript Compatibility**:
- Uses `message.message_id || message.id` for unique key generation
- Requires `message_from` field for source identification
- Engineer chat handled via `message_category === 'engineer_chat'`
- AI responses use `sender_type === 'ai'` for styling

**Successful Implementation Verification** ✅:
- **2025-07-05**: Unified RabbitMQ architecture successfully implemented
- **Real-time Delivery**: Engineer chat messages now delivered instantly via WebSocket
- **Architecture Parity**: Engineer chat uses identical message flow as Agent system
- **Field Compatibility**: All message fields correctly mapped for frontend processing

**If Real-time Messages Not Working**:
1. Check RabbitMQ service status
2. Verify main.py consumer thread is running
3. Check routing key format matches: `notifications.frontend.{event_id}.{message_from}.{message_type}`
4. Verify WebSocket room membership (users must join event rooms)
5. Ensure message contains required fields: `id`, `message_id`, `message_from`, `message_type`

## Important Notes
- This product is developed by Chinese engineers, so when you chat with me, please use Chinese.
- Output some text for me to update changelog each time you finish a feature.