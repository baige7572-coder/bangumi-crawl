import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request as request
import io
import re
import os
import csv
import json
import threading
import sys
import math

# 适配EXE
def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# 创建保存文件夹到桌面
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
save_dir = os.path.join(desktop_path, "BGM收藏作品")
if not os.path.exists(save_dir):
    os.makedirs(save_dir)

# 下载网页内容函数
def download(url: str):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        req = request.Request(url, headers=headers)
        response = request.urlopen(req, timeout=30)
        textIOWrapper = io.TextIOWrapper(buffer=response, encoding="UTF-8")
        html = textIOWrapper.read()
        return html
    except Exception as e:
        raise Exception(f"网页下载失败：{str(e)}")

# 获取收藏页总页数
def get_total_pages(user_id):
    try:
        # 访问用户主页，获取收藏总数
        user_home_url = f'https://bangumi.tv/anime/list/{user_id}/collect'
        html = download(user_home_url)
        # 正则匹配看过数目
        count_regex = r'看过 \D*(\d+)'
        count_match = re.search(count_regex, html)
        if not count_match:
            raise Exception("未找到收藏总数，请检查用户ID或页面结构")
        total_collect = int(count_match.group(1))
        if total_collect == 0:
            return 1
        # 总页数，每页24个，向上取整
        items_per_page = 24
        total_pages = math.ceil(total_collect / items_per_page)
        return total_pages

    except Exception as e:
        raise Exception(f"获取总页数失败：{str(e)}")

# 核心爬取函数
def crawl_data(user_id, progress_bar, status_label):
    all_results = []
    try:
        total_pages = get_total_pages(user_id)
        status_label.config(text=f"探测到总页数：{total_pages}页，开始爬取...", foreground="blue")
        progress_bar.update()
    except Exception as e:
        status_label.config(text=f"获取总页数失败：{str(e)}", foreground="red")
        messagebox.showerror("爬取失败", str(e))
        return

    # 按自动获取的总页数分页爬取
    for page in range(1, total_pages + 1):
        # 更新进度条和状态
        progress_bar['value'] = (page / total_pages) * 100
        status_label.config(text=f"正在爬取第{page}/{total_pages}页...", foreground="blue")
        progress_bar.update()
        status_label.update()

        url = f'https://bgm.tv/anime/list/{user_id}/collect?orderby=rate&page={page}'
        try:
            html = download(url)
            # 匹配每个作品的完整容器
            item_regex = r'<li id="item_\d+" class="item.*?">(.*?)</li>'
            items = re.findall(item_regex, html, flags=re.DOTALL)
            page_results = []
            for item in items:
                # 提取作品名称、评分、收藏日期
                name_match = re.search(r'<a href="/subject/.*?" class="l">(.*?)</a>', item, flags=re.DOTALL)
                score_match = re.search(r'<span class="starlight stars(\d+)"></span>', item, flags=re.DOTALL)
                date_match = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日)', item, flags=re.DOTALL)
                # 空值兜底，避免条目丢失
                name = name_match.group(1).strip() if name_match else "未知名称"
                score = score_match.group(1) if score_match else "0"
                date = date_match.group(1).strip() if date_match else "未知日期"
                # 保留有名称的有效数据
                if name != "未知名称":
                    page_results.append((name, round(int(score), 10), date))
            all_results.extend(page_results)
        except Exception as e:
            status_label.config(text=f"第{page}页爬取失败：{str(e)}", foreground="orange")
            continue

    # 保存爬取数据
    if all_results:
        # 保存CSV文件
        csv_filename = f"用户{user_id}_收藏作品_共{total_pages}页.csv"
        csv_path = os.path.join(save_dir, csv_filename)
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["作品名称", "评分", "收藏日期"])
            writer.writerows(all_results)

        # 保存JSON文件
        json_filename = f"用户{user_id}_收藏作品_共{total_pages}页.json"
        json_path = os.path.join(save_dir, json_filename)
        json_data = [{"作品名称": n, "评分": s, "收藏日期": d} for n, s, d in all_results]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=4)

        # 生成统计分析TXT报告
        scores = [s for n, s, d in all_results if isinstance(s, (int, float))]  # 过滤非数字评分
        release_dates = [d for n, s, d in all_results]
        total_count = len(all_results)
        avg_score = round(sum(scores) / len(scores), 2) if scores else 0.0

        # 计算评分标准差
        if len(scores) < 2:
            std_score = 0.0
        else:
            variance = sum([(s - avg_score) ** 2 for s in scores]) / (len(scores) - 1)
            std_score = round(math.sqrt(variance), 2)

        # 统计各评分作品数量
        score_count = {}
        for s in scores:
            score_key = str(s)
            score_count[score_key] = score_count.get(score_key, 0) + 1
        sorted_score_count = sorted(score_count.items(), key=lambda x: float(x[0]), reverse=True)

        # 统计各年份收藏作品数量
        year_count = {}
        for date in release_dates:
            if date in ["无上映日期", "未知日期"]:
                continue
            year_match = re.search(r'(\d{4})', date)
            if year_match:
                year = year_match.group(1)
                year_count[year] = year_count.get(year, 0) + 1
        sorted_year_count = sorted(year_count.items(), key=lambda x: int(x[0]))

        # 统计前20%高评分作品的时间分布
        top_20_percent_num = max(1, int(total_count * 0.2))
        sorted_results = sorted(all_results, key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0, reverse=True)
        top_20_results = sorted_results[:top_20_percent_num]

        top_20_year_count = {}
        top_20_month_count = {}
        for n, s, d in top_20_results:
            if d in ["无上映日期", "未知日期"]:
                continue
            # 年份统计
            year_match = re.search(r'(\d{4})', d)
            if year_match:
                year = year_match.group(1)
                top_20_year_count[year] = top_20_year_count.get(year, 0) + 1
            # 月份统计（补零标准化）
            month_match = re.search(r'(\d{1,2})月|(\d{1,2})-(\d{1,2})', d)
            if month_match:
                month = month_match.group(1) or month_match.group(3)
                month = f"{int(month):02d}"
                top_20_month_count[month] = top_20_month_count.get(month, 0) + 1

        sorted_top_20_year = sorted(top_20_year_count.items(), key=lambda x: int(x[0]))
        sorted_top_20_month = sorted(top_20_month_count.items(), key=lambda x: int(x[0]))

        # 拼接TXT报告内容
        txt_content = f"""=== BGM收藏动画统计报告 ===
1. 基础数据
   成功爬取作品总数：{total_count} 部
   评分作品数：{len(scores)} 部
   平均评分：{avg_score} 分
   评分标准差：{std_score}
   爬取总页数：{total_pages} 页

2. 各评分作品数量
"""
        for score, count in sorted_score_count:
            txt_content += f"   {score}分：{count} 部\n"

        txt_content += f"""
3. 各年份收藏作品数量
"""
        for year, count in sorted_year_count:
            txt_content += f"   {year}年：{count} 部\n"
        if not sorted_year_count:
            txt_content += "   - 无有效年份数据\n"

        txt_content += f"""
4. 前20%高评分作品（共{top_20_percent_num}部）收藏时间分布
   4.1 年份分布
"""
        for year, count in sorted_top_20_year:
            txt_content += f"      {year}年：{count} 部\n"
        if not sorted_top_20_year:
            txt_content += "      - 无有效年份数据\n"

        txt_content += f"""   4.2 月份分布
"""
        for month, count in sorted_top_20_month:
            txt_content += f"      {month}月：{count} 部\n"
        if not sorted_top_20_month:
            txt_content += "      - 无有效月份数据\n"

        # 保存统计TXT文件
        txt_filename = f"用户{user_id}_收藏作品统计报告.txt"
        txt_path = os.path.join(save_dir, txt_filename)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(txt_content)

        # 爬取完成更新状态
        progress_bar['value'] = 100
        status_label.config(text=f"爬取完成！共{len(all_results)}条数据", foreground="green")
        messagebox.showinfo("爬取成功喵",
                            f"数据已保存到桌面「BGM收藏作品」文件夹！\n\n"
                            f"共爬取{total_pages}页，合计{len(all_results)}部作品\n\n"
                            f"CSV文件：{csv_filename}\n"
                            f"JSON文件：{json_filename}\n"
                            f"统计报告：{txt_filename}\n\n"
                            "点击「打开保存文件夹」可直接查看。")
    else:
        # 无数据返回处理
        progress_bar['value'] = 0
        status_label.config(text="爬取完成，但未获取到任何数据！", foreground="red")
        messagebox.warning("爬取警告", "未爬取到任何数据，请检查：\n1. 用户ID是否正确\n2. 网络是否正常（能否访问bgm.tv）\n3. 该用户是否有收藏动画")

# 启动爬取，按钮点击事件
def start_crawl(entry_user_id, progress_bar, status_label):
    # 仅校验用户ID非空
    user_id = entry_user_id.get().strip()
    if not user_id:
        messagebox.showerror("输入错误", "用户ID不能为空！\n（可从BGM个人主页URL中获取，例：https://bgm.tv/user/1005264 → ID为1005264）")
        return
    # 重置进度条
    progress_bar['value'] = 0
    # 多线程启动爬取
    crawl_thread = threading.Thread(target=crawl_data, args=(user_id, progress_bar, status_label))
    crawl_thread.daemon = True  # 主线程退出时子线程同步退出
    crawl_thread.start()

# 打开保存文件夹
def open_save_dir():
    if os.path.exists(save_dir):
        os.startfile(save_dir)
    else:
        messagebox.showinfo("提示", "文件夹尚未创建，请先爬取数据！")

# 构建可视化界面
def create_gui():
    root = tk.Tk()
    root.title("BGM收藏看过作品爬取工具 V2.1")
    root.geometry("500x300")
    root.resizable(False, False)  # 禁止缩放窗口

    # 界面样式优化（微软雅黑字体，统一风格）
    style = ttk.Style()
    style.configure("TLabel", font=("微软雅黑", 10))
    style.configure("TEntry", font=("微软雅黑", 10))
    style.configure("TButton", font=("微软雅黑", 10))
    style.configure("TProgressbar", height=10)

    # 标题标签
    title_label = ttk.Label(root, text="BGM用户收藏动画数据爬取", font=("微软雅黑", 14, "bold"))
    title_label.pack(pady=18)

    # 输入框框架
    input_frame = ttk.Frame(root)
    input_frame.pack(pady=5)

    # 用户ID输入框
    label_user_id = ttk.Label(input_frame, text="BGM用户ID：")
    label_user_id.grid(row=0, column=0, padx=10, pady=8, sticky="e")
    entry_user_id = ttk.Entry(input_frame, width=27)  # 加宽输入框提升体验
    entry_user_id.grid(row=0, column=1, padx=10, pady=8)
    entry_user_id.insert(0, "-")  # 设置默认测试ID

    # 开始爬取按钮
    btn_crawl = ttk.Button(root, text="开始爬取全部收藏",
                           command=lambda: start_crawl(entry_user_id, progress_bar, status_label))
    btn_crawl.pack(pady=10, ipadx=20, ipady=5)

    # 进度条
    progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate")
    progress_bar.pack(pady=5)

    # 状态提示标签
    status_label = ttk.Label(root, text="就绪 - 自动探测总页数并爬取", font=("微软雅黑", 9))
    status_label.pack(pady=5)

    # 辅助按钮框架（打开文件夹+关于）
    btn_frame = ttk.Frame(root)
    btn_frame.pack(pady=3)
    # 打开保存文件夹按钮
    btn_open_dir = ttk.Button(btn_frame, text="打开保存文件夹", command=open_save_dir)
    btn_open_dir.grid(row=0, column=0, padx=25)
    # 关于按钮
    def show_about():
        messagebox.showinfo("关于", "BGM收藏作品爬取工具 V2.1\n- 自动探测并爬取全部收藏页数\n- 支持CSV/JSON/统计TXT多格式保存\n- 防界面卡死/中文乱码/单页失败续爬\n适用于bgm.tv用户收藏动画数据爬取\n开发者：白鸽₍˄·͈༝·͈˄*₎◞ ̑̑")
    btn_about = ttk.Button(btn_frame, text="关于", command=show_about)
    btn_about.grid(row=0, column=1, padx=25)

    # 窗口居中显示-
    root.update_idletasks()
    x = (root.winfo_screenwidth() - root.winfo_width()) // 2
    y = (root.winfo_screenheight() - root.winfo_height()) // 2
    root.geometry(f"+{x}+{y}")

    # 启动主界面循环
    root.mainloop()

# 主程序入口
if __name__ == "__main__":
    create_gui()