#!/usr/bin/env python
import os
import argparse
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from PIL import Image
import plotly.express as px
import plotly.io as pio
from tqdm import tqdm
import warnings
import base64
import webbrowser
from pathlib import Path
import json
warnings.filterwarnings('ignore')

# Add argument parser
parser = argparse.ArgumentParser(description='Generate travel company revenue visualization using Plotly')
parser.add_argument('--output', type=str, default='output/travel_revenue_plotly.html', 
                    help='Output HTML file path')
parser.add_argument('--frames-per-year', type=int, default=4, 
                    help='Number of frames to generate per year (default: 4 for quarterly)')
parser.add_argument('--height', type=int, default=800, 
                    help='Height of the visualization in pixels (default: 800)')
parser.add_argument('--width', type=int, default=1600, 
                    help='Width of the visualization in pixels (default: 1600)')
parser.add_argument('--max-companies', type=int, default=15, 
                    help='Maximum number of companies to display (default: 15)')
parser.add_argument('--transition-duration', type=int, default=500, 
                    help='Transition duration between frames in ms (default: 500)')
args = parser.parse_args()

# Create required directories
output_dir = os.path.dirname(args.output)
if output_dir and not os.path.exists(output_dir):
    os.makedirs(output_dir)
    print(f"Created directory: {output_dir}")

# Create a color mapping for regions
region_colors = {
    'North America': '#778899',  # 浅灰色，对应原来的 Turquoise
    'Europe': '#778899',         # 浅灰色，对应原来的 Royal Blue
    'Asia Pacific': '#778899',   # 浅灰色，对应原来的 Red
    'Latin America': '#778899',  # 浅灰色，对应原来的 Lime Green
    'China': '#2577e3',          # 蓝色，对应 TCOM 的颜色
    'Middle East': '#778899',    # 浅灰色，对应原来的 Burlywood
    'India': '#e74c3c',          # 红色，对应 YTRA 和 MMYT 的颜色
    'Australia': '#e74c3c'       # 红色，对应 WBJ 的颜色
}

# Define ticker to company mapping
ticker_to_company = {
    'ABNB': 'Airbnb',
    'BKNG': 'Booking Holdings',
    'PCLN': 'Priceline',
    'DESP': 'Despegar',
    'EASEMYTRIP': 'EaseMyTrip',
    'EDR': 'Endeavor',
    'EXPE': 'Expedia',
    'LMN': 'Lastminute.com',
    'MMYT': 'MakeMyTrip',
    'OWW': 'Orbitz Worldwide',
    'SEERA': 'Seera Group',
    'TCOM': 'Trip.com Group',
    'TRIP': 'TripAdvisor',
    'TRVG': 'Trivago',
    'WBJ': 'Webjet',
    'YTRA': 'Yatra',
    'IXIGO': 'Ixigo',
    'FLT': 'Flight Centre',
    'LONG': 'eLong',  # 确保eLong使用LONG作为ticker
    'TCEL': 'TongCheng',
    'KYAK': 'KAYAK'  # 修正：CSV中是KYAK而不是KAYAK
}

# Define IPO dates for companies (decimal year format)
# Based on the provided event list
ipo_dates = {
    'EDR': 2014.5,
    
    'Orbitz': 2003.5,
    'PCLN': 1998.21,  # Mar 1999
    'EXPE': 1999.84,  # Nov 1999
    'LMN': 2000.21,   # Mar 2000
    'WBJ': 2000.38,   # May 2000
    'LONG': 2004.75,  # Oct 2004
    'TCOM': 2004,  # Dec 2003 (Ctrip)
    'OWW': 2003.92,   # Dec 2003 (Orbitz)
    'KYAK': 2012.54,  # Jul 2012
    'MMYT': 2010.63,  # Aug 2010
    'TRIP': 2011.92,  # Dec 2011
    'SEERA': 2012.29, # Apr 2012 (Al Tayyar Travel)
    'TRVG': 2016.96,  # Dec 2016
    'YTRA': 2016.75,  # Oct 2016
    'TCEL': 2018.88,  # Nov 2018 (Tongcheng-eLong)
    'ABNB': 2020.92,  # Dec 2020
    'EASEMYTRIP': 2021.21, # Mar 2021
    'DESP': 2017.71,  # Sep 2017
    'IXIGO': 2024.42  # Jun 2024
}

# 需要排除的公司列表（不在可视化中显示）
excluded_companies = ['FLT', 'Skyscanner', 'Kiwi', 'Almosafer', 'Traveloka', 'Etraveli', 'Travelocity', 'Webjet OTA', 'Wego', 'Cleartrip']

# 扩展排除公司列表，包含CSV中实际的列名
excluded_columns = excluded_companies + ['Flight Centre', 'Flight center', "Travelocity"]

# 创建反向映射，用于将CSV中的原始列名映射回对应的ticker
company_to_ticker = {}
for ticker, company in ticker_to_company.items():
    company_to_ticker[company.lower()] = ticker
    # 也添加原始名称到ticker的映射
    company_to_ticker[ticker.lower()] = ticker

# 特定列名到ticker的直接映射
special_column_to_ticker = {
    'elong': 'LONG',
    'tongcheng': 'TCEL',
    'webjet': 'WBJ',
    'webjet ota': 'WBJ',
    'kyak': 'KYAK',
    'orbitz': 'ORBITZ',  # 修改为全大写，匹配company_colors中的键
    'orbitz worldwide': 'OWW',  # 添加Orbitz Worldwide的映射
    'ctrip': 'TCOM',     # 添加Ctrip到TCOM的映射
    'trip.com': 'TCOM',  # 添加Trip.com到TCOM的映射
    'trip.com group': 'TCOM'  # 添加完整名称映射
}

# Define company to region mapping
company_to_region = {
    'ABNB': 'North America',
    'BKNG': 'North America',
    'PCLN': 'North America',
    'DESP': 'Latin America',
    'EASEMYTRIP': 'India',
    'EXPE': 'North America',
    'LMN': 'Europe',
    'MMYT': 'India',
    'OWW': 'North America',
    'SEERA': 'Middle East',
    'TCOM': 'China',
    'TRIP': 'North America',
    'TRVG': 'Europe',
    'WBJ': 'Australia',
    'YTRA': 'India',
    'IXIGO': 'India',
    'FLT': 'Australia',
    'LONG': 'China',
    'TCEL': 'China',
    'Orbitz': 'North America',
    'ORBITZ': 'North America',
    'Travelocity': 'North America',
    'Webjet': 'Australia',
    'EaseMyTrip': 'India',
    'Yatra': 'India',
    'Almosafer': 'Middle East',
    'Wego': 'Middle East',
    'Skyscanner': 'Europe',
    'Etraveli': 'Europe',
    'Kiwi': 'Europe',
    'Cleartrip': 'India',
    'Traveloka': 'Asia Pacific',
    'Cleartrip ME & Flyin': 'Middle East',
    'Cleartrip Arabia': 'Middle East',
    'Webjet OTA': 'Australia',
    'EDR': 'North America',
    'KYAK': 'North America'  # 修正：CSV中是KYAK而不是KAYAK
}

# 为特定公司添加颜色设置
company_colors = {
    'ABNB': '#ff5895',
    'ALMOSAFER': '#bb5387',
    'BKNG': '#003480',
    'DESP': '#755bd8',
    'EXPE': '#fbcc33',
    'EASEMYTRIP': '#00a0e2',
    'IXIGO': '#e74c3c',
    'MMYT': '#e74c3c',
    'TRIP': '#00af87',
    'TRVG': '#e74c3c',
    'WEGO': '#4e843d',
    'YTRA': '#e74c3c',
    'TCOM': '#2577e3',
    'EDR': '#2577e3',
    'LMN': '#fc03b1',
    'WBJ': '#e74c3c',
    'SEERA': '#750808',
    'PCLN': '#003480',
    'ORBITZ': '#8edbfa',
    'OWW': '#8edbfa',  # Same as Orbitz
    'TRAVELOCITY': '#1d3e5c',
    'SKYSCANNER': '#0770e3',
    'ETRAVELI': '#b2e9ff',
    'KIWI': '#e5fdd4',
    'CLEARTRIP': '#e74c3c',
    'TRAVELOKA': '#38a0e2',
    'FLT': '#d2b6a8',
    'KYAK': '#0770e3',  # Using Skyscanner blue for KAYAK
    'LONG': '#E60010',  # Keep existing color
    'TCEL': '#800080'   # Keep existing color
}

def parse_quarter(quarter_str):
    """Parse quarter string into (year, quarter)"""
    year, quarter = quarter_str.split("'")
    year = int(year)  # Year is already in 4-digit format
    quarter = int(quarter[1])  # Extract quarter number
    return year, quarter

def format_revenue(value):
    """Format revenue values with B for billions and M for millions"""
    if value <= 0:  # 对于零值或负值返回空字符串
        return ''
    elif value >= 1000:
        return f'${value/1000:.2f}B'  # 显示两位小数
    return f'${value:.0f}M'

def get_logo_path(identifier, year):
    """Get the appropriate logo path based on company or ticker and year"""
    logo_base_path = '../99.utility/travel-company-bar-video/logos/'
    
    # 处理特殊公司和按年份变化的logo
    # 统一使用ticker作为查找key
    company = identifier
    
    # 如果输入是ticker，尝试转换为公司名来获取logo
    if identifier in ticker_to_company:
        company = identifier  # 保持原始ticker
    
    if company == 'BKNG' or company == 'PCLN':
        if year < 2014.25:
            return f'{logo_base_path}PCLN_logo.png'
        elif year < 2018.08:
            return f'{logo_base_path}1PCLN_logo.png'
        else:
            return f'{logo_base_path}BKNG_logo.png'
    elif company == 'Cleartrip':
        return f'{logo_base_path}Cleartrip_logo.png'
    elif company == 'TRVG':
        if year < 2013.0:
            return f'{logo_base_path}Trivago1.jpg'
        elif year < 2023.0:
            return f'{logo_base_path}Trivago2.jpg'
        else:
            return f'{logo_base_path}TRVG_logo.png'
    elif company == 'EXPE':
        if year < 2010.0:
            return f'{logo_base_path}1_expedia.png'
        elif year < 2012.0:
            return f'{logo_base_path}Expedia2.jpg'
        else:
            return f'{logo_base_path}EXPE_logo.png'
    elif company == 'TCOM':
        if year < 2019.75:
            return f'{logo_base_path}1TCOM_logo.png'
        else:
            return f'{logo_base_path}TCOM_logo.png'
    elif company == 'Traveloka':
            return f'{logo_base_path}Traveloka_logo.png'
    elif company == 'Yatra':
        return f'{logo_base_path}Yatra_logo.png'
    elif company == 'TRIP':
        if year < 2020.0:
            return f'{logo_base_path}1TRIP_logo.png'
        else:
            return f'{logo_base_path}TRIP_logo.png'
    elif company == 'SEERA':
        if year < 2019.25:
            return f'{logo_base_path}1SEERA_logo.png'
        else:
            return f'{logo_base_path}SEERA_logo.png'
    elif company == 'LMN':
        if year >= 2014.0 and year < 2015.42:
            return f'{logo_base_path}1LMN_logo.png'
        else:
            return f'{logo_base_path}LMN_logo.png'
    elif company == 'Orbitz' or company == 'ORBITZ' or company == 'OWW':
        if year < 2005.0:
            return f'{logo_base_path}Orbitz1.png'
        else:
            return f'{logo_base_path}Orbitz_logo.png'
    elif company == 'TCEL':
        return f'{logo_base_path}TongCheng_logo.png'
    elif company == 'LONG':
        return f'{logo_base_path}Elong_logo.png'
    elif company == 'FLT':
        return f'{logo_base_path}FlightCentre_logo.png'
    elif company == 'WBJ' or company == 'Webjet' or company == 'Webjet OTA':
        return f'{logo_base_path}Webjet_logo.png'
    elif company == 'Webjet':
        return f'{logo_base_path}Webjet_logo.png'
    elif company == 'ABNB':
        return f'{logo_base_path}ABNB_logo.png'
    elif company == 'KYAK' or company == 'KAYAK':  # 修正：CSV中是KYAK而不是KAYAK
        # 使用现有的Kayak logo文件
        if year < 2009.0:
            return f'{logo_base_path}Kayak-Logo-2000-2009.png'
        elif year < 2015.0:
            return f'{logo_base_path}Kayak-Logo-2009-2015.png'
        else:
            return f'{logo_base_path}Kayak-Logo-2015-2018.png'
    else:
        # 检查是否有温度logo，如果有则优先使用
        temp_logo_path = f'{logo_base_path}{company}_temp_logo.png'
        if os.path.exists(temp_logo_path):
            return temp_logo_path
        
        # 尝试匹配不同格式的logo文件
        for file_extension in ['png', 'jpg', 'jpeg', 'svg']:
            logo_path = f'{logo_base_path}{company}_logo.{file_extension}'
            if os.path.exists(logo_path):
                return logo_path
    
    print(f"Warning: Logo not found for {company}")
    return None

def get_encoded_image(logo_path):
    """将logo转换为base64编码以便直接在Plotly中使用"""
    if not logo_path or not os.path.exists(logo_path):
        return None
    
    try:
        with open(logo_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            # 判断文件类型
            if logo_path.lower().endswith('.png'):
                return f'data:image/png;base64,{encoded_string}'
            elif logo_path.lower().endswith(('.jpg', '.jpeg')):
                return f'data:image/jpeg;base64,{encoded_string}'
            elif logo_path.lower().endswith('.svg'):
                return f'data:image/svg+xml;base64,{encoded_string}'
            else:
                return None
    except Exception as e:
        print(f"Error encoding image {logo_path}: {e}")
        return None

def create_visualization():
    """Create interactive Plotly visualization for travel company revenue data"""
    print("Starting Plotly Travel Company Revenue Visualization.")
    
    # Load the data from CSV
    data = pd.read_csv('../99.utility/travel-company-bar-video/Animated Bubble Chart_ Historic Financials Online Travel Industry - Revenue2.csv')
    print(f"Loaded {len(data)} rows of data.")
    
    # Handle "Revenue" row
    if "Revenue" in data.iloc[0].values:
        data = data.iloc[1:].reset_index(drop=True)
        print(f"Processed quarterly data down to {len(data)} rows.")
    
    # Set the first column as index (quarter)
    quarters = data.iloc[:, 0].tolist()
    data.set_index(data.columns[0], inplace=True)
    
    # 准备所有季度的数据
    all_quarters_data = []
    
    # 确保每个时间点始终显示固定数量的柱状图
    fixed_bar_count = args.max_companies
    
    # Process each quarter
    iterations = 0
    start_time = pd.Timestamp.now()
    
    for quarter in tqdm(quarters, desc="Processing data"):
        iterations += 1
        year, q = parse_quarter(quarter)
        decimal_year = year + (q - 1) * 0.25
        
        quarter_data = data.loc[quarter].copy()
        
        # Convert values to numeric
        for col in quarter_data.index:
            if pd.notna(quarter_data[col]) and quarter_data[col] != '':
                # Remove $, commas, and 'M' or 'B' indicators
                value_str = str(quarter_data[col]).replace('$', '').replace(',', '').strip()
                if 'B' in value_str:
                    # Convert billions to millions
                    quarter_data[col] = float(value_str.replace('B', '')) * 1000
                elif 'M' in value_str:
                    quarter_data[col] = float(value_str.replace('M', ''))
                else:
                    try:
                        quarter_data[col] = float(value_str)
                    except:
                        quarter_data[col] = np.nan
            else:
                quarter_data[col] = np.nan
        
        # Drop NaN values and get top companies by revenue
        quarter_data = quarter_data.dropna()
        
        # 排除指定公司
        companies_to_drop = []
        for company_name in list(quarter_data.index):
            # 直接检查公司名称是否在排除列表中
            if company_name in excluded_columns:
                companies_to_drop.append(company_name)
                continue
            
            # 检查公司名称转为小写后是否匹配
            company_lower = company_name.lower()
            exclude_this = False
            for excluded in excluded_columns:
                if excluded.lower() == company_lower:
                    companies_to_drop.append(company_name)
                    exclude_this = True
                    break
            
            if exclude_this:
                continue
                
            # 如果是通过ticker排除，继续检查
            if company_lower in company_to_ticker:
                ticker = company_to_ticker[company_lower]
                if ticker in excluded_companies:
                    companies_to_drop.append(company_name)
                    continue
            
            # 检查特殊映射
            if company_lower in special_column_to_ticker:
                ticker = special_column_to_ticker[company_lower]
                if ticker in excluded_companies:
                    companies_to_drop.append(company_name)
                    continue
                    
            # 获取公司对应的ticker
            ticker = None
            if company_lower in special_column_to_ticker:
                ticker = special_column_to_ticker[company_lower]
            elif company_lower in company_to_ticker:
                ticker = company_to_ticker[company_lower]
            else:
                ticker = company

            # 新增：2005.5到2015.5之间不要显示LMN
            if ticker == 'LMN' and 2005.5 <= decimal_year <= 2014.5:
                companies_to_drop.append(company_name)
                continue
            
            # 检查公司是否已经IPO
            if ticker in ipo_dates and decimal_year < ipo_dates[ticker]:
                # 特殊处理Booking Holdings (BKNG)，它在2018之前是Priceline (PCLN)
                if ticker == 'BKNG':
                    # 如果当前时间早于PCLN的IPO日期，则排除
                    if decimal_year < ipo_dates['PCLN']:
                        companies_to_drop.append(company_name)
                        continue
                    # 如果在PCLN IPO日期和BKNG改名日期之间，则不排除
                else:
                    companies_to_drop.append(company_name)
                    continue
        
        # 批量删除需要排除的公司
        if companies_to_drop:
            quarter_data = quarter_data.drop(companies_to_drop)
        
        top_companies = quarter_data.sort_values(ascending=False).head(fixed_bar_count)
        
        companies = []
        revenues = []
        colors = []
        hover_texts = []
        logos = []
        y_positions = []  # Add numerical y positions
        
        # 计算实际有效的公司数量
        actual_company_count = len(top_companies)
        
        # Create lists for each company's data
        for i, (company, revenue) in enumerate(top_companies.items()):
            if pd.notna(revenue) and revenue > 0:
                # 确定正确的ticker显示
                ticker = None
                company_lower = company.lower()
                
                # 尝试从特殊映射中获取ticker
                if company_lower in special_column_to_ticker:
                    ticker = special_column_to_ticker[company_lower]
                # 尝试从反向映射中获取ticker
                elif company_lower in company_to_ticker:
                    ticker = company_to_ticker[company_lower]
                # 如果都没有匹配，使用原始公司名作为ticker
                else:
                    ticker = company
                
                # 特殊处理BKNG ticker - 在2018.08之前显示为PCLN
                display_ticker = ticker
                if ticker == 'BKNG' and decimal_year < 2018.08:
                    display_ticker = 'PCLN'
                
                # Get company full name and region
                company_name = ticker_to_company.get(ticker, company)
                region = company_to_region.get(ticker, company_to_region.get(company, 'Other'))
                
                # 为特定公司指定颜色，其他公司根据区域设置颜色
                if ticker in company_colors:
                    color = company_colors[ticker]
                elif company in company_colors:
                    color = company_colors[company]
                else:
                    color = region_colors.get(region, '#808080')
                
                # Get logo path and encode it
                logo_path = get_logo_path(ticker, decimal_year)
                encoded_logo = get_encoded_image(logo_path) if logo_path else None
                
                companies.append(display_ticker)  # 使用处理后的ticker
                revenues.append(revenue)
                colors.append(color)
                logos.append(encoded_logo)
                y_positions.append(i)  # Use numerical position
                
                hover_text = f"<b>{company_name}</b><br>"
                hover_text += f"Revenue: {format_revenue(revenue)}<br>"
                hover_text += f"Region: {region}<br>"
                hover_text += f"Ticker: {display_ticker}"
                hover_texts.append(hover_text)
        
        # 添加虚拟空白bar来填满固定数量的位置
        for i in range(actual_company_count, fixed_bar_count):
            companies.append("")
            revenues.append(0)  # 零收入的bar不会显示
            colors.append('rgba(0,0,0,0)')  # 透明颜色
            logos.append(None)
            y_positions.append(i)
            hover_texts.append("")
        
        # Store data
        quarter_info = {
            'quarter': quarter,
            'companies': companies,
            'revenues': revenues,
            'colors': colors,
            'hover_texts': hover_texts,
            'formatted_revenues': [format_revenue(rev) for rev in revenues],  # 使用修改后的format_revenue函数
            'logos': logos,
            'y_positions': y_positions,  # Add y_positions to the data
            'actual_company_count': actual_company_count  # 记录实际公司数量
        }
        all_quarters_data.append(quarter_info)
    
    end_time = pd.Timestamp.now()
    elapsed_time = (end_time - start_time).total_seconds()
    iterations_per_second = iterations / elapsed_time if elapsed_time > 0 else 0
    print(f"Completed visualization data preparation for {iterations} rows at {iterations_per_second:.2f} iterations per second.")
    
    # Get initial data
    initial_data = all_quarters_data[0]
    
    # Create initial chart
    fig = go.Figure()
    
    # Add traces - Note: Using numerical y positions
    fig.add_trace(
            go.Bar(
                x=initial_data['revenues'],
                y=initial_data['y_positions'],
                orientation='h',
                marker=dict(color=initial_data['colors'],
                            line=dict(width=0, color='rgba(0,0,0,0)')),
                hoverinfo='none',
                width=0.8,  # 增加柱状图宽度为0.8，与airline_plotly_viz相同
                showlegend=False
            )
    )
    
    # Add text layer with transparent bars - Add vertical offset
    fig.add_trace(
            go.Bar(
                x=initial_data['revenues'],
                y=[y - 0.05 for y in initial_data['y_positions']],  # Add small offset for text
                orientation='h',
                marker=dict(color='rgba(0,0,0,0)',
                            line=dict(width=0, color='rgba(0,0,0,0)')),
                text=initial_data['formatted_revenues'],
                textposition='outside',
                textfont=dict(
                    family='Monda',
                    size=14,
                    color='black'
                ),
                cliponaxis=False,
                textangle=0,
                constraintext='none',
                hoverinfo='none',
                width=0.8,  # 保持与上面柱状图相同的宽度
                showlegend=False
            )
    )
    
    # Add logos with consistent size and proper alignment
    max_revenue = max([max([r for r in quarter_info['revenues'] if r > 0] or [1]) for quarter_info in all_quarters_data])
    
    # 修改初始图表的logo显示位置，使其显示在revenue数字旁边
    for i, (company, revenue, logo, formatted_revenue) in enumerate(zip(
        initial_data['companies'], 
        initial_data['revenues'], 
        initial_data['logos'], 
        initial_data['formatted_revenues']
    )):
        if logo and revenue > 0:
            # 计算logo位置 - 放在revenue文本右侧，增加偏移量和尺寸
            logo_x = revenue + (max_revenue * 0.07)  # 偏移量不变
            logo_y = i
            
            # 为特定公司设置不同的logo尺寸
            logo_width = max_revenue * 0.15  # 默认logo宽度
            logo_height = 1.0  # 默认logo高度
            
            # 根据公司调整logo尺寸
            if company == 'Etraveli' or company == 'LONG' or company == 'eLong':
                logo_width = max_revenue * 0.09  # 缩小40%
                logo_height = 0.6  # 缩小40%
            # 如果是Lastminute.com，设置更大的尺寸
            elif company == 'LMN':
                logo_width = max_revenue * 0.2  # 放大33%
                logo_height = 1.35  # 放大35%
            # 处理Trip.com (TCOM) - 根据时间判断使用不同的尺寸
            elif company == 'TCOM':
                # 仅当是第二个logo时才特殊放大（2019.75之后）
                if decimal_year >= 2019.75:
                    logo_width = max_revenue * 0.3  # 放大到原来的两倍
                    logo_height = 2.0  # 放大到原来的两倍
            
            fig.add_layout_image(
                dict(
                    source=logo,
                    xref="x",
                    yref="y",
                    x=logo_x,
                    y=logo_y,
                    sizex=logo_width,
                    sizey=logo_height,
                    xanchor="left",
                    yanchor="middle",
                    sizing="contain",
                    opacity=1.0
                )
            )

    # 调整x轴以容纳logo和文本
    x_axis_range = [0, max_revenue * 1.5]  # 进一步增加空间
    
    # 设置固定的y轴范围
    y_axis_range = [-0.5, fixed_bar_count - 0.5]
    
    # 添加左侧垂直线
    vertical_line = {
        'type': 'line',
        'x0': 0,
        'y0': y_axis_range[0],
        'x1': 0,
        'y1': y_axis_range[1],
        'line': {
            'color': 'lightgrey',
            'width': 1,
            'dash': 'dot'
        }
    }
    
    # Update layout with fixed yaxis range
    fig.update_layout(
        title={
            'text': "Travel Companies Revenue Visualization",
            'y':0.95,
            'x':0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'family': 'Monda', 'size': 24}
        },
        width=args.width,
        height=args.height,
        xaxis=dict(
            title={
                'text': "Revenue (Million USD)",
                'font': {'family': 'Monda', 'size': 16}
            },
            tickformat="$,.0f",
            range=x_axis_range,
            showgrid=True,
            gridcolor='lightgrey',
            gridwidth=1,
            griddash='dot',
            zeroline=True,
            zerolinecolor='lightgrey',
            zerolinewidth=1,
            tickfont={'family': 'Monda', 'size': 14}
        ),
        yaxis=dict(
            title={
                'text': "",
                'font': {'family': 'Monda', 'size': 16}
            },
            tickmode='array',
            tickvals=initial_data['y_positions'][:initial_data['actual_company_count']],  # 只显示有效公司的刻度
            ticktext=initial_data['companies'][:initial_data['actual_company_count']],    # 只显示有效公司的名称
            tickfont={'family': 'Monda', 'size': 14},
            fixedrange=True,
            range=y_axis_range,  # 使用固定的y轴范围
            autorange='reversed'  # 保持反向排序
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        hovermode="closest",
        font=dict(family="Monda", size=14),
        margin=dict(l=100, r=150, t=100, b=140),
        showlegend=False,
        xaxis_range=x_axis_range,
        bargap=0.15,  # 减小gap值为0.15，与airline_plotly_viz相同
        bargroupgap=0.1,
        shapes=[vertical_line],  # 添加垂直线
        uniformtext=dict(
            mode='hide',
            minsize=14
        ),
        barmode='group'
    )
    
    # Convert to HTML
    html_content = pio.to_html(
        fig,
        include_plotlyjs=False,
        full_html=False,
        div_id='travel-chart'
    )
    
    # Convert data to JSON for JavaScript
    quarters_data_json = json.dumps(all_quarters_data)
    
    # Create custom HTML with updated JavaScript
    custom_html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Travel Company Revenue Visualization</title>
    <script src="https://cdn.plot.ly/plotly-2.27.1.min.js"></script>
    <style>
        body {{
            font-family: 'Monda', Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: white;
        }}
        .control-panel {{
            text-align: center;
            margin-top: 20px;
            margin-bottom: 30px;
        }}
        .quarter-display {{
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .slider-container {{
            width: 80%;
            margin: 0 auto;
            margin-bottom: 15px;
        }}
        .button-container {{
            margin-top: 10px;
        }}
        button {{
            font-family: 'Monda', Arial, sans-serif;
            padding: 8px 20px;
            margin: 0 5px;
            cursor: pointer;
            background-color: #f0f0f0;
            border: 1px solid #ccc;
            border-radius: 4px;
        }}
        button:hover {{
            background-color: #e0e0e0;
        }}
        #quarter-slider {{
            width: 100%;
        }}
    </style>
</head>
<body>
    {html_content}
    
    <div class="control-panel">
        <div class="quarter-display">
            <span id="current-quarter">{initial_data['quarter']}</span>
        </div>
        <div class="slider-container">
            <input type="range" id="quarter-slider" min="0" max="{len(quarters) - 1}" value="0">
        </div>
        <div class="button-container">
            <button id="play-button">Play</button>
            <button id="pause-button">Pause</button>
            <button id="reset-button">Reset</button>
        </div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const allQuartersData = {quarters_data_json};
            let currentQuarterIndex = 0;
            let isPlaying = false;
            let animationInterval = null;
            const chartDiv = document.getElementById('travel-chart');
            const currentQuarterDisplay = document.getElementById('current-quarter');
            const quarterSlider = document.getElementById('quarter-slider');
            const playButton = document.getElementById('play-button');
            const pauseButton = document.getElementById('pause-button');
            const resetButton = document.getElementById('reset-button');
            
            // 初始数据设置
            const initialData = allQuartersData[0];
            const traces = [
                {{
                    type: 'bar',
                    x: initialData.revenues,
                    y: initialData.y_positions,
                    orientation: 'h',
                    marker: {{
                        color: initialData.colors,
                        line: {{
                            width: 0,
                            color: 'rgba(0,0,0,0)'
                        }}
                    }},
                    hoverinfo: 'none',
                    width: 0.8,  // 增加柱状图宽度为0.8，与airline_plotly_viz相同
                    showlegend: false
                }},
                {{
                    type: 'bar',
                    x: initialData.revenues,
                    y: initialData.y_positions.map(y => y - 0.05),  // 文本的轻微偏移
                    orientation: 'h',
                    marker: {{
                        color: 'rgba(0,0,0,0)',
                        line: {{
                            width: 0,
                            color: 'rgba(0,0,0,0)'
                        }}
                    }},
                    text: initialData.formatted_revenues,
                    textposition: 'outside',
                    textfont: {{
                        family: 'Monda',
                        size: 14,
                        color: 'black'
                    }},
                    cliponaxis: false,
                    textangle: 0,
                    constraintext: 'none',
                    hoverinfo: 'none',
                    width: 0.8,  // 保持与上面柱状图相同的宽度
                    showlegend: false
                }}
            ];
            
            const layout = {{
                title: {{
                    text: "Travel Company Revenue Visualization",
                    y: 0.95,
                    x: 0.5,
                    xanchor: 'center',
                    yanchor: 'top',
                    font: {{family: 'Monda', size: 24}}
                }},
                width: {args.width},
                height: {args.height},
                xaxis: {{
                    title: {{
                        text: "Revenue",
                        font: {{family: 'Monda', size: 16}}
                    }},
                    tickformat: "$,.0f",
                    range: [0, Math.max(...initialData.revenues) * 1.5],
                    showgrid: true,
                    gridcolor: 'lightgrey',
                    gridwidth: 1,
                    griddash: 'dot',
                    zeroline: true,
                    zerolinecolor: 'lightgrey',
                    zerolinewidth: 1,
                    tickfont: {{family: 'Monda', size: 14}}
                }},
                yaxis: {{
                    title: {{
                        text: "",
                        font: {{family: 'Monda', size: 16}}
                    }},
                    tickmode: 'array',
                    tickvals: initialData.y_positions,
                    ticktext: initialData.companies,
                    tickfont: {{family: 'Monda', size: 14}},
                    autorange: 'reversed',
                    fixedrange: true
                }},
                plot_bgcolor: 'white',
                paper_bgcolor: 'white',
                hovermode: "closest",
                font: {{family: "Monda", size: 14}},
                margin: {{l: 100, r: 150, t: 100, b: 140}},
                showlegend: false,  // 关闭图例显示
                images: initialData.logos.map((logo, i) => 
                    logo ? {{
                        source: logo,
                        xref: "x",
                        yref: "y",
                        x: initialData.revenues[i] + (Math.max(...initialData.revenues) * 0.07),
                        y: i,
                        sizex: initialData.companies[i] === 'Etraveli' || initialData.companies[i] === 'LONG' || initialData.companies[i] === 'eLong' ? 
                              Math.max(...initialData.revenues) * 0.09 : // Etraveli和eLong使用更小的logo
                              initialData.companies[i] === 'LMN' ?
                              Math.max(...initialData.revenues) * 0.2 : // Lastminute.com使用更大的logo
                              // 为Trip.com使用特殊尺寸 (只针对第二个logo)
                              initialData.companies[i] === 'TCOM' && parseFloat(initialData.quarter.split("'")[0]) + 
                                                   (parseInt(initialData.quarter.split("'")[1].replace('Q', '')) - 1) / 4 >= 2019.75 ? 
                              Math.max(...initialData.revenues) * 0.3 : // TCOM第二个logo更大，放大到两倍
                              Math.max(...initialData.revenues) * 0.15,  // 其他公司使用正常大小
                        sizey: initialData.companies[i] === 'Etraveli' || initialData.companies[i] === 'LONG' || initialData.companies[i] === 'eLong' ? 
                              0.6 : 
                              initialData.companies[i] === 'LMN' ?
                              1.35 : 
                              // 为Trip.com使用特殊高度 (只针对第二个logo)
                              initialData.companies[i] === 'TCOM' && parseFloat(initialData.quarter.split("'")[0]) + 
                                                   (parseInt(initialData.quarter.split("'")[1].replace('Q', '')) - 1) / 4 >= 2019.75 ?
                              2.0 : 1.0,               // 根据公司调整logo高度
                        xanchor: "left",
                        yanchor: "middle",
                        sizing: "contain",
                        opacity: 1.0
                    }} : null
                ).filter(img => img !== null),
                bargap: 0.15,  // 减小gap值为0.15，与airline_plotly_viz相同
                bargroupgap: 0.1,
                uniformtext: {{
                    mode: 'hide',
                    minsize: 14
                }},
                barmode: 'group',
                shapes: [
                    {{  // 添加左侧垂直线
                        type: 'line',
                        x0: 0,
                        y0: -0.5,
                        x1: 0,
                        y1: 14.5,
                        line: {{
                            color: 'lightgrey',
                            width: 1,
                            dash: 'dot'
                        }}
                    }}
                ]
            }};
            
            // 初始化图表
            Plotly.newPlot(chartDiv, traces, layout);
            
            // 历史最大值记录
            let historicalMaxRevenue = Math.max(...initialData.revenues);
            
            // 平滑动画函数
            function playAnimation() {{
                if (isPlaying) return;
                isPlaying = true;
                
                let lastFrameTime = performance.now();
                const quarterDuration = {args.transition_duration};  // 每个季度持续时间
                let currentTime = 0;
                
                // 平滑动画帧函数
                function animate() {{
                    if (!isPlaying) return;
                    
                    const now = performance.now();
                    const deltaTime = now - lastFrameTime;
                    lastFrameTime = now;
                    
                    currentTime += deltaTime;
                    const totalDuration = quarterDuration * (allQuartersData.length - 1);
                    const normalizedTime = (currentTime % totalDuration) / totalDuration;
                    
                    const exactIndex = normalizedTime * (allQuartersData.length - 1);
                    const currentIndex = Math.floor(exactIndex);
                    const nextIndex = (currentIndex + 1) % allQuartersData.length;
                    const progress = exactIndex - currentIndex;
                    
                    quarterSlider.value = currentIndex;
                    
                    const currentData = allQuartersData[currentIndex];
                    const nextData = allQuartersData[nextIndex];
                    
                    // 解析当前帧和下一帧的年份
                    const currentYear = parseFloat(currentData.quarter.split("'")[0]) + 
                                       (parseInt(currentData.quarter.split("'")[1].replace('Q', '')) - 1) / 4;
                    const nextYear = parseFloat(nextData.quarter.split("'")[0]) + 
                                    (parseInt(nextData.quarter.split("'")[1].replace('Q', '')) - 1) / 4;
                    
                    // 增加新公司处理逻辑
                    // 检查下一季度是否有新的公司出现，如果有则直接显示它们
                    const currentCompanies = new Set(currentData.companies);
                    const nextCompanies = new Set(nextData.companies);
                    
                    // 创建一个空的结果数组
                    let interpolatedData = [];
                    
                    // 处理所有当前和下一帧中出现的公司
                    const allCompanies = new Set([...currentData.companies, ...nextData.companies]);
                    
                    // 跟踪已处理的公司
                    let processedCompanies = new Set();
                    
                    // 第一步：处理当前帧中存在的公司
                    for (let i = 0; i < currentData.companies.length; i++) {{
                        const company = currentData.companies[i];
                        const currentRevenue = currentData.revenues[i];
                        
                        // 跳过空公司名或零收入
                        if (!company || currentRevenue <= 0) continue;
                        
                        // 检查公司是否会在下一帧消失
                        const nextCompanyIndex = nextData.companies.indexOf(company);
                        const willDisappear = nextCompanyIndex === -1;
                        
                        // 如果公司将要消失
                        if (willDisappear) {{
                            // 只在过渡开始时显示，超过阈值则完全消失
                            if (progress <= 0.05) {{
                                interpolatedData.push({{
                                    company: company,
                                    revenue: currentRevenue,
                                    logo: currentData.logos[i],
                                    color: currentData.colors[i],
                                    formattedRevenue: formatRevenue(currentRevenue),
                                    y_position: interpolatedData.length
                                }});
                            }}
                        }} else {{
                            // 公司继续存在，进行正常插值
                            const nextRevenue = nextData.revenues[nextCompanyIndex];
                            interpolatedData.push({{
                                company: company,
                                revenue: currentRevenue + (nextRevenue - currentRevenue) * progress,
                                logo: currentData.logos[i],
                                color: currentData.colors[i],
                                formattedRevenue: formatRevenue(currentRevenue + (nextRevenue - currentRevenue) * progress),
                                y_position: interpolatedData.length
                            }});
                        }}
                        
                        processedCompanies.add(company);
                    }}
                    
                    // 第二步：处理下一帧中新出现的公司
                    for (let i = 0; i < nextData.companies.length; i++) {{
                        const company = nextData.companies[i];
                        const nextRevenue = nextData.revenues[i];
                        
                        // 跳过空公司名、零收入或已处理的公司
                        if (!company || nextRevenue <= 0 || processedCompanies.has(company)) continue;
                        
                        // 新出现的公司 - 当进度超过阈值时直接完整显示
                        if (progress > 0.05) {{
                            interpolatedData.push({{
                                company: company,
                                revenue: nextRevenue, // 直接使用完整值
                                logo: nextData.logos[i],
                                color: nextData.colors[i],
                                formattedRevenue: formatRevenue(nextRevenue),
                                y_position: interpolatedData.length
                            }});
                        }}
                    }}
                    
                    // 按收入排序
                    interpolatedData.sort((a, b) => b.revenue - a.revenue);
                    
                    // 确保始终有固定数量的柱状图 - 添加空白占位项
                    const maxDisplayedCompanies = 15;
                    while (interpolatedData.length < maxDisplayedCompanies) {{
                        interpolatedData.push({{
                            company: "",
                            revenue: 0,
                            logo: null,
                            color: 'rgba(0,0,0,0)',
                            formattedRevenue: '',
                            y_position: interpolatedData.length
                        }});
                    }}
                    
                    // 如果数据超过了最大显示数量，截取前15个
                    if (interpolatedData.length > maxDisplayedCompanies) {{
                        interpolatedData = interpolatedData.slice(0, maxDisplayedCompanies);
                    }}
                    
                    // 提取已排序的数据
                    const companiesSorted = interpolatedData.map(d => d.company);
                    const revenuesSorted = interpolatedData.map(d => d.revenue);
                    const logosSorted = interpolatedData.map(d => d.logo);
                    const colorsSorted = interpolatedData.map(d => d.color);
                    const formattedRevenuesSorted = interpolatedData.map(d => d.formattedRevenue);
                    const yPositionsSorted = interpolatedData.map((d, i) => i);
                    
                    // 计算当前最大收入和历史最大收入
                    const currentMaxRevenue = Math.max(...revenuesSorted);
                    historicalMaxRevenue = Math.max(historicalMaxRevenue, currentMaxRevenue);
                    const xAxisMax = historicalMaxRevenue * 1.5;
                    
                    try {{
                        // 更新图表
                        Plotly.update(chartDiv, {{
                            'x': [revenuesSorted, revenuesSorted],
                            'y': [yPositionsSorted, yPositionsSorted.map(y => y - 0.05)],  // 文本偏移
                            'marker.color': [colorsSorted, Array(colorsSorted.length).fill('rgba(0,0,0,0)')],
                            'text': [[], formattedRevenuesSorted]
                        }}, {{
                            'yaxis.ticktext': companiesSorted,
                            'yaxis.tickvals': yPositionsSorted,
                            'xaxis.range': [0, xAxisMax]
                        }});
                        
                        // 单独处理logo图像和图表形状
                        const logoImages = [];
                        
                        for (let i = 0; i < logosSorted.length; i++) {{
                            const logo = logosSorted[i];
                            if (!logo) continue;
                            
                            const company = companiesSorted[i];
                            if (!company || revenuesSorted[i] <= 0) continue;
                            
                            // 确定是否是新出现的公司
                            const isNewCompany = !currentCompanies.has(company);
                            // 确定是否是即将消失的公司
                            const willDisappear = !nextCompanies.has(company);
                            
                            // 新公司且进度未超过阈值，或者要消失的公司且进度超过阈值，则跳过
                            if ((isNewCompany && progress <= 0.05) || (willDisappear && progress > 0.05)) {{
                                continue;
                            }}
                            
                            // 为特定公司设置不同的logo尺寸
                            let logoSizeX = historicalMaxRevenue * 0.15;  // 默认logo宽度
                            let logoSizeY = 1.0;  // 默认logo高度
                            
                            // 如果是Etraveli或eLong，设置更小的尺寸
                            if (company === 'Etraveli' || company === 'LONG' || company === 'eLong') {{
                                logoSizeX = historicalMaxRevenue * 0.09;  // 缩小40%
                                logoSizeY = 0.6;  // 缩小40%
                            }}
                            // 如果是Lastminute.com，设置更大的尺寸
                            else if (company === 'LMN') {{
                                logoSizeX = historicalMaxRevenue * 0.2;  // 放大33%
                                logoSizeY = 1.35;  // 放大35%
                            }}
                            // 处理Trip.com (TCOM) - 根据时间判断使用不同的尺寸
                            else if (company === 'TCOM') {{
                                // 获取当前季度的年份
                                const currentYear = parseFloat(currentData.quarter.split("'")[0]) + 
                                                   (parseInt(currentData.quarter.split("'")[1].replace('Q', '')) - 1) / 4;
                                // 仅当是第二个logo时才特殊放大（2019.75之后）
                                if (currentYear >= 2019.75) {{
                                    logoSizeX = historicalMaxRevenue * 0.3;  // 放大到原来的两倍
                                    logoSizeY = 2.0;  // 放大到原来的两倍
                                }}
                            }}
                            
                            logoImages.push({{
                                source: logo,
                                xref: "x",
                                yref: "y",
                                x: revenuesSorted[i] + (xAxisMax * 0.05),
                                y: i,
                                sizex: logoSizeX,
                                sizey: logoSizeY,
                                xanchor: "left",
                                yanchor: "middle",
                                sizing: "contain",
                                opacity: 1.0  // 总是完全不透明
                            }});
                        }}
                        
                        // 定义左侧垂直线
                        const verticalLine = {{
                            type: 'line',
                            x0: 0,
                            y0: -0.5,
                            x1: 0,
                            y1: 14.5,
                            line: {{
                                color: 'lightgrey',
                                width: 1,
                                dash: 'dot'
                            }}
                        }};
                        
                        // 更新logo图像和形状
                        Plotly.relayout(chartDiv, {{
                            'images': logoImages,
                            'shapes': [verticalLine]  // 确保垂直线一直显示
                        }});
                        
                        // 更新季度显示
                        const quarterText = interpolateQuarters(currentData.quarter, nextData.quarter, progress);
                        currentQuarterDisplay.textContent = quarterText;
                        
                    }} catch (e) {{
                        console.error("Animation error:", e);
                    }}
                    
                    requestAnimationFrame(animate);
                }}
                
                requestAnimationFrame(animate);
            }}
            
            // 格式化收入显示，修改为零值不显示
            function formatRevenue(value) {{
                if (value <= 0) {{
                    return '';  // 零值或负值返回空字符串
                }}
                if (value >= 1000) {{
                    return '$' + (value/1000).toFixed(2) + 'B';
                }}
                return '$' + Math.round(value) + 'M';
            }}
            
            // 季度插值函数
            function interpolateQuarters(q1, q2, progress) {{
                const [year1, quarter1] = q1.split("'").map(x => parseInt(x.replace('Q', '')));
                let [year2, quarter2] = q2.split("'").map(x => parseInt(x.replace('Q', '')));
                
                if (year2 < year1) {{
                    year2 = year1;
                }}
                
                const yearDiff = year2 - year1;
                const quarterDiff = quarter2 - quarter1;
                const totalQuarters = yearDiff * 4 + quarterDiff;
                const interpolatedQuarters = quarter1 + totalQuarters * progress;
                
                const interpolatedYear = Math.floor(year1 + (interpolatedQuarters - 1) / 4);
                const interpolatedQuarter = Math.floor(((interpolatedQuarters - 1) % 4) + 1);
                
                return interpolatedYear + "'Q" + interpolatedQuarter;
            }}
            
            // 暂停动画
            function pauseAnimation() {{
                isPlaying = false;
            }}
            
            // 重置动画
            function resetAnimation() {{
                pauseAnimation();
                quarterSlider.value = 0;
                currentQuarterIndex = 0;
                updateChart(0);
            }}
            
            // 更新图表到特定季度
            function updateChart(index) {{
                if (index < 0 || index >= allQuartersData.length) return;
                
                const currentData = allQuartersData[index];
                currentQuarterIndex = index;
                
                try {{
                    // 解析当前季度的年份
                    const currentYear = parseFloat(currentData.quarter.split("'")[0]) + 
                                      (parseInt(currentData.quarter.split("'")[1].replace('Q', '')) - 1) / 4;
                    
                    // 准备数据 - 从当前季度提取有效公司数据
                    let displayData = [];
                    for (let i = 0; i < currentData.companies.length; i++) {{
                        if (currentData.revenues[i] > 0) {{
                            displayData.push({{
                                company: currentData.companies[i],
                                revenue: currentData.revenues[i],
                                logo: currentData.logos[i],
                                color: currentData.colors[i],
                                formattedRevenue: currentData.formatted_revenues[i],
                                y_position: i
                            }});
                        }}
                    }}
                    
                    // 按收入排序
                    displayData.sort((a, b) => b.revenue - a.revenue);
                    
                    // 限制最多显示15个公司
                    const maxDisplayedCompanies = 15;
                    
                    // 如果数据超过了最大显示数量，截取前15个
                    if (displayData.length > maxDisplayedCompanies) {{
                        displayData = displayData.slice(0, maxDisplayedCompanies);
                    }}
                    
                    // 确保始终有固定数量的柱状图 - 添加空白占位项
                    while (displayData.length < maxDisplayedCompanies) {{
                        displayData.push({{
                            company: "",
                            revenue: 0,
                            logo: null,
                            color: 'rgba(0,0,0,0)',
                            formattedRevenue: '',
                            y_position: displayData.length
                        }});
                    }}
                    
                    // 提取排序后的数据
                    const companiesSorted = displayData.map(d => d.company);
                    const revenuesSorted = displayData.map(d => d.revenue);
                    const colorsSorted = displayData.map(d => d.color);
                    const formattedRevenuesSorted = displayData.map(d => d.formattedRevenue);
                    const logosSorted = displayData.map(d => d.logo);
                    const yPositionsSorted = displayData.map((d, i) => i);
                    
                    // 更新图表数据
                    Plotly.update(chartDiv, {{
                        'x': [revenuesSorted, revenuesSorted],
                        'y': [yPositionsSorted, yPositionsSorted.map(y => y - 0.05)],
                        'marker.color': [colorsSorted, Array(colorsSorted.length).fill('rgba(0,0,0,0)')],
                        'text': [[], formattedRevenuesSorted]
                    }}, {{
                        'yaxis.ticktext': companiesSorted,
                        'yaxis.tickvals': yPositionsSorted,
                        'xaxis.range': [0, Math.max(...revenuesSorted.filter(r => r > 0)) * 1.5 || 100]
                    }});
                    
                    // 更新logo
                    const logos = logosSorted.filter(l => l !== null);
                    const maxRevenue = Math.max(...revenuesSorted.filter(r => r > 0)) || 100;
                    
                    // 只为有实际收入和logo的公司添加logo
                    const newImages = [];
                    
                    for (let i = 0; i < displayData.length; i++) {{
                        const item = displayData[i];
                        if (item.logo && item.revenue > 0) {{
                            // 计算logo位置 - 放在revenue文本右侧，增加偏移量
                            const logoX = item.revenue + (maxRevenue * 0.07);
                            
                            newImages.push({{
                                source: item.logo,
                                xref: "x",
                                yref: "y",
                                x: logoX,
                                y: i,
                                sizex: maxRevenue * 0.15,  // 增大logo宽度
                                sizey: 1.0,                // 增大logo高度
                                xanchor: "left",
                                yanchor: "middle",
                                sizing: "contain",
                                opacity: 1.0
                            }});
                        }}
                    }}
                    
                    // 应用logo变更
                    if (newImages.length > 0) {{
                        Plotly.relayout(chartDiv, {{
                            'images': newImages,
                            'xaxis.range': [0, maxRevenue * 1.5]
                        }});
                    }}
                    
                    // 更新季度显示
                    currentQuarterDisplay.textContent = currentData.quarter;
                    
                }} catch (e) {{
                    console.error("Update error:", e);
                }}
            }}
            
            // 事件监听器设置
            quarterSlider.addEventListener('input', function() {{
                pauseAnimation();
                updateChart(parseInt(this.value));
            }});
            
            playButton.addEventListener('click', playAnimation);
            pauseButton.addEventListener('click', pauseAnimation);
            resetButton.addEventListener('click', resetAnimation);
            
            // 自动开始动画
            setTimeout(playAnimation, 1000);
        }});
    </script>
</body>
</html>
"""

    
    # Save HTML file
    with open(args.output, 'w') as f:
        f.write(custom_html)
    
    print(f"Visualization saved successfully to {args.output}")
    
    # Automatically open the HTML file in browser
    output_path = Path(args.output).resolve()
    webbrowser.open('file://' + str(output_path), new=2)
    
    return fig

if __name__ == "__main__":
    print("Starting Plotly Travel Company Revenue Visualization")
    fig = create_visualization()
    print("Visualization complete!") 