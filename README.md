# bangumi-crawl
bangumi 网站用户收藏/看过动画条目爬取、导出及简单统计工具

## 功能
- 爬取指定用户的 bangumi 收藏/看过动画列表；
- 支持导出为 Excel/CSV 格式；
- 简单的数据分析（如评分统计、类型分布）。

## 使用方法
### 普通用户（无需编程基础）
1. 下载 Release 中的 `bgm_crawl_v2.0.exe`；
2. 双击运行，按照提示输入 bangumi 用户 ID/登录 cookie；
3. 等待爬取完成，结果会保存在程序同目录下。

### 开发者（需要 Python 环境）
1. 克隆仓库：`git clone https://github.com/baige7572-coder/bangumi-crawl.git`；
2. 安装依赖：`pip install -r requirements.txt`；
3. 运行代码：`python bgm_crawl.py`。

## 注意事项
- 请勿高频爬取，避免触发 bangumi 反爬机制；
- 需要登录 bangumi 账号获取 cookie（可选，部分数据需要登录后才能爬取）。
