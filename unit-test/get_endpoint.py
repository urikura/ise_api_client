import requests
import json
import os
import base64
from dotenv import load_dotenv
import urllib3 # SSL警告を無効にするために必要

# 自己署名証明書などを使用している場合のSSL警告を無効にする
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_endpoints_raw():
    """
    ISEからEndpoint一覧を取得する関数。
    .envファイルからISEのIPアドレス、ERSのユーザー名、パスワードを読み込み、
    Basic認証ヘッダーを生成してリクエストを送信する。
    APIからの生レスポンス（JSON形式）をそのまま返す。
    """
    load_dotenv()  # .envファイルをロード
    ise_ip = os.getenv('ISE_IP')  # ISEのIPアドレス
    ers_username = os.getenv('ISE_USERNAME')  # ERSのユーザー名
    ers_password = os.getenv('ISE_PASSWORD')  # ERSのパスワード
    http_proxy = os.getenv('HTTP_PROXY') # プロキシ設定を取得

    if not ise_ip or not ers_username or not ers_password:
        print(".envファイルにISE_IP、ISE_USERNAME、またはISE_PASSWORDが設定されていません")
        return None

    try:
        # Basic認証ヘッダーを生成
        creds = f"{ers_username}:{ers_password}".encode('utf-8')
        encoded_auth = base64.b64encode(creds).decode('utf-8')
        headers = {
            'Accept': 'application/json',
            'authorization': f"Basic {encoded_auth}",
            'cache-control': 'no-cache',
        }

        # プロキシ設定
        proxies = None
        if http_proxy:
            proxies = {
                'http': http_proxy,
                'https': http_proxy,
            }
            print(f"プロキシを使用します: {http_proxy}")

        # URLを組み立て
        # Endpoint一覧を取得するAPIエンドポイントは /ers/config/endpoint です。
        url = f"https://{ise_ip}:9060/ers/config/endpoint"
        print(f"APIリクエストURL: {url}")

        # GETリクエストを送信
        # verify=False はSSL証明書の検証を行わない設定です。本番環境では適切に証明書を設定し、Trueにすることを推奨します。
        response = requests.get(url, headers=headers, verify=False, proxies=proxies)
        response.raise_for_status()  # エラーレスポンスの場合は例外を発生させる

        # レスポンスがJSON形式であることを期待してパース
        data = response.json()
        return data

    except requests.exceptions.RequestException as e:
        print(f"Endpoint情報の取得に失敗しました: {e}")
        if hasattr(e, 'response') and e.response is not None:
             print(f"HTTP Status Code: {e.response.status_code}")
             print(f"Response Body: {e.response.text}")
        return None
    except json.JSONDecodeError:
        print("レスポンスがJSON形式ではありません。ISEからの応答を確認してください。")
        print(f"Response Text: {response.text}")
        return None
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")
        return None

if __name__ == "__main__":
    # 関数を呼び出して結果を取得
    endpoints_data = get_endpoints_raw()
    if endpoints_data:
        # 結果を整形して表示
        print("\n--- ISE Endpoint一覧 API レスポンス (Raw) ---")
        # ensure_ascii=False で日本語などの文字化けを防ぎます
        print(json.dumps(endpoints_data, indent=4, ensure_ascii=False))
        print("----------------------------------------------")

        # 特にgroupIdが存在するかどうかを確認するための追加表示
        if 'SearchResult' in endpoints_data and 'resources' in endpoints_data['SearchResult']:
            print(f"\n取得したEndpoint数: {endpoints_data['SearchResult']['total']}")
            print("\n--- 各Endpoint情報のgroupIdを確認 ---")
            for i, endpoint in enumerate(endpoints_data['SearchResult']['resources']):
                mac = endpoint.get('name', 'MACアドレス不明')
                endpoint_id = endpoint.get('id', 'ID不明')
                group_id = endpoint.get('groupId', 'groupIdキーなし') # groupIdキーが存在しない場合は'groupIdキーなし'と表示
                print(f"Endpoint {i+1} (MAC: {mac}, ID: {endpoint_id}): groupId = {group_id}")
            print("------------------------------------------")

    else:
        print("Endpoint情報の取得に失敗しました。エラーメッセージを確認してください。")

