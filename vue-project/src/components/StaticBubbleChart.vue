<template>
  <div class="chart-container">
    <div class="flex justify-end mb-4 gap-4">
      <button 
        @click="toggleDataDisplay"
        class="px-4 py-2 bg-wego-green text-white rounded hover:bg-wego-green-dark flex items-center gap-2"
      >
        {{ showLabels ? 'Show Dots' : 'Show Labels' }}
      </button>
      <button 
        @click="saveChart"
        class="px-4 py-2 bg-wego-green text-white rounded hover:bg-wego-green-dark flex items-center gap-2"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
          <path d="M7.707 10.293a1 1 0 10-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 11.586V6h-2v5.586l-1.293-1.293z" />
          <path d="M3 17a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" />
        </svg>
        Save Chart
      </button>
    </div>
    <div id="static-chart" class="w-full h-full"></div>
  </div>
</template>
<!-- TODO: detect null value and delete it from the chart -->
 <!-- TODO: add delete method for delete the logo on teh page -->
<style scoped>
.chart-container {
  width: 100%;
  height: 100%;
  min-height: 840px;
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.zero-line {
  opacity: 0.5;
}

.dot, .cross {
  cursor: pointer;
  transition: all 0.2s ease;
}

.dot:hover, .cross:hover {
  transform: scale(1.5);
}

.quarter-label {
  pointer-events: none;
  user-select: none;
}

.active {
  stroke: #000;
  stroke-width: 2px;
}

.logo {
  cursor: move;
  user-select: none;
}
</style>

<script setup>
import { onMounted, ref } from 'vue';
import * as d3 from 'd3';
import * as XLSX from 'xlsx';

// Import all logos
import ABNB_LOGO from '/logos/ABNB_logo.png'
import BKNG_LOGO from '/logos/BKNG_logo.png'
import EXPE_LOGO from '/logos/EXPE_logo.png'
import TCOM_LOGO from '/logos/TCOM_logo.png'
import TRIP_LOGO from '/logos/TRIP_logo.png'
import TRVG_LOGO from '/logos/TRVG_logo.png'
import EDR_LOGO from '/logos/EDR_logo.png'
import DESP_LOGO from '/logos/DESP_logo.png'
import MMYT_LOGO from '/logos/MMYT_logo.png'
import IXIGO_LOGO from '/logos/IXIGO_logo.png'
import LMN_LOGO from '/logos/LMN_logo.png'
import YTRA_LOGO from '/logos/YTRA_logo.png'
import OWW_LOGO from '/logos/OWW_logo.png'
import TRAVELOCITY_LOGO from '/logos/Travelocity_logo.png'
import EASEMYTRIP_LOGO from '/logos/EASEMYTRIP_logo.png'
import WEGO_LOGO from '/logos/Wego_logo.png'
import SKYSCANNER_LOGO from '/logos/Skyscanner_logo.png'
import ETRAVELI_LOGO from '/logos/Etraveli_logo.png'
import KIWI_LOGO from '/logos/Kiwi_logo.png'
import CLEARTRIP_LOGO from '/logos/Cleartrip_logo.png'
import TRAVELOKA_LOGO from '/logos/Traveloka_logo.png'
import FLIGHTCENTRE_LOGO from '/logos/FlightCentre_logo.png'
import SEERA_LOGO from '/logos/SEERA_logo.png'

// Add new logo imports after existing imports
import ALMOSAFER_LOGO from '/logos/Almosafer_logo.png'
import OTA_LOGO from '/logos/OTA_logo.png'

const colorDict = {
  'ABNB': '#ff5895',
  'Almosafer': '#bb5387',
  'BKNG': '#003480',
  'DESP': '#755bd8',
  'EXPE': '#fbcc33',
  'EaseMyTrip': '#00a0e2',
  'Ixigo': '#e74c3c',
  'MMYT': '#e74c3c',
  'TRIP': '#00af87',
  'TRVG': '#e74c3c',
  'Wego': '#4e843d',
  'Yatra': '#e74c3c',
  'TCOM': '#2577e3',
  'EDR': '#2577e3',
  'LMN': '#fc03b1',
  'PCLN': '#003480',
  'Orbitz': '#8edbfa',
  'Travelocity': '#1d3e5c',
  'Skyscanner': '#0770e3',
  'Etraveli': '#b2e9ff',
  'Kiwi': '#e5fdd4',
  'Cleartrip': '#e74c3c',
  'Traveloka': '#38a0e2',
  'FLT': '#d2b6a8',
  'Webjet OTA': '#e74c3c'
};

const logoDict = {
  'ABNB': ABNB_LOGO,
  'BKNG': BKNG_LOGO,
  'EXPE': EXPE_LOGO,
  'TCOM': TCOM_LOGO,
  'TRIP': TRIP_LOGO,
  'TRVG': TRVG_LOGO,
  'EDR': EDR_LOGO,
  'DESP': DESP_LOGO,
  'MMYT': MMYT_LOGO,
  'Ixigo': IXIGO_LOGO,
  'LMN': LMN_LOGO,
  'Yatra': YTRA_LOGO,
  'Orbitz': OWW_LOGO,
  'Travelocity': TRAVELOCITY_LOGO,
  'EaseMyTrip': EASEMYTRIP_LOGO,
  'Wego': WEGO_LOGO,
  'Skyscanner': SKYSCANNER_LOGO,
  'Etraveli': ETRAVELI_LOGO,
  'Kiwi': KIWI_LOGO,
  'Cleartrip': CLEARTRIP_LOGO,
  'Traveloka': TRAVELOKA_LOGO,
  'FLT': FLIGHTCENTRE_LOGO,
  'Almosafer': ALMOSAFER_LOGO,
  'Webjet OTA': OTA_LOGO
};

const companyNames = {
  'ABNB': 'Airbnb',
  'BKNG': 'Booking.com',
  'EXPE': 'Expedia',
  'TCOM': 'Trip.com',
  'TRIP': 'TripAdvisor',
  'TRVG': 'Trivago',
  'EDR': 'Edreams',
  'DESP': 'Despegar',
  'MMYT': 'MakeMyTrip',
  'Ixigo': 'Ixigo',
  'LMN': 'Lastminute',
  'Yatra': 'Yatra.com',
  'Orbitz': 'Orbitz',
  'Travelocity': 'Travelocity',
  'EaseMyTrip': 'EaseMyTrip',
  'Wego': 'Wego',
  'Skyscanner': 'Skyscanner',
  'Etraveli': 'Etraveli',
  'Kiwi': 'Kiwi',
  'Cleartrip': 'Cleartrip',
  'FLT': 'Flight Centre',
  'Almosafer': 'Almosafer',
  'Webjet OTA': 'Webjet OTA'
};

let chartData = ref([]);

// Fixed domains for consistent scaling
const globalXDomain = [-0.15, 0.60];  // EBITDA margin range
const globalYDomain = [-0.15, 0.85];  // Revenue growth range

// Add state to store adjusted positions
const logoPositions = ref({});

// Add drag behavior function
const createDragBehavior = (xScale, yScale) => {
  return d3.drag()
    .on('drag', (event, d) => {
      const logoGroup = d3.select(event.sourceEvent.target.parentNode);
      const newX = parseFloat(logoGroup.select('image').attr('x')) + event.dx;
      const newY = parseFloat(logoGroup.select('image').attr('y')) + event.dy;
      
      logoGroup.select('image')
        .attr('x', newX)
        .attr('y', newY);
      
      // Store the adjusted position
      logoPositions.value[d.company] = { x: newX, y: newY };
    });
};

// Add state for display toggle
const showLabels = ref(false);

// Add toggle function
const toggleDataDisplay = () => {
  showLabels.value = !showLabels.value;
  initChart(); // Redraw chart with new display type
};

// Add after imports
const EXCEL_URL = 'https://1drv.ms/x/c/130fda80f0432a83/EaUo2h8IJTZDsA5Rmm-FVDcB_-0mTOTuBOEN26R8EDarGQ?download=1';

// Add after the imports and before onMounted
const processExcelData = (file) => {
  console.log('Processing Excel file:', file.name);
  const reader = new FileReader();
  
  reader.onload = async (e) => {
    try {
      const data = new Uint8Array(e.target.result);
      const workbook = XLSX.read(data, { type: 'array' });
      console.log('Available sheets:', workbook.SheetNames);
      
      // Get the TTM sheet
      const ttmSheet = workbook.Sheets['TTM (bounded)'];
      if (!ttmSheet) {
        console.error('TTM (bounded) sheet not found');
        return;
      }

      // Convert sheet to JSON with headers
      const jsonData = XLSX.utils.sheet_to_json(ttmSheet, { header: 1 });
      console.log('First row:', jsonData[0]);
      
      // Find target quarter rows
      let growthRowIndex = -1;
      let marginRowIndex = -1;
      
      jsonData.forEach((row, index) => {
        if (!row[0]) return;
        const quarter = String(row[0]).trim();
        if (quarter === '2024\'Q4') {
          if (index <= 115) {
            growthRowIndex = index;
          } else {
            marginRowIndex = index;
          }
        }
      });
      
      console.log('Found indices:', { growthRowIndex, marginRowIndex });
      
      if (growthRowIndex === -1 || marginRowIndex === -1) {
        throw new Error('Required data rows not found');
      }
      
      const headers = jsonData[0];
      const growthRow = jsonData[growthRowIndex];
      const marginRow = jsonData[marginRowIndex];
      
      const processedData = [];
      
      headers.forEach((company, index) => {
        if (!company || index === 0) return;
        
        const revenueGrowth = parseFloat(growthRow[index]);
        const ebitdaMargin = parseFloat(marginRow[index]);
        
        console.log(`Processing ${company}:`, {
          revenueGrowth,
          ebitdaMargin,
          isValid: !isNaN(revenueGrowth) && !isNaN(ebitdaMargin)
        });
        
        if (!isNaN(revenueGrowth) && !isNaN(ebitdaMargin) &&
            revenueGrowth >= globalYDomain[0] && revenueGrowth <= globalYDomain[1] &&
            ebitdaMargin >= globalXDomain[0] && ebitdaMargin <= globalXDomain[1]) {
          processedData.push({
            company: company.trim(),
            ebitdaMargin: ebitdaMargin,
            revenueGrowth: revenueGrowth
          });
        }
      });
      
      console.log('Processed data:', processedData);
      
      if (processedData.length === 0) {
        throw new Error('No valid data points found');
      }
      
      // Update chart data
      chartData.value = processedData;
      console.log('Chart data updated:', chartData.value);
      
      // Initialize chart
      initChart();
      
    } catch (error) {
      console.error('Error processing Excel file:', error);
      console.error('Error stack:', error.stack);
    }
  };
  
  reader.onerror = (error) => {
    console.error('Error reading file:', error);
  };
  
  reader.readAsArrayBuffer(file);
};

// Update fetchDataFromUrl function
const fetchDataFromUrl = async () => {
  console.log('Using static data...');
  try {
    // Static data - removed SEERA and fixed company names
    const companies = ['ABNB', 'BKNG', 'EXPE', 'TCOM', 'TRIP', 'TRVG', 'EDR', 'DESP', 'MMYT', 'Ixigo', 'Almosafer', 'Wego', 'Webjet', 'Webjet OTA', 'Cleartrip Arabia', 'LMN', 'EaseMyTrip', 'Yatra'];
    const revenueGrowth = [0.13, 0.12, 0.07, 0.29, 0.04, -0.08, 0.06, 0.17, 0.29, 0.26, 0.47, 0.59, null, 0.10, null, -0.07, 0.02, 0.33];
    const ebitdaMargin = [0.21, 0.27, 0.10, 0.31, 0.07, -0.07, 0.13, 0.07, 0.14, 0.09, 0.06, 0.14, null, 0.50, null, 0.12, 0.43, 0.00];
    
    const processedData = [];
    
    companies.forEach((company, index) => {
      const growth = revenueGrowth[index];
      const margin = ebitdaMargin[index];
      
      // Skip if either value is null or undefined
      if (growth === null || margin === null || growth === undefined || margin === undefined) {
        console.log(`Skipping ${company} due to missing data`);
        return;
      }
      
      console.log(`Processing ${company}:`, {
        revenueGrowth: growth,
        ebitdaMargin: margin,
        isValid: !isNaN(growth) && !isNaN(margin)
      });
      
      if (!isNaN(growth) && !isNaN(margin) &&
          growth >= globalYDomain[0] && growth <= globalYDomain[1] &&
          margin >= globalXDomain[0] && margin <= globalXDomain[1]) {
        processedData.push({
          company: company,
          ebitdaMargin: margin,
          revenueGrowth: growth
        });
      }
    });
    
    console.log('Processed data:', processedData);
    
    if (processedData.length === 0) {
      throw new Error('No valid data points found');
    }
    
    // Update chart data
    chartData.value = processedData;
    console.log('Chart data updated:', chartData.value);
    
    // Initialize chart
    initChart();
    
  } catch (error) {
    console.error('Error processing static data:', error);
    console.error('Error stack:', error.stack);
    
    // Show error message in chart area
    const container = d3.select('#static-chart')
      .append('div')
      .style('text-align', 'center')
      .style('padding-top', '40px')
      .style('color', '#e74c3c');

    container.append('div')
      .style('font-size', '18px')
      .style('font-weight', 'bold')
      .style('margin-bottom', '12px')
      .text('Error loading data');

    container.append('div')
      .style('font-size', '14px')
      .text('Please try refreshing the page or contact support if the issue persists.');
  }
};

// Update onMounted hook
onMounted(async () => {
  console.log('Component mounted, fetching data...');
  await fetchDataFromUrl();
});

// Initialize chart
const initChart = () => {
  try {
    console.log('Starting chart initialization with data:', chartData.value);
    
    // Clear previous chart
    d3.select('#static-chart').selectAll('*').remove();
    
    // Skip if no data
    if (!chartData.value || chartData.value.length === 0) {
      console.log('No data to display');
      const container = d3.select('#static-chart')
        .append('div')
        .style('text-align', 'center')
        .style('padding-top', '40px')
        .style('color', '#4e843d');  // Wego green color

      container.append('div')
        .style('font-size', '18px')
        .style('font-weight', 'bold')
        .style('margin-bottom', '12px')
        .text('No data to display');

      container.append('div')
        .style('font-size', '14px')
        .text('Please click the "Upload XLSX" button in the header to load your data.');

      return;
    }

    // Log data points for debugging
    chartData.value.forEach(d => {
      console.log('Processing data point:', {
        company: d.company,
        ebitdaMargin: d.ebitdaMargin,
        revenueGrowth: d.revenueGrowth,
        hasLogo: !!logoDict[d.company],
        color: colorDict[d.company]
      });
    });
    
    // Create SVG
    const svg = d3.select('#static-chart').append('svg')
      .attr('width', '100%')
      .attr('height', '100%')
      .attr('viewBox', '0 0 1200 840')
      .attr('preserveAspectRatio', 'xMidYMid meet');

    const margin = { top: 40, right: 20, bottom: 50, left: 60 };
    const width = 1200 - margin.left - margin.right;
    const height = 840 - margin.top - margin.bottom;

    const g = svg.append("g")
      .attr("transform", `translate(${margin.left}, ${margin.top})`);

    // Initialize scales with fixed domains
    const xScale = d3.scaleLinear()
      .domain(globalXDomain)
      .range([0, width]);

    const yScale = d3.scaleLinear()
      .domain(globalYDomain)
      .range([height, 0]);

    // Create axes
    const xAxis = d3.axisBottom(xScale).tickFormat(d3.format('.0%'));
    const yAxis = d3.axisLeft(yScale).tickFormat(d3.format('.0%'));

    // Add axes
    g.append('g')
      .attr('class', 'x-axis')
      .attr('transform', `translate(0,${height})`)
      .call(xAxis);

    g.append('g')
      .attr('class', 'y-axis')
      .call(yAxis);

    // Add axis labels
    g.append('text')
      .attr('class', 'x-label')
      .attr('text-anchor', 'middle')
      .attr('x', width / 2)
      .attr('y', height + 40)
      .text('EBITDA Margin TTM')
      .style('font-size', '14px');

    g.append('text')
      .attr('class', 'y-label')
      .attr('text-anchor', 'middle')
      .attr('transform', 'rotate(-90)')
      .attr('y', -45)
      .attr('x', -height / 2)
      .text('Revenue Growth YoY TTM')
      .style('font-size', '14px');

    // Add zero lines
    g.append('line')
      .attr('class', 'zero-line')
      .attr('x1', xScale(0))
      .attr('y1', 0)
      .attr('x2', xScale(0))
      .attr('y2', height)
      .attr('stroke', '#4e843d')
      .attr('stroke-dasharray', '4,4');

    g.append('line')
      .attr('class', 'zero-line')
      .attr('x1', 0)
      .attr('y1', yScale(0))
      .attr('x2', width)
      .attr('y2', yScale(0))
      .attr('stroke', '#4e843d')
      .attr('stroke-dasharray', '4,4');

    // Add data points
    chartData.value.forEach(d => {
      console.log('Drawing data point:', d);
      
      // Skip invalid data points
      if (!d.company || isNaN(d.ebitdaMargin) || isNaN(d.revenueGrowth)) {
        console.log('Skipping invalid data point:', d);
        return;
      }

      // Add data point
      if (showLabels.value) {
        // Add text label
        g.append('text')
          .attr('class', 'data-label')
          .attr('x', xScale(d.ebitdaMargin))
          .attr('y', yScale(d.revenueGrowth))
          .attr('text-anchor', 'middle')
          .attr('dy', '0.35em')
          .style('font-size', '12px')
          .style('fill', colorDict[d.company] || '#000')
          .text(`${(d.revenueGrowth * 100).toFixed(1)}% / ${(d.ebitdaMargin * 100).toFixed(1)}%`);
      } else {
        // Add dot
        g.append('circle')
          .attr('class', 'data-dot')
          .attr('cx', xScale(d.ebitdaMargin))
          .attr('cy', yScale(d.revenueGrowth))
          .attr('r', 6)
          .style('fill', colorDict[d.company] || '#000')
          .style('stroke', 'white')
          .style('stroke-width', '2px');
      }

      // Add logo if available
      if (logoDict[d.company]) {
        const img = new Image();
        img.onload = () => {
          // Create a group for the logo to make dragging more stable
          const logoGroup = g.append('g')
            .attr('class', 'logo-group')
            .style('cursor', 'move');

          // Calculate initial position (centered on the data point)
          const logoSize = 96; // Increased from 80 to 96 (1.2x larger)
          const x = xScale(d.ebitdaMargin) - logoSize/2;
          const y = yScale(d.revenueGrowth) - logoSize/2 - 30; // Added -20 to move logo up
          
          // Add the logo image
          logoGroup.append('image')
            .attr('class', 'logo')
            .attr('width', logoSize)
            .attr('height', logoSize)
            .attr('xlink:href', logoDict[d.company])
            .attr('x', x)
            .attr('y', y);

          // Add invisible background rect to make dragging easier
          logoGroup.insert('rect', 'image')
            .attr('class', 'logo-hit-area')
            .attr('x', x)
            .attr('y', y)
            .attr('width', logoSize)
            .attr('height', logoSize)
            .attr('fill', 'transparent');

          // Apply drag behavior to the group
          logoGroup.call(d3.drag()
            .on('start', function() {
              d3.select(this).raise();
            })
            .on('drag', function(event) {
              const dx = event.dx;
              const dy = event.dy;
              
              // Update both rect and image positions
              const currentX = parseFloat(d3.select(this).select('image').attr('x'));
              const currentY = parseFloat(d3.select(this).select('image').attr('y'));
              
              d3.select(this).select('rect')
                .attr('x', currentX + dx)
                .attr('y', currentY + dy);
                
              d3.select(this).select('image')
                .attr('x', currentX + dx)
                .attr('y', currentY + dy);
            }));
        };
        img.src = logoDict[d.company];
      }
    });

  } catch (error) {
    console.error('Error initializing chart:', error);
    console.error('Error stack:', error.stack);
  }
};

// Add save chart function
const saveChart = async () => {
  try {
    const svgNode = document.querySelector('#static-chart svg');
    const svgWidth = svgNode.viewBox.baseVal.width || 1200;
    const svgHeight = svgNode.viewBox.baseVal.height || 840;
    
    // First, load all images
    const images = svgNode.querySelectorAll('image');
    await Promise.all(Array.from(images).map(async (image) => {
      try {
        const url = image.getAttribute('href') || image.getAttribute('xlink:href');
        const response = await fetch(url);
        if (!response.ok) throw new Error('Image load failed');
        const blob = await response.blob();
        const base64 = await new Promise((resolve) => {
          const reader = new FileReader();
          reader.onload = () => resolve(reader.result);
          reader.readAsDataURL(blob);
        });
        image.setAttribute('href', base64);
      } catch (error) {
        image.remove();
      }
    }));
    
    const svgData = new XMLSerializer().serializeToString(svgNode);
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    const img = new Image();
    
    // Set ultra-high resolution scale
    const scale = 8;  // Increased from 4 to 8 for maximum quality
    canvas.width = svgWidth * scale;
    canvas.height = svgHeight * scale;
    
    // Enable maximum quality image rendering
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';
    
    // Set white background
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    // Set image source with proper SVG dimensions
    const svgBlob = new Blob([svgData], { type: 'image/svg+xml;charset=utf-8' });
    const svgUrl = URL.createObjectURL(svgBlob);
    img.src = svgUrl;
    
    // Clean up the object URL after loading
    img.onload = () => {
      URL.revokeObjectURL(svgUrl);
      
      // Scale the context while maintaining aspect ratio
      ctx.scale(scale, scale);
      
      // Draw the image at the correct size
      ctx.drawImage(img, 0, 0, svgWidth, svgHeight);
      
      // Create download link with maximum quality PNG
      const link = document.createElement('a');
      link.download = '2024Q4_Market_Performance.png';
      canvas.toBlob((blob) => {
        link.href = URL.createObjectURL(blob);
        link.click();
        URL.revokeObjectURL(link.href);
      }, 'image/png', 1.0);
    };
  } catch (error) {
    console.error('Error saving chart:', error);
  }
};

// Expose methods
defineExpose({
  processExcelData,
  saveChart
});
</script> 