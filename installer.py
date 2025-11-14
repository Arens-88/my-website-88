#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FBA费用计算器安装程序
功能：
1. 图形界面安装向导
2. 自定义安装路径
3. 自动添加防火墙规则
4. 创建桌面快捷方式
5. 安装进度显示
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import tkinter.font as tkfont
import os
import sys
import shutil
import subprocess
import ctypes
import threading
import time
from datetime import datetime
import webbrowser

# 设置中文支持
if sys.platform == 'win32':
    # 移除matplotlib依赖，使用系统默认字体支持中文
    pass

class FBAInstaller:
    def __init__(self, root):
        self.root = root
        self.root.title("FBA费用计算器安装向导")
        self.root.geometry("600x450")
        self.root.resizable(False, False)
        
        # 设置窗口图标
        try:
            self.root.iconbitmap(default="")  # 可以设置自定义图标
        except:
            pass
        
        # 设置窗口在屏幕中央
        self.center_window()
        
        # 安装程序版本
        self.installer_version = "1.3.4"
        
        # 默认安装路径
        self.default_install_path = os.path.join(os.environ["ProgramFiles"], "FBA费用计算器")
        self.install_path = tk.StringVar(value=self.default_install_path)
        
        # 站点选择
        self.selected_site = tk.StringVar(value="us")  # us或jp
        
        # 进度条变量
        self.progress_var = tk.DoubleVar(value=0)
        
        # 安装状态
        self.install_status = tk.StringVar(value="准备安装...")
        
        # 需要安装的文件列表 - 支持1.3.4版本
        self.files_to_install = [
            {"source": "downloads/FBA费用计算器_美国站.exe", "target": "FBA费用计算器_美国站.exe"},
            {"source": "downloads/FBA费用计算器_日本站.exe", "target": "FBA费用计算器_日本站.exe"},
            {"source": "downloads/update_info.json", "target": "update_info.json"},
            {"source": "version.json", "target": "version.json"}
        ]
        
        # 创建界面
        self.create_welcome_page()
    
    def center_window(self):
        """将窗口居中显示"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")
    
    def create_welcome_page(self):
        """创建欢迎页面"""
        # 清空当前窗口
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 创建标题
        title_frame = ttk.Frame(self.root)
        title_frame.pack(pady=30)
        
        title_label = ttk.Label(title_frame, text="欢迎使用FBA费用计算器安装向导", 
                               font=("SimHei", 16, "bold"))
        title_label.pack()
        
        version_label = ttk.Label(title_frame, text=f"安装程序版本: {self.installer_version}")
        version_label.pack(pady=5)
        
        # 创建内容区域
        content_frame = ttk.Frame(self.root)
        content_frame.pack(padx=50, fill=tk.BOTH, expand=True)
        
        # 显示功能介绍
        features_text = (
            "FBA费用计算器是一款专业的亚马逊FBA配送费用计算工具，具有以下功能：\n\n"
            "• FBA配送费计算 - 精确计算亚马逊FBA配送费用\n"
            "• 重量转换工具 - 支持多种重量单位之间的转换\n"
            "• 货币转换工具 - 实时汇率查询和转换\n"
            "• 主题切换功能 - 多种颜色主题可选\n"
            "• 自动更新功能 - 及时获取最新版本和功能"
        )
        
        features_label = ttk.Label(content_frame, text=features_text, 
                                 justify=tk.LEFT, wraplength=500)
        features_label.pack(fill=tk.BOTH, expand=True)
        
        # 创建按钮区域
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=20, fill=tk.X, padx=50)
        
        # 后退按钮（在欢迎页禁用）
        self.back_button = ttk.Button(button_frame, text="后退", state=tk.DISABLED, 
                                     command=self.back_page)
        self.back_button.pack(side=tk.LEFT, padx=10)
        
        # 取消按钮
        cancel_button = ttk.Button(button_frame, text="取消", 
                                 command=self.cancel_install)
        cancel_button.pack(side=tk.RIGHT, padx=10)
        
        # 下一步按钮
        next_button = ttk.Button(button_frame, text="下一步", 
                               command=self.show_install_path_page)
        next_button.pack(side=tk.RIGHT, padx=10)
    
    def show_install_path_page(self):
        """显示安装路径选择页面"""
        # 清空当前窗口
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 创建标题
        title_frame = ttk.Frame(self.root)
        title_frame.pack(pady=20)
        
        title_label = ttk.Label(title_frame, text="选择安装位置", 
                               font=("SimHei", 14, "bold"))
        title_label.pack()
        
        # 创建内容区域
        content_frame = ttk.Frame(self.root)
        content_frame.pack(padx=50, fill=tk.BOTH, expand=True)
        
        # 安装路径选择
        path_frame = ttk.Frame(content_frame)
        path_frame.pack(fill=tk.X, pady=10)
        
        path_label = ttk.Label(path_frame, text="安装到:")
        path_label.pack(side=tk.LEFT, padx=5)
        
        path_entry = ttk.Entry(path_frame, textvariable=self.install_path, width=50)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        browse_button = ttk.Button(path_frame, text="浏览...", 
                                 command=self.browse_install_path)
        browse_button.pack(side=tk.RIGHT, padx=5)
        
        # 站点选择
        site_frame = ttk.Frame(content_frame)
        site_frame.pack(anchor=tk.W, pady=10)
        
        ttk.Label(site_frame, text="选择版本:").pack(side=tk.LEFT, padx=5)
        
        us_radio = ttk.Radiobutton(site_frame, text="美国站", value="us", 
                                 variable=self.selected_site)
        us_radio.pack(side=tk.LEFT, padx=5)
        
        jp_radio = ttk.Radiobutton(site_frame, text="日本站", value="jp", 
                                 variable=self.selected_site)
        jp_radio.pack(side=tk.LEFT, padx=5)
        
        # 创建开始菜单快捷方式选项
        self.create_shortcut_var = tk.BooleanVar(value=True)
        shortcut_checkbox = ttk.Checkbutton(content_frame, 
                                         text="创建桌面快捷方式",
                                         variable=self.create_shortcut_var)
        shortcut_checkbox.pack(anchor=tk.W, pady=10)
        
        # 添加防火墙规则选项
        self.add_firewall_var = tk.BooleanVar(value=True)
        firewall_checkbox = ttk.Checkbutton(content_frame, 
                                         text="添加防火墙例外规则",
                                         variable=self.add_firewall_var)
        firewall_checkbox.pack(anchor=tk.W, pady=10)
        
        # 创建按钮区域
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=20, fill=tk.X, padx=50)
        
        # 后退按钮
        self.back_button = ttk.Button(button_frame, text="后退", 
                                     command=self.back_page)
        self.back_button.pack(side=tk.LEFT, padx=10)
        
        # 取消按钮
        cancel_button = ttk.Button(button_frame, text="取消", 
                                 command=self.cancel_install)
        cancel_button.pack(side=tk.RIGHT, padx=10)
        
        # 安装按钮
        install_button = ttk.Button(button_frame, text="安装", 
                                  command=self.show_install_progress_page)
        install_button.pack(side=tk.RIGHT, padx=10)
    
    def show_install_progress_page(self):
        """显示安装进度页面"""
        # 清空当前窗口
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 创建标题
        title_frame = ttk.Frame(self.root)
        title_frame.pack(pady=20)
        
        title_label = ttk.Label(title_frame, text="正在安装...", 
                               font=("SimHei", 14, "bold"))
        title_label.pack()
        
        # 创建内容区域
        content_frame = ttk.Frame(self.root)
        content_frame.pack(padx=50, fill=tk.BOTH, expand=True)
        
        # 进度条
        progress_frame = ttk.Frame(content_frame)
        progress_frame.pack(fill=tk.X, pady=20)
        
        progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                     length=500, mode="determinate")
        progress_bar.pack(fill=tk.X)
        
        # 状态标签
        status_label = ttk.Label(content_frame, textvariable=self.install_status)
        status_label.pack(pady=10)
        
        # 创建日志区域
        log_frame = ttk.LabelFrame(content_frame, text="安装日志")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_text = tk.Text(log_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 启动安装线程
        install_thread = threading.Thread(target=self.perform_installation)
        install_thread.daemon = True
        install_thread.start()
    
    def show_complete_page(self):
        """显示安装完成页面"""
        # 清空当前窗口
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # 创建标题
        title_frame = ttk.Frame(self.root)
        title_frame.pack(pady=30)
        
        title_label = ttk.Label(title_frame, text="安装完成！", 
                               font=("SimHei", 16, "bold"))
        title_label.pack()
        
        # 创建内容区域
        content_frame = ttk.Frame(self.root)
        content_frame.pack(padx=50, fill=tk.BOTH, expand=True)
        
        # 显示完成信息
        site_name = "美国站" if self.selected_site.get() == "us" else "日本站"
        exe_name = "FBA费用计算器_美国站.exe" if self.selected_site.get() == "us" else "FBA费用计算器_日本站.exe"
        
        complete_text = (
            f"FBA费用计算器-{site_name}已成功安装到您的电脑上。\n\n"
            f"安装位置: {self.install_path.get()}\n"
            f"桌面快捷方式: {'已创建' if self.create_shortcut_var.get() else '未创建'}\n"
            f"防火墙规则: {'已添加' if self.add_firewall_var.get() else '未添加'}\n\n"
            "您现在可以通过以下方式启动程序：\n"
            f"• 双击桌面上的快捷方式：FBA费用计算器_{site_name}.lnk\n"
            f"• 直接运行安装目录中的可执行文件：{exe_name}"
        )
        
        complete_label = ttk.Label(content_frame, text=complete_text, 
                                 justify=tk.LEFT, wraplength=500)
        complete_label.pack(fill=tk.BOTH, expand=True)
        
        # 运行程序选项
        self.run_program_var = tk.BooleanVar(value=True)
        run_checkbox = ttk.Checkbutton(content_frame, 
                                    text="安装完成后运行FBA费用计算器",
                                    variable=self.run_program_var)
        run_checkbox.pack(anchor=tk.W, pady=10)
        
        # 创建按钮区域
        button_frame = ttk.Frame(self.root)
        button_frame.pack(pady=20, fill=tk.X, padx=50)
        
        # 完成按钮
        finish_button = ttk.Button(button_frame, text="完成", 
                                 command=self.finish_installation)
        finish_button.pack(side=tk.RIGHT, padx=10)
    
    def browse_install_path(self):
        """浏览安装路径"""
        path = filedialog.askdirectory(title="选择安装目录", 
                                     initialdir=self.install_path.get())
        if path:
            self.install_path.set(os.path.join(path, "FBA费用计算器"))
    
    def back_page(self):
        """返回上一页"""
        # 根据当前显示的内容决定返回哪个页面
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Label) and child.cget("text") == "选择安装位置":
                        self.create_welcome_page()
                        return
        
        # 默认返回欢迎页
        self.create_welcome_page()
    
    def cancel_install(self):
        """取消安装"""
        if messagebox.askyesno("确认取消", "确定要取消安装吗？"):
            self.root.destroy()
    
    def log_message(self, message):
        """记录安装日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.root.after(0, lambda: self._update_log(log_entry))
    
    def _update_log(self, log_entry):
        """更新日志显示（在主线程中执行）"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def update_status(self, status):
        """更新安装状态"""
        self.root.after(0, lambda: self._update_status_text(status))
    
    def _update_status_text(self, status):
        """更新状态文本（在主线程中执行）"""
        self.install_status.set(status)
    
    def update_progress(self, progress):
        """更新进度条"""
        self.root.after(0, lambda: self._update_progress_value(progress))
    
    def _update_progress_value(self, progress):
        """更新进度值（在主线程中执行）"""
        self.progress_var.set(progress)
    
    def perform_installation(self):
        """执行安装过程"""
        try:
            # 创建安装目录
            install_dir = self.install_path.get()
            self.update_status("准备安装目录...")
            self.log_message(f"准备安装目录: {install_dir}")
            
            if not os.path.exists(install_dir):
                os.makedirs(install_dir)
                self.log_message(f"成功创建安装目录")
            else:
                self.log_message(f"安装目录已存在，将覆盖现有文件")
            
            # 创建downloads子目录
            downloads_dir = os.path.join(install_dir, "downloads")
            if not os.path.exists(downloads_dir):
                os.makedirs(downloads_dir)
                self.log_message(f"成功创建downloads目录")
            
            # 复制文件
            self.update_status("复制程序文件...")
            total_files = len(self.files_to_install)
            for i, file_info in enumerate(self.files_to_install):
                source_path = file_info["source"]
                target_path = os.path.join(install_dir, file_info["target"])
                
                # 确保目标目录存在
                target_dir = os.path.dirname(target_path)
                if target_dir and not os.path.exists(target_dir):
                    os.makedirs(target_dir)
                
                try:
                    if os.path.exists(source_path):
                        self.log_message(f"复制文件: {source_path} -> {target_path}")
                        shutil.copy2(source_path, target_path)
                        
                        # 更新进度
                        progress = (i + 1) / total_files * 70  # 文件复制占70%
                        self.update_progress(progress)
                    else:
                        self.log_message(f"警告: 源文件不存在: {source_path}")
                except Exception as e:
                    self.log_message(f"复制文件失败: {str(e)}")
            
            # 创建桌面快捷方式
            if self.create_shortcut_var.get():
                self.update_status("创建桌面快捷方式...")
                self.log_message("正在创建桌面快捷方式")
                self.create_desktop_shortcut()
                self.update_progress(80)
            
            # 添加防火墙规则
            if self.add_firewall_var.get():
                self.update_status("设置防火墙规则...")
                self.log_message("正在添加防火墙例外规则")
                self.add_firewall_rule()
                self.update_progress(90)
            
            # 创建卸载脚本
            self.update_status("创建卸载脚本...")
            self.log_message("正在创建卸载脚本")
            self.create_uninstall_script()
            self.update_progress(95)
            
            # 完成安装
            self.update_status("安装完成！")
            self.log_message("FBA费用计算器安装完成")
            self.update_progress(100)
            
            # 等待1秒后显示完成页面
            time.sleep(1)
            self.root.after(0, self.show_complete_page)
            
        except Exception as e:
            self.log_message(f"安装过程中出错: {str(e)}")
            self.update_status(f"安装失败: {str(e)}")
            
            def show_error():
                messagebox.showerror("安装失败", f"安装过程中出现错误：{str(e)}")
                self.root.destroy()
            
            self.root.after(0, show_error)
    
    def create_desktop_shortcut(self):
        """创建桌面快捷方式"""
        try:
            import winshell
            from win32com.client import Dispatch
            
            desktop = winshell.desktop()
            
            # 根据站点选择创建对应的快捷方式
            if self.selected_site.get() == "us":
                shortcut_name = "FBA费用计算器_美国站.lnk"
                exe_name = "FBA费用计算器_美国站.exe"
                description = "FBA费用计算器 - 美国站版本"
            else:
                shortcut_name = "FBA费用计算器_日本站.lnk"
                exe_name = "FBA费用计算器_日本站.exe"
                description = "FBA费用计算器 - 日本站版本"
            
            shortcut_path = os.path.join(desktop, shortcut_name)
            target_path = os.path.join(self.install_path.get(), exe_name)
            working_dir = self.install_path.get()
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.Targetpath = target_path
            shortcut.WorkingDirectory = working_dir
            shortcut.Description = description
            shortcut.IconLocation = target_path
            shortcut.Save()
            
            self.log_message(f"桌面快捷方式创建成功: {shortcut_path}")
            
        except Exception as e:
            self.log_message(f"创建桌面快捷方式失败: {str(e)}")
            # 尝试使用备用方法
            try:
                exe_name = "FBA费用计算器_美国站.exe" if self.selected_site.get() == "us" else "FBA费用计算器_日本站.exe"
                shortcut_content = f"@echo off\nstart \"\" \"{os.path.join(self.install_path.get(), exe_name)}\""
                bat_name = "运行FBA费用计算器_美国站.bat" if self.selected_site.get() == "us" else "运行FBA费用计算器_日本站.bat"
                bat_path = os.path.join(winshell.desktop(), bat_name)
                with open(bat_path, 'w', encoding='utf-8') as f:
                    f.write(shortcut_content)
                self.log_message(f"创建备用启动脚本: {bat_path}")
            except:
                pass
    
    def add_firewall_rule(self):
        """添加Windows防火墙规则"""
        try:
            # 检查是否以管理员权限运行
            if not self.is_admin():
                self.log_message("需要管理员权限才能添加防火墙规则")
                # 尝试以管理员身份重新运行命令
                exe_path = os.path.join(self.install_path.get(), "FBA费用计算器.exe")
                
                # 使用netsh命令添加防火墙规则
                cmd = f'netsh advfirewall firewall add rule name="FBA费用计算器" dir=in action=allow program="{exe_path}" enable=yes profile=any'
                
                # 尝试使用PowerShell以管理员身份运行
                powershell_cmd = f'powershell -Command "Start-Process cmd -ArgumentList \'/c {cmd}\' -Verb RunAs"'
                
                self.log_message(f"尝试以管理员身份添加防火墙规则")
                
                # 这里我们只记录命令，实际执行需要用户确认
                self.log_message(f"防火墙规则添加命令: {cmd}")
                self.log_message("请注意: 可能需要您手动确认防火墙规则的添加")
                
                return
            
            # 直接添加防火墙规则
            exe_path = os.path.join(self.install_path.get(), "FBA费用计算器.exe")
            
            # 使用netsh命令添加防火墙规则
            cmd = ['netsh', 'advfirewall', 'firewall', 'add', 'rule', 
                  'name="FBA费用计算器"', 'dir=in', 'action=allow', 
                  f'program="{exe_path}"', 'enable=yes', 'profile=any']
            
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            
            if result.returncode == 0:
                self.log_message("防火墙规则添加成功")
            else:
                self.log_message(f"添加防火墙规则失败: {result.stderr}")
                
        except Exception as e:
            self.log_message(f"添加防火墙规则时出错: {str(e)}")
    
    def create_uninstall_script(self):
        """创建卸载脚本"""
        try:
            uninstall_script = os.path.join(self.install_path.get(), "卸载FBA费用计算器.bat")
            
            # 创建卸载脚本内容
            uninstall_content = (
                '@echo off\n'
                'echo 正在卸载FBA费用计算器...\n'
                'echo.\n'
                'echo 1. 删除桌面快捷方式\n'
                'del "%USERPROFILE%\Desktop\FBA费用计算器.lnk" > nul 2>&1\n'
                'del "%USERPROFILE%\Desktop\运行FBA费用计算器.bat" > nul 2>&1\n'
                'echo.\n'
                'echo 2. 删除防火墙规则\n'
                'netsh advfirewall firewall delete rule name="FBA费用计算器" > nul 2>&1\n'
                'echo.\n'
                'echo 3. 删除程序文件\n'
                f'rmdir /s /q "{self.install_path.get()}"\n'
                'echo.\n'
                'echo 卸载完成！\n'
                'pause\n'
                'exit'
            )
            
            with open(uninstall_script, 'w', encoding='utf-8') as f:
                f.write(uninstall_content)
            
            self.log_message(f"卸载脚本创建成功: {uninstall_script}")
            
        except Exception as e:
            self.log_message(f"创建卸载脚本失败: {str(e)}")
    
    def is_admin(self):
        """检查是否以管理员权限运行"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    
    def finish_installation(self):
        """完成安装并退出"""
        # 如果选择运行程序
        if self.run_program_var.get():
            try:
                exe_name = "FBA费用计算器_美国站.exe" if self.selected_site.get() == "us" else "FBA费用计算器_日本站.exe"
                exe_path = os.path.join(self.install_path.get(), exe_name)
                subprocess.Popen(exe_path)
            except Exception as e:
                messagebox.showwarning("启动失败", f"无法启动FBA费用计算器: {str(e)}")
        
        # 退出安装程序
        self.root.destroy()

def main():
    # 检查是否以管理员权限运行
    if not ctypes.windll.shell32.IsUserAnAdmin():
        # 尝试以管理员权限重新运行
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        return
    
    # 创建主窗口
    root = tk.Tk()
    
    # 设置中文字体
    if sys.platform == 'win32':
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family="SimHei", size=10)
        root.option_add("*Font", default_font)
    
    # 创建安装程序实例
    installer = FBAInstaller(root)
    
    # 启动主循环
    root.mainloop()

if __name__ == "__main__":
    main()