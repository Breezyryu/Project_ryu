# 🔋 Battery Data Preprocessor

A comprehensive Python toolkit for processing, analyzing, and visualizing battery testing data from multiple formats. Built with automatic format detection, advanced analytics, and interactive web-based reporting.

## 📋 Table of Contents

- [Features](#-features)
- [Supported Data Formats](#-supported-data-formats)
- [Installation](#-installation)
- [Quick Start](#-quick-start)
- [Usage Examples](#-usage-examples)
- [API Documentation](#-api-documentation)
- [Advanced Features](#-advanced-features)
- [GUI Interface](#-gui-interface)
- [Web Automation](#-web-automation)
- [Contributing](#-contributing)
- [License](#-license)

## 🚀 Features

### Core Capabilities
- **🔄 Unified Data Loading**: Automatic format detection and standardized output
- **📊 Advanced Analytics**: Sequential analysis with data quality validation
- **🎨 Interactive Visualizations**: Web-based dashboards with Plotly integration
- **🤖 Browser Automation**: Automated report generation with Playwright
- **🖥️ GUI Interface**: User-friendly Streamlit-based interface
- **📁 Multiple Export Formats**: CSV, Parquet, HDF5, JSON support

### Analysis Features
- **Data Quality Validation**: Comprehensive integrity checks
- **Electrochemical Analysis**: Voltage, current, and cycling behavior
- **Anomaly Detection**: Statistical outlier identification
- **Performance Metrics**: Capacity, efficiency, and temperature analysis
- **Degradation Analysis**: Long-term performance trends

## 📊 Supported Data Formats

### Toyo Format (Toyo1/Toyo2)
- **Structure**: Numbered directories (93/, 86/) with individual test files and CAPACITY.LOG
- **Files**: 000001, 000002, etc. + CAPACITY.LOG
- **Auto-detection**: Format version detection (Toyo1 vs Toyo2)
- **Data**: Voltage, current, temperature, cycle data

### PNE Format
- **Structure**: Channel directories (M01Ch003[003]/) with CSV files
- **Files**: ch03_SaveData*.csv + index files
- **Features**: 47-column structure with unit conversion (µV→V, µA→A)
- **Index Files**: savingFileIndex_start.csv, savingFileIndex_last.csv

## 🛠 Installation

### Prerequisites
- Python 3.8+
- pip package manager

### Basic Installation
```bash
git clone <repository-url>
cd battery-data-preprocessor
pip install -r requirements.txt
```

### Full Installation (with web features)
```bash
# Install additional dependencies
pip install plotly streamlit playwright

# Install Playwright browsers
playwright install
```

### Requirements
```
pandas>=1.5.0
numpy>=1.20.0
scipy>=1.7.0
plotly>=5.0.0          # For visualizations
streamlit>=1.20.0      # For GUI
playwright>=1.30.0     # For browser automation
```

## 🚀 Quick Start

### Basic Usage

```python
from preprocess.loaders import create_unified_loader

# Load data with automatic format detection
loader = create_unified_loader("path/to/your/data")
standardized_data = loader.load_data()

print(f"Loaded {len(standardized_data.data):,} records")
print(f"Format: {standardized_data.format_type}")
print(f"Columns: {list(standardized_data.data.columns)}")
```

### Analysis Pipeline

```python
from preprocess.analysis.battery_analyzer import create_battery_analyzer

# Create analyzer
analyzer = create_battery_analyzer(standardized_data.data)

# Run comprehensive analysis
results = analyzer.run_comprehensive_analysis()

# Generate report
report = analyzer.generate_analysis_report()
print(report)
```

### Web Visualization

```python
import asyncio
from automation.web_visualizer import BatteryReportGenerator

async def generate_report():
    generator = BatteryReportGenerator()
    outputs = await generator.generate_comprehensive_report(
        standardized_data,
        open_browser=True
    )
    return outputs

# Run async function
outputs = asyncio.run(generate_report())
```

## 📖 Usage Examples

### Example 1: Complete Processing Pipeline

```python
import asyncio
from pathlib import Path
from preprocess.loaders import create_unified_loader
from preprocess.analysis.battery_analyzer import create_battery_analyzer
from automation.web_visualizer import BatteryReportGenerator

async def process_battery_data(data_path):
    # 1. Load data
    loader = create_unified_loader(data_path)
    standardized_data = loader.load_data()
    
    # 2. Analyze data
    analyzer = create_battery_analyzer(standardized_data.data)
    analysis_results = analyzer.run_comprehensive_analysis()
    
    # 3. Generate web report
    generator = BatteryReportGenerator()
    outputs = await generator.generate_comprehensive_report(standardized_data)
    
    return outputs

# Usage
outputs = asyncio.run(process_battery_data("path/to/data"))
```

### Example 2: Data Quality Assessment

```python
from preprocess.analysis.battery_analyzer import create_battery_analyzer

# Load your data first
analyzer = create_battery_analyzer(data)

# Validate data quality
validation = analyzer.validate_data_quality()

print(f"Status: {'VALID' if validation.is_valid else 'INVALID'}")
print(f"Quality Score: {validation.quality_score:.1f}%")
print(f"Issues: {len(validation.issues)}")

# Show recommendations
for rec in validation.recommendations:
    print(f"• {rec}")
```

### Example 3: Export Data

```python
# Export to different formats
outputs = {}

# CSV export
outputs['csv'] = standardized_data.data.to_csv("battery_data.csv", index=False)

# Parquet export (compressed, fast)
outputs['parquet'] = standardized_data.data.to_parquet("battery_data.parquet")

# JSON export
outputs['json'] = standardized_data.data.to_json("battery_data.json", orient='records')
```

## 📚 API Documentation

### Core Classes

#### `UnifiedDataLoader`
```python
loader = create_unified_loader(data_path, format_hint=None)

# Methods
loader.get_summary()                    # Get data summary
loader.load_data()                      # Load standardized data
loader.get_capacity_data()              # Get capacity/cycle data
loader.export_standardized_data(path)   # Export to file
```

#### `BatteryDataAnalyzer`
```python
analyzer = create_battery_analyzer(data, format_type)

# Methods
analyzer.validate_data_quality()        # Data quality validation
analyzer.analyze_basic_statistics()     # Statistical analysis
analyzer.detect_anomalies()             # Anomaly detection
analyzer.calculate_performance_metrics() # Performance metrics
analyzer.run_comprehensive_analysis()   # Complete pipeline
analyzer.generate_analysis_report()     # Text report
```

#### `WebVisualizer`
```python
visualizer = create_web_visualizer(config)

# Methods
visualizer.create_interactive_dashboard() # HTML dashboard
await visualizer.capture_screenshot()     # Browser screenshot
await visualizer.generate_automated_report() # Complete report
```

### Data Structures

#### `StandardizedData`
```python
@dataclass
class StandardizedData:
    data: pd.DataFrame          # Standardized data
    format_type: DataFormat     # Original format
    metadata: Dict[str, Any]    # Summary metadata
    raw_metadata: Dict[str, Any] # Raw loader metadata
```

#### `AnalysisResult`
```python
@dataclass
class AnalysisResult:
    analysis_type: str          # Analysis type identifier
    results: Dict[str, Any]     # Analysis results
    metadata: Dict[str, Any]    # Analysis metadata
    timestamp: datetime         # When analysis was run
```

## 🎯 Advanced Features

### Sequential Analysis Integration

The system uses **Sequential Thinking** patterns for systematic analysis:

1. **Data Quality Validation** → Integrity checks, missing data analysis
2. **Basic Statistical Analysis** → Descriptive statistics, correlations
3. **Electrochemical Analysis** → Voltage, current, cycling patterns
4. **Anomaly Detection** → Outlier identification, temporal anomalies
5. **Performance Metrics** → Capacity, efficiency, temperature analysis

### Context7 Integration

Leverages **Context7** for best practices in data processing:
- Pandas optimization techniques
- Scientific computing patterns
- Data visualization standards
- Export format recommendations

### Magic UI Components

**Streamlit-based GUI** with modern components:
- Drag-and-drop file upload
- Interactive data preview
- Real-time analysis progress
- Export controls
- Visualization dashboards

### Playwright Automation

**Browser automation** capabilities:
- Automated screenshot capture
- Interactive report generation
- Cross-browser compatibility
- Headless operation support

## 🖥️ GUI Interface

### Launch GUI

```bash
# Navigate to project directory
cd battery-data-preprocessor

# Launch Streamlit GUI
streamlit run gui/battery_data_gui.py
```

### GUI Features

- **📂 Data Input**: Local directory or file upload
- **🔍 Format Detection**: Automatic format identification
- **📊 Data Preview**: Interactive data tables
- **📈 Visualizations**: Real-time charts and plots
- **📁 Export Controls**: Multiple format options
- **📋 Analysis Summary**: Quality metrics and insights

### GUI Screenshots

The GUI provides:
1. **Data source selection** (local directory or upload)
2. **Automatic format detection** with confidence indicators
3. **Interactive data preview** with filtering and sorting
4. **Real-time visualizations** with Plotly integration
5. **Export controls** for multiple formats
6. **Analysis dashboard** with quality metrics

## 🤖 Web Automation

### Automated Report Generation

```python
from automation.web_visualizer import BatteryReportGenerator

# Create generator
generator = BatteryReportGenerator()

# Generate report with screenshots
outputs = await generator.generate_comprehensive_report(
    standardized_data,
    output_dir=Path("reports"),
    open_browser=True
)

# Outputs include:
# - Interactive HTML report
# - Dashboard screenshot (PNG)
# - Analysis summary (JSON)
```

### Browser Automation Features

- **Automated Screenshots**: Full-page dashboard captures
- **Interactive Reports**: HTML with embedded visualizations  
- **Cross-browser Testing**: Chrome, Firefox, Safari support
- **Headless Operation**: Server-friendly automation
- **Custom Styling**: Professional report templates

## 🧪 Testing and Validation

### Run Tests

```bash
# Run basic tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=preprocess --cov-report=html

# Run specific test categories
python -m pytest tests/test_loaders.py -v
python -m pytest tests/test_analysis.py -v
```

### Validation Checks

The system includes comprehensive validation:

- **Data Integrity**: Missing values, data types, ranges
- **Temporal Consistency**: Time gaps, duplicate timestamps
- **Value Validation**: Physical ranges for voltage, current, temperature
- **Statistical Validation**: Outlier detection, distribution analysis
- **Format Compliance**: Structure validation for each format

## 📁 Project Structure

```
battery-data-preprocessor/
├── preprocess/
│   ├── loaders/                 # Data loading modules
│   │   ├── toyo_loader.py      # Toyo format loader
│   │   ├── pne_loader.py       # PNE format loader
│   │   └── unified_loader.py   # Unified interface
│   └── analysis/               # Analysis modules
│       └── battery_analyzer.py # Sequential analysis
├── gui/
│   └── battery_data_gui.py     # Streamlit GUI
├── automation/
│   └── web_visualizer.py       # Playwright automation
├── examples/
│   └── basic_usage_example.py  # Usage examples
├── tests/                      # Test suites
├── docs/                       # Documentation
├── requirements.txt            # Dependencies
└── README.md                   # This file
```

## 🎓 Educational Resources

### Tutorial Series

1. **[Basic Usage Tutorial](examples/basic_usage_example.py)**: Complete walkthrough
2. **[Data Loading Guide](docs/data_loading.md)**: Format-specific instructions
3. **[Analysis Pipeline](docs/analysis_guide.md)**: Sequential analysis workflow
4. **[Visualization Guide](docs/visualization.md)**: Web-based reporting
5. **[Advanced Features](docs/advanced_features.md)**: Custom analysis and automation

### Best Practices

- **Data Preparation**: Clean, validate, and structure your data
- **Analysis Workflow**: Follow sequential analysis patterns
- **Quality Validation**: Always validate before analysis
- **Resource Management**: Use chunking for large datasets
- **Export Strategy**: Choose appropriate formats for downstream use

## 🔧 Configuration

### Analysis Configuration

```python
# Configure analyzer parameters
analyzer.config.update({
    'voltage_limits': (2.5, 4.5),      # V
    'current_limits': (-10.0, 10.0),   # A
    'temperature_limits': (-20, 80),    # °C
    'outlier_threshold': 3.0,           # Standard deviations
    'min_cycle_points': 10              # Minimum points per cycle
})
```

### Visualization Configuration

```python
from automation.web_visualizer import VisualizationConfig

config = VisualizationConfig(
    width=1200,
    height=800,
    theme='plotly_white',
    interactive=True
)

visualizer = create_web_visualizer(config)
```

## 🚀 Performance Optimization

### Large Dataset Handling

- **Chunked Processing**: Process data in manageable chunks
- **Memory Management**: Efficient pandas operations
- **Parallel Processing**: Multi-core analysis where possible
- **Caching**: Intermediate result caching for repeated analysis

### Tips for Better Performance

```python
# Use efficient data types
data = data.astype({
    'Voltage_V': 'float32',
    'Current_A': 'float32',
    'Temperature_C': 'float32'
})

# Limit visualization data points
plot_data = data.sample(n=10000) if len(data) > 10000 else data

# Use parquet for faster I/O
data.to_parquet('battery_data.parquet', compression='snappy')
```

## 🤝 Contributing

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd battery-data-preprocessor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install development dependencies
pip install -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install
```

### Contribution Guidelines

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** changes (`git commit -m 'Add amazing feature'`)
4. **Push** to branch (`git push origin feature/amazing-feature`)
5. **Open** a Pull Request

### Code Standards

- Follow **PEP 8** style guidelines
- Add **type hints** for all functions
- Include **docstrings** for all public APIs
- Write **unit tests** for new features
- Update **documentation** for changes

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Pandas Development Team** for excellent data manipulation tools
- **Plotly Team** for interactive visualization capabilities
- **Streamlit Team** for rapid web app development
- **Microsoft Playwright** for browser automation
- **Battery Research Community** for domain expertise and data format insights

## 📞 Support

### Getting Help

- **Documentation**: Check the `docs/` directory
- **Examples**: Run `examples/basic_usage_example.py`
- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Browser Automation**: Install Playwright browsers (`playwright install`)
3. **Large Files**: Use chunking or sampling for memory efficiency
4. **Format Detection**: Verify directory structure matches format specifications

---

**Made with ❤️ for the Battery Research Community**

*Empowering researchers with intelligent data preprocessing and analysis tools*