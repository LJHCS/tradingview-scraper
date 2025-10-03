"""
Module providing functionality to connect to TradingView's WebSocket API 
for real-time trade data streaming. This module includes classes and methods 
to manage WebSocket connections, send messages, and handle session management.
"""

import json
import string
import logging
import secrets
import re      # 추가
import requests # 추가

from websocket import create_connection

# Configure logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class StreamHandler:
    """
    Class for managing a WebSocket connection to a trading data service.
    """

    def __init__(self, websocket_url: str, session_id: str = None):
        """
        Initializes the StreamData instance.
        Args:
            websocket_url (str): The URL of the WebSocket server.
            # jwt_token 인자를 session_id로 변경
            session_id (str, optional): TradingView sessionid cookie value for authentication.
        """
        # session_id로 auth_token을 가져오는 로직 추가
        auth_token = "unauthorized_user_token"
        if session_id:
            token = self._get_auth_token(session_id)
            if token:
                auth_token = token
            else:
                logging.error("Failed to get auth token. Connecting as unauthorized user.")

        self.request_header = {
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
            "Cache-Control": "no-cache",
            "Connection": "Upgrade",
            "Host": "data.tradingview.com",
            "Origin": "https://www.tradingview.com",
            "Pragma": "no-cache",
            "Sec-WebSocket-Extensions": "permessage-deflate; client_max_window_bits",
            "Upgrade": "websocket",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/107.0.0.0 Safari/537.36"
            )
        }
        self.ws = create_connection(websocket_url, headers=self.request_header)
        self._initialize(auth_token=auth_token)

    # session_id로 토큰을 가져오는 작은 함수 하나만 추가
    def _get_auth_token(self, session_id: str) -> str | None:
        try:
            response = requests.get(
                'https://www.tradingview.com/disclaimer/',
                cookies={'sessionid': session_id}
            )
            response.raise_for_status()
            match = re.search(r'"auth_token":"(.+?)"', response.text)
            return match.group(1) if match else None
        except requests.RequestException as e:
            logging.error(f"HTTP request failed while getting auth token: {e}")
            return None

    # jwt_token 변수명을 auth_token으로만 변경 (기능은 동일)
    def _initialize(self, auth_token: str):
        """
        Initializes the quote and chart sessions and sets up authentication.
        """
        quote_session = self.generate_session(prefix="qs_")
        chart_session = self.generate_session(prefix="cs_")
        logging.info("Quote session generated: %s, Chart session generated: %s",
                     quote_session, chart_session)

        self._initialize_sessions(quote_session, chart_session, auth_token)
        self.quote_session = quote_session
        self.chart_session = chart_session

    # --- 이하 모든 메서드는 원래 코드와 완전히 동일합니다 ---

    def generate_session(self, prefix: str) -> str:
        random_string = ''.join(secrets.choice(string.ascii_lowercase) for _ in range(12))
        return prefix + random_string

    def prepend_header(self, message: str) -> str:
        message_length = len(message)
        return f"~m~{message_length}~m~{message}"

    def construct_message(self, func: str, param_list: list) -> str:
        return json.dumps({"m": func, "p": param_list}, separators=(',', ':'))

    def create_message(self, func: str, param_list: list) -> str:
        return self.prepend_header(self.construct_message(func, param_list))

    def send_message(self, func: str, args: list):
        message = self.create_message(func, args)
        logging.debug("Sending message: %s", message)
        try:
            self.ws.send(message)
        except (ConnectionError, TimeoutError) as e:
            logging.error("Failed to send message: %s", e)

    # jwt_token 변수명을 auth_token으로만 변경 (기능은 동일)
    def _initialize_sessions(self, quote_session: str, chart_session: str, auth_token: str):
        """
        Initializes WebSocket sessions for quotes and charts by sending setup messages.
        """
        self.send_message("set_auth_token", [auth_token])
        self.send_message("set_locale", ["en", "US"])
        self.send_message("chart_create_session", [chart_session, ""])
        self.send_message("quote_create_session", [quote_session])
        self.send_message("quote_set_fields", [quote_session, *self._get_quote_fields()])
        self.send_message("quote_hibernate_all", [quote_session])

    def _get_quote_fields(self) -> list:
        return [
            "ch", "chp", "current_session", "description", "local_description",
            "language", "exchange", "fractional", "is_tradable", "lp",
            "lp_time", "minmov", "minmove2", "original_name", "pricescale",
            "pro_name", "short_name", "type", "update_mode", "volume",
            "currency_code", "rchp", "rtc"
        ]