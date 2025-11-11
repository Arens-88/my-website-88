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

class FBAShippingCalculator:
    # 程序版本信息
    VERSION = "1.3.1"
    UPDATE_URL = "https://example.com/fba_calculator/latest_version.json"  # 更新检查URL
    SETTINGS_FILE = "settings.json"  # 设置文件路径
    UPDATE_INFO_FILE = "update_info.json"  # 更新信息文件路径
    UPLOAD_SERVER_URL = "https://tomarens.xyz"  # 上传服务器地址
    
    def __init__(self, root):
        # 设置中文字体支持
        self.setup_fonts()
        
        # 加载用户设置
        self.settings = self.load_settings()
        
        self.root = root
        self.root.title(f"FBA配送费计算器 v{self.VERSION}")
        
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
        
        # 创建顶部导航框架
        self.create_navigation_frame()
        
        # 创建主容器
        self.content_container = ttk.Frame(root, padding="20")
        self.content_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 程序退出时保存设置
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 检查是否为开发者模式（通过命令行参数或设置）
        self.is_developer_mode = '--developer' in sys.argv
        
        # 初始化当前页面
        self.current_page = "fba"
        
        # 添加站点选择变量，默认为美国站
        self.site_var = tk.StringVar(value="us")  # us表示美国站，jp表示日本站
        self.current_site = "us"  # 设置当前站点，确保在创建UI之前就有这个属性
        self.current_site = "us"  # 当前站点，用于单位转换判断
        
        # 创建FBA计算器页面容器
        self.fba_frame = ttk.Frame(self.content_container)
        
        # 创建汇率计算器页面容器（初始隐藏）
        self.currency_frame = ttk.Frame(self.content_container)
        
        # 创建重量转换器页面容器（初始隐藏）
        self.weight_converter_frame = ttk.Frame(self.content_container)
        
        # 为FBA计算器创建UI元素
        self.container = self.fba_frame  # 让原有代码使用fba_frame作为容器
        self.create_title()
        
        # 添加站点切换按钮
        self.create_site_selector()
        
        self.create_size_inputs()
        self.create_weight_inputs()
        self.create_segment_display()
        self.create_buttons()
        self.create_result_area()
        
        # 创建汇率计算器UI
        self.create_currency_converter_ui()
        
        # 创建重量转换器UI
        self.create_weight_converter_ui()
        
        # 显示默认页面
        self.show_page("fba")
        
        # 添加底部状态栏
        self.create_status_bar()
        
        # 启动后台检查更新
        self.check_for_updates_in_background()
        
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
        # 根据操作系统设置合适的字体
        system = platform.system()
        if system == "Windows":
            self.default_font = ("微软雅黑", 10)
            self.header_font = ("微软雅黑", 11, "bold")
            self.title_font = ("微软雅黑", 16, "bold")
            self.button_font = ("微软雅黑", 10, "normal")
        else:
            # 非Windows系统使用通用字体
            self.default_font = ("SimHei", 10)
            self.header_font = ("SimHei", 11, "bold")
            self.title_font = ("SimHei", 16, "bold")
            self.button_font = ("SimHei", 10, "normal")
    
    def is_developer_mode(self):
        """检查是否处于开发者模式
        
        开发者模式检测方法：
        1. 检查是否有开发者模式的环境变量
        2. 检查当前目录是否包含开发相关文件
        3. 检查是否以Python脚本方式运行（非编译版本）
        
        Returns:
            bool: 是否为开发者模式
        """
        try:
            # 检查环境变量
            if os.environ.get('FBA_CALCULATOR_DEV_MODE') == '1':
                return True
            
            # 检查开发相关文件是否存在
            dev_files = ['fba_gui.spec', 'requirements.txt', 'test_update.py']
            current_dir = os.path.dirname(os.path.abspath(__file__))
            for dev_file in dev_files:
                if os.path.exists(os.path.join(current_dir, dev_file)):
                    return True
            
            # 检查是否以Python脚本方式运行（非编译版本）
            if not getattr(sys, 'frozen', False):
                return True
                
        except Exception:
            pass
            
        return False
        
    def show_local_feedback(self):
        """显示本地反馈管理界面"""
        # 创建反馈管理窗口
        feedback_window = tk.Toplevel(self.root)
        feedback_window.title("本地反馈管理")
        feedback_window.geometry("700x500")
        feedback_window.configure(bg=self.color_theme["background"])
        
        # 设置窗口在屏幕中心
        feedback_window.update_idletasks()
        width = feedback_window.winfo_width()
        height = feedback_window.winfo_height()
        x = (feedback_window.winfo_screenwidth() // 2) - (width // 2)
        y = (feedback_window.winfo_screenheight() // 2) - (height // 2)
        feedback_window.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
        # 创建标签页控件
        notebook = ttk.Notebook(feedback_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建所有反馈标签页
        all_frame = ttk.Frame(notebook)
        notebook.add(all_frame, text="所有反馈")
        
        # 创建待发送标签页
        pending_frame = ttk.Frame(notebook)
        notebook.add(pending_frame, text="待发送")
        
        # 创建已发送标签页
        sent_frame = ttk.Frame(notebook)
        notebook.add(sent_frame, text="已发送")
        
        # 创建发送失败标签页
        failed_frame = ttk.Frame(notebook)
        notebook.add(failed_frame, text="发送失败")
        
        # 加载反馈数据
        def load_feedbacks():
            # 确定反馈文件位置
            if getattr(sys, 'frozen', False):  # 编译后的可执行文件
                feedback_dir = os.path.dirname(os.path.abspath(sys.executable))
            else:  # 直接运行Python脚本
                feedback_dir = os.path.dirname(os.path.abspath(__file__))
            
            feedback_file = os.path.join(feedback_dir, "feedback.json")
            feedbacks = []
            
            if os.path.exists(feedback_file):
                try:
                    with open(feedback_file, 'r', encoding='utf-8') as f:
                        feedbacks = json.load(f)
                except json.JSONDecodeError:
                    logging.error("反馈文件损坏，创建新的反馈列表")
                    feedbacks = []
            
            return feedbacks, feedback_file
        
        # 显示反馈列表
        def display_feedbacks(frame, status_filter=None):
            # 清空现有内容
            for widget in frame.winfo_children():
                widget.destroy()
            
            # 加载反馈数据
            feedbacks, _ = load_feedbacks()
            
            # 根据状态筛选
            if status_filter:
                filtered_feedbacks = [f for f in feedbacks if f.get('status') == status_filter]
            else:
                filtered_feedbacks = feedbacks
            
            # 创建滚动框架
            canvas = tk.Canvas(frame, bg=self.color_theme["background"])
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
            scrollable_frame = ttk.Frame(canvas)
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # 放置滚动区域
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # 如果没有反馈
            if not filtered_feedbacks:
                ttk.Label(
                    scrollable_frame,
                    text="暂无反馈记录",
                    font=self.default_font,
                    background=self.color_theme["background"]
                ).pack(pady=50)
                return
            
            # 显示反馈列表
            for i, feedback in enumerate(filtered_feedbacks):
                feedback_frame = ttk.LabelFrame(
                    scrollable_frame,
                    text=f"反馈 #{len(filtered_feedbacks) - i} - {feedback.get('timestamp', '未知时间')}",
                    padding="10"
                )
                feedback_frame.pack(fill=tk.X, padx=10, pady=5)
                
                # 反馈信息
                info_text = []
                info_text.append(f"类型: {feedback.get('type', 'unknown')}")
                info_text.append(f"状态: {feedback.get('status', 'unknown')}")
                info_text.append(f"版本: {feedback.get('version', 'unknown')}")
                if feedback.get('contact'):
                    info_text.append(f"联系方式: {feedback.get('contact')}")
                info_text.append(f"系统: {feedback.get('system', 'unknown')}")
                
                ttk.Label(
                    feedback_frame,
                    text="\n".join(info_text),
                    font=self.default_font,
                    justify=tk.LEFT
                ).pack(fill=tk.X, padx=5, pady=5)
                
                # 反馈内容
                content_frame = ttk.Frame(feedback_frame)
                content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
                
                content_text = tk.Text(
                    content_frame,
                    wrap=tk.WORD,
                    font=self.default_font,
                    height=5,
                    relief=tk.SUNKEN,
                    bd=1
                )
                content_text.insert(tk.END, feedback.get('content', ''))
                content_text.config(state=tk.DISABLED)
                content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                
                scrollbar = ttk.Scrollbar(
                    content_frame,
                    orient=tk.VERTICAL,
                    command=content_text.yview
                )
                scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                content_text.config(yscrollcommand=scrollbar.set)
                
                # 如果状态是pending或failed，显示重试按钮
                if feedback.get('status') in ['pending', 'failed']:
                    def retry_send(feedback_index=i):
                        threading.Thread(target=send_feedback_again, args=(filtered_feedbacks[feedback_index],)).start()
                    
                    retry_button = ttk.Button(
                        feedback_frame,
                        text="重试发送",
                        command=retry_send
                    )
                    retry_button.pack(side=tk.RIGHT, padx=5, pady=5)
        
        # 重新发送反馈
        def send_feedback_again(feedback_data):
            try:
                if not self.check_internet_connection():
                    messagebox.showerror("网络错误", "当前没有网络连接，请稍后再试。")
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
                    feedbacks, feedback_file = load_feedbacks()
                    # 查找并更新对应的反馈
                    for f in feedbacks:
                        if (f.get('timestamp') == feedback_data.get('timestamp') and 
                            f.get('content') == feedback_data.get('content')):
                            f['status'] = 'sent'
                            break
                    # 保存更新后的反馈列表
                    with open(feedback_file, 'w', encoding='utf-8') as f:
                        json.dump(feedbacks, f, ensure_ascii=False, indent=2)
                    # 刷新界面
                    feedback_window.after(0, lambda: refresh_all_tabs())
                    messagebox.showinfo("发送成功", "反馈已成功发送到服务器。")
                else:
                    # 更新为失败状态
                    feedbacks, feedback_file = load_feedbacks()
                    for f in feedbacks:
                        if (f.get('timestamp') == feedback_data.get('timestamp') and 
                            f.get('content') == feedback_data.get('content')):
                            f['status'] = 'failed'
                            break
                    with open(feedback_file, 'w', encoding='utf-8') as f:
                        json.dump(feedbacks, f, ensure_ascii=False, indent=2)
                    feedback_window.after(0, lambda: refresh_all_tabs())
                    messagebox.showerror("发送失败", "无法发送反馈到服务器，请稍后再试。")
            except Exception as e:
                logging.error(f"重试发送反馈时出错: {str(e)}")
                messagebox.showerror("错误", "操作过程中出现错误，请稍后再试。")
        
        # 刷新所有标签页
        def refresh_all_tabs():
            display_feedbacks(all_frame)
            display_feedbacks(pending_frame, 'pending')
            display_feedbacks(sent_frame, 'sent')
            display_feedbacks(failed_frame, 'failed')
        
        # 初始加载
        refresh_all_tabs()
        
        # 添加刷新按钮
        button_frame = ttk.Frame(feedback_window)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        refresh_button = ttk.Button(
            button_frame,
            text="刷新列表",
            command=refresh_all_tabs
        )
        refresh_button.pack(side=tk.LEFT, padx=5)
        
        # 添加说明标签
        ttk.Label(
            button_frame,
            text="提示: 您可以查看所有本地存储的反馈记录，并重新发送失败的反馈。",
            font=self.default_font
        ).pack(side=tk.LEFT, padx=10)

    
    def create_navigation_frame(self):
        """创建顶部导航框架，包含切换按钮"""
        # 创建带阴影效果的导航框架
        shadow_frame = ttk.Frame(self.root, style="Card.TFrame")
        shadow_frame.pack(fill=tk.X, padx=10, pady=10)
        
        nav_frame = ttk.Frame(shadow_frame)
        nav_frame.pack(fill=tk.X, padx=2, pady=2)
        
        # 创建FBA计算器按钮
        self.fba_button = ttk.Button(
            nav_frame, 
            text="FBA费用计算器", 
            command=lambda: self.show_page("fba"),
            style="Nav.TButton"
        )
        self.fba_button.pack(side=tk.LEFT, padx=10, pady=5)
        
        # 创建汇率计算器按钮
        self.currency_button = ttk.Button(
            nav_frame, 
            text="汇率转换器", 
            command=lambda: self.show_page("currency"),
            style="Nav.TButton"
        )
        self.currency_button.pack(side=tk.LEFT, padx=10, pady=5)
        
        # 创建重量转换器按钮
        self.weight_converter_button = ttk.Button(
            nav_frame, 
            text="重量转换器", 
            command=lambda: self.show_page("weight_converter"),
            style="Nav.TButton"
        )
        self.weight_converter_button.pack(side=tk.LEFT, padx=10, pady=5)
        
        # 开发者模式：添加上传更新按钮
        if self.is_developer_mode():
            self.upload_update_button = ttk.Button(
                nav_frame, 
                text="上传更新", 
                command=self.upload_update,
                style="Nav.TButton"
            )
            self.upload_update_button.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # 添加设置按钮
        self.settings_button = ttk.Button(
            nav_frame, 
            text="设置", 
            command=self.show_settings_dialog,
            style="Nav.TButton"
        )
        self.settings_button.pack(side=tk.RIGHT, padx=10, pady=5)
            
        # 添加更新检查按钮
        self.update_button = ttk.Button(
            nav_frame, 
            text="检查更新", 
            command=self.check_for_updates,
            style="Nav.TButton"
        )
        self.update_button.pack(side=tk.RIGHT, padx=10, pady=5)
    
    def show_page(self, page_name):
        """显示指定页面，隐藏其他页面"""
        # 首先隐藏所有页面
        self.fba_frame.pack_forget()
        self.currency_frame.pack_forget()
        self.weight_converter_frame.pack_forget()
        
        # 重置所有导航按钮状态
        for button in [self.fba_button, self.currency_button, self.weight_converter_button]:
            button.config(state=tk.NORMAL)
        
        # 根据页面名称显示相应的框架
        if page_name == "fba":
            self.fba_frame.pack(fill=tk.BOTH, expand=True)
            self.fba_button.config(state=tk.DISABLED)  # 高亮当前页面按钮
        elif page_name == "currency":
            self.currency_frame.pack(fill=tk.BOTH, expand=True)
            self.currency_button.config(state=tk.DISABLED)  # 高亮当前页面按钮
            # 切换到汇率页面时获取最新汇率
            self.fetch_exchange_rates()
        elif page_name == "weight_converter":
            self.weight_converter_frame.pack(fill=tk.BOTH, expand=True)
            self.weight_converter_button.config(state=tk.DISABLED)  # 高亮当前页面按钮
        else:
            self.fba_frame.pack_forget()
            self.currency_frame.pack(fill=tk.BOTH, expand=True)
            self.currency_button.config(state=tk.DISABLED)
            # 显示汇率页面时尝试获取实时汇率
            self.fetch_exchange_rates()
        
        self.current_page = page_name
        
        # 更新状态栏
        if hasattr(self, 'status_var'):
            page_names = {
                "fba": "FBA费用计算器",
                "currency": "汇率转换器",
                "weight_converter": "重量转换器"
            }
            self.status_var.set(f"当前页面: {page_names.get(page_name, '未知页面')}")
    
    def apply_theme(self):
        # 应用颜色主题
        try:
            # 添加缺失的颜色键
            if "button_active" not in self.color_theme:
                self.color_theme["button_active"] = self.color_theme["button_bg"]
            if "button_pressed" not in self.color_theme:
                self.color_theme["button_pressed"] = self.color_theme["button_bg"]
            if "border_color" not in self.color_theme:
                self.color_theme["border_color"] = "#bdc3c7"
            
            # 为ttk组件设置样式，不直接使用bg选项
            self.style.configure("TFrame", background=self.color_theme["frame_bg"])
            self.style.configure("TLabel", foreground=self.color_theme["text_fg"], background=self.color_theme["frame_bg"])
            self.style.configure("TLabelframe", background=self.color_theme["frame_bg"], bordercolor=self.color_theme["border_color"], relief="raised")
            self.style.configure("TLabelframe.Label", background=self.color_theme["frame_bg"], foreground=self.color_theme["text_fg"])
            
            # 更新按钮样式
            self.style.configure("Accent.TButton", foreground=self.color_theme["text_fg"])
            self.style.map(
                "Accent.TButton",
                background=[
                    ('active', self.color_theme["button_active"]),
                    ('pressed', self.color_theme["button_pressed"]),
                    ('!disabled', self.color_theme["button_bg"])
                ]
            )
            
            # 更新导航按钮样式
            self.style.configure("Nav.TButton", foreground=self.color_theme["text_fg"])
            self.style.map(
                "Nav.TButton",
                background=[
                    ('active', self.color_theme.get("header_bg", self.color_theme["button_active"])),
                    ('pressed', self.color_theme.get("header_bg", self.color_theme["button_active"])),
                    ('!disabled', self.color_theme.get("highlight_bg", self.color_theme["button_bg"]))
                ]
            )
            
            # 更新输入框样式
            self.style.configure("Custom.TEntry", foreground=self.color_theme["text_fg"])
            
            # 更新根窗口背景（根窗口可以使用bg选项）
            self.root.configure(bg=self.color_theme["background"])
            
            # 更新分段显示颜色
            if hasattr(self, 'segment_display') and hasattr(self, 'size_segment'):
                segment_bg = self.color_theme["segment_bg"] if self.size_segment.startswith("超大") else self.color_theme["frame_bg"]
                segment_fg = "#922b21" if self.size_segment.startswith("超大") else "#1a5276"
                self.segment_display.configure(background=segment_bg, foreground=segment_fg)
                
        except Exception as e:
            # 异常处理，确保程序不会因为主题应用错误而崩溃
            logging.error(f"应用主题时出错: {str(e)}")
            pass
    
    def create_currency_converter_ui(self):
        """创建汇率转换器界面"""
        # 页面标题
        title_label = ttk.Label(
            self.currency_frame, 
            text="汇率转换器", 
            font=self.title_font
        )
        title_label.pack(pady=10)
        
        # 创建主内容区域，分为左侧转换区和右侧汇率信息区
        main_area = ttk.Frame(self.currency_frame)
        main_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧转换区域
        convert_frame = ttk.LabelFrame(main_area, text="货币转换")
        convert_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 金额输入
        input_frame = ttk.Frame(convert_frame)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(input_frame, text="金额:").pack(side=tk.LEFT, padx=5)
        self.amount_var = tk.StringVar(value="100")
        amount_entry = ttk.Entry(input_frame, textvariable=self.amount_var, width=15)
        amount_entry.pack(side=tk.LEFT, padx=5)
        
        # 货币选择
        currency_frame = ttk.Frame(convert_frame)
        currency_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(currency_frame, text="从:").pack(side=tk.LEFT, padx=5)
        self.from_currency = tk.StringVar(value="CNY")
        from_currency_combo = ttk.Combobox(currency_frame, textvariable=self.from_currency, values=["CNY", "USD", "EUR"], width=10)
        from_currency_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(currency_frame, text="到:").pack(side=tk.LEFT, padx=5)
        self.to_currency = tk.StringVar(value="USD")
        to_currency_combo = ttk.Combobox(currency_frame, textvariable=self.to_currency, values=["CNY", "USD", "EUR"], width=10)
        to_currency_combo.pack(side=tk.LEFT, padx=5)
        
        # 转换按钮
        convert_button = ttk.Button(convert_frame, text="转换", command=self.convert_currency)
        convert_button.pack(pady=10)
        
        # 转换结果
        result_frame = ttk.Frame(convert_frame)
        result_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(result_frame, text="转换结果:").pack(anchor=tk.W, pady=5)
        self.conversion_result_var = tk.StringVar(value="请点击转换按钮")
        result_label = ttk.Label(result_frame, textvariable=self.conversion_result_var, font=self.header_font)
        result_label.pack(anchor=tk.W, pady=5)
        
        # 右侧汇率信息区域
        rates_frame = ttk.LabelFrame(main_area, text="当前汇率 (更新时间: 未知)")
        rates_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 保存rates_frame引用，以便后续更新标题
        self.rates_frame = rates_frame
        
        # 汇率信息文本框
        self.rates_text = tk.Text(rates_frame, height=10, width=30, wrap=tk.WORD, state=tk.DISABLED)
        self.rates_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 刷新汇率按钮
        refresh_button = ttk.Button(rates_frame, text="刷新汇率", command=self.fetch_exchange_rates)
        refresh_button.pack(pady=10)
        
        # 存储汇率数据
        self.exchange_rates = {
            "CNY": {"USD": 0.138, "EUR": 0.129},
            "USD": {"CNY": 7.246, "EUR": 0.933},
            "EUR": {"CNY": 7.752, "USD": 1.072}
        }
        self.last_update_time = "未知"
        
    def create_weight_converter_ui(self):
        """创建独立的重量转换工具界面"""
        # 获取重量转换器框架
        frame = self.weight_converter_frame
        
        # 创建标题
        title_label = ttk.Label(
            frame, 
            text="重量单位转换器", 
            font=self.title_font
        )
        title_label.pack(pady=20)
        
        # 创建输入框架
        input_frame = ttk.LabelFrame(frame, text="转换设置", padding="20")
        input_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # 输入值
        value_frame = ttk.Frame(input_frame)
        value_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(value_frame, text="输入值:", width=10).pack(side=tk.LEFT, padx=5)
        
        self.weight_input_var = tk.StringVar(value="1")
        self.weight_input_entry = ttk.Entry(
            value_frame, 
            textvariable=self.weight_input_var, 
            width=15,
            justify=tk.RIGHT
        )
        self.weight_input_entry.pack(side=tk.LEFT, padx=5)
        
        # 源单位选择
        from_unit_frame = ttk.Frame(input_frame)
        from_unit_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(from_unit_frame, text="从单位:", width=10).pack(side=tk.LEFT, padx=5)
        
        self.from_unit_var = tk.StringVar(value="磅")
        units_frame = ttk.Frame(from_unit_frame)
        units_frame.pack(side=tk.LEFT)
        
        units = ["磅 (lb)", "盎司 (oz)"]
        unit_values = ["磅", "盎司"]
        
        for text, value in zip(units, unit_values):
            ttk.Radiobutton(
                units_frame, 
                text=text, 
                variable=self.from_unit_var, 
                value=value
            ).pack(side=tk.LEFT, padx=10)
        
        # 目标单位选择
        to_unit_frame = ttk.Frame(input_frame)
        to_unit_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(to_unit_frame, text="到单位:", width=10).pack(side=tk.LEFT, padx=5)
        
        self.to_unit_var = tk.StringVar(value="千克")
        to_units_frame = ttk.Frame(to_unit_frame)
        to_units_frame.pack(side=tk.LEFT)
        
        for text, value in zip(units, unit_values):
            ttk.Radiobutton(
                to_units_frame, 
                text=text, 
                variable=self.to_unit_var, 
                value=value
            ).pack(side=tk.LEFT, padx=10)
        
        # 转换按钮
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=20)
        
        self.convert_button = ttk.Button(
            button_frame, 
            text="转换重量", 
            command=self.convert_weight
        )
        self.convert_button.pack(padx=10)
        
        # 结果显示
        result_frame = ttk.LabelFrame(frame, text="转换结果", padding="20")
        result_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # 创建结果标签
        self.weight_result_var = tk.StringVar(value="请点击转换按钮")
        self.weight_result_label = ttk.Label(
            result_frame, 
            textvariable=self.weight_result_var,
            font=self.header_font,
            wraplength=600
        )
        self.weight_result_label.pack(pady=10)
        
        # 添加转换信息区域
        info_frame = ttk.LabelFrame(frame, text="转换信息", padding="20")
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        info_text = """
        常用重量单位转换关系：
        • 1 磅 = 16 盎司 = 453.59237 克 = 0.45359237 千克
        • 1 盎司 = 28.349523125 克
        • 1 千克 = 1000 克 = 35.2739619 盎司 = 2.20462262 磅
        """
        
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack(anchor=tk.W)
    
    def convert_weight(self):
        """执行重量单位转换计算"""
        try:
            # 获取输入值和单位
            input_value = float(self.weight_input_var.get())
            from_unit = self.from_unit_var.get()
            to_unit = self.to_unit_var.get()
            
            # 如果单位相同，直接显示结果
            if from_unit == to_unit:
                self.weight_result_var.set(f"{input_value} {from_unit} = {input_value} {to_unit}")
                return
            
            # 首先将所有单位转换为克进行中间计算
            if from_unit == "磅":
                weight_in_grams = input_value * 453.59237
            elif from_unit == "盎司":
                weight_in_grams = input_value * 28.349523125
            elif from_unit == "克":
                weight_in_grams = input_value
            elif from_unit == "千克":
                weight_in_grams = input_value * 1000
            else:
                weight_in_grams = input_value  # 默认不转换
            
            # 然后将克转换为目标单位
            if to_unit == "磅":
                converted_weight = weight_in_grams / 453.59237
            elif to_unit == "盎司":
                converted_weight = weight_in_grams / 28.349523125
            elif to_unit == "克":
                converted_weight = weight_in_grams
            elif to_unit == "千克":
                converted_weight = weight_in_grams / 1000
            else:
                converted_weight = weight_in_grams  # 默认不转换
            
            # 根据单位决定保留的小数位数
            if to_unit in ["磅", "千克"]:
                result_str = f"{converted_weight:.6f}"
            elif to_unit == "盎司":
                result_str = f"{converted_weight:.4f}"
            else:  # 克
                result_str = f"{converted_weight:.2f}"
            
            # 去除末尾多余的零和小数点
            result_str = result_str.rstrip('0').rstrip('.') if '.' in result_str else result_str
            
            # 更新结果显示
            self.weight_result_var.set(f"{input_value} {from_unit} = {result_str} {to_unit}")
            
        except ValueError:
            self.weight_result_var.set("错误：请输入有效的数字")
        except Exception as e:
            self.weight_result_var.set(f"转换错误：{str(e)}")
    
    def fetch_exchange_rates(self):
        """获取实时汇率数据"""
        try:
            # 由于我们不能使用实际的API密钥，这里使用模拟数据
            # 在实际应用中，应该使用真实的汇率API
            import random
            
            # 模拟从API获取数据的延迟
            import time
            time.sleep(0.5)
            
            # 模拟实时汇率数据，在基础汇率上添加小波动
            base_rates = {
                "CNY": {"USD": 0.138, "EUR": 0.129},
                "USD": {"CNY": 7.246, "EUR": 0.933},
                "EUR": {"CNY": 7.752, "USD": 1.072}
            }
            
            # 添加±2%的随机波动以模拟实时变化
            self.exchange_rates = {}
            for from_curr, to_rates in base_rates.items():
                self.exchange_rates[from_curr] = {}
                for to_curr, rate in to_rates.items():
                    # 添加±2%的随机波动
                    fluctuation = random.uniform(0.98, 1.02)
                    self.exchange_rates[from_curr][to_curr] = round(rate * fluctuation, 4)
            
            # 更新时间
            self.last_update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 更新界面显示
            self.update_rates_display()
            
        except Exception as e:
            logging.error(f"获取汇率数据时出错: {str(e)}")
            messagebox.showerror("错误", "无法获取实时汇率数据，请稍后再试。")
    
    def update_rates_display(self):
        """更新汇率信息显示"""
        # 更新框架标题
        self.rates_frame.config(text=f"当前汇率 (更新时间: {self.last_update_time})")
        
        # 更新汇率文本框
        self.rates_text.config(state=tk.NORMAL)
        self.rates_text.delete(1.0, tk.END)
        
        rates_info = []
        rates_info.append("主要货币汇率:")
        rates_info.append("")
        
        # 添加人民币兑其他货币汇率
        rates_info.append(f"1 CNY = {self.exchange_rates['CNY']['USD']:.4f} USD")
        rates_info.append(f"1 CNY = {self.exchange_rates['CNY']['EUR']:.4f} EUR")
        rates_info.append("")
        
        # 添加美元兑其他货币汇率
        rates_info.append(f"1 USD = {self.exchange_rates['USD']['CNY']:.4f} CNY")
        rates_info.append(f"1 USD = {self.exchange_rates['USD']['EUR']:.4f} EUR")
        rates_info.append("")
        
        # 添加欧元兑其他货币汇率
        rates_info.append(f"1 EUR = {self.exchange_rates['EUR']['CNY']:.4f} CNY")
        rates_info.append(f"1 EUR = {self.exchange_rates['EUR']['USD']:.4f} USD")
        
        # 添加到文本框
        self.rates_text.insert(tk.END, "\n".join(rates_info))
        self.rates_text.config(state=tk.DISABLED)
    
    def convert_currency(self):
        """执行货币转换计算"""
        try:
            # 获取输入金额
            amount = float(self.amount_var.get())
            if amount <= 0:
                raise ValueError("金额必须大于0")
            
            # 获取货币类型
            from_curr = self.from_currency.get()
            to_curr = self.to_currency.get()
            
            # 如果货币相同，直接显示结果
            if from_curr == to_curr:
                result = f"{amount:.2f} {from_curr} = {amount:.2f} {to_curr}"
            else:
                # 获取汇率并计算
                rate = self.exchange_rates[from_curr][to_curr]
                converted_amount = amount * rate
                result = f"{amount:.2f} {from_curr} = {converted_amount:.2f} {to_curr} (汇率: 1 {from_curr} = {rate:.4f} {to_curr})"
            
            # 更新结果显示
            self.conversion_result_var.set(result)
            
        except ValueError as ve:
            messagebox.showerror("输入错误", f"请输入有效的金额: {str(ve)}")
        except Exception as e:
            logging.error(f"货币转换时出错: {str(e)}")
            messagebox.showerror("错误", "货币转换过程中出现错误，请重试。")
    
    def create_title(self):
        title_frame = ttk.Frame(self.container)
        title_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = ttk.Label(
            title_frame, 
            text="FBA配送费计算器", 
            font=self.title_font
        )
        title_label.pack(anchor=tk.CENTER)
    
    def create_site_selector(self):
        # 创建站点选择器框架
        site_frame = ttk.Frame(self.container)
        site_frame.pack(pady=10, fill=tk.X)
        
        # 添加站点选择标签
        ttk.Label(site_frame, text="选择站点：", font=self.default_font).pack(side=tk.LEFT, padx=10)
        
        # 创建站点选择按钮
        self.us_button = ttk.Button(
            site_frame,
            text="美国站",
            command=lambda: self.switch_site("us"),
            style="Accent.TButton" if self.site_var.get() == "us" else "TButton"
        )
        self.us_button.pack(side=tk.LEFT, padx=5)
        
        self.jp_button = ttk.Button(
            site_frame,
            text="日本站",
            command=lambda: self.switch_site("jp"),
            style="Accent.TButton" if self.site_var.get() == "jp" else "TButton"
        )
        self.jp_button.pack(side=tk.LEFT, padx=5)
    
    def switch_site(self, site):
        # 更新站点选择变量
        self.site_var.set(site)
        
        # 更新按钮样式，高亮当前选中的站点
        self.us_button.config(style="Accent.TButton" if site == "us" else "TButton")
        self.jp_button.config(style="Accent.TButton" if site == "jp" else "TButton")
        
        # 清空结果区域
        self.result_text.delete(1.0, tk.END)
        
        # 保存当前值以便单位转换
        current_values = {}
        if hasattr(self, 'max_len_var') and self.max_len_var.get():
            try:
                current_values['max_len'] = float(self.max_len_var.get())
                current_values['mid_len'] = float(self.mid_len_var.get()) if hasattr(self, 'mid_len_var') and self.mid_len_var.get() else 0
                current_values['min_len'] = float(self.min_len_var.get()) if hasattr(self, 'min_len_var') and self.min_len_var.get() else 0
            except ValueError:
                pass
        
        if hasattr(self, 'weight_var') and self.weight_var.get():
            try:
                current_values['weight'] = float(self.weight_var.get())
            except ValueError:
                pass
        
        # 更新尺寸输入框架的标题和单位
        if site == "us":
            # 美国站设置
            if hasattr(self, 'size_frame'):
                self.size_frame.config(text="商品尺寸（英寸）")
            if hasattr(self, 'weight_frame'):
                self.weight_frame.config(text="商品重量（磅/盎司）")
            
            # 转换单位：厘米 -> 英寸，克 -> 磅
            if 'max_len' in current_values and self.current_site == "jp":
                # 厘米转英寸 (1厘米 = 0.3937英寸)
                self.max_len_var.set(round(current_values['max_len'] * 0.3937, 2))
                self.mid_len_var.set(round(current_values['mid_len'] * 0.3937, 2))
                self.min_len_var.set(round(current_values['min_len'] * 0.3937, 2))
            
            if 'weight' in current_values and self.current_site == "jp":
                # 克转磅 (1克 = 0.00220462磅)
                self.weight_var.set(round(current_values['weight'] * 0.00220462, 2))
            
            # 显示美国站特有的输入框
            if hasattr(self, 'weight_oz_entry'):
                self.weight_oz_entry.grid(row=0, column=2, padx=5)
            if hasattr(self, 'weight_oz_label'):
                self.weight_oz_label.grid(row=0, column=3, padx=5)
            
            # 显示重量单位选择行
            if hasattr(self, 'weight_frame') and hasattr(self.weight_frame, 'children'):
                for child in self.weight_frame.winfo_children():
                    if isinstance(child, ttk.Frame) and child.winfo_children():
                        # 检查第一个子元素是否是单位标签
                        first_child = child.winfo_children()[0]
                        if isinstance(first_child, ttk.Label) and first_child.cget('text') == "重量单位:":
                            child.pack(fill=tk.X, pady=(0, 10))
                            break
            
            # 更新尺寸分段框架标题
            if hasattr(self, 'segment_frame'):
                self.segment_frame.config(text="商品尺寸分段")
            
            # 显示切换提示
            self.result_text.insert(tk.END, "已切换到美国站计算模式\n")
        else:
            # 日本站设置
            if hasattr(self, 'size_frame'):
                self.size_frame.config(text="商品尺寸（厘米）")
            if hasattr(self, 'weight_frame'):
                self.weight_frame.config(text="商品重量（克）")
            
            # 转换单位：英寸 -> 厘米，磅 -> 克
            if 'max_len' in current_values and self.current_site == "us":
                # 英寸转厘米 (1英寸 = 2.54厘米)
                self.max_len_var.set(round(current_values['max_len'] * 2.54, 2))
                self.mid_len_var.set(round(current_values['mid_len'] * 2.54, 2))
                self.min_len_var.set(round(current_values['min_len'] * 2.54, 2))
            
            if 'weight' in current_values and self.current_site == "us":
                # 磅转克 (1磅 = 453.592克)
                self.weight_var.set(round(current_values['weight'] * 453.592, 2))
            
            # 隐藏美国站特有的输入框
            if hasattr(self, 'weight_oz_entry'):
                self.weight_oz_entry.grid_remove()
            if hasattr(self, 'weight_oz_label'):
                self.weight_oz_label.grid_remove()
            
            # 隐藏重量单位选择行
            if hasattr(self, 'weight_frame') and hasattr(self.weight_frame, 'children'):
                for child in self.weight_frame.winfo_children():
                    if isinstance(child, ttk.Frame) and child.winfo_children():
                        # 检查第一个子元素是否是单位标签
                        first_child = child.winfo_children()[0]
                        if isinstance(first_child, ttk.Label) and first_child.cget('text') == "重量单位:":
                            child.pack_forget()
                            break
            
            # 更新尺寸分段框架标题
            if hasattr(self, 'segment_frame'):
                self.segment_frame.config(text="商品尺寸分段 (最长边)")
            
            # 清空尺寸分段显示
            if hasattr(self, 'segment_display_var'):
                self.segment_display_var.set("请输入商品尺寸和重量")
            
            # 显示日本站特有的输入框
            if hasattr(self, 'price_over_1000_check'):
                # 使用pack布局而不是grid，保持与容器一致
                self.price_over_1000_check.pack(pady=5, anchor=tk.W)
            else:
                # 创建价格超过1000日元的复选框
                self.price_over_1000_var = tk.BooleanVar(value=True)
                self.price_over_1000_check = ttk.Checkbutton(
                    self.weight_frame,
                    text="价格超过1000日元",
                    variable=self.price_over_1000_var
                )
                # 使用pack布局
                self.price_over_1000_check.pack(pady=5, anchor=tk.W)
            
            # 添加冷冻商品复选框
            if hasattr(self, 'is_frozen_check'):
                self.is_frozen_check.pack(pady=5, anchor=tk.W)
            else:
                self.is_frozen_var = tk.BooleanVar(value=False)
                self.is_frozen_check = ttk.Checkbutton(
                    self.weight_frame,
                    text="冷冻商品",
                    variable=self.is_frozen_var
                )
                self.is_frozen_check.pack(pady=5, anchor=tk.W)
            # 显示切换提示
            self.result_text.insert(tk.END, "已切换到日本站计算模式\n")
        
        # 更新单位标签（在所有站点设置之后执行，确保标签已经创建）
        # 更新尺寸单位标签
        if hasattr(self, 'size_unit_labels') and self.size_unit_labels:
            target_unit = "英寸" if site == "us" else "厘米"
            for label in self.size_unit_labels:
                # 强制设置正确的单位标签文本
                label.config(text=target_unit)
                # 记录日志以便调试
                print(f"更新尺寸单位标签 -> {target_unit}")
        
        # 更新重量单位标签
        if hasattr(self, 'weight_unit_label'):
            target_weight_unit = "磅" if site == "us" else "克"
            self.weight_unit_label.config(text=target_weight_unit)
            # 记录日志以便调试
            print(f"更新重量单位标签: {target_weight_unit}")
        
        # 确保框架标题也正确更新
        if hasattr(self, 'size_frame'):
            size_frame_title = "商品尺寸（英寸）" if site == "us" else "商品尺寸（厘米）"
            self.size_frame.config(text=size_frame_title)
        
        if hasattr(self, 'weight_frame'):
            weight_frame_title = "商品重量（磅/盎司）" if site == "us" else "商品重量（克）"
            self.weight_frame.config(text=weight_frame_title)
        
        # 更新当前站点
        self.current_site = site
        
        # 提示用户注意单位变化
        self.result_text.insert(tk.END, f"当前单位：{'英寸/磅' if site == 'us' else '厘米/克'}")
        
        # 移除对不存在的reset_inputs方法的调用
        pass
    
    def create_size_inputs(self):
        # 根据当前站点设置初始尺寸单位和框架文本
        default_size_unit = "英寸"
        frame_text = "商品尺寸（英寸）"
        
        if hasattr(self, 'current_site') and self.current_site == "jp":
            default_size_unit = "厘米"
            frame_text = "商品尺寸（厘米）"
        
        # 尺寸输入框架
        size_frame = ttk.LabelFrame(self.container, text=frame_text, padding="15")
        size_frame.pack(fill=tk.X, pady=(0, 15))
        self.size_frame = size_frame
        
        # 尺寸变量
        self.max_len_var = tk.StringVar()
        self.mid_len_var = tk.StringVar()
        self.min_len_var = tk.StringVar()
        
        # 存储尺寸单位标签引用
        self.size_unit_labels = []
        
        # 根据当前站点直接创建正确单位的输入行
        if hasattr(self, 'current_site'):
            if self.current_site == "jp":
                # 日本站：使用厘米单位
                max_len_label = self.create_input_row(size_frame, "最长边:", self.max_len_var, default_unit="厘米")
                mid_len_label = self.create_input_row(size_frame, "次长边:", self.mid_len_var, default_unit="厘米")
                min_len_label = self.create_input_row(size_frame, "最短边:", self.min_len_var, default_unit="厘米")
                # 立即设置正确的单位标签文本
                max_len_label.config(text="厘米")
                mid_len_label.config(text="厘米")
                min_len_label.config(text="厘米")
            else:
                # 美国站：使用英寸单位
                max_len_label = self.create_input_row(size_frame, "最长边:", self.max_len_var, default_unit="英寸")
                mid_len_label = self.create_input_row(size_frame, "次长边:", self.mid_len_var, default_unit="英寸")
                min_len_label = self.create_input_row(size_frame, "最短边:", self.min_len_var, default_unit="英寸")
                # 立即设置正确的单位标签文本
                max_len_label.config(text="英寸")
                mid_len_label.config(text="英寸")
                min_len_label.config(text="英寸")
        else:
            # 默认情况：使用默认单位
            max_len_label = self.create_input_row(size_frame, "最长边:", self.max_len_var, default_unit=default_size_unit)
            mid_len_label = self.create_input_row(size_frame, "次长边:", self.mid_len_var, default_unit=default_size_unit)
            min_len_label = self.create_input_row(size_frame, "最短边:", self.min_len_var, default_unit=default_size_unit)
            # 设置默认单位标签文本
            max_len_label.config(text=default_size_unit)
            mid_len_label.config(text=default_size_unit)
            min_len_label.config(text=default_size_unit)
        
        # 保存单位标签引用以便后续更新
        self.size_unit_labels.append(max_len_label)
        self.size_unit_labels.append(mid_len_label)
        self.size_unit_labels.append(min_len_label)
    
    def create_input_row(self, parent, label_text, var, default_unit="英寸"):
        row = ttk.Frame(parent)
        row.pack(fill=tk.X, pady=5)
        
        label = ttk.Label(row, text=label_text, width=15, anchor=tk.W)
        label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 创建带有焦点效果的输入框
        entry = ttk.Entry(row, textvariable=var, width=20, font=self.default_font, style="Custom.TEntry")
        entry.pack(side=tk.LEFT, padx=(0, 5))
        
        # 为输入框添加焦点和失焦效果
        def on_focus(event):
            entry.config(foreground="#2c3e50")
        
        def on_focusout(event):
            entry.config(foreground="#000000")
        
        entry.bind("<FocusIn>", on_focus)
        entry.bind("<FocusOut>", on_focusout)
        
        # 绑定输入事件，实时更新尺寸分段
        entry.bind("<KeyRelease>", lambda event: self.update_size_segment())
        
        # 直接使用传入的default_unit作为显示文本，不进行映射
        # 这样可以确保create_size_inputs和create_weight_inputs方法中设置的单位能直接显示
        unit_label = ttk.Label(row, text=default_unit)
        unit_label.pack(side=tk.LEFT)
        
        # 记录日志以便调试
        print(f"创建输入行，单位: {default_unit}")
        
        return unit_label
        
    def create_status_bar(self):
        """创建底部状态栏"""
        self.status_var = tk.StringVar(value="就绪")
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        
        # 版本信息
        version_label = ttk.Label(
            status_frame,
            text=f"版本: {self.VERSION}",
            font=self.default_font,
            anchor=tk.W
        )
        version_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # 左侧状态栏信息
        status_label = ttk.Label(
            status_frame, 
            textvariable=self.status_var,
            font=self.default_font,
            anchor=tk.W
        )
        status_label.pack(side=tk.LEFT, padx=10, pady=5, fill=tk.X, expand=True)
        
        # 上次更新检查时间
        self.last_update_check_var = tk.StringVar(value="")
        update_check_label = ttk.Label(
            status_frame,
            textvariable=self.last_update_check_var,
            font=self.default_font,
            anchor=tk.E
        )
        update_check_label.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # 右侧显示当前时间
        self.time_var = tk.StringVar()
        time_label = ttk.Label(
            status_frame,
            textvariable=self.time_var,
            font=self.default_font,
            anchor=tk.E
        )
        time_label.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # 更新时间
        self.update_time()
        
    def update_time(self):
        """更新状态栏时间"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.time_var.set(current_time)
        self.root.after(1000, self.update_time)  # 每秒更新一次
    
    def check_for_updates_in_background(self):
        """在后台线程中检查更新，避免阻塞UI"""
        def update_check():
            try:
                self.check_for_updates(show_no_update_msg=False)
            except Exception as e:
                logging.error(f"后台检查更新失败: {str(e)}")
        
        # 创建并启动后台线程
        thread = threading.Thread(target=update_check)
        thread.daemon = True
        thread.start()
    
    def check_for_updates(self, show_no_update_msg=True):
        """检查是否有新版本可用"""
        try:
            # 更新状态栏
            self.root.after(0, lambda: self.status_var.set("正在检查更新..."))
            
            # 这里是模拟检查更新，实际使用时应该从服务器获取
            update_info = self.get_latest_version_info()
            
            if update_info:
                latest_version = update_info.get("version", "0.0.0")
                download_url = update_info.get("download_url", "")
                release_notes = update_info.get("release_notes", "")
                
                # 更新检查时间
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
                self.root.after(0, lambda: self.last_update_check_var.set(f"上次检查更新: {current_time}"))
                
                # 比较版本号
                if self.is_newer_version(latest_version, self.VERSION):
                    # 显示更新提示对话框
                    self.root.after(0, lambda: self.show_update_dialog(latest_version, download_url, release_notes))
                elif show_no_update_msg:
                    self.root.after(0, lambda: messagebox.showinfo("检查更新", f"当前已是最新版本 v{self.VERSION}"))
            
        except Exception as e:
            logging.error(f"检查更新时出错: {str(e)}")
            if show_no_update_msg:
                self.root.after(0, lambda: messagebox.showerror("更新检查失败", "无法连接到更新服务器，请稍后再试。"))
        finally:
            self.root.after(0, lambda: self.status_var.set("就绪"))
    
    def get_latest_version_info(self):
        """获取最新版本信息，优化为优先使用本地服务器，增加多重备用方案"""
        # 定义域名配置 - 统一使用tomarens.xyz
        DOMAIN = "tomarens.xyz"
        
        # 首先尝试从本地更新信息文件获取
        update_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.UPDATE_INFO_FILE)
        if os.path.exists(update_file):
            try:
                with open(update_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logging.error(f"读取本地更新信息文件失败: {str(e)}")
        
        # 然后尝试从远程服务器获取，使用多域名尝试
        try:
            if self.check_internet_connection():
                import urllib.request
                import urllib.error
                
                # 尝试多个域名和协议
                domains = [
                    f"http://{DOMAIN}:8081",  # 本地服务器配置
                    f"https://{DOMAIN}",      # HTTPS
                    f"http://{DOMAIN}",       # HTTP
                ]
                
                for domain in domains:
                    try:
                        remote_url = f"{domain}/{self.UPDATE_INFO_FILE}"
                        with urllib.request.urlopen(remote_url, timeout=8) as response:
                            if response.status == 200:
                                data = response.read().decode('utf-8')
                                return json.loads(data)
                    except Exception as inner_e:
                        logging.warning(f"从 {domain} 获取更新信息失败: {str(inner_e)}")
                        continue  # 尝试下一个域名
        except Exception as e:
            logging.error(f"远程更新检查失败: {str(e)}")
        
        # 如果都失败了，返回默认数据，使用统一域名
        return {
            "version": self.VERSION,
            "download_url": f"http://{DOMAIN}:8081/downloads/FBA费用计算器.exe",
            "release_notes": "暂无更新信息"
        }
    
    def is_newer_version(self, latest, current):
        """比较版本号，判断是否有新版本"""
        try:
            latest_parts = [int(part) for part in latest.split(".")]
            current_parts = [int(part) for part in current.split(".")]
            
            # 比较每个版本部分
            for i in range(min(len(latest_parts), len(current_parts))):
                if latest_parts[i] > current_parts[i]:
                    return True
                elif latest_parts[i] < current_parts[i]:
                    return False
            
            # 如果前面的部分都相同，检查长度
            return len(latest_parts) > len(current_parts)
        except:
            return False
    
    def show_update_dialog(self, latest_version, download_url, release_notes):
        """显示更新提示对话框"""
        update_window = tk.Toplevel(self.root)
        update_window.title("发现新版本")
        update_window.geometry("500x400")  # 增加窗口高度以确保按钮完全显示
        update_window.resizable(False, False)
        update_window.configure(bg=self.color_theme["background"])
        
        # 设置窗口在屏幕中心
        update_window.update_idletasks()
        width = update_window.winfo_width()
        height = update_window.winfo_height()
        x = (update_window.winfo_screenwidth() // 2) - (width // 2)
        y = (update_window.winfo_screenheight() // 2) - (height // 2)
        update_window.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
        # 创建框架
        content_frame = ttk.Frame(update_window, style="TFrame")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 标题标签
        title_label = ttk.Label(
            content_frame,
            text=f"发现新版本 v{latest_version}",
            font=(self.header_font[0], 16, "bold"),
            style="TLabel"
        )
        title_label.pack(pady=10)
        
        # 当前版本信息
        current_label = ttk.Label(
            content_frame,
            text=f"当前版本: v{self.VERSION}",
            style="TLabel"
        )
        current_label.pack(pady=5)
        
        # 更新内容
        notes_label = ttk.Label(
            content_frame,
            text="更新内容:",
            style="TLabel"
        )
        notes_label.pack(pady=5, anchor="w")
        
        notes_text = tk.Text(
            content_frame,
            height=8,
            width=50,
            font=self.default_font,
            wrap=tk.WORD,
            state=tk.DISABLED,
            bg=self.color_theme["frame_bg"],
            fg=self.color_theme["text_fg"]
        )
        notes_text.pack(pady=5, fill=tk.BOTH, expand=True)
        notes_text.configure(state=tk.NORMAL)
        notes_text.insert(tk.END, release_notes)
        notes_text.configure(state=tk.DISABLED)
        
        # 按钮框架
        button_frame = ttk.Frame(content_frame, style="TFrame")
        button_frame.pack(fill=tk.X, pady=10)
        
        # 立即更新按钮
        update_button = ttk.Button(
            button_frame,
            text="立即更新",
            style="Accent.TButton",
            command=lambda: [update_window.destroy(), self.download_update(download_url)]
        )
        update_button.pack(side=tk.LEFT, padx=5)
        
        # 稍后提醒按钮
        later_button = ttk.Button(
            button_frame,
            text="稍后提醒",
            style="TButton",
            command=update_window.destroy
        )
        later_button.pack(side=tk.RIGHT, padx=5)
    
    def upload_update(self):
        """自动上传更新到服务器"""
        try:
            self.status_var.set("准备上传更新...")
            
            # 获取当前程序文件路径和目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # 首先检查当前目录是否有可执行文件
            exe_files = [f for f in os.listdir(current_dir) if f.endswith(".exe") and "FBA费用计算器" in f]
            if exe_files:
                exe_path = os.path.join(current_dir, exe_files[0])
            else:
                # 然后检查dist目录
                dist_dir = os.path.join(current_dir, "dist")
                if os.path.exists(dist_dir):
                    exe_files = [f for f in os.listdir(dist_dir) if f.endswith(".exe")]
                    if exe_files:
                        exe_path = os.path.join(dist_dir, exe_files[0])
                    else:
                        messagebox.showerror("错误", "未找到可执行文件，请先构建应用程序。")
                        self.status_var.set("就绪")
                        return
                else:
                    # 如果是编译后的程序，使用当前可执行文件
                    if getattr(sys, 'frozen', False):
                        exe_path = sys.executable
                    else:
                        messagebox.showerror("错误", "未找到可执行文件，请先构建应用程序。")
                        self.status_var.set("就绪")
                        return
            
            # 提示用户输入新版本信息
            new_version_window = tk.Toplevel(self.root)
            new_version_window.title("上传更新")
            new_version_window.geometry("550x550")  # 增大窗口尺寸
            new_version_window.resizable(False, False)
            new_version_window.configure(bg=self.color_theme["background"])
            
            # 设置窗口在屏幕中心
            new_version_window.update_idletasks()
            width = new_version_window.winfo_width()
            height = new_version_window.winfo_height()
            x = (new_version_window.winfo_screenwidth() // 2) - (width // 2)
            y = (new_version_window.winfo_screenheight() // 2) - (height // 2)
            new_version_window.geometry('{}x{}+{}+{}'.format(width, height, x, y))
            
            # 创建框架
            content_frame = ttk.Frame(new_version_window, style="TFrame")
            content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            
            # 版本号输入
            version_frame = ttk.Frame(content_frame)
            version_frame.pack(fill=tk.X, pady=10)
            
            ttk.Label(version_frame, text="新版本号:", style="TLabel").pack(side=tk.LEFT, padx=5)
            version_var = tk.StringVar(value=self.VERSION)
            version_entry = ttk.Entry(version_frame, textvariable=version_var, width=20, style="Custom.TEntry")
            version_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            
            # 显示当前找到的可执行文件
            exe_label = ttk.Label(content_frame, text=f"将上传文件: {os.path.basename(exe_path)}", style="TLabel")
            exe_label.pack(anchor=tk.W, padx=5, pady=5)
            
            # 发布说明输入
            notes_frame = ttk.LabelFrame(content_frame, text="发布说明", padding="10")
            notes_frame.pack(fill=tk.BOTH, expand=True, pady=10)
            
            # 预设发布说明
            default_notes = "1. 调整了BUG反馈界面大小，提供更好的用户体验\n2. 添加了数据导出功能，支持Excel和CSV格式\n3. 添加了批量处理功能，可导入文件批量计算费用\n4. 修复了上传更新功能的问题\n5. 优化了用户界面体验"
            
            # 创建带有滚动条的文本框，确保可编辑
            notes_text = tk.Text(notes_frame, height=10, font=self.default_font, wrap=tk.WORD)
            # 添加垂直滚动条
            scrollbar = ttk.Scrollbar(notes_frame, command=notes_text.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            notes_text.config(yscrollcommand=scrollbar.set)
            # 确保文本框占据剩余空间
            notes_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            # 插入默认文本
            notes_text.insert(tk.END, default_notes)
            # 确保文本框是可编辑的（默认状态）
            notes_text.config(state=tk.NORMAL)
            
            # 按钮框架
            button_frame = ttk.Frame(content_frame)
            button_frame.pack(fill=tk.X, pady=10)
            
            # 上传进度变量
            progress_var = tk.DoubleVar()
            progress_bar = ttk.Progressbar(content_frame, variable=progress_var, maximum=100)
            progress_label = ttk.Label(content_frame, text="", style="TLabel")
            
            def do_upload():
                try:
                    new_version = version_var.get().strip()
                    if not new_version:
                        messagebox.showerror("错误", "请输入新版本号")
                        return
                    
                    release_notes = notes_text.get("1.0", tk.END).strip()
                    
                    # 更新状态栏
                    self.status_var.set("正在上传更新...")
                    
                    # 显示进度条
                    progress_label.pack(pady=5)
                    progress_bar.pack(fill=tk.X, pady=5)
                    new_version_window.update_idletasks()
                    
                    # 创建或确保必要的目录存在
                    downloads_dir = os.path.join(current_dir, "downloads")
                    if not os.path.exists(downloads_dir):
                        os.makedirs(downloads_dir)
                    
                    # 更新本地update_info.json文件
                    update_info = {
                        "version": new_version,
                        "download_url": f"https://tomarens.xyz/downloads/FBA费用计算器.exe",
                        "release_notes": release_notes,
                        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # 保存更新信息到多个位置以确保兼容性
                    update_file = os.path.join(current_dir, self.UPDATE_INFO_FILE)
                    with open(update_file, 'w', encoding='utf-8') as f:
                        json.dump(update_info, f, ensure_ascii=False, indent=4)
                    
                    # 同时保存到downloads目录
                    update_file_downloads = os.path.join(downloads_dir, self.UPDATE_INFO_FILE)
                    with open(update_file_downloads, 'w', encoding='utf-8') as f:
                        json.dump(update_info, f, ensure_ascii=False, indent=4)
                    
                    progress_var.set(40)
                    progress_label.config(text="已更新版本信息文件")
                    new_version_window.update_idletasks()
                    
                    # 复制文件到downloads目录
                    target_exe_path = os.path.join(downloads_dir, "FBA费用计算器.exe")
                    try:
                        # 确保目标目录可写
                        if not os.access(downloads_dir, os.W_OK):
                            # 尝试修改权限
                            import stat
                            os.chmod(downloads_dir, stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR | stat.S_IWGRP | stat.S_IRGRP | stat.S_IXGRP)
                        
                        # 复制文件
                        shutil.copy2(exe_path, target_exe_path)
                        
                        # 确保文件有执行权限
                        os.chmod(target_exe_path, stat.S_IWUSR | stat.S_IRUSR | stat.S_IXUSR | stat.S_IWGRP | stat.S_IRGRP | stat.S_IXGRP)
                        
                    except Exception as copy_error:
                        logging.error(f"复制文件失败: {str(copy_error)}")
                        messagebox.showwarning("警告", f"文件复制失败，但版本信息已更新: {str(copy_error)}")
                    
                    progress_var.set(80)
                    progress_label.config(text="已复制文件到下载目录")
                    new_version_window.update_idletasks()
                    
                    # 显示同步信息
                    progress_label.config(text="正在同步到网站...")
                    new_version_window.update_idletasks()
                    
                    # 尝试同步到Github目录（如果存在）
                    github_dir = os.path.join(os.path.dirname(current_dir), "Github")
                    if os.path.exists(github_dir):
                        # 复制update_info.json到Github目录
                        github_update_file = os.path.join(github_dir, "update_info.json")
                        try:
                            shutil.copy2(update_file, github_update_file)
                            progress_var.set(90)
                        except Exception as e:
                            logging.error(f"同步到Github目录失败: {str(e)}")
                    
                    # 尝试同步到网站目录（www.tomarens.xyz的本地映射）
                    website_dirs = [
                        os.path.join(os.path.dirname(current_dir), "tomarens.xyz"),
                        "D:\\www\\tomarens.xyz"
                    ]
                    website_updated = False
                    
                    for web_dir in website_dirs:
                        if os.path.exists(web_dir):
                            try:
                                # 复制update_info.json到网站根目录
                                web_update_file = os.path.join(web_dir, "update_info.json")
                                shutil.copy2(update_file, web_update_file)
                                
                                # 确保downloads目录存在
                                web_downloads_dir = os.path.join(web_dir, "downloads")
                                if not os.path.exists(web_downloads_dir):
                                    os.makedirs(web_downloads_dir)
                                
                                # 复制可执行文件到网站downloads目录
                                web_exe_path = os.path.join(web_downloads_dir, "FBA费用计算器.exe")
                                shutil.copy2(target_exe_path, web_exe_path)
                                
                                # 复制反馈页面
                                feedback_html = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feedback.html")
                                if os.path.exists(feedback_html):
                                    shutil.copy2(feedback_html, os.path.join(web_dir, "feedback.html"))
                                
                                website_updated = True
                                break
                            except Exception as e:
                                logging.error(f"同步到网站目录 {web_dir} 失败: {str(e)}")
                    
                    progress_var.set(100)
                    progress_label.config(text="上传完成！")
                    new_version_window.update_idletasks()
                    
                    # 显示完成信息
                    completion_msg = f"更新已成功准备！\n\n"
                    completion_msg += f"1. 版本号: {new_version}\n"
                    completion_msg += f"2. 可执行文件已复制到: {target_exe_path}\n"
                    completion_msg += f"3. 更新信息已保存\n"
                    
                    if website_updated:
                        completion_msg += "4. 文件已自动同步到网站服务器\n\n"
                        completion_msg += "更新已完成，用户可以通过检查更新功能获取新版本。"
                    else:
                        completion_msg += "\n请确保将这些文件同步到网站服务器，特别是:\n"
                        completion_msg += "- 将downloads目录中的文件上传到网站的downloads目录\n"
                        completion_msg += "- 确保update_info.json可在网站根目录访问\n"
                        completion_msg += "\n提示: 可以尝试手动复制文件到网站服务器的www.tomarens.xyz目录"
                    
                    messagebox.showinfo("准备完成", completion_msg)
                    new_version_window.destroy()
                    self.status_var.set("就绪")
                    
                except Exception as e:
                    logging.error(f"上传更新失败: {str(e)}")
                    messagebox.showerror("上传失败", f"上传更新时出错: {str(e)}")
                    self.status_var.set("就绪")
            
            # 上传按钮 - 增大按钮尺寸
            upload_button = ttk.Button(
                button_frame, 
                text="上传更新", 
                style="Accent.TButton",
                command=do_upload,
                width=12  # 增大按钮宽度
            )
            upload_button.pack(side=tk.RIGHT, padx=15, pady=15)
            
            # 取消按钮 - 增大按钮尺寸
            cancel_button = ttk.Button(
                button_frame, 
                text="取消", 
                style="TButton",
                command=new_version_window.destroy,
                width=12  # 增大按钮宽度
            )
            cancel_button.pack(side=tk.RIGHT, padx=10)
            
        except Exception as e:
            logging.error(f"准备上传更新时出错: {str(e)}")
            messagebox.showerror("错误", f"准备上传更新时出错: {str(e)}")
            self.status_var.set("就绪")
    
    def download_update(self, download_url):
        """下载更新安装程序（用户手动安装）"""
        try:
            self.status_var.set("正在下载安装程序...")
            
            # 检查是否有互联网连接或本地服务器连接
            is_connected = self.check_internet_connection(download_url)
            
            if not is_connected:
                # 如果没有网络连接，提示用户并提供替代方法
                messagebox.showinfo(
                    "连接问题", 
                    "无法连接到服务器。将打开浏览器到下载页面，请手动下载安装程序。"
                )
                webbrowser.open(download_url)
                return
            
            # 确定下载目录
            download_dir = self.settings.get("update_download_dir", None)
            # 解析环境变量
            if download_dir:
                import os
                download_dir = os.path.expandvars(download_dir)
            if not download_dir or not os.path.exists(download_dir):
                # 如果没有保存的下载目录或目录不存在，询问用户
                default_dir = os.path.dirname(os.path.abspath(sys.executable)) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
                user_choice = messagebox.askyesno(
                    "选择下载位置", 
                    f"是否将安装程序下载到当前程序目录？\n{default_dir}\n\n选择'否'将允许您自定义下载位置。"
                )
                
                if user_choice:
                    download_dir = default_dir
                else:
                    download_dir = filedialog.askdirectory(
                        title="选择安装程序下载位置",
                        initialdir=default_dir
                    )
                    if not download_dir:  # 用户取消了选择
                        self.status_var.set("就绪")
                        return
                
                # 保存用户选择的下载目录
                self.settings["update_download_dir"] = download_dir
                self.save_settings()
            
            # 在后台线程中下载文件，避免阻塞UI
            def download_file():
                try:
                    import os
                    import threading
                    import queue
                    import requests
                    from concurrent.futures import ThreadPoolExecutor
                    
                    # 使用安装程序名称
                    installer_name = "FBA费用计算器安装程序.exe"
                    installer_path = os.path.join(download_dir, installer_name)
                    
                    # 下载优化器配置
                    chunk_size = 10 * 1024 * 1024  # 10MB块大小
                    max_workers = 4  # 并发线程数
                    
                    # 获取文件大小
                    try:
                        response = requests.head(download_url, allow_redirects=True)
                        response.raise_for_status()
                        file_size = int(response.headers.get('content-length', 0))
                        
                        if file_size == 0:
                            # 如果无法获取文件大小，回退到传统下载方式
                            self.root.after(0, lambda: self._fallback_download(download_url, download_dir, installer_name))
                            return
                    except:
                        # 如果HEAD请求失败，回退到传统下载方式
                        self.root.after(0, lambda: self._fallback_download(download_url, download_dir, installer_name))
                        return
                    
                    # 创建临时文件目录
                    temp_dir = os.path.join(download_dir, "temp_chunks")
                    if not os.path.exists(temp_dir):
                        os.makedirs(temp_dir)
                    
                    # 计算分块数量
                    chunks = []
                    for i in range(0, file_size, chunk_size):
                        start = i
                        end = min(i + chunk_size - 1, file_size - 1)
                        chunks.append((start, end, i // chunk_size))
                    
                    total_chunks = len(chunks)
                    completed_chunks = 0
                    progress_lock = threading.Lock()
                    error_occurred = False
                    
                    # 下载单个块
                    def download_chunk(chunk_info):
                        nonlocal completed_chunks, error_occurred
                        start, end, index = chunk_info
                        chunk_file = os.path.join(temp_dir, f"chunk_{index}")
                        
                        try:
                            headers = {'Range': f'bytes={start}-{end}'}
                            session = requests.Session()
                            session.mount('https://', requests.adapters.HTTPAdapter(pool_connections=10, pool_maxsize=10))
                            
                            # 添加重试机制
                            max_retries = 3
                            retry_count = 0
                            
                            while retry_count < max_retries:
                                try:
                                    with session.get(download_url, headers=headers, stream=True, timeout=30) as response:
                                        response.raise_for_status()
                                        
                                        with open(chunk_file, 'wb') as f:
                                            for chunk in response.iter_content(chunk_size=8192):
                                                if chunk:
                                                    f.write(chunk)
                                    
                                    # 验证文件大小
                                    if os.path.getsize(chunk_file) == end - start + 1:
                                        break
                                    else:
                                        raise Exception("块大小不匹配")
                                except Exception as e:
                                    retry_count += 1
                                    if retry_count >= max_retries:
                                        raise e
                                    # 指数退避
                                    import time
                                    time.sleep(2 ** retry_count)
                        
                        except Exception as e:
                            logging.error(f"下载块 {index} 失败: {str(e)}")
                            nonlocal error_occurred
                            error_occurred = True
                            return
                        finally:
                            # 更新进度
                            with progress_lock:
                                completed_chunks += 1
                                progress = min(int(100 * completed_chunks / total_chunks), 100)
                                self.root.after(0, lambda p=progress: self.status_var.set(f"正在下载安装程序... {p}%"))
                    
                    # 使用线程池下载所有块
                    with ThreadPoolExecutor(max_workers=max_workers) as executor:
                        executor.map(download_chunk, chunks)
                    
                    # 检查是否有错误
                    if error_occurred:
                        raise Exception("部分块下载失败")
                    
                    # 合并文件块
                    self.root.after(0, lambda: self.status_var.set("正在合并文件块..."))
                    
                    with open(installer_path, 'wb') as output:
                        for i in range(total_chunks):
                            chunk_file = os.path.join(temp_dir, f"chunk_{i}")
                            if os.path.exists(chunk_file):
                                with open(chunk_file, 'rb') as f:
                                    output.write(f.read())
                                os.remove(chunk_file)
                    
                    # 清理临时目录
                    if os.path.exists(temp_dir):
                        os.rmdir(temp_dir)
                    
                    # 下载完成后提示用户手动安装
                    self.root.after(0, lambda: [
                        self.status_var.set("安装程序下载完成"),
                        messagebox.showinfo(
                            "下载完成",
                            f"安装程序已成功下载到以下位置：\n{installer_path}\n\n请双击安装程序文件进行手动安装。"
                        ),
                        # 自动打开下载目录，方便用户找到安装程序
                        os.startfile(download_dir)
                    ])
                    
                except Exception as download_error:
                    logging.error(f"优化下载失败: {str(download_error)}")
                    # 如果优化下载失败，回退到传统方式
                    self.root.after(0, lambda: self._fallback_download(download_url, download_dir, installer_name))
                finally:
                    self.root.after(0, lambda: self.status_var.set("就绪"))
            
            # 启动下载线程
            download_thread = threading.Thread(target=download_file)
            download_thread.daemon = True
            download_thread.start()
            
            # 记录用户选择了更新
            logging.info("用户选择了下载更新")
            
        except Exception as e:
            logging.error(f"下载更新失败: {str(e)}")
            messagebox.showerror("下载失败", "无法下载更新文件，请稍后再试。")
            self.status_var.set("就绪")
    
    def _fallback_download(self, download_url, download_dir, installer_name):
        """回退到传统下载方式"""
        try:
            import urllib.request
            import os
            
            installer_path = os.path.join(download_dir, installer_name)
            
            def report_progress(block_num, block_size, total_size):
                if total_size > 0:
                    progress = min(int(100 * block_num * block_size / total_size), 100)
                    self.root.after(0, lambda: self.status_var.set(f"正在下载安装程序（传统方式）... {progress}%"))
                else:
                    self.root.after(0, lambda: self.status_var.set("正在下载安装程序（传统方式）..."))
            
            urllib.request.urlretrieve(download_url, installer_path, reporthook=report_progress)
            
            self.root.after(0, lambda: [
                self.status_var.set("安装程序下载完成"),
                messagebox.showinfo(
                    "下载完成",
                    f"安装程序已成功下载到以下位置：\n{installer_path}\n\n请双击安装程序文件进行手动安装。"
                ),
                os.startfile(download_dir)
            ])
            
        except Exception as e:
            logging.error(f"传统下载失败: {str(e)}")
            self.root.after(0, lambda: [
                messagebox.showinfo(
                    "下载方法切换", 
                    "直接下载失败，将打开浏览器到下载页面，请手动下载安装程序。"
                ),
                webbrowser.open(download_url)
            ])
    
    def prepare_update(self, temp_file_path, download_dir, exe_name):
        """准备更新，创建批处理文件来替换原程序"""
        try:
            # 目标程序路径
            if getattr(sys, 'frozen', False):  # 编译后的可执行文件
                target_exe_path = sys.executable
            else:  # 直接运行Python脚本
                target_exe_path = os.path.join(download_dir, exe_name)
            
            # 创建批处理文件来完成更新
            batch_file = os.path.join(download_dir, "update.bat")
            
            # 批处理文件内容
            batch_content = f"""
@echo off

echo 正在安装更新...

REM 等待3秒，确保主程序已关闭
ping -n 3 127.0.0.1 > nul

REM 备份原程序（可选）
if exist "{target_exe_path}" (
    echo 备份原程序...
    copy "{target_exe_path}" "{target_exe_path}.bak" > nul
)

REM 替换程序
move /y "{temp_file_path}" "{target_exe_path}" > nul

REM 删除批处理文件自身
del "%~f0"

REM 启动更新后的程序
start "" "{target_exe_path}"
echo 更新完成，程序已重新启动。
"""
            
            # 写入批处理文件
            with open(batch_file, 'w', encoding='utf-8') as f:
                f.write(batch_content)
            
            # 保存用户设置到一个临时位置
            settings_backup = os.path.join(download_dir, "settings_backup.json")
            with open(settings_backup, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            
            # 提示用户更新将在关闭程序后进行
            result = messagebox.askokcancel(
                "准备更新",
                f"更新已准备就绪！\n\n为了完成更新，程序需要关闭并重新启动。\n\n点击'确定'将立即关闭程序并执行更新。"
            )
            
            if result:
                # 关闭主程序
                self.root.destroy()
                
                # 启动批处理文件
                import subprocess
                subprocess.Popen(batch_file, shell=True, cwd=download_dir)
            
        except Exception as e:
            logging.error(f"准备更新时出错: {str(e)}")
            messagebox.showerror("更新准备失败", "准备更新过程中出现错误，请手动更新。")
    
    def check_internet_connection(self, url=None):
        """检查是否有互联网连接或指定URL的连接
        
        Args:
            url: 可选，要检查连接的URL
            
        Returns:
            bool: 连接是否成功
        """
        try:
            import urllib.request
            
            # 如果提供了URL，直接检查该URL的连接
            if url:
                try:
                    urllib.request.urlopen(url, timeout=5)
                    return True
                except:
                    # 如果指定URL连接失败，继续尝试其他连接
                    pass
            
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
    
    def open_file_location(self, file_path):
        """打开文件所在位置"""
        try:
            import subprocess
            # Windows下打开文件所在目录并选中文件
            subprocess.Popen(f'explorer /select,"{file_path}"')
        except Exception as e:
            logging.error(f"打开文件位置失败: {str(e)}")
            # 如果无法选中文件，至少打开目录
            try:
                import subprocess
                subprocess.Popen(f'explorer "{os.path.dirname(file_path)}"')
            except:
                pass
    
    def load_settings(self):
        """加载用户设置"""
        try:
            # 确定设置文件位置
            if getattr(sys, 'frozen', False):  # 编译后的可执行文件
                settings_path = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), self.SETTINGS_FILE)
            else:  # 直接运行Python脚本
                settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.SETTINGS_FILE)
            
            # 读取设置文件
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logging.error(f"加载设置时出错: {str(e)}")
        
        # 返回默认设置
        return {
            "update_download_dir": None,
            "theme": "default",
            "window_size": "maximized"
        }
    
    def save_settings(self):
        """保存用户设置"""
        try:
            # 确定设置文件位置
            if getattr(sys, 'frozen', False):  # 编译后的可执行文件
                settings_path = os.path.join(os.path.dirname(os.path.abspath(sys.executable)), self.SETTINGS_FILE)
            else:  # 直接运行Python脚本
                settings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.SETTINGS_FILE)
            
            # 确保设置目录存在
            settings_dir = os.path.dirname(settings_path)
            if not os.path.exists(settings_dir):
                os.makedirs(settings_dir)
            
            # 保存设置文件
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, ensure_ascii=False, indent=2)
            
            # 验证保存是否成功
            if os.path.exists(settings_path):
                # 检查文件大小是否合理
                file_size = os.path.getsize(settings_path)
                if file_size > 0:
                    # 重新读取验证内容
                    with open(settings_path, 'r', encoding='utf-8') as f:
                        loaded_settings = json.load(f)
                    # 比较关键字段确保保存正确
                    if loaded_settings.get('version') == self.settings.get('version'):
                        logging.info("设置保存成功")
                        # 显示保存成功提示
                        self.status_var.set("设置已成功保存")
                        # 3秒后恢复状态栏
                        self.root.after(3000, lambda: self.status_var.set("就绪"))
                        return True
            
            # 如果验证失败
            logging.warning("设置文件保存但验证失败")
            return False
            
        except Exception as e:
            logging.error(f"保存设置时出错: {str(e)}")
            return False
    
    def show_settings_dialog(self):
        """显示设置对话框，包含常规程序设置和BUG反馈功能"""
        # 创建设置窗口
        settings_window = tk.Toplevel(self.root)
        settings_window.title("设置")
        settings_window.geometry("700x600")
        settings_window.resizable(False, False)
        settings_window.configure(bg=self.color_theme["background"])
        
        # 设置窗口在屏幕中心
        settings_window.update_idletasks()
        width = settings_window.winfo_width()
        height = settings_window.winfo_height()
        x = (settings_window.winfo_screenwidth() // 2) - (width // 2)
        y = (settings_window.winfo_screenheight() // 2) - (height // 2)
        settings_window.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
        # 创建标签页控件
        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建常规设置标签页
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="常规设置")
        
        # 创建BUG反馈标签页
        bug_feedback_frame = ttk.Frame(notebook)
        notebook.add(bug_feedback_frame, text="BUG反馈")
        
        # 加载常规设置页面
        self._load_general_settings(general_frame)
        
        # 加载BUG反馈页面
        self._load_bug_feedback_page(bug_feedback_frame, settings_window)
    
    def _load_general_settings(self, parent):
        """加载常规设置页面"""
        # 创建设置分组
        appearance_frame = ttk.LabelFrame(parent, text="外观设置", padding="15")
        appearance_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 主题选择
        theme_frame = ttk.Frame(appearance_frame)
        theme_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(theme_frame, text="程序主题:", width=15, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 10))
        
        theme_var = tk.StringVar(value=self.settings.get("theme", "default"))
        theme_frame_inner = ttk.Frame(theme_frame)
        theme_frame_inner.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 可用主题选项
        themes = [
            ("默认主题", "default"),
            ("浅色主题", "light"),
            ("深色主题", "dark")
        ]
        
        for text, value in themes:
            ttk.Radiobutton(
                theme_frame_inner, 
                text=text, 
                variable=theme_var, 
                value=value
            ).pack(side=tk.LEFT, padx=(0, 20))
        
        # 窗口设置分组
        window_frame = ttk.LabelFrame(parent, text="窗口设置", padding="15")
        window_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 窗口启动大小
        window_size_frame = ttk.Frame(window_frame)
        window_size_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(window_size_frame, text="启动时窗口大小:", width=15, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 10))
        
        window_size_var = tk.StringVar(value=self.settings.get("window_size", "maximized"))
        window_size_frame_inner = ttk.Frame(window_size_frame)
        window_size_frame_inner.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        sizes = [
            ("最大化", "maximized"),
            ("窗口化", "windowed")
        ]
        
        for text, value in sizes:
            ttk.Radiobutton(
                window_size_frame_inner, 
                text=text, 
                variable=window_size_var, 
                value=value
            ).pack(side=tk.LEFT, padx=(0, 20))
        
        # 更新设置分组
        update_frame = ttk.LabelFrame(parent, text="更新设置", padding="15")
        update_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # 启动时检查更新
        check_update_var = tk.BooleanVar(value=self.settings.get("check_update_on_start", True))
        check_update_checkbox = ttk.Checkbutton(
            update_frame, 
            text="启动时自动检查更新", 
            variable=check_update_var
        )
        check_update_checkbox.pack(anchor=tk.W, pady=5)
        
        # 保存设置按钮
        def save_general_settings():
            # 更新设置
            self.settings["theme"] = theme_var.get()
            self.settings["window_size"] = window_size_var.get()
            self.settings["check_update_on_start"] = check_update_var.get()
            
            # 应用主题变更
            if theme_var.get() != "default":
                self._apply_theme_by_name(theme_var.get())
            
            # 保存设置并检查结果
            if self.save_settings():
                messagebox.showinfo("保存成功", "设置已成功保存！")
                window.destroy()  # 保存成功后关闭窗口
            else:
                messagebox.showerror("保存失败", "设置保存失败，请检查文件权限或磁盘空间。")
        
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=10, pady=10, side=tk.BOTTOM)
        
        save_button = ttk.Button(
            button_frame, 
            text="保存设置", 
            command=save_general_settings,
            style="Accent.TButton"
        )
        save_button.pack(side=tk.RIGHT, padx=5)
    
    def _load_bug_feedback_page(self, parent, window):
        """加载BUG反馈页面"""
        # 创建反馈说明
        info_label = ttk.Label(
            parent, 
            text="请描述您遇到的问题或建议，我们会尽快处理！",
            font=self.header_font
        )
        info_label.pack(pady=10, padx=10, anchor=tk.CENTER)
        
        # 添加本地反馈管理按钮
        feedback_manage_frame = ttk.Frame(parent)
        feedback_manage_frame.pack(fill=tk.X, padx=10, pady=5)
        
        manage_button = ttk.Button(
            feedback_manage_frame,
            text="查看本地反馈记录",
            command=self.show_local_feedback,
            style="Custom.TButton"
        )
        manage_button.pack(side=tk.RIGHT, padx=5)
        
        # 反馈类型
        type_frame = ttk.Frame(parent)
        type_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(type_frame, text="反馈类型:", width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 10))
        
        feedback_type_var = tk.StringVar(value="bug")
        type_frame_inner = ttk.Frame(type_frame)
        type_frame_inner.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        types = [
            ("Bug报告", "bug"),
            ("功能建议", "feature"),
            ("其他反馈", "other")
        ]
        
        for text, value in types:
            ttk.Radiobutton(
                type_frame_inner, 
                text=text, 
                variable=feedback_type_var, 
                value=value
            ).pack(side=tk.LEFT, padx=(0, 20))
        
        # 联系方式
        contact_frame = ttk.Frame(parent)
        contact_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(contact_frame, text="联系方式:", width=10, anchor=tk.W).pack(side=tk.LEFT, padx=(0, 10))
        
        contact_var = tk.StringVar(value="")
        contact_entry = ttk.Entry(
            contact_frame, 
            textvariable=contact_var, 
            width=50,
            style="Custom.TEntry"
        )
        contact_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(parent, text="（可选：邮箱、电话等，方便我们联系您）").pack(padx=10, anchor=tk.W)
        
        # 反馈内容
        content_frame = ttk.LabelFrame(parent, text="详细描述", padding="10")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        content_text = tk.Text(
            content_frame, 
            wrap=tk.WORD,
            font=self.default_font,
            height=8,  # 减小高度，为按钮留出更多空间
            relief=tk.SUNKEN,
            bd=2
        )
        content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(
            content_frame, 
            orient=tk.VERTICAL, 
            command=content_text.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        content_text.config(yscrollcommand=scrollbar.set)
        
        # 按钮框架 - 修改布局，不使用side=tk.BOTTOM确保按钮始终可见
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, padx=10, pady=20)
        
        # 验证码功能
        import random
        import string
        
        def generate_captcha(length=6):
            """生成随机验证码"""
            characters = string.ascii_letters + string.digits
            return ''.join(random.choice(characters) for _ in range(length))
        
        # 显示验证码的标签
        captcha_value = generate_captcha()
        captcha_var = tk.StringVar(value=captcha_value)
        captcha_label = ttk.Label(button_frame, text="验证码:", font=('Arial', 12, 'bold'))
        captcha_label.pack(side=tk.LEFT, padx=(0, 5))
        
        captcha_display = ttk.Label(button_frame, textvariable=captcha_var, font=('Arial', 12, 'bold'), width=8)
        captcha_display.pack(side=tk.LEFT, padx=(0, 5))
        
        # 刷新验证码按钮
        def refresh_captcha():
            nonlocal captcha_value
            new_captcha = generate_captcha()
            captcha_value = new_captcha
            captcha_var.set(new_captcha)
        
        refresh_button = ttk.Button(button_frame, text="刷新", command=refresh_captcha)
        refresh_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # 验证码输入框
        captcha_entry = ttk.Entry(button_frame, width=10, font=('Arial', 12))
        captcha_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # 提交按钮函数
        def submit_feedback():
            # 获取反馈内容
            content = content_text.get("1.0", tk.END).strip()
            if not content:
                messagebox.showerror("错误", "请输入反馈内容")
                return
            
            # 验证码验证
            user_captcha = captcha_entry.get().strip()
            if user_captcha.upper() != captcha_value.upper():
                messagebox.showerror("验证码错误", "请输入正确的验证码")
                refresh_captcha()  # 刷新验证码
                captcha_entry.delete(0, tk.END)  # 清空输入
                return
            
            # 创建反馈数据
            feedback_data = {
                "type": feedback_type_var.get(),
                "contact": contact_var.get(),
                "content": content,
                "version": self.VERSION,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "system": platform.platform()
            }
            
            # 保存反馈到文件并尝试发送到服务器
            try:
                # 确定反馈文件位置
                if getattr(sys, 'frozen', False):  # 编译后的可执行文件
                    feedback_dir = os.path.dirname(os.path.abspath(sys.executable))
                else:  # 直接运行Python脚本
                    feedback_dir = os.path.dirname(os.path.abspath(__file__))
                
                feedback_file = os.path.join(feedback_dir, "feedback.json")
                
                # 增强的本地反馈存储功能
                feedbacks = []
                if os.path.exists(feedback_file):
                    try:
                        with open(feedback_file, 'r', encoding='utf-8') as f:
                            feedbacks = json.load(f)
                    except json.JSONDecodeError:
                        # 如果文件损坏，创建新的空列表
                        logging.error("反馈文件损坏，创建新的反馈列表")
                        feedbacks = []
                
                # 添加反馈状态和时间戳
                feedback_data['status'] = 'pending'  # pending, sent, failed
                feedback_data['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                feedbacks.append(feedback_data)
                
                # 保存反馈
                try:
                    # 确保目录存在
                    os.makedirs(os.path.dirname(feedback_file), exist_ok=True)
                    with open(feedback_file, 'w', encoding='utf-8') as f:
                        json.dump(feedbacks, f, ensure_ascii=False, indent=2)
                    logging.info("反馈已成功保存到本地")
                except Exception as e:
                    logging.error(f"保存反馈到本地失败: {str(e)}")
                
                # 本地反馈存储已完成，现在尝试发送到服务器
                server_success = False
                try:
                    if self.check_internet_connection():
                        import urllib.request
                        import urllib.error
                        
                        # 使用统一域名，尝试多个端点
                        DOMAIN = "tomarens.xyz"
                        endpoints = [
                            f"http://{DOMAIN}:8081/submit_feedback",  # 本地服务器配置
                            f"https://{DOMAIN}/submit_feedback",      # HTTPS
                            f"http://{DOMAIN}/submit_feedback",       # HTTP
                        ]
                        
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
                            else:
                                logging.error(f"发送反馈到服务器失败，HTTP状态码: {response.status}")
                except Exception as e:
                    logging.error(f"发送反馈到服务器异常: {str(e)}")
                
                # 无论是否发送到服务器，都显示成功信息
                if server_success:
                    messagebox.showinfo("提交成功", f"感谢您的反馈！我们会尽快处理。\n\n反馈已保存到本地文件: {feedback_file}")
                else:
                    messagebox.showinfo("提交成功（本地）", f"反馈已成功保存到本地文件，将在网络恢复后尝试发送到服务器。\n\n本地文件路径: {feedback_file}")
                window.destroy()
                
            except Exception as e:
                logging.error(f"保存反馈时出错: {str(e)}")
                messagebox.showerror("提交失败", "保存反馈时出现错误，请稍后再试。")
        
        # 添加提交按钮到按钮框架 - 增大按钮尺寸
        submit_button = ttk.Button(
            button_frame, 
            text="提交反馈", 
            command=submit_feedback,
            style="Accent.TButton",
            width=12  # 增大按钮宽度
        )
        submit_button.pack(side=tk.RIGHT, padx=15, pady=15)
    
    def _apply_theme_by_name(self, theme_name):
        """根据主题名称应用主题"""
        # 预定义主题
        themes = {
            "light": {
                "background": "#f8f9fa",
                "frame_bg": "#ffffff",
                "text_bg": "#ffffff",
                "text_fg": "#212529",
                "button_bg": "#e9ecef",
                "button_active": "#dee2e6",
                "button_pressed": "#ced4da",
                "highlight_bg": "#d1ecf1",
                "header_bg": "#bee5eb",
                "segment_bg": "#f8d7da",
                "border_color": "#adb5bd",
                "shadow_color": "#6c757d"
            },
            "dark": {
                "background": "#212529",
                "frame_bg": "#343a40",
                "text_bg": "#343a40",
                "text_fg": "#f8f9fa",
                "button_bg": "#495057",
                "button_active": "#6c757d",
                "button_pressed": "#868e96",
                "highlight_bg": "#2c5aa0",
                "header_bg": "#1664aa",
                "segment_bg": "#721c24",
                "border_color": "#6c757d",
                "shadow_color": "#000000"
            }
        }
        
        # 应用主题
        if theme_name in themes:
            self.color_theme = themes[theme_name]
            self.apply_theme()
    
    def on_closing(self):
        """程序关闭时执行的操作"""
        # 保存用户设置
        self.save_settings()
        # 关闭程序
        self.root.destroy()
    
    def create_weight_inputs(self):
        # 重量输入框架
        self.weight_frame = ttk.LabelFrame(self.container, text="商品重量", padding="15")
        self.weight_frame.pack(fill=tk.X, pady=(0, 15))
        weight_frame = self.weight_frame
        
        # 重量单位变量
        self.weight_unit_var = tk.StringVar(value="磅")
        # 保存上一次选择的单位，用于转换
        self.last_weight_unit = "磅"
        
        # 单位选择行
        unit_row = ttk.Frame(weight_frame)
        unit_row.pack(fill=tk.X, pady=(0, 10))
        
        unit_label = ttk.Label(unit_row, text="重量单位:", width=15, anchor=tk.W)
        unit_label.pack(side=tk.LEFT, padx=(0, 10))
        
        unit_frame = ttk.Frame(unit_row)
        unit_frame.pack(side=tk.LEFT)
        
        # 磅单选按钮
        lb_radio = ttk.Radiobutton(
            unit_frame, 
            text="磅 (lb)", 
            variable=self.weight_unit_var, 
            value="磅",
            command=lambda: [self.on_weight_unit_change(), self.update_size_segment()]
        )
        lb_radio.pack(side=tk.LEFT, padx=(0, 20))
        
        # 盎司单选按钮
        oz_radio = ttk.Radiobutton(
            unit_frame, 
            text="盎司 (oz)", 
            variable=self.weight_unit_var, 
            value="盎司",
            command=lambda: [self.on_weight_unit_change(), self.update_size_segment()]
        )
        oz_radio.pack(side=tk.LEFT, padx=(0, 20))
        
        # 移除克和千克选项，只保留磅和盎司
        
        # 重量值输入
        self.weight_var = tk.StringVar()
        
        # 根据当前站点设置默认单位标签
        default_unit = "磅"
        if hasattr(self, 'current_site') and self.current_site == "jp":
            default_unit = "克"
        
        # 根据当前站点设置初始UI状态
        if hasattr(self, 'current_site'):
            if self.current_site == "jp":
                # 日本站：设置克单位，隐藏单位选择
                self.weight_unit_var.set("克")
                # 创建重量输入行，直接使用正确的默认单位
                self.weight_unit_label = self.create_input_row(
                    weight_frame, 
                    "重量值:", 
                    self.weight_var, 
                    default_unit="克"
                )
                # 移除强制设置，让单位标签直接使用default_unit值
                pass
                # 隐藏单位选择
                unit_row.pack_forget()
            else:
                # 美国站：设置磅单位，显示单位选择
                self.weight_unit_var.set("磅")
                # 创建重量输入行，使用磅单位
                self.weight_unit_label = self.create_input_row(
                    weight_frame, 
                    "重量值:", 
                    self.weight_var, 
                    default_unit="磅"
                )
                # 移除强制设置，让单位标签直接使用default_unit值
                pass
                # 显示单位选择
                unit_row.pack(fill=tk.X, pady=(0, 10))
        else:
            # 默认情况（没有current_site属性）
            self.weight_unit_label = self.create_input_row(
                weight_frame, 
                "重量值:", 
                self.weight_var, 
                default_unit=default_unit
            )
            # 默认显示单位选择
            unit_row.pack(fill=tk.X, pady=(0, 10))
    
    def create_segment_display(self):
        # 尺寸分段显示框架
        self.segment_frame = ttk.LabelFrame(self.container, text="商品尺寸分段", padding="15")
        self.segment_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 分段信息显示
        segment_info_frame = ttk.Frame(self.segment_frame)
        segment_info_frame.pack(fill=tk.X, pady=5)
        
        segment_label = ttk.Label(segment_info_frame, text="当前分段:", width=15, anchor=tk.W)
        segment_label.pack(side=tk.LEFT, padx=(0, 10))
        
        # 分段显示文本框
        self.segment_display_var = tk.StringVar(value="请输入商品尺寸和重量")
        self.segment_display = ttk.Label(
            segment_info_frame, 
            textvariable=self.segment_display_var, 
            font=self.header_font, 
            foreground="#1a5276",
            wraplength=400,
            anchor=tk.W
        )
        self.segment_display.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def create_buttons(self):
        # 创建带阴影效果的按钮框架
        shadow_frame = ttk.Frame(self.container)
        shadow_frame.pack(fill=tk.X, pady=(0, 15))
        
        button_frame = ttk.Frame(shadow_frame)
        button_frame.pack(fill=tk.X, padx=2, pady=2)
        
        # 创建六个按钮，使用立体感样式
        self.calc_button = ttk.Button(
            button_frame, 
            text="计算配送费", 
            command=self.calculate_shipping,
            style="Accent.TButton",
            width=15
        )
        self.calc_button.pack(side=tk.LEFT, padx=(0, 10), pady=5)
        
        self.clear_button = ttk.Button(
            button_frame, 
            text="清空", 
            command=self.clear_all,
            style="Accent.TButton",
            width=10
        )
        self.clear_button.pack(side=tk.LEFT, padx=(0, 10), pady=5)
        
        self.export_button = ttk.Button(
            button_frame, 
            text="数据导出", 
            command=self.export_data,
            style="Accent.TButton",
            width=10
        )
        self.export_button.pack(side=tk.LEFT, padx=(0, 10), pady=5)
        
        self.batch_process_button = ttk.Button(
            button_frame, 
            text="批量处理", 
            command=self.batch_process,
            style="Accent.TButton",
            width=10
        )
        self.batch_process_button.pack(side=tk.LEFT, padx=(0, 10), pady=5)
        
        self.theme_button = ttk.Button(
            button_frame, 
            text="更改主题", 
            command=self.show_theme_dialog,
            style="Accent.TButton",
            width=10
        )
        self.theme_button.pack(side=tk.LEFT, padx=(0, 10), pady=5)
        
        self.exit_button = ttk.Button(
            button_frame, 
            text="退出", 
            command=self.root.destroy,
            style="Accent.TButton",
            width=10
        )
        self.exit_button.pack(side=tk.RIGHT, pady=5)
    
    def create_result_area(self):
        # 结果框架
        result_frame = ttk.LabelFrame(self.container, text="计算结果", padding="15")
        result_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 创建内部框架以更好地管理布局
        text_frame = ttk.Frame(result_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建结果文本框
        self.result_text = tk.Text(
            text_frame, 
            wrap=tk.WORD,
            font=self.default_font,
            state=tk.DISABLED,
            height=10,
            relief=tk.SUNKEN,
            bd=2
        )
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(
            text_frame, 
            orient=tk.VERTICAL, 
            command=self.result_text.yview
        )
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.result_text.config(yscrollcommand=scrollbar.set)
    
    def clear_all(self):
        # 清空所有输入
        self.max_len_var.set("")
        self.mid_len_var.set("")
        self.min_len_var.set("")
        self.weight_var.set("")
        self.weight_unit_var.set("磅")
        
        # 更新重量单位标签
        self.on_weight_unit_change()
        
        # 清空结果区域
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.config(state=tk.DISABLED)
        
        # 重置尺寸分段显示
        self.segment_display_var.set("请输入商品尺寸和重量")
        
        # 询问是否清空历史记录
        if hasattr(self, 'calculation_history') and self.calculation_history:
            if messagebox.askyesno("清空历史", "是否同时清空计算历史记录？"):
                self.calculation_history.clear()
        
    def on_weight_unit_change(self):
        # 检查当前站点，如果是日本站，直接显示克单位并不执行转换
        if hasattr(self, 'current_site') and self.current_site == "jp":
            # 日本站时始终显示克单位
            self.weight_unit_label.config(text="克 (g)")
            return
        
        # 获取新的单位和当前重量值
        new_unit = self.weight_unit_var.get()
        weight_value = self.weight_var.get()
        
        # 更新单位标签，显示完整的单位名称（包括英文缩写）
        unit_display_map = {
            "磅": "磅 (lb)",
            "盎司": "盎司 (oz)"
        }
        display_text = unit_display_map.get(new_unit, new_unit)
        self.weight_unit_label.config(text=display_text)
        
        # 如果有重量值且单位发生了变化，则进行转换
        if weight_value and hasattr(self, 'last_weight_unit') and self.last_weight_unit != new_unit:
            try:
                weight = float(weight_value)
                
                # 单位转换逻辑 - 首先转换为克（中间单位）
                weight_in_grams = 0
                
                # 从当前单位转换为克
                if self.last_weight_unit == "磅":
                    weight_in_grams = weight * 453.59237
                elif self.last_weight_unit == "盎司":
                    weight_in_grams = weight * 28.349523125
                
                # 从克转换为新单位
                converted_weight = 0
                format_str = "{0:.2f}"  # 默认格式
                
                if new_unit == "磅":
                    converted_weight = weight_in_grams / 453.59237
                    format_str = "{0:.2f}"
                elif new_unit == "盎司":
                    converted_weight = weight_in_grams / 28.349523125
                    format_str = "{0:.1f}"
                
                # 更新显示值
                self.weight_var.set(format_str.format(converted_weight))
            except ValueError:
                # 如果输入不是有效的数字，不做处理
                pass
        
        # 更新最后选择的单位
        if hasattr(self, 'last_weight_unit'):
            self.last_weight_unit = new_unit
    
    def update_result(self, text):
        # 更新结果显示
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, text)
        self.result_text.config(state=tk.DISABLED)
    
    def update_size_segment(self):
        """实时更新尺寸分段显示"""
        try:
            # 获取输入值
            if not (self.max_len_var.get() and self.mid_len_var.get() and 
                   self.min_len_var.get() and self.weight_var.get()):
                # 输入不完整时显示提示信息
                if hasattr(self, 'segment_display_var'):
                    self.segment_display_var.set("请输入商品尺寸和重量")
                return
            
            max_len = float(self.max_len_var.get())
            mid_len = float(self.mid_len_var.get())
            min_len = float(self.min_len_var.get())
            weight = float(self.weight_var.get())
            
            # 验证输入
            if max_len <= 0 or mid_len <= 0 or min_len <= 0 or weight <= 0:
                # 输入无效时显示提示信息
                if hasattr(self, 'segment_display_var'):
                    self.segment_display_var.set("请输入有效的数值")
                return
            
            # 根据当前站点使用不同的尺寸分段方法
            if hasattr(self, 'current_site') and self.current_site == "jp":
                # 日本站：使用最长边判断尺寸分段
                size_segment = self.determine_size_segment_jp(max_len)
            else:
                # 美国站：使用完整的尺寸分段逻辑
                weight_unit = self.weight_unit_var.get()
                len_girth = max_len + 2 * (mid_len + min_len)
                weight_oz = weight if weight_unit == '盎司' else weight * 16
                weight_lb = weight if weight_unit == '磅' else weight / 16
                size_segment = self.determine_size_segment(
                    max_len, mid_len, min_len, len_girth, weight_lb, weight_oz
                )
            
            # 更新显示
            if hasattr(self, 'segment_display_var'):
                self.segment_display_var.set(size_segment)
            
        except (ValueError, TypeError):
            # 输入不完整或无效时显示提示信息
            if hasattr(self, 'segment_display_var'):
                self.segment_display_var.set("请输入有效的数值")
            pass
    
    def _apply_theme_to_widget(self, widget):
        """递归应用主题到所有控件"""
        try:
            # 应用基本样式
            if hasattr(widget, 'configure'):
                # 标签和框架
                if isinstance(widget, (ttk.Label, tk.Label)):
                    widget.configure(foreground=self.color_theme["text_fg"])
                # 输入框
                elif isinstance(widget, (ttk.Entry, tk.Entry)):
                    widget.configure(foreground=self.color_theme["text_fg"])
                # 框架类
                elif isinstance(widget, ttk.LabelFrame):
                    widget.configure(style="Custom.TLabelframe")
            
            # 递归处理子控件
            if hasattr(widget, 'winfo_children'):
                for child in widget.winfo_children():
                    self._apply_theme_to_widget(child)
        except:
            pass  # 忽略无法配置的控件
    
    def show_theme_dialog(self):
        """显示主题颜色选择对话框"""
        theme_window = tk.Toplevel(self.root)
        theme_window.title("选择主题颜色")
        theme_window.geometry("400x450")
        theme_window.transient(self.root)
        theme_window.grab_set()
        
        # 创建颜色选项，增加更多主题
        colors = {
            "默认": {
                "background": "#f0f0f0",
                "frame_bg": "#ffffff",
                "text_bg": "#ffffff",
                "text_fg": "#000000",
                "button_bg": "#e6e6e6",
                "highlight_bg": "#d4e6f1",
                "header_bg": "#aed6f1",
                "segment_bg": "#f9ebea"
            },
            "蓝色": {
                "background": "#e6f3ff",
                "frame_bg": "#ffffff",
                "text_bg": "#f0f8ff",
                "text_fg": "#00008b",
                "button_bg": "#d4e6f1",
                "highlight_bg": "#aed6f1",
                "header_bg": "#5dade2",
                "segment_bg": "#aed6f1"
            },
            "深蓝": {
                "background": "#001f3f",
                "frame_bg": "#001f3f",
                "text_bg": "#001f3f",
                "text_fg": "#ffffff",
                "button_bg": "#003366",
                "highlight_bg": "#1e3a8a",
                "header_bg": "#004d80",
                "segment_bg": "#1e3a8a"
            },
            "绿色": {
                "background": "#e8f8f5",
                "frame_bg": "#ffffff",
                "text_bg": "#f8f9f9",
                "text_fg": "#145a32",
                "button_bg": "#d5f5e3",
                "highlight_bg": "#a9dfbf",
                "header_bg": "#52be80",
                "segment_bg": "#a9dfbf"
            },
            "翠绿色": {
                "background": "#e0f2f1",
                "frame_bg": "#ffffff",
                "text_bg": "#e0f2f1",
                "text_fg": "#004d40",
                "button_bg": "#b2dfdb",
                "highlight_bg": "#80cbc4",
                "header_bg": "#26a69a",
                "segment_bg": "#80cbc4"
            },
            "暖色调": {
                "background": "#fef9e7",
                "frame_bg": "#ffffff",
                "text_bg": "#fcf3cf",
                "text_fg": "#922b21",
                "button_bg": "#fdebd0",
                "highlight_bg": "#fad7a0",
                "header_bg": "#f39c12",
                "segment_bg": "#fad7a0"
            },
            "紫色": {
                "background": "#f3e5f5",
                "frame_bg": "#ffffff",
                "text_bg": "#f3e5f5",
                "text_fg": "#4a148c",
                "button_bg": "#e1bee7",
                "highlight_bg": "#ce93d8",
                "header_bg": "#9c27b0",
                "segment_bg": "#ce93d8"
            },
            "粉色": {
                "background": "#fce4ec",
                "frame_bg": "#ffffff",
                "text_bg": "#fce4ec",
                "text_fg": "#880e4f",
                "button_bg": "#f8bbd0",
                "highlight_bg": "#f48fb1",
                "header_bg": "#e91e63",
                "segment_bg": "#f48fb1"
            },
            "灰色": {
                "background": "#f5f5f5",
                "frame_bg": "#ffffff",
                "text_bg": "#f5f5f5",
                "text_fg": "#212121",
                "button_bg": "#e0e0e0",
                "highlight_bg": "#bdbdbd",
                "header_bg": "#757575",
                "segment_bg": "#bdbdbd"
            },
            "高对比度": {
                "background": "#000000",
                "frame_bg": "#121212",
                "text_bg": "#121212",
                "text_fg": "#ffffff",
                "button_bg": "#212121",
                "highlight_bg": "#424242",
                "header_bg": "#757575",
                "segment_bg": "#424242"
            }
        }
        
        # 主题变量
        selected_theme = tk.StringVar(value="默认")
        
        # 创建主题选项框架
        theme_frame = ttk.LabelFrame(theme_window, text="选择主题", padding="15")
        theme_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 创建滚动区域来容纳更多主题选项
        canvas = tk.Canvas(theme_frame)
        scrollbar = ttk.Scrollbar(theme_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 放置滚动区域
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 添加主题选项
        for theme_name in colors.keys():
            theme_radio = ttk.Radiobutton(
                scrollable_frame, 
                text=theme_name, 
                variable=selected_theme, 
                value=theme_name
            )
            theme_radio.pack(anchor=tk.W, pady=8, padx=5)
        
        # 应用按钮
        def apply_theme():
            self.color_theme = colors[selected_theme.get()]
            self.apply_theme()
            
            # 重新创建所有样式
            self._create_styles()
            
            # 使用try-except处理组件配置
            try:
                self.root.configure(bg=self.color_theme["background"])
            except (AttributeError, TypeError):
                pass
            
            try:
                self.container.configure(bg=self.color_theme["background"])
            except (AttributeError, TypeError):
                pass
            
            # 递归应用主题到所有主要框架
            for frame in [self.fba_frame, self.currency_frame]:
                self._apply_theme_to_widget(frame)
            
            # 更新导航栏
            try:
                self.nav_frame.configure(bg=self.color_theme["header_bg"])
            except (AttributeError, TypeError):
                pass
            
            # 更新按钮和标签
            try:
                for button in [self.calculate_button, self.clear_button, self.theme_button, self.quit_button]:
                    if button:
                        button.configure(style="Custom.TButton")
            except (AttributeError, TypeError):
                pass
            
            # 更新输入框样式
            try:
                for entry in [self.max_len_entry, self.mid_len_entry, self.min_len_entry, self.weight_entry]:
                    if entry:
                        entry.configure(style="Custom.TEntry")
            except (AttributeError, TypeError):
                pass
            
            # 确保汇率转换器也应用主题
            try:
                for widget in ['amount_entry', 'result_label', 'rates_text']:
                    if hasattr(self, widget):
                        self._apply_theme_to_widget(getattr(self, widget))
            except:
                pass
            
            # 关闭主题窗口
            theme_window.destroy()
        
        # 创建样式方法
        def _create_styles(self):
            """创建和更新所有ttk样式"""
            try:
                # 清除现有样式
                style = ttk.Style()
                
                # 创建自定义框架样式
                style.configure("Custom.TLabelframe", 
                              background=self.color_theme["frame_bg"])
                style.configure("Custom.TLabelframe.Label", 
                              foreground=self.color_theme["text_fg"])
                
                # 创建自定义按钮样式
                style.configure("Custom.TButton", 
                              background=self.color_theme["button_bg"])
                
                # 创建自定义输入框样式
                style.configure("Custom.TEntry", 
                              fieldbackground=self.color_theme["text_bg"],
                              foreground=self.color_theme["text_fg"])
                
                # 创建分段显示样式
                style.configure("Segment.TLabelframe", 
                              background=self.color_theme["segment_bg"])
                
                # 创建单选按钮样式
                style.configure("Custom.TRadiobutton", 
                              foreground=self.color_theme["text_fg"])
            except:
                pass  # 忽略样式错误
        
        # 将方法绑定到类实例
        _create_styles(self)
        
        # 更新文本框样式
        try:
            self.result_text.configure(
                bg=self.color_theme["text_bg"],
                fg=self.color_theme["text_fg"]
            )
        except (AttributeError, TypeError):
            pass
            
            # 关闭对话框
            try:
                theme_window.destroy()
            except (AttributeError, TypeError):
                pass
        
        # 设置自定义样式
        self.style.configure("Custom.TLabelframe", background=self.color_theme["frame_bg"])
        self.style.configure("Segment.TLabelframe", background=self.color_theme["segment_bg"])
        
        # 按钮框架
        button_frame = ttk.Frame(theme_window)
        button_frame.pack(fill=tk.X, padx=20, pady=(0, 20))
        
        # 取消按钮
        cancel_button = ttk.Button(
            button_frame, 
            text="取消", 
            command=theme_window.destroy,
            width=10
        )
        cancel_button.pack(side=tk.RIGHT, padx=(0, 10))
        
        # 应用按钮
        apply_button = ttk.Button(
            button_frame, 
            text="应用", 
            command=apply_theme,
            width=10
        )
        apply_button.pack(side=tk.RIGHT)
    
    def calculate_shipping(self):
        try:
            # 获取当前选中的站点
            current_site = self.site_var.get()
            
            # 获取输入值
            max_len = float(self.max_len_var.get())
            mid_len = float(self.mid_len_var.get())
            min_len = float(self.min_len_var.get())
            weight = float(self.weight_var.get())
            weight_unit = self.weight_unit_var.get()
            
            # 验证输入
            if max_len <= 0 or mid_len <= 0 or min_len <= 0 or weight <= 0:
                messagebox.showerror("输入错误", "所有数值必须大于0！")
                return
            
            if current_site == "us":
                # 美国站计算逻辑
                # 计算长度+围长
                len_girth = max_len + 2 * (mid_len + min_len)
                
                # 单位转换
                weight_oz = weight if weight_unit == '盎司' else weight * 16
                weight_lb = weight if weight_unit == '磅' else weight / 16
                
                # 判断尺寸分段
                size_segment = self.determine_size_segment(
                    max_len, mid_len, min_len, len_girth, weight_lb, weight_oz
                )
                
                # 计算费用并获取详细计算过程
                fee, calculation_steps = self.calculate_fee_with_steps(
                    size_segment, weight_lb, weight_oz, weight_unit
                )
                
                # 生成结果文本
                result_text = f"===== 计算结果 =====\n\n"
                result_text += f"📦 商品尺寸分段：{size_segment}\n\n"
                result_text += f"⚖️ 重量：{weight} {weight_unit}\n"
                result_text += f"   转换：{weight_lb:.2f} 磅 / {weight_oz:.2f} 盎司\n\n"
                result_text += f"📏 尺寸详情：\n"
                result_text += f"   最长边：{max_len} 英寸\n"
                result_text += f"   次长边：{mid_len} 英寸\n"
                result_text += f"   最短边：{min_len} 英寸\n"
                result_text += f"   长度+围长：{len_girth:.2f} 英寸\n\n"
                result_text += f"💰 配送费：${fee}\n\n"
                result_text += f"===== 计算过程 =====\n\n{calculation_steps}"
                
                # 保存到历史记录
                calculation_record = {
                    'timestamp': datetime.now(),
                    'site': 'us',
                    'max_len': max_len,
                    'mid_len': mid_len,
                    'min_len': min_len,
                    'weight': weight,
                    'weight_unit': weight_unit,
                    'size_segment': size_segment,
                    'shipping_fee': fee,
                    'len_girth': len_girth
                }
            else:
                # 日本站计算逻辑
                # 计算总尺寸（日本站使用总尺寸判断）
                total_size = max_len + mid_len + min_len
                
                # 检查商品价格
                # 使用用户在界面上选择的价格信息
                price_over_1000 = self.price_over_1000_var.get() if hasattr(self, 'price_over_1000_var') else True
                
                # 判断尺寸分段
                size_segment = self.determine_size_segment_jp(max_len)
                
                # 检查是否为冷冻商品
                is_frozen = self.is_frozen_var.get() if hasattr(self, 'is_frozen_var') else False
                
                # 计算费用并获取详细计算过程
                fee, calculation_steps = self.calculate_fee_with_steps_jp(
                    size_segment, weight, price_over_1000, is_frozen
                )
                
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
                    'weight_unit': weight_unit,
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
    
    def calculate_fba_fee(self, weight_g, length_cm, width_cm, height_cm):
        """
        计算FBA费用
        参数:
        - weight_g: 重量(克)
        - length_cm: 最长边(厘米)
        - width_cm: 次长边(厘米)
        - height_cm: 最短边(厘米)
        返回:
        - 包含尺寸分段、重量显示、围长显示和费用的字典
        """
        # 单位转换: 厘米转英寸 (1英寸 = 2.54厘米)
        max_len_in = length_cm / 2.54
        mid_len_in = width_cm / 2.54
        min_len_in = height_cm / 2.54
        
        # 单位转换: 克转磅和盎司 (1磅 = 453.592克, 1盎司 = 28.3495克)
        weight_lb = weight_g / 453.592
        weight_oz = weight_g / 28.3495
        
        # 计算长度+围长
        len_girth = max_len_in + 2 * (mid_len_in + min_len_in)
        
        # 判断尺寸分段
        size_segment = self.determine_size_segment(
            max_len_in, mid_len_in, min_len_in, len_girth, weight_lb, weight_oz
        )
        
        # 计算费用
        fee, _ = self.calculate_fee_with_steps(
            size_segment, weight_lb, weight_oz, '磅'  # 使用磅作为单位
        )
        
        # 准备返回结果
        return {
            'size_tier': size_segment,
            'weight_display': f"{weight_lb:.2f} 磅 / {weight_oz:.2f} 盎司",
            'girth_display': f"{len_girth:.2f} 英寸",
            'fee': fee
        }
    
    def determine_size_segment_jp(self, max_len_cm):
        """
        判断日本站的尺寸分段（6.1日本站FBA费用计算模块）
        参数:
        - max_len_cm: 最长边(厘米)
        返回:
        - 尺寸分段描述
        """
        # 根据新的日本站FBA配送费规则，区分不同尺寸分段
        # 新规则包括：小号、标准、大件、超大件等类别
        
        # 小号：不超过23厘米×35厘米×10厘米
        # 这里简化处理，主要根据最长边判断
        if max_len_cm <= 35:
            return "小号"
        # 标准尺寸：不超过80厘米
        elif max_len_cm <= 80:
            return "标准"
        # 大件：不超过120厘米
        elif max_len_cm <= 120:
            return "大件"
        # 超大件：超过120厘米但不超过200厘米
        elif max_len_cm <= 200:
            return "超大件"
        else:
            return "超大件（超出200厘米）"
    
    def calculate_fee_with_steps_jp(self, size_segment, weight_g, price_over_1000, is_frozen=False):
        """
        计算日本站FBA配送费用并返回详细计算过程（6.1日本站FBA费用计算模块）
        参数:
        - size_segment: 尺寸分段
        - weight_g: 重量(克)
        - price_over_1000: 价格是否超过1000日元
        - is_frozen: 是否为冷冻商品
        返回:
        - (费用, 计算步骤)
        """
        steps = []
        
        # 获取最大长度（从UI输入中获取）
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
        
        # 根据新表格定义的费用标准
        # 选择正确的费用表（价格超过/不超过1000日元）
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
                # 根据表格，超出200厘米或超过40千克的商品需要支付尺寸费用
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
            steps.append("- 对于需要温控包装的商品，如保温时间超过96小时，可能需支付额外费用")
        
        # 添加注释
        steps.append("\n注：本计算基于2025年最新的亚马逊日本站FBA配送费标准（6.1日本站FBA费用计算模块）")
        
        # 添加特殊说明
        steps.append("\n特别说明：")
        steps.append("- 对于危险商品和需要特殊处理的商品，可能适用不同的费用标准")
        steps.append("- 超过200厘米或超过40千克的商品可能需要支付额外的尺寸费用")
        steps.append("- 实际费用可能因亚马逊政策调整而变化，请以亚马逊官网为准")
        steps.append("- 冷冻商品可能产生额外的温控包装和处理费用")
        
        return fee, "\n".join(steps)
    
    def determine_size_segment(self, max_len, mid_len, min_len, len_girth, weight_lb, weight_oz):
        # 超大件判断
        is_oversized = (
            max_len > 59 or 
            mid_len > 33 or 
            min_len > 33 or 
            len_girth > 130 or 
            weight_lb > 50
        )
        
        if is_oversized or weight_lb >= 50:
            # 按重量细分超大件
            if weight_lb < 50:
                return "超大件：0至50磅"
            elif 50 <= weight_lb < 70:
                return "超大件：50至70磅（不含50磅）"
            elif 70 <= weight_lb < 150:
                return "超大件：70至150磅（不含70磅）"
            else:
                return "超大件：150磅以上（不含150磅）"
        else:
            # 判断标准尺寸/大件
            if (weight_oz <= 16) and (max_len <= 15) and (mid_len <= 12) and (min_len <= 0.75):
                return "小号标准尺寸"
            elif (weight_oz <= 320) and (max_len <= 18) and (mid_len <= 14) and (min_len <= 8):
                return "大号标准尺寸"
            elif (weight_lb <= 50) and (max_len <= 59) and (mid_len <= 33) and (min_len <= 33) and (len_girth <= 130):
                return "大号大件"
            else:
                # 其他情况按重量归为超大件
                if weight_lb < 50:
                    return "超大件：0至50磅"
                elif 50 <= weight_lb < 70:
                    return "超大件：50至70磅（不含50磅）"
                elif 70 <= weight_lb < 150:
                    return "超大件：70至150磅（不含70磅）"
                else:
                    return "超大件：150磅以上（不含150磅）"
    
    def calculate_fee(self, size_segment, weight_lb, weight_oz, weight_unit):
        # 小号标准尺寸（盎司）
        if size_segment == "小号标准尺寸":
            if weight_oz <= 2:
                return 3.06
            elif weight_oz <= 4:
                return 3.15
            elif weight_oz <= 6:
                return 3.24
            elif weight_oz <= 8:
                return 3.33
            elif weight_oz <= 10:
                return 3.43
            elif weight_oz <= 12:
                return 3.53
            elif weight_oz <= 14:
                return 3.60
            elif weight_oz <= 16:
                return 3.65
            else:
                return "重量区间不匹配"
        
        # 大号标准尺寸（支持盎司和磅）
        elif size_segment == "大号标准尺寸":
            if weight_unit == '盎司':
                if weight_oz <= 4:
                    return 3.68
                elif weight_oz <= 8:
                    return 3.90
                elif weight_oz <= 12:
                    return 4.15
                elif weight_oz <= 16:
                    return 4.55
                elif 24 < weight_oz <= 28:
                    return 4.55
                else:
                    # 对于超过上述范围的盎司值，转换为磅计算
                    return self.calculate_large_standard_fee_by_lb(weight_lb)
            else:
                return self.calculate_large_standard_fee_by_lb(weight_lb)
        
        # 大号大件（磅）
        elif size_segment == "大号大件":
            if weight_lb <= 0:
                return 9.61
            else:
                return round(9.61 + max(0, weight_lb - 0) * 0.38, 2)
        
        # 超大件：0至50磅
        elif size_segment == "超大件：0至50磅":
            return round(26.33 + max(0, weight_lb) * 0.38, 2)
        
        # 超大件：50至70磅
        elif size_segment == "超大件：50至70磅（不含50磅）":
            return round(40.12 + max(0, weight_lb - 51) * 0.75, 2)
        
        # 超大件：70至150磅
        elif size_segment == "超大件：70至150磅（不含70磅）":
            return round(54.81 + max(0, weight_lb - 71) * 0.75, 2)
        
        # 超大件：150磅以上
        elif size_segment == "超大件：150磅以上（不含150磅）":
            return round(194.95 + max(0, weight_lb - 151) * 0.19, 2)
        
        else:
            return "无法计算配送费"
    
    def calculate_large_standard_fee_by_lb(self, weight_lb):
        # 大号标准尺寸按磅计算的逻辑
        # 首先转换为盎司进行更精确的计算
        weight_oz = weight_lb * 16
        
        # 根据重量区间返回对应费用
        if weight_oz <= 4:
            return 3.68
        elif weight_oz <= 8:
            return 3.90
        elif weight_oz <= 12:
            return 4.15
        elif weight_oz <= 16:  # 1磅
            return 4.55
        elif weight_lb <= 1.25:
            return 4.99
        elif weight_lb <= 1.5:
            return 5.37
        elif weight_lb <= 1.75:
            return 5.52
        elif weight_lb <= 2:
            return 5.77
        elif weight_lb <= 2.25:
            return 5.87
        elif weight_lb <= 2.5:
            return 6.05
        elif weight_lb <= 2.75:
            return 6.21
        elif weight_lb <= 3:
            return 6.62
        elif weight_lb <= 20:
            return round(6.92 + max(0, weight_lb - 3) * 4 * 0.08, 2)
        else:
            return "超出重量范围"
    
    def export_data(self):
        """将计算结果导出为Excel或CSV格式"""
        try:
            # 检查是否有计算历史记录
            if not self.calculation_history and not self.result_text.get(1.0, tk.END).strip():
                messagebox.showinfo("提示", "没有可导出的数据，请先进行计算")
                return
            
            # 创建导出选项对话框
            export_window = tk.Toplevel(self.root)
            export_window.title("导出数据选项")
            export_window.geometry("400x250")
            export_window.transient(self.root)
            export_window.grab_set()
            
            ttk.Label(export_window, text="请选择导出选项：", font=('Arial', 10, 'bold')).pack(pady=15)
            
            # 导出类型选项
            export_type_var = tk.StringVar(value="current")
            
            ttk.Radiobutton(export_window, text="仅导出当前计算结果", variable=export_type_var, value="current").pack(anchor=tk.W, padx=20, pady=5)
            ttk.Radiobutton(export_window, text="导出全部计算历史记录", variable=export_type_var, value="history").pack(anchor=tk.W, padx=20, pady=5)
            
            # 导出格式选项
            ttk.Label(export_window, text="\n请选择导出格式：", font=('Arial', 10)).pack(pady=5)
            format_var = tk.StringVar(value="excel")
            
            format_frame = ttk.Frame(export_window)
            format_frame.pack(pady=5)
            ttk.Radiobutton(format_frame, text="Excel格式 (.xlsx)", variable=format_var, value="excel").pack(side=tk.LEFT, padx=20)
            ttk.Radiobutton(format_frame, text="CSV格式 (.csv)", variable=format_var, value="csv").pack(side=tk.LEFT, padx=20)
            
            # 准备导出数据的函数
            def prepare_export_data():
                export_type = export_type_var.get()
                format_type = format_var.get()
                export_window.destroy()
                
                # 准备导出数据
                data_list = []
                
                if export_type == "current":
                    # 获取当前结果
                    result_text = self.result_text.get(1.0, tk.END).strip()
                    if not result_text:
                        messagebox.showinfo("提示", "没有当前计算结果可导出")
                        return None, export_type, format_type
                    
                    data = {}
                    lines = result_text.split('\n')
                    for line in lines:
                        if '商品尺寸分段：' in line:
                            data['尺寸分段'] = line.split('：')[-1].strip()
                        elif '重量：' in line:
                            data['重量'] = line.split('：')[-1].strip()
                        elif '最长边：' in line:
                            data['最长边'] = line.split('：')[-1].strip()
                        elif '次长边：' in line:
                            data['次长边'] = line.split('：')[-1].strip()
                        elif '最短边：' in line:
                            data['最短边'] = line.split('：')[-1].strip()
                        elif '长度+围长：' in line:
                            data['长度+围长'] = line.split('：')[-1].strip()
                        elif '配送费：' in line:
                            data['配送费'] = line.split('：')[-1].strip()
                    data_list.append(data)
                else:
                    # 使用历史记录数据
                    if not self.calculation_history:
                        messagebox.showinfo("提示", "计算历史记录为空")
                        return None, export_type, format_type
                    data_list = self.calculation_history.copy()
                
                return data_list, export_type, format_type
            
            # 创建按钮框架
            button_frame = ttk.Frame(export_window)
            button_frame.pack(pady=15)
            ttk.Button(button_frame, text="确定", command=lambda: execute_export(prepare_export_data())).pack(side=tk.LEFT, padx=10)
            ttk.Button(button_frame, text="取消", command=export_window.destroy).pack(side=tk.LEFT, padx=10)
            
            # 等待对话框关闭
            self.root.wait_window(export_window)
            
            # 执行导出的函数
            def execute_export(result):
                if result is None:
                    return
                    
                data_list, export_type, format_type = result
                if data_list is None:
                    return
                
                # 打开文件保存对话框
                file_types = [
                    ("Excel文件", "*.xlsx"),
                    ("CSV文件", "*.csv"),
                    ("所有文件", "*.*")
                ] if format_type == "excel" else [
                    ("CSV文件", "*.csv"),
                    ("Excel文件", "*.xlsx"),
                    ("所有文件", "*.*")
                ]
                
                default_ext = ".xlsx" if format_type == "excel" else ".csv"
                filename = filedialog.asksaveasfilename(
                    defaultextension=default_ext,
                    filetypes=file_types,
                    title="保存计算结果"
                )
                
                if not filename:
                    return
                
                try:
                    if format_type == "excel" or filename.lower().endswith('.xlsx'):
                        # 使用我们的导出Excel方法
                        self._export_to_excel(filename, data_list)
                    else:
                        # 导出为CSV格式
                        self._export_to_csv(filename, data_list)
                except Exception as e:
                    messagebox.showerror("错误", f"导出失败：\n{str(e)}")
        
        except Exception as e:
            messagebox.showerror("错误", f"导出数据时出错：\n{str(e)}")
    
    def _export_to_excel(self, filename, data):
        """将数据导出为Excel格式，支持单个数据字典或数据列表，并设置自适应列宽"""
        try:
            # 尝试导入pandas
            import pandas as pd
            
            # 确保data是列表格式
            data_list = data if isinstance(data, list) else [data]
            
            if not data_list:
                raise Exception("没有数据可导出")
            
            # 创建DataFrame
            df = pd.DataFrame(data_list)
            
            # 导出到Excel
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
                
                # 获取工作表
                worksheet = writer.sheets['Sheet1']
                
                # 设置列宽自适应
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)  # 限制最大宽度为50
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            messagebox.showinfo("成功", f"数据已成功导出到\n{filename}")
            
        except ImportError:
            # 如果没有安装pandas，降级到CSV格式
            csv_filename = filename.replace('.xlsx', '.csv')
            self._export_to_csv(csv_filename, data)
            messagebox.showinfo("提示", f"未安装pandas库，已将数据导出为CSV格式到\n{csv_filename}")
            
        except Exception as e:
            raise Exception(f"导出Excel失败：{str(e)}")
    
    def _export_to_csv(self, filename, data):
        """将数据导出为CSV格式，支持单个数据字典或数据列表"""
        try:
            import csv
            # 确保data是列表格式
            data_list = data if isinstance(data, list) else [data]
            
            if not data_list:
                raise Exception("没有数据可导出")
                
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                # 使用第一个数据项的键作为字段名
                fieldnames = data_list[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                # 写入所有数据行
                for row in data_list:
                    writer.writerow(row)
            messagebox.showinfo("成功", f"数据已成功导出到\n{filename}")
        except Exception as e:
            raise Exception(f"导出CSV失败：{str(e)}")
    
    def batch_process(self):
        """批量导入产品信息进行费用计算"""
        try:
            # 创建批量处理窗口
            batch_window = tk.Toplevel(self.root)
            batch_window.title("批量处理")
            batch_window.geometry("600x500")
            batch_window.transient(self.root)
            batch_window.grab_set()
            
            # 创建说明标签
            info_frame = ttk.Frame(batch_window)
            info_frame.pack(fill=tk.X, pady=10, padx=10)
            
            ttk.Label(info_frame, text="批量导入产品信息进行FBA费用计算", font=('微软雅黑', 12, 'bold')).pack(pady=5)
            ttk.Label(info_frame, text="支持Excel (.xlsx) 和 CSV (.csv) 格式文件", font=('微软雅黑', 10)).pack(pady=2)
            ttk.Label(info_frame, text="文件需包含：重量(g)、最长边(cm)、次长边(cm)、最短边(cm) 列", font=('微软雅黑', 10)).pack(pady=2)
            
            # 创建进度条
            progress_frame = ttk.Frame(batch_window)
            progress_frame.pack(fill=tk.X, pady=10, padx=10)
            
            progress_var = tk.DoubleVar()
            progress_bar = ttk.Progressbar(progress_frame, variable=progress_var, maximum=100)
            progress_bar.pack(fill=tk.X, side=tk.LEFT, expand=True)
            
            progress_label = ttk.Label(progress_frame, text="0%")
            progress_label.pack(side=tk.RIGHT, padx=10)
            
            # 创建结果文本框
            result_frame = ttk.Frame(batch_window)
            result_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
            
            ttk.Label(result_frame, text="处理结果:", font=('微软雅黑', 10)).pack(anchor=tk.W)
            
            result_text = tk.Text(result_frame, wrap=tk.WORD, height=10, font=self.default_font)
            result_text.pack(fill=tk.BOTH, expand=True)
            
            # 添加滚动条
            scrollbar = ttk.Scrollbar(result_text, command=result_text.yview)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            result_text.config(yscrollcommand=scrollbar.set)
            
            # 创建按钮框架
            button_frame = ttk.Frame(batch_window)
            button_frame.pack(fill=tk.X, pady=10, padx=10)
            
            # 定义下载模板函数
            def download_template():
                try:
                    # 创建示例数据
                    template_data = [
                        {'产品名称': '示例产品1', '重量(g)': 100, '最长边(cm)': 10, '次长边(cm)': 8, '最短边(cm)': 5},
                        {'产品名称': '示例产品2', '重量(g)': 500, '最长边(cm)': 15, '次长边(cm)': 10, '最短边(cm)': 8},
                        {'产品名称': '示例产品3', '重量(g)': 2000, '最长边(cm)': 30, '次长边(cm)': 20, '最短边(cm)': 15}
                    ]
                    
                    # 询问保存格式
                    format_window = tk.Toplevel(batch_window)
                    format_window.title("选择模板格式")
                    format_window.geometry("300x200")
                    format_window.transient(batch_window)
                    format_window.grab_set()
                    
                    ttk.Label(format_window, text="请选择模板文件格式：", font=self.default_font).pack(pady=20)
                    
                    format_var = tk.StringVar(value="excel")
                    
                    format_frame = ttk.Frame(format_window)
                    format_frame.pack(pady=10)
                    ttk.Radiobutton(format_frame, text="Excel格式 (.xlsx)", variable=format_var, value="excel").pack(anchor=tk.W, padx=20, pady=5)
                    ttk.Radiobutton(format_frame, text="CSV格式 (.csv)", variable=format_var, value="csv").pack(anchor=tk.W, padx=20, pady=5)
                    
                    def save_template():
                        format_type = format_var.get()
                        format_window.destroy()
                        
                        # 打开文件保存对话框
                        default_ext = ".xlsx" if format_type == "excel" else ".csv"
                        filename = filedialog.asksaveasfilename(
                            defaultextension=default_ext,
                            filetypes=[("所有文件", "*.*")],
                            title="保存模板文件"
                        )
                        
                        if not filename:
                            return
                        
                        try:
                                if format_type == "excel":
                                    # 尝试使用pandas导出Excel，如果失败则自动降级到CSV
                                    try:
                                        import pandas as pd
                                        df = pd.DataFrame(template_data)
                                        with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                                            df.to_excel(writer, index=False)
                                        messagebox.showinfo("成功", f"模板文件已保存到\n{filename}")
                                    except ImportError:
                                        # 自动降级到CSV格式，避免显示错误信息
                                        csv_filename = filename.replace('.xlsx', '.csv')
                                        import csv
                                        with open(csv_filename, 'w', newline='', encoding='utf-8-sig') as f:
                                            fieldnames = list(template_data[0].keys())
                                            writer = csv.DictWriter(f, fieldnames=fieldnames)
                                            writer.writeheader()
                                            for data in template_data:
                                                writer.writerow(data)
                                        messagebox.showinfo("提示", f"已自动创建CSV模板文件\n{csv_filename}")
                                else:
                                    # 导出为CSV格式
                                    import csv
                                with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                                    fieldnames = list(template_data[0].keys())
                                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                                    writer.writeheader()
                                    for data in template_data:
                                        writer.writerow(data)
                                messagebox.showinfo("成功", f"模板文件已保存到\n{filename}")
                        except Exception as e:
                            messagebox.showerror("错误", f"保存模板文件失败：\n{str(e)}")
                    
                    button_frame_template = ttk.Frame(format_window)
                    button_frame_template.pack(pady=10)
                    ttk.Button(button_frame_template, text="确定", command=save_template).pack(side=tk.LEFT, padx=10)
                    ttk.Button(button_frame_template, text="取消", command=format_window.destroy).pack(side=tk.LEFT, padx=10)
                    
                except Exception as e:
                    messagebox.showerror("错误", f"创建模板文件时出错：\n{str(e)}")
            
            # 导入文件按钮
            def import_file():
                try:
                    # 打开文件选择对话框
                    file_types = [
                        ("Excel文件", "*.xlsx"),
                        ("CSV文件", "*.csv"),
                        ("所有文件", "*.*")
                    ]
                    
                    filename = filedialog.askopenfilename(
                        filetypes=file_types,
                        title="选择产品信息文件"
                    )
                    
                    if not filename:
                        return
                    
                    # 清空结果文本
                    result_text.delete(1.0, tk.END)
                    result_text.insert(tk.END, f"开始处理文件: {filename}\n")
                    result_text.update()
                    
                    # 根据文件扩展名选择处理方式
                    if filename.lower().endswith('.xlsx'):
                        process_excel_file(filename)
                    elif filename.lower().endswith('.csv'):
                        process_csv_file(filename)
                    else:
                        messagebox.showerror("错误", "不支持的文件格式，请选择Excel或CSV文件")
                
                except Exception as e:
                    messagebox.showerror("错误", f"导入文件时出错：\n{str(e)}")
            
            # 按钮将在函数末尾创建
            
            # 处理Excel文件
            def process_excel_file(filename):
                try:
                    # 尝试导入pandas
                    import pandas as pd
                    
                    # 读取Excel文件
                    try:
                        df = pd.read_excel(filename)
                    except Exception as excel_error:
                        # 如果读取Excel失败，尝试提示用户转成CSV格式
                        result_text.insert(tk.END, f"读取Excel文件失败：{str(excel_error)}\n")
                        result_text.insert(tk.END, "尝试将Excel文件转换为CSV格式...\n")
                        result_text.update()
                        
                        # 提示用户手动转换或尝试其他方法
                        if messagebox.askyesno("Excel读取失败", "无法读取Excel文件。这可能是由于缺少必要的依赖项。\n\n是否要尝试将Excel文件转换为CSV格式并继续处理？"):
                            # 尝试使用临时CSV文件路径
                            import tempfile
                            import csv
                            import os
                            
                            try:
                                # 创建临时CSV文件
                                csv_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.csv', encoding='utf-8-sig')
                                csv_temp.close()
                                
                                # 尝试使用pandas转换格式
                                try:
                                    df = pd.read_excel(filename)
                                    df.to_csv(csv_temp.name, index=False, encoding='utf-8-sig')
                                    result_text.insert(tk.END, "成功将Excel文件转换为CSV格式\n")
                                    result_text.update()
                                    # 使用CSV处理函数处理转换后的文件
                                    process_csv_file(csv_temp.name)
                                    # 删除临时文件
                                    os.unlink(csv_temp.name)
                                    return
                                except Exception as convert_error:
                                    result_text.insert(tk.END, f"转换失败：{str(convert_error)}\n")
                                    os.unlink(csv_temp.name)
                                    messagebox.showinfo("提示", "请手动将Excel文件另存为CSV格式，然后选择CSV文件进行处理。")
                                    return
                            except Exception as temp_error:
                                result_text.insert(tk.END, f"创建临时文件失败：{str(temp_error)}\n")
                                messagebox.showinfo("提示", "请手动将Excel文件另存为CSV格式，然后选择CSV文件进行处理。")
                                return
                        else:
                            return
                    
                    # 检查必要的列是否存在
                    required_columns = ['重量(g)', '最长边(cm)', '次长边(cm)', '最短边(cm)']
                    missing_columns = [col for col in required_columns if col not in df.columns]
                    
                    if missing_columns:
                        messagebox.showerror("错误", f"文件缺少必要的列：{', '.join(missing_columns)}")
                        return
                    
                    # 处理每一行数据
                    results = []
                    total_rows = len(df)
                    
                    for index, row in df.iterrows():
                        try:
                            # 更新进度条
                            progress = (index + 1) / total_rows * 100
                            progress_var.set(progress)
                            progress_label.config(text=f"{int(progress)}%")
                            batch_window.update()
                            
                            # 提取数据
                            # 创建默认的column_map
                            column_map = {}
                            # 使用映射的列名或直接使用原始列名
                            weight_g = float(row[column_map.get('重量(g)', '重量(g)')])
                            length_cm = float(row[column_map.get('最长边(cm)', '最长边(cm)')])
                            width_cm = float(row[column_map.get('次长边(cm)', '次长边(cm)')])
                            height_cm = float(row[column_map.get('最短边(cm)', '最短边(cm)')])
                            
                            # 计算费用
                            calc_result = self.calculate_fba_fee(weight_g, length_cm, width_cm, height_cm)
                            
                            # 保存结果
                            result_dict = {
                                '重量(g)': weight_g,
                                '最长边(cm)': length_cm,
                                '次长边(cm)': width_cm,
                                '最短边(cm)': height_cm,
                                '尺寸分段': calc_result['size_tier'],
                                '重量': calc_result['weight_display'],
                                '长度+围长': calc_result['girth_display'],
                                '配送费': calc_result['fee']
                            }
                            
                            # 添加原始数据中的其他列
                            for col in df.columns:
                                if col not in required_columns:
                                    result_dict[col] = row[col]
                            
                            results.append(result_dict)
                            
                            # 显示处理结果
                            result_text.insert(tk.END, f"处理行 {index + 1}/{total_rows}: 成功\n")
                            result_text.see(tk.END)
                            result_text.update()
                            
                        except Exception as e:
                            result_text.insert(tk.END, f"处理行 {index + 1}/{total_rows}: 失败 - {str(e)}\n")
                            result_text.see(tk.END)
                            result_text.update()
                    
                    # 完成后保存结果
                    if results:
                        # 询问是否保存结果
                        if messagebox.askyesno("完成", f"成功处理 {len(results)}/{total_rows} 条数据\n是否保存结果到文件？"):
                            save_results(results)
                
                except ImportError:
                    # 如果导入pandas失败，建议用户使用CSV格式
                    result_text.insert(tk.END, "未找到pandas库，无法处理Excel文件\n")
                    messagebox.showinfo("提示", "未安装pandas和openpyxl库。请将Excel文件另存为CSV格式，然后选择CSV文件进行处理。")
                except Exception as e:
                    # 捕获其他可能的错误
                    result_text.insert(tk.END, f"处理Excel文件时出错：{str(e)}\n")
                    result_text.insert(tk.END, "尝试将Excel文件另存为CSV格式可能会解决此问题\n")
                    messagebox.showerror("错误", f"处理Excel文件时出错：\n{str(e)}\n\n请尝试将Excel文件另存为CSV格式，然后选择CSV文件进行处理。")
            
            # 处理CSV文件
            def process_csv_file(filename):
                try:
                    # 定义必要的列名，确保在所有代码路径中都可用
                    required_columns = ['重量(g)', '最长边(cm)', '次长边(cm)', '最短边(cm)']
                    
                    # 读取CSV文件 - 尝试多种编码格式
                    import csv
                    # 常见的CSV编码格式列表，按优先级排序
                    encodings = ['utf-8-sig', 'gbk', 'cp936', 'cp1252', 'latin-1']
                    rows = None
                    used_encoding = None
                    
                    # 尝试不同的编码格式
                    for encoding in encodings:
                        try:
                            with open(filename, 'r', encoding=encoding) as f:
                                reader = csv.DictReader(f)
                                rows = list(reader)
                            used_encoding = encoding
                            break
                        except UnicodeDecodeError:
                            continue
                    
                    # 如果所有编码都失败
                    if rows is None:
                        raise UnicodeDecodeError('UTF-8', b'', 0, 1, '无法识别文件编码，请尝试使用Excel将文件另存为CSV UTF-8格式')
                    
                    # 检查必要的列是否存在
                    if not rows:
                        messagebox.showerror("错误", "CSV文件为空")
                        return
                    
                    # 获取实际的列名并进行清理（去除空格和其他可能的干扰字符）
                    actual_columns = {col.strip() for col in rows[0].keys()}
                    
                    # 定义必要列的映射，支持多种可能的列名变体
                    column_mappings = {
                        '重量(g)': ['重量(g)', '重量', 'weight'],
                        '最长边(cm)': ['最长边(cm)', '最长边', 'length', '长'],
                        '次长边(cm)': ['次长边(cm)', '次长边', 'width', '宽'],
                        '最短边(cm)': ['最短边(cm)', '最短边', 'height', '高']
                    }
                    
                    # 尝试匹配列名
                    column_map = {}
                    missing_columns = []
                    
                    for req_col, possible_names in column_mappings.items():
                        found = False
                        for actual_col in actual_columns:
                            # 不区分大小写进行匹配，并且考虑部分匹配
                            actual_lower = actual_col.lower()
                            for possible in possible_names:
                                possible_lower = possible.lower()
                                if possible_lower in actual_lower or actual_lower in possible_lower:
                                    column_map[req_col] = actual_col
                                    found = True
                                    break
                            if found:
                                break
                        if not found:
                            missing_columns.append(req_col)
                    
                    if missing_columns:
                        # 尝试使用原始逻辑再次检查，确保向后兼容性
                        original_missing = [col for col in required_columns if col not in rows[0]]
                        if original_missing:
                            messagebox.showerror("错误", f"文件缺少必要的列：{', '.join(original_missing)}")
                            return
                    
                    # 处理每一行数据
                    results = []
                    total_rows = len(rows)
                    
                    for index, row in enumerate(rows):
                        try:
                            # 更新进度条
                            progress = (index + 1) / total_rows * 100
                            progress_var.set(progress)
                            progress_label.config(text=f"{int(progress)}%")
                            batch_window.update()
                            
                            # 提取数据 - 使用column_map进行正确的列名映射
                            weight_g = float(row[column_map.get('重量(g)', '重量(g)')])
                            length_cm = float(row[column_map.get('最长边(cm)', '最长边(cm)')])
                            width_cm = float(row[column_map.get('次长边(cm)', '次长边(cm)')])
                            height_cm = float(row[column_map.get('最短边(cm)', '最短边(cm)')])
                            
                            # 计算费用
                            calc_result = self.calculate_fba_fee(weight_g, length_cm, width_cm, height_cm)
                            
                            # 保存结果
                            result_dict = {
                                '重量(g)': weight_g,
                                '最长边(cm)': length_cm,
                                '次长边(cm)': width_cm,
                                '最短边(cm)': height_cm,
                                '尺寸分段': calc_result['size_tier'],
                                '重量': calc_result['weight_display'],
                                '长度+围长': calc_result['girth_display'],
                                '配送费': calc_result['fee']
                            }
                            
                            # 添加原始数据中的其他列
                            for col in row:
                                if col not in required_columns:
                                    result_dict[col] = row[col]
                            
                            results.append(result_dict)
                            
                            # 显示处理结果
                            result_text.insert(tk.END, f"处理行 {index + 1}/{total_rows}: 成功\n")
                            result_text.see(tk.END)
                            result_text.update()
                            
                        except Exception as e:
                            result_text.insert(tk.END, f"处理行 {index + 1}/{total_rows}: 失败 - {str(e)}\n")
                            result_text.see(tk.END)
                            result_text.update()
                    
                    # 完成后保存结果
                    if results:
                        # 询问是否保存结果
                        if messagebox.askyesno("完成", f"成功处理 {len(results)}/{total_rows} 条数据\n是否保存结果到文件？"):
                            save_results(results)
                
                except Exception as e:
                    messagebox.showerror("错误", f"处理CSV文件时出错：\n{str(e)}")
            
            # 保存结果
            def save_results(results):
                try:
                    # 打开文件保存对话框
                    file_types = [
                        ("Excel文件", "*.xlsx"),
                        ("CSV文件", "*.csv"),
                        ("所有文件", "*.*")
                    ]
                    
                    default_ext = ".xlsx"
                    filename = filedialog.asksaveasfilename(
                        defaultextension=default_ext,
                        filetypes=file_types,
                        title="保存处理结果"
                    )
                    
                    if not filename:
                        return
                    
                    if filename.lower().endswith('.xlsx'):
                        # 尝试使用pandas导出Excel
                        try:
                            import pandas as pd
                            df = pd.DataFrame(results)
                            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                                df.to_excel(writer, index=False)
                            messagebox.showinfo("成功", f"结果已成功保存到\n{filename}")
                        except ImportError:
                            # 如果没有安装pandas，降级到CSV格式
                            save_to_csv(filename.replace('.xlsx', '.csv'), results)
                    else:
                        # 导出为CSV格式
                        save_to_csv(filename, results)
                
                except Exception as e:
                    messagebox.showerror("错误", f"保存结果时出错：\n{str(e)}")
            
            # 保存到CSV文件
            def save_to_csv(filename, results):
                try:
                    import csv
                    with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                        if results:
                            fieldnames = list(results[0].keys())
                            writer = csv.DictWriter(f, fieldnames=fieldnames)
                            writer.writeheader()
                            for data in results:
                                writer.writerow(data)
                    messagebox.showinfo("成功", f"结果已成功保存到\n{filename}")
                except Exception as e:
                    messagebox.showerror("错误", f"保存CSV文件失败：\n{str(e)}")
            

            
            # 添加按钮 - 确保只创建一组按钮
            # 先清空按钮框架，避免重复创建
            for widget in button_frame.winfo_children():
                widget.destroy()
                
            import_btn = ttk.Button(button_frame, text="导入文件", command=import_file, style="Accent.TButton")
            import_btn.pack(side=tk.LEFT, padx=10)
            
            template_btn = ttk.Button(button_frame, text="下载模板", command=download_template, style="Accent.TButton")
            template_btn.pack(side=tk.LEFT, padx=10)
            
            close_btn = ttk.Button(button_frame, text="关闭", command=batch_window.destroy, style="Accent.TButton")
            close_btn.pack(side=tk.RIGHT, padx=10)
            
        except Exception as e:
            messagebox.showerror("错误", f"批量处理时出错：\n{str(e)}")
    
    def calculate_fee_with_steps(self, size_segment, weight_lb, weight_oz, weight_unit):
        """
        计算配送费用并返回详细计算过程
        """
        steps = []
        
        # 记录基本信息
        steps.append(f"1. 根据尺寸分段 '{size_segment}' 计算费用")
        
        # 小号标准尺寸（盎司）
        if size_segment == "小号标准尺寸":
            steps.append("   - 小号标准尺寸费用计算规则（按盎司）:")
            if weight_oz <= 2:
                fee = 3.06
                steps.append(f"   - 当前重量 {weight_oz:.2f} 盎司 ≤ 2盎司，适用费率: $3.06")
            elif weight_oz <= 4:
                fee = 3.15
                steps.append(f"   - 当前重量 2盎司 < {weight_oz:.2f} 盎司 ≤ 4盎司，适用费率: $3.15")
            elif weight_oz <= 6:
                fee = 3.24
                steps.append(f"   - 当前重量 4盎司 < {weight_oz:.2f} 盎司 ≤ 6盎司，适用费率: $3.24")
            elif weight_oz <= 8:
                fee = 3.33
                steps.append(f"   - 当前重量 6盎司 < {weight_oz:.2f} 盎司 ≤ 8盎司，适用费率: $3.33")
            elif weight_oz <= 10:
                fee = 3.43
                steps.append(f"   - 当前重量 8盎司 < {weight_oz:.2f} 盎司 ≤ 10盎司，适用费率: $3.43")
            elif weight_oz <= 12:
                fee = 3.53
                steps.append(f"   - 当前重量 10盎司 < {weight_oz:.2f} 盎司 ≤ 12盎司，适用费率: $3.53")
            elif weight_oz <= 14:
                fee = 3.60
                steps.append(f"   - 当前重量 12盎司 < {weight_oz:.2f} 盎司 ≤ 14盎司，适用费率: $3.60")
            elif weight_oz <= 16:
                fee = 3.65
                steps.append(f"   - 当前重量 14盎司 < {weight_oz:.2f} 盎司 ≤ 16盎司，适用费率: $3.65")
            else:
                fee = "重量区间不匹配"
                steps.append(f"   - 错误: {weight_oz:.2f} 盎司超出小号标准尺寸范围")
        
        # 大号标准尺寸
        elif size_segment == "大号标准尺寸":
            steps.append("   - 大号标准尺寸费用计算规则:")
            if weight_unit == '盎司':
                steps.append(f"   - 当前使用单位: 盎司 ({weight_oz:.2f} 盎司)")
                if weight_oz <= 4:
                    fee = 3.68
                    steps.append(f"   - 当前重量 {weight_oz:.2f} 盎司 ≤ 4盎司，适用费率: $3.68")
                elif weight_oz <= 8:
                    fee = 3.90
                    steps.append(f"   - 当前重量 4盎司 < {weight_oz:.2f} 盎司 ≤ 8盎司，适用费率: $3.90")
                elif weight_oz <= 12:
                    fee = 4.15
                    steps.append(f"   - 当前重量 8盎司 < {weight_oz:.2f} 盎司 ≤ 12盎司，适用费率: $4.15")
                elif weight_oz <= 16:
                    fee = 4.55
                    steps.append(f"   - 当前重量 12盎司 < {weight_oz:.2f} 盎司 ≤ 16盎司，适用费率: $4.55")
                elif 24 < weight_oz <= 28:
                    fee = 4.55
                    steps.append(f"   - 当前重量 24盎司 < {weight_oz:.2f} 盎司 ≤ 28盎司，适用费率: $4.55")
                else:
                    steps.append(f"   - 重量超出盎司区间，转换为磅计算 ({weight_lb:.2f} 磅)")
                    fee = self.calculate_large_standard_fee_by_lb(weight_lb)
                    steps.extend(self.get_large_standard_calculation_steps(weight_lb))
            else:
                steps.append(f"   - 当前使用单位: 磅 ({weight_lb:.2f} 磅)")
                fee = self.calculate_large_standard_fee_by_lb(weight_lb)
                steps.extend(self.get_large_standard_calculation_steps(weight_lb))
        
        # 大号大件
        elif size_segment == "大号大件":
            steps.append("   - 大号大件费用计算规则:")
            base_fee = 9.61
            per_lb_fee = 0.38
            steps.append(f"   - 基础费用: ${base_fee:.2f}")
            steps.append(f"   - 每磅额外费用: ${per_lb_fee:.2f}")
            fee = round(base_fee + max(0, weight_lb) * per_lb_fee, 2)
            steps.append(f"   - 计算公式: ${base_fee:.2f} + {weight_lb:.2f} 磅 × ${per_lb_fee:.2f}/磅 = ${fee:.2f}")
        
        # 超大件：0至50磅
        elif size_segment == "超大件：0至50磅":
            steps.append("   - 超大件(0至50磅)费用计算规则:")
            base_fee = 26.33
            per_lb_fee = 0.38
            steps.append(f"   - 基础费用: ${base_fee:.2f}")
            steps.append(f"   - 每磅额外费用: ${per_lb_fee:.2f}")
            fee = round(base_fee + max(0, weight_lb) * per_lb_fee, 2)
            steps.append(f"   - 计算公式: ${base_fee:.2f} + {weight_lb:.2f} 磅 × ${per_lb_fee:.2f}/磅 = ${fee:.2f}")
        
        # 超大件：50至70磅
        elif size_segment == "超大件：50至70磅（不含50磅）":
            steps.append("   - 超大件(50至70磅)费用计算规则:")
            base_fee = 40.12
            per_lb_fee = 0.75
            steps.append(f"   - 基础费用: ${base_fee:.2f}")
            steps.append(f"   - 超出50磅部分每磅额外费用: ${per_lb_fee:.2f}")
            additional_weight = max(0, weight_lb - 51)
            fee = round(base_fee + additional_weight * per_lb_fee, 2)
            steps.append(f"   - 超出重量: {additional_weight:.2f} 磅")
            steps.append(f"   - 计算公式: ${base_fee:.2f} + {additional_weight:.2f} 磅 × ${per_lb_fee:.2f}/磅 = ${fee:.2f}")
        
        # 超大件：70至150磅
        elif size_segment == "超大件：70至150磅（不含70磅）":
            steps.append("   - 超大件(70至150磅)费用计算规则:")
            base_fee = 54.81
            per_lb_fee = 0.75
            steps.append(f"   - 基础费用: ${base_fee:.2f}")
            steps.append(f"   - 超出70磅部分每磅额外费用: ${per_lb_fee:.2f}")
            additional_weight = max(0, weight_lb - 71)
            fee = round(base_fee + additional_weight * per_lb_fee, 2)
            steps.append(f"   - 超出重量: {additional_weight:.2f} 磅")
            steps.append(f"   - 计算公式: ${base_fee:.2f} + {additional_weight:.2f} 磅 × ${per_lb_fee:.2f}/磅 = ${fee:.2f}")
        
        # 超大件：150磅以上
        elif size_segment == "超大件：150磅以上（不含150磅）":
            steps.append("   - 超大件(150磅以上)费用计算规则:")
            base_fee = 194.95
            per_lb_fee = 0.19
            steps.append(f"   - 基础费用: ${base_fee:.2f}")
            steps.append(f"   - 超出150磅部分每磅额外费用: ${per_lb_fee:.2f}")
            additional_weight = max(0, weight_lb - 151)
            fee = round(base_fee + additional_weight * per_lb_fee, 2)
            steps.append(f"   - 超出重量: {additional_weight:.2f} 磅")
            steps.append(f"   - 计算公式: ${base_fee:.2f} + {additional_weight:.2f} 磅 × ${per_lb_fee:.2f}/磅 = ${fee:.2f}")
        
        else:
            fee = "无法计算配送费"
            steps.append(f"   - 错误: 无法识别的尺寸分段 '{size_segment}'")
        
        # 添加最终结果
        steps.append(f"\n2. 最终配送费用: ${fee}")
        
        # 返回费用和计算步骤
        return fee, "\n".join(steps)
    
    def get_large_standard_calculation_steps(self, weight_lb):
        """
        获取大号标准尺寸按磅计算的详细步骤
        """
        steps = []
        
        if weight_lb <= 1:
            steps.append(f"   - 当前重量 {weight_lb:.2f} 磅 ≤ 1磅，适用费率: $3.68")
        elif weight_lb <= 1.25:
            steps.append(f"   - 当前重量 1磅 < {weight_lb:.2f} 磅 ≤ 1.25磅，适用费率: $4.99")
        elif weight_lb <= 1.5:
            steps.append(f"   - 当前重量 1.25磅 < {weight_lb:.2f} 磅 ≤ 1.5磅，适用费率: $5.37")
        elif weight_lb <= 1.75:
            steps.append(f"   - 当前重量 1.5磅 < {weight_lb:.2f} 磅 ≤ 1.75磅，适用费率: $5.52")
        elif weight_lb <= 2:
            steps.append(f"   - 当前重量 1.75磅 < {weight_lb:.2f} 磅 ≤ 2磅，适用费率: $5.77")
        elif weight_lb <= 2.25:
            steps.append(f"   - 当前重量 2磅 < {weight_lb:.2f} 磅 ≤ 2.25磅，适用费率: $5.87")
        elif weight_lb <= 2.5:
            steps.append(f"   - 当前重量 2.25磅 < {weight_lb:.2f} 磅 ≤ 2.5磅，适用费率: $6.05")
        elif weight_lb <= 2.75:
            steps.append(f"   - 当前重量 2.5磅 < {weight_lb:.2f} 磅 ≤ 2.75磅，适用费率: $6.21")
        elif weight_lb <= 3:
            steps.append(f"   - 当前重量 2.75磅 < {weight_lb:.2f} 磅 ≤ 3磅，适用费率: $6.62")
        elif weight_lb <= 20:
            base_fee = 6.92
            per_quarter_lb = 0.08
            additional_weight = weight_lb - 3
            additional_quarter_lbs = additional_weight * 4
            additional_fee = additional_quarter_lbs * per_quarter_lb
            total_fee = round(base_fee + additional_fee, 2)
            steps.append(f"   - 当前重量 3磅 < {weight_lb:.2f} 磅 ≤ 20磅")
            steps.append(f"   - 基础费用: ${base_fee:.2f}")
            steps.append(f"   - 超出3磅部分: {additional_weight:.2f} 磅")
            steps.append(f"   - 超出部分折合四分之一磅: {additional_quarter_lbs:.2f} 个")
            steps.append(f"   - 每个四分之一磅费用: ${per_quarter_lb:.2f}")
            steps.append(f"   - 超出部分费用: {additional_quarter_lbs:.2f} × ${per_quarter_lb:.2f} = ${additional_fee:.2f}")
            steps.append(f"   - 总费用: ${base_fee:.2f} + ${additional_fee:.2f} = ${total_fee:.2f}")
        else:
            steps.append(f"   - 错误: {weight_lb:.2f} 磅超出大号标准尺寸重量范围")
        
        return steps
    
    def create_weight_converter_ui(self):
        """创建独立的重量转换工具界面"""
        # 获取重量转换器框架
        frame = self.weight_converter_frame
        
        # 创建标题
        title_label = ttk.Label(
            frame, 
            text="重量单位转换器", 
            font=self.title_font
        )
        title_label.pack(pady=20)
        
        # 创建输入框架
        input_frame = ttk.LabelFrame(frame, text="转换设置", padding="20")
        input_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # 输入值
        value_frame = ttk.Frame(input_frame)
        value_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(value_frame, text="输入值:", width=10).pack(side=tk.LEFT, padx=5)
        
        self.weight_input_var = tk.StringVar(value="1")
        self.weight_input_entry = ttk.Entry(
            value_frame, 
            textvariable=self.weight_input_var, 
            width=15,
            justify=tk.RIGHT
        )
        self.weight_input_entry.pack(side=tk.LEFT, padx=5)
        
        # 源单位选择
        from_unit_frame = ttk.Frame(input_frame)
        from_unit_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(from_unit_frame, text="从单位:", width=10).pack(side=tk.LEFT, padx=5)
        
        self.from_unit_var = tk.StringVar(value="磅")
        units_frame = ttk.Frame(from_unit_frame)
        units_frame.pack(side=tk.LEFT)
        
        units = ["磅 (lb)", "盎司 (oz)", "克 (g)", "千克 (kg)"]
        unit_values = ["磅", "盎司"]
        
        for text, value in zip(units, unit_values):
            ttk.Radiobutton(
                units_frame, 
                text=text, 
                variable=self.from_unit_var, 
                value=value
            ).pack(side=tk.LEFT, padx=10)
        
        # 目标单位选择
        to_unit_frame = ttk.Frame(input_frame)
        to_unit_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(to_unit_frame, text="到单位:", width=10).pack(side=tk.LEFT, padx=5)
        
        self.to_unit_var = tk.StringVar(value="千克")
        to_units_frame = ttk.Frame(to_unit_frame)
        to_units_frame.pack(side=tk.LEFT)
        
        for text, value in zip(units, unit_values):
            ttk.Radiobutton(
                to_units_frame, 
                text=text, 
                variable=self.to_unit_var, 
                value=value
            ).pack(side=tk.LEFT, padx=10)
        
        # 转换按钮
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=20)
        
        self.convert_button = ttk.Button(
            button_frame, 
            text="转换重量", 
            command=self.convert_weight
        )
        self.convert_button.pack(padx=10)
        
        # 结果显示
        result_frame = ttk.LabelFrame(frame, text="转换结果", padding="20")
        result_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # 创建结果标签
        self.weight_result_var = tk.StringVar(value="请点击转换按钮")
        self.weight_result_label = ttk.Label(
            result_frame, 
            textvariable=self.weight_result_var,
            font=self.header_font,
            wraplength=600
        )
        self.weight_result_label.pack(pady=10)
        
        # 添加转换信息区域
        info_frame = ttk.LabelFrame(frame, text="转换信息", padding="20")
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        info_text = """
        常用重量单位转换关系：
        • 1 磅 = 16 盎司 = 453.59237 克 = 0.45359237 千克
        • 1 盎司 = 28.349523125 克
        • 1 千克 = 1000 克 = 35.2739619 盎司 = 2.20462262 磅
        """
        
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack(anchor=tk.W)
    
    def convert_weight(self):
        """执行重量单位转换计算"""
        try:
            # 获取输入值和单位
            input_value = float(self.weight_input_var.get())
            from_unit = self.from_unit_var.get()
            to_unit = self.to_unit_var.get()
            
            # 如果单位相同，直接显示结果
            if from_unit == to_unit:
                self.weight_result_var.set(f"{input_value} {from_unit} = {input_value} {to_unit}")
                return
            
            # 首先将所有单位转换为克进行中间计算
            if from_unit == "磅":
                weight_in_grams = input_value * 453.59237
            elif from_unit == "盎司":
                weight_in_grams = input_value * 28.349523125
            elif from_unit == "克":
                weight_in_grams = input_value
            elif from_unit == "千克":
                weight_in_grams = input_value * 1000
            else:
                weight_in_grams = input_value  # 默认不转换
            
            # 然后将克转换为目标单位
            if to_unit == "磅":
                converted_weight = weight_in_grams / 453.59237
            elif to_unit == "盎司":
                converted_weight = weight_in_grams / 28.349523125
            elif to_unit == "克":
                converted_weight = weight_in_grams
            elif to_unit == "千克":
                converted_weight = weight_in_grams / 1000
            else:
                converted_weight = weight_in_grams  # 默认不转换
            
            # 根据单位决定保留的小数位数
            if to_unit in ["磅", "千克"]:
                result_str = f"{converted_weight:.6f}"
            elif to_unit == "盎司":
                result_str = f"{converted_weight:.4f}"
            else:  # 克
                result_str = f"{converted_weight:.2f}"
            
            # 去除末尾多余的零和小数点
            result_str = result_str.rstrip('0').rstrip('.') if '.' in result_str else result_str
            
            # 更新结果显示
            self.weight_result_var.set(f"{input_value} {from_unit} = {result_str} {to_unit}")
            
        except ValueError:
            self.weight_result_var.set("错误：请输入有效的数字")
        except Exception as e:
            self.weight_result_var.set(f"转换错误：{str(e)}")

import sys
import logging
import os





# 确保在打包为可执行文件时能够正确找到路径
def resource_path(relative_path):
    """获取资源的绝对路径，支持PyInstaller打包"""
    try:
        # PyInstaller创建临时文件夹并设置_MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # 正常Python环境
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

# 配置日志，确保在打包环境中也能正常工作
try:
    # 尝试获取可执行文件所在目录
    if hasattr(sys, '_MEIPASS'):
        log_dir = sys._MEIPASS
    else:
        log_dir = os.path.dirname(os.path.abspath(__file__))
    log_file = os.path.join(log_dir, "fba_calculator.log")
except:
    # 如果获取目录失败，使用当前工作目录
    log_file = "fba_calculator.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

def run_app():
    try:
        logging.info("FBA配送费计算器启动")
        
        # 创建主窗口
        root = tk.Tk()
        
        # 设置窗口标题和基本属性
        root.title("FBA配送费计算器")
        
        # 设置中文字体支持（全局设置）
        try:
            if platform.system() == "Windows":
                # Windows系统使用微软雅黑
                root.option_add("*Font", "微软雅黑 10")
            else:
                # 非Windows系统使用通用字体
                root.option_add("*Font", "SimHei 10")
        except Exception as font_error:
            logging.warning(f"设置字体时出错: {str(font_error)}")
            # 如果字体设置失败，继续运行程序
        
        # 创建应用实例
        app = FBAShippingCalculator(root)
        
        # 窗口关闭时的处理
        def on_closing():
            logging.info("用户关闭窗口")
            root.destroy()
        
        root.protocol("WM_DELETE_WINDOW", on_closing)
        
        # 启动主循环
        root.mainloop()
        
        logging.info("FBA配送费计算器正常关闭")
        return 0
        
    except Exception as e:
        error_msg = f"程序运行出错: {str(e)}"
        logging.error(error_msg)
        
        # 显示错误消息
        try:
            # 尝试使用消息框显示错误
            import tkinter.messagebox as messagebox
            messagebox.showerror("程序错误", f"程序运行过程中出现错误：\n{str(e)}")
        except:
            # 如果无法显示图形界面错误，使用命令行
            print(f"错误: {str(e)}")
            try:
                input("按Enter键退出...")
            except:
                pass
        
        return 1
        units_frame = ttk.Frame(from_unit_frame)
        units_frame.pack(side=tk.LEFT)
        
        units = ["磅 (lb)", "盎司 (oz)", "克 (g)", "千克 (kg)"]
        unit_values = ["磅", "盎司", "克", "千克"]
        
        for text, value in zip(units, unit_values):
            ttk.Radiobutton(
                units_frame, 
                text=text, 
                variable=self.from_unit_var, 
                value=value
            ).pack(side=tk.LEFT, padx=10)
        
        # 目标单位选择
        to_unit_frame = ttk.Frame(input_frame)
        to_unit_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(to_unit_frame, text="到单位:", width=10).pack(side=tk.LEFT, padx=5)
        
        self.to_unit_var = tk.StringVar(value="千克")
        to_units_frame = ttk.Frame(to_unit_frame)
        to_units_frame.pack(side=tk.LEFT)
        
        for text, value in zip(units, unit_values):
            ttk.Radiobutton(
                to_units_frame, 
                text=text, 
                variable=self.to_unit_var, 
                value=value
            ).pack(side=tk.LEFT, padx=10)
        
        # 转换按钮
        button_frame = ttk.Frame(frame)
        button_frame.pack(pady=20)
        
        self.convert_button = ttk.Button(
            button_frame, 
            text="转换重量", 
            command=self.convert_weight
        )
        self.convert_button.pack(padx=10)
        
        # 结果显示
        result_frame = ttk.LabelFrame(frame, text="转换结果", padding="20")
        result_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # 创建结果标签
        self.weight_result_var = tk.StringVar(value="请点击转换按钮")
        self.weight_result_label = ttk.Label(
            result_frame, 
            textvariable=self.weight_result_var,
            font=self.header_font,
            wraplength=600
        )
        self.weight_result_label.pack(pady=10)
        
        # 添加转换信息区域
        info_frame = ttk.LabelFrame(frame, text="转换信息", padding="20")
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        info_text = """
        常用重量单位转换关系：
        • 1 磅 = 16 盎司 = 453.59237 克 = 0.45359237 千克
        • 1 盎司 = 28.349523125 克
        • 1 千克 = 1000 克 = 35.2739619 盎司 = 2.20462262 磅
        """
        
        ttk.Label(info_frame, text=info_text, justify=tk.LEFT).pack(anchor=tk.W)
    
    def convert_weight(self):
        """执行重量单位转换计算"""
        try:
            # 获取输入值和单位
            input_value = float(self.weight_input_var.get())
            from_unit = self.from_unit_var.get()
            to_unit = self.to_unit_var.get()
            
            # 如果单位相同，直接显示结果
            if from_unit == to_unit:
                self.weight_result_var.set(f"{input_value} {from_unit} = {input_value} {to_unit}")
                return
            
            # 首先将所有单位转换为克进行中间计算
            if from_unit == "磅":
                weight_in_grams = input_value * 453.59237
            elif from_unit == "盎司":
                weight_in_grams = input_value * 28.349523125
            elif from_unit == "克":
                weight_in_grams = input_value
            elif from_unit == "千克":
                weight_in_grams = input_value * 1000
            else:
                weight_in_grams = input_value  # 默认不转换
            
            # 然后将克转换为目标单位
            if to_unit == "磅":
                converted_weight = weight_in_grams / 453.59237
            elif to_unit == "盎司":
                converted_weight = weight_in_grams / 28.349523125
            elif to_unit == "克":
                converted_weight = weight_in_grams
            elif to_unit == "千克":
                converted_weight = weight_in_grams / 1000
            else:
                converted_weight = weight_in_grams  # 默认不转换
            
            # 根据单位决定保留的小数位数
            if to_unit in ["磅", "千克"]:
                result_str = f"{converted_weight:.6f}"
            elif to_unit == "盎司":
                result_str = f"{converted_weight:.4f}"
            else:  # 克
                result_str = f"{converted_weight:.2f}"
            
            # 去除末尾多余的零和小数点
            result_str = result_str.rstrip('0').rstrip('.') if '.' in result_str else result_str
            
            # 更新结果显示
            self.weight_result_var.set(f"{input_value} {from_unit} = {result_str} {to_unit}")
            
        except ValueError:
            self.weight_result_var.set("错误：请输入有效的数字")
        except Exception as e:
            self.weight_result_var.set(f"转换错误：{str(e)}")

if __name__ == "__main__":
    # 修复在某些环境下的编码问题
    try:
        if hasattr(sys.stdout, 'encoding') and sys.stdout.encoding != 'utf-8' and hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
    
    # 运行应用程序
    sys.exit(run_app())