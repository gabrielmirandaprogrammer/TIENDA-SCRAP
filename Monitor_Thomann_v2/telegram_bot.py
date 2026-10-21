import requests
from config import TOKEN,CHAT_ID
API=f"https://api.telegram.org/bot{TOKEN}"
def send(msg):
    requests.post(f"{API}/sendMessage",json={"chat_id":CHAT_ID,"text":msg})
