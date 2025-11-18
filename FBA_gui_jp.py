import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import platform
import math
import logging
import os
import sys
import json
import threading
import webbrowser
import shutil
from datetime import datetime
import urllib.parse

class FBAShippingCalculatorJP:
    # 程序版本信息
    VERSION = "1.3.1"
    UPDATE_URL = "https://example.com/fba_calculator/latest_version.json"  # 更新检查URL
    SETTINGS_FILE = "settings_jp.json"  # 设置文件路径
    UPDATE_INFO_FILE = "update_info_jp.json"  # 更新信息文件路径
    UPLOAD_SERVER_URL = "https://tomarens.xyz"  # 上传服务器地址
    FEEDBACK_FILE = "feedback_jp.json"  # 反馈文件路径
    
    def __init__(self, root):
        # 设置中文字体支持
        self.setup_fonts()
        
        # 加载用户设置
        self.settings = self.load_settings()
        
        self.root = root
        self.root.title(f"日本站FBA配送费计算器 v{self.VERSION}")
        
        # 初始化计算历史记录
        self.calculation_history = []
        
        # 根据用户设置决定窗口大小
        window_size = self.settings.get("window_size", "maximized")
        if window_size == "maximized":
            # 设置窗口最大化
            try:
                self.root.state('zoomed')  # Windows系统全屏方式
            except:
                try:
                    self.root.attributes('-fullscreen', True)  # 其他系统全屏方式
                except:
                    self.root.geometry("800x700")  # 如果全屏失败，使用默认尺寸
        else:
            # 设置窗口为窗口化模式，使用默认尺寸
            self.root.geometry("800x700")
        
        # 添加退出全屏的键盘绑定
        self.root.bind('<Escape>', lambda e: self.root.attributes('-fullscreen', False) if hasattr(self.root, 'attributes') else None)
        self.root.resizable(True, True)
        
        # 设置默认颜色主题
        self.color_theme = {
            "background": "#f0f0f0",
            "frame_bg": "#ffffff",
            "text_bg": "#ffffff",
            "text_fg": "#000000",
            "button_bg": "#e6e6e6",
            "button_active": "#d5d5d5",
            "button_pressed": "#c0c0c0",
            "highlight_bg": "#d4e6f1",
            "header_bg": "#aed6f1",
            "segment_bg": "#f9ebea",
            "border_color": "#bdc3c7",
            "shadow_color": "#34495e"
        }
        
        # 设置窗口图标和样式
        self.style = ttk.Style()
        self.style.configure("TLabel", font=self.default_font)
        self.style.configure("TButton", font=self.default_font)
        self.style.configure("TLabelframe.Label", font=self.header_font)
        
        # 创建自定义样式
        self._create_styles()
        
        # 设置主题颜色
        self.apply_theme()
        
        # 创建主容器
        self.content_container = ttk.Frame(root, padding="20")
        self.content_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 程序退出时保存设置
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 为FBA计算器创建UI元素
        self.create_title()
        self.create_size_inputs()
        self.create_weight_inputs()
        self.create_segment_display()
        self.create_buttons()
        self.create_result_area()
        
        # 添加底部状态栏
        self.create_status_bar()
    
    def _create_styles(self):
        """创建自定义样式，实现立体化效果"""
        # 创建立体感按钮样式
        self.style.configure(
            "Accent.TButton", 
            font=self.button_font,
            padding=(10, 5),
            relief="raised",
            borderwidth=1
        )
        self.style.map(
            "Accent.TButton",
            background=[
                ('active', '#d5d5d5'),
                ('pressed', '#c0c0c0'),
                ('!disabled', '#e6e6e6')
            ],
            relief=[
                ('pressed', 'sunken'),
                ('!pressed', 'raised')
            ]
        )
        
        # 创建导航按钮样式
        self.style.configure(
            "Nav.TButton",
            font=self.button_font,
            padding=(15, 8),
            relief="raised",
            borderwidth=1
        )
        self.style.map(
            "Nav.TButton",
            background=[
                ('active', '#aed6f1'),
                ('pressed', '#85c1e9'),
                ('!disabled', '#d4e6f1')
            ],
            relief=[
                ('pressed', 'sunken'),
                ('!pressed', 'raised')
            ]
        )
        
        # 创建输入框样式
        self.style.configure(
            "Custom.TEntry",
            font=self.default_font,
            padding=5,
            relief="sunken",
            borderwidth=1
        )
        
        # 创建卡片式框架样式
        self.style.configure(
            "Card.TFrame",
            background="#ffffff",
            relief="flat"
        )
    
    def setup_fonts(self):
        """设置中文字体支持"""
        # 根据操作系统设置字体
        system = platform.system()
        
        if system == "Windows":
            # Windows系统使用默认字体
            self.default_font = ("微软雅黑", 10)
            self.button_font = ("微软雅黑", 10, "bold")
            self.header_font = ("微软雅黑", 12, "bold")
            self.title_font = ("微软雅黑", 16, "bold")
        elif system == "Darwin":
            # macOS系统使用默认字体
            self.default_font = ("Hiragino Sans GB", 12)
            self.button_font = ("Hiragino Sans GB", 12, "bold")
            self.header_font = ("Hiragino Sans GB", 14, "bold")
            self.title_font = ("Hiragino Sans GB", 18, "bold")
        else:
            # Linux等其他系统使用默认字体
            self.default_font = ("SimHei", 10)
            self.button_font = ("SimHei", 10, "bold")
            self.header_font = ("SimHei", 12, "bold")
            self.title_font = ("SimHei", 16, "bold")
    
    def apply_theme(self):
        """应用主题颜色"""
        # 设置主窗口背景
        self.root.configure(bg=self.color_theme["background"])
    
    def load_settings(self):
        """加载用户设置"""
        try:
            if os.path.exists(self.SETTINGS_FILE):
                with open(self.SETTINGS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"加载设置失败: {str(e)}")
        return {}
    
    def save_settings(self):
        """保存用户设置"""
        try:
            with open(self.SETTINGS_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"保存设置失败: {str(e)}")
    
    def check_internet_connection(self, url=None):
        """检查网络连接状态"""
        try:
            import urllib.request
            
            if url:
                # 使用指定的URL进行连接测试
                urllib.request.urlopen(url, timeout=5)
            else:
                # 尝试连接到一个可靠的网站
                urllib.request.urlopen("https://www.baidu.com", timeout=5)
                return True
        except:
            # 检查是否能连接到本地服务器
            try:
                import urllib.request
                urllib.request.urlopen("https://tomarens.xyz", timeout=5)
                return True
            except:
                return False
    
    def show_bug_feedback(self):
        """显示BUG反馈对话框"""
        # 创建一个新的窗口用于BUG反馈
        feedback_window = tk.Toplevel(self.root)
        feedback_window.title("BUG反馈 - 日本站FBA配送费计算器")
        feedback_window.geometry("600x500")
        feedback_window.resizable(False, False)
        
        # 居中显示
        feedback_window.transient(self.root)
        feedback_window.grab_set()
        
        # 创建标签页控件
        notebook = ttk.Notebook(feedback_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建新反馈页面
        new_feedback_frame = ttk.Frame(notebook)
        notebook.add(new_feedback_frame, text="提交反馈")
        
        # 创建本地反馈页面
        local_feedback_frame = ttk.Frame(notebook)
        notebook.add(local_feedback_frame, text="我的反馈")
        
        # 加载BUG反馈页面内容
        self._load_bug_feedback_page(new_feedback_frame, feedback_window)
        
        # 加载本地反馈列表
        self.display_feedbacks(local_feedback_frame)
    
    def _load_bug_feedback_page(self, parent, feedback_window):
        """加载BUG反馈页面内容"""
        # 反馈类型选择
        type_frame = ttk.Frame(parent)
        type_frame.pack(fill=tk.X, pady=10, padx=10)
        
        ttk.Label(type_frame, text="反馈类型:", font=self.default_font).pack(side=tk.LEFT, padx=5)
        
        feedback_type_var = tk.StringVar(value="bug")
        feedback_type_frame = ttk.Frame(type_frame)
        feedback_type_frame.pack(side=tk.LEFT, padx=5)
        
        ttk.Radiobutton(feedback_type_frame, text="BUG问题", variable=feedback_type_var, value="bug").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(feedback_type_frame, text="功能建议", variable=feedback_type_var, value="suggestion").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(feedback_type_frame, text="其他反馈", variable=feedback_type_var, value="other").pack(side=tk.LEFT, padx=5)
        
        # 联系方式输入
        contact_frame = ttk.Frame(parent)
        contact_frame.pack(fill=tk.X, pady=10, padx=10)
        
        ttk.Label(contact_frame, text="联系方式 (选填):", font=self.default_font).pack(side=tk.LEFT, padx=5)
        
        contact_var = tk.StringVar()
        contact_entry = ttk.Entry(contact_frame, textvariable=contact_var, width=40, style="Custom.TEntry")
        contact_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Label(contact_frame, text="(邮箱/微信/QQ)", font=self.default_font).pack(side=tk.LEFT, padx=5)
        
        # 详细描述文本框
        desc_frame = ttk.Frame(parent)
        desc_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
        
        ttk.Label(desc_frame, text="详细描述:", font=self.default_font).pack(anchor=tk.W, padx=5, pady=5)
        
        desc_text = tk.Text(desc_frame, wrap=tk.WORD, height=10, font=self.default_font)
        desc_text.pack(fill=tk.BOTH, expand=True, padx=5)
        
        # 验证码输入区域
        captcha_frame = ttk.Frame(parent)
        captcha_frame.pack(fill=tk.X, pady=10, padx=10)
        
        ttk.Label(captcha_frame, text="验证码:", font=self.default_font).pack(side=tk.LEFT, padx=5)
        
        captcha_var = tk.StringVar()
        captcha_entry = ttk.Entry(captcha_frame, textvariable=captcha_var, width=10, style="Custom.TEntry")
        captcha_entry.pack(side=tk.LEFT, padx=5)
        
        # 提交按钮
        submit_frame = ttk.Frame(parent)
        submit_frame.pack(fill=tk.X, pady=10, padx=10)
        
        def submit_feedback():
            # 获取反馈内容
            feedback_type = feedback_type_var.get()
            contact = contact_var.get()
            content = desc_text.get(1.0, tk.END).strip()
            captcha = captcha_var.get()
            
            # 验证输入
            if not content:
                messagebox.showerror("错误", "请输入详细描述")
                return
            
            # 创建反馈数据
            feedback_data = {
                'type': feedback_type,
                'contact': contact,
                'content': content,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'version': self.VERSION,
                'platform': platform.system(),
                'platform_version': platform.version(),
                'status': 'pending'  # pending, sent, failed
            }
            
            # 保存到本地文件
            feedbacks, feedback_file = load_feedbacks(self.FEEDBACK_FILE)
            feedbacks.append(feedback_data)
            
            try:
                with open(feedback_file, 'w', encoding='utf-8') as f:
                    json.dump(feedbacks, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logging.error(f"保存反馈失败: {str(e)}")
            
            # 尝试发送到服务器
            threading.Thread(target=self._send_feedback_to_server, args=(feedback_data,)).start()
            
            # 显示成功消息
            messagebox.showinfo("提交成功", "感谢您的反馈！我们会尽快处理。")
            feedback_window.destroy()
        
        submit_button = ttk.Button(
            submit_frame,
            text="提交反馈",
            style="Accent.TButton",
            command=submit_feedback
        )
        submit_button.pack(side=tk.RIGHT, padx=10)
    
    def _send_feedback_to_server(self, feedback_data):
        """将反馈数据发送到服务器"""
        try:
            if not self.check_internet_connection():
                # 网络不可用，保持pending状态
                return
            
            import urllib.request
            import urllib.error
            
            # 使用统一域名，尝试多个端点
            DOMAIN = "tomarens.xyz"
            endpoints = [
                f"http://{DOMAIN}:8081/submit_feedback",  # 本地服务器配置
                f"https://{DOMAIN}/submit_feedback",      # HTTPS
                f"http://{DOMAIN}/submit_feedback",       # HTTP
            ]
            
            server_success = False
            for endpoint in endpoints:
                try:
                    data = json.dumps(feedback_data).encode('utf-8')
                    headers = {'Content-Type': 'application/json'}
                    req = urllib.request.Request(endpoint, data=data, headers=headers)
                    
                    with urllib.request.urlopen(req, timeout=10) as response:
                        if response.status == 200:
                            logging.info(f"反馈成功发送到服务器: {endpoint}")
                            server_success = True
                            break  # 成功后退出循环
                except Exception as inner_e:
                    logging.warning(f"向 {endpoint} 发送反馈失败: {str(inner_e)}")
                    continue  # 尝试下一个端点
            
            # 更新反馈状态
            if server_success:
                # 加载所有反馈
                feedbacks, feedback_file = load_feedbacks(self.FEEDBACK_FILE)
                # 查找并更新对应的反馈
                for f in feedbacks:
                    if (f.get('timestamp') == feedback_data.get('timestamp') and 
                        f.get('content') == feedback_data.get('content')):
                        f['status'] = 'sent'
                        break
                
                # 保存更新后的反馈列表
                try:
                    with open(feedback_file, 'w', encoding='utf-8') as f:
                        json.dump(feedbacks, f, ensure_ascii=False, indent=2)
                except Exception as e:
                    logging.error(f"更新反馈状态失败: {str(e)}")
        except Exception as e:
            logging.error(f"发送反馈时发生错误: {str(e)}")
    
    def display_feedbacks(self, parent):
        """显示本地保存的反馈列表"""
        # 创建一个滚动区域
        scroll_frame = ttk.Frame(parent)
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(scroll_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建文本区域用于显示反馈
        feedback_text = tk.Text(
            scroll_frame,
            wrap=tk.WORD,
            font=self.default_font,
            yscrollcommand=scrollbar.set,
            state=tk.DISABLED
        )
        feedback_text.pack(fill=tk.BOTH, expand=True, padx=5)
        
        scrollbar.config(command=feedback_text.yview)
        
        # 加载反馈数据
        feedbacks, _ = load_feedbacks(self.FEEDBACK_FILE)
        
        if not feedbacks:
            feedback_text.config(state=tk.NORMAL)
            feedback_text.insert(tk.END, "暂无反馈记录")
            feedback_text.config(state=tk.DISABLED)
            return
        
        # 显示反馈列表
        feedback_text.config(state=tk.NORMAL)
        feedback_text.delete(1.0, tk.END)
        
        for i, feedback in enumerate(feedbacks, 1):
            # 显示反馈信息
            feedback_text.insert(tk.END, f"\n===== 反馈 #{i} =====\n")
            type_map = {'bug': 'BUG问题', 'suggestion': '功能建议', 'other': '其他反馈'}
            status_map = {'pending': '等待发送', 'sent': '已发送', 'failed': '发送失败'}
            feedback_text.insert(tk.END, f"类型: {type_map.get(feedback.get('type', 'other'), '其他反馈')}\n")
            feedback_text.insert(tk.END, f"时间: {feedback.get('timestamp', '未知')}\n")
            feedback_text.insert(tk.END, f"状态: {status_map.get(feedback.get('status', 'pending'), '未知')}\n")
            
            contact = feedback.get('contact', '')
            if contact:
                feedback_text.insert(tk.END, f"联系方式: {contact}\n")
            
            feedback_text.insert(tk.END, f"内容:\n{feedback.get('content', '无内容')}\n")
        
        feedback_text.config(state=tk.DISABLED)
    
    def check_for_updates_in_background(self):
        """在后台检查更新"""
        threading.Thread(target=self.check_for_updates, args=(False,)).start()
    
    def check_for_updates(self, show_no_update_msg=True):
        """检查程序更新"""
        try:
            # 检查网络连接
            if not self.check_internet_connection():
                if show_no_update_msg:
                    messagebox.showinfo("网络连接", "当前没有网络连接，无法检查更新。")
                return
            
            # 获取最新版本信息
            latest_version_info = self.get_latest_version_info()
            
            if not latest_version_info:
                if show_no_update_msg:
                    messagebox.showinfo("检查更新", "无法获取最新版本信息。")
                return
            
            latest_version = latest_version_info.get("version", "")
            if not latest_version:
                if show_no_update_msg:
                    messagebox.showinfo("检查更新", "无法获取最新版本号。")
                return
            
            # 比较版本号
            if self.is_newer_version(latest_version, self.VERSION):
                # 有新版本
                download_url = latest_version_info.get("download_url", "")
                release_notes = latest_version_info.get("release_notes", "")
                self.show_update_dialog(latest_version, download_url, release_notes)
            else:
                if show_no_update_msg:
                    messagebox.showinfo("检查更新", f"当前已经是最新版本 (v{self.VERSION})。")
        except Exception as e:
            logging.error(f"检查更新时发生错误: {str(e)}")
            if show_no_update_msg:
                messagebox.showerror("错误", f"检查更新时发生错误: {str(e)}")
    
    def get_latest_version_info(self):
        """获取最新版本信息"""
        try:
            import urllib.request
            import urllib.error
            
            # 尝试多个URL获取更新信息
            update_urls = [
                self.UPDATE_URL,  # 默认更新URL
                f"{self.UPLOAD_SERVER_URL}/fba_calculator/latest_version_jp.json",  # 日本站专用更新URL
                "https://tomarens.xyz/fba_calculator/latest_version.json"  # 备用更新URL
            ]
            
            for url in update_urls:
                try:
                    with urllib.request.urlopen(url, timeout=10) as response:
                        if response.status == 200:
                            data = response.read().decode('utf-8')
                            latest_info = json.loads(data)
                            
                            # 保存更新信息到本地文件
                            try:
                                with open(self.UPDATE_INFO_FILE, 'w', encoding='utf-8') as f:
                                    json.dump(latest_info, f, ensure_ascii=False, indent=2)
                            except Exception as e:
                                logging.warning(f"保存更新信息失败: {str(e)}")
                            
                            return latest_info
                except urllib.error.URLError as e:
                    logging.warning(f"从 {url} 获取更新信息失败: {str(e)}")
                    continue
            
            # 如果网络获取失败，尝试从本地文件加载
            if os.path.exists(self.UPDATE_INFO_FILE):
                try:
                    with open(self.UPDATE_INFO_FILE, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception as e:
                    logging.warning(f"从本地文件加载更新信息失败: {str(e)}")
        except Exception as e:
            logging.error(f"获取最新版本信息时发生错误: {str(e)}")
        
        return None
    
    def is_newer_version(self, latest, current):
        """比较版本号，判断是否有新版本"""
        try:
            # 将版本号分割为数字列表
            latest_parts = [int(part) for part in latest.strip('v').split('.')]
            current_parts = [int(part) for part in current.strip('v').split('.')]
            
            # 补齐长度，确保可以逐位比较
            max_length = max(len(latest_parts), len(current_parts))
            latest_parts.extend([0] * (max_length - len(latest_parts)))
            current_parts.extend([0] * (max_length - len(current_parts)))
            
            # 逐位比较版本号
            for i in range(max_length):
                if latest_parts[i] > current_parts[i]:
                    return True
                elif latest_parts[i] < current_parts[i]:
                    return False
            
            # 版本号完全相同
            return False
        except Exception as e:
            logging.error(f"比较版本号时发生错误: {str(e)}")
            # 如果无法解析版本号，保守起见返回False
            return False
    
    def show_update_dialog(self, latest_version, download_url, release_notes):
        """显示更新对话框"""
        update_window = tk.Toplevel(self.root)
        update_window.title("发现新版本 - 日本站FBA配送费计算器")
        update_window.geometry("500x400")
        update_window.resizable(False, False)
        
        # 居中显示
        update_window.transient(self.root)
        update_window.grab_set()
        
        # 创建主容器
        main_frame = ttk.Frame(update_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 版本信息标签
        version_frame = ttk.Frame(main_frame)
        version_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(version_frame, text=f"当前版本: v{self.VERSION}", font=self.default_font).pack(anchor=tk.W, pady=2)
        ttk.Label(version_frame, text=f"最新版本: v{latest_version}", font=self.default_font).pack(anchor=tk.W, pady=2)
        
        # 更新内容区域
        notes_frame = ttk.LabelFrame(main_frame, text="更新内容")
        notes_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(notes_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 创建文本区域显示更新内容
        notes_text = tk.Text(
            notes_frame,
            wrap=tk.WORD,
            font=self.default_font,
            yscrollcommand=scrollbar.set,
            state=tk.DISABLED
        )
        notes_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar.config(command=notes_text.yview)
        
        # 显示更新内容
        notes_text.config(state=tk.NORMAL)
        notes_text.insert(tk.END, release_notes or "暂无更新内容")
        notes_text.config(state=tk.DISABLED)
        
        # 按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # 稍后提醒按钮
        def remind_later():
            update_window.destroy()
        
        remind_button = ttk.Button(
            button_frame,
            text="稍后提醒",
            command=remind_later
        )
        remind_button.pack(side=tk.LEFT, padx=10)
        
        # 下载更新按钮
        def download_and_update():
            if not download_url:
                messagebox.showerror("错误", "下载链接无效")
                return
            
            update_window.destroy()
            self.download_update(download_url)
        
        download_button = ttk.Button(
            button_frame,
            text="立即更新",
            style="Accent.TButton",
            command=download_and_update
        )
        download_button.pack(side=tk.RIGHT, padx=10)
    
    def download_update(self, download_url):
        """下载更新文件"""
        try:
            # 创建下载对话框
            download_window = tk.Toplevel(self.root)
            download_window.title("正在下载更新 - 日本站FBA配送费计算器")
            download_window.geometry("400x200")
            download_window.resizable(False, False)
            
            # 居中显示
            download_window.transient(self.root)
            download_window.grab_set()
            
            # 创建主容器
            main_frame = ttk.Frame(download_window, padding=20)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # 进度条
            progress_var = tk.DoubleVar()
            progress_bar = ttk.Progressbar(
                main_frame,
                variable=progress_var,
                maximum=100
            )
            progress_bar.pack(fill=tk.X, pady=20)
            
            # 状态标签
            status_var = tk.StringVar(value="正在准备下载...")
            status_label = ttk.Label(main_frame, textvariable=status_var, font=self.default_font)
            status_label.pack(pady=10)
            
            # 取消按钮
            def cancel_download():
                download_window.destroy()
            
            cancel_button = ttk.Button(
                main_frame,
                text="取消",
                command=cancel_download
            )
            cancel_button.pack(pady=10)
            
            # 在单独的线程中下载文件
            def download_thread():
                try:
                    import urllib.request
                    import urllib.error
                    import tempfile
                    
                    # 创建临时目录
                    download_dir = tempfile.gettempdir()
                    installer_name = f"FBA_Calculator_JP_v{self.VERSION}_update.exe"
                    temp_file_path = os.path.join(download_dir, installer_name)
                    
                    # 更新状态
                    status_var.set(f"正在下载更新文件...")
                    
                    # 定义进度回调函数
                    def report_progress(count, block_size, total_size):
                        percent = int(count * block_size * 100 / total_size)
                        progress_var.set(percent)
                        status_var.set(f"正在下载更新文件... {percent}%")
                    
                    # 下载文件
                    urllib.request.urlretrieve(
                        download_url,
                        temp_file_path,
                        reporthook=report_progress
                    )
                    
                    # 下载完成
                    status_var.set("下载完成，正在准备更新...")
                    
                    # 准备更新
                    self.prepare_update(temp_file_path, download_dir, installer_name)
                    
                    # 关闭下载窗口
                    download_window.destroy()
                    
                    # 提示用户重启应用
                    messagebox.showinfo(
                        "更新准备完成",
                        "更新已准备完成，请重启应用程序以应用更新。"
                    )
                    
                    # 退出应用
                    self.root.destroy()
                    
                except urllib.error.URLError as e:
                    logging.error(f"下载更新时发生网络错误: {str(e)}")
                    status_var.set(f"下载失败: 网络错误")
                    messagebox.showerror("下载失败", f"网络错误: {str(e)}")
                    
                    # 尝试备用下载方法
                    self._fallback_download(download_url, download_dir, installer_name)
                except Exception as e:
                    logging.error(f"下载更新时发生错误: {str(e)}")
                    status_var.set(f"下载失败: {str(e)}")
                    messagebox.showerror("下载失败", f"发生错误: {str(e)}")
            
            # 启动下载线程
            threading.Thread(target=download_thread, daemon=True).start()
            
        except Exception as e:
            logging.error(f"启动下载时发生错误: {str(e)}")
            messagebox.showerror("错误", f"启动下载失败: {str(e)}")
    
    def _fallback_download(self, download_url, download_dir, installer_name):
        """备用下载方法"""
        try:
            # 尝试使用webbrowser打开下载链接
            response = messagebox.askyesno(
                "下载失败",
                "无法自动下载更新，是否在浏览器中打开下载链接？"
            )
            
            if response:
                webbrowser.open(download_url)
        except Exception as e:
            logging.error(f"备用下载方法失败: {str(e)}")
    
    def prepare_update(self, temp_file_path, download_dir, exe_name):
        """准备更新文件"""
        try:
            # 确保目标文件存在
            if not os.path.exists(temp_file_path):
                raise FileNotFoundError(f"更新文件不存在: {temp_file_path}")
            
            # 获取当前可执行文件路径
            if hasattr(sys, 'frozen'):
                # 打包后的程序
                current_exe_path = sys.executable
            else:
                # 开发环境
                current_exe_path = os.path.abspath(__file__)
            
            # 创建更新脚本
            update_script = """
import os
import sys
import time
import subprocess
import shutil

# 更新文件路径
update_exe = r'{update_exe_path}'
current_exe = r'{current_exe_path}'
temp_exe = r'{temp_exe_path}'

# 等待原程序退出
time.sleep(2)

try:
    # 备份当前程序
    if os.path.exists(current_exe):
        shutil.copy2(current_exe, temp_exe)
    
    # 替换程序文件
    shutil.copy2(update_exe, current_exe)
    
    # 启动更新后的程序
    subprocess.Popen([current_exe])
    
    # 清理临时文件
    if os.path.exists(update_exe):
        os.remove(update_exe)
    if os.path.exists(temp_exe):
        os.remove(temp_exe)
except Exception as e:
    # 如果更新失败，尝试恢复备份
    if os.path.exists(temp_exe) and os.path.exists(current_exe):
        try:
            shutil.copy2(temp_exe, current_exe)
            subprocess.Popen([current_exe])
        except:
            pass
""".format(
                update_exe_path=temp_file_path,
                current_exe_path=current_exe_path,
                temp_exe_path=os.path.join(download_dir, f"{exe_name}_backup.exe")
            )
            
            # 保存更新脚本
            update_script_path = os.path.join(download_dir, "update_script.py")
            with open(update_script_path, 'w', encoding='utf-8') as f:
                f.write(update_script)
            
            # 启动更新脚本
            subprocess.Popen([sys.executable, update_script_path])
        except Exception as e:
            logging.error(f"准备更新时发生错误: {str(e)}")
            raise
    
    def show_settings_dialog(self):
        """显示程序设置对话框"""
        # 创建设置窗口
        settings_window = tk.Toplevel(self.root)
        settings_window.title("程序设置 - 日本站FBA配送费计算器")
        settings_window.geometry("500x400")
        settings_window.resizable(False, False)
        
        # 居中显示
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # 创建主容器
        main_frame = ttk.Frame(settings_window, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建标签页控件
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 创建通用设置页面
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="通用设置")
        
        # 创建主题设置页面
        theme_frame = ttk.Frame(notebook)
        notebook.add(theme_frame, text="主题设置")
        
        # 加载通用设置
        self._load_general_settings(general_frame, settings_window)
        
        # 加载主题设置
        self._load_theme_settings(theme_frame, settings_window)
        
        # 底部按钮区域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # 确认按钮
        def apply_settings():
            self.save_settings()
            messagebox.showinfo("设置已保存", "程序设置已成功保存。")
            settings_window.destroy()
        
        confirm_button = ttk.Button(
            button_frame,
            text="确认",
            style="Accent.TButton",
            command=apply_settings
        )
        confirm_button.pack(side=tk.RIGHT, padx=10)
        
        # 取消按钮
        cancel_button = ttk.Button(
            button_frame,
            text="取消",
            command=settings_window.destroy
        )
        cancel_button.pack(side=tk.RIGHT, padx=5)
    
    def _load_general_settings(self, parent, settings_window):
        """加载通用设置页面"""
        # 窗口设置区域
        window_frame = ttk.LabelFrame(parent, text="窗口设置")
        window_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # 启动时窗口大小
        startup_frame = ttk.Frame(window_frame)
        startup_frame.pack(fill=tk.X, pady=10, padx=10)
        
        ttk.Label(startup_frame, text="启动时窗口大小:", font=self.default_font).pack(side=tk.LEFT, padx=5)
        
        window_size_var = tk.StringVar(value=self.settings.get("window_size", "maximized"))
        
        def on_window_size_change():
            self.settings["window_size"] = window_size_var.get()
        
        ttk.Radiobutton(startup_frame, text="最大化", variable=window_size_var, value="maximized", command=on_window_size_change).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(startup_frame, text="窗口化", variable=window_size_var, value="windowed", command=on_window_size_change).pack(side=tk.LEFT, padx=5)
        
        # 更新设置区域
        update_frame = ttk.LabelFrame(parent, text="更新设置")
        update_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # 启动时检查更新
        check_update_var = tk.BooleanVar(value=self.settings.get("check_update_on_startup", True))
        
        def on_check_update_change():
            self.settings["check_update_on_startup"] = check_update_var.get()
        
        check_update_checkbox = ttk.Checkbutton(
            update_frame,
            text="启动时自动检查更新",
            variable=check_update_var,
            command=on_check_update_change
        )
        check_update_checkbox.pack(anchor=tk.W, pady=10, padx=10)
        
        # 其他设置区域
        other_frame = ttk.LabelFrame(parent, text="其他设置")
        other_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # 显示计算历史记录
        show_history_var = tk.BooleanVar(value=self.settings.get("show_calculation_history", True))
        
        def on_show_history_change():
            self.settings["show_calculation_history"] = show_history_var.get()
        
        show_history_checkbox = ttk.Checkbutton(
            other_frame,
            text="显示计算历史记录",
            variable=show_history_var,
            command=on_show_history_change
        )
        show_history_checkbox.pack(anchor=tk.W, pady=5, padx=10)
        
        # 自动清除输入
        clear_input_var = tk.BooleanVar(value=self.settings.get("auto_clear_input", False))
        
        def on_clear_input_change():
            self.settings["auto_clear_input"] = clear_input_var.get()
        
        clear_input_checkbox = ttk.Checkbutton(
            other_frame,
            text="计算后自动清除输入",
            variable=clear_input_var,
            command=on_clear_input_change
        )
        clear_input_checkbox.pack(anchor=tk.W, pady=5, padx=10)
    
    def _load_theme_settings(self, parent, settings_window):
        """加载主题设置页面"""
        # 主题选择区域
        theme_frame = ttk.LabelFrame(parent, text="主题选择")
        theme_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
        
        # 可用主题列表
        themes = [
            "默认主题",
            "暗黑主题",
            "明亮主题",
            "蓝色主题",
            "绿色主题"
        ]
        
        # 当前主题
        current_theme = self.settings.get("theme", "默认主题")
        theme_var = tk.StringVar(value=current_theme)
        
        # 主题列表框
        theme_listbox = tk.Listbox(
            theme_frame,
            listvariable=tk.StringVar(value=themes),
            font=self.default_font,
            height=5,
            width=30
        )
        theme_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(theme_frame, orient=tk.VERTICAL, command=theme_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        theme_listbox.config(yscrollcommand=scrollbar.set)
        
        # 选中当前主题
        if current_theme in themes:
            theme_listbox.selection_set(themes.index(current_theme))
            theme_listbox.see(themes.index(current_theme))
        
        # 预览按钮
        preview_button = ttk.Button(
            parent,
            text="预览主题",
            command=lambda: self._apply_theme_by_name(theme_var.get())
        )
        preview_button.pack(pady=10)
        
        # 保存按钮
        def save_theme():
            selected_theme = theme_var.get()
            self.settings["theme"] = selected_theme
            self._apply_theme_by_name(selected_theme)
            messagebox.showinfo("主题已应用", f"已应用'{selected_theme}'主题。")
        
        save_theme_button = ttk.Button(
            parent,
            text="保存主题",
            style="Accent.TButton",
            command=save_theme
        )
        save_theme_button.pack(pady=10)
        
        # 主题描述
        desc_frame = ttk.LabelFrame(parent, text="主题说明")
        desc_frame.pack(fill=tk.X, pady=10, padx=10)
        
        desc_text = tk.Text(
            desc_frame,
            wrap=tk.WORD,
            font=self.default_font,
            height=3,
            state=tk.DISABLED
        )
        desc_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 显示主题描述
        desc_text.config(state=tk.NORMAL)
        desc_text.insert(tk.END, "选择喜欢的主题样式，点击预览按钮查看效果，点击保存按钮应用主题。")
        desc_text.config(state=tk.DISABLED)
    
    def _apply_theme_by_name(self, theme_name):
        """根据主题名称应用主题"""
        # 预定义主题颜色
        themes = {
            "默认主题": {
                "background": "#f0f0f0",
                "frame_bg": "#ffffff",
                "text_bg": "#ffffff",
                "text_fg": "#000000",
                "button_bg": "#e6e6e6",
                "button_active": "#d5d5d5",
                "button_pressed": "#c0c0c0",
                "highlight_bg": "#d4e6f1",
                "header_bg": "#aed6f1",
                "segment_bg": "#f9ebea",
                "border_color": "#bdc3c7",
                "shadow_color": "#34495e"
            },
            "暗黑主题": {
                "background": "#2c3e50",
                "frame_bg": "#34495e",
                "text_bg": "#34495e",
                "text_fg": "#ecf0f1",
                "button_bg": "#3498db",
                "button_active": "#2980b9",
                "button_pressed": "#1f6dad",
                "highlight_bg": "#7f8c8d",
                "header_bg": "#2980b9",
                "segment_bg": "#27ae60",
                "border_color": "#7f8c8d",
                "shadow_color": "#000000"
            },
            "明亮主题": {
                "background": "#ffffff",
                "frame_bg": "#f8f9fa",
                "text_bg": "#ffffff",
                "text_fg": "#212529",
                "button_bg": "#6c757d",
                "button_active": "#5a6268",
                "button_pressed": "#545b62",
                "highlight_bg": "#e9ecef",
                "header_bg": "#adb5bd",
                "segment_bg": "#f8f9fa",
                "border_color": "#dee2e6",
                "shadow_color": "#6c757d"
            },
            "蓝色主题": {
                "background": "#e3f2fd",
                "frame_bg": "#bbdefb",
                "text_bg": "#ffffff",
                "text_fg": "#1565c0",
                "button_bg": "#1976d2",
                "button_active": "#1565c0",
                "button_pressed": "#0d47a1",
                "highlight_bg": "#90caf9",
                "header_bg": "#42a5f5",
                "segment_bg": "#64b5f6",
                "border_color": "#90caf9",
                "shadow_color": "#1565c0"
            },
            "绿色主题": {
                "background": "#e8f5e9",
                "frame_bg": "#c8e6c9",
                "text_bg": "#ffffff",
                "text_fg": "#2e7d32",
                "button_bg": "#43a047",
                "button_active": "#388e3c",
                "button_pressed": "#2e7d32",
                "highlight_bg": "#a5d6a7",
                "header_bg": "#66bb6a",
                "segment_bg": "#81c784",
                "border_color": "#a5d6a7",
                "shadow_color": "#2e7d32"
            }
        }
        
        # 获取主题颜色
        theme_colors = themes.get(theme_name, themes["默认主题"])
        
        # 更新颜色主题
        self.color_theme.update(theme_colors)
        
        # 应用主题颜色到UI元素
        self.apply_theme()
    
    def on_closing(self):
        """窗口关闭时的处理"""
        # 保存设置
        self.save_settings()
        self.root.destroy()
    
    def create_title(self):
        """创建标题"""
        title_frame = ttk.Frame(self.content_container)
        title_frame.pack(fill=tk.X, pady=10)
        
        title_label = ttk.Label(
            title_frame,
            text="日本站FBA配送费计算器",
            font=self.title_font
        )
        title_label.pack(anchor=tk.W)
    
    def create_size_inputs(self):
        """创建尺寸输入区域"""
        size_frame = ttk.LabelFrame(self.content_container, text="商品尺寸 (厘米)")
        size_frame.pack(fill=tk.X, pady=10)
        
        # 创建尺寸输入行
        self.max_len_var = tk.StringVar(value="")
        self.mid_len_var = tk.StringVar(value="")
        self.min_len_var = tk.StringVar(value="")
        
        # 最长边输入
        max_len_frame = ttk.Frame(size_frame)
        max_len_frame.pack(fill=tk.X, pady=5, padx=10)
        
        max_len_label = ttk.Label(max_len_frame, text="最长边:", width=10, anchor=tk.W)
        max_len_label.pack(side=tk.LEFT, padx=5)
        
        max_len_entry = ttk.Entry(max_len_frame, textvariable=self.max_len_var, style="Custom.TEntry")
        max_len_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        max_len_unit = ttk.Label(max_len_frame, text="厘米", width=5)
        max_len_unit.pack(side=tk.LEFT, padx=5)
        
        # 次长边输入
        mid_len_frame = ttk.Frame(size_frame)
        mid_len_frame.pack(fill=tk.X, pady=5, padx=10)
        
        mid_len_label = ttk.Label(mid_len_frame, text="次长边:", width=10, anchor=tk.W)
        mid_len_label.pack(side=tk.LEFT, padx=5)
        
        mid_len_entry = ttk.Entry(mid_len_frame, textvariable=self.mid_len_var, style="Custom.TEntry")
        mid_len_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        mid_len_unit = ttk.Label(mid_len_frame, text="厘米", width=5)
        mid_len_unit.pack(side=tk.LEFT, padx=5)
        
        # 最短边输入
        min_len_frame = ttk.Frame(size_frame)
        min_len_frame.pack(fill=tk.X, pady=5, padx=10)
        
        min_len_label = ttk.Label(min_len_frame, text="最短边:", width=10, anchor=tk.W)
        min_len_label.pack(side=tk.LEFT, padx=5)
        
        min_len_entry = ttk.Entry(min_len_frame, textvariable=self.min_len_var, style="Custom.TEntry")
        min_len_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        min_len_unit = ttk.Label(min_len_frame, text="厘米", width=5)
        min_len_unit.pack(side=tk.LEFT, padx=5)
    
    def create_weight_inputs(self):
        """创建重量输入区域"""
        self.weight_frame = ttk.LabelFrame(self.content_container, text="商品信息")
        self.weight_frame.pack(fill=tk.X, pady=10)
        
        # 重量输入
        weight_frame = ttk.Frame(self.weight_frame)
        weight_frame.pack(fill=tk.X, pady=5, padx=10)
        
        weight_label = ttk.Label(weight_frame, text="重量:", width=10, anchor=tk.W)
        weight_label.pack(side=tk.LEFT, padx=5)
        
        self.weight_var = tk.StringVar(value="")
        weight_entry = ttk.Entry(weight_frame, textvariable=self.weight_var, style="Custom.TEntry")
        weight_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        weight_unit = ttk.Label(weight_frame, text="克", width=5)
        weight_unit.pack(side=tk.LEFT, padx=5)
        
        # 创建价格超过1000日元的复选框
        self.price_over_1000_var = tk.BooleanVar(value=True)
        self.price_over_1000_check = ttk.Checkbutton(
            self.weight_frame,
            text="价格超过1000日元",
            variable=self.price_over_1000_var
        )
        self.price_over_1000_check.pack(pady=5, anchor=tk.W, padx=15)
        
        # 创建冷冻商品复选框
        self.is_frozen_var = tk.BooleanVar(value=False)
        self.is_frozen_check = ttk.Checkbutton(
            self.weight_frame,
            text="冷冻商品",
            variable=self.is_frozen_var
        )
        self.is_frozen_check.pack(pady=5, anchor=tk.W, padx=15)
    
    def create_segment_display(self):
        """创建尺寸分段显示区域"""
        segment_frame = ttk.LabelFrame(self.content_container, text="尺寸分段信息")
        segment_frame.pack(fill=tk.X, pady=10)
        
        # 尺寸分段显示
        self.segment_var = tk.StringVar(value="")
        segment_label = ttk.Label(segment_frame, text="当前尺寸分段:")
        segment_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        segment_value = ttk.Label(segment_frame, textvariable=self.segment_var, font=self.button_font)
        segment_value.pack(side=tk.LEFT, padx=5, pady=5)
    
    def create_buttons(self):
        """创建按钮区域"""
        button_frame = ttk.Frame(self.content_container)
        button_frame.pack(fill=tk.X, pady=10)
        
        # 计算按钮
        calculate_button = ttk.Button(
            button_frame,
            text="计算配送费",
            style="Accent.TButton",
            command=self.calculate
        )
        calculate_button.pack(side=tk.LEFT, padx=10)
        
        # 清空按钮
        clear_button = ttk.Button(
            button_frame,
            text="清空输入",
            command=self.clear_inputs
        )
        clear_button.pack(side=tk.LEFT, padx=5)
        
        # 添加右侧功能按钮区域
        right_button_frame = ttk.Frame(button_frame)
        right_button_frame.pack(side=tk.RIGHT, padx=10)
        
        # BUG反馈按钮
        feedback_button = ttk.Button(
            right_button_frame,
            text="BUG反馈",
            command=self.show_bug_feedback
        )
        feedback_button.pack(side=tk.RIGHT, padx=5)
        
        # 上传更新按钮
        update_button = ttk.Button(
            right_button_frame,
            text="检查更新",
            command=self.check_for_updates
        )
        update_button.pack(side=tk.RIGHT, padx=5)
        
        # 程序设置按钮
        settings_button = ttk.Button(
            right_button_frame,
            text="程序设置",
            command=self.show_settings_dialog
        )
        settings_button.pack(side=tk.RIGHT, padx=5)
    
    def create_result_area(self):
        """创建结果显示区域"""
        result_frame = ttk.LabelFrame(self.content_container, text="计算结果")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # 创建文本区域用于显示结果
        self.result_text = tk.Text(result_frame, wrap=tk.WORD, font=self.default_font)
        self.result_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(self.result_text, command=self.result_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=scrollbar.set)
    
    def create_status_bar(self):
        """创建底部状态栏"""
        status_frame = ttk.Frame(self.root, height=30)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # 状态栏信息
        self.status_var = tk.StringVar(value=f"版本 {self.VERSION}")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, anchor=tk.W)
        status_label.pack(fill=tk.X, padx=10, pady=5)
        
        # 更新时间
        self.update_time()
    
    def update_time(self):
        """更新状态栏时间"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.status_var.set(f"版本 {self.VERSION}  |  {current_time}")
        # 每秒更新一次
        self.root.after(1000, self.update_time)
    
    def clear_inputs(self):
        """清空所有输入"""
        self.max_len_var.set("")
        self.mid_len_var.set("")
        self.min_len_var.set("")
        self.weight_var.set("")
        self.segment_var.set("")
        self.result_text.delete(1.0, tk.END)
    
    def update_result(self, result_text):
        """更新结果显示"""
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, result_text)
    
    def calculate(self):
        """执行费用计算"""
        try:
            # 获取输入值
            max_len = float(self.max_len_var.get())
            mid_len = float(self.mid_len_var.get())
            min_len = float(self.min_len_var.get())
            weight = float(self.weight_var.get())
            
            # 排序边长，确保max_len是最长边
            lengths = sorted([max_len, mid_len, min_len], reverse=True)
            max_len, mid_len, min_len = lengths
            
            # 更新尺寸分段显示
            size_segment = self.determine_size_segment_jp(max_len)
            self.segment_var.set(size_segment)
            
            # 检查商品价格
            price_over_1000 = self.price_over_1000_var.get()
            
            # 检查是否为冷冻商品
            is_frozen = self.is_frozen_var.get()
            
            # 计算费用并获取详细计算过程
            fee, calculation_steps = self.calculate_fee_with_steps_jp(
                size_segment, weight, price_over_1000, is_frozen
            )
            
            # 计算总尺寸
            total_size = max_len + mid_len + min_len
            
            # 生成结果文本
            result_text = f"===== 计算结果 =====\n\n"
            result_text += f"📦 商品尺寸分段：{size_segment}\n\n"
            result_text += f"⚖️ 重量：{weight} 克\n\n"
            result_text += f"📏 尺寸详情：\n"
            result_text += f"   最长边：{max_len} 厘米\n"
            result_text += f"   次长边：{mid_len} 厘米\n"
            result_text += f"   最短边：{min_len} 厘米\n"
            result_text += f"   总尺寸：{total_size} 厘米\n\n"
            result_text += f"💰 配送费：{fee} 日元\n\n"
            result_text += f"===== 计算过程 =====\n\n{calculation_steps}"
            
            # 保存到历史记录
            calculation_record = {
                'timestamp': datetime.now(),
                'site': 'jp',
                'max_len': max_len,
                'mid_len': mid_len,
                'min_len': min_len,
                'weight': weight,
                'size_segment': size_segment,
                'shipping_fee': fee,
                'total_size': total_size
            }
            
            # 更新结果
            self.update_result(result_text)
            
            # 添加到历史记录
            self.calculation_history.append(calculation_record)
            
            # 限制历史记录数量，最多保存100条
            if len(self.calculation_history) > 100:
                self.calculation_history.pop(0)
            
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的数字！")
        except Exception as e:
            messagebox.showerror("计算错误", f"计算过程中出现错误：\n{str(e)}")
    
    def determine_size_segment_jp(self, max_len_cm):
        """
        判断日本站的尺寸分段（基于最新FBA配送费计算标准）
        参数:
        - max_len_cm: 最长边(厘米)
        返回:
        - 尺寸分段描述
        """
        # 小号：不超过35厘米（对应23厘米×35厘米×10厘米的规格）
        if max_len_cm <= 35:
            return "小号"
        # 标准尺寸：超过35厘米但不超过80厘米
        elif max_len_cm <= 80:
            return "标准"
        # 大件：超过80厘米但不超过120厘米
        elif max_len_cm <= 120:
            return "大件"
        # 超大件：超过120厘米但不超过200厘米
        elif max_len_cm <= 200:
            return "超大件"
        # 超大件（超出200厘米）：超过200厘米的特殊情况
        else:
            return "超大件（超出200厘米）"
    
    def calculate_fee_with_steps_jp(self, size_segment, weight_g, price_over_1000, is_frozen=False):
        """
        计算日本站FBA配送费用并返回详细计算过程
        参数:
        - size_segment: 尺寸分段
        - weight_g: 重量(克)
        - price_over_1000: 价格是否超过1000日元
        - is_frozen: 是否为冷冻商品
        返回:
        - (费用, 计算步骤)
        """
        steps = []
        
        # 获取最大长度
        max_len_cm = 0
        if hasattr(self, 'max_len_var') and self.max_len_var.get():
            try:
                max_len_cm = float(self.max_len_var.get())
            except ValueError:
                pass
        
        # 转换重量为千克
        weight_kg = weight_g / 1000
        
        # 记录基本信息
        steps.append("===== 日本站FBA配送费计算 =====")
        steps.append(f"1. 根据尺寸分段 '{size_segment}' 计算费用")
        steps.append(f"2. 商品价格{'超过' if price_over_1000 else '不超过'}1000日元")
        steps.append(f"3. 商品重量: {weight_g} 克 ({weight_kg:.2f} 千克)")
        steps.append(f"4. 商品最长边: {max_len_cm} 厘米")
        steps.append(f"5. 商品类型: {'冷冻商品' if is_frozen else '非冷冻商品'}")
        
        # 根据表格定义的费用标准
        if price_over_1000:
            steps.append("6. 使用价格超过1000日元的费用标准")
        else:
            steps.append("6. 使用价格不超过1000日元的费用标准")
        
        # 根据尺寸分段和重量计算费用
        fee = 0
        
        # 如果是冷冻商品，使用冷冻商品的费用标准
        if is_frozen:
            # 冷冻商品 - 小号尺寸费用
            if size_segment == "小号":
                if weight_g <= 250:
                    fee = 695 if price_over_1000 else 647
                    steps.append(f"7. 冷冻商品-小号（≤250克）: {fee} 日元")
            
            # 冷冻商品 - 标准尺寸费用
            elif size_segment == "标准":
                if max_len_cm <= 26:
                    fee = 867 if price_over_1000 else 697
                    steps.append(f"7. 冷冻商品-标准尺寸-1（≤26厘米）: {fee} 日元")
                elif max_len_cm <= 32:
                    fee = 788 if price_over_1000 else 723
                    steps.append(f"7. 冷冻商品-标准尺寸-2（≤32厘米）: {fee} 日元")
                elif max_len_cm <= 45:
                    fee = 830 if price_over_1000 else 754
                    steps.append(f"7. 冷冻商品-标准尺寸-3（≤45厘米）: {fee} 日元")
                elif max_len_cm <= 60:
                    fee = 960 if price_over_1000 else 874
                    steps.append(f"7. 冷冻商品-标准尺寸-4（≤60厘米）: {fee} 日元")
                elif max_len_cm <= 80:
                    if weight_kg <= 2:
                        fee = 898 if price_over_1000 else 804
                        steps.append(f"7. 冷冻商品-标准尺寸-5（≤80厘米，≤2千克）: {fee} 日元")
                    elif weight_kg <= 2.5:
                        fee = 987 if price_over_1000 else 917
                        steps.append(f"7. 冷冻商品-标准尺寸-6（≤80厘米，≤2.5千克）: {fee} 日元")
                    elif weight_kg <= 3.5:
                        fee = 1027 if price_over_1000 else 941
                        steps.append(f"7. 冷冻商品-标准尺寸-7（≤80厘米，≤3.5千克）: {fee} 日元")
                    else:
                        fee = 1071 if price_over_1000 else 941
                        steps.append(f"7. 冷冻商品-标准尺寸-8（≤80厘米，>3.5千克）: {fee} 日元")
            
            # 冷冻商品 - 大件费用
            elif size_segment == "大件":
                if max_len_cm <= 60:
                    if weight_kg <= 2:
                        fee = 984 if price_over_1000 else 898
                        steps.append(f"7. 冷冻商品-大件-1（≤60厘米，≤2千克）: {fee} 日元")
                elif max_len_cm <= 80:
                    if weight_kg <= 2:
                        fee = 990 if price_over_1000 else 900
                        steps.append(f"7. 冷冻商品-大件-2（≤80厘米，≤2千克）: {fee} 日元")
                    elif weight_kg <= 5:
                        fee = 1080 if price_over_1000 else 983
                        steps.append(f"7. 冷冻商品-大件-3（≤80厘米，≤5千克）: {fee} 日元")
                elif max_len_cm <= 100:
                    fee = 1153 if price_over_1000 else 1041
                    steps.append(f"7. 冷冻商品-大件-4（≤100厘米）: {fee} 日元")
            
            # 冷冻商品 - 超大件费用
            elif size_segment == "超大件":
                if max_len_cm <= 120:
                    fee = 1559 if price_over_1000 else 1434
                    steps.append(f"7. 冷冻商品-超大件-1（≤120厘米）: {fee} 日元")
                elif max_len_cm <= 140:
                    fee = 1925 if price_over_1000 else 1760
                    steps.append(f"7. 冷冻商品-超大件-2（≤140厘米）: {fee} 日元")
                elif max_len_cm <= 170:
                    fee = 2760 if price_over_1000 else 2600
                    steps.append(f"7. 冷冻商品-超大件-3（≤170厘米）: {fee} 日元")
                elif max_len_cm <= 200:
                    fee = 3720 if price_over_1000 else 3500
                    steps.append(f"7. 冷冻商品-超大件-4（≤200厘米）: {fee} 日元")
            
            # 冷冻商品 - 超大件（超出200厘米）
            elif size_segment == "超大件（超出200厘米）":
                fee = 4820 if price_over_1000 else 4620
                steps.append(f"7. 冷冻商品-超大件（超出200厘米）: {fee} 日元")
                steps.append("注意：超过200厘米或超过40千克的商品可能需要支付额外的尺寸费用")
        else:
            # 非冷冻商品 - 小号尺寸费用
            if size_segment == "小号":
                if weight_g <= 250:
                    fee = 630 if price_over_1000 else 589
                    steps.append(f"7. 非冷冻商品-小号（≤250克）: {fee} 日元")
            
            # 非冷冻商品 - 标准尺寸费用
            elif size_segment == "标准":
                if max_len_cm <= 26:
                    fee = 807 if price_over_1000 else 677
                    steps.append(f"7. 非冷冻商品-标准尺寸-1（≤26厘米）: {fee} 日元")
                elif max_len_cm <= 32:
                    fee = 781 if price_over_1000 else 723
                    steps.append(f"7. 非冷冻商品-标准尺寸-2（≤32厘米）: {fee} 日元")
                elif max_len_cm <= 45:
                    fee = 860 if price_over_1000 else 784
                    steps.append(f"7. 非冷冻商品-标准尺寸-3（≤45厘米）: {fee} 日元")
                elif max_len_cm <= 60:
                    fee = 994 if price_over_1000 else 914
                    steps.append(f"7. 非冷冻商品-标准尺寸-4（≤60厘米）: {fee} 日元")
                elif max_len_cm <= 80:
                    fee = 896 if price_over_1000 else 801
                    steps.append(f"7. 非冷冻商品-标准尺寸-5（≤80厘米，≤2千克）: {fee} 日元")
            
            # 非冷冻商品 - 大件费用
            elif size_segment == "大件":
                if max_len_cm <= 60:
                    fee = 946 if price_over_1000 else 886
                    steps.append(f"7. 非冷冻商品-大件-1（≤60厘米，≤2千克）: {fee} 日元")
                elif max_len_cm <= 80:
                    if weight_kg <= 2:
                        fee = 963 if price_over_1000 else 893
                        steps.append(f"7. 非冷冻商品-大件-2（≤80厘米，≤2千克）: {fee} 日元")
                    elif weight_kg <= 5:
                        fee = 1032 if price_over_1000 else 933
                        steps.append(f"7. 非冷冻商品-大件-3（≤80厘米，≤5千克）: {fee} 日元")
                elif max_len_cm <= 100:
                    fee = 1052 if price_over_1000 else 944
                    steps.append(f"7. 非冷冻商品-大件-4（≤100厘米）: {fee} 日元")
                elif max_len_cm <= 120:
                    if weight_kg <= 10:
                        fee = 1285 if price_over_1000 else 1101
                        steps.append(f"7. 非冷冻商品-大件-5（≤120厘米，≤10千克）: {fee} 日元")
            
            # 非冷冻商品 - 超大件费用
            elif size_segment == "超大件":
                if max_len_cm <= 140:
                    fee = 1756 if price_over_1000 else 1680
                    steps.append(f"7. 非冷冻商品-超大件-1（≤140厘米）: {fee} 日元")
                elif max_len_cm <= 170:
                    fee = 2675 if price_over_1000 else 2555
                    steps.append(f"7. 非冷冻商品-超大件-2（≤170厘米）: {fee} 日元")
                elif max_len_cm <= 200:
                    if weight_kg <= 30:
                        fee = 3691 if price_over_1000 else 3491
                        steps.append(f"7. 非冷冻商品-超大件-3（≤200厘米，≤30千克）: {fee} 日元")
                    elif weight_kg <= 40:
                        fee = 4650 if price_over_1000 else 4450
                        steps.append(f"7. 非冷冻商品-超大件-4（≤200厘米，≤40千克）: {fee} 日元")
            
            # 非冷冻商品 - 超大件（超出200厘米）
            elif size_segment == "超大件（超出200厘米）":
                fee = 4820 if price_over_1000 else 4620
                steps.append(f"7. 非冷冻商品-超大件（超出200厘米）: {fee} 日元")
                steps.append("注意：超过200厘米或超过40千克的商品可能需要支付额外的尺寸费用")
        
        # 特殊情况处理：如果没有匹配到费用规则
        if fee == 0:
            # 尝试根据重量进行兜底计算
            if is_frozen:
                # 冷冻商品兜底计算
                if weight_kg <= 2:
                    fee = 984 if price_over_1000 else 898
                    steps.append(f"7. 冷冻商品默认费用（≤2千克）: {fee} 日元")
                elif weight_kg <= 5:
                    fee = 1080 if price_over_1000 else 983
                    steps.append(f"7. 冷冻商品默认费用（≤5千克）: {fee} 日元")
                elif weight_kg <= 10:
                    fee = 1285 if price_over_1000 else 1101
                    steps.append(f"7. 冷冻商品默认费用（≤10千克）: {fee} 日元")
                else:
                    fee = 1756 if price_over_1000 else 1680
                    steps.append(f"7. 冷冻商品默认费用（>10千克）: {fee} 日元")
            else:
                # 非冷冻商品兜底计算
                if weight_kg <= 2:
                    fee = 946 if price_over_1000 else 886
                    steps.append(f"7. 非冷冻商品默认费用（≤2千克）: {fee} 日元")
                elif weight_kg <= 5:
                    fee = 1032 if price_over_1000 else 933
                    steps.append(f"7. 非冷冻商品默认费用（≤5千克）: {fee} 日元")
                elif weight_kg <= 10:
                    fee = 1285 if price_over_1000 else 1101
                    steps.append(f"7. 非冷冻商品默认费用（≤10千克）: {fee} 日元")
                else:
                    fee = 1756 if price_over_1000 else 1680
                    steps.append(f"7. 非冷冻商品默认费用（>10千克）: {fee} 日元")
        
        # 添加最终计算结果
        steps.append(f"8. 最终配送费: {fee} 日元")
        
        # 添加燃油附加费说明
        steps.append("\n注：所有费用包含10%的燃油附加费")
        
        # 添加冷冻商品特殊说明
        if is_frozen:
            steps.append("\n冷冻商品特别说明：")
            steps.append("- 冷冻商品需使用温控包装，可能产生额外费用")
            steps.append("- 部分冷冻食品可能受特殊处理费影响")
        
        return fee, "\n".join(steps)

def load_feedbacks(feedback_file="feedback_jp.json"):
    """加载本地保存的反馈数据"""
    feedbacks = []
    try:
        # 确定反馈文件的位置
        if hasattr(sys, '_MEIPASS'):
            # 在打包后的程序中
            feedback_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), feedback_file)
        else:
            # 在开发环境中
            feedback_file_path = feedback_file
        
        # 如果文件存在，加载反馈数据
        if os.path.exists(feedback_file_path):
            with open(feedback_file_path, 'r', encoding='utf-8') as f:
                feedbacks = json.load(f)
    except Exception as e:
        logging.error(f"加载反馈数据失败: {str(e)}")
    
    return feedbacks, feedback_file_path

def run_app():
    """运行应用程序"""
    # 设置日志
    try:
        if hasattr(sys, '_MEIPASS'):
            log_dir = sys._MEIPASS
        else:
            log_dir = os.path.dirname(os.path.abspath(__file__))
        log_file = os.path.join(log_dir, "fba_jp_calculator.log")
    except:
        log_file = "fba_jp_calculator.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    
    logging.info("日本站FBA配送费计算器启动")
    
    # 创建主窗口
    root = tk.Tk()
    
    # 创建应用实例
    app = FBAShippingCalculatorJP(root)
    
    # 启动主循环
    root.mainloop()

if __name__ == "__main__":
    try:
        # 确保UTF-8编码
        if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding != 'utf-8' and hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
    
    sys.exit(run_app())
