// Global variables
let isPlaying = true;
let playInterval;
let currentYearIndex = 0;
let years;
let processedData;
let timeline;
let selectedCompanies = appConfig.defaultSelectedCompanies;
let backgroundTrace;
let currentTraces;
let layout;
let config;

// Create layout configuration
layout = {
    xaxis: {
        title: {
            text: 'Share of Online Bookings (%)',
            font: {
                family: 'Monda',
                size: 22
            },
            standoff: 15
        },
        tickformat: ',.0%',
        range: [-0.05, 1.05],
        showgrid: true,
        gridcolor: '#eee',
        gridwidth: 1,
        zeroline: true,
        zerolinecolor: '#eee',
        showline: true,
        linecolor: '#ccc',
        linewidth: 1,
        tickfont: {
            family: 'Monda',
            size: 20
        },
        tickmode: 'array',
        ticktext: ['0%', '20%', '40%', '60%', '80%', '100%'],
        tickvals: [0, 0.2, 0.4, 0.6, 0.8, 1.0],
        fixedrange: true,
        ticks: 'outside',
        ticklen: 8,
        tickwidth: 1,
        tickcolor: '#ccc'
    },
    yaxis: {
        title: {
            text: 'Online Bookings (USD bn)',
            font: {
                family: 'Monda',
                size: 22
            },
            standoff: 15
        },
        type: 'log',
        showgrid: true,
        gridcolor: '#eee',
        gridwidth: 1,
        zeroline: true,
        zerolinecolor: '#eee',
        showline: true,
        linecolor: '#ccc',
        linewidth: 1,
        tickfont: {
            family: 'Monda',
            size: 20
        },
        tickmode: 'array',
        ticktext: ['0', '10', '40', '90', '160', '250', '400', '600', '800'],
        tickvals: [0, 10, 40, 90, 160, 250, 400, 600, 800],
        range: [0, Math.log10(900)],
        autorange: false,
        fixedrange: true,
        ticks: 'outside',
        ticklen: 8,
        tickwidth: 1,
        tickcolor: '#ccc'
    },
    showlegend: false,
    margin: {
        l: 80,
        r: 20,
        t: 100,
        b: 150
    },
    height: 650,
    
    hovermode: 'closest',
    hoverlabel: {
        bgcolor: 'white',
        font: { 
            family: 'Monda',
            size: 12
        },
        bordercolor: '#666'
    },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    autosize: true
};

// Create config
config = {
    responsive: true,
    displayModeBar: false,
    staticPlot: false
};

// Add getEraText function at the top level
function getEraText(year) {
    const yearNum = parseInt(year);
    if (yearNum >= 2005 && yearNum <= 2007) {
        return "Growth of WWW";
    } else if (yearNum >= 2007 && yearNum <= 2008) {
        return "Great Recession";
    } else if (yearNum >= 2009 && yearNum <= 2018) {
        return "Growth of Mobile";
    } else if (yearNum >= 2019 && yearNum <= 2020) {
        return "Global Pandemic";
    } else if (yearNum >= 2021) {
        return "Post-Pandemic Recovery";
    }
    return "";
}

// Function to create timeline
function createTimeline() {
    const timelineWidth = document.getElementById('timeline').offsetWidth;
    const margin = { left: 80, right: 80 };
    const width = timelineWidth - margin.left - margin.right;

    // Create SVG
    const svg = d3.select('#timeline')
        .append('svg')
        .attr('width', timelineWidth)
        .attr('height', 60);

    const g = svg.append('g')
        .attr('transform', `translate(${margin.left}, 30)`);

    // Create scale
    const xScale = d3.scaleLinear()
        .domain([d3.min(years), d3.max(years)])
        .range([0, width]);

    // Create axis
    const xAxis = d3.axisBottom(xScale)
        .tickFormat(d => d.toString())
        .ticks(years.length)
        .tickValues(years);

    // Add axis
    g.append('g')
        .attr('class', 'timeline-axis')
        .call(xAxis)
        .selectAll('text')
        .style('text-anchor', 'middle')
        .style('font-family', 'Monda')
        .style('font-size', '18px');

    // Make timeline ticks more visible
    g.selectAll('.tick line')
        .style('stroke', '#ccc')
        .style('stroke-width', '1px')
        .attr('y2', '8');

    // Add triangle marker
    const triangle = g.append('path')
        .attr('d', d3.symbol().type(d3.symbolTriangle).size(100))
        .attr('fill', '#4CAF50')
        .attr('transform', `translate(${xScale(years[currentYearIndex])}, -10) rotate(180)`);

    timeline = {
        scale: xScale,
        triangle: triangle
    };
}

// Function to update timeline
function updateTimeline(year) {
    if (timeline && timeline.triangle) {
        timeline.triangle
            .transition()
            .duration(appConfig.animation.duration)
            .attr('transform', `translate(${timeline.scale(year)}, -10) rotate(180)`);
    }
}

// Function to process Excel data
async function fetchData() {
    try {
        const response = await fetch('travel_market_summary.xlsx');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const arrayBuffer = await response.arrayBuffer();
        const data = new Uint8Array(arrayBuffer);
        
        const workbook = XLSX.read(data, { type: 'array' });
        const sheet = workbook.Sheets['Visualization Data'];
        if (!sheet) {
            throw new Error("Sheet 'Visualization Data' not found");
        }
        
        const jsonData = XLSX.utils.sheet_to_json(sheet);

        // Process data
        const processedData = jsonData
            .filter(row => row['Region'] === 'APAC' && row['Market'] && row['Year'])
            .filter(row => {
                // Filter out Taiwan, Hong Kong, and Macau
                const market = row['Market'];
                return market !== 'Taiwan' && market !== 'Hong Kong' && market !== 'Macau';
            })
            .map(row => {
                // 标准化市场名称
                let market = row['Market'];
                if (market === 'Australia-New Zealand' || market === 'Australia/New Zealand') {
                    market = 'Australia & New Zealand';
                }
                return {
                    Market: market,
                    Year: row['Year'],
                    OnlinePenetration: row['Online Penetration'] / 100,
                    OnlineBookings: row['Online Bookings'],
                    GrossBookings: row['Gross Bookings']
                };
            });

        // 获取所有年份和市场
        const allYears = [...new Set(processedData.map(d => d.Year))].sort();
        const allMarkets = [...new Set(processedData.map(d => d.Market))];

        // 处理缺失数据
        const interpolatedData = [];
        allMarkets.forEach(market => {
            const marketData = processedData.filter(d => d.Market === market);
            const marketYears = marketData.map(d => d.Year);

            allYears.forEach(year => {
                if (!marketYears.includes(year)) {
                    // 找到最近的前后年份数据
                    const prevYear = Math.max(...marketYears.filter(y => y < year));
                    const nextYear = Math.min(...marketYears.filter(y => y > year));
                    
                    if (prevYear && nextYear) {
                        const prevData = marketData.find(d => d.Year === prevYear);
                        const nextData = marketData.find(d => d.Year === nextYear);
                        
                        // 线性插值
                        const progress = (year - prevYear) / (nextYear - prevYear);
                        const interpolated = {
                            Market: market,
                            Year: year,
                            OnlinePenetration: prevData.OnlinePenetration + (nextData.OnlinePenetration - prevData.OnlinePenetration) * progress,
                            OnlineBookings: prevData.OnlineBookings + (nextData.OnlineBookings - prevData.OnlineBookings) * progress,
                            GrossBookings: prevData.GrossBookings + (nextData.GrossBookings - prevData.GrossBookings) * progress
                        };
                        interpolatedData.push(interpolated);
                    }
                }
            });
        });

        // 合并原始数据和插值数据
        const finalData = [...processedData, ...interpolatedData].sort((a, b) => {
            if (a.Year === b.Year) {
                return a.Market.localeCompare(b.Market);
            }
            return a.Year - b.Year;
        });

        return finalData;
    } catch (error) {
        console.error('Error loading data:', error);
        return [];
    }
}

// Function to create bubble chart
function createBubbleChart(data, year) {
    const yearData = data.filter(d => d.Year === year && selectedCompanies.includes(d.Market));
    
    // 只在2005年输出原始数据和计算后的值
    if (year === 2005) {
        yearData.forEach(d => {
            const rawValue = d.OnlineBookings;
            const scaledValue = rawValue / 1e9; // 直接转换为十亿
            console.log(`${d.Market}:`);
            console.log(`  Raw: ${rawValue}`);
            console.log(`  Scaled (bn): ${scaledValue}`);
            console.log('-------------------');
        });
    }

    // 输出中国的数据
    const chinaData = yearData.find(d => d.Market === 'China');
    if (chinaData) {
        const rawValue = chinaData.OnlineBookings;
        const scaledValue = rawValue / 1e9; // 转换为十亿
        const safeValue = Math.max(scaledValue, 0.1);
        const logValue = Math.log10(safeValue);
        console.log(`Year ${year} China:`);
        console.log(`  Raw Online Bookings: ${rawValue.toLocaleString()}`);
        console.log(`  Billions: ${scaledValue.toFixed(2)}B`);
        console.log(`  Log Value: ${logValue.toFixed(2)}`);
        console.log('-------------------');
    }

    // Create background text trace
    backgroundTrace = {
        x: [0.5],
        y: [30],  // Adjust y position to better center the text vertically
        mode: 'text',
        text: [getEraText(year)],
        textposition: 'middle center',
        textfont: {
            size: 60,
            family: 'Monda, Arial',
            color: 'rgba(200,200,200,0.3)'
        },
        hoverinfo: 'skip',
        showlegend: false
    };

    // Create base scatter plot with invisible markers
    const trace = {
        x: yearData.map(d => d.OnlinePenetration),
        y: yearData.map(d => {
            const rawValue = d.OnlineBookings / 1e9;
            const safeValue = Math.max(rawValue, 0.1);
            return Math.log10(safeValue);
        }),
        mode: 'none',  // 完全移除所有可视元素
        showlegend: false,
        hoverinfo: 'none',
        visible: true,
        customdata: yearData.map(d => [
            d.GrossBookings / 1e9,
            d.OnlineBookings / 1e9
        ]),
        hovertemplate: '<b>%{text}</b><br>' +
                      'Online Penetration: %{x:.1%}<br>' +
                      'Online Bookings: $%{customdata[1]:.1f}B<br>' +
                      'Gross Bookings: %{customdata[0]:$,.1f}B<br>' +
                      '<extra></extra>'
    };

    // Create images
    const images = yearData.map(d => {
        const logo = appConfig.companyLogos[d.Market];
        if (!logo) {
            console.warn('No logo found for market:', d.Market);
            return null;
        }

        const maxGrossBookings = d3.max(data, d => d.GrossBookings);
        const relativeSize = Math.pow(d.GrossBookings / maxGrossBookings, 0.6);
        const targetSize = relativeSize * 0.8 + 0.01;

        // 计算对数坐标系下的y值
        const rawValue = d.OnlineBookings / 1e9;
        const safeValue = Math.max(rawValue, 0.1);
        const yValue = Math.log10(safeValue);

        // 只在2005年输出调试信息
        if (year === 2005) {
            console.log(`${d.Market}:`);
            console.log(`  Raw Online Bookings: ${d.OnlineBookings}`);
            console.log(`  Converted to billions: ${rawValue}`);
            console.log(`  Safe value: ${safeValue}`);
            console.log(`  Final log10 y-value: ${yValue}`);
            console.log(`  Pixel position: ${layout.yaxis.range[0] + (Math.log10(safeValue) / Math.log10(1000)) * (layout.yaxis.range[1] - layout.yaxis.range[0])}`);
            console.log('-------------------');
        }

        return {
            source: logo,
            xref: "x",
            yref: "y",
            x: d.OnlinePenetration,
            y: yValue,
            sizex: targetSize,
            sizey: targetSize,
            sizing: "contain",
            opacity: 0.8,
            layer: "above",
            xanchor: "center",
            yanchor: "middle"
        };
    }).filter(Boolean);

    // Check if the chart already exists
    const chartDiv = document.getElementById('bubble-chart');
    if (!chartDiv.data) {
        console.log('Initial chart creation');
        // First time creation
        Plotly.newPlot('bubble-chart', [backgroundTrace, trace], {
            ...layout,
            images: images,
            datarevision: Date.now()
        }, {
            ...config,
            doubleClick: false,
            displayModeBar: false,
            staticPlot: false
        }).then(() => {
            Plotly.relayout('bubble-chart', { images });
        });
        // Create race chart
        createRaceChart(data, year);
    } else {
        // Update existing chart with animation
        Plotly.animate('bubble-chart', {
            data: [backgroundTrace, trace],
            layout: {
                ...layout,
                images,
                datarevision: Date.now()
            }
        }, {
            transition: {
                duration: 0,
                easing: 'linear'
            },
            frame: {
                duration: 0,
                redraw: true
            },
            mode: 'immediate'
        });
        // Update race chart
        updateRaceChart(data, year);
    }
}

// Initialize the visualization
async function init() {
    try {
        processedData = await fetchData();
        
        if (!processedData || processedData.length === 0) {
            throw new Error('No data loaded');
        }
        
        years = [...new Set(processedData.map(d => d.Year))].sort();
        currentYearIndex = years.indexOf(appConfig.chart.defaultYear);
        
        // Create timeline
        createTimeline();
        
        // Create initial chart
        createBubbleChart(processedData, years[currentYearIndex]);
        
        // Start animation
        setTimeout(() => {
            isPlaying = true;
            let lastTime = 0;
            const animationDuration = 30000; // 调整为15秒完成一个循环
            const minFrameTime = 1000 / 60; // 限制最大帧率为60fps
            let lastFrameTime = 0;
            
            function animate(currentTime) {
                if (!isPlaying) {
                    return;
                }
//对于bubble大小的调节，参考web_region_bubble
                // 控制帧率
                if (currentTime - lastFrameTime < minFrameTime) {
                    requestAnimationFrame(animate);
                    return;
                }
                lastFrameTime = currentTime;

                if (!lastTime) lastTime = currentTime;
                const elapsed = currentTime - lastTime;
                
                // 计算当前进度 (0 到 1)
                const totalProgress = (elapsed % animationDuration) / animationDuration;
                const indexFloat = totalProgress * (years.length - 1);
                const currentIndex = Math.floor(indexFloat);
                const nextIndex = (currentIndex + 1) % years.length;
                const progress = indexFloat - currentIndex;

                // 更新时间轴标记
                if (timeline && timeline.triangle) {
                    const currentX = timeline.scale(years[currentIndex]);
                    const nextX = timeline.scale(years[nextIndex]);
                    const interpolatedX = currentX + (nextX - currentX) * progress;
                    timeline.triangle.attr('transform', `translate(${interpolatedX}, -10) rotate(180)`);
                }

                // 获取当前和下一年的数据
                const currentYearData = processedData.filter(d => d.Year === years[currentIndex]);
                const nextYearData = processedData.filter(d => d.Year === years[nextIndex]);

                // 创建插值数据
                const interpolatedData = currentYearData.map(d => {
                    const nextData = nextYearData.find(nd => nd.Market === d.Market) || d;
                    return {
                        Market: d.Market,
                        Year: years[currentIndex],
                        OnlinePenetration: d.OnlinePenetration + (nextData.OnlinePenetration - d.OnlinePenetration) * progress,
                        OnlineBookings: d.OnlineBookings + (nextData.OnlineBookings - d.OnlineBookings) * progress,
                        GrossBookings: d.GrossBookings + (nextData.GrossBookings - d.GrossBookings) * progress
                    };
                });

                // 更新图表
                createBubbleChart(interpolatedData, years[currentIndex]);
                
                requestAnimationFrame(animate);
            }

            requestAnimationFrame(animate);
        }, 500);
        
    } catch (error) {
        console.error('Error initializing visualization:', error);
        document.getElementById('bubble-chart').innerHTML = `
            <div style="color: red; padding: 20px;">
                Error loading visualization: ${error.message}<br>
                Please check the browser console for more details.
            </div>
        `;
    }
}

// Start the visualization when the page loads
document.addEventListener('DOMContentLoaded', init); 