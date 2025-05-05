import os
import base64
from dotenv import load_dotenv
import logging

# ロギング設定
logging.basicConfig(
    level=logging.DEBUG,  # デバッグレベルに設定
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)  # ロガーを取得


def create_authorization_header():
    """
    .envファイルからユーザー名とパスワードを読み込み、
    Basic認証ヘッダーを生成する関数。
    """
    load_dotenv()  # .envファイルをロード
    logger.debug(".envファイルをロードしました")  # ロードしたことをログに出力
    username = os.getenv('ISE_USERNAME')  # ユーザー名を取得
    password = os.getenv('ISE_PASSWORD')  # パスワードを取得
    logger.debug(f"ISE_USERNAME: {username}, ISE_PASSWORD: {password}") # ユーザ名とパスワードをログ出力

    if not username or not password:
        logger.error(".envファイルにISE_USERNAMEまたはISE_PASSWORDが設定されていません")
        return None  # エラー時はNoneを返す

    try:
        # ユーザー名とパスワードをコロンで結合し、バイト列に変換
        creds = f"{username}:{password}".encode('utf-8')
        logger.debug(f"結合後のクレデンシャル: {creds}")  # クレデンシャルをログ出力
        # バイト列をBase64エンコード
        base64_creds = base64.b64encode(creds).decode('utf-8')
        logger.debug(f"Base64エンコード後のクレデンシャル: {base64_creds}")  # Base64エンコード後のクレデンシャルをログ出力
        # Authorizationヘッダーの値を組み立て
        authorization_header = f"Basic {base64_creds}"
        logger.debug(f"Authorization Header: {authorization_header}")  # ヘッダーをログ出力（セキュリティのため、実際の値はログレベルをINFO以上にしてマスクすることを推奨）
        return authorization_header
    except Exception as e:
        logger.error(f"Authorizationヘッダーの生成に失敗しました: {e}")
        return None  # エラー時はNoneを返す


if __name__ == "__main__":
    # 関数を呼び出して結果を取得
    auth_header = create_authorization_header()
    if auth_header:
        print("Authorizationヘッダーが生成されました:")
        print(auth_header)  # ヘッダーを画面出力
    else:
        print("Authorizationヘッダーの生成に失敗しました。")

