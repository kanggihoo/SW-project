#!/bin/bash

# 서버 실행 스크립트
# FastAPI 서버와 Streamlit 앱을 iTerm vertical 분할에서 실행

echo "🚀 Starting FastAPI server and Streamlit app in iTerm vertical split..."

# 프로젝트 루트 디렉토리 경로
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

echo "📁 Project directory: $PROJECT_DIR"

# iTerm 창 ID를 저장할 파일
WINDOW_ID_FILE="/tmp/agent_service_window_id.txt"

# iTerm에서 새 창을 만들고 vertical 분할하여 서버 실행
echo "📡 Creating iTerm window with vertical split..."
WINDOW_ID=$(osascript -e "
tell application \"iTerm\"
    create window with default profile
    set windowId to id of current window
    tell current session of current window
        set name to \"FastAPI Server\"
        write text \"cd '$PROJECT_DIR' && . ./.venv/bin/activate && echo '🚀 FastAPI Server Terminal' && uv run python3 src/run_server.py\"
    end tell
    return windowId
end tell
")

# 창 ID를 파일에 저장
echo "$WINDOW_ID" > "$WINDOW_ID_FILE"

# # 잠시 대기
# sleep 2

# # vertical 분할 생성
# echo "🎨 Creating vertical split..."
# osascript -e "
# tell application \"iTerm\"
#     tell current session of current window
#         split vertically with default profile
#     end tell
# end tell
# "

# # 잠시 대기
# sleep 1

# # 분할된 세션에서 Streamlit 실행
# echo "🎨 Starting Streamlit in split session..."
# osascript -e "
# tell application \"iTerm\"
#     set splitSession to second session of current tab of current window
#     tell splitSession
#         set name to \"Streamlit App\"
#         write text \"cd '$PROJECT_DIR' && . ./.venv/bin/activate && echo '🎨 Streamlit App Terminal' && streamlit run src/streamlit_app.py\"
#     end tell
# end tell
# "

# echo "✅ Both servers are starting in iTerm vertical split..."
# echo ""
# echo "📡 FastAPI server is running in left panel"
# echo "🎨 Streamlit app is running in right panel"
# echo ""
# echo "💡 To stop servers, close the iTerm window or use: make stop-servers"
