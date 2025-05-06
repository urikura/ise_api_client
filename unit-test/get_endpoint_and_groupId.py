import requests
import json
import os
import base64
from dotenv import load_dotenv
import urllib3 # SSL警告を無効にするために必要
import time # API呼び出し間の待機に必要（任意）

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

def get_endpoint_mac_and_group():
    """
    ISEからEndpoint一覧を取得し、各Endpointの詳細情報を取得して
    MACアドレスと所属するEndpoint Group IDを表示する。
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
    print("\n--- 各Endpointの詳細情報とGroup ID ---")

    # Step 2: 各EndpointのIDを使用して詳細情報を取得
    endpoint_details_list = []
    for i, endpoint_summary in enumerate(endpoints_summary):
        endpoint_id = endpoint_summary.get('id')
        endpoint_mac_summary = endpoint_summary.get('name', 'MAC不明 (簡易リスト)') # 簡易リストからのMAC

        if not endpoint_id:
            print(f"Endpoint簡易情報 {i+1}: IDが見つかりません。スキップします。")
            continue

        detail_url = f"https://{ise_ip}:9060/ers/config/endpoint/{endpoint_id}"
        # print(f" Endpoint詳細取得 ({endpoint_mac_summary}, ID: {endpoint_id}): {detail_url}") # デバッグ用コメント

        try:
            detail_response = requests.get(detail_url, headers=headers, verify=False, proxies=proxies)
            detail_response.raise_for_status()
            detail_data = detail_response.json()

            # 詳細情報からMACアドレスとGroup IDを抽出
            endpoint_detail = detail_data.get('ERSEndPoint', {})
            mac_address = endpoint_detail.get('mac', endpoint_mac_summary) # 詳細にあればそれを使用、なければ簡易リストから
            group_id = endpoint_detail.get('groupId', 'N/A (詳細情報になし)') # 詳細情報にgroupIdがなければ'N/A (詳細情報になし)'

            print(f"MAC: {mac_address}, Group ID: {group_id}")
            endpoint_details_list.append({'mac': mac_address, 'group_id': group_id})

        except requests.exceptions.RequestException as e:
            print(f" Endpoint詳細情報 ({endpoint_mac_summary}, ID: {endpoint_id}) の取得に失敗しました: {e}")
            if hasattr(e, 'response') and e.response is not None:
                 print(f"  HTTP Status Code: {e.response.status_code}")
                 # print(f"  Response Body: {e.response.text}") # レスポンスボディが大きい場合は注意
            print(f"MAC: {endpoint_mac_summary}, Group ID: エラーにより取得不可")
            endpoint_details_list.append({'mac': endpoint_mac_summary, 'group_id': 'エラーにより取得不可'})
        except json.JSONDecodeError:
             print(f" Endpoint詳細情報 ({endpoint_mac_summary}, ID: {endpoint_id}) のレスポンスがJSON形式ではありません。")
             print(f"MAC: {endpoint_mac_summary}, Group ID: 不明 (不正なレスポンス)")
             endpoint_details_list.append({'mac': endpoint_mac_summary, 'group_id': '不明 (不正なレスポンス)'})
        except Exception as e:
            print(f" Endpoint詳細情報 ({endpoint_mac_summary}, ID: {endpoint_id}) 取得中に予期しないエラーが発生しました: {e}")
            print(f"MAC: {endpoint_mac_summary}, Group ID: 予期しないエラー")
            endpoint_details_list.append({'mac': endpoint_mac_summary, 'group_id': '予期しないエラー'})

        # ISE APIへの短時間での連続アクセスを避けるため、必要に応じて短い待機を入れる
        # time.sleep(0.1) # 例: 0.1秒待機

    print("------------------------------------------")

    return endpoint_details_list

if __name__ == "__main__":
    # 関数を呼び出して結果を取得
    mac_group_list = get_endpoint_mac_and_group()

    if mac_group_list:
        print("\n--- 取得結果サマリー (MAC -> Group ID) ---")
        for item in mac_group_list:
            print(f"MAC: {item['mac']}, Group ID: {item['group_id']}")
        print("-----------------------------------------")
    else:
        print("Endpoint情報の処理が完了しませんでした。")