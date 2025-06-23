# SW-project


## Langfuse 로컬 환경 설정

이 프로젝트에서는 Langfuse를 사용하여 LLM 애플리케이션을 모니터링할 수 있습니다.

### Docker Compose로 Langfuse 실행

1. **Docker Compose 파일 다운로드 및 실행**:
   ```bash
   # Langfuse Docker Compose YAML 파일 다운로드
   curl -o docker-compose.yml https://raw.githubusercontent.com/langfuse/langfuse/main/docker-compose.yml
   
   # Docker Compose로 Langfuse 실행
   docker compose up 
   ```

2. **Langfuse 접속**:
   - 브라우저에서 `http://localhost:3000`으로 접속
   - 초기 설정을 완료하고 프로젝트를 생성

3. **환경 변수 설정**:
   ```bash
   # .env 파일 생성
   echo "LANGFUSE_SECRET_KEY=your-secret-key" >> .env
   echo "LANGFUSE_PUBLIC_KEY=your-public-key" >> .env
   echo "LANGFUSE_HOST=http://localhost:3000" >> .env
   ```

### Langfuse 중지
```bash
docker compose down
```

