import os
import time
import requests
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# 🎯 သင့် Google Apps Script ရဲ့ Web App URL ကို ဒီမှာထည့်ပါ
GAS_WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwOE_rjY1ZHIVnPHWHYXh-ze14okXdQQZ2IAQfGUYZX_k_6zkEGWCT1KQz1NGDzEJ14/exec"

def get_manual_rates():
    """Google Apps Script မှ ဈေးနှုန်းများနှင့် တက်/ကျ မြှားများကို ဆွဲယူမည်"""
    print("⏳ Fetching manual rates from Telegram Bot...")
    try:
        res = requests.get(GAS_WEB_APP_URL, timeout=15)
        data = res.json()
        return (
            float(data["usd"]), float(data["cny"]), float(data["sgd"]),
            data.get("usd_trend", "➖"), data.get("cny_trend", "➖"), data.get("sgd_trend", "➖")
        )
    except Exception as e:
        print(f"❌ Could not fetch rates from GAS: {e}. Using default rates.")
        return 4500.0, 620.0, 3300.0, "➖", "➖", "➖"
def scrape_bsp_final_fix():
    print("⏳ Connecting to BSP PNG... Fetching TT Sell rates for USD, CNY, and SGD...")
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    bsp_rates = {"USD": None, "CNY": None, "SGD": None}

    try:
        driver.get("https://www.bsp.com.pg/international-services/foreign-exchange/exchange-rates/")
        time.sleep(7) 
        soup = BeautifulSoup(driver.page_source, "html.parser")
        table = soup.find("table")
        if not table: return None

        for tr in table.find_all("tr"):
            cols = [td.get_text(strip=True) for td in tr.find_all("td")]
            if len(cols) < 2: continue
            
            code_idx = -1
            for i, c in enumerate(cols):
                if c in ["USD", "CNY", "SGD"]:
                    code_idx = i
                    break
            
            if code_idx != -1:
                code = cols[code_idx]
                try:
                    target_val = cols[code_idx + 4].replace(",", "")
                    if not target_val or float(target_val) == 0:
                        target_val = cols[-1].replace(",", "")
                    if target_val:
                        found_num = re.findall(r"\d+\.\d{4}", target_val)
                        if found_num:
                            bsp_rates[code] = float(found_num[0])
                except:
                    continue
    finally:
        driver.quit()
    return bsp_rates

def run_script():
    # 🎯 မြှားလေးတွေကိုပါ လက်ခံယူပါမယ်
    MANUAL_USD_MMK, MANUAL_CNY_MMK, MANUAL_SGD_MMK, usd_trend, cny_trend, sgd_trend = get_manual_rates()
    print(f"📌 Rates to use -> USD: {MANUAL_USD_MMK}, CNY: {MANUAL_CNY_MMK}, SGD: {MANUAL_SGD_MMK}")

    bsp = scrape_bsp_final_fix()
    
    if bsp and bsp["USD"]:
        pgk_to_mmk_usd = bsp["USD"] * MANUAL_USD_MMK
        pgk_to_mmk_cny = bsp["CNY"] * MANUAL_CNY_MMK if bsp["CNY"] else 0
        pgk_to_mmk_sgd = bsp["SGD"] * MANUAL_SGD_MMK if bsp["SGD"] else 0

        # 🎯 စာသားဘေးမှာ မြှားလေးတွေ ကပ်ထည့်ပါမယ်
        msg = "🏦 *Kina Exchange Rates*\n"
        msg += "----------------------------------------\n"
        msg += f"🇺🇸 *USD/MMK Market:* `{MANUAL_USD_MMK:,.0f}` {usd_trend}\n"
        msg += f"🇨🇳 *CNY/MMK Market:* `{MANUAL_CNY_MMK:,.0f}` {cny_trend}\n"
        msg += f"🇸🇬 *SGD/MMK Market:* `{MANUAL_SGD_MMK:,.0f}` {sgd_trend}\n"
        msg += "----------------------------------------\n"
        msg += "🇵🇬 *1 PGK -> Myanmar Kyats*\n"
        msg += f"• Via USD: *{pgk_to_mmk_usd:,.2f}* MMK\n"
        msg += f"• Via CNY: *{pgk_to_mmk_cny:,.2f}* MMK\n"
        msg += f"• Via SGD: *{pgk_to_mmk_sgd:,.2f}* MMK\n"
        msg += "----------------------------------------\n"
        msg += f"ℹ️ _BSP Verified: U:{bsp['USD']:.4f} | C:{bsp['CNY']:.4f} | S:{bsp['SGD']:.4f}_\n"
        msg += f"🕒 _Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}_"

        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        print(f"✅ Success! Message sent to Telegram.")
    else:
        print("❌ Error: Could not fetch complete data from BSP.")

if __name__ == "__main__":
    run_script()
