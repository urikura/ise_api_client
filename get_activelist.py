import requests
import json
import urllib3
from dotenv import load_dotenv
import os
import logging
import base64
import xml.etree.ElementTree as ET  # XML処理のためのライブラリをインポート
from xml.dom import minidom  # XML整形のためのライブラリをインポート


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
load_dotenv()

# ロギング設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# .envファイルからISE関連の設定情報を読み込む
ISE_IP = os.getenv('ISE_IP')
ISE_USERNAME = os.getenv('ISE_USERNAME')
ISE_PASSWORD = os.getenv('ISE_PASSWORD')
HTTP_PROXY = os.getenv('HTTP_PROXY')

def get_authorization_header():
    """
    ISEへのリクエストに必要なAuthorizationヘッダーを生成する。
    .envファイルからISEのユーザー名とパスワードを取得し、
    Basic認証のためのヘッダーを生成する。
    """
    user = ISE_USERNAME
    password = ISE_PASSWORD
    creds = str.encode(':'.join((user, password)))
    auth_header = bytes.decode(base64.b64encode(creds))
    # Authorizationヘッダー全体をログ出力しないように修正
    logger.debug("Authorization Header: (omitted for security)")
    return 'Basic ' + auth_header

def get_proxies():
    """
    HTTP_PROXY環境変数が設定されている場合はプロキシ設定を返し、
    設定されていない場合はNoneを返す。
    """
    logger.debug(f"HTTP_PROXY: {HTTP_PROXY}")
    if HTTP_PROXY:
        return {
            'http': HTTP_PROXY,
            'https': HTTP_PROXY,
        }
    else:
        return None

def get_active_sessions():
    """
    ISEからアクティブなセッションのリストを取得する。
    """
    # url = f"https://{ISE_IP}:9060/ers/monitoring/liveSession/activeList" # 元のURL
    url = f"https://{ISE_IP}/admin/API/mnt/Session/ActiveList"  # 修正後のURL
    headers = {
        'Accept': 'application/xml', # JSON形式でのレスポンスを要求
        'authorization': get_authorization_header(),
        'cache-control': "no-cache",
    }
    proxies = get_proxies()
    try:
        response = requests.get(
            url,
            auth=(ISE_USERNAME, ISE_PASSWORD),
            headers=headers,
            verify=False,
            proxies=proxies,
            timeout=10, # タイムアウトを10秒に設定
        )
        response.raise_for_status()  # エラーレスポンスの場合は例外を発生させる
        # data = response.json() # JSONレスポンスをパースするのではなく、
        # logger.debug(f"Response data: {data}")  # レスポンスデータをログ出力
        return response.text # レスポンスの生のテキストを返す

        # 必要な情報のみを抽出してリストに格納
        # sessions = []
        # for item in data['sessions']: # 'SearchResult' ではなく 'sessions'
        #     session_data = {
        #         'ip_address': item['FramedIPAddress'], # 正しいキーを使用
        #         'mac_address': item['CallingStationId'], # 正しいキーを使用
        #         'session_id': item['SessionId'],
        #         'username': item.get('UserName', 'N/A'),  # ユーザー名が存在しない場合は'N/A'を設定
        #         'start_time': item['StartTime'], # 正しいキーを使用
        #         'end_time': item.get('EndTime', 'N/A'),
        #     }
        #     sessions.append(session_data)
        # return sessions
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")  # エラー内容をログ出力
        return {'error': str(e)}  # エラー情報を返す
    # except json.JSONDecodeError as e: # JSONDecodeErrorではなく、他のエラーをキャッチする
    #     logger.error(f"JSONDecodeError: {e}. Response text: {response.text}")
    #     return {'error': f"JSONDecodeError: {e}.  Response text: {response.text}"}, 500
    except Exception as e:
        logger.error(f"Error: {e}. Response text: {response.text}")
        return {'error': f"Error: {e}. Response text: {response.text}"}, 500

def generate_xml(sessions):
    """
    セッション情報をXML形式の文字列に変換する。

    Args:
        sessions (list): セッション情報のリスト。

    Returns:
        str: セッション情報を表すXML形式の文字列。
    """
    root = ET.Element('sessions')  # ルート要素を作成
    for session in sessions:
        session_element = ET.SubElement(root, 'session')  # 各セッションの要素を作成
        # サブ要素を作成してテキストを設定
        ip_address_element = ET.SubElement(session_element, 'ip_address')
        ip_address_element.text = session['ip_address']
        mac_address_element = ET.SubElement(session_element, 'mac_address')
        mac_address_element.text = session['mac_address']
        session_id_element = ET.SubElement(session_element, 'session_id')
        session_id_element.text = session['session_id']
        username_element = ET.SubElement(session_element, 'username')
        username_element.text = session['username']
        start_time_element = ET.SubElement(session_element, 'start_time')
        start_time_element.text = session['start_time']
        end_time_element = ET.SubElement(session_element, 'end_time')
        end_time_element.text = session['end_time']

    # XMLを文字列に変換し、整形
    xml_string = ET.tostring(root, encoding='utf-8')
    dom = minidom.parseString(xml_string)
    pretty_xml_string = dom.toprettyxml(indent="  ")  # インデントを指定して整形
    return pretty_xml_string


def main():
    """
    アクティブなセッションのリストを取得し、XML形式で結果を表示する。
    """
    sessions = get_active_sessions()
    if isinstance(sessions, dict) and 'error' in sessions:
        print(json.dumps(sessions, indent=2, ensure_ascii=False))  # エラー情報をJSONで表示
    else:
        # xml_output = generate_xml(sessions) # XMLを生成するのではなく、
        # print(xml_output)  # XML形式で結果を表示
        print(sessions) # 生のレスポンスデータを表示する
        

if __name__ == "__main__":
    main()

