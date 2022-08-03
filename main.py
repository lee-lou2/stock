import json
import os
from typing import List

from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from starlette.staticfiles import StaticFiles
from dotenv import load_dotenv

from stock import Stock


# 환경 변수 조회
load_dotenv(dotenv_path=".env", verbose=True)

# 앱 실행
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# 서비스 초기화
stock = Stock()


@app.get("/")
async def get():
    host = os.environ.get("BASE_HOST")

    file = "./items.json"
    if os.path.isfile(file):
        with open(file, "r") as f:
            symbol_list = json.load(f)
    else:
        symbol_list = {}

    return HTMLResponse("""
<!DOCTYPE html>
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1, minimum-scale=1, maximum-scale=1, viewport-fit=cover" />
        <meta http-equiv="Content-Security-Policy" content="upgrade-insecure-requests">
        <meta
            property="og:url" """ + f"""
            content="https://{host}" """ + """
        />
        <meta
            property="og:title"
            content="습관 만들기"
        />
        <meta
            property="og:description"
            content="기상, 운동, 메모 습관 메이커 😍"
        />
        <meta
            property="og:image"
            content="/static/favicon.png"
        />
        <link id="favicon" rel="icon" type="image/x-icon" href="static/favicon.ico">
        <title>실시간 주식 현황</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@4.6.1/dist/css/bootstrap.min.css">
    </head>
    <body>
        <div class="d-flex p-2 flex-column">
            <div>
                <button type="button" id="conn-btn" class="btn mb-3 btn-primary btn-lg btn-block" onclick="connectWebSocket(event);">
                    <spen>연결하기</spen>
                </button>
            </div>
            <div id="items"></div>
            <textarea class="form-control mb-3" id="symbol-list" rows="3"></textarea>
            <button type="button" class="btn mb-3 btn-dark btn-lg btn-block" onclick="updateItems();">
                <spen>저장하기</spen>
            </button>
        </div>
        <script>
            var ws = null;
            var status = 0; 
            const btn = document.getElementById('conn-btn');
            const textArea = document.getElementById('symbol-list');
            
            function connectWebSocket() {
                // 웹소켓 초기화
                ws = new WebSocket("ws://""" + host + """/ws");
                // 데이터 받아와서 적용
                ws.onmessage = function(event) {
                    status = 2;
                    const items = document.getElementById('items');
                    items.innerHTML = event.data;
                };
            };
            function updateItems() {
                fetch('https://""" + host + """/items/', {
                    method: 'POST',
                    headers: {
                      'Content-Type': 'application/json',
                    },
                    body: textArea.value
                })
                .then((res) => location.reload())
                .then((data) => console.log(data));
            };
            function sendMessage(event) {
                if (ws != null) {
                    try {
                        // 상태 확인
                        if (status == 1) {
                            // 재실행
                            location.reload();
                        } else if (status == 0) {
                            // 최초 실행
                            status = 3;
                            btn.setAttribute('disabled', true);
                            btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
                            
                            // 리스트 설정
                            var obj = """ + f""" {symbol_list} """ + """;
                            var pretty = JSON.stringify(obj, undefined, 4);
                            textArea.innerHTML = pretty;
                            textArea.style.height = textArea.scrollHeight + 'px';
                            
                            setTimeout(sendMessage, 1000);
                        }else {
                            // 상태 정상
                            status = 1;
                            // 소켓 데이터 전송
                            ws.send('');
                            setTimeout(sendMessage, 5000);
                        }
                    } catch (error) {
                        // 재실행
                        location.reload();
                    }
                } else {
                    // 최초 상태
                    btn.removeAttribute('disabled');
                    btn.innerHTML = '<span>연결하기</span>';
                    setTimeout(sendMessage, 1000);
                }
            };
            sendMessage();
            connectWebSocket();
        </script>
        <script src="https://code.jquery.com/jquery-3.2.1.slim.min.js" integrity="sha384-KJ3o2DKtIkvYIK3UENzmM7KCkRr/rE9/Qpg6aAZGJwFDMVNA/GpGFF93hXpG5KkN" crossorigin="anonymous"></script>
        <script src="https://cdn.jsdelivr.net/npm/popper.js@1.12.9/dist/umd/popper.min.js" integrity="sha384-ApNbgh9B+Y1QKtv3Rn7W3mgPxhU9K/ScQsAP7hUibX39j7fakFPskvXusvfa0b4Q" crossorigin="anonymous"></script>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@4.0.0/dist/js/bootstrap.min.js" integrity="sha384-JZR6Spejh4U02d8jOt6vLEHfe/JQGiRRSQQxSfFWpi1MquVdAyjUar5+76PVCmYl" crossorigin="anonymous"></script>
    </body>
</html>
""")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """웹 소켓 - 데이터 업데이트"""
    await websocket.accept()
    while True:
        try:
            await websocket.receive_text()
            response = stock.run()
            message = "".join([res.get("message") for res in response.get("results")])
            data = response.get("total") + message + response.get("market_now")
            await websocket.send_text(data)
        except Exception as ex:
            print(ex)
            break


class Item(BaseModel):
    """종목 상세"""
    market: str
    code: str
    name: str
    balance: int
    price: float


class Items(BaseModel):
    """종목 리스트"""
    items: List[Item]


@app.post("/items/")
async def update_items(items: Items):
    """파일 업데이트"""
    with open("./items.json", "w+") as f:
        json.dump(items.dict(), f)
    return items
