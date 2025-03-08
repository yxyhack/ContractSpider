# ContractSpider - Smart Contract Address Crawler

[中文版本](#contractspider---智能合约地址爬虫)

ContractSpider is a specialized crawler tool designed to automatically extract Ethereum smart contract addresses from DApp and DeFi project websites. This tool uses advanced web analysis and artificial intelligence technology to identify and extract publicly available contract addresses and their contextual information.

## Features

- Automatically explores website structure, including documentation subdomains and sitemaps
- Intelligently identifies pages containing contract addresses
- Extracts Ethereum format contract addresses and their contextual information
- Filters blackhole addresses and invalid addresses
- Supports using OpenAI API for intelligent page analysis
- Supports batch processing of multiple website URLs
- Provides test mode for quick validation of a single URL
- Saves results in CSV format for easy subsequent analysis

## Installation Requirements

```bash
# Install dependencies
pip install requests beautifulsoup4 selenium webdriver-manager openai httpx keyring lxml
```

## Usage

### Basic Usage

```bash
# Crawl a single website
python main.py https://example.com

# Test mode - quickly check a single URL
python main.py --test https://example.com

# Batch process multiple URLs
python main.py --url_list_file urls.txt

# Specify output file
python main.py https://example.com --output results.csv
```

### Command Line Arguments

```
Arguments:
  url                   Website URL to crawl
  --test                Test mode
  --url_list_file URL_LIST_FILE
                        Path to a file containing multiple URLs, one per line
  --output OUTPUT, -o OUTPUT
                        Output CSV file path
  --openai-api-key OPENAI_API_KEY
                        OpenAI API key, if not provided, retrieves from keyring OPENAI_API_KEY_SILICON
  --openai-api-base OPENAI_API_BASE
                        OpenAI API base URL
  --openai-model OPENAI_MODEL
                        OpenAI model name (default: Qwen/Qwen2.5-7B-Instruct)
  --openai-max-tokens OPENAI_MAX_TOKENS
                        Maximum tokens for generated response (default: 4096)
  --openai-max-context OPENAI_MAX_CONTEXT
                        Maximum context length for the model (default: 4096)
  --openai-timeout OPENAI_TIMEOUT
                        API call timeout in seconds (default: 90)
```

## API Key Configuration

The tool supports two ways to provide the OpenAI API key:

1. Directly through command line parameter:
```bash
python main.py https://example.com --openai-api-key sk-your-api-key
```

2. Using keyring to store the API key:
```bash
python -c "import keyring; keyring.set_password('system', 'OPENAI_API_KEY_SILICON', 'your-api-key')"
```

If no API key is provided and it cannot be retrieved from keyring, the program will report an error and exit.

## Output Format

The program outputs a CSV file containing the following fields:
- Address: Extracted Ethereum contract address
- Context: Contextual text of the address on the page
- Source URL: Page URL where the address was found
- Chain: Chain information (default is "Unknown")
- Contract: Contract name (default is empty)

## Test Mode

Test mode is used to quickly validate the tool's ability to process a specific URL:

```bash
python main.py --test https://example.com
```

Test mode will:
1. Check if the URL is accessible
2. Attempt to extract Ethereum addresses from the page
3. Evaluate whether the page is a contract page
4. Display examples of found addresses and their context
5. If no addresses are found on the current page, it will try to explore possible documentation pages

## Batch Processing

To batch process multiple websites, create a text file with one URL per line:

```
https://example1.com
https://example2.com
https://example3.com
```

Then process using the following command:

```bash
python main.py --url_list_file urls.txt
```

## Notes

- The tool disables SSL verification by default to handle certificate issues on some websites
- It is recommended to install the lxml library for better XML parsing support: `pip install lxml`
- Crawling speed has random delays (2-6 seconds) to avoid triggering website anti-crawling mechanisms
- By default, it crawls a maximum of 5000 pages or extracts 3000 addresses

## License

[MIT License](LICENSE)

---

# ContractSpider - 智能合约地址爬虫

[English Version](#contractspider---smart-contract-address-crawler)

ContractSpider是一个专门用于从DApp和DeFi项目网站中自动提取以太坊智能合约地址的爬虫工具。该工具使用先进的网页分析和人工智能技术，能够识别并提取网站上公开的合约地址及其上下文信息。

## 功能特点

- 自动探索网站结构，包括文档子域名和站点地图
- 智能识别包含合约地址的页面
- 提取以太坊格式的合约地址及其上下文信息
- 过滤黑洞地址和无效地址
- 支持使用OpenAI API进行智能页面分析
- 支持批量处理多个网站URL
- 提供测试模式，用于快速验证单个URL
- 结果保存为CSV格式，方便后续分析

## 安装要求

```bash
# 安装依赖
pip install requests beautifulsoup4 selenium webdriver-manager openai httpx keyring lxml
```

## 使用方法

### 基本用法

```bash
# 爬取单个网站
python main.py https://example.com

# 测试模式 - 快速检查单个URL
python main.py --test https://example.com

# 批量处理多个URL
python main.py --url_list_file urls.txt

# 指定输出文件
python main.py https://example.com --output results.csv
```

### 命令行参数

```
参数:
  url                   要爬取的网站URL
  --test                测试模式
  --url_list_file URL_LIST_FILE
                        包含多个URL的文件路径，每行一个URL
  --output OUTPUT, -o OUTPUT
                        输出CSV文件路径
  --openai-api-key OPENAI_API_KEY
                        OpenAI API密钥，如果不提供则从keyring中获取OPENAI_API_KEY_SILICON
  --openai-api-base OPENAI_API_BASE
                        OpenAI API基础URL
  --openai-model OPENAI_MODEL
                        OpenAI模型名称 (默认: Qwen/Qwen2.5-7B-Instruct)
  --openai-max-tokens OPENAI_MAX_TOKENS
                        生成回复的最大token数 (默认: 4096)
  --openai-max-context OPENAI_MAX_CONTEXT
                        模型的最大上下文长度 (默认: 4096)
  --openai-timeout OPENAI_TIMEOUT
                        API调用超时时间(秒) (默认: 90)
```

## API密钥配置

工具支持两种方式提供OpenAI API密钥:

1. 通过命令行参数直接提供:
```bash
python main.py https://example.com --openai-api-key sk-your-api-key
```

2. 使用keyring存储API密钥:
```bash
python -c "import keyring; keyring.set_password('system', 'OPENAI_API_KEY_SILICON', '您的API密钥')"
```

如果未提供API密钥且无法从keyring获取，程序将报错并退出。

## 输出格式

程序输出CSV文件包含以下字段:
- Address: 提取的以太坊合约地址
- Context: 地址在页面中的上下文文本
- Source URL: 发现地址的页面URL
- Chain: 链信息(默认为"未知")
- Contract: 合约名称(默认为空)

## 测试模式

测试模式用于快速验证工具对特定URL的处理能力:

```bash
python main.py --test https://example.com
```

测试模式会:
1. 检查URL是否可访问
2. 尝试提取页面中的以太坊地址
3. 评估页面是否为合约页面
4. 显示找到的地址示例及其上下文
5. 如果当前页面未找到地址，会尝试探索可能的文档页面

## 批量处理

要批量处理多个网站，可以创建一个文本文件，每行包含一个URL:

```
https://example1.com
https://example2.com
https://example3.com
```

然后使用以下命令处理:

```bash
python main.py --url_list_file urls.txt
```

## 注意事项

- 工具默认禁用SSL验证，以处理某些网站的证书问题
- 建议安装lxml库以获得更好的XML解析支持: `pip install lxml`
- 爬取速度设置了随机延迟(2-6秒)，以避免触发网站的反爬机制
- 默认最多爬取5000个页面或提取3000个地址

## 许可证

[MIT License](LICENSE) 