#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import csv
import json
import logging
import os
import random
import re
import ssl
import sys
import time
import urllib.parse
import urllib3
import warnings
from typing import Dict, List, Set, Tuple, Optional, Union
import concurrent.futures

# 禁用SSL警告和证书验证
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
ssl._create_default_https_context = ssl._create_unverified_context
os.environ['WDM_SSL_VERIFY'] = '0'  # 为WebDriver Manager禁用SSL验证
os.environ['PYTHONHTTPSVERIFY'] = '0'  # 为Python HTTP客户端禁用SSL验证

import requests
# 全局禁用requests的SSL验证
requests.packages.urllib3.disable_warnings()
# 设置默认不验证SSL证书
old_merge_environment_settings = requests.Session.merge_environment_settings
def merge_environment_settings(self, url, proxies, stream, verify, cert):
    settings = old_merge_environment_settings(self, url, proxies, stream, verify, cert)
    settings['verify'] = False
    return settings
requests.Session.merge_environment_settings = merge_environment_settings

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import openai
import httpx
import keyring

# 尝试导入lxml解析器，如果不存在则记录警告
try:
    import lxml
    HAS_LXML = True
except ImportError:
    HAS_LXML = False
    warnings.warn("lxml库未安装，站点地图XML解析可能会失败。请安装lxml: pip install lxml")

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 以太坊地址正则表达式
ETH_ADDRESS_PATTERN = re.compile(r'0x[a-fA-F0-9]{40}\b')

# 合约页面相关关键字
CONTRACT_KEYWORDS = [
    # 基础合约术语
    'contract', 'address', 'deploy', 'deployment', 'deployed', 'smart contract',
    'mainnet', 'testnet', 'ethereum', 'blockchain', 'transaction',
    
    # 文档相关
    'developers', 'docs', 'doc', 'smart-contracts',
    
    # 合约类型
    'ERC20', 'ERC721', 'ERC1155', 'Token', 'NFT', 'Staking', 'Vault',
    'Governance', 'DAO', 'Swap', 'Exchange', 'Liquidity', 'Pool',
    'Farm', 'Yield', 'Lending', 'Borrowing', 'Bridge', 'Oracle',
    'Auction', 'Marketplace', 'Escrow', 'Multisig', 'Wallet',
    'Timelock', 'Vesting', 'Presale', 'ICO', 'IDO', 'Launchpad',
    
    # DEX相关
    'Router', 'Factory', 'Pair', 'LP', 'LiquidityPool', 'AMM',
    'SwapRouter', 'QuoterV2', 'NonfungiblePositionManager',
    'TickLens', 'UniswapV3Factory', 'SwapRouter02',
    
    # PancakeSwap相关
    'PancakeRouter', 'PancakeFactory', 'PancakePair', 'PancakeERC20',
    'MasterChef', 'SyrupPool', 'SmartChef', 'BunnyFactory',
    'BunnyMinter', 'CakeToken', 'SyrupBar', 'LotteryV2',
    'PancakeProfile', 'PredictionV2', 'ChainlinkOracle',
    'AnniversaryAchievement', 'IFO', 'IFOPool', 'AutoCakePool',
    'CakeVault', 'BnbStaking', 'ApeSwapStrategy', 'PancakeBunnies',
    
    # 借贷相关
    'Comptroller', 'cToken', 'Unitroller', 'JumpRateModel',
    'InterestRateModel', 'PriceOracle', 'ChainlinkPriceOracle',
    'RewardDistributor', 'StakingRewards', 'YieldFarm',
    'LendingPool', 'BorrowingPool', 'FlashLoan', 'Liquidation',
    'Collateral', 'Synthetic', 'StableCoin', 'AlgorithmicStableCoin',
    
    # 其他DeFi组件
    'RebaseToken', 'BondingCurve', 'CurvePool', 'MetaPool',
    'TokenBridge', 'BridgePool', 'CrossChainBridge', 'Anyswap',
    'Multichain', 'Wormhole', 'Stargate', 'LayerZero', 'Axelar',
    
    # 治理相关
    'Governor', 'GovernorAlpha', 'GovernorBravo', 'Proposal',
    'VotingEscrow', 'GaugeController', 'Minter', 'FeeDistributor',
    
    # 代理和安全
    'Proxy', 'ProxyAdmin', 'TransparentUpgradeableProxy',
    'BeaconProxy', 'UpgradeableBeacon', 'Implementation',
    'Initializable', 'ReentrancyGuard', 'Pausable', 'Ownable',
    
    # 链名称
    'polygon', 'bsc', 'binance', 'avalanche', 'arbitrum', 'optimism', 'eth', 'ethereum',
    'base', 'bnb', 'fantom', 'gnosis', 'matic', 'moonbeam', 'moonriver', 'moonbase',
    'klaytn', 'solana', 'tron', 'avalanche', 'heco',
    
    
    # 开发相关
    'solidity', 'interface', 'abi'
]

# 合约页面相关URL关键字
URL_KEYWORDS = [
    'contract', 'address', 'deploy', 'smart-contract',
    'mainnet', 'testnet','developers', 'docs', 'doc', 'smart-contracts',
    'router', 'factory', 'pair', 'lp', 'liquiditypool', 'amm',
    'swaprouter', 'quoterv2', 'nonfungiblepositionmanager',
    'takelens', 'uniswapv3factory', 'swaprouter02',
    'pancakerouter', 'pancakefactory', 'pancakepair', 'pancakeerc20',
    'masterchef', 'syruppool', 'smartchef', 'bunnyfactory',
    'deployed', 'deployment', 'deployments', 'deployedcontracts',
    'contracts', 'contractaddress', 'contractaddresses', 'contract-addresses',
    'contract-address', 'contract-address-registry', 'contract-address-list' 
]

class ContractSpider:
    def __init__(self, 
                 base_url: str, 
                 output_file: str,
                 openai_api_key: str,
                 openai_api_base: str,
                 openai_model: str,
                 openai_max_tokens: int,
                 openai_max_context: int,
                 openai_timeout: int):
        
        # 处理URL
        self.base_url = self._normalize_url(base_url)
        self.domain = urllib.parse.urlparse(self.base_url).netloc
        
        # 输出文件设置
        if output_file is None or output_file == "":
            self.output_file = f"{self.domain.replace('.', '_')}_contract_addresses.csv"
        else:
            self.output_file = output_file
            
        # OpenAI设置
        self.openai_api_key = openai_api_key
        self.openai_api_base = openai_api_base
        self.openai_model = openai_model
        self.openai_max_tokens = openai_max_tokens
        self.openai_max_context = openai_max_context
        self.openai_timeout = openai_timeout
        
        if openai_api_key:
            self._setup_openai()
            
        # 初始化WebDriver
        self.driver = self._setup_webdriver()
        
        # 初始化集合和计数器
        self.visited_urls = set()
        self.to_visit_urls = set([self.base_url])
        self.contract_pages = set()
        self.extracted_addresses = set()
        self.address_contexts = []
        
        # 黑洞地址列表 - 这些地址将被过滤掉
        self.blackhole_addresses = {
            "0x000000000000000000000000000000000000dead",
            "0x0000000000000000000000000000000000000000",
            "0x0000000000000000000000000000000000000001",
            "0xdead000000000000000042069420694206942069",
            "0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee"
        }
        
        # 已保存到CSV的地址集合
        self.saved_addresses = set()
        self._load_existing_addresses()
        
        # 检查是否有文档子域名
        self._check_for_docs_subdomain()

    def _normalize_url(self, url: str) -> str:
        """规范化URL格式"""
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        return url
    
    def _setup_openai(self):
        """配置OpenAI API"""
        openai.api_key = self.openai_api_key
        
        # 设置更详细的日志
        openai.debug = True
        
        # 全局禁用SSL验证
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        # 配置自定义HTTP客户端，禁用SSL验证
        # 创建一个忽略SSL验证的httpx客户端
        httpx_client = httpx.Client(
            verify=False,  # 禁用SSL验证
            timeout=self.openai_timeout
        )
        
        # 将客户端设置为OpenAI的默认客户端
        openai.http_client = httpx_client
        
        # 全局禁用Python请求的SSL验证
        import ssl
        ssl._create_default_https_context = ssl._create_unverified_context
        
        # 重要：必须在创建客户端后设置API基础URL
        if self.openai_api_base:
            # 确保API基础URL正确设置
            openai.base_url = self.openai_api_base
            logger.info(f"使用自定义OpenAI API基础URL: {self.openai_api_base}")
        logger.info(f"OpenAI模型设置为: {self.openai_model}")
        
        # 测试API连接
        try:
            logger.info("测试OpenAI API连接...")
            # 记录当前的API设置
            logger.info(f"当前API设置 - 基础URL: {openai.base_url}, API密钥: {self.openai_api_key[:5]}...")
            
            # 使用一个简单的请求测试连接
            response = openai.chat.completions.create(
                model=self.openai_model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=5,
                timeout=30,
            )
            logger.info("OpenAI API连接测试成功")
        except Exception as e:
            logger.warning(f"OpenAI API连接测试失败: {str(e)}")
            logger.warning("继续执行，但API调用可能会失败")

    def _setup_webdriver(self):
        """配置和初始化WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        # 忽略SSL证书错误
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--allow-insecure-localhost")
        chrome_options.add_argument("--ignore-ssl-errors=yes")
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        # 添加重试逻辑
        max_retries = 3
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                logger.info(f"尝试初始化WebDriver (尝试 {retry_count + 1}/{max_retries})...")
                
                # 尝试使用ChromeDriverManager
                try:
                    service = Service(ChromeDriverManager().install())
                except Exception as e:
                    logger.warning(f"ChromeDriverManager失败: {e}")
                    logger.info("尝试使用系统默认ChromeDriver...")
                    # 尝试使用系统默认的ChromeDriver
                    service = Service()
                
                driver = webdriver.Chrome(service=service, options=chrome_options)
                driver.set_page_load_timeout(30)
                logger.info("WebDriver初始化成功")
                return driver
                
            except Exception as e:
                retry_count += 1
                last_error = e
                logger.warning(f"WebDriver初始化失败 (尝试 {retry_count}/{max_retries}): {e}")
                
                if retry_count < max_retries:
                    # 等待一段时间后重试
                    wait_time = 2 ** retry_count  # 指数退避
                    logger.info(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
        
        # 所有重试都失败
        logger.error(f"WebDriver初始化失败，已达到最大重试次数: {last_error}")
        sys.exit(1)
    
    def _check_for_docs_subdomain(self):
        """智能检查可能的文档子域名和路径，并尝试解析站点地图"""
        parsed_url = urllib.parse.urlparse(self.base_url)
        base_domain = '.'.join(parsed_url.netloc.split('.')[-2:])
        
        # 常见的文档子域名模式
        docs_subdomains = [
            f"https://docs.{base_domain}",
            f"https://doc.{base_domain}",
            f"https://developer.{base_domain}",
            f"https://developers.{base_domain}",
            f"https://api.{base_domain}"
        ]
        
        # 生成常见的文档路径组合
        docs_paths = self._generate_common_paths(parsed_url.netloc, base_domain)
        
        # 合并所有可能的文档URL
        potential_docs_urls = docs_subdomains + docs_paths
        
        # 尝试获取站点地图
        sitemap_urls = self._get_sitemap_urls(self.base_url)
        if sitemap_urls:
            logger.info(f"从站点地图中发现 {len(sitemap_urls)} 个URL")
            # 过滤站点地图URL，只保留可能包含合约信息的URL
            filtered_sitemap_urls = self._filter_contract_related_urls(sitemap_urls)
            logger.info(f"过滤后保留 {len(filtered_sitemap_urls)} 个可能包含合约信息的URL")
            # 将过滤后的URL添加到待访问列表
            self.to_visit_urls.update(filtered_sitemap_urls)
        
        # 并行检查所有可能的文档URL
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self._check_url_exists, url): url for url in potential_docs_urls}
            for future in concurrent.futures.as_completed(futures):
                url = futures[future]
                try:
                    exists = future.result()
                    if exists:
                        logger.info(f"发现可能的文档URL: {url}")
                        self.to_visit_urls.add(url)
                        # 尝试获取该文档页面的站点地图
                        doc_sitemap_urls = self._get_sitemap_urls(url)
                        if doc_sitemap_urls:
                            filtered_doc_urls = self._filter_contract_related_urls(doc_sitemap_urls)
                            logger.info(f"从文档站点地图中发现 {len(filtered_doc_urls)} 个可能包含合约信息的URL")
                            self.to_visit_urls.update(filtered_doc_urls)
                except Exception as e:
                    logger.debug(f"检查URL时出错: {url}, 错误: {e}")

    def _get_sitemap_urls(self, base_url):
        """尝试获取站点地图中的URL"""
        sitemap_urls = set()
        
        # 检查是否有lxml解析器
        if not HAS_LXML:
            logger.warning("未安装lxml库，站点地图解析可能不准确。建议安装lxml: pip install lxml")
        
        # 常见的站点地图路径
        sitemap_paths = [
            "/sitemap.xml",
            "/sitemap_index.xml",
            "/sitemap/sitemap.xml",
            "/sitemap/index.xml",
            "/docs/sitemap.xml",
            "/developers/sitemap.xml"
        ]
        
        for path in sitemap_paths:
            sitemap_url = urllib.parse.urljoin(base_url, path)
            try:
                logger.debug(f"尝试获取站点地图: {sitemap_url}")
                response = requests.get(sitemap_url, timeout=10, verify=False)
                
                # 检查是否成功获取站点地图
                if response.status_code == 200:
                    content_type = response.headers.get('Content-Type', '').lower()
                    
                    # 有些站点地图可能不会正确设置Content-Type
                    if 'xml' in content_type or sitemap_url.endswith('.xml'):
                        # 解析XML
                        try:
                            parser = 'xml' if HAS_LXML else 'html.parser'
                            soup = BeautifulSoup(response.content, parser)
                            
                            # 处理sitemap索引
                            sitemapTags = soup.find_all('sitemap')
                            if sitemapTags:
                                logger.info(f"发现站点地图索引: {sitemap_url}")
                                for sitemap in sitemapTags:
                                    loc = sitemap.find('loc')
                                    if loc:
                                        sub_sitemap_url = loc.text
                                        sub_urls = self._parse_sitemap(sub_sitemap_url)
                                        sitemap_urls.update(sub_urls)
                            else:
                                # 直接解析URL
                                urls = self._parse_sitemap(sitemap_url, soup)
                                sitemap_urls.update(urls)
                        except Exception as e:
                            logger.warning(f"解析站点地图出错: {sitemap_url}, 错误: {e}")
            except Exception as e:
                logger.debug(f"获取站点地图失败: {sitemap_url}, 错误: {e}")
        
        return sitemap_urls

    def _parse_sitemap(self, sitemap_url, soup=None):
        """解析站点地图XML，提取URL"""
        urls = set()
        try:
            if soup is None:
                response = requests.get(sitemap_url, timeout=10, verify=False)
                if response.status_code != 200:
                    return urls
                
                # 检查是否有lxml解析器
                if HAS_LXML:
                    soup = BeautifulSoup(response.content, 'xml')
                else:
                    # 如果没有lxml，尝试使用html.parser，但可能不准确
                    soup = BeautifulSoup(response.content, 'html.parser')
                    logger.warning("使用html.parser解析XML，结果可能不准确。建议安装lxml: pip install lxml")
            
            # 提取所有URL
            url_tags = soup.find_all('url')
            for url_tag in url_tags:
                loc = url_tag.find('loc')
                if loc:
                    url = loc.text.strip()
                    urls.add(url)
            
            # 如果没有找到<url>标签，尝试直接查找<loc>标签（某些站点地图格式不同）
            if not url_tags:
                loc_tags = soup.find_all('loc')
                for loc in loc_tags:
                    url = loc.text.strip()
                    urls.add(url)
            
            logger.debug(f"从站点地图中提取了 {len(urls)} 个URL: {sitemap_url}")
            return urls
        except Exception as e:
            logger.warning(f"解析站点地图出错: {sitemap_url}, 错误: {e}")
            # 如果是XML解析错误，给出更明确的提示
            if "Couldn't find a tree builder with the features you requested: xml" in str(e):
                logger.warning("XML解析错误，请安装lxml库: pip install lxml")
            return urls

    def _filter_contract_related_urls(self, urls):
        """过滤URL，只保留可能包含合约信息的URL"""
        filtered_urls = set()
        
        # 合约相关关键词
        contract_keywords = [
            'contract', 'address', 'deploy', 'deployment', 'deployed', 'smart-contract',
            'mainnet', 'testnet', 'ethereum', 'blockchain', 'transaction',
            'developers', 'docs', 'doc', 'smart-contracts',
            'erc20', 'erc721', 'erc1155', 'token', 'nft', 'staking', 'vault',
            'governance', 'dao', 'swap', 'exchange', 'liquidity', 'pool',
            'farm', 'yield', 'lending', 'borrowing', 'bridge', 'oracle'
        ]
        
        for url in urls:
            url_lower = url.lower()
            # 检查URL是否包含合约相关关键词
            if any(keyword in url_lower for keyword in contract_keywords):
                filtered_urls.add(url)
        
        return filtered_urls

    def _generate_common_paths(self, current_domain, base_domain):
        """生成常见的文档和合约路径组合"""
        # 基础路径前缀
        base_prefixes = [
            f"https://{current_domain}",
            f"https://{base_domain}"
        ]
        
        # 一级路径关键词
        level1_keywords = [
            "docs", "doc", "documentation", 
            "developers", "developer",
            "contracts", "contract", 
            "addresses", "address",
            "deployments", "deployment", "deployed",
            "smart-contracts", "api"
        ]
        
        # 二级路径关键词
        level2_keywords = [
            "contracts", "contract", 
            "addresses", "address",
            "deployments", "deployment", "deployed",
            "mainnet", "testnet", "ethereum", "polygon", "arbitrum", "optimism",
            "v1", "v2", "v3", "latest",
            "protocol", "tokens", "gho", "stablecoin",
            "developers", "reference", "api"
        ]
        
        # 生成路径组合
        paths = []
        
        # 添加一级路径
        for prefix in base_prefixes:
            for kw in level1_keywords:
                paths.append(f"{prefix}/{kw}")
        
        # 添加二级路径组合
        for prefix in base_prefixes:
            for kw1 in ["docs", "doc", "documentation", "developers", "developer"]:
                for kw2 in level2_keywords:
                    paths.append(f"{prefix}/{kw1}/{kw2}")
        
        # 添加特定的合约地址路径组合
        contract_path_combinations = [
            "contract-addresses", "contract-address", "contractaddresses", "contractaddress",
            "deployed-contracts", "deployed-addresses", "smart-contract-addresses",
            "mainnet-addresses", "mainnet-deployments", "mainnet-contracts",
            "ethereum-addresses", "ethereum-deployments", "ethereum-contracts"
        ]
        
        for prefix in base_prefixes:
            for combo in contract_path_combinations:
                paths.append(f"{prefix}/{combo}")
                # 也添加到docs下
                paths.append(f"{prefix}/docs/{combo}")
                paths.append(f"{prefix}/developers/{combo}")
        
        # 添加DeFi特定路径
        defi_paths = [
            "/protocol", "/protocol/contracts", "/protocol/addresses",
            "/tokens", "/tokens/addresses", "/tokens/contracts",
            "/markets", "/markets/addresses", "/markets/contracts",
            "/governance", "/governance/addresses", "/governance/contracts",
            "/staking", "/staking/addresses", "/staking/contracts",
            "/lending", "/lending/addresses", "/lending/contracts",
            "/v1", "/v2", "/v3", "/latest",
            "/v1/contracts", "/v2/contracts", "/v3/contracts",
            "/mainnet", "/testnet", "/ethereum", "/polygon", "/arbitrum", "/optimism",
            "/mainnet/contracts", "/ethereum/contracts"
        ]
        
        for prefix in base_prefixes:
            for path in defi_paths:
                paths.append(f"{prefix}{path}")
        
        return list(set(paths))  # 去重

    def _extract_page_urls(self, soup: BeautifulSoup, current_url: str) -> Set[str]:
        """从页面提取链接"""
        urls = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # 跳过无效链接
            if href.startswith(('#', 'javascript:')):
                continue
            
            # 使用urljoin正确处理相对路径，包括../这种情况
            full_url = urllib.parse.urljoin(current_url, href)
            
            # 解析URL
            parsed_href = urllib.parse.urlparse(full_url)
            parsed_current = urllib.parse.urlparse(current_url)
            
            # 允许同一根域名下的不同子域名
            current_root_domain = self._get_root_domain(parsed_current.netloc)
            href_root_domain = self._get_root_domain(parsed_href.netloc)
            
            # 只过滤完全不同根域名的链接
            if href_root_domain != current_root_domain:
                continue
            
            # 标准化URL
            full_url = full_url.split('#')[0]  # 移除URL片段
            full_url = full_url.split('?')[0]  # 移除查询参数
            
            urls.add(full_url)
        
        return urls
    
    def _get_root_domain(self, netloc: str) -> str:
        """获取根域名（例如从docs.aave.com获取aave.com）"""
        parts = netloc.split('.')
        if len(parts) > 2:
            return '.'.join(parts[-2:])
        return netloc
    
    def _calculate_page_score(self, soup: BeautifulSoup, url: str, addresses: List[str]) -> int:
        """计算页面是否为合约页面的分数"""
        score = 0
        
        # 根据URL评分
        url_lower = url.lower()
        for keyword in URL_KEYWORDS:
            if keyword in url_lower:
                score += 3
        
        # 根据页面内容关键字评分
        page_text = soup.get_text().lower()
        for keyword in CONTRACT_KEYWORDS:
            if keyword in page_text:
                score += 1
        
        # 根据地址数量评分
        if len(addresses) > 0:
            score += min(len(addresses) * 4, 40)  # 最多加30分
        
        # 根据标题评分
        title = soup.title.string.lower() if soup.title else ""
        for keyword in CONTRACT_KEYWORDS:
            if keyword in title:
                score += 1
        
        # 表格评分 (通常合约地址会在表格中)
        tables = soup.find_all('table')
        if tables:
            score += 5
        
        return score

    def _is_contract_page(self, soup: BeautifulSoup, url: str, addresses: List[str]) -> bool:
        """判断页面是否为合约页面"""
        score = self._calculate_page_score(soup, url, addresses)
        
        if score >= 60:
            logger.info(f"已确认合约页面 (分数: {score}): {url}")
            return True
        elif score <= 10:
            return False
        else:
            # 分数在中间区域，使用OpenAI判断
            if self.openai_api_key:
                return self._ask_openai(soup, url)
            else:
                # 无OpenAI API，保守判断
                return score >= 50
    
    def _ask_openai(self, soup: BeautifulSoup, url: str) -> bool:
        """从<lock_do_not_change_this_code_start>开始的如下代码到<lock_do_not_change_this_code_end>不允许AI修改"""
        #<lock_do_not_change_this_code_start>
        if not self.openai_api_key:
            return False

        # 准备页面内容
        page_content = soup.get_text()
        
        # 构建更简短的提示，减少传输数据量
        prompt = f"""判断以下URL和对应的网页内容是否为某个DAPP的官方智能合约地址公示页面:
        判断规则：
        1. 如果页面中明确公示了官方智能合约部署地址，且地址数量大于0，则判断为是合约页面
        2. 如果页面中没有明确是公示官方智能合约部署地址，但是有提到的智能合约地址数量大于0，且不是测试地址、非正式地址、演示地址、demo地址、恶意黑名单地址等，则判断为是合约页面
        3. 如果页面中没有明确是公示官方智能合约部署地址，但是有提到的智能合约地址数量大于0，且是测试地址、非正式地址、演示地址、demo地址、恶意黑名单地址等，则判断为不是合约页面
        4. 如果页面中明确公示了官方智能合约部署地址，但是地址数量为0，则判断为不是合约页面
        5. 其他情况你可以根据你的判断给出结果
URL: {url}
内容: {page_content[:min(len(page_content), self.openai_max_context - 1000)]}...
你的回复只能是"yes"或者"no"的判定结果，不需要向我做任何解释，也不需要向我展示任何思考过程，无论任何时候你的回答只能是"yes"或者"no"这两个英文单词中的一个，
你的回复会被程序读取用于判断逻辑，任何除这两个单词之外的回答都会导致程序判断错误出现故障。"""
        #<lock_do_not_change_this_code_end>
        logger.info(f"准备发送OpenAI请求，模型: {self.openai_model}")
        
        # 直接尝试一次，不在这里实现重试逻辑（因为OpenAI库已有内部重试）
        try:
            # 使用新版本OpenAI API调用方式
            response = openai.chat.completions.create(
                model=self.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.openai_max_tokens,  # 有时候模型会有一定概率输出多余内容最后再输出 ok
                timeout=self.openai_timeout * 2,
            )
            
            # 记录响应信息
            logger.info(f"OpenAI响应成功，模型: {response.model}, 用时: {response.usage.total_tokens}tokens")
            
            # 解析回答
            answer = response.choices[0].message.content.strip().lower()
            logger.info(f"OpenAI原始回答: '{answer}'")
            
            if "是" in answer or "yes" in answer:
                logger.info(f"OpenAI判断结果: 是合约页面 - {url}")
                return True
            else:
                logger.info(f"OpenAI判断结果: 不是合约页面 - {url}")
                return False
                
        except Exception as e:
            logger.error(f"OpenAI API错误: {str(e)}")
            logger.error(f"错误类型: {type(e).__name__}")
            
            # 对于连接错误，尝试使用基于分数的判断作为备选
            score = self._calculate_page_score(soup, url, self._extract_addresses(str(soup)))
            logger.info(f"由于API错误，使用分数判断: {score}/50")
            return score >= 40  # 使用更高的阈值作为保守判断
        
        return False
    
    def _extract_addresses(self, html: str) -> List[str]:
        """从HTML中提取以太坊地址"""
        # 以太坊地址正则表达式 - 基本模式
        basic_pattern = r'0x[a-fA-F0-9]{40}'
        
        # 查找所有匹配的潜在地址
        potential_addresses = re.findall(basic_pattern, html)
        
        # 过滤有效地址
        valid_addresses = []
        for addr in potential_addresses:
            addr_lower = addr.lower()
            
            # 跳过黑洞地址
            if addr_lower in self.blackhole_addresses:
                continue
                
            # 检查地址是否为更长字符串的一部分（如交易ID）
            # 查找这个地址后面是否紧跟着十六进制字符
            longer_pattern = re.escape(addr) + r'[a-fA-F0-9]+'
            if re.search(longer_pattern, html):
                logger.debug(f"跳过可能是交易ID一部分的地址: {addr}")
                continue
                
            # 检查地址前缀 - 过滤掉以大量0开头但不是特定黑洞地址的地址
            # 这里的逻辑是：如果地址以8个或更多0开头，但不是标准的黑洞地址（全0或特定格式），可能是无效地址
            if addr_lower.startswith('0x000000000000000000') and addr_lower not in self.blackhole_addresses:
                logger.debug(f"跳过可疑前缀地址: {addr}")
                continue
                
            # 检查地址上下文 - 如果地址出现在明显的非合约上下文中，跳过它
            # 例如，在JSON数据的id字段中
            addr_context = self._get_address_surrounding_text(html, addr, 50)
            suspicious_contexts = ['"id":', '"hash":', 'transaction', 'txid', 'txhash', 'block']
            if any(ctx in addr_context.lower() for ctx in suspicious_contexts):
                logger.debug(f"跳过可疑上下文中的地址: {addr}, 上下文: {addr_context}")
                continue
                
            # 通过所有检查，认为是有效地址
            valid_addresses.append(addr_lower)
        
        # 去重
        unique_addresses = list(set(valid_addresses))
        
        # 记录过滤情况
        if len(potential_addresses) != len(unique_addresses):
            logger.info(f"地址过滤: 从 {len(potential_addresses)} 个潜在地址减少到 {len(unique_addresses)} 个有效地址")
            
        return unique_addresses
        
    def _get_address_surrounding_text(self, html: str, address: str, context_length: int = 50) -> str:
        """获取地址周围的文本上下文，用于判断地址有效性"""
        try:
            # 找到地址在HTML中的位置
            pos = html.find(address)
            if pos == -1:
                return ""
                
            # 获取前后文本
            start = max(0, pos - context_length)
            end = min(len(html), pos + len(address) + context_length)
            
            return html[start:end]
        except Exception as e:
            logger.error(f"获取地址上下文时出错: {e}")
            return ""
    
    def _extract_address_context(self, soup: BeautifulSoup, address: str) -> str:
        """提取地址的上下文信息"""
        # 寻找包含地址的元素
        elements = soup.find_all(string=re.compile(address))
        if not elements:
            return ""
        
        # 从最近的父元素获取上下文
        element = elements[0]
        parent = element.parent
        
        # 尝试找到合适的上下文容器
        context_element = parent
        for _ in range(3):  # 向上最多查找3层
            if context_element.name in ['tr', 'div', 'section', 'article', 'li']:
                break
            context_element = context_element.parent
            if context_element is None:
                context_element = parent
                break
        
        # 提取上下文文本并清理
        context = context_element.get_text(separator=' ', strip=True)
        context = re.sub(r'\s+', ' ', context)
        
        # 如果上下文太长，进行截断
        if len(context) > 500:
            # 尝试找到地址附近的文本
            addr_pos = context.find(address)
            start = max(0, addr_pos - 200)
            end = min(len(context), addr_pos + len(address) + 200)
            context = context[start:end]
            
        return context
    
    def _load_existing_addresses(self):
        """加载已存在CSV文件中的地址，避免重复写入"""
        if os.path.exists(self.output_file):
            try:
                with open(self.output_file, 'r', newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if 'Address' in row:
                            self.saved_addresses.add(row['Address'].lower())
                logger.info(f"已从CSV加载 {len(self.saved_addresses)} 个已存在的地址")
            except Exception as e:
                logger.error(f"加载已存在地址时出错: {e}")
    
    def _save_results(self):
        """保存结果到CSV文件"""
        if not self.address_contexts:
            logger.warning("没有找到合约地址，不生成输出文件")
            return
            
        try:
            # 过滤掉已经保存过的地址
            new_contexts = []
            for item in self.address_contexts:
                address = item['Address'].lower()
                if address not in self.saved_addresses:
                    new_contexts.append(item)
                    self.saved_addresses.add(address)
                    logger.info(f"添加新地址 {address} 到保存列表")
            
            # 如果没有新的地址，则不需要写入
            if not new_contexts:
                logger.info("没有新的合约地址需要保存")
                return
                
            # 确定是新建还是追加模式
            mode = 'w' if not os.path.exists(self.output_file) else 'a'
            write_header = mode == 'w'
            
            with open(self.output_file, mode, newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['Address', 'Context', 'Source URL', 'Chain', 'Contract'])
                if write_header:
                    writer.writeheader()
                writer.writerows(new_contexts)
                
            logger.info(f"已保存 {len(new_contexts)} 个新合约地址到 {self.output_file}")
            
            # 更新address_contexts，只保留已保存的内容
            self.address_contexts = []
            
        except Exception as e:
            logger.error(f"保存结果时出错: {e}")
            
    def test_url(self, url: str):
        """测试特定URL的处理能力"""
        logger.info(f"测试URL: {url}")
        
        try:
            # 访问页面
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 获取页面HTML并解析
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # 提取以太坊地址并判断页面类型
            addresses = self._extract_addresses(html)
            is_contract_page = self._is_contract_page(soup, url, addresses)
            
            print("\n--- 测试结果 ---")
            print(f"URL: {url}")
            print(f"找到的以太坊地址数量: {len(addresses)}")
            if addresses:
                print("地址示例:")
                for addr in addresses[:5]:
                    print(f"  - {addr}")
            
            print(f"页面得分: {self._calculate_page_score(soup, url, addresses)}/50")
            print(f"页面判断结果: {'这是一个合约页面' if is_contract_page else '这不是一个合约页面'}")
            
            # 如果当前页面没有找到地址，尝试探索文档页面
            if not addresses:
                print("\n当前页面未找到合约地址，尝试探索文档页面...")
                
                # 检查是否有文档子域名
                self._check_for_docs_subdomain()
                
                # 尝试访问已知可能包含合约地址的页面
                potential_contract_pages = [
                    "https://aave.com/docs/developers/gho",  # Aave GHO合约页面
                    "https://docs.aave.com/developers/deployed-contracts/deployed-contracts",
                    "https://aave.com/docs/developers/deployed-contracts",
                    "https://aave.com/docs/developers/v3/deployed-contracts"
                ]
                
                # 将发现的文档URL也添加到潜在页面列表
                for doc_url in self.to_visit_urls:
                    if "doc" in doc_url.lower() or "developer" in doc_url.lower():
                        potential_contract_pages.append(doc_url)
                
                # 访问潜在的合约页面
                found_addresses = False
                for page_url in potential_contract_pages[:5]:  # 限制测试页面数量
                    try:
                        print(f"\n尝试访问: {page_url}")
                        self.driver.get(page_url)
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )
                        
                        # 处理重定向
                        final_url = self.driver.current_url
                        if final_url != page_url:
                            print(f"重定向: {page_url} -> {final_url}")
                            page_url = final_url
                        
                        page_html = self.driver.page_source
                        page_soup = BeautifulSoup(page_html, 'html.parser')
                        page_addresses = self._extract_addresses(page_html)
                        
                        print(f"找到的以太坊地址数量: {len(page_addresses)}")
                        if page_addresses:
                            found_addresses = True
                            print("地址示例:")
                            for addr in page_addresses[:5]:
                                print(f"  - {addr}")
                                
                            # 显示一些上下文示例
                            print("\n上下文示例:")
                            for i, addr in enumerate(page_addresses[:3]):
                                context = self._extract_address_context(page_soup, addr)
                                print(f"\n地址 {i+1}: {addr}")
                                print(f"上下文: {context[:200]}...")
                    except Exception as e:
                        print(f"访问页面出错: {page_url}, 错误: {e}")
                
                if not found_addresses:
                    print("\n在所有测试页面中均未找到合约地址。")
                    print("建议：")
                    print("1. 确保URL正确，尝试直接访问文档或开发者页面")
                    print("2. 安装lxml库以支持XML解析: pip install lxml")
                    print("3. 使用非测试模式运行爬虫，以便更全面地探索网站")
            else:
                # 显示一些上下文示例
                print("\n上下文示例:")
                for i, addr in enumerate(addresses[:3]):
                    context = self._extract_address_context(soup, addr)
                    print(f"\n地址 {i+1}: {addr}")
                    print(f"上下文: {context[:200]}...")
            
        except Exception as e:
            logger.error(f"测试URL时出错: {e}")
        finally:
            self.driver.quit()
            
    def crawl(self, max_addresses: int = 3000, max_pages: int = 5000):
        """爬取网站并提取合约地址"""
        # 设置OpenAI和WebDriver
        self._setup_openai()
        self._setup_webdriver()
        
        # 检查是否有docs子域名
        self._check_for_docs_subdomain()
        
        visited_count = 0
        
        try:
            while self.to_visit_urls and visited_count < max_pages and len(self.extracted_addresses) < max_addresses:
                # 获取下一个URL
                current_url = self.to_visit_urls.pop()
                self.visited_urls.add(current_url)
                visited_count += 1
                
                logger.info(f"[{visited_count}/{max_pages}] 访问: {current_url}")
                
                try:
                    # 访问页面
                    self.driver.get(current_url)
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    
                    # 处理重定向 - 获取当前URL（可能与请求的URL不同）
                    final_url = self.driver.current_url
                    if final_url != current_url:
                        logger.info(f"重定向: {current_url} -> {final_url}")
                        # 将最终URL也添加到已访问集合中
                        self.visited_urls.add(final_url)
                        # 使用最终URL进行后续处理
                        current_url = final_url
                    
                    # 获取页面内容
                    html = self.driver.page_source
                    soup = BeautifulSoup(html, 'html.parser')
                    
                    # 提取以太坊地址
                    addresses = self._extract_addresses(html)
                    
                    # 如果找到地址，判断是否为合约页面
                    if addresses and self._is_contract_page(soup, current_url, addresses):
                        logger.info(f"已确认合约页面 (分数: {self._calculate_page_score(soup, current_url, addresses)}): {current_url}")
                        self.contract_pages.add(current_url)
                        
                        # 提取地址上下文并保存
                        for address in addresses:
                            if address in self.extracted_addresses:
                                continue
                                
                            self.extracted_addresses.add(address)
                            context = self._extract_address_context(soup, address)
                            
                            self.address_contexts.append({
                                'Address': address,
                                'Context': context,
                                'Source URL': current_url,
                                'Chain': '未知',  # 不再通过RPC验证链信息
                                'Contract': ''  # 不再获取合约名称
                            })
                            
                            logger.info(f"已提取地址: {address}")
                            
                            # 每提取一个新地址就保存一次结果
                            self._save_results()
                    
                    # 提取页面中的其他URL
                    new_urls = self._extract_page_urls(soup, current_url)
                    for url in new_urls:
                        if url not in self.visited_urls:
                            self.to_visit_urls.add(url)
                    
                except TimeoutException:
                    logger.warning(f"页面加载超时: {current_url}")
                except WebDriverException as e:
                    logger.warning(f"WebDriver错误: {e}")
                except Exception as e:
                    logger.error(f"处理页面时出错: {current_url}, 错误: {e}")
                
                # 显示进度
                if visited_count % 10 == 0:
                    logger.info(f"已爬取 {visited_count} 个页面, 找到 {len(self.extracted_addresses)} 个合约地址")
                
                # 随机暂停2-6秒避免触发反爬机制
                time.sleep(random.uniform(2, 6))
                
        finally:
            self.driver.quit()
            
        # 保存结果
        if self.address_contexts:
            self._save_results()

    def _check_url_exists(self, url):
        """检查URL是否存在"""
        try:
            # 忽略SSL验证
            response = requests.head(url, timeout=10, verify=False, allow_redirects=True)
            return response.status_code < 400
        except requests.RequestException:
            return False


def main():
    parser = argparse.ArgumentParser(description='智能合约地址爬虫')
    
    # 测试模式和正常模式的区别
    parser.add_argument('--test', action='store_true', help='测试模式')
    
    # URL参数，在测试模式下可选，在正常模式下必需
    parser.add_argument('url', nargs='?', help='要爬取的网站URL')
    
    # URL列表文件参数
    parser.add_argument('--url_list_file', help='包含多个URL的文件路径，每行一个URL')
    
    # 输出文件
    parser.add_argument('--output', '-o', help='输出CSV文件路径')
    
    # OpenAI API相关设置
    parser.add_argument('--openai-api-key', help='OpenAI API密钥，如果不提供则从keyring中获取OPENAI_API_KEY_SILICON')
    parser.add_argument('--openai-api-base', help='OpenAI API基础URL')
    parser.add_argument('--openai-model', default='Qwen/Qwen2.5-7B-Instruct', help='OpenAI模型名称')
    parser.add_argument('--openai-max-tokens', type=int, default=4096, help='生成回复的最大token数')
    parser.add_argument('--openai-max-context', type=int, default=4096, help='模型的最大上下文长度')
    parser.add_argument('--openai-timeout', type=int, default=90, help='API调用超时时间(秒)')
    
    args = parser.parse_args()
    
    # 从keyring获取API密钥
    api_key = args.openai_api_key
    if not api_key:
        try:
            api_key = keyring.get_password("system", "OPENAI_API_KEY_SILICON")
        except Exception as e:
            logger.error(f"从keyring获取API密钥时出错: {e}")
            logger.info("请使用以下命令将您的API密钥添加到keyring中:")
            logger.info("python -c \"import keyring; keyring.set_password('system', 'OPENAI_API_KEY_SILICON', '您的API密钥')\"")
            logger.info("或者使用 --openai-api-key 参数直接提供API密钥")
            return 1
    
    # 检查参数
    if args.test:
        if not args.url:
            parser.error("测试模式需要提供URL参数")
        
        try:
            # 初始化爬虫
            spider = ContractSpider(
                base_url=args.url,
                output_file=args.output or "",
                openai_api_key=api_key,
                openai_api_base=args.openai_api_base or "https://api.siliconflow.cn/v1/",
                openai_model=args.openai_model if args.openai_model else "Qwen/Qwen2.5-7B-Instruct",
                openai_max_tokens=args.openai_max_tokens if args.openai_max_tokens else 4096,
                openai_max_context=args.openai_max_context if args.openai_max_context else 4096,
                openai_timeout=args.openai_timeout if args.openai_timeout else 90
            )
            
            # 测试模式
            spider.test_url(args.url)
        except Exception as e:
            logger.error(f"测试模式出错: {e}")
            return 1
    else:
        # 正常爬取模式
        if not args.url and not args.url_list_file:
            parser.error("在非测试模式下，必须提供URL参数或URL列表文件")
        
        # 处理URL列表文件
        if args.url_list_file:
            try:
                # 检查文件是否存在
                if not os.path.exists(args.url_list_file):
                    logger.error(f"URL列表文件不存在: {args.url_list_file}")
                    return 1
                
                # 读取URL列表
                with open(args.url_list_file, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]
                
                if not urls:
                    logger.error(f"URL列表文件为空: {args.url_list_file}")
                    return 1
                
                logger.info(f"从文件 {args.url_list_file} 中读取了 {len(urls)} 个URL")
                
                # 依次处理每个URL
                for i, url in enumerate(urls):
                    logger.info(f"开始处理第 {i+1}/{len(urls)} 个URL: {url}")
                    
                    try:
                        # 为每个URL创建单独的输出文件
                        domain = urllib.parse.urlparse(url).netloc if url.startswith(('http://', 'https://')) else urllib.parse.urlparse(f"https://{url}").netloc
                        output_file = f"{domain.replace('.', '_')}_contract_addresses.csv" if not args.output else f"{os.path.splitext(args.output)[0]}_{domain}.csv"
                        
                        # 初始化爬虫
                        spider = ContractSpider(
                            base_url=url,
                            output_file=output_file,
                            openai_api_key=api_key,
                            openai_api_base=args.openai_api_base or "https://api.siliconflow.cn/v1/",
                            openai_model=args.openai_model if args.openai_model else "Qwen/Qwen2.5-7B-Instruct",
                            openai_max_tokens=args.openai_max_tokens if args.openai_max_tokens else 4096,
                            openai_max_context=args.openai_max_context if args.openai_max_context else 4096,
                            openai_timeout=args.openai_timeout if args.openai_timeout else 90
                        )
                        
                        # 爬取
                        spider.crawl()
                        logger.info(f"完成URL {url} 的爬取，结果保存到 {output_file}")
                    except KeyboardInterrupt:
                        logger.info("用户中断程序")
                        return 1
                    except Exception as e:
                        logger.error(f"处理URL {url} 时出错: {e}")
                        # 继续处理下一个URL
                        continue
            except Exception as e:
                logger.error(f"处理URL列表文件时出错: {e}")
                return 1
        elif args.url:
            # 处理单个URL
            try:
                # 初始化爬虫
                spider = ContractSpider(
                    base_url=args.url,
                    output_file=args.output or "",
                    openai_api_key=api_key,
                    openai_api_base=args.openai_api_base or "https://api.siliconflow.cn/v1/",
                    openai_model=args.openai_model if args.openai_model else "Qwen/Qwen2.5-7B-Instruct",
                    openai_max_tokens=args.openai_max_tokens if args.openai_max_tokens else 4096,
                    openai_max_context=args.openai_max_context if args.openai_max_context else 4096,
                    openai_timeout=args.openai_timeout if args.openai_timeout else 90
                )
                
                # 爬取
                spider.crawl()
            except KeyboardInterrupt:
                logger.info("用户中断程序")
                return 1
            except Exception as e:
                logger.error(f"程序执行出错: {e}")
                return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
