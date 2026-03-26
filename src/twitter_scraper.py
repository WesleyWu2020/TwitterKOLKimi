# src/twitter_scraper.py
"""
Twitter 爬虫模块 (Playwright 安全实现)

安全策略:
1. 随机延迟 - 避免机械化操作模式
2. 会话保持 - Cookie 持久化，减少登录次数
3. 视窗随机化 - 避免浏览器指纹追踪
4. 限流保护 - 每小时最多抓取 5 个 KOL
5. 错误重试 - 指数退避重试机制
"""
import json
import random
import time
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional
from loguru import logger


@dataclass
class TweetData:
    """推文数据结构"""
    tweet_id: str
    username: str
    display_name: str
    content: str
    posted_at: datetime
    likes: int = 0
    retweets: int = 0
    has_btc_keyword: bool = False


class TwitterScraper:
    """
    Twitter 爬虫类 (Playwright 安全实现)
    
    使用 Playwright 模拟真实用户行为，包含多层安全防护：
    - 随机延迟
    - 会话保持
    - 视窗随机化
    - 限流保护
    """
    
    # 常见 User-Agent 列表
    USER_AGENTS = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    ]
    
    # 视窗大小范围
    VIEWPORT_SIZES = [
        {"width": 1280, "height": 720},
        {"width": 1366, "height": 768},
        {"width": 1440, "height": 900},
        {"width": 1536, "height": 864},
        {"width": 1920, "height": 1080},
    ]
    
    # 限流配置
    MAX_KOLS_PER_HOUR = 5
    RATE_LIMIT_FILE = "data/twitter_rate_limit.json"
    
    def __init__(self, config, headless: bool = True, cookie_file: str = "data/twitter_cookies.json"):
        """
        初始化爬虫
        
        Args:
            config: TwitterConfig 配置对象
            headless: 是否使用无头模式（调试时可设为 False）
            cookie_file: Cookie 持久化文件路径
        """
        self.config = config
        self.headless = headless
        self.cookie_file = Path(cookie_file)
        self.rate_limit_file = Path(self.RATE_LIMIT_FILE)
        
        # Playwright 对象（延迟初始化）
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        # 登录状态
        self.is_logged_in = False
        
        logger.info(f"TwitterScraper initialized (headless={headless})")
    
    def _get_random_delay(self, min_sec: float = 3.0, max_sec: float = 10.0) -> float:
        """获取随机延迟秒数"""
        return random.uniform(min_sec, max_sec)
    
    def _get_random_viewport(self) -> Dict[str, int]:
        """获取随机视窗大小"""
        return random.choice(self.VIEWPORT_SIZES)
    
    def _get_random_user_agent(self) -> str:
        """获取随机 User-Agent"""
        return random.choice(self.USER_AGENTS)
    
    def _check_rate_limit(self) -> bool:
        """
        检查是否超过每小时抓取限制
        
        Returns:
            True if within limit, False if exceeded
        """
        if not self.rate_limit_file.exists():
            return True
        
        try:
            with open(self.rate_limit_file, "r") as f:
                data = json.load(f)
            
            last_reset = datetime.fromisoformat(data.get("last_reset", "2000-01-01T00:00:00"))
            count = data.get("count", 0)
            
            # 如果超过1小时，重置计数
            if datetime.now(timezone.utc) - last_reset > timedelta(hours=1):
                logger.info("Rate limit window reset")
                return True
            
            if count >= self.MAX_KOLS_PER_HOUR:
                logger.warning(f"Rate limit exceeded: {count}/{self.MAX_KOLS_PER_HOUR} KOLs this hour")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return True  # 出错时允许继续
    
    def _update_rate_limit(self, increment: int = 1):
        """更新抓取计数"""
        try:
            data = {"last_reset": datetime.now(timezone.utc).isoformat(), "count": 0}
            
            if self.rate_limit_file.exists():
                with open(self.rate_limit_file, "r") as f:
                    data = json.load(f)
                
                # 检查是否需要重置
                last_reset = datetime.fromisoformat(data.get("last_reset", "2000-01-01T00:00:00"))
                if datetime.now(timezone.utc) - last_reset > timedelta(hours=1):
                    data = {"last_reset": datetime.now(timezone.utc).isoformat(), "count": 0}
            
            data["count"] = data.get("count", 0) + increment
            
            self.rate_limit_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.rate_limit_file, "w") as f:
                json.dump(data, f)
                
        except Exception as e:
            logger.error(f"Error updating rate limit: {e}")
    
    def _save_cookies(self):
        """保存 Cookie 到文件"""
        if not self.context:
            return
        
        try:
            cookies = self.context.cookies()
            self.cookie_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cookie_file, "w") as f:
                json.dump(cookies, f)
            logger.info(f"Cookies saved to {self.cookie_file}")
        except Exception as e:
            logger.error(f"Error saving cookies: {e}")
    
    def _load_cookies(self) -> List[Dict]:
        """从文件加载 Cookie"""
        if not self.cookie_file.exists():
            return []
        
        try:
            with open(self.cookie_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading cookies: {e}")
            return []
    
    def _init_browser(self):
        """初始化浏览器（带随机配置）"""
        try:
            from playwright.sync_api import sync_playwright
            
            self.playwright = sync_playwright().start()
            
            # 随机视窗和 UA
            viewport = self._get_random_viewport()
            user_agent = self._get_random_user_agent()
            
            self.browser = self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--disable-features=IsolateOrigins,site-per-process",
                ]
            )
            
            self.context = self.browser.new_context(
                viewport=viewport,
                user_agent=user_agent,
                locale="en-US",
                timezone_id="America/New_York",
            )
            
            # 加载之前保存的 Cookie
            cookies = self._load_cookies()
            if cookies:
                self.context.add_cookies(cookies)
                logger.info(f"Loaded {len(cookies)} cookies from previous session")
            
            self.page = self.context.new_page()
            
            # 注入脚本隐藏 webdriver 属性
            self.page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            """)
            
            logger.info(f"Browser initialized with viewport {viewport}")
            
        except ImportError:
            logger.error("Playwright not installed. Run: pip install playwright && playwright install")
            raise
    
    def _close_browser(self):
        """关闭浏览器"""
        try:
            if self.context:
                self._save_cookies()
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")
    
    def _check_login_status(self) -> bool:
        """
        检查是否已登录
        
        通过检查主页元素或导航栏头像来判断
        """
        if not self.page:
            return False
        
        try:
            # 检查当前 URL
            current_url = self.page.url
            
            # 如果已经在主页，直接检查元素
            if "twitter.com/home" in current_url:
                home_indicators = [
                    "[data-testid='primaryColumn']",
                    "[data-testid='sidebarColumn']",
                    "[data-testid='AppTabBar_Home_Link']",
                ]
                for selector in home_indicators:
                    try:
                        if self.page.locator(selector).first.count() > 0:
                            logger.debug(f"Found home indicator: {selector}")
                            return True
                    except:
                        continue
            
            # 尝试访问主页
            self.page.goto("https://twitter.com/home", timeout=15000)
            time.sleep(self._get_random_delay(2, 4))
            
            # 检查是否被重定向到登录页
            if "login" in self.page.url or "flow" in self.page.url:
                logger.debug("Redirected to login page, not logged in")
                return False
            
            # 检查主页元素
            indicators = [
                ("text=For you", "For you feed"),
                ("text=Following", "Following feed"),
                ("[data-testid='SideNav_AccountSwitcher_Button']", "Account switcher"),
                ("[aria-label='Compose tweet']", "Compose button"),
            ]
            
            for selector, name in indicators:
                try:
                    if self.page.locator(selector).first.is_visible(timeout=3000):
                        logger.info(f"✓ Login verified: Found {name}")
                        return True
                except:
                    continue
            
            logger.debug("Login check: No home indicators found")
            return False
            
        except Exception as e:
            logger.warning(f"Login check error: {e}")
            return False
    
    def _click_button_by_text(self, keywords: List[str], timeout: int = 5000) -> bool:
        """
        通过关键词点击按钮（支持多种语言）
        
        Args:
            keywords: 按钮文本关键词列表
            timeout: 超时时间（毫秒）
            
        Returns:
            是否成功点击
        """
        try:
            # 查找所有按钮
            buttons = self.page.locator("button").all()
            
            for btn in buttons:
                try:
                    text = btn.inner_text(timeout=1000).lower()
                    if any(kw.lower() in text for kw in keywords):
                        btn.click()
                        logger.debug(f"Clicked button: {text}")
                        return True
                except:
                    continue
            
            return False
            
        except Exception as e:
            logger.warning(f"Failed to click button: {e}")
            return False
    
    def _handle_login_flow(self) -> bool:
        """
        处理完整的登录流程，包括各种验证页面
        
        Returns:
            是否成功完成登录流程
        """
        try:
            # 等待页面加载
            time.sleep(self._get_random_delay(4, 7))
            
            current_url = self.page.url
            logger.debug(f"Current URL: {current_url}")
            
            # ===== 第 1 步：输入用户名/邮箱 =====
            # 截图显示页面有 "Phone, email, or username" 输入框
            # 这个输入框通常是 input[name='text']
            username_selectors = [
                "input[name='text']",  # 最常见
                "input[autocomplete='username']",
                "input[type='text']",
                "input[inputmode='email']",
            ]
            
            username_input = None
            for selector in username_selectors:
                try:
                    elem = self.page.locator(selector).first
                    if elem.count() > 0 and elem.is_visible(timeout=5000):
                        # 检查 placeholder 是否包含 username/email/phone 关键字
                        try:
                            placeholder = elem.get_attribute("placeholder") or ""
                            if any(kw in placeholder.lower() for kw in ["phone", "email", "username"]):
                                username_input = elem
                                logger.debug(f"Found username input: {selector} (placeholder: {placeholder})")
                                break
                        except:
                            # 如果无法获取 placeholder，也接受这个元素
                            username_input = elem
                            logger.debug(f"Found username input: {selector}")
                            break
                except Exception as e:
                    logger.debug(f"Selector {selector} failed: {e}")
                    continue
            
            if not username_input:
                logger.error("Could not find username input field")
                # 保存截图便于调试
                try:
                    self.page.screenshot(path="data/login_error_no_username.png")
                    logger.info("Screenshot saved to data/login_error_no_username.png")
                except:
                    pass
                return False
            
            # 清除输入框并输入用户名
            username_input.click()
            username_input.fill("")  # 先清空
            time.sleep(0.5)
            username_input.fill(self.config.username)
            logger.info(f"Filled username: {self.config.username}")
            time.sleep(self._get_random_delay(2, 4))
            
            # 点击下一步
            logger.debug("Clicking Next button...")
            if not self._click_button_by_text(["Next", "下一步", "Continue", "继续"]):
                # 尝试按 Enter 键
                username_input.press("Enter")
            
            # 等待页面跳转
            logger.debug("Waiting for page transition...")
            time.sleep(self._get_random_delay(5, 8))
            
            # 检查当前 URL 和页面内容
            current_url = self.page.url
            page_content = self.page.content().lower()
            logger.debug(f"After clicking Next - URL: {current_url}")
            
            # ===== 第 2 步：处理中间验证页面 =====
            # 检查是否在密码页面
            password_selectors = [
                "input[type='password']",
                "input[autocomplete='current-password']",
                "input[name='password']",
            ]
            
            # 等待密码输入框出现（最多等待10秒）
            password_input = None
            max_wait = 10
            waited = 0
            while waited < max_wait:
                for selector in password_selectors:
                    try:
                        elem = self.page.locator(selector).first
                        if elem.count() > 0 and elem.is_visible(timeout=2000):
                            password_input = elem
                            logger.debug(f"Found password input: {selector}")
                            break
                    except:
                        continue
                
                if password_input:
                    break
                
                # 检查是否仍在用户名页面（说明可能输入错误）
                username_elem = self.page.locator("input[name='text']").first
                if username_elem.count() > 0 and username_elem.is_visible(timeout=1000):
                    # 检查是否有错误信息
                    error_elem = self.page.locator("[role='alert']").first
                    if error_elem.count() > 0:
                        error_text = error_elem.inner_text(timeout=2000)
                        logger.error(f"Login error on username page: {error_text}")
                        return False
                
                time.sleep(1)
                waited += 1
                logger.debug(f"Waiting for password field... ({waited}s)")
            
            if not password_input:
                # 检查是否是手机号验证页面
                phone_input = self.page.locator("input[type='tel']").first
                if phone_input.count() > 0 and phone_input.is_visible(timeout=2000):
                    logger.error("❌ Phone verification required!")
                    logger.error("   This account requires phone number verification.")
                    logger.error("   Please use an account without phone verification,")
                    logger.error("   or verify manually in a browser first.")
                    return False
                
                # 检查是否是异常登录页面
                if any(kw in page_content for kw in ["unusual", "suspicious", "confirm your identity"]):
                    logger.error("❌ Twitter detected suspicious login!")
                    logger.error("   Please login manually in a browser first to verify.")
                    try:
                        self.page.screenshot(path="data/login_suspicious.png")
                        logger.info("   Screenshot saved to data/login_suspicious.png")
                    except:
                        pass
                    return False
                
                logger.error("❌ Could not find password input field")
                logger.error(f"   Current URL: {current_url}")
                try:
                    self.page.screenshot(path="data/login_error_no_password.png")
                    logger.info("   Screenshot saved to data/login_error_no_password.png")
                except:
                    pass
                return False
            
            # 输入密码
            password_input.click()
            password_input.fill("")
            time.sleep(0.5)
            password_input.fill(self.config.password)
            logger.info("Filled password")
            time.sleep(self._get_random_delay(2, 4))
            
            # 点击登录
            logger.debug("Clicking Log in button...")
            if not self._click_button_by_text(["Log in", "登录", "Sign in", "Signin"]):
                password_input.press("Enter")
            
            logger.info("Submitted login form, waiting for redirect...")
            time.sleep(self._get_random_delay(8, 12))
            
            # 检查登录结果
            final_url = self.page.url
            logger.debug(f"After login - URL: {final_url}")
            
            # 检查是否仍在登录相关页面
            if "login" in final_url or "flow" in final_url:
                # 检查错误信息
                error_selectors = [
                    "[data-testid='toast']",
                    "[role='alert']",
                    "span:has-text('wrong')",
                    "span:has-text('incorrect')",
                ]
                for sel in error_selectors:
                    try:
                        error_elem = self.page.locator(sel).first
                        if error_elem.count() > 0:
                            error_text = error_elem.inner_text(timeout=2000)
                            if error_text:
                                logger.error(f"Login error: {error_text}")
                                break
                    except:
                        pass
                
                logger.warning("Still on login page after submitting")
                return False
            
            logger.info("✓ Login form submitted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error in login flow: {e}")
            return False
    
    def _login(self, max_retries: int = 3) -> bool:
        """
        登录 Twitter（增强版，支持多种验证场景）
        
        Args:
            max_retries: 最大重试次数
            
        Returns:
            是否登录成功
        """
        for attempt in range(max_retries):
            try:
                logger.info(f"Login attempt {attempt + 1}/{max_retries}")
                
                # 访问登录页
                logger.debug("Navigating to login page...")
                self.page.goto("https://twitter.com/i/flow/login", timeout=30000)
                
                # 执行登录流程
                if not self._handle_login_flow():
                    logger.warning("Login flow failed, retrying...")
                    time.sleep(self._get_random_delay(5, 10))
                    continue
                
                # 检查登录结果
                logger.debug("Checking login status...")
                
                # 等待页面跳转
                time.sleep(self._get_random_delay(3, 5))
                
                # 检查是否登录成功
                if self._check_login_status():
                    logger.info("✅ Login successful!")
                    self.is_logged_in = True
                    self._save_cookies()
                    return True
                
                # 检查是否有验证码/挑战
                page_content = self.page.content().lower()
                challenge_keywords = ["verify", "challenge", "authentication", "confirm", "unusual"]
                if any(kw in page_content for kw in challenge_keywords):
                    logger.error("❌ Login challenge/verification required!")
                    logger.error("   Please login manually once to verify your account.")
                    
                    # 保存截图便于诊断
                    try:
                        self.page.screenshot(path="data/login_challenge.png")
                        logger.info("   Screenshot saved to data/login_challenge.png")
                    except:
                        pass
                    return False
                
                # 检查是否在登录页面（可能密码错误）
                if "login" in self.page.url or "flow" in self.page.url:
                    error_msg = ""
                    try:
                        # 尝试获取错误信息
                        error_elem = self.page.locator("[data-testid='toast']").first
                        if error_elem.count() > 0:
                            error_msg = error_elem.inner_text(timeout=3000)
                    except:
                        pass
                    
                    if error_msg:
                        logger.warning(f"Login page still visible. Error: {error_msg}")
                    else:
                        logger.warning("Still on login page, possibly wrong password")
                
                logger.warning(f"Login attempt {attempt + 1} did not succeed, waiting before retry...")
                time.sleep(self._get_random_delay(8, 15))
                
            except Exception as e:
                logger.error(f"Login attempt {attempt + 1} error: {e}")
                time.sleep(self._get_random_delay(5, 10))
        
        logger.error("❌ All login attempts failed")
        return False
    
    def _ensure_logged_in(self) -> bool:
        """确保已登录"""
        if self.is_logged_in and self._check_login_status():
            return True
        
        return self._login()
    
    def parse_tweet_data(self, raw_data: Dict[str, Any]) -> Optional[TweetData]:
        """
        解析原始推文数据
        
        Args:
            raw_data: 原始API返回数据
            
        Returns:
            解析后的TweetData对象，解析失败返回None
        """
        if not raw_data or not isinstance(raw_data, dict):
            return None
        
        try:
            tweet_id = raw_data.get("id")
            if not tweet_id:
                return None
            
            content = raw_data.get("text", "")
            return TweetData(
                tweet_id=str(tweet_id),
                username=raw_data.get("username", ""),
                display_name=raw_data.get("name", ""),
                content=content,
                posted_at=datetime.now(timezone.utc),  # 简化处理
                likes=raw_data.get("public_metrics", {}).get("like_count", 0),
                retweets=raw_data.get("public_metrics", {}).get("retweet_count", 0),
                has_btc_keyword=self._check_btc_keyword(content)
            )
        except Exception as e:
            logger.error(f"Failed to parse tweet data: {e}")
            return None

    def _parse_tweet_element(self, tweet_element, username: str) -> Optional[TweetData]:
        """解析单个推文元素"""
        try:
            # 获取推文文本
            text_locator = tweet_element.locator("[data-testid='tweetText']")
            if text_locator.count() == 0:
                return None
            content = text_locator.inner_text()
            
            # 获取推文ID
            link_element = tweet_element.locator("a[href*='/status/']").first
            href = link_element.get_attribute("href") if link_element.count() > 0 else ""
            tweet_id = href.split("/status/")[-1].split("?")[0] if "/status/" in href else ""
            
            # 获取时间
            time_element = tweet_element.locator("time").first
            time_str = time_element.get_attribute("datetime") if time_element.count() > 0 else None
            posted_at = datetime.fromisoformat(time_str.replace("Z", "+00:00")) if time_str else datetime.now(timezone.utc)
            
            # 获取互动数据
            likes = 0
            retweets = 0
            
            try:
                likes_element = tweet_element.locator("[data-testid='like']")
                if likes_element.count() > 0:
                    likes_text = likes_element.inner_text()
                    likes = int(likes_text.replace(",", "")) if likes_text.replace(",", "").isdigit() else 0
            except:
                pass
            
            # 检查BTC关键词
            has_btc = self._check_btc_keyword(content)
            
            return TweetData(
                tweet_id=tweet_id,
                username=username,
                display_name=username,  # 简化处理
                content=content,
                posted_at=posted_at,
                likes=likes,
                retweets=retweets,
                has_btc_keyword=has_btc
            )
            
        except Exception as e:
            logger.error(f"Error parsing tweet element: {e}")
            return None
    
    def fetch_tweets_from_kol(self, username: str, max_tweets: int = 10) -> List[TweetData]:
        """
        从指定 KOL 获取推文（安全实现）
        
        Args:
            username: KOL 用户名
            max_tweets: 最大抓取推文数（默认10条）
            
        Returns:
            推文数据列表
        """
        if not self._check_rate_limit():
            logger.warning(f"Rate limit exceeded, skipping {username}")
            return []
        
        try:
            # 初始化浏览器
            self._init_browser()
            
            # 确保已登录
            if not self._ensure_logged_in():
                logger.error("Failed to login, cannot fetch tweets")
                return []
            
            logger.info(f"Fetching tweets for KOL: {username}")
            
            # 访问用户主页
            profile_url = f"https://twitter.com/{username}"
            self.page.goto(profile_url, timeout=30000)
            time.sleep(self._get_random_delay(4, 8))
            
            # 检查是否存在用户
            if self.page.locator("text=This account doesn't exist").is_visible(timeout=5000) or \
               self.page.locator("text=Account suspended").is_visible(timeout=5000):
                logger.warning(f"Account {username} doesn't exist or is suspended")
                return []
            
            tweets = []
            last_height = 0
            scroll_attempts = 0
            max_scroll_attempts = 10
            
            while len(tweets) < max_tweets and scroll_attempts < max_scroll_attempts:
                # 获取当前可见的推文
                tweet_elements = self.page.locator("article[data-testid='tweet']").all()
                
                for tweet_element in tweet_elements:
                    if len(tweets) >= max_tweets:
                        break
                    
                    tweet = self._parse_tweet_element(tweet_element, username)
                    if tweet and tweet.tweet_id and not any(t.tweet_id == tweet.tweet_id for t in tweets):
                        tweets.append(tweet)
                        logger.debug(f"Parsed tweet: {tweet.tweet_id[:20]}...")
                
                # 滚动加载更多
                self.page.evaluate("window.scrollBy(0, window.innerHeight * 0.8)")
                time.sleep(self._get_random_delay(3, 6))
                
                # 检查是否到底
                current_height = self.page.evaluate("window.pageYOffset")
                if current_height == last_height:
                    scroll_attempts += 1
                else:
                    scroll_attempts = 0
                last_height = current_height
            
            # 更新限流计数
            self._update_rate_limit(1)
            
            logger.info(f"Successfully fetched {len(tweets)} tweets from {username}")
            return tweets
            
        except Exception as e:
            logger.error(f"Error fetching tweets from {username}: {e}")
            return []
        
        finally:
            self._close_browser()
    
    def fetch_all_kols_tweets(self, kols: List[Dict[str, Any]], max_tweets_per_kol: int = 10) -> List[TweetData]:
        """
        批量获取多个 KOL 的推文（带限流保护）
        
        Args:
            kols: KOL 列表
            max_tweets_per_kol: 每个 KOL 最大抓取推文数
            
        Returns:
            所有推文数据列表
        """
        all_tweets = []
        
        for i, kol in enumerate(kols):
            # 检查限流
            if not self._check_rate_limit():
                logger.warning("Rate limit reached, stopping batch fetch")
                break
            
            # 检查粉丝数
            followers_count = kol.get("followers_count", 0)
            if followers_count < self.config.min_followers:
                logger.debug(f"Skipping {kol['username']}: insufficient followers ({followers_count})")
                continue
            
            try:
                logger.info(f"Processing KOL {i+1}/{len(kols)}: {kol['username']}")
                tweets = self.fetch_tweets_from_kol(kol["username"], max_tweets_per_kol)
                all_tweets.extend(tweets)
                
                # KOL 之间的间隔（避免太频繁）
                if i < len(kols) - 1:
                    delay = self._get_random_delay(10, 30)
                    logger.info(f"Waiting {delay:.1f}s before next KOL...")
                    time.sleep(delay)
                    
            except Exception as e:
                logger.error(f"Failed to fetch tweets from {kol['username']}: {e}")
                continue
        
        logger.info(f"Batch fetch complete: {len(all_tweets)} tweets from {len(kols)} KOLs")
        return all_tweets
    
    def _check_btc_keyword(self, text: str) -> bool:
        """检查文本是否包含 BTC 相关关键词"""
        if not text:
            return False
        text_upper = text.upper()
        keywords_upper = [k.upper() for k in self.config.keywords]
        return any(kw in text_upper for kw in keywords_upper)
