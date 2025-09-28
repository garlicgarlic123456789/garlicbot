"""
GarlicBot AI Models Configuration

AI 모델 설정 및 초기화를 담당하는 모듈입니다.
"""

import os
import google.generativeai as genai

# 환경변수에서 API 키 가져오기
gemini_api_key = os.environ.get('GOOGLE_API_KEY')
API_URL = os.environ.get('API_URL')


# 기본 Gemini 모델들
model = genai.GenerativeModel('gemini-1.5-flash')
two_model = genai.GenerativeModel('gemini-2.0-flash')
two_lite_model = genai.GenerativeModel('gemini-2.0-flash-lite')
two_five_lite_model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-06-17')

# 안전 설정
safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE"
    },
]

# 마늘봇 전용 모델들 (긴 시스템 프롬프트들은 생략하고 참조만)
cute_model = genai.GenerativeModel('gemini-2.0-flash',
                                   safety_settings=safety_settings)

cute_model2 = genai.GenerativeModel('gemini-2.0-flash',
                                    safety_settings=safety_settings)

cute_model3 = genai.GenerativeModel('gemini-2.0-flash',
                                    safety_settings=safety_settings)

cute_model4 = genai.GenerativeModel('gemini-2.0-flash',
                                    safety_settings=safety_settings)

cute_model5 = genai.GenerativeModel('gemini-2.0-flash',
                                    safety_settings=safety_settings)

cute_model6 = genai.GenerativeModel('gemini-2.0-flash',
                                    safety_settings=safety_settings)

cute_model7 = genai.GenerativeModel('gemini-2.0-flash',
                                    safety_settings=safety_settings)

cute_model8 = genai.GenerativeModel('gemini-2.0-flash',
                                    safety_settings=safety_settings)

cute_model9 = genai.GenerativeModel('gemini-2.5-flash-lite',
                                    safety_settings=safety_settings)

# 심사 모델
judge_model = genai.GenerativeModel('tunedModels/ai25040301-x1nhe0vhq77q')

# 특별 모델들
special_model = genai.GenerativeModel('gemini-2.0-flash',
                                    safety_settings=safety_settings)

# API 엔드포인트
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={gemini_api_key}"


def get_model_by_name(model_name: str):
    """모델 이름을 통해 모델 객체를 반환하는 함수"""
    model_map = {
        'gemini-1.5-flash': model,
        'gemini-2.0-flash': two_model,
        'gemini-2.0-flash-lite': two_lite_model,
        'gemini-2.5-flash-lite': two_five_lite_model,
        'cute_model': cute_model,
        'cute_model2': cute_model2,
        'cute_model3': cute_model3,
        'cute_model4': cute_model4,
        'cute_model5': cute_model5,
        'cute_model6': cute_model6,
        'cute_model7': cute_model7,
        'cute_model8': cute_model8,
        'cute_model9': cute_model9,
        'judge_model': judge_model,
    }

    return model_map.get(model_name, model)  # 기본값은 model


def get_random_cute_model():
    """랜덤한 마늘봇 모델을 반환하는 함수"""
    import random
    cute_models = [cute_model, cute_model2, cute_model3, cute_model4,
                   cute_model5, cute_model6, cute_model7, cute_model8, cute_model9]
    return random.choice(cute_models)