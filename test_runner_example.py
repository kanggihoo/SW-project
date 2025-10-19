# ssh -i ~/.ssh/ssh-aws-aiserver-ec2.pem -L 5430:langgraph.cd6cwm4qy5ph.ap-northeast-2.rds.amazonaws.com:5432 -N ec2-user@3.36.171.231
import psycopg
from psycopg.rows import dict_row  # 딕셔너리 형태로 결과를 받기 위해 import

DB_HOST = '127.0.0.1'
DB_PORT = '5430'  # SSH 터널링에 사용한 로컬 포트

# 아래 정보는 EC2 환경과 동일
DB_USER = 'postgres'
DB_PASSWORD = 'Kk529021'
DB_NAME = 'postgres'


# 접속 정보를 하나의 문자열(DSN)로 만듭니다.
conn_info = f'host={DB_HOST} user={DB_USER} password={DB_PASSWORD} dbname={DB_NAME} port={DB_PORT}'


def get_connection():
    """PostgreSQL 데이터베이스 연결을 생성하고 반환하는 함수"""
    try:
        # row_factory를 통해 결과를 딕셔너리로 받도록 설정
        connection = psycopg.connect(conn_info, row_factory=dict_row)
        print('✅ PostgreSQL 데이터베이스 연결 성공!')
        return connection
    except psycopg.Error as e:
        print(f'❌ PostgreSQL 데이터베이스 연결 실패: {e}')
        return None


if __name__ == '__main__':
    conn = get_connection()
    if conn:
        try:
            # with 문을 사용하면 cursor와 connection이 자동으로 닫힙니다.
            with conn.cursor() as cur:
                # 간단한 쿼리 실행 예제
                cur.execute('SELECT NOW();')
                result = cur.fetchone()
                print('쿼리 실행 결과:', result)
        finally:
            # with 문을 사용했더라도, connection 객체 자체는 닫아주는 것이 좋습니다.
            conn.close()
            print('데이터베이스 연결 해제')
