import os
import logging

# 로그 설정
def setup_logger(name:str="crawler" , file_name: str = "crawling.log"):
    """
    Sets up a logger with different levels for file and console handlers.
    - File handler logs ERROR and higher level messages.
    - Console handler logs WARNING and higher level messages.
    """
    # 로거 인스턴스를 가져옵니다. 고정된 이름을 사용하여 항상 동일한 로거를 사용합니다.
    logger = logging.getLogger(name)

    # 핸들러가 이미 설정된 경우, 중복 로깅을 방지하기 위해 기존 로거를 반환합니다.
    if logger.hasHandlers():
        return logger

    # 로거가 처리할 최저 로그 레벨을 설정합니다. 핸들러 레벨 중 가장 낮은 값으로 설정해야 합니다.
    logger.setLevel(logging.INFO)  # WARNING < ERROR

    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, file_name)
    
    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 콘솔 출력을 위한 StreamHandler 설정 (WARNING 레벨 이상)
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    
    # 파일 저장을 위한 FileHandler 설정 (ERROR 레벨 이상)
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.ERROR)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger