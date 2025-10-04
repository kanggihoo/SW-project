.PHONY: run-servers start-docker stop-docker start-cli stop-cli start-streamlit stop-streamlit

VENV_PYTHON:= .venv/bin/python3

run-servers:
	@echo "🚀 Starting servers in iTerm vertical split..."
	@./scripts/shell/run_server.sh

run:
	@echo "🚀 Starting servers in iTerm vertical split..."
	@./scripts/shell/run_server.sh
# 서버 중지 및 iTerm 창 닫기
stop-servers:
	@echo "🛑 Stopping servers..."
	@pkill -f "uv run python3 src/run_service.py" || true
	# @pkill -f "streamlit run src/streamlit_app.py" || true
	# @pkill -f "streamlit" || true
	@echo "✅ Servers stopped"
	@echo "🪟 Closing iTerm window..."
	@if [ -f "/tmp/agent_service_window_id.txt" ]; then \
		WINDOW_ID=$$(cat /tmp/agent_service_window_id.txt); \
		osascript -e "tell application \"iTerm\" to close window id $$WINDOW_ID" || true; \
		rm -f /tmp/agent_service_window_id.txt; \
	else \
		osascript -e 'tell application "iTerm" to close every window' || true; \
	fi
	@echo "✅ iTerm window closed"


test:
	@echo "🚀 Running tests..."
	@$(VENV_PYTHON) examples/query_analyzer/test_query_analyzer.py

# Docker Compose 관련 명령어
start-docker:
	@echo "🛑 Stopping local PostgreSQL service..."
	@brew services stop postgresql@17 || true
	@echo "🐳 Starting Docker Compose services..."
	@docker compose up 
	@echo "✅ Docker Compose services started"

stop-docker:
	@echo "🛑 Stopping Docker Compose services..."
	@docker compose down
	@echo "🔄 Starting local PostgreSQL service..."
	@brew services start postgresql@17
	@echo "✅ Docker Compose stopped and PostgreSQL restarted"

# CLI 실행 관련 명령어
# 사용법: make start-cli [DB=sqlite|postgres] [MT=langfuse|none] [ENV=production|development] [LOG=info|debug] [MODE=development|production]
# make start-cli DB=postgres ENV=development LOG=debug
start-cli:
	@echo "🚀 Starting CLI application in new iTerm window..."
	@DB_TYPE=$${DB:-sqlite}; \
	MONITOR_TYPE=$${MT:-langfuse}; \
	ENVIRONMENT=$${ENV:-production}; \
	LOG_LEVEL=$${LOG:-info}; \
	FASTAPI_MODE=$${MODE:-development}; \
	osascript \
		-e 'tell application "iTerm"' \
		-e 'set newWindow to (create window with default profile)' \
		-e 'tell current session of newWindow' \
		-e 'write text "cd $(PWD)"' \
		-e 'write text ". ./.venv/bin/activate"' \
		-e 'write text "python src/run_cli.py --database-type='$$DB_TYPE' --monitoring-type='$$MONITOR_TYPE' --environment='$$ENVIRONMENT' --log-level='$$LOG_LEVEL' --mode='$$FASTAPI_MODE'"' \
		-e 'end tell' \
		-e 'return id of newWindow' \
		-e 'end tell' > /tmp/cli_window_id.txt 2>&1; \
	WINDOW_ID=$$(cat /tmp/cli_window_id.txt 2>/dev/null | tr -d '\n\r' | grep -o '[0-9]*' | head -1); \
	if [ -n "$$WINDOW_ID" ]; then \
		echo "$$WINDOW_ID" > /tmp/cli_window_id.txt; \
		echo "✅ CLI application started in iTerm window (ID: $$WINDOW_ID)"; \
	else \
		echo "⚠️  CLI application started but could not capture window ID"; \
	fi

stop-cli:
	@echo "🛑 Stopping CLI application..."
	@pkill -f "python src/run_cli.py" || true
	@if [ -f "/tmp/cli_window_id.txt" ]; then \
		WINDOW_ID=$$(cat /tmp/cli_window_id.txt); \
		echo "🪟 Closing iTerm window (ID: $$WINDOW_ID)..."; \
		osascript -e "tell application \"iTerm\" to close window id $$WINDOW_ID" 2>/dev/null || true; \
		rm -f /tmp/cli_window_id.txt; \
	fi
	@echo "✅ CLI application stopped"

# Streamlit 서버 관련 명령어
start-streamlit:
	@echo "🚀 Starting Streamlit server in new iTerm window..."
	@osascript \
		-e 'tell application "iTerm"' \
		-e 'set newWindow to (create window with default profile)' \
		-e 'tell current session of newWindow' \
		-e 'write text "cd $(PWD)"' \
		-e 'write text ". ./.venv/bin/activate"' \
		-e 'write text "export PYTHONPATH=\"$$PYTHONPATH:$(PWD)\""' \
		-e 'write text "streamlit run gui/streamlit_app.py"' \
		-e 'end tell' \
		-e 'return id of newWindow' \
		-e 'end tell' > /tmp/streamlit_window_id.txt 2>&1
	@WINDOW_ID=$$(cat /tmp/streamlit_window_id.txt 2>/dev/null | tr -d '\n\r' | grep -o '[0-9]*' | head -1); \
	if [ -n "$$WINDOW_ID" ]; then \
		echo "$$WINDOW_ID" > /tmp/streamlit_window_id.txt; \
		echo "✅ Streamlit server started in iTerm window (ID: $$WINDOW_ID)"; \
	else \
		echo "⚠️  Streamlit server started but could not capture window ID"; \
	fi

stop-streamlit:
	@echo "🛑 Stopping Streamlit server..."
	@pkill -f "streamlit run gui/streamlit_app.py" || true
	@if [ -f "/tmp/streamlit_window_id.txt" ]; then \
		WINDOW_ID=$$(cat /tmp/streamlit_window_id.txt); \
		echo "🪟 Closing iTerm window (ID: $$WINDOW_ID)..."; \
		osascript -e "tell application \"iTerm\" to close window id $$WINDOW_ID" 2>/dev/null || true; \
		rm -f /tmp/streamlit_window_id.txt; \
	fi
	@echo "✅ Streamlit server stopped"
