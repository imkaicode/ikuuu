import requests
from bs4 import BeautifulSoup
import re
import os
from datetime import datetime
from urllib.parse import urlparse

def print_with_time(message):
    """带时间戳的打印"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_time}] {message}")

def login_and_get_cookie(email, password):
    """登录 SSPanel 并获取 Cookie"""
    if not email or not password:
        print_with_time("❌ 错误: 邮箱或密码为空")
        return None, None
    
    print_with_time(f"🔑 正在使用账号 {email[:3]}***{email.split('@')[1] if '@' in email else ''} 登录...")
    
    session = requests.Session()
    
    # 可用的登录 URL 列表
    url_list = [
        "https://ikuuu.fyi/auth/login",
        "https://ikuuu.win/auth/login",
        "https://ikuuu.de/auth/login"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0'
    }
    
    # 遍历尝试每一个 URL
    for login_page_url in url_list:
        parsed_url = urlparse(login_page_url)
        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"  # 动态提取主域名
        
        try:
            print_with_time(f"🌐 尝试访问: {login_page_url}")
            
            # 获取登录页面
            response = session.get(login_page_url, headers=headers, timeout=10)
            if response.status_code != 200:
                print_with_time(f"⚠️ 无法访问页面，状态码: {response.status_code}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 查找 CSRF token
            csrf_token = None
            csrf_input = soup.find('input', {'name': '_token'})
            if csrf_input:
                csrf_token = csrf_input.get('value')
            
            # 准备登录数据
            login_data = {
                'email': email,
                'passwd': password
            }
            
            if csrf_token:
                login_data['_token'] = csrf_token
            
            # 动态设置与当前域名匹配的请求头
            req_headers = headers.copy()
            req_headers.update({
                'Origin': base_url,
                'Referer': login_page_url,
                'Content-Type': 'application/x-www-form-urlencoded'
            })
            
            # 发送登录请求 (使用当前尝试的 URL)
            response = session.post(login_page_url, data=login_data, headers=req_headers, timeout=10)
            
            # 检查登录是否成功
            if response.status_code == 200:
                try:
                    res_json = response.json()
                    is_success = 'user' in response.url or res_json.get('ret') == 1
                    msg = res_json.get('msg', '未知错误')
                except Exception:
                    is_success = 'user' in response.url
                    msg = "非 JSON 格式响应"

                if is_success:
                    print_with_time(f"✅ 登录成功 (通过域名: {base_url})")
                    # 提取 Cookie
                    cookies = session.cookies.get_dict()
                    cookie_string = '; '.join([f"{name}={value}" for name, value in cookies.items()])
                    return cookie_string, base_url
                else:
                    print_with_time(f"❌ 登录失败: {msg}")
            else:
                print_with_time(f"❌ 登录请求失败，状态码: {response.status_code}")
                
        except Exception as e:
            print_with_time(f"❌ 登录过程中发生错误: {str(e)}")
    
    # 全部尝试后均失败
    return None, None

def checkin(cookie, base_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
        'Origin': base_url,
        'Referer': f"{base_url}/user",
        'Cookie': cookie
    }
    url = f"{base_url}/user/checkin"
    
    try:
        response = requests.post(url, headers=headers)
        data = response.json()
        
        if data.get('ret') == 1:
            print_with_time(f"✅ 签到成功: {data['msg']}")
            return True
        elif "已经签到" in data.get('msg', ''):
            print_with_time(f"ℹ️ 今日已签到: {data['msg']}")
            return True
        else:
            print_with_time(f"❌ 签到失败: {data['msg']}")
            return False
    except Exception as e:
        print_with_time(f"❌ 签到请求失败: {str(e)}")
        return False

def get_user_traffic(cookie, base_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0',
        'Origin': base_url,
        'Referer': f"{base_url}/user/code",
        'Cookie': cookie
    }
    url = f"{base_url}/user"
    
    try:
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找剩余流量信息
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
                        today_used = match.group(1).strip()
                        print(f"📊 今日已用: {today_used}")
                    else:
                        print(f"📊 今日使用情况: {today_used_text}")
        
        print("-" * 40)
        return soup
    except Exception as e:
        print_with_time(f"❌ 获取流量信息失败: {str(e)}")
        return None

if __name__ == "__main__":
    print("=" * 60)
    print_with_time("🚀 iKuuu 自动签到程序启动")
    print("=" * 60)
    
    # 自动获取所有以 IKUUU_EMAIL_ 开头的环境变量账号
    accounts = []
    
    # 兼容单账号 (IKUUU_EMAIL) 和多账号 (IKUUU_EMAIL_1, IKUUU_EMAIL_2 等)
    single_email = os.getenv('IKUUU_EMAIL')
    if single_email:
        accounts.append((single_email, os.getenv('IKUUU_PASSWORD', '')))
    
    # 动态扫描环境变量中的多账号编号
    idx = 1
    while True:
        email = os.getenv(f'IKUUU_EMAIL_{idx}')
        password = os.getenv(f'IKUUU_PASSWORD_{idx}')
        if not email:
            break
        accounts.append((email, password))
        idx += 1

    if not accounts:
        print_with_time("❌ 未检测到任何登录环境变量！请检查 Secrets 配置。")
        exit(1)

    has_error = False

    # 循环遍历每个账号执行签到
    for idx, (email, password) in enumerate(accounts, 1):
        print("\n" + "=" * 50)
        print_with_time(f"👤 开始处理第 {idx} 个账号")
        print("=" * 50)
        
        cookie_data, base_url = login_and_get_cookie(email, password)
        
        if cookie_data and base_url:
            # 执行签到
            checkin(cookie_data, base_url)
            # 获取流量
            get_user_traffic(cookie_data, base_url)
        else:
            print_with_time(f"❌ 账号 {email} 处理失败")
            has_error = True

    print("\n" + "=" * 60)
    print_with_time("✨ 所有账号处理完成")
    print("=" * 60)
    
    if has_error:
        exit(1)
