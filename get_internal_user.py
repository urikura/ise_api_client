import requests
import json
import os
import base64
from dotenv import load_dotenv
import logging
import urllib3

# 警告を抑制
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ロギング設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)


def get_internal_user():
    """
    ISEからInternal User情報を取得する関数。
    .envファイルからISEのIPアドレス、ERSのユーザー名、パスワードを読み込み、
    Basic認証ヘッダーを生成してリクエストを送信する。
    """
    load_dotenv()  # .envファイルをロード
    ise_host = os.getenv('ISE_IP')  # ISEのIPアドレス
    ers_username = os.getenv('ISE_USERNAME')  # ERSのユーザー名
    ers_password = os.getenv('ISE_PASSWORD')  # ERSのパスワード
    http_proxy = os.getenv('HTTP_PROXY') # HTTPプロキシ設定を取得

    if not ise_host or not ers_username or not ers_password:
        logger.error(
            ".envファイルにISE_IP、ISE_USERNAME、またはISE_PASSWORDが設定されていません"
        )
        return None

    try:
        # Basic認証ヘッダーを生成
        creds = f"{ers_username}:{ers_password}".encode('utf-8')
        encoded_auth = base64.b64encode(creds).decode('utf-8')
        headers = {
            'accept': 'application/json',
            'authorization': f"Basic {encoded_auth}",
            'cache-control': 'no-cache',
        }

        # URLを組み立て
        url = f"https://{ise_host}:9060/ers/config/internaluser/"
        logger.debug(f"Request URL: {url}")  # リクエストURLをログ出力

        # プロキシ設定
        proxies = {}
        if http_proxy:
            proxies = {
                'http': http_proxy,
                'https': http_proxy,
            }
            logger.debug(f"Using proxy: {proxies}")  # プロキシ設定をログ出力
        else:
            logger.debug("Not using a proxy") # プロキシを使用しないことをログ出力

        # GETリクエストを送信
        response = requests.get(url, headers=headers, verify=False, proxies=proxies)
        response.raise_for_status()  # エラーレスポンスの場合は例外を発生させる
        data = response.json()
        logger.debug(f"Response data: {data}")  # レスポンスデータをログ出力
        return data
    except requests.exceptions.RequestException as e:
        logger.error(f"Internal User情報の取得に失敗しました: {e}")
        return None
    except json.JSONDecodeError:
        logger.error("レスポンスがJSON形式ではありません")
        return None
    except Exception as e:
        logger.error(f"予期しないエラーが発生しました: {e}")
        return None



if __name__ == "__main__":
    # 関数を呼び出して結果を取得
    internal_user_data = get_internal_user()
    if internal_user_data:
        # 結果を整形して表示
        print(json.dumps(internal_user_data, indent=4, ensure_ascii=False))
    else:
        print("Internal User情報の取得に失敗しました。")

