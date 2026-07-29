import requests
from bs4 import BeautifulSoup
import re
import os
from datetime import datetime

# 定义日志文件路径
LOG_FILE = "checkin_result.txt"

def print_with_time(message, to_file=True):
    """带时间戳的打印并写入文件"""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{current_time}] {message}"
    
    # 1. 打印到 GitHub Actions 控制台
    print(log_line)
    
    # 2. 追加写入文件
    if to_file:
        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(log_line + "\n")
        except Exception as e:
            print(f"写入文件失败: {e}")

def write_separator(text=""):
    """写入分割线到文件和控制台"""
    line = "=" * 60 if not text else f"--- {text} ---"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def checkin_and_get_traffic(cookie):
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

    # 1. 签到
    for base_url in base_urls:
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
                    break
                except Exception:
                    pass
        except Exception:
            pass

    if not working_url:
        print_with_time("❌ 所有域名访问失败，请检查 Cookie 是否已过期。")
        return False

    # 2. 获取流量详情并写入文件
    try:
        user_url = f"{working_url}/user"
        res = session.get(user_url, headers=headers, timeout=10)
        html = res.text
        
        print_with_time("📊 账号流量使用详情:")
        
        # 匹配 c3.js 传入的数据数组，例如 ['已用', 7.14, '7.14MB'] 或 ['今日已用', '0B'] 等
        # SSPanel 常见的 C3 图表配置格式：['标签名', 数值/带单位字符串]
        patterns = [
            r"\[\s*['\"]([^'\"]*?(?:已用|可用|今日已用)[^'\"]*?)['\"]\s*,\s*['\"]?([\d\.]+\s*(?:[KMGT]?B))['\"]?",
            r"['\"]?([^'\"]*?(?:已用|可用|今日已用)[^'\"]*?)['\"]?\s*:\s*['\"]?([\d\.]+\s*(?:[KMGT]?B))['\"]?"
        ]
        
        found_data = []
        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            if matches:
                for label, val in matches:
                    item = f"{label.strip()}: {val.strip()}"
                    if item not in found_data:
                        found_data.append(item)
                        print_with_time(f"   📈 {item}")
        
        # 兜底方案：如果图表 JS 匹配不到，直接全局抓取包含 "已用" 或 "可用" 后跟流量单位的文本片段
        if not found_data:
            text_matches = re.findall(r"((?:今日已用|已用|可用)[^<>\n\r]{0,20}?[\d\.]+\s*(?:[KMGT]?B))", html)
            if text_matches:
                for match in text_matches:
                    clean_match = re.sub(r'\s+', ' ', match).strip()
                    if clean_match not in found_data:
                        found_data.append(clean_match)
                        print_with_time(f"   📈 {clean_match}")

        if not found_data:
            print_with_time("⚠️ 未能在页面中找到流量数据，可能是网页结构变更或登录已失效。")

    except Exception as e:
        print_with_time(f"❌ 获取流量信息失败: {str(e)}")

    return True

if __name__ == "__main__":
    write_separator(datetime.now().strftime("%Y-%m-%d 自动签到任务"))
    
    cookies = []
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
        print_with_time(f"👤 --- 开始处理第 {i} 个账号 ---")
        success = checkin_and_get_traffic(cookie)
        if not success:
            has_error = True

    write_separator()
    
    if has_error:
        exit(1)
