# model 설정 관련 config 파일


class Config(dict):
    def __init__(self):
        _model_dict = {
            "DEFAULT_CAPTION_MODEL": "gemini-2.5-flash-lite-preview-06-17",
            "DEFAULT_COLOR_MODEL": "gemini-2.5-flash-lite-preview-06-17",
            "DEFAULT_OCR_MODEL": "gemini-1.5-flash-8b",
            "DEFAULT_IMAGE_SIZE": 224,
            "DEFAULT_CAPTION_TEMPERATURE": 0.1,
            "DEFAULT_OCR_TEMPERATURE": 0.0
        }
        
        _langchain_dict = {
            "DEFAULT_LANGCHAIN_PROJECT_NAME": "fashion-caption-analysis",
            "DEFAULT_TRACING_ENABLED": True
        }
        
        super().__init__()
        self.update(_model_dict)
        self.update(_langchain_dict)
        
class LLMInputKeys:
    DEEP_CAPTION = "deep_caption"
    COLOR_IMAGES = "color_images"
    TEXT_IMAGES = "text_images"


    