import datetime
import math
import os

import pytz as pytz
import requests
import json


class Stock:
    def __init__(self):
        # 환경 변수 설정
        self.APP_KEY = os.environ.get("APP_KEY")
        self.APP_SECRET = os.environ.get("APP_SECRET")
        self.ACCESS_TOKEN = {}
        self.URL_BASE = os.environ.get("URL_BASE")
        self.headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {self.get_access_token}",
            "appKey": self.APP_KEY,
            "appSecret": self.APP_SECRET,
        }

    @property
    def get_access_token(self):
        """토큰 발급"""
        now = datetime.datetime.now()
        if self.ACCESS_TOKEN.get("expires_in") \
                and self.ACCESS_TOKEN.get("expires_in") > now:
            return self.ACCESS_TOKEN.get("token")
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.APP_KEY,
            "appsecret": self.APP_SECRET
        }
        url = f"{self.URL_BASE}/oauth2/tokenP"
        res = requests.post(url, headers=headers, data=json.dumps(body))
        self.ACCESS_TOKEN = {
            "token": res.json()["access_token"],
            "expires_in": now + datetime.timedelta(seconds=int(res.json()["expires_in"]))
        }
        print(res.json()["access_token"])
        return res.json()["access_token"]

    def get_kor_current_price(self, code: str):
        """현재가 조회"""
        path = "uapi/domestic-stock/v1/quotations/inquire-price"
        url = f"{self.URL_BASE}/{path}"
        headers = self.headers
        headers["tr_id"] = "FHKST01010100"
        params = {
            "fid_cond_mrkt_div_code": "J",
            "fid_input_iscd": code,
        }
        res = requests.get(url, headers=headers, params=params)
        current_price = int(res.json()["output"]["stck_prpr"])
        start_price = int(res.json()["output"]["stck_sdpr"])
        rate = ((current_price - start_price) / start_price) * 100
        rate = math.floor(rate * 100) / 100
        rate = f"+{rate}" if rate > 0 else str(rate)
        return current_price, start_price, rate

    def get_kor_daily_price(self):
        """국내 지수"""
        path = "uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice"
        url = f"{self.URL_BASE}/{path}"
        headers = self.headers
        headers["tr_id"] = "FHKUP03500100"
        headers["custtype"] = "P"
        now = datetime.datetime.now().astimezone(
            pytz.timezone("Asia/Seoul")
        ).strftime("%Y%m%d")
        options = [
            ("코스피", "0001"),
        ]
        response = {}
        for option in options:
            params = {
                "FID_COND_MRKT_DIV_CODE": "U",
                "FID_INPUT_ISCD": option[1],
                "FID_INPUT_DATE_1": now,
                "FID_INPUT_DATE_2": now,
                "FID_PERIOD_DIV_CODE": "D"
            }
            res = requests.get(url, headers=headers, params=params)
            data = (
                float(res.json()["output1"]["bstp_nmix_prpr"]),
                float(res.json()["output1"]["prdy_nmix"]),
                res.json()["output1"]["bstp_nmix_prdy_ctrt"]
            )
            response.setdefault(option[0], data)
        return response

    def get_usa_daily_price(self):
        """해외 지수/환율 조회"""
        path = "uapi/overseas-price/v1/quotations/inquire-daily-chartprice"
        url = f"{self.URL_BASE}/{path}"
        headers = self.headers
        headers["tr_id"] = "FHKST03030100"
        headers["custtype"] = "P"
        now = datetime.datetime.now().astimezone(
            pytz.timezone("Asia/Seoul")
        ).strftime("%Y%m%d")
        options = [
            ("다우지수", ".DJI", "N"),
            ("환율", "FX@KRW", "X"),
        ]
        response = {}
        for option in options:
            params = {
                "FID_COND_MRKT_DIV_CODE": option[2],
                "FID_INPUT_ISCD": option[1],
                "FID_INPUT_DATE_1": now,
                "FID_INPUT_DATE_2": now,
                "FID_PERIOD_DIV_CODE": "D"
            }
            res = requests.get(url, headers=headers, params=params)
            data = (
                float(res.json()["output1"]["ovrs_nmix_prpr"]),
                float(res.json()["output1"]["ovrs_nmix_prdy_clpr"]),
                res.json()["output1"]["prdy_ctrt"]
            )
            response.setdefault(option[0], data)
        return response

    def get_usa_current_price(self, market: str, code: str):
        """현재가 조회"""
        path = "uapi/overseas-price/v1/quotations/price"
        url = f"{self.URL_BASE}/{path}"
        headers = self.headers
        headers["tr_id"] = "HHDFS00000300"
        params = {
            "AUTH": "",
            "EXCD": market,
            "SYMB": code,
        }
        res = requests.get(url, headers=headers, params=params)
        return float(res.json()["output"]["last"]), float(res.json()["output"]["base"]), res.json()["output"]["rate"]

    def get_kor_range_price(self, code: str):
        path = "/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion"
        url = f"{self.URL_BASE}/{path}"
        headers = self.headers
        headers["tr_id"] = "FHPST01060000"
        headers["custtype"] = "P"
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": code,
            "FID_INPUT_HOUR_1": "140101"
        }
        res = requests.get(url, headers=headers, params=params)
        data_list = res.json().get("output2")
        for data in data_list:
            체결_시간 = data.get("stck_cntg_hour")
            전일_대비_부호 = data.get("prdy_vrss_sign")

            pass
        return data_list

    def run(self):
        # 보유 리스트 불러오기
        file = "./items.json"
        if os.path.isfile(file):
            with open(file, "r") as f:
                symbol_file = json.load(f)
            symbol_list = symbol_file.get("items")
        else:
            symbol_list = []

        # 지수/환율
        daily_price = self.get_usa_daily_price()
        daily_price.update(self.get_kor_daily_price())

        results = []
        total_price = 0
        all_price = 0

        # print(self.get_kor_range_price("183490"))
        for symbol in symbol_list:
            # 데이터 조회
            market = symbol.get("market")
            code = symbol.get("code")  # 종목 코드
            balance = symbol.get("balance")  # 보유량
            buy_price = symbol.get("price")  # 매수가
            exchange_rate = 1 if market == "KOR" else int(daily_price.get("환율")[0])  # 환율

            # 현재가 조회
            current_price, start_price, rate = self.get_kor_current_price(code=code)\
                if market == "KOR" else self.get_usa_current_price(market=market, code=code)
            # 가격 종합
            price = int(((current_price * exchange_rate) * balance) - ((buy_price * exchange_rate) * balance))

            # 총 손익율
            total_rate = ((current_price - buy_price) / buy_price) * 100
            total_rate = math.floor(total_rate * 100) / 100
            border_color = "border-danger" if "+" in rate else "border-primary"
            total_rate = f"+{total_rate}" if total_rate > 0 else str(total_rate)

            # 오늘 손익
            today_price = int(((current_price - start_price) * exchange_rate) * balance)

            # 현재가
            current_price = int(current_price * exchange_rate)

            # 잔고
            symbol_total_price = current_price * balance

            web_kor_url = "https://m.stock.naver.com/domestic/stock/" + symbol.get("code") + "/discuss"
            web_usa_url = f"https://m.stock.naver.com/worldstock/stock/" + symbol.get("code") + "/discuss"
            web_url = web_kor_url if market == "KOR" else web_usa_url
            results.append({
                "name": symbol.get("name"),
                "current_price": format(current_price, ","),
                "price": format(price, ","),
                "percent": ((current_price - buy_price) / buy_price) * 100,
                "message": f"""
                <a href='""" + web_url + f"""' target='_blank' style='color: black;text-decoration: none;'>
                    <div class="card {border_color} mb-3 card-block">
                      <div class="card-header h5">{symbol.get("name")}</div>
                      <ul class="list-group list-group-flush">
                        <li class="list-group-item">💰 현재가 : {format(current_price, ",")} 원 [{str(rate).strip()}%]</li>
                        <li class="list-group-item">🔒 오늘 손익 : {format(today_price, ",")} 원</li>
                        <li class="list-group-item">🚀 총 손익 : {format(price, ",")} 원 [{total_rate}%]</li>
                      </ul>
                      <div class="card-footer text-muted">
                        총 {format(symbol_total_price, ",")} 원
                      </div>
                    </div>
                </a>
                """
            })
            total_price += price
            all_price += current_price * balance

        # 현재 시간
        now = datetime.datetime.now().astimezone(
            pytz.timezone("Asia/Seoul")
        ).strftime("%Y-%m-%d %H:%M:%S")
        return {
            "now": now,
            "results": results,
            "total_price": format(total_price, ","),
            "total": f"""
                <div class="card card-block mb-3">
                  <ul class="list-group list-group-flush">
                    <li class="list-group-item">⏰ {now}</li>
                  </ul>
                </div>
                <div class="card bg-light mb-3">
                    <div class="card-header h5">총 합계</div>
                    <div class="card-body">
                        <h5 class="card-title">{format(total_price, ",")} 원</h5>
                        ( {format(int(all_price), ",")}원 )
                    </div>
                </div>
            """,
            "market_now": f"""
                <div class="card bg-secondary card-block mb-3">
                    <div class="card-header text-white h5">시장 현황</div>
                    <ul class="list-group list-group-flush text-dark">
                        <li class="list-group-item">➕ 코스피 : {daily_price["코스피"][0]}
                        [{"+" + daily_price["코스피"][2] if "-" not in daily_price["코스피"][2] else daily_price["코스피"][2]}%]</li>
                        <li class="list-group-item">➕ 다우 지수 : {daily_price["다우지수"][0]} 
                        [{"+" + daily_price["다우지수"][2] if "-" not in daily_price["다우지수"][2] else daily_price["다우지수"][2]}%]</li>
                        <li class="list-group-item">➕ 환율 : {daily_price["환율"][0]} 
                        [{"+" + daily_price["환율"][2] if "-" not in daily_price["환율"][2] else daily_price["환율"][2]}%]</li>
                    </ul>
                </div>
            """
        }
