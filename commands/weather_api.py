import requests
import urllib.parse
from datetime import datetime

def get_asos_data_current(service_key, stn_ids="108", data_type="JSON"):
    """
    기상청 종관기상관측(ASOS) 자료를 현재 시각 기준으로 조회하는 함수입니다.

    Parameters:
    - service_key: 기상청에서 발급받은 인증키 (str)
    - stn_ids: 조회할 지점 번호 (str), 예: "108" (서울)
    - data_type: 응답 데이터 형식 (str), "JSON" 또는 "XML"

    Returns:
    - 응답 데이터 (dict 또는 str): 요청 성공 시 JSON 객체 또는 XML 문자열 반환
    - 오류 발생 시 예외(Exception) 발생
    """
    base_url = "https://data.kma.go.kr/apiData/getData"
    endpoint = "/url/kma_sfctm2.php"

    # 현재 시각 정보 설정
    now = datetime.now()
    start_dt = now.strftime("%Y%m%d")
    start_hh = "00"
    end_dt = now.strftime("%Y%m%d")
    end_hh = now.strftime("%H")

    params = {
        "type": "json",
        "dataCd": "ASOS",
        "dateCd": "HR",
        "startDt": start_dt,
        "startHh": start_hh,
        "endDt": end_dt,
        "endHh": end_hh,
        "stnIds": stn_ids,
        "schList": "1",
        "pageIndex": "1",
        "pageUnit": "100",
        "dataType": data_type,
        "serviceKey": urllib.parse.unquote(service_key)
    }

    url = base_url + endpoint

    try:
        response = requests.get(url, params=params)
        print("응답 코드:", response.status_code)
        print("응답 내용:\n", response.text)  # 앞 500자만 출력
        response.raise_for_status()  # HTTP 오류 발생 시 예외 발생
        return response.json() if data_type.upper() == "JSON" else response.text
    except requests.exceptions.RequestException as e:
        print(f"API 요청 중 오류 발생: {e}")
        return None