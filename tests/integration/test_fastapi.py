import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, MagicMock
import json
from app.main import app

import uvicorn

def test_main():
    uvicorn.run(app, host="0.0.0.0" , port=8000 )


class TestFastAPIApp:
    """FastAPI 애플리케이션 테스트 클래스"""
    
    @pytest.fixture
    def client(self):
        """테스트용 FastAPI 클라이언트"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_dependencies(self):
        """의존성 모킹을 위한 fixture"""
        with patch('app.main.get_fashion_repo') as mock_repo, \
             patch('app.main.get_aws_manager') as mock_aws:
            
            # FashionRepository 모킹
            mock_repo_instance = Mock()
            mock_repo_instance.close_connection = Mock()
            mock_repo.return_value = mock_repo_instance
            
            # AWSManager 모킹
            mock_aws_instance = Mock()
            mock_aws_instance.close_connection = Mock()
            mock_aws.return_value = mock_aws_instance
            
            yield {
                'fashion_repo': mock_repo_instance,
                'aws_manager': mock_aws_instance
            }
    
    def test_root_endpoint(self, client):
        """루트 엔드포인트 테스트"""
        response = client.get("/")
        
        assert response.status_code == 200
        assert response.json() == {"message": "Welcome to the Clothing Recommendation API"}
    
    def test_app_title_and_version(self, client):
        """애플리케이션 메타데이터 테스트"""
        response = client.get("/docs")
        
        assert response.status_code == 200
        # OpenAPI 문서가 생성되었는지 확인
        assert "Clothing Recommendation API" in response.text
    
    def test_api_router_included(self, client):
        """API 라우터가 포함되었는지 테스트"""
        # API 라우터의 엔드포인트가 존재하는지 확인
        response = client.get("/api/v1/")
        # 404가 나와야 함 (루트 엔드포인트가 없으므로)
        assert response.status_code == 404
    
    def test_websocket_router_included(self, client):
        """WebSocket 라우터가 포함되었는지 테스트"""
        # WebSocket 엔드포인트가 존재하는지 확인
        response = client.get("/ws")
        # WebSocket은 GET 요청으로 접근할 수 없으므로 405 Method Not Allowed가 나와야 함
        assert response.status_code == 405
    
    @patch('app.main.logger')
    def test_lifespan_startup_success(self, mock_logger, mock_dependencies):
        """lifespan 시작 성공 테스트"""
        # lifespan 컨텍스트 매니저 테스트
        with app.router.lifespan_context(app):
            # 의존성이 정상적으로 초기화되었는지 확인
            mock_dependencies['fashion_repo'].close_connection.assert_not_called()
            mock_dependencies['aws_manager'].close_connection.assert_not_called()
        
        # 종료 시 close_connection이 호출되었는지 확인
        mock_dependencies['fashion_repo'].close_connection.assert_called_once()
        mock_dependencies['aws_manager'].close_connection.assert_called_once()
    
    @patch('app.main.logger')
    def test_lifespan_startup_with_exceptions(self, mock_logger, mock_dependencies):
        """lifespan 시작 시 예외 처리 테스트"""
        # 의존성 초기화 시 예외 발생 시뮬레이션
        with patch('app.main.get_fashion_repo', side_effect=Exception("DB Connection Error")), \
             patch('app.main.get_aws_manager', side_effect=Exception("AWS Connection Error")):
            
            with app.router.lifespan_context(app):
                # 예외가 발생해도 애플리케이션이 계속 실행되어야 함
                pass
            
            # 로그에 에러가 기록되었는지 확인
            mock_logger.error.assert_called()
    
    def test_exception_handlers_registered(self):
        """예외 핸들러가 등록되었는지 테스트"""
        # FastAPI 앱에 예외 핸들러가 등록되었는지 확인
        assert RequestValidationError in app.exception_handlers
        assert HTTPException in app.exception_handlers
    
    def test_app_metadata(self):
        """애플리케이션 메타데이터 확인"""
        assert app.title == "Clothing Recommendation API"
        assert app.description == "An API for clothing recommendations using LangGraph"
        assert app.version == "1.0.0"


class TestFastAPIEndpoints:
    """FastAPI 엔드포인트 테스트 클래스"""
    
    @pytest.fixture
    def client(self):
        """테스트용 FastAPI 클라이언트"""
        return TestClient(app)
    
    def test_root_endpoint_response_structure(self, client):
        """루트 엔드포인트 응답 구조 테스트"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        # 응답 구조 확인
        assert "message" in data
        assert isinstance(data["message"], str)
        assert "Clothing Recommendation API" in data["message"]
    
    def test_root_endpoint_content_type(self, client):
        """루트 엔드포인트 Content-Type 테스트"""
        response = client.get("/")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
    
    def test_nonexistent_endpoint(self, client):
        """존재하지 않는 엔드포인트 테스트"""
        response = client.get("/nonexistent")
        
        assert response.status_code == 404
    
    def test_method_not_allowed(self, client):
        """허용되지 않는 HTTP 메서드 테스트"""
        response = client.post("/")
        
        assert response.status_code == 405


class TestFastAPIDependencies:
    """FastAPI 의존성 테스트 클래스"""
    
    @patch('app.main.get_fashion_repo')
    @patch('app.main.get_aws_manager')
    def test_dependencies_initialization(self, mock_aws, mock_repo):
        """의존성 초기화 테스트"""
        # 의존성 함수들이 호출되었는지 확인
        mock_repo.assert_called()
        mock_aws.assert_called()
    
    @patch('app.main.logger')
    def test_dependency_error_handling(self, mock_logger):
        """의존성 에러 처리 테스트"""
        with patch('app.main.get_fashion_repo', side_effect=Exception("Test DB Error")), \
             patch('app.main.get_aws_manager', side_effect=Exception("Test AWS Error")):
            
            # lifespan 컨텍스트에서 에러가 발생해도 로깅되고 계속 진행되어야 함
            with app.router.lifespan_context(app):
                pass
            
            # 에러 로그가 기록되었는지 확인
            assert mock_logger.error.called


class TestFastAPIConfiguration:
    """FastAPI 설정 테스트 클래스"""
    
    def test_app_configuration(self):
        """애플리케이션 설정 확인"""
        # 기본 설정 확인
        assert app.title == "Clothing Recommendation API"
        assert app.description == "An API for clothing recommendations using LangGraph"
        assert app.version == "1.0.0"
        
        # lifespan이 설정되었는지 확인
        assert app.router.lifespan_context is not None
        
        # 예외 핸들러가 설정되었는지 확인
        assert len(app.exception_handlers) > 0
    
    def test_router_inclusion(self):
        """라우터 포함 확인"""
        # WebSocket 라우터가 포함되었는지 확인
        websocket_routes = [route for route in app.routes if hasattr(route, 'tags') and 'websocket' in route.tags]
        assert len(websocket_routes) > 0
        
        # API 라우터가 포함되었는지 확인
        api_routes = [route for route in app.routes if hasattr(route, 'tags') and 'api/v1' in route.tags]
        assert len(api_routes) > 0


# 필요한 import 추가
from fastapi.exceptions import RequestValidationError, HTTPException
