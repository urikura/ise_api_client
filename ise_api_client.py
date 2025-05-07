from flask import Flask, render_template, request, jsonify
import requests
import json
import urllib3
from dotenv import load_dotenv
import os
import logging
import base64
import xml.etree.ElementTree as ET # XML処理
import time # API呼び出し間の待機に必要

# 自己署名証明書などを使用している場合のSSL警告を無効にする（開発時のみ使用し、本番環境では警告を有効にしてください）
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

# 環境変数はFlaskの実行時に読み込まれますが、関数内でos.getenvで都度取得します。
# グローバル変数は削除またはコメントアウトします。
# ISE_IP = os.getenv('ISE_IP')
# ISE_USERNAME = os.getenv('ISE_USERNAME')
# ISE_PASSWORD = os.getenv('ISE_PASSWORD')
# HTTP_PROXY = os.getenv('HTTP_PROXY')

# =====================================================
# ヘルパー関数群
# =====================================================

def get_ise_connection_details():
    """
    .envファイルからISEの接続情報を取得する。
    APIコールを行う関数内でこれを呼び出す。
    """
    # load_dotenv() はスクリプト冒頭で行われているためここでは不要ですが、
    # 念のため必要な環境変数が取得できるか確認します。
    ise_ip = os.getenv('ISE_IP')
    username = os.getenv('ISE_USERNAME')
    password = os.getenv('ISE_PASSWORD')
    http_proxy = os.getenv('HTTP_PROXY')

    # 必須の設定がない場合はログを出力
    if not ise_ip or not username or not password:
        logger.error(".envファイルにISE_IP、ISE_USERNAMEまたはISE_PASSWORDが設定されていません")
        # エラーの場合はNoneを返す
        return None, None, None, None

    return ise_ip, username, password, http_proxy

def get_basic_auth_header(username, password):
    """
    Basic認証ヘッダーの 'Basic <encoded_creds>' 部分の値を生成する。
    """
    # usernameまたはpasswordがNoneの場合はNoneを返す
    if not username or not password:
         logger.error("認証情報が不足しているためAuthorizationヘッダーを生成できません。")
         return None

    creds = f"{username}:{password}".encode('utf-8')
    encoded_auth = bytes.decode(base64.b64encode(creds)) # <-- Base64エンコード後の文字列

    # Authorizationヘッダー全体をログ出力しないように修正
    logger.debug("Authorization Header: (omitted for security)")
    return 'Basic ' + encoded_auth


def get_proxies():
    """
    HTTP_PROXY環境変数が設定されている場合はプロキシ設定を返し、
    設定されていない場合はNoneを返す。
    """
    proxy = os.getenv('HTTP_PROXY') # 環境変数から都度取得
    logger.debug(f"HTTP_PROXY: {proxy}")
    if proxy:
        return {
            'http': proxy,
            'https': proxy,
        }
    else:
        return None

# Helper function to get Group Name by ID
def get_group_name_by_id(ise_ip, username, password, http_proxy, group_id):
    """
    Endpoint GroupのIDを使って、そのGroupの名前を取得するヘルパー関数。
    """
    if not group_id:
        return 'N/A (IDなし)'

    # ヘッダーとプロキシ設定を取得
    headers = {"Accept": "application/json"} # Endpoint Group詳細はJSONを期待
    auth_header_value = get_basic_auth_header(username, password) # 'Basic <encoded>' 形式の文字列を取得
    if auth_header_value:
         headers['authorization'] = auth_header_value # ヘッダー辞書に追加
    else:
         # 認証ヘッダーが生成できなかった場合はエラーを返す
         return "名前取得失敗 (認証情報不足)"

    proxies = get_proxies() # ヘルパー関数を使う


    group_url = f"https://{ise_ip}:9060/ers/config/endpointgroup/{group_id}"
    logger.debug(f"  Group詳細取得 (ID: {group_id}): {group_url}") # デバッグ用コメント

    try:
        response = requests.get(group_url, headers=headers, verify=False, proxies=proxies)
        response.raise_for_status()
        group_data = response.json()

        # Endpoint Group詳細レスポンスの構造に合わせて名前を抽出
        # 前回の調査結果に基づき、'EndPointGroup' キーの下に 'name' があると想定
        group_detail = group_data.get('EndPointGroup', {})
        group_name = group_detail.get('name', '名前不明 (キーなし)')

        return group_name

    except requests.exceptions.RequestException as e:
        logger.error(f"Group詳細情報 (ID: {group_id}) の取得に失敗しました: {e}")
        return f"取得失敗 ({e.response.status_code if hasattr(e, 'response') and e.response is not None else 'N/A'})"
    except json.JSONDecodeError:
        logger.error(f"Group詳細情報 (ID: {group_id}) のレスポンスがJSON形式ではありません。")
        return "不明 (不正なレスポンス)"
    except Exception as e:
        logger.error(f"Group詳細情報 (ID: {group_id}) 取得中に予期しないエラーが発生しました: {e}")
        return f"予期しないエラー ({e})"


# =====================================================
# Flask routes
# =====================================================

@app.route('/', methods=['GET']) # POSTメソッドは.envから読み込むため不要
def index():
    logger.debug(f"Request URL: {request.url}")

    # .envファイルから読み込んだIPとユーザー名をテンプレートに渡します
    # check_env APIから取得する方がJavaScriptで扱いやすいので、
    # こちらは基本テンプレート表示のみとします。
    return render_template('index.html')


@app.route('/check_env')
def check_env():
    """
    .envファイルが存在するかどうかを確認し、ISE_IPとISE_USERNAMEの値をJSONレスポンスで返す
    """
    logger.debug(f"Request URL: {request.url}")
    env_exists = os.path.exists('.env')
    # 環境変数が設定されているかを確認し、値またはデフォルト値を返す
    ise_ip_value = os.getenv('ISE_IP', '設定されていません')
    ise_username_value = os.getenv('ISE_USERNAME', '設定されていません')
    logger.debug(f".env exists: {env_exists}, ISE_IP: {ise_ip_value}, ISE_USERNAME:{ise_username_value}")
    return jsonify({'exists': env_exists, 'ise_ip': ise_ip_value, 'ise_username':ise_username_value})



@app.route('/get_sessions')
def get_sessions():
    """
    ISEからActive Session一覧を取得し、セッション数とRaw XMLを返すAPI。
    XML APIを使用。
    """
    # ヘルパー関数で接続情報を取得
    ise_ip, username, password, http_proxy = get_ise_connection_details()
    if not ise_ip:
        return jsonify({'error': '.envファイルにISE_IP、ISE_USERNAMEまたはISE_PASSWORDが設定されていません'}), 500
    if not username or not password:
         return jsonify({'error': 'ISE_USERNAMEまたはISE_PASSWORDが設定されていません'}), 500


    url = f"https://{ise_ip}/admin/API/mnt/Session/ActiveList"
    logger.debug(f"Request URL: {request.url}, Target URL: {url}")

    # XML APIは認証情報をHTTP Headerではなく、requestsのauthパラメータで渡します。
    # ERS APIとは認証方法が異なることに注意。
    headers = {
        'Accept': 'application/xml',  # Acceptヘッダーをapplication/xmlに設定
        'cache-control': "no-cache",
    }
    proxies = get_proxies() # ヘルパー関数を使う

    try:
        response = requests.get(
            url,
            auth=(username, password), # XML APIはauthタプルを使用
            headers=headers,
            verify=False,
            proxies=proxies,
        )
        response.raise_for_status()
        xml_data = response.text  # レスポンスはXML

        # --- XMLをパースしてセッション数を取得 ---
        root = ET.fromstring(xml_data)
        no_of_active_session = root.attrib.get('noOfActiveSession', "N/A")
        logger.debug(f"Number of active sessions: {no_of_active_session}")
        # ----------------------------------------

        # セッション情報からMACアドレスなども抽出できますが、
        # 今回は Raw XML 返却がご要望のため、ここではリスト化は必須ではありません。
        # mac_addresses = []
        # ... XMLパースしてリスト化するコード ...

        # セッション数とRaw XMLデータを返す
        return jsonify({'noOfActiveSession': no_of_active_session, 'raw_xml': xml_data})
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        error_message = str(e)
        if hasattr(e, 'response') and e.response is not None:
            error_message += f" Status Code: {e.response.status_code}" # XMLレスポンスボディは長いため除外
        return jsonify({'error': f'Active Session取得失敗: {error_message}'}), 500
    except ET.ParseError as e:
        logger.error(f"XML Parse Error: {e}")
        return jsonify({'error': f'Active Session XML Parse Error: {e}'}), 500
    except Exception as e:
        logger.error(f"An unexpected error occurred during get_sessions: {e}")
        return jsonify({'error': f'Active Session取得中に予期しないエラー: {e}'}), 500



@app.route('/get_endpoints')  # エンドポイント一覧取得API (Group名付き)
def get_endpoints():
    """
    ISEからEndpoint一覧を取得し、各Endpointの詳細情報および所属Groupの名前を取得して返すAPI。
    ERS APIを使用。
    """
    # ヘルパー関数で接続情報を取得
    ise_ip, username, password, http_proxy = get_ise_connection_details()
    if not ise_ip:
        return jsonify({'error': '.envファイルにISE_IP、ISE_USERNAMEまたはISE_PASSWORDが設定されていません'}), 500
    if not username or not password:
         return jsonify({'error': 'ISE_USERNAMEまたはISE_PASSWORDが設定されていません'}), 500


    # ヘッダーとプロキシ設定を取得
    headers = {"Accept": "application/json"} # Endpoint一覧はJSONを期待
    auth_header_value = get_basic_auth_header(username, password)
    if auth_header_value:
         headers['authorization'] = auth_header_value
    else:
         # 認証ヘッダーが生成できなかった場合はエラーを返す
         return jsonify({'error': '認証情報が不足しているためAPIリクエストヘッダーを生成できません'}), 500

    proxies = get_proxies() # ヘルパー関数を使う


    # Step 1: Endpointの簡易リストを取得 (IDとMACを含む)
    list_url = f"https://{ise_ip}:9060/ers/config/endpoint"
    logger.debug(f"Endpoint簡易リスト取得: {list_url}")

    try:
        response = requests.get(list_url, headers=headers, verify=False, proxies=proxies)
        response.raise_for_status()
        list_data = response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Endpoint簡易リストの取得に失敗しました: {e}")
        error_message = str(e)
        if hasattr(e, 'response') and e.response is not None:
            error_message += f" Status Code: {e.response.status_code}, Body: {e.response.text}"
        return jsonify({'error': f"Endpoint簡易リスト取得失敗: {error_message}"}), 500
    except json.JSONDecodeError:
        logger.error("Endpoint簡易リストのレスポンスがJSON形式ではありません。")
        return jsonify({'error': "Endpoint簡易リストのレスポンスが不正です。"}), 500
    except Exception as e:
        logger.error(f"Endpoint簡易リスト取得中に予期しないエラーが発生しました: {e}")
        return jsonify({'error': f"Endpoint簡易リスト取得中に予期しないエラー: {str(e)}"}), 500


    endpoints_summary = list_data.get('SearchResult', {}).get('resources', [])
    if not endpoints_summary:
        logger.info("取得できるEndpoint情報がありませんでした。")
        return jsonify({'endpoints': []}) # 空のリストを返す

    logger.debug(f"取得したEndpoint簡易情報数: {len(endpoints_summary)}")

    # Step 2 & 3: 各Endpointの詳細情報とGroup名を順番に取得
    endpoint_results = []
    for i, endpoint_summary in enumerate(endpoints_summary):
        endpoint_id = endpoint_summary.get('id')
        # 簡易リストのnameはMACアドレスを期待
        endpoint_mac_summary = endpoint_summary.get('name', 'MAC不明 (簡易リスト)')

        if not endpoint_id:
            logger.warning(f"Endpoint簡易情報 {i+1}: IDが見つかりません。スキップします。")
            continue

        # Endpoint詳細取得 (2番目のAPIコール)
        # time.sleep(0.05) # 必要に応じて短い待機
        detail_url = f"https://{ise_ip}:9060/ers/config/endpoint/{endpoint_id}"
        try:
            detail_response = requests.get(detail_url, headers=headers, verify=False, proxies=proxies)
            detail_response.raise_for_status()
            detail_data = detail_response.json()

            endpoint_detail = detail_data.get('ERSEndPoint', {})
            # 詳細情報にあればそちらのMACを使用、なければ簡易リストから
            mac_address = endpoint_detail.get('mac', endpoint_mac_summary)
            # 詳細情報からgroupIdを取得
            group_id = endpoint_detail.get('groupId', 'N/A')

            group_name = 'N/A'
            if group_id and group_id != 'N/A':
                # Group名取得 (3番目のAPIコール)
                # time.sleep(0.05) # 必要に応じて短い待機
                group_name = get_group_name_by_id(ise_ip, username, password, http_proxy, group_id)


            endpoint_results.append({
                'mac': mac_address,
                'group_id': group_id,
                'group_name': group_name
            })

        except requests.exceptions.RequestException as e:
            logger.error(f"Endpoint詳細情報 ({endpoint_mac_summary}, ID: {endpoint_id}) の取得に失敗しました: {e}")
            endpoint_results.append({
                'mac': endpoint_mac_summary,
                'group_id': 'エラー',
                'group_name': f'取得失敗 ({e.response.status_code if hasattr(e, 'response') and e.response is not None else 'N/A'})'
            })
        except json.JSONDecodeError:
             logger.error(f"Endpoint詳細情報 ({endpoint_mac_summary}, ID: {endpoint_id}) のレスポンスがJSON形式ではありません。")
             endpoint_results.append({
                 'mac': endpoint_mac_summary,
                 'group_id': '不明',
                 'group_name': '不明 (不正なレスポンス)'
             })
        except Exception as e:
            logger.error(f"Endpoint詳細情報 ({endpoint_mac_summary}, ID: {endpoint_id}) 取得中に予期しないエラーが発生しました: {e}")
            endpoint_results.append({
                'mac': endpoint_mac_summary,
                'group_id': 'エラー',
                'group_name': f'予期しないエラー ({e})'
            })


    return jsonify({'endpoints': endpoint_results})


@app.route('/delete_endpoint', methods=['POST'])
def delete_endpoint():
    """
    指定されたMACアドレスのEndpointを削除するAPI。
    まずMACアドレスからEndpointIDを検索し、その後Endpointリソース自体を削除する。
    ERS APIを使用。
    """
    mac_address = request.json.get('mac_address')
    # 削除APIのURLにGroup IDは不要ですが、UIからの入力としては受け取ったままにします。（今回の修正でUIからは削除済み）
    # endpoint_group_id_from_ui = request.json.get('endpoint_group_id')
    # logger.debug(f"Received delete request for MAC: {mac_address}, Group ID from UI: {endpoint_group_id_from_ui}") # UIからのGroup IDログは削除


    if not mac_address: # 削除に必要なのはMACアドレスのみ
         return jsonify({'error': 'MACアドレスが必要です'}), 400

    # ヘルパー関数で接続情報を取得
    ise_ip, username, password, http_proxy = get_ise_connection_details()
    if not ise_ip:
        return jsonify({'error': '.envファイルにISE_IP、ISE_USERNAMEまたはISE_PASSWORDが設定されていません'}), 500
    if not username or not password:
         return jsonify({'error': 'ISE_USERNAMEまたはISE_PASSWORDが設定されていません'}), 500


    # ヘッダーとプロキシ設定を取得
    headers = {"Accept": "application/json"} # Endpoint検索レスポンスはJSONを期待
    auth_header_value = get_basic_auth_header(username, password)
    if auth_header_value:
         headers['authorization'] = auth_header_value
    else:
         # 認証ヘッダーが生成できなかった場合はエラーを返す
         return jsonify({'error': '認証情報が不足しているためAPIリクエストヘッダーを生成できません'}), 500

    proxies = get_proxies() # ヘルパー関数を使う

    logger.debug(
        f"Attempting to find Endpoint ID for MAC: {mac_address}"
    )

    # Step 1: MACアドレスに一致するEndpointのIDを取得
    # フィルター検索がうまくいかないため、全件リストを取得してPythonで検索する
    list_url = f"https://{ise_ip}:9060/ers/config/endpoint"
    logger.debug(f"Getting full endpoint list to find ID: {list_url}")
    try:
        response = requests.get(
            list_url,
            headers=headers,
            verify=False,
            proxies=proxies,
        )
        response.raise_for_status()
        list_data = response.json()
        logger.debug(f"Full endpoint list received. Searching for MAC: {mac_address}")

        endpoint_id = None
        # SearchResult.resources はEndpoint簡易情報のリストを期待
        endpoints_list = list_data.get('SearchResult', {}).get('resources', [])

        for endpoint_summary in endpoints_list:
            # 簡易リストのnameがMACアドレスであることを期待して比較
            if endpoint_summary.get('name', '').lower() == mac_address.lower():
                endpoint_id = endpoint_summary.get('id')
                break # MAC一致するものが見つかったらループを抜ける

        if not endpoint_id:
            message = f'MACアドレス {mac_address} に一致するEndpointが見つかりませんでした。'
            logger.warning(message)
            # Endpointが見つからなかった場合は404を返す
            return jsonify({'message': message}), 404

        logger.debug(f"Found Endpoint ID: {endpoint_id} for MAC: {mac_address}")

        # Step 2: Endpointリソース自体を削除するためのAPI呼び出し (DELETEメソッド)
        # ユーザー情報とドキュメント（後者の形式）に基づき、/ers/config/endpoint/{endpointId} にDELETE
        delete_url = f"https://{ise_ip}:9060/ers/config/endpoint/{endpoint_id}"
        logger.debug(f"Delete URL: {delete_url}")

        # DELETEメソッドも認証ヘッダーが必要です。Acceptヘッダーも通常必要です。
        # 削除APIはレスポンスボディがないことが多いですが、AcceptはJSONで送るのが無難です。
        delete_headers = {"Accept": "application/json"}
        if auth_header_value:
            delete_headers['authorization'] = auth_header_value
        # Content-TypeはDELETEでは通常不要

        response = requests.delete(
            delete_url,
            headers=delete_headers, # DELETEメソッドもheadersが必要
            verify=False,
            proxies=proxies,
        )
        # DELETE成功時は通常204 No Contentが返されます。
        # raise_for_status() は204でも例外を発生させません。
        response.raise_for_status()
        logger.info(f"Successfully deleted Endpoint with MAC {mac_address} (ID: {endpoint_id})")
        # 成功レスポンスとしてメッセージを返す
        return jsonify({'message': f'MACアドレス {mac_address} のEndpointを削除しました。'})

    except requests.exceptions.RequestException as e:
        logger.error(f"Endpoint削除リクエスト失敗: {e}")
        error_message = str(e)
        if hasattr(e, 'response') and e.response is not None:
            error_message += f" Status Code: {e.response.status_code}, Body: {e.response.text}"
        return jsonify({'error': f'Endpoint削除失敗: {error_message}'}), 500
    except Exception as e:
        logger.error(f"Endpoint削除中に予期しないエラーが発生しました: {e}")
        return jsonify({'error': f'Endpoint削除中に予期しないエラー: {str(e)}'}), 500


@app.route('/add_endpoint', methods=['POST'])
def add_endpoint():
    """
    指定されたMACアドレスのEndpointを指定されたGroupに追加するAPI。
    ERS APIを使用。
    """
    mac_address = request.json.get('mac_address')
    endpoint_group_id = request.json.get('endpoint_group_id')

    if not mac_address or not endpoint_group_id:
         return jsonify({'error': 'MACアドレスとEndpoint Group IDが必要です'}), 400

    # ヘルパー関数で接続情報を取得
    ise_ip, username, password, http_proxy = get_ise_connection_details()
    if not ise_ip:
        return jsonify({'error': '.envファイルにISE_IP、ISE_USERNAMEまたはISE_PASSWORDが設定されていません'}), 500
    if not username or not password:
         return jsonify({'error': 'ISE_USERNAMEまたはISE_PASSWORDが設定されていません'}), 500


    # ヘッダーとプロキシ設定を取得
    # POSTリクエストなので Content-Type: application/json が必要
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json', # AcceptもJSONが一般的
    }
    auth_header_value = get_basic_auth_header(username, password)
    if auth_header_value:
         headers['authorization'] = auth_header_value
    else:
         # 認証ヘッダーが生成できなかった場合はエラーを返す
         return jsonify({'error': '認証情報が不足しているためAPIリクエストヘッダーを生成できません'}), 500

    proxies = get_proxies() # ヘルパー関数を使う

    # --- 修正: Endpointリソースを作成するAPIエンドポイントを使用 ---
    url = f"https://{ise_ip}:9060/ers/config/endpoint"
    # ---------------------------------------------------------

    # 追加するEndpointの情報ペイロード
    # --- 修正: CURLサンプルに合わせたペイロード構造 ---
    payload = {
        "ERSEndPoint": { # <-- 最上位キーを ERSEndPoint に変更
            "mac": mac_address,
            "groupId": endpoint_group_id, # <-- Group ID をペイロードに含める
            "staticGroupAssignment": True # <-- staticGroupAssignment をペイロードに含める (通常はTrue)
            # 必要に応じて他の属性（description, profileIdなど）を追加
            # "description": "Added via API Client",
        }
    }
    # -----------------------------------------------------
    logger.debug(f"Add Endpoint Payload: {json.dumps(payload)}")
    logger.debug(f"Add Endpoint URL: {url}")


    try:
        response = requests.post(
            url,
            headers=headers,
            data=json.dumps(payload), # Python辞書をJSON文字列に変換
            verify=False,
            proxies=proxies,
        )
        # POST成功時は通常201 Createdが返されます
        response.raise_for_status()
        logger.info(f"Successfully added MAC {mac_address} to Group ID {endpoint_group_id}")
        # 成功レスポンスとしてメッセージを返す
        return jsonify({'message': f'MACアドレス {mac_address} をEndpointGroupに追加しました。'})
    except requests.exceptions.RequestException as e:
        logger.error(f"Endpoint追加リクエスト失敗: {e}")
        error_message = str(e)
        if hasattr(e, 'response') and e.response is not None:
            error_message += f" Status Code: {e.response.status_code}, Body: {e.response.text}"
        return jsonify({'error': f'Endpoint追加失敗: {error_message}'}), 500
    except Exception as e:
        logger.error(f"Endpoint追加中に予期しないエラーが発生しました: {e}")
        return jsonify({'error': f'Endpoint追加中に予期しないエラー: {str(e)}'}), 500


if __name__ == '__main__':
    # debug=True は開発時のみ使用し、本番環境ではFalseにしてください。
    # host='0.0.0.0' は全てのインターフェースでリッスンします。本番環境では特定のIPに制限することを検討してください。
    app.run(debug=True, host='0.0.0.0', port=5001)
