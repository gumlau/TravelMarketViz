// Your Google Sheets ID
const sheetId = '2PACX-1vQYwQTSYwig7AZ0fjPniLVfUUJnLz3PP4f4fBtqkBNPYqrkKtQyZDaB99kHk2eCzuCh5i8oxTPCHeQ9';

// Sheet names for each table (Revenue Growth, EBITDA Margin, Revenue)
const sheetNames = {
    revenueGrowth: 'Revenue Growth YoY',
    ebitdaMargin: 'EBITDA_MARGIN',
    revenue: 'Revenue'
};

// Array of company symbols to be selected by default
const defaultSelectedCompanies = ["Almosafer", "Cleartrip", "EaseMyTrip", "Ixigo", "MMYT", "Skyscanner", "Wego", "Yatra"];

// Company logos mapping
const companyLogos = {
    "ABNB": "logos/ABNB_logo.png",
    "BKNG": "logos/BKNG_logo.png",
    "EXPE": "logos/EXPE_logo.png",
    "TCOM": "logos/TCOM_logo.png",
    "TRIP": "logos/TRIP_logo.png",
    "TRVG": "logos/TRVG_logo.png",
    "EDR": "logos/EDR_logo.png",
    "DESP": "logos/DESP_logo.png",
    "MMYT": "logos/MMYT_logo.png",
    "Ixigo": "logos/IXIGO_logo.png",
    "SEERA": "logos/SEERA_logo.png",
    "Webjet": "logos/WEB_logo.png",
    "LMN": "logos/LMN_logo.png",
    "Yatra": "logos/YTRA_logo.png",
    "Orbitz": "logos/OWW_logo.png",
    "Travelocity": "logos/Travelocity_logo.png",
    "EaseMyTrip": "logos/EASEMYTRIP_logo.png",
    "Wego":  "logos/Wego_logo.png",
    "Skyscanner":  "logos/Skyscanner_logo.png",
    "Etraveli":  "logos/Etraveli_logo.png",
    "Kiwi":  "logos/Kiwi_logo.png",
    "Cleartrip": "logos/Cleartrip_logo.png",
    "Traveloka": "logos/Traveloka_logo.png",
    "FLT": "logos/FlightCentre_logo.png",
    "Almosafer": "logos/Almosafer_logo.png",
    "Webjet OTA": "logos/OTA_logo.png",

    // Add other company logos here...
};

// Raw color dictionary with potential leading/trailing spaces
const color_dict_raw = {
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
    'Webjet': '#e74c3c',
    'SEERA': '#750808',
    'PCLN': '#003480',
    'Orbitz': '#8edbfa',
    'Travelocity': '#1d3e5c',
    'Skyscanner': '#0770e3',
    'Etraveli': '#b2e9ff',
    'Kiwi': '#e5fdd4',
    'Cleartrip': '#e74c3c',
    'Traveloka': '#38a0e2',
    'FLT': '#d2b6a8',
    'Almosafer': '#ba0d86',
    'Webjet OTA': '#e74c3c',
    
};

// Mapping of company symbols to full names
const companyNames = {
    "ABNB": "Airbnb",
    "BKNG": "Booking.com",
    "EXPE": "Expedia",
    "TCOM": "Trip.com",
    "TRIP": "TripAdvisor",
    "TRVG": "Trivago",
    "EDR": "Edreams",
    "DESP": "Despegar",
    "MMYT": "MakeMyTrip",
    "Ixigo": "Ixigo",
    "SEERA": "Seera Group",
    "Webjet": "Webjet",
    "LMN": "Lastminute",
    "Yatra": "Yatra.com",
    "Orbitz": "Orbitz",
    "Travelocity": "Travelocity",
    "EaseMyTrip": "EaseMyTrip",
    "Wego": "Wego",
    "Skyscanner": "Skyscanner",
    "Etraveli": "Etraveli",
    "Kiwi": "Kiwi",
    "Cleartrip": "Cleartrip",
    "FLT": "Flight Centre",
    "Almosafer": "Almosafer",

    // Add more mappings as needed...
};

// Global variables
let maxRevenueValue = 10000; // Initialize with a default value
let isPlaying = false;
let playInterval;
let currentQuarterIndex = 0;
let uniqueQuarters;
let mergedData;
let timelineTriangle;
let xScaleTimeline;
let timelineHeight = 80;
let selectedCompanies = defaultSelectedCompanies.slice(); // Initialize with default companies

// Function to clean the color dictionary by trimming keys
function cleanColorDict(rawDict) {
    const cleanedDict = {};
    for (const [key, value] of Object.entries(rawDict)) {
        const cleanKey = key.trim();
        cleanedDict[cleanKey] = value;
    }
    return cleanedDict;
}

// Cleaned color dictionary without leading/trailing spaces
const color_dict = cleanColorDict(color_dict_raw);

// Function to parse CSV data into a usable array of objects
function processData(csvText) {
    console.log('Starting to process CSV data');
    const rows = csvText.split('\n').map(row => 
        row.split(',').map(cell => {
            // Remove quotes and trim whitespace
            const cleaned = cell.trim().replace(/^["']|["']$/g, '');
            // Try to convert to number if possible
            const num = parseFloat(cleaned);
            return isNaN(num) ? cleaned : num;
        })
    );

    // Find EBITDA row
    const ebitdaStartIndex = rows.findIndex(row => 
        row[0] && String(row[0]).toLowerCase().includes('ebitda margin')
    );

    if (ebitdaStartIndex === -1) {
        throw new Error('EBITDA Margin row not found');
    }

    // Get headers (company names)
    const headers = rows[0].slice(1).map(h => h ? h.trim() : null).filter(Boolean);
    console.log('Processed headers:', headers);

    // Process data rows
    const processedData = [];
    const quarters = new Set();
    let maxRevenue = 0;
    
    // Process rows between headers and EBITDA row
    let currentYear = null;
    let quarterCount = 0;

    for (let i = 1; i < ebitdaStartIndex; i++) {
        const row = rows[i];
        
        if (!row || !row[0]) {
            console.log(`Skipping row ${i}: Empty row`);
            continue;
        }
        
        // Get year from first column
        const year = String(row[0]).trim();
        if (!year || year === 'Revenue Growth YoY') {
            console.log(`Skipping row ${i}: Invalid year or header row`);
            continue;
        }
        
        // Reset quarter count when year changes
        if (year !== currentYear) {
            currentYear = year;
            quarterCount = 1;
        } else {
            quarterCount++;
        }
        
        // Get corresponding EBITDA row
        const ebitdaRow = rows[ebitdaStartIndex + (i - 1)];
        if (!ebitdaRow) {
            console.log(`Skipping row ${i}: No corresponding EBITDA row`);
            continue;
        }
        
        const quarter = `${year}'Q${quarterCount}`;
        
        // Process each company's data
        headers.forEach((company, j) => {
            const colIndex = j + 1;
            let revenueGrowth = parseFloat(row[colIndex]);
            let ebitdaMargin = parseFloat(ebitdaRow[colIndex]);
            
            if (!isNaN(revenueGrowth) && !isNaN(ebitdaMargin)) {
                // Convert to percentage if the values are in decimal format
                revenueGrowth = revenueGrowth <= 1 && revenueGrowth >= -1 ? revenueGrowth * 100 : revenueGrowth;
                ebitdaMargin = ebitdaMargin <= 1 && ebitdaMargin >= -1 ? ebitdaMargin * 100 : ebitdaMargin;
                
                // Use a scaled revenue value for bubble size
                const revenue = 1000 + Math.abs(revenueGrowth * 50); // Adjusted scaling factor
                maxRevenue = Math.max(maxRevenue, revenue);

                processedData.push({
                quarter,
                    company,
                    revenueGrowth: revenueGrowth,
                    ebitdaMargin: ebitdaMargin,
                    revenue: revenue
                });
                quarters.add(quarter);
            }
        });
    }

    // Update global maxRevenueValue
    maxRevenueValue = maxRevenue;

    console.log('Final processed data:', {
        totalQuarters: quarters.size,
        quarters: Array.from(quarters).sort(),
        totalDataPoints: processedData.length,
        sampleData: processedData.slice(0, 5),
        maxRevenue: maxRevenue
    });

    return processedData;
}

// Function to initialize company filters
function initializeCompanyFilters(data) {
    const companies = [...new Set(data.map(d => d.company))].sort();
    const filterContainer = d3.select("#company-filters");

    // Clear any existing filters
    filterContainer.html('');

    companies.forEach(companySymbol => {
        const id = `filter-${companySymbol}`;
        const companyName = companyNames[companySymbol] || companySymbol;

        const label = filterContainer.append("label")
            .attr("for", id)
            .style("display", "flex")
            .style("align-items", "center")
            .style("margin-bottom", "5px");

        const input = label.append("input")
            .attr("type", "checkbox")
            .attr("id", id)
            .attr("value", companySymbol)
            .property("checked", selectedCompanies.includes(companySymbol))
            .on("change", handleFilterChange);

        label.append("span")
            .html(`${companySymbol} - ${companyName}`);
    });
}

// Function to handle filter changes
function handleFilterChange() {
    const checkedBoxes = d3.selectAll("#company-filters input[type='checkbox']")
        .nodes()
        .filter(d => d.checked)
        .map(d => d.value);

    selectedCompanies = checkedBoxes;

    if (selectedCompanies.length === 0) {
        console.warn("No companies selected. Charts will be empty.");
    }

    const selectedQuarter = uniqueQuarters[currentQuarterIndex];
    updateBubbleChart(selectedQuarter, mergedData);
    updateBarChart(selectedQuarter, mergedData);
    updateLineCharts(mergedData);
}

// Function to fetch and process data from Google Sheet
async function importFromGoogleSheet() {
    const sheetUrl = `https://docs.google.com/spreadsheets/d/e/${sheetId}/pub?output=csv`;
    
    try {
        console.log('Starting Google Sheet import...');
        console.log('Using sheet URL:', sheetUrl);
        const response = await fetch(sheetUrl, {
            mode: 'cors',
            headers: {
                'Accept': 'text/csv'
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to fetch data from Google Sheet');
        }
        
        const csvText = await response.text();
        console.log('Received CSV response length:', csvText.length);
        
        // Process the data
        mergedData = processData(csvText);
        
        // Initialize the visualization
        initializeVisualization(mergedData);
        
    } catch (error) {
        console.error('Error importing from Google Sheet:', error);
        console.error('Error stack:', error.stack);
        alert('Failed to import data: ' + error.message);
    }
}

// Function to initialize the visualization
function initializeVisualization(data) {
    // Sort quarters chronologically
    uniqueQuarters = [...new Set(data.map(d => d.quarter))].sort((a, b) => {
        // Parse YYYY'QN format
        const [yearA, quarterA] = a.split("'");
        const [yearB, quarterB] = b.split("'");
        
        // Compare years first
        const yearDiff = parseInt(yearA) - parseInt(yearB);
        if (yearDiff !== 0) return yearDiff;
        
        // If years are same, compare quarters (Q1, Q2, Q3, Q4)
        return parseInt(quarterA.substring(1)) - parseInt(quarterB.substring(1));
    });

    currentQuarterIndex = uniqueQuarters.length - 1;

    // Extract unique years and find Q1 indices
    let uniqueYears = [...new Set(uniqueQuarters.map(q => {
        const parts = q.split("'");
        return parts[0] || "";
    }))].filter(year => year !== "");

    // Add 2025 if it's not already included
    if (!uniqueYears.includes("2025")) {
        uniqueYears.push("2025");
    }

    const yearIndices = uniqueQuarters.reduce((acc, q, i) => {
        if (q.includes("Q1")) acc.push(i);
        return acc;
    }, []);

    // Add index for 2025 if it's not already included
    if (!yearIndices.includes(uniqueQuarters.length)) {
        yearIndices.push(uniqueQuarters.length);
    }

    // Initialize company filters
    initializeCompanyFilters(data);

    // Create timeline
    createTimeline(uniqueQuarters, data, yearIndices, uniqueYears);

    // Update initial charts
    updateBubbleChart(uniqueQuarters[currentQuarterIndex], data);
    updateBarChart(uniqueQuarters[currentQuarterIndex], data);
    updateLineCharts(data);
}

// Auto import data when page loads
document.addEventListener('DOMContentLoaded', async () => {
    try {
        await importFromGoogleSheet();
    } catch (error) {
        console.error('Failed to load initial data:', error);
    }
});

// Function to create the interactive timeline using D3.js
function createTimeline(quarters, data, yearIndices, uniqueYears) {
    const timelineWidth = document.getElementById('timeline').offsetWidth;
    const margin = { left: 80, right: 80 };
    const width = timelineWidth - margin.left - margin.right;
    const height = 60;
    
    // Clear any existing timeline
    d3.select("#timeline svg").remove();
    
    const svg = d3.select("#timeline")
        .append('svg')
        .attr('width', timelineWidth)
        .attr('height', height);
    
    const g = svg.append('g')
        .attr('transform', `translate(${margin.left}, 30)`);
    
    // Create scale with extended domain to include 2025
    xScaleTimeline = d3.scaleLinear()
        .domain([0, quarters.length])  // Extended by 1 to include 2025
        .range([0, width]);
    
    // Define tick values for every quarter plus 2025
    const allTickValues = d3.range(0, quarters.length + 1);  // Added +1 to include 2025
    
    // Define the tick format to show year labels only for Q1 and 2025
    const axisBottom = d3.axisBottom(xScaleTimeline)
        .tickValues(allTickValues)
        .tickFormat((d, i) => {
            if (i === quarters.length) {
                return '2025';
            }
            if (yearIndices.includes(i)) {
                const yearIndex = yearIndices.indexOf(i);
                return uniqueYears[yearIndex] || '';
            }
            return '';
        });
    
    // Append the x-axis to the SVG
    g.append("g")
        .attr("class", "timeline-axis")
        .call(axisBottom)
        .selectAll("text")
        .style("text-anchor", "middle")
        .style("font-family", "Monda")
        .style("font-size", "12px");
    
    // Style the axis lines
    g.selectAll(".timeline-axis path, .timeline-axis line")
        .style("stroke", "#ccc")
        .style("stroke-width", "1px");
    
    // Differentiate tick lengths
    g.selectAll(".timeline-axis .tick line")
        .attr("y2", d => yearIndices.includes(d) || d === quarters.length ? 8 : 4)
        .attr("stroke", "#ccc");
    
    // Create the triangle indicator
    timelineTriangle = g.append("path")
        .attr("d", d3.symbol().type(d3.symbolTriangle).size(100))
        .attr("fill", "#4CAF50")
        .attr("transform", `translate(${xScaleTimeline(currentQuarterIndex)}, -10) rotate(180)`);

    // Make the timeline responsive
    window.addEventListener('resize', () => {
        const newWidth = document.getElementById('timeline').offsetWidth;
        const width = newWidth - margin.left - margin.right;
        svg.attr("width", newWidth);
        xScaleTimeline.range([0, width]);
        g.select(".timeline-axis")
            .call(axisBottom.scale(xScaleTimeline));

        const newX = xScaleTimeline(currentQuarterIndex);
        timelineTriangle
            .attr("transform", `translate(${newX}, -10) rotate(180)`);
    });
}

// Function to update the timeline triangle position
function updateTimelineTriangle(index) {
    if (!timelineTriangle) return;
    
    const timelineWidth = document.getElementById('timeline').offsetWidth;
    const margin = { left: 80, right: 80 };
    const width = timelineWidth - margin.left - margin.right;
    xScaleTimeline.range([0, width]);
    
    const x = xScaleTimeline(index);
    timelineTriangle
        .transition()
        .duration(300)
        .ease(d3.easeCubicInOut)
        .attr("transform", `translate(${x}, -10) rotate(180)`);
}

// Function to update the bubble chart
function updateBubbleChart(quarter, sheetData) {
    // Filter data for the selected quarter and selected companies
    const quarterData = sheetData.filter(d => d.quarter === quarter && selectedCompanies.includes(d.company));
    if (quarterData.length === 0) {
        Plotly.react('bubble-chart', [], { title: `No data available for ${quarter}` });
        return;
    }

    // Prepare the bubble data
    const bubbleData = [{
        x: quarterData.map(d => d.ebitdaMargin),
        y: quarterData.map(d => d.revenueGrowth),
        text: quarterData.map(d => d.company),
        mode: 'markers',
        marker: {
            size: quarterData.map(d => Math.sqrt(Math.abs(d.revenue))),
            color: quarterData.map(d => color_dict[d.company] || 'gray'),
            sizemode: 'area',
            sizeref: 2.0 * Math.max(...quarterData.map(d => Math.sqrt(Math.abs(d.revenue)))) / (20**2),
            sizemin: 4
        },
        customdata: quarterData.map(d => d.company),
        hoverinfo: 'text+x+y+marker.size',
        hovertext: quarterData.map(d => `${d.company}<br>Revenue Growth: ${d.revenueGrowth.toFixed(1)}%<br>EBITDA Margin: ${d.ebitdaMargin.toFixed(1)}%<br>Revenue: $${d3.format(",")(d.revenue)}M`)
    }];

    // Prepare images for each company
    const images = quarterData.map(d => {
        const logoPath = companyLogos[d.company];
        if (!logoPath) return null; // Skip if no logo defined
        return {
            source: logoPath,
            xref: 'x',
            yref: 'y',
            x: d.ebitdaMargin,
            y: d.revenueGrowth + 5,
            sizex: 10,
            sizey: 10,
            xanchor: 'center',
            yanchor: 'bottom',
            layer: 'above',
            sizing: 'contain',
            opacity: 1
        };
    }).filter(img => img !== null);

    // Define the layout with images
    const layout = {
        title: `Revenue Growth vs EBITDA Margin for ${quarter}`,
        xaxis: { 
            title: 'EBITDA Margin (%)', 
            range: [-60, 60], 
            gridcolor: '#eee',
            zeroline: true,
            zerolinecolor: '#4e843d',
            zerolinewidth: 1
        },
        yaxis: { 
            title: 'Revenue Growth YoY (%)', 
            range: [-40, 110], 
            gridcolor: '#eee',
            zeroline: true,
            zerolinecolor: '#4e843d',
            zerolinewidth: 1
        },
        margin: { t: 60, l: 80, r: 80, b: 80 },
        images: images,
        showlegend: false,
        hovermode: 'closest',
        plot_bgcolor: 'white',
        paper_bgcolor: 'white',
        annotations: [
            {
                xref: 'paper',
                yref: 'paper',
                x: -0.1,
                y: -0.18,
                xanchor: 'left',
                yanchor: 'bottom',
                text: "Note: Values are shown in percentages.",
                showarrow: false,
                font: {
                    size: 12,
                    color: 'gray'
                }
            }
        ]
    };

    // Animation configuration
    const animation = {
        transition: {
            duration: 500,
            easing: 'cubic-in-out'
        },
        frame: {
            duration: 500,
            redraw: true
        }
    };

    // Check if the chart already exists
    const chartDiv = document.getElementById('bubble-chart');
    if (chartDiv.data && chartDiv.data.length > 0) {
        // Update existing chart with animation
        Plotly.animate('bubble-chart', {
            data: bubbleData,
            layout: layout
        }, animation);
    } else {
        // Initial render without animation
    Plotly.react('bubble-chart', bubbleData, layout, {responsive: true});
    }
}

function updateBarChart(quarter, sheetData) {
    const margin = { 
        l: 120,  // 左边距用于公司名称
        r: 120,  // 右边距用于数值标签
        t: 40,
        b: 50,
        autoexpand: false
    };
    const width = 450;
    const height = 400;

    // Filter and sort data in ascending order
    const quarterData = sheetData
        .filter(d => d.quarter === quarter && selectedCompanies.includes(d.company))
        .sort((a, b) => b.revenue - a.revenue)  // 保持升序排列
        .slice(0, 15);

    if (quarterData.length === 0) {
        Plotly.purge('bar-chart');
        return;
    }

    // Prepare the bar chart data
    const barData = {
        type: 'bar',
        x: quarterData.map(d => d.revenue),
        y: quarterData.map(d => d.company),
        orientation: 'h',
        marker: {
            color: quarterData.map(d => color_dict[d.company] || '#999999')
        },
        text: quarterData.map(d => d3.format("$,.1f")(d.revenue) + "M"),
        textposition: 'outside',
        hoverinfo: 'text',
        textfont: {
            family: 'Monda',
            size: 11,
            color: '#333'
        },
        cliponaxis: false,
        textangle: 0,
        offsetgroup: 1,
        width: 0.6,  // 条形宽度
        constraintext: 'none'
    };

    // Create layout
    const layout = {
        width: width,
        height: height,
        xaxis: {
            title: {
                text: 'Revenue (USD M)',
                font: {
                    family: 'Monda',
                    size: 12
                },
                standoff: 20
            },
            showgrid: true,
            gridcolor: '#eee',
            gridwidth: 1,
            zeroline: true,
            zerolinecolor: '#eee',
            tickfont: {
                family: 'Monda',
                size: 11
            },
            range: [0, maxRevenueValue * 1.3],
            fixedrange: true,
            ticklen: 6,
            ticksuffix: '   ',
            automargin: true
        },
        yaxis: {
            showgrid: false,
            tickfont: {
                family: 'Monda',
                size: 11
            },
            fixedrange: true,
            ticklabelposition: 'outside left',  // 将标签放在左侧
            automargin: true,
            range: [14.5, -0.5],  // 反转y轴范围，使较大的值显示在顶部
            dtick: 1,
            side: 'left',  // 确保标签在左侧
            autorange: false  // 禁用自动范围以保持顺序
        },
        margin: margin,
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        showlegend: false,
        barmode: 'group',
        bargap: 0.15,  // 调整条形间距
        bargroupgap: 0.1,
        font: {
            family: 'Monda'
        },
        uniformtext: {
            mode: 'show',
            minsize: 10
        }
    };

    // Configuration
    const config = {
        displayModeBar: false,
        responsive: true,
        staticPlot: false
    };

    // Check if the chart exists
    const chartDiv = document.getElementById('bar-chart');
    if (chartDiv.data && chartDiv.data.length > 0) {
        // Update with animation
        Plotly.animate('bar-chart', {
            data: [barData],
            layout: layout
        }, {
            transition: {
                duration: 500,
                easing: 'cubic-in-out'
            },
            frame: {
                duration: 500,
                redraw: true
            }
        });
    } else {
        // Initial render
        Plotly.newPlot('bar-chart', [barData], layout, config);
    }
}

function updateLineCharts(mergedData) {
    // Prepare the data for the line charts
    const quarters = [...new Set(mergedData.map(d => d.quarter))];

    // Sort the quarters in chronological order
    quarters.sort((a, b) => {
        try {
            const [aYear, aQ] = a.split("'");
            const [bYear, bQ] = b.split("'");
            const aQuarter = parseInt(aQ.substring(1));
            const bQuarter = parseInt(bQ.substring(1));
            return (parseInt(aYear) - parseInt(bYear)) || (aQuarter - bQuarter);
        } catch (error) {
            console.warn('Error parsing quarter:', error);
            return 0;
        }
    });
    
    // For each selected company, create traces for each metric
    const ebitdaMarginTraces = [];
    const revenueGrowthTraces = [];
    const revenueTraces = [];
    
    selectedCompanies.forEach(company => {
        const companyData = mergedData.filter(d => d.company === company);
        
        // Ensure data is sorted by quarter
        companyData.sort((a, b) => quarters.indexOf(a.quarter) - quarters.indexOf(b.quarter));
        
        // Get x (quarters) and y (values)
        const x = companyData.map(d => d.quarter);
        const yEbitdaMargin = companyData.map(d => d.ebitdaMargin * 100); // Convert to percentage
        const yRevenueGrowth = companyData.map(d => d.revenueGrowth * 100); // Convert to percentage
        const yRevenue = companyData.map(d => d.revenue);
        
        // Create traces for EBITDA Margin
        ebitdaMarginTraces.push({
            x: x,
            y: yEbitdaMargin,
            mode: 'lines+markers',
            name: company,
            line: { color: color_dict[company] || 'gray' },
            hovertemplate: `%{x}<br>${company}<br>EBITDA Margin: %{y:.1f}%<extra></extra>`
        });
        
        // Create traces for Revenue Growth
        revenueGrowthTraces.push({
            x: x,
            y: yRevenueGrowth,
            mode: 'lines+markers',
            name: company,
            line: { color: color_dict[company] || 'gray' },
            hovertemplate: `%{x}<br>${company}<br>Revenue Growth: %{y:.1f}%<extra></extra>`
        });
        
        // Create traces for Revenue
        revenueTraces.push({
            x: x,
            y: yRevenue,
            mode: 'lines+markers',
            name: company,
            line: { color: color_dict[company] || 'gray' },
            hovertemplate: `%{x}<br>${company}<br>Revenue: $%{y:,.0f}M<extra></extra>`
        });
    });
    
    // Define layouts for each chart
    const layoutEbitdaMargin = {
        title: 'EBITDA Margin Over Time',
        xaxis: { 
            title: 'Quarter', 
            tickangle: -45,
            categoryorder: 'array',
            categoryarray: quarters
        },
        yaxis: { 
            title: 'EBITDA Margin (%)',
            range: [-60, 60],
            zeroline: true,
            zerolinecolor: '#4e843d',
            zerolinewidth: 1
        },
        hovermode: 'x unified',
        margin: { t: 50, l: 80, r: 50, b: 100 },
        plot_bgcolor: 'white',
        paper_bgcolor: 'white'
    };
    
    const layoutRevenueGrowth = {
        title: 'Revenue Growth Over Time',
        xaxis: { 
            title: 'Quarter', 
            tickangle: -45,
            categoryorder: 'array',
            categoryarray: quarters
        },
        yaxis: { 
            title: 'Revenue Growth YoY (%)',
            range: [-40, 110],
            zeroline: true,
            zerolinecolor: '#4e843d',
            zerolinewidth: 1
        },
        hovermode: 'x unified',
        margin: { t: 50, l: 80, r: 50, b: 100 },
        plot_bgcolor: 'white',
        paper_bgcolor: 'white'
    };
    
    const layoutRevenue = {
        title: 'Revenue Over Time',
        xaxis: { 
            title: 'Quarter', 
            tickangle: -45,
            categoryorder: 'array',
            categoryarray: quarters
        },
        yaxis: { 
            title: 'Revenue (in Millions)',
            zeroline: true,
            zerolinecolor: '#4e843d',
            zerolinewidth: 1
        },
        hovermode: 'x unified',
        margin: { t: 50, l: 80, r: 50, b: 100 },
        plot_bgcolor: 'white',
        paper_bgcolor: 'white'
    };
    
    // Plot the charts using Plotly
    try {
    Plotly.react('line-chart-ebitda-margin', ebitdaMarginTraces, layoutEbitdaMargin, { responsive: true });
    Plotly.react('line-chart-revenue-growth', revenueGrowthTraces, layoutRevenueGrowth, { responsive: true });
    Plotly.react('line-chart-revenue', revenueTraces, layoutRevenue, { responsive: true });
    } catch (error) {
        console.error('Error updating line charts:', error);
}
}

// Function to handle the Play/Pause button
function handlePlayPause() {
    const playButton = document.getElementById('play-button');
    const playIcon = playButton.querySelector('i');
    if (isPlaying) {
        // Pause the auto-play
        clearInterval(playInterval);
        playButton.textContent = '';
        playButton.appendChild(playIcon);
        playButton.appendChild(document.createTextNode(' Play'));
        isPlaying = false;
    } else {
        // Start the auto-play
        playButton.textContent = '';
        playButton.appendChild(playIcon);
        playButton.appendChild(document.createTextNode(' Pause'));
        isPlaying = true;
        playInterval = setInterval(() => {
            currentQuarterIndex = (currentQuarterIndex + 1) % uniqueQuarters.length;
            const selectedQuarter = uniqueQuarters[currentQuarterIndex];
            
            // Update the position of the triangle on the timeline
            updateTimelineTriangle(currentQuarterIndex);
            
            // Update the bubble and bar charts based on selected companies
            updateBubbleChart(selectedQuarter, mergedData);
            updateBarChart(selectedQuarter, mergedData);
        }, 500); // Adjusted interval to accommodate transition durations
    }
}

// Tooltip Functions
const tooltip = d3.select("#chart-tooltip");

function showTooltip(event, content) {
    tooltip
        .html(content)
        .style("left", (event.pageX + 15) + "px")
        .style("top", (event.pageY - 28) + "px")
        .transition()
        .duration(200)
        .style("opacity", .9);
}

function moveTooltip(event) {
    tooltip
        .style("left", (event.pageX + 15) + "px")
        .style("top", (event.pageY - 28) + "px");
}

function hideTooltip() {
    tooltip
        .transition()
        .duration(500)
        .style("opacity", 0);
}

// Debounce Function to limit the rate of function execution
function debounce(func, delay) {
    let timeout;
    return function(...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), delay);
    };
}

// Enhanced Search Functionality with Debounce and Highlighting
d3.select("#search-input").on("input", debounce(function() {
    const searchTerm = this.value.trim().toLowerCase();

    d3.selectAll("#company-filters label")
        .style("display", function() {
            const companySymbol = d3.select(this).select("input").attr("value");
            const companyName = companyNames[companySymbol] || companySymbol;

            // Check if either symbol or name includes the search term
            const symbolMatch = companySymbol.toLowerCase().includes(searchTerm);
            const nameMatch = companyName.toLowerCase().includes(searchTerm);

            if (symbolMatch || nameMatch) {
                // Highlight matching parts
                let displayText = `${companySymbol} - ${companyName}`;

                if (searchTerm !== "") {
                    const regex = new RegExp(`(${searchTerm})`, 'gi');
                    displayText = displayText.replace(regex, '<span class="highlight">$1</span>');
                }

                d3.select(this).select("span").html(displayText);
                return "flex";
            } else {
                // Remove any existing highlights and hide the label
                d3.select(this).select("span").html(`${companySymbol} - ${companyName}`);
                return "none";
            }
        });
}, 300)); // 300ms delay

// Select All and Deselect All Button Functions
d3.select("#select-all").on("click", () => {
    d3.selectAll("#company-filters input[type='checkbox']")
        .property("checked", true)
        .each(function() {
            const company = this.value;
            if (!selectedCompanies.includes(company)) {
                selectedCompanies.push(company);
            }
        });
    updateBubbleChart(uniqueQuarters[currentQuarterIndex], mergedData);
    updateBarChart(uniqueQuarters[currentQuarterIndex], mergedData);
    updateLineCharts(mergedData); // Update line charts
});

d3.select("#deselect-all").on("click", () => {
    d3.selectAll("#company-filters input[type='checkbox']")
        .property("checked", false);
    selectedCompanies = [];
    updateBubbleChart(uniqueQuarters[currentQuarterIndex], mergedData);
    updateBarChart(uniqueQuarters[currentQuarterIndex], mergedData);
    updateLineCharts(mergedData); // Update line charts
});

// Initialize Tooltip for Play Button
const playTooltip = d3.select("#play-tooltip");

d3.select("#play-button")
    .on("mouseover", function(event) {
        playTooltip
            .style("opacity", 1)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 10) + "px")
            .text(isPlaying ? "Click to Pause" : "Click to Play");
    })
    .on("mousemove", function(event) {
        playTooltip
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 10) + "px");
    })
    .on("mouseout", function() {
        playTooltip
            .style("opacity", 0);
    });

// Event listener for the Play/Pause button
document.getElementById('play-button').addEventListener('click', handlePlayPause);