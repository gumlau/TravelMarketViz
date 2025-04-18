import os
import cv2
import glob
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import re
import subprocess
import shutil
import sys
import time
import matplotlib.colors as mcolors
import matplotlib.font_manager as fm
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
from PIL import Image, ImageFilter, ImageEnhance
from tqdm import tqdm
import multiprocessing as mp
from functools import partial
import warnings
import matplotlib
import io
from io import BytesIO
matplotlib.use('Agg')  # Use Agg backend for better performance

# Add argument parser
parser = argparse.ArgumentParser(description='Generate airline revenue bar chart race visualization directly as video')
parser.add_argument('--fps', type=int, default=30, help='Frames per second (default: 60)')
parser.add_argument('--output', type=str, default='output/airline_revenue.mp4', help='Output video file path')
parser.add_argument('--quality', type=str, choices=['high', 'medium', 'low'], default='high', 
                    help='Video quality: high, medium, or low (default: high)')
parser.add_argument('--frames-per-year', type=int, default=300, help='Number of frames to generate per year (default: 600)')
parser.add_argument('--preserve-colors', action='store_true', default=True, 
                    help='Preserve original colors in video (default: True)')
parser.add_argument('--quarters-only', action='store_true', help='Only generate frames for each quarter')
parser.add_argument('--duration', type=int, default=600, help='Target video duration in seconds (default: 300)')
parser.add_argument('--monda-font', type=str, default=None, help='Path to Monda font file (optional)')
args = parser.parse_args()

# Set quality parameters
FRAMES_PER_YEAR = args.frames_per_year if not args.quarters_only else 4
OUTPUT_DPI = 108  # Reduced from 144 to 108 for good balance of quality and performance
FIGURE_SIZE = (19.2, 10.8)  # 1080p size
LOGO_DPI = 300  # High DPI for sharp logos

# Global variable for Monda font path
monda_font_path = None

# Create required directories
logos_dir = 'airline-bar-video/logos'
output_dir = 'output'
for directory in [logos_dir, output_dir]:
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")

# Global variables
frame_indices = []
logo_cache = {}  # Cache for preprocessed logos

def optimize_figure_for_performance():
    """Optimize matplotlib performance settings"""
    plt.rcParams['path.simplify'] = True
    plt.rcParams['path.simplify_threshold'] = 1.0
    plt.rcParams['agg.path.chunksize'] = 10000
    plt.rcParams['figure.dpi'] = OUTPUT_DPI
    plt.rcParams['savefig.dpi'] = OUTPUT_DPI
    plt.rcParams['savefig.bbox'] = 'standard'
    plt.rcParams['figure.autolayout'] = False
    plt.rcParams['figure.constrained_layout.use'] = False
    plt.rcParams['savefig.format'] = 'png'
    plt.rcParams['savefig.pad_inches'] = 0.1
    plt.rcParams['figure.figsize'] = FIGURE_SIZE
    
    # Set Monda font for all text elements if available
    if monda_font_path and os.path.exists(monda_font_path):
        # Register the font with fontmanager
        try:
            print(f"Applying Monda font from {monda_font_path}")
            prop = fm.FontProperties(fname=monda_font_path)
            font_name = prop.get_name()
            plt.rcParams['font.family'] = 'sans-serif'
            plt.rcParams['font.sans-serif'] = [font_name, 'Arial', 'DejaVu Sans', 'Helvetica', 'sans-serif']
            # Set it for all text elements
            plt.rcParams['text.color'] = '#808080'
            plt.rcParams['axes.labelcolor'] = '#808080'
            plt.rcParams['xtick.color'] = '#808080'
            plt.rcParams['ytick.color'] = '#808080'
        except Exception as e:
            print(f"Error applying Monda font: {e}")
            plt.rcParams['font.family'] = 'sans-serif'
            plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica', 'sans-serif']
    else:
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Helvetica', 'sans-serif']
    
    plt.rcParams['axes.facecolor'] = 'white'
    plt.rcParams['axes.grid'] = False
    plt.rcParams['axes.edgecolor'] = '#dddddd'
    plt.rcParams['axes.linewidth'] = 0.8
    plt.rcParams['grid.color'] = '#dddddd'
    plt.rcParams['grid.linestyle'] = '--'
    plt.rcParams['grid.linewidth'] = 0.5

def preprocess_logo(image_array, target_size=None, upscale_factor=4):
    """Optimized logo preprocessing function"""
    cache_key = f"{hash(str(image_array.tobytes()))}-{str(target_size)}"
    if cache_key in logo_cache:
        return logo_cache[cache_key]

    try:
        if isinstance(image_array, np.ndarray):
            if image_array.dtype == np.float32:
                image_array = (image_array * 255).astype(np.uint8)
            image = Image.fromarray(image_array)
        else:
            image = image_array

        original_mode = image.mode
        original_size = image.size

        if target_size:
            w, h = target_size
            large_size = (w * 5, h * 5)
            image = image.resize(large_size, Image.Resampling.LANCZOS)

            # Apply stronger sharpening and contrast enhancement
            if original_mode == 'RGBA':
                r, g, b, a = image.split()
                rgb = Image.merge('RGB', (r, g, b))
                
                enhancer = ImageEnhance.Sharpness(rgb)
                rgb = enhancer.enhance(2.2)
                
                contrast = ImageEnhance.Contrast(rgb)
                rgb = contrast.enhance(1.6)
                
                brightness = ImageEnhance.Brightness(rgb)
                rgb = brightness.enhance(1.15)
                
                r, g, b = rgb.split()
                image = Image.merge('RGBA', (r, g, b, a))
            else:
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(2.2)
                
                contrast = ImageEnhance.Contrast(image)
                image = contrast.enhance(1.6)
                
                brightness = ImageEnhance.Brightness(image)
                image = brightness.enhance(1.15)

            image = image.filter(ImageFilter.UnsharpMask(radius=1.5, percent=220, threshold=2))
            image = image.filter(ImageFilter.GaussianBlur(radius=0.3))
            image = image.resize(target_size, Image.Resampling.LANCZOS)

        result = np.array(image)
        logo_cache[cache_key] = result
        return result
        
    except Exception as e:
        print(f"Error in preprocess_logo: {e}")
        import traceback
        traceback.print_exc()
        return image_array

def format_revenue(value, pos):
    """Format revenue values with B for billions and M for millions"""
    if value >= 1000:
        return f'${value/1000:.1f}B'
    return f'${value:.0f}M'

def parse_quarter(quarter_str):
    """Parse quarter string into (year, quarter)"""
    year, quarter = quarter_str.split("'")
    year = int(year)  # Year is already in 4-digit format
    quarter = int(quarter[1])  # Extract quarter number
    return year, quarter

def is_before_may_2004(year, quarter):
    """Helper function to check if date is before May 2004"""
    if year < 2004:
        return True
    elif year == 2004:
        return quarter <= 1  # Q1 and earlier are before May
    return False

# Create a color mapping for regions
region_colors = {
    'North America': '#40E0D0',  # Turquoise
    'Europe': '#4169E1',         # Royal Blue
    'Asia Pacific': '#FF4B4B',   # Red
    'Latin America': '#32CD32',  # Lime Green
    'China': '#FF4B4B',          # Red (same as Asia Pacific)
    'Middle East': '#DEB887',    # Burlywood
    'Russia': '#FF4B4B',         # Red (same as Asia Pacific)
    'Turkey': '#DEB887'          # Burlywood (same as Middle East)
}

# Define constants for visualization
MAX_BARS = 15  # Maximum number of bars to show
BAR_HEIGHT = 0.8  # Height of each bar
BAR_PADDING = 0.2  # Padding between bars
TOTAL_BAR_HEIGHT = BAR_HEIGHT + BAR_PADDING  # Total height including padding
TICK_FONT_SIZE = 14  # Increased from 10
LABEL_FONT_SIZE = 14  # Increased from 10
VALUE_FONT_SIZE = 14  # Increased from 10

# Create a mapping for company logos
logo_mapping = {
    "easyJet": [{"start_year": 1999, "end_year": 9999, "file": "airline-bar-video/logos/easyJet-1999-now.jpg"}],
    "Emirates": [{"start_year": 1999, "end_year": 9999, "file": "airline-bar-video/logos/Emirates-logo.jpg"}],
    "Air France-KLM": [
        {"start_year": 1999, "end_year": 2004, "file": "airline-bar-video/logos/klm-1999-now.png"},
        {"start_year": 2004, "end_year": 9999, "file": "airline-bar-video/logos/Air-France-KLM-Holding-Logo.png"}
    ],
    "American Airlines": [
        {"start_year": 1967, "end_year": 2013, "file": "airline-bar-video/logos/american-airlines-1967-2013.jpg"},
        {"start_year": 2013, "end_year": 9999, "file": "airline-bar-video/logos/american-airlines-2013-now.jpg"}
    ],
    "Delta Air Lines": [
        {"start_year": 2000, "end_year": 2007, "file": "airline-bar-video/logos/delta-air-lines-2000-2007.png"},
        {"start_year": 2007, "end_year": 9999, "file": "airline-bar-video/logos/delta-air-lines-2007-now.jpg"}
    ],
    "Southwest Airlines": [
        {"start_year": 1989, "end_year": 2014, "file": "airline-bar-video/logos/southwest-airlines-1989-2014.png"},
        {"start_year": 2014, "end_year": 9999, "file": "airline-bar-video/logos/southwest-airlines-2014-now.png"}
    ],
    "United Airlines": [
        {"start_year": 1998, "end_year": 2010, "file": "airline-bar-video/logos/united-airlines-1998-2010.jpg"},
        {"start_year": 2010, "end_year": 9999, "file": "airline-bar-video/logos/united-airlines-2010-now.jpg"}
    ],
    "Alaska Air": [
        {"start_year": 1972, "end_year": 2014, "file": "airline-bar-video/logos/alaska-air-1972-2014.png"},
        {"start_year": 2014, "end_year": 2016, "file": "airline-bar-video/logos/alaska-air-2014-2016.png"},
        {"start_year": 2016, "end_year": 9999, "file": "airline-bar-video/logos/alaska-air-2016-now.jpg"}
    ],
    "Finnair": [
        {"start_year": 1999, "end_year": 2010, "file": "airline-bar-video/logos/Finnair-1999-2010.jpg"},
        {"start_year": 2010, "end_year": 9999, "file": "airline-bar-video/logos/Finnair-2010-now.jpg"}
    ],
    "Deutsche Lufthansa": [
        {"start_year": 1999, "end_year": 2018, "file": "airline-bar-video/logos/Deutsche Lufthansa-1999-2018.png"},
        {"start_year": 2018, "end_year": 9999, "file": "airline-bar-video/logos/Deutsche Lufthansa-2018-now.jpg"}
    ],
    "Singapore Airlines": [{"start_year": 1999, "end_year": 9999, "file": "airline-bar-video/logos/Singapore Airlines-1999-now.jpg"}],
    "Qantas Airways": [{"start_year": 1999, "end_year": 9999, "file": "airline-bar-video/logos/Qantas Airways-1999-now.jpg"}],
    "Cathay Pacific": [{"start_year": 1999, "end_year": 9999, "file": "airline-bar-video/logos/Cathay Pacific-1999-now.png"}],
    "LATAM Airlines": [
        {"start_year": 1999, "end_year": 2016, "file": "airline-bar-video/logos/LATAM Airlines-1999-2016.png"},
        {"start_year": 2016, "end_year": 9999, "file": "airline-bar-video/logos/LATAM Airlines-2016-now.jpg"}
    ],
    "Air China": [{"start_year": 1999, "end_year": 9999, "file": "airline-bar-video/logos/Air China-1999-now.png"}],
    "China Eastern": [{"start_year": 1999, "end_year": 9999, "file": "airline-bar-video/logos/China Eastern-1999-now.jpg"}],
    "China Southern": [{"start_year": 1999, "end_year": 9999, "file": "airline-bar-video/logos/China Southern-1999-now.jpg"}],
    "Hainan Airlines": [
        {"start_year": 1999, "end_year": 2004, "file": "airline-bar-video/logos/Hainan Airlines-1999-2004.png"},
        {"start_year": 2004, "end_year": 9999, "file": "airline-bar-video/logos/Hainan Airlines-2004-now.jpg"}
    ],
    "Qatar Airways": [{"start_year": 1999, "end_year": 9999, "file": "airline-bar-video/logos/Qatar Airways-1999-now.jpg"}],
    "Turkish Airlines": [
        {"start_year": 1999, "end_year": 2018, "file": "airline-bar-video/logos/Turkish Airlines-1999-2018.png"},
        {"start_year": 2018, "end_year": 9999, "file": "airline-bar-video/logos/Turkish Airlines-2018-now.png"}
    ],
    "JetBlue": [{"start_year": 1999, "end_year": 9999, "file": "airline-bar-video/logos/jetBlue-1999-now.jpg"}],
    "SkyWest": [
        {"start_year": 1972, "end_year": 2001, "file": "airline-bar-video/logos/skywest-1972-2001.png"},
        {"start_year": 2001, "end_year": 2008, "file": "airline-bar-video/logos/skywest-2001-2008.png"},
        {"start_year": 2018, "end_year": 9999, "file": "airline-bar-video/logos/skywest-2018-now.jpg"}
    ],
    "Northwest Airlines": [
        {"start_year": 1989, "end_year": 2003, "file": "airline-bar-video/logos/northwest-airlines-1989-2003.png"},
        {"start_year": 2003, "end_year": 9999, "file": "airline-bar-video/logos/northwest-airlines-2003-now.jpg"}
    ],
    "TWA": [{"start_year": 1999, "end_year": 9999, "file": "airline-bar-video/logos/TWA-1999-now.png"}],
    "Air Canada": [
        {"start_year": 1995, "end_year": 2005, "file": "airline-bar-video/logos/air-canada-1995-2005.jpg"},
        {"start_year": 2005, "end_year": 9999, "file": "airline-bar-video/logos/air-canada-2005-now.png"}
    ],
    "IAG": [{"start_year": 1999, "end_year": 9999, "file": "airline-bar-video/logos/IAG-1999-now.png"}],
    "Ryanair": [
        {"start_year": 1999, "end_year": 2001, "file": "airline-bar-video/logos/Ryanair-1999-2001.png"},
        {"start_year": 2001, "end_year": 2013, "file": "airline-bar-video/logos/Ryanair-2001-2013.jpg"},
        {"start_year": 2013, "end_year": 9999, "file": "airline-bar-video/logos/Ryanair-2013-now.jpg"}
    ],
    "Aeroflot": [
        {"start_year": 1999, "end_year": 2003, "file": "airline-bar-video/logos/Aeroflot-1999-2003.jpg"},
        {"start_year": 2003, "end_year": 9999, "file": "airline-bar-video/logos/Aeroflot-2003-now.jpg"}
    ],
    "Norwegian Air": [{"start_year": 1999, "end_year": 9999, "file": "airline-bar-video/logos/norwegian-logo.jpg"}]
}

def get_logo_path(airline, year, iata_code, month=6):
    """Get the appropriate logo path based on airline name, year and month"""
    if iata_code == "DY":
        norwegian_logo = "airline-bar-video/logos/norwegian-logo.jpg"
        return norwegian_logo if os.path.exists(norwegian_logo) else None
        
    if airline not in logo_mapping:
        return None
        
    logo_versions = logo_mapping[airline]
    
    if airline == "Air France-KLM":
        if year < 2004 or (year == 2004 and month < 5):
            for version in logo_versions:
                if version["file"] == "airline-bar-video/logos/klm-1999-now.png":
                    logo_path = version["file"]
                    return logo_path if os.path.exists(logo_path) else None
        else:
            for version in logo_versions:
                if version["file"] == "airline-bar-video/logos/Air-France-KLM-Holding-Logo.png":
                    logo_path = version["file"]
                    return logo_path if os.path.exists(logo_path) else None
    
    for version in logo_versions:
        if version["start_year"] <= year <= version["end_year"]:
            logo_path = version["file"]
            if os.path.exists(logo_path):
                return logo_path
            else:
                return None
    
    return None

def create_frame(args):
    """Optimized frame creation function for direct video rendering"""
    frame_idx, quarters_data, revenue_data_arg, metadata_arg, quarters_only = args
    optimize_figure_for_performance()
    
    frame_int = int(frame_idx)
    frame_fraction = frame_idx - frame_int
    fig_width = FIGURE_SIZE[0]
    fig_height = FIGURE_SIZE[1]
    
    fig = plt.figure(figsize=(fig_width, fig_height), facecolor='white', dpi=OUTPUT_DPI)
    fig.set_size_inches(fig_width, fig_height, forward=True)
    
    # 使用线性匀速插值，不对frame_fraction做任何变换
    
    if frame_fraction == 0 or quarters_only:
        current_quarter = quarters_data[frame_int]
        quarter_data_main = revenue_data_arg.loc[current_quarter]
        interpolated_data = quarter_data_main
    else:
        if frame_int < len(quarters_data) - 1:
            q1 = quarters_data[frame_int]
            q2 = quarters_data[frame_int + 1]
            q1_data = revenue_data_arg.loc[q1]
            q2_data = revenue_data_arg.loc[q2]
            
            # 使用线性匀速插值
            smooth_t = frame_fraction  # 线性匀速，不应用任何缓动函数
            interpolated_data = q1_data * (1 - smooth_t) + q2_data * smooth_t
        else:
            current_quarter = quarters_data[frame_int]
            interpolated_data = revenue_data_arg.loc[current_quarter]
    
    text_color = '#808080'
    
    gs = fig.add_gridspec(2, 1, height_ratios=[0.15, 1], 
                          left=0.1, right=0.9,
                          bottom=0.1, top=0.95,
                          hspace=0.05)
    
    ax_timeline = fig.add_subplot(gs[0])
    ax = fig.add_subplot(gs[1])

    quarter_data = []
    colors = []
    labels = []
    logos = []
    logos_data = []
    
    if frame_int < len(quarters_data):
        current_quarter = quarters_data[frame_int]
    else:
        current_quarter = quarters_data[-1]
    
    year, quarter = parse_quarter(current_quarter)
    
    if frame_fraction > 0:
        # 计算年份和月份进度，确保时间轴平滑过渡
        if frame_int < len(quarters_data) - 1:
            q1 = quarters_data[frame_int]
            q2 = quarters_data[frame_int + 1]
            year1, quarter1 = parse_quarter(q1)
            year2, quarter2 = parse_quarter(q2)
            
            # 线性匀速插值年份和季度
            year_fraction1 = year1 + (quarter1 - 1) * 0.25
            year_fraction2 = year2 + (quarter2 - 1) * 0.25
            
            # 使用原始frame_fraction执行线性插值，不应用任何缓动
            year_fraction = year_fraction1 * (1 - frame_fraction) + year_fraction2 * frame_fraction
            
            year_integer = int(year_fraction)
            month = int((year_fraction - year_integer) * 12) + 1
            quarter_display = f"{year_integer} {month:02d}"
            current_month = month
            current_year = year_integer
        else:
            # 在最后一个季度后的线性过渡
            year_fraction = year + (quarter - 1) * 0.25 + frame_fraction * 0.25
            year_integer = int(year_fraction)
            month = int((year_fraction - year_integer) * 12) + 1
            quarter_display = f"{year_integer} {month:02d}"
            current_month = month
            current_year = year_integer
    else:
        quarter_display = f"{year} Q{quarter}"
        month_mapping = {1: 2, 2: 5, 3: 8, 4: 11}
        current_month = month_mapping[quarter]
        current_year = year
    
    # 获取当前帧所有公司列表及其排序键
    airline_data = []
    for airline in interpolated_data.index:
        value = interpolated_data[airline]
        if pd.notna(value) and value > 0:  # Only include positive non-null values
            region = metadata_arg.loc['Region', airline]
            color = region_colors.get(region, '#808080')
            
            # Special handling for Air France-KLM label
            if airline == "Air France-KLM":
                if current_year < 2004 or (current_year == 2004 and current_month < 5):
                    label = "KL"
                else:
                    iata_code = metadata_arg.loc['IATA Code', airline]
                    label = iata_code if pd.notna(iata_code) else airline[:3]
            else:
                iata_code = metadata_arg.loc['IATA Code', airline]
                label = iata_code if pd.notna(iata_code) else airline[:3]
            
            # Get logo path using IATA code and current_year/current_month
            logo_path = get_logo_path(airline, current_year, iata_code, current_month)
            
            airline_data.append({
                'airline': airline,
                'value': value,
                'region': region,
                'color': color,
                'label': label,
                'logo_path': logo_path
            })
    
    # Check if we have any valid data
    if not airline_data:
        fig.suptitle(f'No data available for {current_quarter}', fontsize=14)
        buf = BytesIO()
        plt.savefig(buf, format='rgba', dpi=OUTPUT_DPI)
        buf.seek(0)
        plt.close(fig)
        return np.frombuffer(buf.getvalue(), dtype=np.uint8).reshape((int(fig_height * OUTPUT_DPI), int(fig_width * OUTPUT_DPI), -1))
    
    # 按照value对公司数据进行排序
    airline_data.sort(key=lambda x: x['value'], reverse=True)
    
    # Limit to top N airlines
    if len(airline_data) > MAX_BARS:
        airline_data = airline_data[:MAX_BARS]
    
    # 提取排序后的数据列表
    quarter_data = [item['value'] for item in airline_data]
    colors = [item['color'] for item in airline_data]
    labels = [item['label'] for item in airline_data]
    logos = [item['logo_path'] for item in airline_data]
    
    # Calculate fixed positions for bars
    num_bars = len(quarter_data)
    y_positions = np.arange(num_bars) * TOTAL_BAR_HEIGHT
    
    # Create bars
    bars = ax.barh(y_positions, quarter_data, 
                   height=BAR_HEIGHT, 
                   color=colors,
                   edgecolor='none')
    
    # 处理logo
    for i, (logo_path, y) in enumerate(zip(logos, y_positions)):
        if logo_path and os.path.exists(logo_path):
            try:
                img = plt.imread(logo_path)
                
                img_height = BAR_HEIGHT * 0.8
                aspect_ratio = img.shape[1] / img.shape[0]
                img_width = img_height * aspect_ratio
                
                target_height_pixels = int(40)
                target_width_pixels = int(target_height_pixels * aspect_ratio)
                
                if isinstance(img, np.ndarray):
                    if img.dtype == np.float32:
                        img = (img * 255).astype(np.uint8)
                    pil_img = Image.fromarray(img)
                else:
                    pil_img = img
                
                pil_img = pil_img.resize((target_width_pixels, target_height_pixels), Image.Resampling.LANCZOS)
                
                if pil_img.mode == 'RGBA':
                    r, g, b, a = pil_img.split()
                    rgb = Image.merge('RGB', (r, g, b))
                    enhancer = ImageEnhance.Sharpness(rgb)
                    rgb = enhancer.enhance(1.8)
                    contrast = ImageEnhance.Contrast(rgb)
                    rgb = contrast.enhance(1.3)
                    r, g, b = rgb.split()
                    pil_img = Image.merge('RGBA', (r, g, b, a))
                else:
                    enhancer = ImageEnhance.Sharpness(pil_img)
                    pil_img = enhancer.enhance(1.8)
                    contrast = ImageEnhance.Contrast(pil_img)
                    pil_img = contrast.enhance(1.3)
                
                img_array = np.array(pil_img)
                
                if img_array.dtype != np.float32 and img_array.max() > 1.0:
                    img_array = img_array.astype(np.float32) / 255.0
                
                logos_data.append({
                    'img_array': img_array,
                    'index': i,
                    'y': y,
                    'value': quarter_data[i]  # 保存对应的值，确保位置计算一致
                })
                
            except Exception as e:
                continue
    
    # Customize the plot
    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels, fontsize=TICK_FONT_SIZE, color=text_color)
    
    # Format x-axis with custom formatter and set consistent colors
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(format_revenue))
    ax.xaxis.set_tick_params(labelsize=TICK_FONT_SIZE, colors=text_color)
    for label in ax.get_xticklabels():
        label.set_color(text_color)
    
    # 计算一致的显示最大值，确保所有元素位置计算基于相同的比例
    max_value = max(quarter_data) if quarter_data else 0
    
    # Get historical maximum value across all quarters up to current frame
    historical_max = 0
    for i in range(frame_int + 1):
        quarter_historical = quarters_data[i]
        historical_data = revenue_data_arg.loc[quarter_historical]
        quarter_max = historical_data.max()
        if pd.notna(quarter_max) and quarter_max > historical_max:
            historical_max = quarter_max
    
    # Use max of current frame and historical max
    display_max = max(max_value, historical_max)
    
    # 增加右侧空间以容纳logo，避免logo被裁剪
    ax.set_xlim(0, display_max * 1.5)  # 从1.3倍增加到1.5倍
    
    # 预先计算所有元素的位置，确保同步
    element_positions = []
    for i, bar in enumerate(bars):
        value = quarter_data[i]
        # 使用统一的位置计算公式
        base_position = value
        text_offset = display_max * 0.01  # 文本偏移量
        logo_offset = display_max * 0.08  # 减小logo偏移量，从0.15改为0.08
        
        element_positions.append({
            'index': i,
            'y': y_positions[i],
            'value': value,
            'text_position': base_position + text_offset,
            'logo_position': base_position + logo_offset
        })
    
    # 按照预计算的位置添加文本
    for pos in element_positions:
        value = pos['value']
        value_text = format_revenue(value, None)
        ax.text(pos['text_position'], pos['y'], value_text,
                va='center', ha='left', fontsize=VALUE_FONT_SIZE, color=text_color)
    
    # 使用相同的预计算位置添加logo
    for logo_data in logos_data:
        i = logo_data['index']
        img_array = logo_data['img_array']
        pos = element_positions[i]
        
        # 创建OffsetImage对象，增大zoom值
        img_box = OffsetImage(img_array, zoom=0.9)  # 增大zoom从0.5到0.9
        img_box.image.axes = ax
        
        # 使用预计算的logo位置创建AnnotationBbox
        ab = AnnotationBbox(img_box, (pos['logo_position'], pos['y']),
                           frameon=False,
                           box_alignment=(0, 0.5))
        ax.add_artist(ab)
    
    # Set fixed y-axis limits - reduced padding to move bars up
    total_height = MAX_BARS * TOTAL_BAR_HEIGHT
    ax.set_ylim(total_height, -BAR_PADDING * 2)  # Reduced negative padding to move bars up
    
    # Add grid lines
    ax.grid(True, axis='x', alpha=0.3, which='major', linestyle='--')
    
    # Style the axes
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.tick_params(axis='y', which='both', left=False)
    
    # Add simplified Revenue label at the bottom with consistent color
    ax.set_xlabel('Revenue', fontsize=16, labelpad=10, color=text_color)
    
    # Set up timeline - New style with smoother animation
    ax_timeline.set_facecolor('none')  # Transparent background
    
    # Get min and max quarters for timeline
    min_quarter = quarters_data[0]
    max_quarter = quarters_data[-1]
    min_year, min_q = parse_quarter(min_quarter)
    max_year, max_q = parse_quarter(max_quarter)
    
    # Set timeline limits with padding
    ax_timeline.set_xlim(-1, len(quarters_data) + 0.5)
    ax_timeline.set_ylim(-0.2, 0.2)
    
    # Set up timeline styling
    ax_timeline.spines['top'].set_visible(False)
    ax_timeline.spines['right'].set_visible(False)
    ax_timeline.spines['left'].set_visible(False)
    ax_timeline.spines['bottom'].set_visible(True)
    ax_timeline.spines['bottom'].set_linewidth(1.5)
    ax_timeline.spines['bottom'].set_color(text_color)
    ax_timeline.spines['bottom'].set_position(('data', 0))
    
    # Add quarter markers with vertical lines
    for i, quarter in enumerate(quarters_data):
        year, q = parse_quarter(quarter)
        if q == 1:  # Major tick for Q1
            ax_timeline.vlines(i, -0.03, 0, colors=text_color, linewidth=1.5)
            # Show label for every other year, starting from 2025 and going backwards
            if year % 2 == 1 or year == 2025:  # Show years that are odd (2023, 2021, etc.) plus 2025
                ax_timeline.text(i, -0.07, str(year), ha='center', va='top', 
                               fontsize=16, color=text_color)
        else:  # Minor tick for other quarters
            ax_timeline.vlines(i, -0.02, 0, colors=text_color, linewidth=0.5, alpha=0.7)
    
    # 确保2025年的标记显示在时间轴上
    # 检查最后一个季度是否为2024年第4季度
    last_year, last_q = parse_quarter(quarters_data[-1])
    if last_year == 2024 and last_q == 4:
        # 在时间轴上添加2025年的标记
        next_year_pos = len(quarters_data)
        ax_timeline.vlines(next_year_pos, -0.03, 0, colors=text_color, linewidth=1.5)
        ax_timeline.text(next_year_pos, -0.07, "2025", ha='center', va='top', 
                       fontsize=16, color=text_color)
    
    # Add current position marker (inverted triangle)
    # 直接使用原始frame_fraction确保线性匀速过渡
    timeline_position = frame_int + frame_fraction  # 线性匀速，不应用缓动函数
    ax_timeline.plot(timeline_position, 0.03, marker='v', color='#4e843d', markersize=10, zorder=5)
    
    # Remove timeline ticks
    ax_timeline.set_xticks([])
    ax_timeline.set_yticks([])
    
    # Render the figure to a numpy array
    buf = BytesIO()
    plt.savefig(buf, format='rgba', dpi=OUTPUT_DPI)
    buf.seek(0)
    plt.close(fig)
    
    # Convert to numpy array for video encoding
    frame_array = np.frombuffer(buf.getvalue(), dtype=np.uint8).reshape((int(fig_height * OUTPUT_DPI), int(fig_width * OUTPUT_DPI), -1))
    return frame_array

def configure_video_settings():
    """Configure video encoding settings based on quality parameter"""
    if args.quality == 'high':
        crf = '10'  # 降低CRF以提高质量（从12降低到10）
        preset = 'slow'  # Slow preset for better compression
        bitrate = '25M'  # 增加比特率从20M到25M
    elif args.quality == 'medium':
        crf = '16'  # 从18降低到16
        preset = 'medium'
        bitrate = '15M'  # 从12M增加到15M
    else:  # low
        crf = '20'  # 从23降低到20
        preset = 'medium'  # 从fast改为medium
        bitrate = '10M'  # 从8M增加到10M
    
    # 始终使用高质量像素格式以保持颜色准确度
    pix_fmt = 'yuv444p'  # 无色度子采样，更好的颜色保存
    
    return {
        'crf': crf,
        'preset': preset,
        'bitrate': bitrate,
        'pix_fmt': pix_fmt
    }

def create_video_directly(frame_indices, output_path, fps):
    """Create video directly from matplotlib frames without saving intermediate PNGs"""
    print("\nInitializing video creation...")
    print(f"Total frames to generate: {len(frame_indices)}")
    
    # Get the first frame to determine dimensions
    print("Creating test frame to determine dimensions...")
    test_frame = create_frame((frame_indices[0], quarters, revenue_data, metadata, args.quarters_only))
    height, width, channels = test_frame.shape
    print(f"Frame size: {width}x{height}")
    
    # Check if FFmpeg is installed
    try:
        subprocess.check_output(['ffmpeg', '-version'], stderr=subprocess.STDOUT)
        
        # Get video encoding settings
        video_settings = configure_video_settings()
        
        # Create a pipe to FFmpeg
        command = [
            'ffmpeg', '-y',  # Overwrite output file if it exists
            '-f', 'rawvideo',
            '-vcodec', 'rawvideo',
            '-s', f'{width}x{height}',  # Size of one frame
            '-pix_fmt', 'rgb24',  # Input pixel format
            '-r', str(fps),  # Frame rate
            '-i', '-',  # Input from pipe
            '-c:v', 'libx264',  # Output codec
            '-profile:v', 'high444',  # Support yuv444p
            '-pix_fmt', video_settings['pix_fmt'],
            '-preset', video_settings['preset'],
            '-crf', video_settings['crf'],
            '-b:v', video_settings['bitrate'],
            '-movflags', '+faststart',  # Optimize for web playback
            '-colorspace', 'bt709',     # Use standard color space
            '-color_primaries', 'bt709',
            '-color_trc', 'bt709',
            '-loglevel', 'error',  # Only show errors
            output_path
        ]
        
        print("\nStarting frame generation...")
        ffmpeg_process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Create a progress bar
        total_frames = len(frame_indices)

        # Calculate optimal chunk size for multiprocessing
        cpu_count = mp.cpu_count()
        # 减小chunk_size以提高更新频率，使生成更平滑
        chunk_size = max(1, min(total_frames // (cpu_count * 8), 20))  # 更小的块大小

        # Prepare arguments for multiprocessing
        frame_args = [(idx, quarters, revenue_data, metadata, args.quarters_only) for idx in frame_indices]
        
        # 创建有序字典保存帧
        from collections import OrderedDict
        frame_buffer = OrderedDict()
        next_frame_idx = 0
        
        # Create a pool of workers
        with mp.Pool(processes=cpu_count) as pool:
            # Create frames in parallel using imap for better order consistency
            with tqdm(total=total_frames, desc="Generating frames", unit="frame",
                     bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
                try:
                    # 使用imap而不是imap_unordered可以保持顺序一致
                    for idx, frame in enumerate(pool.imap(create_frame, frame_args, chunksize=chunk_size)):
                        # Convert frame if needed
                        if frame.dtype != np.uint8:
                            frame = (frame * 255).astype(np.uint8)
                        
                        # Ensure frame is in correct RGB format
                        if frame.shape[2] == 4:  # RGBA format
                            frame = frame[:, :, :3]  # Remove alpha channel
                        
                        # Write the frame to FFmpeg process
                        try:
                            ffmpeg_process.stdin.write(frame.tobytes())
                            pbar.update(1)
                            # 每100帧打印一次状态更新
                            if idx % 100 == 0:
                                print(f"\nProcessed {idx}/{total_frames} frames")
                        except IOError as e:
                            print("\nError writing frame to FFmpeg:", e)
                            break
                except Exception as e:
                    print("\nError during frame generation:", e)
                    pool.terminate()
                    raise e

        # Close the pipe and wait for FFmpeg to finish
        print("\nFinishing video encoding...")
        ffmpeg_process.stdin.close()
        ffmpeg_process.wait()
        
        if ffmpeg_process.returncode != 0:
            stderr = ffmpeg_process.stderr.read().decode()
            print(f"\nFFmpeg error: {stderr}")
            return False
        
        # Check if output file was created successfully
        if os.path.exists(output_path) and os.path.getsize(output_path) > 100000:
            print("\nVideo created successfully!")
            return True
        else:
            print("\nError: Output file is invalid")
            return False
            
    except (FileNotFoundError, subprocess.SubprocessError) as e:
        print("\nFalling back to OpenCV...")
        try:
            # Initialize video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Try MP4V codec
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            if not out.isOpened():
                print("Error: Could not initialize video writer")
                return False
            
            # Create frames and write to video using multiprocessing
            total_frames = len(frame_indices)
            
            # Calculate optimal chunk size for multiprocessing
            cpu_count = mp.cpu_count()
            chunk_size = max(1, min(total_frames // (cpu_count * 8), 20))  # 更小的块大小

            # Create a pool of workers
            with mp.Pool(processes=cpu_count) as pool:
                with tqdm(total=total_frames, desc="Generating frames (OpenCV)", unit="frame",
                         bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]") as pbar:
                    try:
                        # 使用imap而不是imap_unordered可以保持顺序一致
                        for idx, frame in enumerate(pool.imap(create_frame, frame_args, chunksize=chunk_size)):
                            # Convert frame to BGR format (required by OpenCV)
                            if frame.dtype != np.uint8:
                                frame = (frame * 255).astype(np.uint8)
                            
                            # Convert RGB to BGR
                            if frame.shape[2] >= 3:
                                frame = cv2.cvtColor(frame[:, :, :3], cv2.COLOR_RGB2BGR)
                            
                            # Write the frame
                            out.write(frame)
                            pbar.update(1)
                            # 每100帧打印一次状态更新
                            if idx % 100 == 0:
                                print(f"\nProcessed {idx}/{total_frames} frames")
                    except Exception as e:
                        print("\nError during frame generation:", e)
                        pool.terminate()
                        raise e
            
            # Release the video writer
            out.release()
            
            # Check if output file was created successfully
            if os.path.exists(output_path) and os.path.getsize(output_path) > 100000:
                print("\nVideo created successfully!")
                return True
            else:
                print("\nError: Output file is invalid")
                return False
                
        except Exception as e:
            print("\nError:", e)
            return False

def main():
    # Initialize matplotlib in main process
    plt.switch_backend('Agg')
    
    # Load the data from CSV
    global metadata, revenue_data, quarters, monda_font_path
    
    # Use global scope for these variables
    df = pd.read_csv('airline-bar-video/airlines_final.csv')
    
    # Process metadata
    metadata = df.iloc[:7].copy()  # First 7 rows contain metadata
    revenue_data = df.iloc[7:].copy()  # Revenue data starts from row 8
    
    # Set proper index for metadata
    metadata.set_index(metadata.columns[0], inplace=True)
    
    # Convert revenue columns by removing ' M' suffix, commas, and converting to float
    for col in revenue_data.columns[1:]:  # Skip the first column which contains row labels
        revenue_data[col] = pd.to_numeric(revenue_data[col].str.replace(',', '').str.replace(' M', ''), errors='coerce')
    
    # Set index for revenue data
    revenue_data.set_index(revenue_data.columns[0], inplace=True)
    
    # Get the quarters from the revenue data index
    quarters = revenue_data.index.tolist()
    
    # Check font configurations
    monda_font_path = args.monda_font
    if not monda_font_path:
        # Try to find Monda font in system
        system_fonts = fm.findSystemFonts()
        for font in system_fonts:
            if 'monda' in font.lower():
                monda_font_path = font
                break
    
    if monda_font_path and os.path.exists(monda_font_path):
        # Register the font with matplotlib
        fm.fontManager.addfont(monda_font_path)
    
    # Create output directory if it doesn't exist
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Get the total number of frames to generate based on the number of quarters
    total_quarters = len(quarters)
    
    # Generate frame indices
    global frame_indices
    
    if args.quarters_only:
        # In quarters-only mode, generate exactly one frame per quarter
        frame_indices = list(range(total_quarters))
        total_frames = total_quarters
    else:
        # 在正常模式下，根据FRAMES_PER_YEAR在季度之间生成更多帧以实现更平滑的过渡
        frames_per_quarter = FRAMES_PER_YEAR // 4
        
        # 增加每季度之间的插值帧数
        if args.quality == 'high':
            # 高质量模式下使用更多的帧
            frames_per_quarter = max(frames_per_quarter, 200)  # 确保至少有200帧/季度
        elif args.quality == 'medium':
            frames_per_quarter = max(frames_per_quarter, 100)  # 中等质量至少100帧/季度
        else:
            frames_per_quarter = max(frames_per_quarter, 50)   # 低质量至少50帧/季度
        
        # Create frame indices with appropriate interpolation between quarters
        frame_indices = []
        
        # Generate frames with increased density for smoother transitions
        for i in range(total_quarters - 1):
            # Add the main quarter frame
            frame_indices.append(i)
            
            # Add interpolated frames between quarters with increased density
            for j in range(1, frames_per_quarter):
                # Calculate fractional index for interpolation
                fraction = j / frames_per_quarter
                frame_indices.append(i + fraction)
        
        # Add the last quarter
        frame_indices.append(total_quarters - 1)
        total_frames = len(frame_indices)
        
        # Sort frames to ensure sequential generation
        frame_indices.sort()
    
    print(f"Generated {len(frame_indices)} frame indices for animation")
    
    # Calculate appropriate FPS based on desired duration
    target_fps = args.fps
    
    # If a specific duration is requested, calculate the ideal FPS
    if args.duration:
        calculated_fps = total_frames / args.duration
        fps = max(min(calculated_fps, 90), 24)  # Keep fps between 24 and 90
    else:
        # 根据质量设置调整FPS以获得更流畅的播放
        if args.quality == 'high':
            fps = min(max(target_fps, 60), 90)  # 高质量使用60-90fps
        elif args.quality == 'medium':
            fps = min(max(target_fps, 45), 60)  # 中等质量使用45-60fps
        else:
            fps = min(max(target_fps, 30), 45)  # 低质量使用30-45fps
    
    # Round fps to nearest integer for simplicity
    fps = round(fps)
    print(f"Using {fps} frames per second for video output")
    
    # Create video directly
    success = create_video_directly(frame_indices, args.output, fps)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    try:
        # Initialize multiprocessing with spawn method
        mp.set_start_method('spawn')
        
        # Run main program
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1) 