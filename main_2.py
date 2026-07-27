import requests
from bs4 import BeautifulSoup
import re
import os
from datetime import datetime

def print_with_time(message):
    """带时间戳的打印"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_time}] {message}")

def checkin_and_get_traffic(cookie):
    """使用 Cookie 直接尝试多个域名进行签到和获取流量"""
    # 备用域名列表
    base_urls = [
        "https://ikuuu.fyi",
        "https://ikuuu.win",
        "https://ikuuu.de"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
        'Cookie': cookie
    }

    session = requests.Session()
    working_url = None

    # 1. 寻找可用的域名并执行签到
    for base_url in base_urls:
        print_with_time(f"🌐 尝试使用域名: {base_url} ...")
        
        req_headers = headers.copy()
        req_headers.update({
            'Origin': base_url,
            'Referer': f"{base_url}/user"
        })
        
        checkin_url = f"{base_url}/user/checkin"
        
        try:
            res = session.post(checkin_url, headers=req_headers, timeout=10)
            if res.status_code == 200:
                try:
                    data = res.json()
                    msg = data.get('msg', '')
                    if data.get('ret') == 1:
                        print_with_time(f"✅ 签到成功 [{base_url}]: {msg}")
                    elif "已经签到" in msg:
                        print_with_time(f"ℹ️ 今日已签到 [{base_url}]: {msg}")
                    else:
                        print_with_time(f"❌ 签到失败 [{base_url}]: {msg}")
                    
                    working_url = base_url
                    break  # 签到成功或确认已签到，跳出域名遍历
                except Exception:
                    print_with_time(f"⚠️ {base_url} 响应非 JSON，可能 Cookie 已失效或域名重定向")
            else:
                print_with_time(f"⚠️ {base_url} 请求状态码异常: {res.status_code}")
        except Exception as e:
            print_with_time(f"⚠️ 连接 {base_url} 失败: {str(e)}")

    if not working_url:
        print_with_time("❌ 所有域名访问失败，请检查 Cookie 是否已过期或环境变量设置。")
        return False

    # 2. 获取流量信息
    try:
        user_url = f"{working_url}/user"
        res = session.get(user_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        traffic_cards = soup.find_all('div', class_='card-statistic-2')
        print_with_time("📊 流量使用情况:")
        print("-" * 40)
        
        for card in traffic_cards:
            header = card.find('h4')
            if header and '剩余流量' in header.text:
                body = card.find('div', class_='card-body')
                if body:
                    remaining_traffic = re.sub(r'\s+', ' ', body.get_text(strip=True))
                    print(f"📈 剩余流量: {remaining_traffic}")
                
                stats = card.find('div', class_='card-stats-title')
                if stats:
                    today_used_text = re.sub(r'\s+', ' ', stats.get_text(strip=True))
                    match = re.search(r':\s*(.+)', today_used_text)
                    if match:
                        print(f"📊 今日已用: {match.group(1).strip()}")
                    else:
                        print(f"📊 今日使用情况: {today_used_text}")
        print("-" * 40)
    except Exception as e:
        print_with_time(f"❌ 获取流量信息失败: {str(e)}")

    return True

if __name__ == "__main__":
    print("=" * 60)
    print_with_time("🚀 iKuuu 免登录 Cookie 签到程序启动")
    print("=" * 60)
    
    cookies = []
    
    # 兼容 IKUUU_COOKIE 和 IKUUU_COOKIE_1, IKUUU_COOKIE_2...
    single_cookie = os.getenv('IKUUU_COOKIE')
    if single_cookie:
        cookies.append(single_cookie)
        
    idx = 1
    while True:
        c = os.getenv(f'IKUUU_COOKIE_{idx}')
        if not c:
            break
        cookies.append(c)
        idx += 1

    if not cookies:
        print_with_time("❌ 未找到 IKUUU_COOKIE 环境变量！")
        exit(1)

    has_error = False
    for i, cookie in enumerate(cookies, 1):
        print("\n" + "=" * 50)
        print_with_time(f"👤 开始处理第 {i} 个账号")
        print("=" * 50)
        
        success = checkin_and_get_traffic(cookie)
        if not success:
            has_error = True

    print("\n" + "=" * 60)
    print_with_time("✨ 所有账号处理完成")
    print("=" * 60)
    
    if has_error:
        exit(1)
