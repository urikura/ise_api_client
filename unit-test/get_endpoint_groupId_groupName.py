import requests
import json
import os
import base64
from dotenv import load_dotenv
import urllib3 # SSL警告を無効にするために必要
import time # API呼び出し間の待機に必要

# 自己署名証明書などを使用している場合のSSL警告を無効にする
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_ise_connection_details():
    """
    .envファイルからISEの接続情報を取得する。
    """
    load_dotenv()  # .envファイルをロード
    ise_ip = os.getenv('ISE_IP')  # ISEのIPアドレス
    ers_username = os.getenv('ISE_USERNAME')  # ERSのユーザー名
    ers_password = os.getenv('ISE_PASSWORD')  # ERSのパスワード
    http_proxy = os.getenv('HTTP_PROXY') # プロキシ設定を取得

    if not ise_ip or not ers_username or not ers_password:
        print(".envファイルにISE_IP、ISE_USERNAME、またはISE_PASSWORDが設定されていません")
        return None, None, None, None

    return ise_ip, ers_username, ers_password, http_proxy

def get_basic_auth_header(username, password):
    """
    Basic認証ヘッダーを生成する。
    """
    creds = f"{username}:{password}".encode('utf-8')
    encoded_auth = base64.b64encode(creds).decode('utf-8')
    return {
        'Accept': 'application/json',
        'authorization': f"Basic {encoded_auth}",
        'cache-control': 'no-cache',
    }

def get_proxies(http_proxy):
    """
    プロキシ設定を返す。
    """
    if http_proxy:
        print(f"プロキシを使用します: {http_proxy}")
        return {
            'http': http_proxy,
            'https': http_proxy,
        }
    return None

def get_group_name_by_id(ise_ip, username, password, http_proxy, group_id):
    """
    Endpoint GroupのIDを使って、そのGroupの名前を取得する。
    """
    if not group_id or group_id == 'N/A (詳細情報になし)' or group_id == 'エラーにより取得不可':
        return 'N/A (IDが無効)'

    headers = get_basic_auth_header(username, password)
    proxies = get_proxies(http_proxy)
    group_url = f"https://{ise_ip}:9060/ers/config/endpointgroup/{group_id}"

    try:
        # print(f"  Group詳細取得 (ID: {group_id}): {group_url}") # デバッグ用コメント
        response = requests.get(group_url, headers=headers, verify=False, proxies=proxies)
        response.raise_for_status()
        group_data = response.json()

        # --- ここを修正 ---
        # Group詳細から名前を抽出 ('EndPointGroup' キーの下にある 'name' キーを使用)
        group_detail = group_data.get('EndPointGroup', {}) # 'EndPointGroup' オブジェクトを取得
        group_name = group_detail.get('name', '名前不明 (キーなし)') # 'EndPointGroup' オブジェクトから 'name' を取得
        # -----------------

        return group_name

    except requests.exceptions.RequestException as e:
        # print(f"  Group詳細情報 (ID: {group_id}) の取得に失敗しました: {e}") # デバッグ用コメント
        if hasattr(e, 'response') and e.response is not None:
             # print(f"   HTTP Status Code: {e.response.status_code}") # デバッグ用コメント
             pass # エラーコードは必要に応じてログ出力
        return f"取得失敗 ({e})"
    except json.JSONDecodeError:
        # print(f"  Group詳細情報 (ID: {group_id}) のレスポンスがJSON形式ではありません。") # デバッグ用コメント
        return "不明 (不正なレスポンス)"
    except Exception as e:
        # print(f"  Group詳細情報 (ID: {group_id}) 取得中に予期しないエラーが発生しました: {e}") # デバッグ用コメント
        return f"予期しないエラー ({e})"

def get_endpoints_with_group_names():
    """
    ISEからEndpoint一覧を取得し、各Endpointの詳細情報および所属Groupの名前を取得して表示する。
    """
    ise_ip, username, password, http_proxy = get_ise_connection_details()
    if not ise_ip:
        return

    headers = get_basic_auth_header(username, password)
    proxies = get_proxies(http_proxy)

    # Step 1: Endpointの簡易リストを取得 (IDとMACを含む)
    list_url = f"https://{ise_ip}:9060/ers/config/endpoint"
    print(f"Endpoint簡易リスト取得: {list_url}")

    try:
        response = requests.get(list_url, headers=headers, verify=False, proxies=proxies)
        response.raise_for_status()
        list_data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"Endpoint簡易リストの取得に失敗しました: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"HTTP Status Code: {e.response.status_code}")
             print(f"Response Body: {e.response.text}")
        return
    except json.JSONDecodeError:
        print("Endpoint簡易リストのレスポンスがJSON形式ではありません。")
        return
    except Exception as e:
        print(f"Endpoint簡易リスト取得中に予期しないエラーが発生しました: {e}")
        return

    endpoints_summary = list_data.get('SearchResult', {}).get('resources', [])
    if not endpoints_summary:
        print("取得できるEndpoint情報がありませんでした。")
        return

    print(f"\n取得したEndpoint簡易情報数: {len(endpoints_summary)}")
    print("\n--- 各Endpointの詳細情報、Group ID、Group Name ---")

    # Step 2 & 3: 各Endpointの詳細情報とGroup名を順番に取得
    endpoint_results = []
    for i, endpoint_summary in enumerate(endpoints_summary):
        endpoint_id = endpoint_summary.get('id')
        endpoint_mac_summary = endpoint_summary.get('name', 'MAC不明 (簡易リスト)') # 簡易リストからのMAC

        if not endpoint_id:
            print(f"Endpoint簡易情報 {i+1}: IDが見つかりません。スキップします。")
            continue

        # Endpoint詳細取得 (2番目のAPIコール)
        # time.sleep(0.1) # 必要に応じて待機
        detail_url = f"https://{ise_ip}:9060/ers/config/endpoint/{endpoint_id}"
        try:
            detail_response = requests.get(detail_url, headers=headers, verify=False, proxies=proxies)
            detail_response.raise_for_status()
            detail_data = detail_response.json()

            endpoint_detail = detail_data.get('ERSEndPoint', {})
            mac_address = endpoint_detail.get('mac', endpoint_mac_summary)
            group_id = endpoint_detail.get('groupId', 'N/A (詳細情報になし)') # 詳細情報にgroupIdがなければ

            group_name = 'N/A (Group IDなし)'
            if group_id and group_id != 'N/A (詳細情報になし)':
                # Group名取得 (3番目のAPIコール)
                # time.sleep(0.1) # 必要に応じて待機
                group_name = get_group_name_by_id(ise_ip, username, password, http_proxy, group_id)

            print(f"MAC: {mac_address}, Group ID: {group_id}, Group Name: {group_name}")
            endpoint_results.append({'mac': mac_address, 'group_id': group_id, 'group_name': group_name})

        except requests.exceptions.RequestException as e:
            print(f" Endpoint詳細情報 ({endpoint_mac_summary}, ID: {endpoint_id}) の取得に失敗しました: {e}")
            print(f"MAC: {endpoint_mac_summary}, Group ID: エラーにより取得不可, Group Name: エラーにより取得不可")
            endpoint_results.append({'mac': endpoint_mac_summary, 'group_id': 'エラーにより取得不可', 'group_name': 'エラーにより取得不可'})
        except json.JSONDecodeError:
             print(f" Endpoint詳細情報 ({endpoint_mac_summary}, ID: {endpoint_id}) のレスポンスがJSON形式ではありません。")
             print(f"MAC: {endpoint_mac_summary}, Group ID: 不明 (不正なレスポンス), Group Name: 不明")
             endpoint_results.append({'mac': endpoint_mac_summary, 'group_id': '不明 (不正なレスポンス)', 'group_name': '不明'})
        except Exception as e:
            print(f" Endpoint詳細情報 ({endpoint_mac_summary}, ID: {endpoint_id}) 取得中に予期しないエラーが発生しました: {e}")
            print(f"MAC: {endpoint_mac_summary}, Group ID: 予期しないエラー, Group Name: 予期しないエラー")
            endpoint_results.append({'mac': endpoint_mac_summary, 'group_id': '予期しないエラー', 'group_name': '予期しないエラー'})


    print("------------------------------------------")

    return endpoint_results

if __name__ == "__main__":
    # 関数を呼び出して結果を取得
    mac_group_list = get_endpoints_with_group_names()

    # 必要に応じて、リスト全体をJSONなどで出力することも可能です
    # if mac_group_list:
    #    print("\n--- 取得結果サマリー (JSON) ---")
    #    print(json.dumps(mac_group_list, indent=4, ensure_ascii=False))
    #    print("-----------------------------------------")