"""
텍스트 이미지에서 추출되는 의류 정보 관련 Pydantic 모델 정의 모듈
"""

from typing import Annotated
from pydantic import BaseModel, Field, field_validator
import json
from typing import Union, Dict

# class FabricPropertiesInfo(BaseModel):
#     """원단 특성 및 착용감 정보"""
#     fit_characteristics: Annotated[str|None, Field(
#         default=None,
#         description="핏 관련 특성 (예: ['여유로운 핏', '몸에 잘 맞는 핏', '타이트한 핏', '루즈한 핏'])"
#     )]
#     texture: Annotated[str|None, Field(
#         default=None,
#         description="촉감 관련 특성 (예: ['부드러운 촉감', '매끄러운 질감', '거친 질감', '도톰한 감촉', '보드라운 느낌'])"
#     )]
#     stretch: Annotated[str|None, Field(
#         default=None,
#         description="신축성 관련 특성 (예: ['신축성 좋음', '신축성 없음', '약간의 신축성', '4way 스트레치', '세로 방향 신축'])"
#     )]
#     transparency: Annotated[str|None, Field(
#         default=None,
#         description="비침 관련 특성 (예: ['비침 없음', '약간 비침', '속옷 비침', '투명함', '불투명'])"
#     )]
#     thickness: Annotated[str|None, Field(
#         default=None,
#         description="두께 관련 특성 (예: ['얇은 소재', '두꺼운 소재', '적당한 두께', '도톰함', '얇고 가벼움', '두껍고 든든함'])"
#     )]
#     wearing_experience: Annotated[str|None, Field(
#         default=None,
#         description="착용 경험 관련 특성 (예: ['가벼움', '무게감 있음', '형태 유지', '드레이프성', '통기성 좋음'])"
#     )]

class MultiSizeInfo(BaseModel):
    """
    S, M, L 등 여러 사이즈 정보를 한 번에 처리
    예:
    {
    "S": {"총장": "68", "가슴단면": "50"},
    "M": {"총장": "70", "가슴단면": "52"},
    "L": {"총장": "72", "가슴단면": "54"}
    }
    """
    is_exist: Annotated[bool, Field(
        default=False,
        description="사이즈 실측 정보가 포함된 이미지 존재 여부(존재시 True)"
    )]
    size_measurements: Annotated[
        Union[Dict[str, Dict[str, str]], str, None], # str 타입도 허용
        Field(
            default=None,
            description="사이즈(예: S, M, L)별로 정리된 상세 실측 정보. JSON 문자열 또는 딕셔너리 형태"
        )
    ]

    @field_validator('size_measurements', mode='before')
    @classmethod
    def parse_size_measurements(cls, v):
        """size_measurements 필드를 검증하고 변환"""
        if v is None:
            return None
        
        # 이미 딕셔너리인 경우 그대로 반환
        if isinstance(v, dict):
            return v
        
        # 문자열인 경우 JSON 파싱 시도
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, dict):
                    return parsed
                else:
                    # JSON이지만 딕셔너리가 아닌 경우 None 반환
                    return None
            except (json.JSONDecodeError, ValueError):
                # JSON 파싱 실패시 None 반환
                return None
        
        # 다른 타입인 경우 None 반환
        return None


# class CareInfo(BaseModel):
#     """세탁 및 관리 방법"""
#     washing_method: Annotated[str|None, Field(
#         default=None,
#         description="의류에 대한 세탁 방법에 대한 설명 글 (예: '찬물 단독 세탁', '손세탁 권장', '세탁기 가능', '드라이클리닝')"
#     )]
#     care_precautions: Annotated[str|None, Field(
#         default=None,
#         description="의류 관리 시 주의사항 (예: ['직사광선 피해서 건조', '다림질 시 중온', '표백제 사용 금지', '비틀어 짜지 마세요'])"
#     )]


# class ProductDescription(BaseModel):
#     """의류 소개 및 특징 문구"""
#     design_highlights: Annotated[list[str], Field(
#         default_factory=list,
#         description="디자인 포인트 및 특징 (예: ['독특한 네크라인', '포켓 디테일', '언밸런스 실루엣', '빈티지 워싱'])"
#     )]
#     styling_suggestions: Annotated[list[str], Field(
#         default_factory=list,
#         description="스타일링 제안 (예: ['데님과 매치', '레이어드 연출', '벨트로 포인트', '단독 착용 추천'])"
#     )]
#     tpo_recommendations: Annotated[list[str], Field(
#         default_factory=list,
#         description="TPO 제안 (예: ['캐주얼한 일상', '데이트룩', '여행룩', '홈카페 룩', '출근룩'])"
#     )]
#     emotional_expressions: Annotated[list[str], Field(
#         default_factory=list,
#         description="감성적 표현 (예: ['자연스러운 편안함', '세련된 분위기', '발랄한 느낌', '우아한 매력'])"
#     )]

