"""
VLM 출력을 위한 기본 타입 정의 모듈
"""
from enum import Enum


class PrimaryColor(str, Enum):
    """대표 색상 (Level 1)"""
    WHITE = "화이트"
    GRAY = "그레이"
    BLACK = "블랙"
    RED = "레드"
    PINK = "핑크"
    YELLOW = "옐로우"
    ORANGE = "오렌지"
    GREEN = "그린"
    BLUE = "블루"
    PURPLE = "퍼플/바이올렛"
    BROWN = "브라운"
    BEIGE = "베이지/크림"
    DENIM = "데님"
    METALLIC = "메탈릭"
    MULTICOLOR = "멀티컬러"
    OTHER = "기타"


class ColorAttribute(str, Enum):
    """색상 속성 태그 (Level 2)"""
    # 명도
    BRIGHT = "밝은"
    DARK = "어두운"
    DEEP = "딥"
    
    # 채도
    VIVID = "선명한"
    MUTED = "흐릿한"
    PALE = "페일"
    GRAYISH = "그레이시"
    
    # 톤&느낌
    PASTEL = "파스텔"
    NEON = "네온"
    WARM = "웜톤"
    COOL = "쿨톤"
    NEUTRAL = "뉴트럴"
    SOFT = "소프트"


class Neckline(str, Enum):
    """상의 넥라인 타입"""
    ROUND = "라운드넥"
    V_NECK = "브이넥"
    U_NECK = "유넥"
    TURTLE = "터틀넥/폴라"
    COLLAR = "카라"
    HENLEY = "헨리넥"
    HOOD = "후드"
    SQUARE = "스퀘어넥"
    BOAT = "보트넥"


class SleeveLength(str, Enum):
    """상의 소매 길이 타입"""
    SLEEVELESS = "민소매"
    SHORT = "반소매"
    THREE_QUARTER = "5부/7부"
    LONG = "긴소매"


class PatternType(str, Enum):
    """상의 패턴 타입"""
    SOLID = "무지/솔리드"
    STRIPE = "스트라이프"
    CHECK = "체크"
    DOT = "도트"
    FLORAL = "플로럴"
    ANIMAL = "애니멀 프린트"
    PAISLEY = "페이즐리"
    ARGYLE = "아가일"
    GEOMETRIC = "기하학"
    TYPOGRAPHY = "타이포그래피/레터링"
    OTHER = "기타"


class ClosureType(str, Enum):
    """상의 여밈 방식 타입"""
    NONE = "여밈 없음"
    BUTTON = "버튼/단추"
    ZIPPER = "지퍼"
    SNAP = "스냅 버튼"
    STRING = "스트링/끈"


class FitType(str, Enum):
    """상의 핏 타입"""
    SLIM = "슬림 핏"
    REGULAR = "레귤러 핏/스탠다드 핏"
    OVERSIZED = "오버사이즈 핏"


class StyleTag(str, Enum):
    """의류 스타일 태그"""
    MODERN = "모던/미니멀"
    BASIC = "심플 베이직"
    CASUAL = "캐주얼"
    STREET = "스트릿"
    FORMAL = "포멀"
    SPORTY = "스포티/애슬레저"
    OUTDOOR = "아웃도어"
    VINTAGE = "레트로"
    UNIQUE = "유니크"


class TPOTag(str, Enum):
    """의류 TPO 태그"""
    DAILY = "데일리"
    OFFICE = "오피스/비즈니스"
    FORMAL = "격식/하객"
    DATE = "데이트/주말"
    TRAVEL = "여행/휴가"
    PARTY = "파티/모임"
    EXERCISE = "운동"
    HOME = "홈웨어/라운지"


