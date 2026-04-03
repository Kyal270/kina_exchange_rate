import os

# Code ရဲ့ အပေါ်ဆုံးနားမှာ ဒါလေး ပြင်လိုက်ပါ
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
import time
import requests
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager



# 🎯 Market Gap Settings
USD_GAP = 1.3239  # +32.39%
CNY_GAP = 1.3674  # +36.74%
SGD_GAP = 1.3239  # +32.39% (Adjust if different)

def get_google_rate(url):
    """Fetch base rate from Google Finance"""
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(res.content, "html.parser")
        return float(soup.find("div", {"data-last-price": True})["data-last-price"])
    except:
        return None

def scrape_bsp_final_fix():
    print("⏳ Connecting to BSP PNG... Fetching TT Sell rates for USD, CNY, and SGD...")
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # Initialize results dictionary
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

            # Check for target currencies in the row
            row_text = " ".join(cols).upper()
            
            code_idx = -1
            for i, c in enumerate(cols):
                if c in ["USD", "CNY", "SGD"]:
                    code_idx = i
                    break
            
            if code_idx != -1:
                code = cols[code_idx]
                try:
                    # Target TT Sell (Index + 4 or fallback to Last Column)
                    target_val = cols[code_idx + 4].replace(",", "")
                    
                    if not target_val or float(target_val) == 0:
                        target_val = cols[-1].replace(",", "")
                    
                    if target_val:
                        # Extract the float value using regex
                        found_num = re.findall(r"\d+\.\d{4}", target_val)
                        if found_num:
                            bsp_rates[code] = float(found_num[0])
                except:
                    continue

    finally:
        driver.quit()
    return bsp_rates

def run_script():
    # 1. Scrape BSP Rates
    bsp = scrape_bsp_final_fix()
    
    # 2. Fetch Google Market Rates
    g_usd = get_google_rate("https://www.google.com/finance/quote/USD-MMK")
    g_cny = get_google_rate("https://www.google.com/finance/quote/CNY-MMK")
    g_sgd = get_google_rate("https://www.google.com/finance/quote/SGD-MMK")

    if bsp and bsp["USD"] and g_usd:
        # Calculate Myanmar Market Prices
        m_usd = g_usd * USD_GAP
        m_cny = g_cny * CNY_GAP if g_cny else 0
        m_sgd = g_sgd * SGD_GAP if g_sgd else 0

        # Calculate Final PGK to MMK Rates
        pgk_to_mmk_usd = bsp["USD"] * m_usd
        pgk_to_mmk_cny = bsp["CNY"] * m_cny if bsp["CNY"] else 0
        pgk_to_mmk_sgd = bsp["SGD"] * m_sgd if bsp["SGD"] else 0

        # Construct English Telegram Message
        msg = "🏦 *Kina Exchange Rates*\n"
        msg += "----------------------------------------\n"
        msg += f"🇺🇸 *USD/MMK Market:* `{m_usd:,.0f}`\n"
        msg += f"🇨🇳 *CNY/MMK Market:* `{m_cny:,.0f}`\n"
        msg += f"🇸🇬 *SGD/MMK Market:* `{m_sgd:,.0f}`\n"
        msg += "----------------------------------------\n"
        msg += "🇵🇬 *1 PGK -> Myanmar Kyats*\n"
        msg += f"• Via USD: *{pgk_to_mmk_usd:,.2f}* MMK\n"
        msg += f"• Via CNY: *{pgk_to_mmk_cny:,.2f}* MMK\n"
        msg += f"• Via SGD: *{pgk_to_mmk_sgd:,.2f}* MMK\n"
        msg += "----------------------------------------\n"
        msg += f"ℹ️ _BSP Verified: U:{bsp['USD']:.4f} | C:{bsp['CNY']:.4f} | S:{bsp['SGD']:.4f}_\n"
        msg += f"🕒 _Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}_"

        # Send to Telegram
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        
        print(f"✅ Success! Message sent to Telegram.")
        print(f"Rates used -> USD: {bsp['USD']}, CNY: {bsp['CNY']}, SGD: {bsp['SGD']}")
    else:
        print("❌ Error: Could not fetch complete data from BSP or Google.")

if __name__ == "__main__":
    run_script()
