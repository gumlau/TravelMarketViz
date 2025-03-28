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
parser.add_argument('--fps', type=int, default=60, help='Frames per second (default: 60)')
parser.add_argument('--output', type=str, default='output/airline_revenue.mp4', help='Output video file path')
parser.add_argument('--quality', type=str, choices=['high', 'medium', 'low'], default='high', 
                    help='Video quality: high, medium, or low (default: high)')
parser.add_argument('--frames-per-year', type=int, default=240, help='Number of frames to generate per year (default: 240)')
parser.add_argument('--preserve-colors', action='store_true', default=True, 
                    help='Preserve original colors in video (default: True)')
parser.add_argument('--quarters-only', action='store_true', help='Only generate frames for each quarter')
parser.add_argument('--duration', type=int, default=120, help='Target video duration in seconds (default: 120)')
args = parser.parse_args()

# Set quality parameters
FRAMES_PER_YEAR = args.frames_per_year if not args.quarters_only else 4
OUTPUT_DPI = 108  # Reduced from 144 to 108 for good balance of quality and performance
FIGURE_SIZE = (19.2, 10.8)  # 1080p size
LOGO_DPI = 300  # High DPI for sharp logos

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
        print(f"Using cached logo for size {target_size}")
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
        print(f"Original logo size: {original_size}, mode: {original_mode}")

        if target_size:
            w, h = target_size
            # Use a larger upscale for better quality
            large_size = (w * 3, h * 3)  # Increased upscale factor from 2 to 3
            print(f"Resizing to intermediate size: {large_size} using LANCZOS")
            image = image.resize(large_size, Image.Resampling.LANCZOS)

            # Apply stronger sharpening and contrast enhancement
            if original_mode == 'RGBA':
                r, g, b, a = image.split()
                rgb = Image.merge('RGB', (r, g, b))
                
                # Apply stronger sharpening
                enhancer = ImageEnhance.Sharpness(rgb)
                rgb = enhancer.enhance(1.8)  # Increased from 1.5 to 1.8
                
                # Add contrast enhancement
                contrast = ImageEnhance.Contrast(rgb)
                rgb = contrast.enhance(1.3)  # Increased from 1.2 to 1.3
                
                # Restore alpha channel
                r, g, b = rgb.split()
                image = Image.merge('RGBA', (r, g, b, a))
            else:
                # Apply stronger sharpening
                enhancer = ImageEnhance.Sharpness(image)
                image = enhancer.enhance(1.8)  # Increased from 1.5 to 1.8
                
                # Add contrast enhancement
                contrast = ImageEnhance.Contrast(image)
                image = contrast.enhance(1.3)  # Increased from 1.2 to 1.3

            # Apply unsharp mask filter for additional sharpness
            print("Applying UnsharpMask filter")
            image = image.filter(ImageFilter.UnsharpMask(radius=1.2, percent=180, threshold=3))
            
            # Resize to target size with high-quality resampling
            print(f"Final resize to target size: {target_size} using LANCZOS")
            image = image.resize(target_size, Image.Resampling.LANCZOS)

        result = np.array(image)
        print(f"Processed logo array shape: {result.shape}")
        logo_cache[cache_key] = result
        return result
        
    except Exception as e:
        print(f"Error in preprocess_logo: {e}")
        import traceback
        traceback.print_exc()
        # If preprocessing fails, return the original image
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
    ]
}

def get_logo_path(airline, year, iata_code, month=6):
    """Get the appropriate logo path based on airline name, year and month"""
    if airline not in logo_mapping:
        print(f"No logo mapping found for {airline} (IATA: {iata_code})")
        return None
        
    logo_versions = logo_mapping[airline]
    print(f"Found {len(logo_versions)} logo versions for {airline}")
    
    # 特殊处理Air France-KLM
    if airline == "Air France-KLM":
        # 2004年5月之前使用KLM logo
        if year < 2004 or (year == 2004 and month < 5):
            for version in logo_versions:
                if version["file"] == "airline-bar-video/logos/klm-1999-now.png":
                    logo_path = version["file"]
                    print(f"Selected KLM logo for {airline} ({year}-{month}): {logo_path}")
                    return logo_path if os.path.exists(logo_path) else None
        else:
            # 2004年5月及之后使用Air France-KLM logo
            for version in logo_versions:
                if version["file"] == "airline-bar-video/logos/Air-France-KLM-Holding-Logo.png":
                    logo_path = version["file"]
                    print(f"Selected Air France-KLM logo for {airline} ({year}-{month}): {logo_path}")
                    return logo_path if os.path.exists(logo_path) else None
    
    # 其他航空公司正常处理
    # Find the appropriate logo version for the given year
    for version in logo_versions:
        if version["start_year"] <= year <= version["end_year"]:
            logo_path = version["file"]
            print(f"Selected logo for {airline} ({year}): {logo_path}")
            
            if os.path.exists(logo_path):
                print(f"Verified logo file exists: {logo_path}")
                return logo_path
            else:
                print(f"ERROR: Logo file not found: {logo_path}")
                print(f"Current working directory: {os.getcwd()}")
                print(f"Absolute path would be: {os.path.abspath(logo_path)}")
                return None
    
    print(f"No logo version found for {airline} in year {year}")
    return None

def create_frame(frame_idx):
    """Optimized frame creation function for direct video rendering"""
    optimize_figure_for_performance()
    
    frame_int = int(frame_idx)
    frame_fraction = frame_idx - frame_int
    # Set strict uniform image size
    fig_width = FIGURE_SIZE[0]
    fig_height = FIGURE_SIZE[1]
    
    # Create figure with strict size
    fig = plt.figure(figsize=(fig_width, fig_height), facecolor='white', dpi=OUTPUT_DPI)
    
    # Ensure figure size is strictly uniform
    fig.set_size_inches(fig_width, fig_height, forward=True)
    
    # 使用更平滑的插值方法
    if frame_fraction == 0 or args.quarters_only:
        current_quarter = quarters[frame_int]
        quarter_data_main = revenue_data.loc[current_quarter]
        
        # For exact quarters, use the quarter data directly
        print(f"\nProcessing exact quarter frame for {current_quarter}")
        interpolated_data = quarter_data_main
    else:
        # 使用cubic插值方法代替线性插值
        if frame_int < len(quarters) - 1:
            q1 = quarters[frame_int]
            q2 = quarters[frame_int + 1]
            q1_data = revenue_data.loc[q1]
            q2_data = revenue_data.loc[q2]
            
            print(f"\nProcessing interpolated frame between {q1} and {q2} (fraction: {frame_fraction:.3f})")
            
            # 使用平滑的缓动函数代替线性插值
            # 平滑缓动：t * t * (3 - 2 * t) 代替简单的 t
            smooth_t = frame_fraction * frame_fraction * (3 - 2 * frame_fraction)
            
            # 使用平滑系数进行插值
            interpolated_data = q1_data * (1 - smooth_t) + q2_data * smooth_t
        else:
            # Fallback for last frame
            current_quarter = quarters[frame_int]
            interpolated_data = revenue_data.loc[current_quarter]
    
    # Create figure with optimized settings
    print(f"\nCreating frame {frame_idx} with figure size {FIGURE_SIZE}, DPI {OUTPUT_DPI}")
    
    # Set consistent color for all text elements and grid lines
    text_color = '#808080'
    
    # Create a gridspec with space for timeline and bars - adjusted ratios for layout
    gs = fig.add_gridspec(2, 1, height_ratios=[0.15, 1], 
                          left=0.1, right=0.9,  # Fixed left/right margins
                          bottom=0.1, top=0.95,  # Fixed top/bottom margins
                          hspace=0.05)
    
    # Create axis for timeline
    ax_timeline = fig.add_subplot(gs[0])
    
    # Create main axis for bar chart
    ax = fig.add_subplot(gs[1])

    # Get data for the current quarter
    quarter_data = []
    colors = []
    labels = []
    logos = []
    logos_data = []
    
    # Get the current quarter from integer part of frame_idx
    if frame_int < len(quarters):
        current_quarter = quarters[frame_int]
    else:
        current_quarter = quarters[-1]
    
    # Parse quarter info
    year, quarter = parse_quarter(current_quarter)
    
    # If we're at an interpolated frame, adjust the quarter display
    if frame_fraction > 0:
        # Calculate the exact decimal year
        year_fraction = year + (quarter - 1) * 0.25 + frame_fraction * 0.25
        year_integer = int(year_fraction)
        month = int((year_fraction - year_integer) * 12) + 1
        quarter_display = f"{year_integer} {month:02d}"
        
        # 精确计算当前的年和月，用于KLM/Air France-KLM的判断
        current_month = month
        current_year = year_integer
    else:
        quarter_display = f"{year} Q{quarter}"
        
        # 对于季度帧，估算月份（Q1=2月, Q2=5月, Q3=8月, Q4=11月）
        month_mapping = {1: 2, 2: 5, 3: 8, 4: 11}
        current_month = month_mapping[quarter]
        current_year = year
    
    print(f"\nProcessing frame for {quarter_display}")
    
    # Iterate through airlines
    for airline in interpolated_data.index:
        value = interpolated_data[airline]
        if pd.notna(value) and value > 0:  # Only include positive non-null values
            quarter_data.append(value)
            region = metadata.loc['Region', airline]
            colors.append(region_colors.get(region, '#808080'))  # Default to gray if region not found
            
            # Special handling for Air France-KLM label
            if airline == "Air France-KLM":
                # 精确判断是否在2004年5月之前
                if current_year < 2004 or (current_year == 2004 and current_month < 5):
                    labels.append("KL")
                else:
                    # Use IATA code instead of full name
                    iata_code = metadata.loc['IATA Code', airline]
                    labels.append(iata_code if pd.notna(iata_code) else airline[:3])
            else:
                # Use IATA code instead of full name
                iata_code = metadata.loc['IATA Code', airline]
                labels.append(iata_code if pd.notna(iata_code) else airline[:3])
            # Get logo path using IATA code and current_year/current_month
            logo_path = get_logo_path(airline, current_year, iata_code, current_month)
            logos.append(logo_path)
    
    # Check if we have any valid data
    if not quarter_data:
        print(f"\nWarning: No valid data for quarter {current_quarter}")
        fig.suptitle(f'No data available for {current_quarter}', fontsize=14)
        buf = BytesIO()
        plt.savefig(buf, format='rgba', dpi=OUTPUT_DPI)
        buf.seek(0)
        plt.close(fig)
        return np.frombuffer(buf.getvalue(), dtype=np.uint8).reshape((int(fig_height * OUTPUT_DPI), int(fig_width * OUTPUT_DPI), -1))
    
    # Sort data in descending order
    sorted_indices = np.argsort(quarter_data)[::-1]  # Reverse order for descending
    quarter_data = [quarter_data[i] for i in sorted_indices]
    colors = [colors[i] for i in sorted_indices]
    labels = [labels[i] for i in sorted_indices]
    logos = [logos[i] for i in sorted_indices]
    
    # Limit to top N airlines
    if len(quarter_data) > MAX_BARS:
        quarter_data = quarter_data[:MAX_BARS]
        colors = colors[:MAX_BARS]
        labels = labels[:MAX_BARS]
        logos = logos[:MAX_BARS]
    
    # Calculate fixed positions for bars
    num_bars = len(quarter_data)
    y_positions = np.arange(num_bars) * TOTAL_BAR_HEIGHT
    
    # Create bars
    bars = ax.barh(y_positions, quarter_data, 
                   height=BAR_HEIGHT, 
                   color=colors,
                   edgecolor='none')
    
    # Add logos
    for i, (logo_path, y) in enumerate(zip(logos, y_positions)):
        if logo_path and os.path.exists(logo_path):
            try:
                print(f"Loading logo from: {logo_path}")
                img = plt.imread(logo_path)
                
                # Calculate logo dimensions, maintaining aspect ratio
                img_height = BAR_HEIGHT * 0.8  # Set to 80% of bar height
                aspect_ratio = img.shape[1] / img.shape[0]
                img_width = img_height * aspect_ratio
                
                # Calculate target size in pixels
                target_height_pixels = int(40)  # Fixed height of 40 pixels
                target_width_pixels = int(target_height_pixels * aspect_ratio)
                
                print(f"Processing logo with size: {target_width_pixels}x{target_height_pixels} pixels")
                
                # Process logo image - convert to PIL image for processing
                if isinstance(img, np.ndarray):
                    if img.dtype == np.float32:
                        img = (img * 255).astype(np.uint8)
                    pil_img = Image.fromarray(img)
                else:
                    pil_img = img
                
                # Resize with high quality
                pil_img = pil_img.resize((target_width_pixels, target_height_pixels), Image.Resampling.LANCZOS)
                
                # Apply sharpening enhancement
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
                
                # Convert back to numpy array
                img_array = np.array(pil_img)
                
                # Convert back to format matplotlib can use
                if img_array.dtype != np.float32 and img_array.max() > 1.0:
                    img_array = img_array.astype(np.float32) / 255.0
                
                # Save processed logo data, to add later after calculating display_max
                logos_data.append({
                    'img_array': img_array,
                    'index': i,
                    'y': y
                })
                
                print(f"Processed logo successfully")
            except Exception as e:
                print(f"Error loading logo {logo_path}: {e}")
                # Print full exception stack trace for debugging
                import traceback
                traceback.print_exc()
                # Don't let logo issues stop processing
                continue
    
    # Customize the plot
    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels, fontsize=TICK_FONT_SIZE, color=text_color)
    
    # Add value labels at the end of the bars
    for i, bar in enumerate(bars):
        value = quarter_data[i]
        value_text = format_revenue(value, None)
        ax.text(value + (max(quarter_data) * 0.01), y_positions[i], value_text,
                va='center', ha='left', fontsize=VALUE_FONT_SIZE)
    
    # Format x-axis with custom formatter and set consistent colors
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(format_revenue))
    ax.xaxis.set_tick_params(labelsize=TICK_FONT_SIZE, colors=text_color)
    for label in ax.get_xticklabels():
        label.set_color(text_color)
    
    # Set axis limits with padding for logos and labels
    max_value = max(quarter_data) if quarter_data else 0
    
    # Get historical maximum value across all quarters up to current frame
    historical_max = 0
    for i in range(frame_int + 1):
        quarter_historical = quarters[i]
        historical_data = revenue_data.loc[quarter_historical]
        quarter_max = historical_data.max()
        if pd.notna(quarter_max) and quarter_max > historical_max:
            historical_max = quarter_max
    
    # Use max of current frame and historical max
    display_max = max(max_value, historical_max)
    ax.set_xlim(0, display_max * 1.3)  # Add extra space on the right for logos and labels
    
    # Now add all processed logos with adjusted positions based on display_max
    for logo_data in logos_data:
        i = logo_data['index']
        y = logo_data['y']
        img_array = logo_data['img_array']
        
        # Calculate logo position (right side of bar)
        value = quarter_data[i]
        value_width = len(format_revenue(value, None)) * 10  # Approximate text width
        
        # 使用更平滑的偏移量计算方法
        # 基础偏移系数，根据值的大小来平滑调整
        base_offset_percentage = 0.04 + 0.02 * (1 - min(value / display_max, 1))
        text_padding = value_width / 100
        
        # 确保logo和数值标签之间有足够的间距
        min_offset = display_max * 0.08
        # 对偏移量应用平方根平滑化，使得短条和长条的logo位置变化更加均匀
        x_offset = max(min_offset, display_max * base_offset_percentage * (0.5 + 0.5 * np.sqrt(value / display_max)) + text_padding)
        
        # 对非常短的条做特殊处理，让位置变化更平滑
        if value < display_max * 0.1:  # 如果值小于最大值的10%
            # 使用平滑插值而不是简单乘法
            factor = 1.5 - 0.5 * (value / (display_max * 0.1))
            x_offset *= factor
        
        x = value + x_offset  # 计算最终位置
        
        # Create OffsetImage and add to chart
        zoom_factor = 0.8
        
        # Special handling for Air France-KLM logo to make it smaller
        current_logo_path = logos[i] if i < len(logos) else None
        if current_logo_path == "airline-bar-video/logos/Air-France-KLM-Holding-Logo.png":
            zoom_factor = 0.5  # Reduce zoom factor for this specific logo
            print(f"Applying smaller zoom factor ({zoom_factor}) for Air France-KLM logo")
        
        imagebox = OffsetImage(img_array, zoom=zoom_factor)
        ab = AnnotationBbox(imagebox, (x, y),
                          box_alignment=(0, 0.5),  # Left-center alignment
                          frameon=False)
        ax.add_artist(ab)
        print(f"Added logo successfully at position ({x}, {y})")
    
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
    ax.set_xlabel('Revenue', fontsize=16, labelpad=10, color=text_color)  # Increased from 12 to 16
    
    # Set up timeline - New style
    ax_timeline.set_facecolor('none')  # Transparent background
    
    # Get min and max quarters for timeline
    min_quarter = quarters[0]
    max_quarter = quarters[-1]
    min_year, min_q = parse_quarter(min_quarter)
    max_year, max_q = parse_quarter(max_quarter)
    
    # Set timeline limits with padding - 增加右侧空间以显示2025年
    ax_timeline.set_xlim(-1, len(quarters) + 0.5)  # 增加右侧空间
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
    for i, quarter in enumerate(quarters):
        year, q = parse_quarter(quarter)
        if q == 1:  # Major tick for Q1
            ax_timeline.vlines(i, -0.03, 0, colors=text_color, linewidth=1.5)
            # Show label for every year with increased font size
            ax_timeline.text(i, -0.07, str(year), ha='center', va='top', 
                           fontsize=16, color=text_color)  # Increased from 12 to 16
        else:  # Minor tick for other quarters
            ax_timeline.vlines(i, -0.02, 0, colors=text_color, linewidth=0.5, alpha=0.7)
    
    # 确保2025年的标记显示在时间轴上
    # 检查最后一个季度是否为2024年第4季度
    last_year, last_q = parse_quarter(quarters[-1])
    if last_year == 2024 and last_q == 4:
        # 在时间轴上添加2025年的标记
        next_year_pos = len(quarters)
        ax_timeline.vlines(next_year_pos, -0.03, 0, colors=text_color, linewidth=1.5)
        ax_timeline.text(next_year_pos, -0.07, "2025", ha='center', va='top', 
                       fontsize=16, color=text_color)
    
    # Add current position marker (inverted triangle)
    timeline_position = frame_int + frame_fraction
    ax_timeline.plot(timeline_position, 0.03, marker='v', color='#4e843d', markersize=10, zorder=5)
    
    # Remove timeline ticks
    ax_timeline.set_xticks([])
    ax_timeline.set_yticks([])
    
    # Remove the current quarter display
    # The following line is commented out to remove the quarter display above the timeline
    # ax_timeline.text(len(quarters)/2, 0.15, quarter_display, 
    #                ha='center', va='center', fontsize=14, color='black', 
    #                bbox=dict(facecolor='white', alpha=0.8, edgecolor='none', boxstyle='round,pad=0.5'))
    
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
        crf = '15'  # 降低CRF以提高质量（从17降低到15）
        preset = 'slow'  # Slow preset for better compression
        bitrate = '15M'  # 增加比特率从12M到15M
    elif args.quality == 'medium':
        crf = '20'  # 从22降低到20
        preset = 'medium'
        bitrate = '10M'  # 从8M增加到10M
    else:  # low
        crf = '25'  # 从27降低到25
        preset = 'fast'
        bitrate = '6M'  # 从4M增加到6M
    
    # Choose pixel format based on preserve-colors setting
    if args.preserve_colors:
        # Use higher quality pixel format to preserve color accuracy
        pix_fmt = 'yuv444p'  # No chroma subsampling, better color preservation
    else:
        pix_fmt = 'yuv420p'  # Standard format, but has chroma subsampling
    
    return {
        'crf': crf,
        'preset': preset,
        'bitrate': bitrate,
        'pix_fmt': pix_fmt
    }

def create_video_directly(frame_indices, output_path, fps):
    """Create video directly from matplotlib frames without saving intermediate PNGs"""
    # Get the first frame to determine dimensions
    print("Creating test frame to determine dimensions...")
    test_frame = create_frame(frame_indices[0])
    height, width, channels = test_frame.shape
    print(f"Frame dimensions: {width}x{height}, {channels} channels")
    
    # Check if FFmpeg is installed
    try:
        subprocess.check_output(['ffmpeg', '-version'], stderr=subprocess.STDOUT)
        print("FFmpeg detected - using FFmpeg for video encoding")
        
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
            output_path
        ]
        
        print(f"FFmpeg command: {' '.join(command)}")
        ffmpeg_process = subprocess.Popen(command, stdin=subprocess.PIPE)
        
        # Create a progress bar
        total_frames = len(frame_indices)
        with tqdm(total=total_frames, desc="Creating video") as pbar:
            for frame_idx in frame_indices:
                # Create the frame
                frame = create_frame(frame_idx)
                
                # Convert frame if needed
                if frame.dtype != np.uint8:
                    frame = (frame * 255).astype(np.uint8)
                
                # Ensure frame is in correct RGB format
                if frame.shape[2] == 4:  # RGBA format
                    frame = frame[:, :, :3]  # Remove alpha channel
                
                # Write the frame to FFmpeg process
                ffmpeg_process.stdin.write(frame.tobytes())
                pbar.update(1)
        
        # Close the pipe and wait for FFmpeg to finish
        ffmpeg_process.stdin.close()
        ffmpeg_process.wait()
        
        if ffmpeg_process.returncode != 0:
            print(f"FFmpeg error: returned code {ffmpeg_process.returncode}")
            return False
        
        # Check if output file was created successfully
        if os.path.exists(output_path) and os.path.getsize(output_path) > 100000:
            output_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"\nVideo created successfully: {output_path}")
            print(f"Video size: {output_size_mb:.2f} MB")
            print(f"Duration: {total_frames / fps:.2f} seconds ({total_frames / fps / 60:.2f} minutes)")
            print(f"Resolution: {width}x{height}")
            return True
        else:
            print("Error: Output file too small or not created")
            return False
            
    except (FileNotFoundError, subprocess.SubprocessError) as e:
        print(f"FFmpeg not found or error during execution: {e}")
        print("Falling back to OpenCV video creation")
        
        # Try using OpenCV as a fallback
        try:
            # Initialize video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Try MP4V codec
            out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
            
            if not out.isOpened():
                print("Error: Could not open OpenCV VideoWriter")
                return False
            
            # Create frames and write to video
            for frame_idx in tqdm(frame_indices, desc="Creating video with OpenCV"):
                frame = create_frame(frame_idx)
                
                # Convert frame to BGR format (required by OpenCV)
                if frame.dtype != np.uint8:
                    frame = (frame * 255).astype(np.uint8)
                
                # Convert RGB to BGR
                if frame.shape[2] >= 3:
                    frame = cv2.cvtColor(frame[:, :, :3], cv2.COLOR_RGB2BGR)
                
                # Write the frame
                out.write(frame)
            
            # Release the video writer
            out.release()
            
            # Check if output file was created successfully
            if os.path.exists(output_path) and os.path.getsize(output_path) > 100000:
                output_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                print(f"\nVideo created successfully with OpenCV: {output_path}")
                print(f"Video size: {output_size_mb:.2f} MB")
                print(f"Duration: {len(frame_indices) / fps:.2f} seconds ({len(frame_indices) / fps / 60:.2f} minutes)")
                print(f"Resolution: {width}x{height}")
                return True
            else:
                print("Error: Output file too small or not created with OpenCV")
                return False
                
        except Exception as e:
            print(f"Error creating video with OpenCV: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    # Load the data from CSV
    print("Loading data...")
    global metadata, revenue_data, quarters
    
    # Use global scope for these variables
    df = pd.read_csv('airline-bar-video/airlines_final.csv')  # 使用新的airlines_final.csv
    
    # Print all airline data from the CSV
    print("\nAll airline data from CSV:")
    print(df.iloc[7:])
    
    # Process metadata
    metadata = df.iloc[:7].copy()  # First 7 rows contain metadata
    revenue_data = df.iloc[7:].copy()  # Revenue data starts from row 8
    
    # Set proper index for metadata
    metadata.set_index(metadata.columns[0], inplace=True)
    
    # Print raw revenue data before conversion
    print("\nRaw revenue data before conversion:")
    print(revenue_data.head())
    
    # Convert revenue columns by removing ' M' suffix, commas, and converting to float
    for col in revenue_data.columns[1:]:  # Skip the first column which contains row labels
        revenue_data[col] = pd.to_numeric(revenue_data[col].str.replace(',', '').str.replace(' M', ''), errors='coerce')
    
    # Set index for revenue data
    revenue_data.set_index(revenue_data.columns[0], inplace=True)
    
    # Get the quarters from the revenue data index
    quarters = revenue_data.index.tolist()
    
    # Print logo files at start
    print("\nLogo files in logos directory:")
    logo_files = os.listdir(logos_dir)
    print("\n".join(sorted(logo_files)))
    print(f"\nTotal logo files found: {len(logo_files)}\n")
    
    # 检查Emirates logo文件是否存在
    if os.path.exists("airline-bar-video/logos/Emirates-logo.jpg"):
        print("✓ Emirates logo found")
    else:
        print("✗ Emirates logo NOT found! Please ensure the file exists.")
    
    # Check font configurations
    # Check for Monda font, otherwise use a system sans-serif font
    font_path = None
    system_fonts = fm.findSystemFonts()
    for font in system_fonts:
        if 'monda' in font.lower():
            font_path = font
            break
    
    if font_path:
        monda_font = fm.FontProperties(fname=font_path)
        print(f"Found Monda font at: {font_path}")
    else:
        monda_font = fm.FontProperties(family='sans-serif')
        print("Monda font not found, using default sans-serif")
    
    # Verify key logo files
    important_logos = [
        "logos/american-airlines-2013-now.jpg",
        "logos/delta-air-lines-2007-now.jpg",
        "logos/southwest-airlines-2014-now.png",
        "logos/Emirates-logo.jpg"  # 添加Emirates logo到验证列表
    ]
    
    print("\nVerifying key logo files:")
    for logo in important_logos:
        if os.path.exists(logo):
            print(f"  ✓ {logo} exists")
        else:
            print(f"  ✗ {logo} MISSING")
    
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
        print(f"Quarters-only mode: Generating {total_frames} frames (one per quarter)")
    else:
        # In normal mode, generate multiple frames between quarters based on FRAMES_PER_YEAR
        frames_per_quarter = FRAMES_PER_YEAR // 4
        print(f"Normal mode: Generating approximately {frames_per_quarter} frames per quarter")
        
        # Create frame indices with appropriate interpolation between quarters
        frame_indices = []
        
        # Generate frames based on FRAMES_PER_YEAR
        for i in range(total_quarters - 1):
            # Add the main quarter frame
            frame_indices.append(i)
            
            # Add interpolated frames between quarters
            for j in range(1, frames_per_quarter):
                # Calculate fractional index for interpolation
                fraction = j / frames_per_quarter
                frame_indices.append(i + fraction)
        
        # Add the last quarter
        frame_indices.append(total_quarters - 1)
        total_frames = len(frame_indices)
        
        # Sort frames to ensure sequential generation
        frame_indices.sort()
    
    print(f"Total frames to generate: {total_frames}")
    print(f"First few frame indices: {frame_indices[:10]}")
    
    # Calculate appropriate FPS based on desired duration
    fps = args.fps
    if args.duration:
        calculated_fps = total_frames / args.duration
        if calculated_fps < fps:
            fps = calculated_fps  # Use calculated FPS if it's lower than requested FPS
            print(f"Adjusted FPS to {fps:.2f} to match {args.duration} second duration")
    
    estimated_duration = total_frames / fps
    print(f"Using {fps:.2f} fps")
    print(f"Estimated video duration: {estimated_duration:.2f} seconds ({estimated_duration/60:.2f} minutes)")
    
    # Create video directly
    success = create_video_directly(frame_indices, args.output, fps)
    
    if success:
        print("\nVideo creation completed successfully!")
    else:
        print("\nThere were issues creating the video. Please check the logs.")

if __name__ == "__main__":
    try:
        # Set up to display more debug info
        print("Running with extra logging enabled...")
        
        # Run main program
        main()
    except Exception as e:
        print(f"ERROR in main program execution: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1) 