// 定义国家代码映射
const countryCodeMapping = {
    "Singapore": "SG",
    "China": "CN",
    "India": "IN",
    "Indonesia": "ID",
    "Malaysia": "MY",
    "Thailand": "TH",
    "Vietnam": "VN",
    "Philippines": "PH",
    "Japan": "JP",
    "South Korea": "KR",
    "Hong Kong": "HK",
    "Taiwan": "TW",
    "Macau": "MO",
    "Australia & New Zealand": "AU/NZ"
};

// 获取国家代码的辅助函数
function getCountryCode(countryName) {
    return countryCodeMapping[countryName] || countryName;
}

// 在文件开头添加一个变量来跟踪历史最大值
let historicalMaxValue = 0;

function createRaceChart(data, year) {
    console.log("Creating race chart for year:", year);
    console.log("Raw data received:", data);

    // 数据验证
    if (!data || !Array.isArray(data)) {
        console.error("Invalid data received:", data);
        return;
    }

    // 计算所有年份的最大值
    const allYearsData = data.map(d => d['Gross Bookings'] * appConfig.dataProcessing.bookingsScaleFactor);
    const maxValueAllYears = Math.max(...allYearsData);
    
    // 更新历史最大值
    historicalMaxValue = Math.max(historicalMaxValue, maxValueAllYears);
    console.log("Historical max value:", historicalMaxValue);

    // 验证年份数据
    const yearData = data.filter(d => d.Year === year);
    console.log(`Data for year ${year}:`, yearData);

    if (yearData.length === 0) {
        console.error(`No data found for year ${year}`);
        return;
    }

    // Replace APAC countries data with Middle Eastern countries data
    const middleEastCountriesData = window.processedCountriesData ? 
        window.processedCountriesData.filter(d => d.Year === year && 
            ['Egypt', 'Qatar', 'Rest of Middle East', 'Saudi Arabia', 'U.A.E.', 'Malaysia', 'Indonesia'].includes(d.Market)) : [];

    console.log("Middle Eastern countries data:", middleEastCountriesData);

    // Combine region and country data
    let combinedData = [...yearData];

    // Debug log to check if Middle Eastern countries are being processed
    console.log("Middle Eastern countries data for race chart:", middleEastCountriesData);

    // Ensure Middle Eastern countries are added to combinedData
    middleEastCountriesData.forEach(country => {
        const countryData = {
            Region: country.Market,
            'Gross Bookings': country.GrossBookings,
            'Online Bookings': country.OnlineBookings,
            'Online Penetration': country.OnlinePenetration,
            Year: country.Year
        };
        console.log(`Adding Middle Eastern country data for ${country.Market}:`, countryData);
        combinedData.push(countryData);
    });

    // Ensure all major regions have data
    const requiredRegions = [
        'Europe', 
        'Eastern Europe', 
        'Latin America', 
        'Middle East (sum)', 
        'North America',
        'Asia-Pacific'
    ];

    requiredRegions.forEach(region => {
        const exists = combinedData.some(d => d.Region === region);
        if (!exists) {
            console.warn(`Adding placeholder for missing region: ${region}`);
            combinedData.push({
                Region: region,
                Year: year,
                'Gross Bookings': 0.1,
                'Online Bookings': 0.1,
                'Online Penetration': 0.1
            });
        }
    });

    // Debug log to check combined data before processing
    console.log("Combined data before processing for race chart:", combinedData);

    // Process data
    const processedData = combinedData.map(d => {
        const regionName = d.Region;
        const isApacCountry = middleEastCountriesData.some(c => c.Market === regionName) || 
                            ['Malaysia', 'Indonesia'].includes(regionName);
        
        // Special handling for display names
        let displayName = regionName;
        if (regionName === 'Australia & New Zealand') {
            displayName = 'Australia & NZ';
        }
        // Add "(sum)" to Middle East region display name
        if (regionName === 'Middle East (sum)') {
            displayName = 'Middle East (sum)';
        }
        // Convert U.A.E. to UAE
        if (regionName === 'U.A.E.') {
            displayName = 'UAE';
        }

        const isRegion = requiredRegions.includes(regionName);
        
        // Ensure values are valid
        const grossBookings = parseFloat(d['Gross Bookings']) || 0;
        const value = grossBookings * appConfig.dataProcessing.bookingsScaleFactor;
        
        console.log(`Processing ${regionName}:`, {
            originalValue: d['Gross Bookings'],
            processedValue: value,
            scaleFactor: appConfig.dataProcessing.bookingsScaleFactor
        });

        let color;
        if (regionName === 'Middle East (sum)' || (middleEastCountriesData.some(c => c.Market === regionName) && !['Malaysia', 'Indonesia'].includes(regionName))) {
            color = '#DEB887';
        } else if (regionName === 'Europe') {
            color = '#4169E1';
        } else if (regionName === 'Eastern Europe') {
            color = '#9370DB';
        } else if (regionName === 'Latin America') {
            color = '#32CD32';
        } else if (regionName === 'North America') {
            color = '#40E0D0';
        } else if (regionName === 'Asia-Pacific' || ['Malaysia', 'Indonesia'].includes(regionName)) {
            color = '#FF4B4B'; // Red color for Asia-Pacific, Malaysia and Indonesia
        } else {
            color = '#888888';
        }

        return {
            region: regionName,
            displayName: displayName,
            value: value,
            originalValue: grossBookings,
            color: color,
            isApacCountry: isApacCountry,
            isRegion: isRegion
        };
    });

    // 区分区域和国家数据并各自排序
    const regionData = processedData
        .filter(d => d.isRegion && d.value > 0.1)
        .sort((a, b) => a.value - b.value);

    const excludedRegions = ['Hong Kong', 'Macau', 'Taiwan'];
    const countryData = processedData
        .filter(d => !d.isRegion && d.value > 0.1 && !excludedRegions.includes(d.region))
        .sort((a, b) => a.value - b.value);

    // 只取国家数据，不包含区域数据
    const targetData = countryData;

    // 获取当前最大值
    const currentTopValue = countryData.length > 0 ? countryData[countryData.length - 1].value : 0;
    console.log("Current top value:", currentTopValue);
    
    // 使用历史最大值和当前最大值中的较大值
    const xAxisMax = Math.max(currentTopValue, historicalMaxValue);
    console.log("Using x-axis max:", xAxisMax);

    // 创建柱状图数据
    const barData = {
        type: 'bar',
        x: targetData.map(d => d.value),
        y: targetData.map(d => d.displayName),
        orientation: 'h',
        marker: {
            color: targetData.map(d => d.color),
            width: 0.2
        },
        text: targetData.map(d => d.value),
        textposition: 'outside',
        hoverinfo: 'text',
        texttemplate: '%{text:$.1f}B',
        textfont: {
            family: 'Monda',
            size: 14
        },
        cliponaxis: false
    };
    
    // 创建布局
    const layout = {
        title: {
            text: '',
            font: {
                family: 'Monda',
                size: 16
            },
            y: 0.95
        },
        xaxis: {
            title: {
                text: 'Gross Bookings (USD bn)',
                font: {
                    family: 'Monda',
                    size: 16
                },
                standoff: 15
            },
            showgrid: true,
            gridcolor: '#eee',
            gridwidth: 1,
            zeroline: true,
            zerolinecolor: '#eee',
            tickfont: {
                family: 'Monda',
                size: 18
            },
            range: [0, 70],
            fixedrange: false,
            ticks: 'outside',
            ticklen: 8,
            tickwidth: 1,
            tickcolor: '#ccc',
            showticklabels: true,
            tickvals: [0, 20, 40, 60],
            ticktext: ['0', '20', '40', '60']
        },
        yaxis: {
            showgrid: false,
            tickfont: {
                family: 'Monda',
                size: 14
            },
            fixedrange: true,
            automargin: true
        },
        margin: {
            l: 120,
            r: 60,
            t: 10,
            b: 50
        },
        height: 400,
        width: 400,
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        showlegend: false,
        barmode: 'group',
        bargap: 0.1,
        bargroupgap: 0.1,
        font: {
            family: 'Monda'
        }
    };

    // 创建配置
    const config = {
        displayModeBar: false,
        responsive: false,
        staticPlot: false
    };
    
    // 渲染图表
    Plotly.newPlot('race-chart', [barData], layout, config);
    
    // 存储当前数据以便进行平滑过渡
    window.raceChartData = targetData;
    window.previousSortedData = targetData.map(d => ({...d}));
}

// 添加线性插值函数
function lerp(start, end, t) {
    return start * (1 - t) + end * t;
}

// 添加动画状态变量
let animationFrameId = null;
let animationStartTime = null;
let animationDuration = 800; // 动画持续时间（毫秒）

function updateRaceChart(data, year, forceUpdate = false) {
    // 如果没有设置全局最大值，重新绘制整个图表
    if (typeof historicalMaxValue === 'undefined') {
        createRaceChart(data, year);
        return;
    }

    // 取消之前的动画
    if (animationFrameId) {
        cancelAnimationFrame(animationFrameId);
    }

    // 获取当前年份的数据并处理
    const yearData = data.filter(d => d.Year === year);
    const middleEastCountriesData = window.processedCountriesData ? 
        window.processedCountriesData.filter(d => d.Year === year && 
            ['Egypt', 'Qatar', 'Rest of Middle East', 'Saudi Arabia', 'U.A.E.', 'Malaysia', 'Indonesia'].includes(d.Market)) : [];

    // 组合并处理数据
    let combinedData = [...yearData];

    // Add Middle East countries data
    middleEastCountriesData.forEach(country => {
        combinedData.push({
            Region: country.Market,
            'Gross Bookings': country.GrossBookings,
            'Online Bookings': country.OnlineBookings,
            'Online Penetration': country.OnlinePenetration,
            Year: year
        });
    });

    // 确保所有必要区域都存在
    const requiredRegions = [
        'Europe', 
        'Eastern Europe', 
        'Latin America', 
        'Middle East (sum)', 
        'North America',
        'Asia-Pacific'
    ];

    requiredRegions.forEach(region => {
        if (!combinedData.some(d => d.Region === region)) {
            combinedData.push({
                Region: region,
                Year: year,
                'Gross Bookings': 0.1,
                'Online Bookings': 0.1,
                'Online Penetration': 0.1
            });
        }
    });

    // 处理数据
    const processedData = combinedData.map(d => {
        const regionName = d.Region;
        const isApacCountry = middleEastCountriesData.some(c => c.Market === regionName) || 
                            ['Malaysia', 'Indonesia'].includes(regionName);
        
        // 特殊处理Australia & New Zealand，其他国家保持全名
        let displayName = regionName;
        if (regionName === 'Australia & New Zealand') {
            displayName = 'Australia & NZ';
        }
        // Add "(sum)" to Middle East region display name
        if (regionName === 'Middle East (sum)') {
            displayName = 'Middle East (sum)';
        }
        // Convert U.A.E. to UAE
        if (regionName === 'U.A.E.') {
            displayName = 'UAE';
        }
        
        const isRegion = requiredRegions.includes(regionName);
        
        // 确保数值是有效的
        const grossBookings = parseFloat(d['Gross Bookings']) || 0;
        const value = grossBookings * appConfig.dataProcessing.bookingsScaleFactor;
        
        console.log(`Processing ${regionName}:`, {
            originalValue: d['Gross Bookings'],
            processedValue: value,
            scaleFactor: appConfig.dataProcessing.bookingsScaleFactor
        });

        let color;
        if (regionName === 'Middle East (sum)' || (middleEastCountriesData.some(c => c.Market === regionName) && !['Malaysia', 'Indonesia'].includes(regionName))) {
            color = '#DEB887';
        } else if (regionName === 'Europe') {
            color = '#4169E1';
        } else if (regionName === 'Eastern Europe') {
            color = '#9370DB';
        } else if (regionName === 'Latin America') {
            color = '#32CD32';
        } else if (regionName === 'North America') {
            color = '#40E0D0';
        } else if (regionName === 'Asia-Pacific' || ['Malaysia', 'Indonesia'].includes(regionName)) {
            color = '#FF4B4B'; // Red color for Asia-Pacific, Malaysia and Indonesia
        } else {
            color = '#888888';
        }

        return {
            region: regionName,
            displayName: displayName,
            value: value,
            originalValue: grossBookings,
            color: color,
            isApacCountry: isApacCountry,
            isRegion: isRegion
        };
    });

    // 区分区域和国家数据并各自排序
    const regionData = processedData
        .filter(d => d.isRegion && d.value > 0.1)
        .sort((a, b) => a.value - b.value);

    const excludedRegions = ['Hong Kong', 'Macau', 'Taiwan'];
    const countryData = processedData
        .filter(d => !d.isRegion && d.value > 0.1 && !excludedRegions.includes(d.region))
        .sort((a, b) => a.value - b.value);

    // 只取国家数据，不包含区域数据
    const targetData = countryData;

    // 获取当前最大值
    const currentTopValue = countryData.length > 0 ? countryData[countryData.length - 1].value : 0;
    console.log("Current top value:", currentTopValue);
    
    // 使用历史最大值和当前最大值中的较大值
    const xAxisMax = Math.max(currentTopValue, historicalMaxValue);
    console.log("Using x-axis max:", xAxisMax);

    // 如果是第一次更新，直接绘制图表
    if (!window.raceChartData) {
        window.raceChartData = targetData;
        
        Plotly.newPlot('race-chart', [{
            type: 'bar',
            orientation: 'h',
            x: targetData.map(d => d.value),
            y: targetData.map(d => d.displayName),
            text: targetData.map(d => d.value.toFixed(1)),
            textposition: 'outside',
            marker: {
                color: targetData.map(d => d.color),
                width: 0.4
            },
            hoverinfo: 'text',
            texttemplate: '%{text:$.1f}B',
            textfont: { family: 'Monda', size: 14 }
        }], {
            xaxis: {
                range: [0, xAxisMax * 1.2],
                title: {
                    text: 'Gross Bookings (USD bn)',
                    font: { family: 'Monda', size: 16 }
                },
                fixedrange: false,
                showgrid: true,
                gridcolor: '#eee',
                gridwidth: 1,
                zeroline: true,
                zerolinecolor: '#eee',
                tickfont: { family: 'Monda', size: 18 },
                ticks: 'outside',
                ticklen: 8,
                tickwidth: 1,
                tickcolor: '#ccc',
                showticklabels: true,
                tickvals: [0, 200, 400, 600],
                ticktext: ['0', '200', '400', '600']
            },
            yaxis: {
                autorange: true,
                fixedrange: true,
                showgrid: false,
                tickfont: { family: 'Monda', size: 14 }
            },
            margin: { l: 120, r: 60, t: 10, b: 50 },
            height: 400,
            width: 400,
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            showlegend: false,
            bargap: 0.1,
            bargroupgap: 0.1,
            font: { family: 'Monda' }
        }, {
            displayModeBar: false,
            responsive: false
        });
        
        return;
    }
    
    // 保存当前图表状态
    const currentData = {
        x: [...document.getElementById('race-chart').data[0].x],
        y: [...document.getElementById('race-chart').data[0].y],
        colors: [...document.getElementById('race-chart').data[0].marker.color]
    };
    
    // 创建映射关系以便跟踪每个国家
    const currentEntries = currentData.y.map((name, index) => ({
        name,
        value: currentData.x[index],
        color: currentData.colors[index]
    }));
    
    // 创建目标状态的数据映射
    const targetMapping = new Map();
    targetData.forEach(d => {
        targetMapping.set(d.displayName, {
            value: d.value,
            color: d.color
        });
    });
    
    // 设置动画开始时间
    const startTime = performance.now();
    const duration = appConfig.animation.duration;
    
    // 创建动画函数
    function animate(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // 计算当前帧的每个条形的值
        let currentFrameEntries = currentEntries.map(entry => {
            const targetInfo = targetMapping.get(entry.name);
            if (!targetInfo) return entry; // 如果目标中没有这个条目，保持不变
            
            const startValue = entry.value;
            const endValue = targetInfo.value;
            const currentValue = startValue + (endValue - startValue) * progress;
            
            return {
                name: entry.name,
                value: currentValue,
                color: targetInfo.color
            };
        });
        
        // 对当前帧的条形按值排序
        currentFrameEntries.sort((a, b) => a.value - b.value);
        
        // 提取排序后的数据
        const sortedNames = currentFrameEntries.map(e => e.name);
        const sortedValues = currentFrameEntries.map(e => e.value);
        const sortedColors = currentFrameEntries.map(e => e.color);
        
        // 更新图表，使用sorted数据
        Plotly.update('race-chart', {
            x: [sortedValues],
            y: [sortedNames],
            'marker.color': [sortedColors],
            text: [sortedValues.map(val => val.toFixed(1))],
            texttemplate: ['%{text}B']
        }, {
            xaxis: {
                range: [0, 70],
                showticklabels: true,
                tickvals: [0, 20, 40, 60],
                ticktext: ['0', '200', '400', '600'],
                tickfont: { family: 'Monda', size: 18 }
            }
        }, {
            transition: {
                duration: 0
            }
        });
        
        // 如果动画未完成，继续下一帧
        if (progress < 1) {
            animationFrameId = requestAnimationFrame(animate);
        } else {
            // 动画结束，更新存储的数据
            window.raceChartData = targetData;
        }
    }
    
    // 开始动画
    animationFrameId = requestAnimationFrame(animate);
}