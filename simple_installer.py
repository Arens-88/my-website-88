#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FBA费用计算器 - 简单安装程序
极简版本，无额外依赖
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
from datetime import datetime

class SimpleFBAInstaller:
    def __init__(self, root):
        self.root = root
        self.root.title("FBA费用计算器安装向导")
        self.root.geometry("600x400")
        self.root.resizable(False, False)
        
        # 设置中文字体
        self.set_chinese_font()
        
        # 默认安装路径
        self.default_install_path = os.path.join(os.environ["ProgramFiles"], "FBA费用计算器")
        self.install_path = tk.StringVar(value=self.default_install_path)
        
        # 进度条变量
        self.progress_var = tk.DoubleVar(value=0)
        self.status_var = tk.StringVar(value="准备安装...")
        
        # 选项变量
        self.create_shortcut_var = tk.BooleanVar(value=True)
        self.add_firewall_var = tk.BooleanVar(value=True)
        
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
        """创建主界面"""
        # 标题区域
        title_frame = ttk.Frame(self.root, padding="20")
        title_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(title_frame, text="FBA费用计算器安装向导", 
                               font=("SimHei", 16, "bold"))
        title_label.pack(anchor=tk.CENTER)
        
        # 内容区域
        content_frame = ttk.Frame(self.root, padding="20")
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 安装路径选择
        path_frame = ttk.LabelFrame(content_frame, text="安装位置", padding="10")
        path_frame.pack(fill=tk.X, pady=10)
        
        path_entry = ttk.Entry(path_frame, textvariable=self.install_path, width=50)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        browse_button = ttk.Button(path_frame, text="浏览...", command=self.browse_path)
        browse_button.pack(side=tk.RIGHT, padx=5)
        
        # 选项区域
        options_frame = ttk.LabelFrame(content_frame, text="安装选项", padding="10")
        options_frame.pack(fill=tk.X, pady=10)
        
        shortcut_check = ttk.Checkbutton(options_frame, text="创建桌面快捷方式", 
                                       variable=self.create_shortcut_var)
        shortcut_check.pack(anchor=tk.W, pady=5)
        
        firewall_check = ttk.Checkbutton(options_frame, text="添加防火墙例外规则", 
                                       variable=self.add_firewall_var)
        firewall_check.pack(anchor=tk.W, pady=5)
        
        # 进度区域
        progress_frame = ttk.Frame(content_frame)
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, 
                                          length=500, mode="determinate")
        self.progress_bar.pack(fill=tk.X)
        
        status_label = ttk.Label(content_frame, textvariable=self.status_var)
        status_label.pack(pady=5, anchor=tk.CENTER)
        
        # 按钮区域
        button_frame = ttk.Frame(self.root, padding="20")
        button_frame.pack(fill=tk.X)
        
        cancel_button = ttk.Button(button_frame, text="取消", command=self.cancel_install)
        cancel_button.pack(side=tk.RIGHT, padx=10)
        
        install_button = ttk.Button(button_frame, text="安装", command=self.start_installation)
        install_button.pack(side=tk.RIGHT, padx=10)
    
    def browse_path(self):
        """浏览安装路径"""
        path = filedialog.askdirectory(title="选择安装目录", 
                                     initialdir=self.install_path.get())
        if path:
            self.install_path.set(os.path.join(path, "FBA费用计算器"))
    
    def cancel_install(self):
        """取消安装"""
        if messagebox.askyesno("确认取消", "确定要取消安装吗？"):
            self.root.destroy()
    
    def start_installation(self):
        """开始安装"""
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
            if not os.path.exists(downloads_dir):
                os.makedirs(downloads_dir)
            
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
                shutil.copy2(main_exe_path, os.path.join(install_dir, "dist", "FBA费用计算器.exe"))
            else:
                raise Exception("未找到FBA费用计算器.exe文件")
            
            # 3. 创建快捷方式
            if self.create_shortcut_var.get():
                self.update_status("创建桌面快捷方式...")
                self.update_progress(60)
                self.create_shortcut(install_dir)
            
            # 4. 添加防火墙规则
            if self.add_firewall_var.get():
                self.update_status("设置防火墙规则...")
                self.update_progress(80)
                self.add_firewall_rule(install_dir)
            
            # 5. 创建卸载脚本
            self.create_uninstall_script(install_dir)
            
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
                f.write(f"sLinkFile = \"{shortcut_path}\\n")
                f.write("Set oLink = oWS.CreateShortcut(sLinkFile)\n")
                f.write(f"oLink.TargetPath = \"{target_exe}\\n")
                f.write(f"oLink.WorkingDirectory = \"{install_dir}\\n")
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
    installer = SimpleFBAInstaller(root)
    
    # 启动主循环
    root.mainloop()

if __name__ == "__main__":
    main()