from flask import Flask, render_template, request, jsonify
import requests
import json
import urllib3
from dotenv import load_dotenv
import os
import logging
import base64
import xml.etree.ElementTree as ET # XML処理

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
load_dotenv()

# ロギング設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    )
logger = logging.getLogger(__name__)


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



@app.route('/', methods=['GET', 'POST'])
def index():
    global ISE_IP, ISE_USERNAME, ISE_PASSWORD
    logger.debug(f"Request URL: {request.url}")
    if request.method == 'POST':
        ISE_IP = request.form['ise_ip']
        ISE_USERNAME = request.form['ise_username']
        ISE_PASSWORD = request.form['ise_password']
        logger.debug(
            f"POST data: ISE_IP={ISE_IP}, ISE_USERNAME={ISE_USERNAME}, ISE_PASSWORD={ISE_PASSWORD}"
        )
        return "設定を保存しました"
    return render_template(
        'index.html',
        ise_ip=ISE_IP,
        ise_username=ISE_USERNAME,
        ise_password="[*****]",  # パスワードを[*****]でマスク
    )


@app.route('/check_env')
def check_env():
    """
    .envファイルが存在するかどうかを確認し、ISE_IPの値とともにJSONレスポンスを返す
    """
    logger.debug(f"Request URL: {request.url}")
    env_exists = os.path.exists('.env')
    ise_ip_value = os.getenv('ISE_IP') if env_exists else ""
    ise_username_value = os.getenv('ISE_USERNAME') if env_exists else "" #usernameも取得
    logger.debug(f".env exists: {env_exists}, ISE_IP: {ise_ip_value}, ISE_USERNAME:{ise_username_value}")
    return jsonify({'exists': env_exists, 'ise_ip': ise_ip_value, 'ise_username':ise_username_value}) #usernameも返す


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



@app.route('/get_endpoint_groups')
def get_endpoint_groups():
    url = f"https://{ISE_IP}:9060/ers/config/endpointgroup"
    logger.debug(f"Request URL: {request.url}, Target URL: {url}")
    headers = {
        'Accept': 'application/json',
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
        )
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Response data: {data}")
        endpoint_groups = [
            group['name'] for group in data['SearchResult']['resources']
        ]
        return jsonify({'endpoint_groups': endpoint_groups})
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/get_endpoints')  # エンドポイント一覧取得API
def get_endpoints():
    """
    ISEからEndpoint一覧を取得するAPI
    """
    url = f"https://{ISE_IP}:9060/ers/config/endpoint"
    logger.debug(f"Request URL: {request.url}, Target URL: {url}")
    headers = {
        'Accept': 'application/json',
        'authorization': get_authorization_header(),
        'cache-control': "no-cache",
    }
    proxies = get_proxies()
    try:
        response = requests.get(url, headers=headers, verify=False, proxies=proxies)
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Response data: {data}")
        endpoints = [
            {'id': ep['id'], 'mac': ep['name'], 'group_id': ep.get('groupId', 'N/A')}  # 必要な情報のみ抽出
            for ep in data['SearchResult']['resources']
        ]
        return jsonify({'endpoints': endpoints})
    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to get endpoints: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/get_sessions')
def get_sessions():
    url = f"https://{ISE_IP}/admin/API/mnt/Session/ActiveList"
    logger.debug(f"Request URL: {request.url}, Target URL: {url}")
    headers = {
        'Accept': 'application/xml',  # Acceptヘッダーをapplication/xmlに設定
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
        )
        response.raise_for_status()
        xml_data = response.text  # レスポンスはXML
        logger.debug(f"Response data (XML): {xml_data}")

        # XMLを解析して必要な情報を抽出
        root = ET.fromstring(xml_data)
        sessions = []
        # activeListにnoOfActiveSession属性があるか確認
        if root.attrib.get('noOfActiveSession') is not None:
            no_of_active_session = root.attrib['noOfActiveSession']
            logger.debug(f"Number of active sessions: {no_of_active_session}")
        else:
            no_of_active_session = "N/A"
            logger.warning("noOfActiveSession attribute not found in XML response.")

        # セッション情報が存在する場合のみ処理を行う
        if root is not None: # 常にrootは存在する。
            for session_element in root.findall(".//session"): # findallでsessionタグを検索
                session_data = {
                    'ip_address': session_element.find('Framed-IP-Address').text if session_element.find('Framed-IP-Address') is not None else 'N/A',
                    'mac_address': session_element.find('calling-station-id').text if session_element.find('calling-station-id') is not None else 'N/A',
                    'session_id': session_element.find('SessionId').text if session_element.find('SessionId') is not None else 'N/A',
                }
                sessions.append(session_data)
        return jsonify({'sessions': sessions, 'noOfActiveSession': no_of_active_session}) #jsonifyにnoOfActiveSessionを含める
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return jsonify({'error': str(e)}), 500
    except ET.ParseError as e:
        logger.error(f"XML Parse Error: {e}")
        return jsonify({'error': f'XML Parse Error: {e}'}), 500



@app.route('/delete_endpoint', methods=['POST'])
def delete_endpoint():
    mac_address = request.json['mac_address']
    endpoint_group_id = request.json['endpoint_group_id']
    logger.debug(
        f"Request URL: {request.url}, MAC: {mac_address}, Group ID: {endpoint_group_id}"
    )
    # EndpointIDを取得するためのAPI呼び出し
    endpoint_id_url = (
        f"https://{ISE_IP}:9060/ers/config/endpoint?filter=mac.equals.{mac_address}"
    )
    headers = {
        'Accept': 'application/json',
        'authorization': get_authorization_header(),
        'cache-control': "no-cache",
    }
    proxies = get_proxies()
    try:
        response = requests.get(
            endpoint_id_url,
            auth=(ISE_USERNAME, ISE_PASSWORD),
            headers=headers,
            verify=False,
            proxies=proxies,
        )
        response.raise_for_status()
        data = response.json()
        logger.debug(f"Response data: {data}")

        if data['SearchResult']['total'] == 0:
            message = f'MACアドレス {mac_address} は見つかりませんでした。'
            logger.warning(message)
            return jsonify({'message': message}), 404

        endpoint_id = data['SearchResult']['resources'][0]['id']
        delete_url = f"https://{ISE_IP}:9060/ers/config/endpointgroup/{endpoint_group_id}/endpoints/{endpoint_id}"
        response = requests.delete(
            delete_url,
            auth=(ISE_USERNAME, ISE_PASSWORD),
            headers=headers,
            verify=False,
            proxies=proxies,
        )
        response.raise_for_status()
        return jsonify({'message': f'MACアドレス {mac_address} を削除しました。'})
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return jsonify({'error': str(e)}), 500



@app.route('/add_endpoint', methods=['POST'])
def add_endpoint():
    mac_address = request.json['mac_address']
    endpoint_group_id = request.json['endpoint_group_id']
    logger.debug(
        f"Request URL: {request.url}, MAC: {mac_address}, Group ID: {endpoint_group_id}"
    )
    url = f"https://{ISE_IP}:9060/ers/config/endpointgroup/{endpoint_group_id}/endpoints"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'authorization': get_authorization_header(),
        'cache-control': "no-cache",
    }
    proxies = get_proxies()
    payload = {"Endpoint": {"mac": mac_address}}
    try:
        response = requests.post(
            url,
            auth=(ISE_USERNAME, ISE_PASSWORD),
            headers=headers,
            data=json.dumps(payload),
            verify=False,
            proxies=proxies,
        )
        response.raise_for_status()
        return jsonify({'message': f'MACアドレス {mac_address} を追加しました。'})
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

