.PHONY: run-servers

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
