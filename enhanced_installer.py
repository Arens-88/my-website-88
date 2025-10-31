#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FBA费用计算器 - 增强版安装程序
支持本地安装和自动更新功能
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import shutil
import subprocess
import ctypes
import threading
import time
import json
import urllib.request
import hashlib
from datetime import datetime

class EnhancedFBAInstaller:
    def __init__(self, root):
        self.root = root
        self.root.title("FBA费用计算器安装/更新向导")
        self.root.geometry("600x500")  # 增加窗口高度以确保所有控件可见
        self.root.resizable(False, False)
        
        # 设置中文字体
        self.set_chinese_font()
        
        # 默认安装路径
        self.default_install_path = os.path.join(os.environ["ProgramFiles"], "FBA费用计算器")
        self.install_path = tk.StringVar(value=self.default_install_path)
        
        # 进度条变量
        self.progress_var = tk.DoubleVar(value=0)
        self.status_var = tk.StringVar(value="准备就绪...")
        
        # 选项变量
        self.create_shortcut_var = tk.BooleanVar(value=True)
        self.add_firewall_var = tk.BooleanVar(value=True)
        self.auto_check_update_var = tk.BooleanVar(value=True)
        
        # 更新服务器信息
        self.update_info_url = "https://tomarens.xyz/update_info.json"
        self.current_version = "1.0.0"  # 安装程序版本
        self.update_info = None
        self.is_update_mode = False
        self.update_exe_path = None
        
        # 创建主界面
        self.create_main_window()
    
    def set_chinese_font(self):
        """设置中文字体支持"""
        try:
            default_font = tk.font.nametofont("TkDefaultFont")
            default_font.configure(family="SimHei", size=10)
            self.root.option_add("*Font", default_font)
        except:
            pass  # 使用系统默认字体
    
    def create_main_window(self):
        """创建主界面 - 完全重写布局以确保按钮可见"""
        # 设置窗口背景
        self.root.configure(padx=20, pady=20)
        
        # 标题标签 - 使用绝对定位
        title_label = ttk.Label(self.root, text="FBA费用计算器安装/更新向导", 
                               font=("SimHei", 16, "bold"))
        title_label.pack(fill=tk.X, pady=(0, 20))
        
        # 使用Canvas和Scrollbar创建可滚动区域
        canvas_frame = ttk.Frame(self.root)
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        canvas = tk.Canvas(canvas_frame, width=560, height=300)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # 创建内容框架，放入Canvas中
        content_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=content_frame, anchor="nw")
        
        # 安装路径选择
        path_frame = ttk.LabelFrame(content_frame, text="安装位置", padding="10", width=540)
        path_frame.pack(fill=tk.X, pady=(0, 10))
        
        path_entry = ttk.Entry(path_frame, textvariable=self.install_path, width=50)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        browse_button = ttk.Button(path_frame, text="浏览...", command=self.browse_path)
        browse_button.pack(side=tk.RIGHT, padx=5)
        
        # 选项区域
        options_frame = ttk.LabelFrame(content_frame, text="选项", padding="10", width=540)
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        shortcut_check = ttk.Checkbutton(options_frame, text="创建桌面快捷方式", 
                                       variable=self.create_shortcut_var)
        shortcut_check.pack(anchor=tk.W, pady=5)
        
        firewall_check = ttk.Checkbutton(options_frame, text="添加防火墙例外规则", 
                                       variable=self.add_firewall_var)
        firewall_check.pack(anchor=tk.W, pady=5)
        
        update_check = ttk.Checkbutton(options_frame, text="启动时自动检查更新", 
                                     variable=self.auto_check_update_var)
        update_check.pack(anchor=tk.W, pady=5)
        
        # 更新检查按钮
        check_update_frame = ttk.Frame(content_frame, width=540)
        check_update_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.check_update_button = ttk.Button(check_update_frame, text="检查更新", 
                                            command=self.check_for_updates)
        self.check_update_button.pack(side=tk.LEFT, padx=5)
        
        self.update_status_var = tk.StringVar(value="")
        update_status_label = ttk.Label(check_update_frame, textvariable=self.update_status_var)
        update_status_label.pack(side=tk.LEFT, padx=10)
        
        # 进度区域
        progress_frame = ttk.Frame(content_frame, width=540)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                          length=520, mode="determinate")
        self.progress_bar.pack(fill=tk.X)
        
        status_label = ttk.Label(content_frame, textvariable=self.status_var)
        status_label.pack(pady=5, anchor=tk.CENTER)
        
        # 配置Canvas的滚动区域
        def on_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        content_frame.bind("<Configure>", on_configure)
        
        # 按钮区域 - 使用固定高度的框架确保始终可见
        button_frame = ttk.Frame(self.root, height=50)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        button_frame.pack_propagate(False)  # 防止框架收缩
        
        # 创建按钮容器，右对齐
        buttons_container = ttk.Frame(button_frame)
        buttons_container.pack(side=tk.RIGHT, pady=10)
        
        # 创建取消按钮
        cancel_button = ttk.Button(buttons_container, text="取消", command=self.cancel_install, width=10)
        cancel_button.pack(side=tk.RIGHT, padx=5)
        
        # 创建安装按钮
        self.action_button = ttk.Button(buttons_container, text="安装", command=self.start_installation, width=10)
        self.action_button.pack(side=tk.RIGHT, padx=5)
    
    def browse_path(self):
        """浏览安装路径"""
        path = filedialog.askdirectory(title="选择安装目录", 
                                     initialdir=self.install_path.get())
        if path:
            self.install_path.set(os.path.join(path, "FBA费用计算器"))
    
    def cancel_install(self):
        """取消安装/更新"""
        if messagebox.askyesno("确认取消", "确定要取消吗？"):
            self.root.destroy()
    
    def check_for_updates(self):
        """检查更新"""
        self.update_status_var.set("正在检查更新...")
        self.check_update_button.config(state=tk.DISABLED)
        
        # 在单独的线程中检查更新
        check_thread = threading.Thread(target=self._check_updates_worker)
        check_thread.daemon = True
        check_thread.start()
    
    def _check_updates_worker(self):
        """检查更新的工作线程"""
        try:
            # 首先尝试从本地文件检查更新信息
            local_update_info = os.path.join(os.path.dirname(os.path.abspath(__file__)), "update_info.json")
            if os.path.exists(local_update_info):
                with open(local_update_info, 'r', encoding='utf-8') as f:
                    self.update_info = json.load(f)
                self.root.after(0, lambda: self.update_status_var.set(f"找到本地更新信息: v{self.update_info.get('version')}"))
            else:
                # 如果本地文件不存在，尝试从服务器获取
                response = urllib.request.urlopen(self.update_info_url, timeout=10)
                data = response.read().decode('utf-8')
                self.update_info = json.loads(data)
                self.root.after(0, lambda: self.update_status_var.set(f"从服务器获取更新信息: v{self.update_info.get('version')}"))
            
            # 检查是否有新版本
            if self.update_info and 'version' in self.update_info:
                # 这里简化版本比较，实际应用中可能需要更复杂的比较逻辑
                if self._is_newer_version(self.update_info['version'], self.current_version):
                    def show_update_available():
                        result = messagebox.askyesno(
                            "发现新版本", 
                            f"发现新版本: v{self.update_info['version']}\n\n" +
                            f"发布说明: {self.update_info.get('release_notes', '无')}\n\n" +
                            "是否立即下载并更新？"
                        )
                        if result:
                            self.action_button.config(text="更新")
                            self.is_update_mode = True
                            self.start_update()
                    
                    self.root.after(0, show_update_available)
                else:
                    self.root.after(0, lambda: self.update_status_var.set("当前已是最新版本"))
            else:
                self.root.after(0, lambda: self.update_status_var.set("无法获取有效更新信息"))
        
        except urllib.error.URLError as e:
            self.root.after(0, lambda: self.update_status_var.set("网络连接失败，尝试使用本地更新..."))
            # 尝试使用本地备份的更新信息
            self._try_local_update_backup()
        except Exception as e:
            self.root.after(0, lambda: self.update_status_var.set(f"检查更新失败: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.check_update_button.config(state=tk.NORMAL))
    
    def _try_local_update_backup(self):
        """尝试使用本地备份的更新信息"""
        backup_paths = [
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_update_info.json"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads", "update_info.json")
        ]
        
        for backup_path in backup_paths:
            if os.path.exists(backup_path):
                try:
                    with open(backup_path, 'r', encoding='utf-8') as f:
                        self.update_info = json.load(f)
                    self.root.after(0, lambda: self.update_status_var.set(f"使用备份更新信息: v{self.update_info.get('version')}"))
                    return
                except:
                    pass
        
        self.root.after(0, lambda: self.update_status_var.set("无可用更新信息"))
    
    def _is_newer_version(self, new_version, current_version):
        """比较版本号，判断是否为新版本"""
        try:
            # 简化的版本比较逻辑
            new_parts = [int(part) for part in new_version.split('.')]
            current_parts = [int(part) for part in current_version.split('.')]
            
            # 补齐长度
            max_len = max(len(new_parts), len(current_parts))
            new_parts.extend([0] * (max_len - len(new_parts)))
            current_parts.extend([0] * (max_len - len(current_parts)))
            
            # 逐位比较
            for i in range(max_len):
                if new_parts[i] > current_parts[i]:
                    return True
                elif new_parts[i] < current_parts[i]:
                    return False
            return False
        except:
            # 如果版本号格式不规范，假设是新版本
            return True
    
    def start_update(self):
        """开始更新过程"""
        # 禁用按钮
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Button):
                        child.config(state=tk.DISABLED)
        
        # 启动更新线程
        update_thread = threading.Thread(target=self.update)
        update_thread.daemon = True
        update_thread.start()
    
    def start_installation(self):
        """开始安装过程"""
        # 禁用按钮
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Button):
                        child.config(state=tk.DISABLED)
        
        # 启动安装线程
        install_thread = threading.Thread(target=self.install)
        install_thread.daemon = True
        install_thread.start()
    
    def update(self):
        """执行更新过程"""
        try:
            install_dir = self.install_path.get()
            
            # 确保安装目录存在
            if not os.path.exists(install_dir):
                self.update_status("安装目录不存在，将进行完整安装...")
                self.install()
                return
            
            # 1. 下载更新文件
            self.update_status("正在下载更新文件...")
            self.update_progress(20)
            
            # 确定下载URL
            download_url = self.update_info.get('download_url', '')
            
            # 创建downloads目录
            downloads_dir = os.path.join(install_dir, "downloads")
            if not os.path.exists(downloads_dir):
                os.makedirs(downloads_dir)
            
            # 下载文件
            self.update_exe_path = os.path.join(downloads_dir, "FBA费用计算器_update.exe")
            
            # 尝试多种下载方式
            download_success = False
            
            # 方式1: 直接从URL下载
            if download_url and download_url.startswith(('http://', 'https://')):
                try:
                    def report_progress(count, block_size, total_size):
                        percent = int(count * block_size * 100 / total_size)
                        if percent <= 100:
                            self.root.after(0, lambda: self.progress_var.set(20 + percent * 0.5))
                    
                    urllib.request.urlretrieve(download_url, self.update_exe_path, reporthook=report_progress)
                    download_success = True
                except Exception as e:
                    self.update_status(f"直接下载失败，尝试备用方式: {str(e)}")
            
            # 方式2: 检查本地是否已有更新文件
            if not download_success:
                local_candidate = os.path.join(os.path.dirname(os.path.abspath(__file__)), "FBA费用计算器.exe")
                if os.path.exists(local_candidate):
                    shutil.copy2(local_candidate, self.update_exe_path)
                    download_success = True
                    self.update_progress(70)
            
            # 方式3: 检查dist目录
            if not download_success:
                dist_candidate = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist", "FBA费用计算器.exe")
                if os.path.exists(dist_candidate):
                    shutil.copy2(dist_candidate, self.update_exe_path)
                    download_success = True
                    self.update_progress(70)
            
            if not download_success:
                raise Exception("无法获取更新文件，请检查网络连接或手动下载")
            
            # 2. 验证下载的文件
            self.update_status("验证更新文件...")
            self.update_progress(80)
            
            if not os.path.exists(self.update_exe_path) or os.path.getsize(self.update_exe_path) < 1024 * 1024:  # 至少1MB
                raise Exception("更新文件无效或损坏")
            
            # 3. 替换主程序文件
            self.update_status("正在应用更新...")
            self.update_progress(90)
            
            # 创建更新批处理脚本
            update_bat_path = os.path.join(downloads_dir, "apply_update.bat")
            target_exe = os.path.join(install_dir, "FBA费用计算器.exe")
            
            with open(update_bat_path, "w") as f:
                f.write("@echo off\n")
                f.write("echo 正在应用更新...\n")
                f.write("echo 等待程序关闭...\n")
                f.write("ping 127.0.0.1 -n 3 > nul\n")
                f.write(f"move /Y \"{self.update_exe_path}\" \"{target_exe}\"\n")
                f.write(f"copy /Y \"{target_exe}\" \"{downloads_dir}\FBA费用计算器.exe\"\n")
                f.write(f"copy /Y \"{target_exe}\" \"{install_dir}\dist\FBA费用计算器.exe\"\n")
                f.write("echo 更新应用完成！\n")
                f.write(f"echo 正在启动程序...\n")
                f.write(f"start \"\" \"{target_exe}\"\n")
                f.write("exit\n")
            
            # 4. 完成更新
            self.update_status("更新完成！准备重启程序...")
            self.update_progress(100)
            
            # 显示完成消息
            def show_complete():
                messagebox.showinfo("更新完成", "FBA费用计算器已成功更新！程序将自动重启。")
                # 启动更新批处理脚本
                subprocess.Popen([update_bat_path], shell=True)
                self.root.destroy()
            
            self.root.after(1000, show_complete)
            
        except Exception as e:
            def show_error():
                messagebox.showerror("更新失败", f"更新过程中出错：{str(e)}")
                self.root.destroy()
            
            self.root.after(0, show_error)
    
    def install(self):
        """执行安装过程"""
        try:
            install_dir = self.install_path.get()
            
            # 1. 创建安装目录
            self.update_status("创建安装目录...")
            self.update_progress(10)
            
            if not os.path.exists(install_dir):
                os.makedirs(install_dir)
            
            # 创建必要的子目录
            downloads_dir = os.path.join(install_dir, "downloads")
            dist_dir = os.path.join(install_dir, "dist")
            
            if not os.path.exists(downloads_dir):
                os.makedirs(downloads_dir)
            
            if not os.path.exists(dist_dir):
                os.makedirs(dist_dir)
            
            # 2. 复制主程序文件
            self.update_status("复制程序文件...")
            self.update_progress(30)
            
            # 查找主程序文件
            exe_sources = [
                "dist/FBA费用计算器.exe",
                "FBA费用计算器.exe",
                "../FBA费用计算器.exe"
            ]
            
            main_exe_path = None
            for source in exe_sources:
                if os.path.exists(source):
                    main_exe_path = source
                    break
            
            if main_exe_path:
                # 复制到主目录
                target_exe = os.path.join(install_dir, "FBA费用计算器.exe")
                shutil.copy2(main_exe_path, target_exe)
                
                # 复制到downloads目录（用于更新功能）
                shutil.copy2(main_exe_path, os.path.join(downloads_dir, "FBA费用计算器.exe"))
                shutil.copy2(main_exe_path, os.path.join(dist_dir, "FBA费用计算器.exe"))
            else:
                raise Exception("未找到FBA费用计算器.exe文件")
            
            # 3. 保存更新配置
            self.update_status("配置更新设置...")
            self.update_progress(50)
            
            # 保存更新信息文件
            if self.update_info:
                with open(os.path.join(downloads_dir, "update_info.json"), 'w', encoding='utf-8') as f:
                    json.dump(self.update_info, f, ensure_ascii=False, indent=4)
            
            # 保存配置文件
            config = {
                "auto_check_update": self.auto_check_update_var.get(),
                "update_info_url": self.update_info_url,
                "last_update_check": datetime.now().isoformat(),
                "version": self.current_version
            }
            
            with open(os.path.join(install_dir, "settings.json"), 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
            
            # 4. 创建快捷方式
            if self.create_shortcut_var.get():
                self.update_status("创建桌面快捷方式...")
                self.update_progress(60)
                self.create_shortcut(install_dir)
            
            # 5. 添加防火墙规则
            if self.add_firewall_var.get():
                self.update_status("设置防火墙规则...")
                self.update_progress(80)
                self.add_firewall_rule(install_dir)
            
            # 6. 创建卸载脚本和更新脚本
            self.create_uninstall_script(install_dir)
            self.create_update_script(install_dir)
            
            # 完成安装
            self.update_status("安装完成！")
            self.update_progress(100)
            
            # 显示完成消息
            def show_complete():
                if messagebox.askyesno("安装完成", "FBA费用计算器已成功安装！\n是否立即运行程序？"):
                    try:
                        subprocess.Popen(os.path.join(install_dir, "FBA费用计算器.exe"))
                    except:
                        messagebox.showwarning("启动失败", "无法启动程序，请手动运行安装目录中的可执行文件。")
                self.root.destroy()
            
            self.root.after(1000, show_complete)
            
        except Exception as e:
            def show_error():
                messagebox.showerror("安装失败", f"安装过程中出错：{str(e)}")
                self.root.destroy()
            
            self.root.after(0, show_error)
    
    def update_status(self, status):
        """更新状态文本"""
        self.root.after(0, lambda: self.status_var.set(status))
    
    def update_progress(self, value):
        """更新进度条"""
        self.root.after(0, lambda: self.progress_var.set(value))
    
    def create_shortcut(self, install_dir):
        """创建桌面快捷方式"""
        try:
            # 使用批处理方式创建快捷方式
            desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
            shortcut_path = os.path.join(desktop, "FBA费用计算器.lnk")
            target_exe = os.path.join(install_dir, "FBA费用计算器.exe")
            
            # 创建一个临时的vbs脚本
            vbs_script = os.path.join(install_dir, "create_shortcut.vbs")
            with open(vbs_script, "w") as f:
                f.write(f"Set oWS = WScript.CreateObject(\"WScript.Shell\")\n")
                f.write(f"sLinkFile = \"{shortcut_path}\"\n")
                f.write("Set oLink = oWS.CreateShortcut(sLinkFile)\n")
                f.write(f"oLink.TargetPath = \"{target_exe}\"\n")
                f.write(f"oLink.WorkingDirectory = \"{install_dir}\"\n")
                f.write("oLink.Description = \"FBA费用计算器\"\n")
                f.write("oLink.Save\n")
            
            # 运行vbs脚本
            subprocess.run(["cscript", "//nologo", vbs_script], shell=True)
            
            # 删除临时脚本
            if os.path.exists(vbs_script):
                os.remove(vbs_script)
                
        except Exception as e:
            # 如果失败，创建批处理文件作为备选
            desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
            bat_path = os.path.join(desktop, "运行FBA费用计算器.bat")
            with open(bat_path, "w") as f:
                f.write(f"@echo off\n")
                f.write(f'start "" "{os.path.join(install_dir, "FBA费用计算器.exe")}"\n')
    
    def add_firewall_rule(self, install_dir):
        """添加防火墙规则"""
        try:
            exe_path = os.path.join(install_dir, "FBA费用计算器.exe")
            
            # 构建命令
            cmd = f'netsh advfirewall firewall add rule name="FBA费用计算器" dir=in action=allow program="{exe_path}" enable=yes profile=any'
            
            # 检查是否以管理员权限运行
            if self.is_admin():
                # 直接运行命令
                subprocess.run(cmd, shell=True, capture_output=True)
            else:
                # 创建一个批处理文件让用户以管理员身份运行
                bat_path = os.path.join(install_dir, "添加防火墙规则.bat")
                with open(bat_path, "w") as f:
                    f.write(f"@echo off\n")
                    f.write("echo 正在添加防火墙规则...\n")
                    f.write(f"{cmd}\n")
                    f.write("echo 防火墙规则添加完成！\n")
                    f.write("pause\n")
        except:
            pass  # 防火墙规则添加失败不影响安装
    
    def create_uninstall_script(self, install_dir):
        """创建卸载脚本"""
        try:
            uninstall_script = os.path.join(install_dir, "卸载FBA费用计算器.bat")
            with open(uninstall_script, "w") as f:
                f.write("@echo off\n")
                f.write("echo 正在卸载FBA费用计算器...\n")
                f.write("echo 删除桌面快捷方式...\n")
                f.write("del \"%USERPROFILE%\\Desktop\\FBA费用计算器.lnk\" > nul 2>&1\n")
                f.write("del \"%USERPROFILE%\\Desktop\\运行FBA费用计算器.bat\" > nul 2>&1\n")
                f.write("echo 删除防火墙规则...\n")
                f.write('netsh advfirewall firewall delete rule name="FBA费用计算器" > nul 2>&1\n')
                f.write("echo 删除程序文件...\n")
                f.write(f'ping 127.0.0.1 -n 2 > nul\n')  # 延迟
                f.write(f'start /b cmd /c "ping 127.0.0.1 -n 3 > nul && rmdir /s /q \"{install_dir}\""\n')
                f.write("echo 卸载完成！\n")
                f.write("exit\n")
        except:
            pass
    
    def create_update_script(self, install_dir):
        """创建手动更新脚本"""
        try:
            update_script = os.path.join(install_dir, "检查更新.bat")
            current_exe = os.path.abspath(sys.argv[0])
            
            with open(update_script, "w") as f:
                f.write("@echo off\n")
                f.write("echo 正在检查FBA费用计算器更新...\n")
                f.write(f'start "" "{current_exe}"\n')
                f.write("exit\n")
        except:
            pass
    
    def is_admin(self):
        """检查是否以管理员权限运行"""
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False

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
    
    # 创建安装程序实例
    installer = EnhancedFBAInstaller(root)
    
    # 启动主循环
    root.mainloop()

if __name__ == "__main__":
    main()