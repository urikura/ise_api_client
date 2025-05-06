import requests
import json
import os
import base64
from dotenv import load_dotenv

def get_identity_groups():
    """
    ISEからIdentity Group一覧を取得する関数。
    .envファイルからISEのIPアドレス、ERSのユーザー名、パスワードを読み込み、
    Basic認証ヘッダーを生成してリクエストを送信する。
    """
    load_dotenv()  # .envファイルをロード
    ise_ip = os.getenv('ISE_IP')  # ISEのIPアドレス
    ers_username = os.getenv('ISE_USERNAME')  # ERSのユーザー名
    ers_password = os.getenv('ISE_PASSWORD')  # ERSのパスワード

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

        # URLを組み立て
        url = f"https://{ise_ip}:9060/ers/config/identitygroup"

        # GETリクエストを送信
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status()  # エラーレスポンスの場合は例外を発生させる
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Identity Group情報の取得に失敗しました: {e}")
        return None
    except json.JSONDecodeError:
        print("レスポンスがJSON形式ではありません")
        return None
    except Exception as e:
        print(f"予期しないエラーが発生しました: {e}")
        return None

if __name__ == "__main__":
    # 関数を呼び出して結果を取得
    identity_groups_data = get_identity_groups()
    if identity_groups_data:
        # 結果を整形して表示
        print(json.dumps(identity_groups_data, indent=4, ensure_ascii=False))
    else:
        print("Identity Group情報の取得に失敗しました。")
