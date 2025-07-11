# model 설정 관련 config 파일


class Config(dict):
    def __init__(self):
        _model_dict = {
            "DEFAULT_CAPTION_MODEL": "gemini-2.5-flash-lite-preview-06-17",
            "DEFAULT_COLOR_MODEL": "gemini-2.5-flash-lite-preview-06-17",
            "DEFAULT_OCR_MODEL": "gemini-2.5-flash-lite-preview-06-17",
            "DEFAULT_IMAGE_SIZE": 224,
            "DEFAULT_TEMPERATURE": 0.1
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


    