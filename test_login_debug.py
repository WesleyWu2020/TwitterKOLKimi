#!/usr/bin/env python3
"""
Twitter 登录诊断脚本
用于详细查看登录过程中的问题和页面状态
"""
import sys
import time
from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stderr, level="DEBUG")

from src.config import load_config
from src.twitter_scraper import TwitterScraper

config = load_config("config/config.yaml")

print("=" * 60)
print("Twitter 登录诊断工具")
print("=" * 60)
print(f"\n配置信息:")
print(f"  - 用户名: {config.twitter.username}")
print(f"  - 目标 KOL: cz_binance")
print(f"  - 无头模式: False (会显示浏览器窗口)")
print("\n" + "=" * 60)
print("开始测试登录...")
print("=" * 60 + "\n")

# 使用 headless=False 以便观察
scraper = TwitterScraper(config.twitter, headless=False)

# 手动执行登录流程以便观察
try:
    from playwright.sync_api import sync_playwright
    
    scraper.playwright = sync_playwright().start()
    
    viewport = scraper._get_random_viewport()
    user_agent = scraper._get_random_user_agent()
    
    print(f"[1/6] 启动浏览器...")
    print(f"       视窗: {viewport}")
    print(f"       UA: {user_agent[:50]}...")
    
    scraper.browser = scraper.playwright.chromium.launch(
        headless=False,
        args=[
            "--disable-blink-features=AutomationControlled",
        ]
    )
    
    scraper.context = scraper.browser.new_context(
        viewport=viewport,
        user_agent=user_agent,
        locale="en-US",
    )
    
    # 加载 Cookie
    cookies = scraper._load_cookies()
    if cookies:
        print(f"[2/6] 加载了 {len(cookies)} 个 Cookie")
        scraper.context.add_cookies(cookies)
    else:
        print("[2/6] 没有之前的 Cookie")
    
    scraper.page = scraper.context.new_page()
    
    # 隐藏 webdriver
    scraper.page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
    
    print("[3/6] 访问 Twitter 登录页面...")
    scraper.page.goto("https://twitter.com/i/flow/login", timeout=30000)
    
    print("[4/6] 等待页面加载...")
    time.sleep(5)
    
    # 检查当前页面状态
    print("\n" + "=" * 60)
    print("页面诊断信息:")
    print("=" * 60)
    print(f"当前 URL: {scraper.page.url}")
    
    # 检查页面标题
    title = scraper.page.title()
    print(f"页面标题: {title}")
    
    # 检查是否有登录表单
    username_input = scraper.page.locator("input[autocomplete='username']")
    phone_input = scraper.page.locator("input[name='text']")
    
    print(f"\n元素检测:")
    print(f"  - 用户名输入框存在: {username_input.count() > 0}")
    print(f"  - 手机号输入框存在: {phone_input.count() > 0}")
    
    # 检查是否有验证码/挑战
    challenge_text = scraper.page.locator("text=Verify").count() > 0 or \
                     scraper.page.locator("text=Challenge").count() > 0 or \
                     scraper.page.locator("text=unusual").count() > 0
    
    print(f"  - 检测到验证/挑战: {challenge_text}")
    
    # 检查页面内容
    page_content = scraper.page.content()
    if "log in" in page_content.lower() or "sign in" in page_content.lower():
        print(f"  - 页面包含登录提示: True")
    
    if "suspended" in page_content.lower():
        print(f"  - ⚠️ 账号可能被暂停!")
    
    print("\n" + "=" * 60)
    print("尝试输入用户名...")
    print("=" * 60)
    
    # 尝试输入用户名
    if username_input.count() > 0:
        print(f"输入用户名: {config.twitter.username}")
        username_input.fill(config.twitter.username)
        time.sleep(2)
        
        # 查找并点击下一步按钮
        next_buttons = scraper.page.locator("button").all()
        print(f"找到 {len(next_buttons)} 个按钮")
        
        for i, btn in enumerate(next_buttons[:5]):
            try:
                text = btn.inner_text()
                print(f"  按钮 {i}: '{text}'")
                if "next" in text.lower() or "下一步" in text:
                    print(f"  -> 点击按钮: {text}")
                    btn.click()
                    break
            except:
                pass
        
        print("\n等待密码输入页面...")
        time.sleep(5)
        
        # 检查是否到了密码页面
        password_input = scraper.page.locator("input[type='password']")
        print(f"\n密码输入框存在: {password_input.count() > 0}")
        
        if password_input.count() > 0:
            print("检测到密码输入页面 ✓")
            print(f"当前 URL: {scraper.page.url}")
            
            # 输入密码
            print("\n输入密码...")
            password_input.fill(config.twitter.password)
            time.sleep(2)
            
            # 查找登录按钮
            login_buttons = scraper.page.locator("button").all()
            for btn in login_buttons[:5]:
                try:
                    text = btn.inner_text()
                    if "log in" in text.lower() or "登录" in text:
                        print(f"点击登录按钮: {text}")
                        btn.click()
                        break
                except:
                    pass
            
            print("\n等待登录完成...")
            time.sleep(8)
            
            # 检查登录结果
            print("\n" + "=" * 60)
            print("登录结果检查:")
            print("=" * 60)
            print(f"当前 URL: {scraper.page.url}")
            print(f"页面标题: {scraper.page.title()}")
            
            # 检查是否登录成功
            if "home" in scraper.page.url or "twitter.com/home" in scraper.page.url:
                print("\n✅ 登录成功!")
                scraper._save_cookies()
            elif "flow/login" in scraper.page.url:
                print("\n❌ 可能仍在登录页面，登录失败")
                
                # 检查错误信息
                error_text = scraper.page.locator("[data-testid='toast']").inner_text() if scraper.page.locator("[data-testid='toast']").count() > 0 else ""
                if error_text:
                    print(f"错误信息: {error_text}")
            else:
                print(f"\n⚠️ 未知状态，请查看浏览器窗口")
        else:
            print("\n❌ 未检测到密码输入页面")
            print("可能的页面内容:")
            print(scraper.page.content()[:1000])
    else:
        print("❌ 未找到用户名输入框")
        print("\n页面内容片段:")
        print(scraper.page.content()[:2000])

except Exception as e:
    print(f"\n❌ 发生错误: {e}")
    import traceback
    traceback.print_exc()

finally:
    print("\n" + "=" * 60)
    print("按 Enter 键关闭浏览器...")
    print("=" * 60)
    input()
    
    try:
        scraper._close_browser()
    except:
        pass
