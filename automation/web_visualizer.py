"""
Web-based Battery Data Visualization with Playwright Automation

Automated browser-based visualization and reporting for battery data analysis.
Provides automated screenshots, interactive plots, and web-based report generation.
"""

import asyncio
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from datetime import datetime
import logging
import json
import tempfile
import webbrowser
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from playwright.async_api import async_playwright, Page, Browser
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logging.warning("Playwright not available - browser automation features disabled")

from preprocess.loaders import StandardizedData, DataFormat
from preprocess.analysis.battery_analyzer import BatteryDataAnalyzer, AnalysisResult

logger = logging.getLogger(__name__)

@dataclass
class VisualizationConfig:
    """Configuration for web visualizations."""
    width: int = 1200
    height: int = 800
    theme: str = 'plotly_white'
    export_format: str = 'html'
    interactive: bool = True
    
class WebVisualizer:
    """
    Web-based visualizer with browser automation capabilities.
    
    Creates interactive HTML reports with Plotly visualizations and
    uses Playwright for automated screenshot capture and report generation.
    """
    
    def __init__(self, config: Optional[VisualizationConfig] = None):
        """
        Initialize web visualizer.
        
        Args:
            config: Visualization configuration
        """
        self.config = config or VisualizationConfig()
        self.browser = None
        self.page = None
        
        if not PLAYWRIGHT_AVAILABLE:
            logger.warning("Playwright not available - limited functionality")
    
    async def initialize_browser(self, headless: bool = True) -> bool:
        """
        Initialize Playwright browser.
        
        Args:
            headless: Whether to run browser in headless mode
            
        Returns:
            True if successful, False otherwise
        """
        if not PLAYWRIGHT_AVAILABLE:
            logger.error("Playwright not available")
            return False
        
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=headless)
            self.page = await self.browser.new_page()
            
            # Set viewport size
            await self.page.set_viewport_size({
                "width": self.config.width, 
                "height": self.config.height
            })
            
            logger.info("Browser initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            return False
    
    async def close_browser(self):
        """Close browser and cleanup resources."""
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
        
        logger.info("Browser closed")
    
    def create_interactive_dashboard(self, 
                                   standardized_data: StandardizedData,
                                   analysis_results: Dict[str, AnalysisResult]) -> str:
        """
        Create interactive HTML dashboard with battery data visualizations.
        
        Args:
            standardized_data: Standardized battery data
            analysis_results: Analysis results from BatteryDataAnalyzer
            
        Returns:
            HTML content as string
        """
        logger.info("Creating interactive dashboard...")
        
        data = standardized_data.data
        
        # Import plotly for visualization
        try:
            import plotly.graph_objects as go
            import plotly.express as px
            from plotly.subplots import make_subplots
            import plotly.io as pio
        except ImportError:
            logger.error("Plotly not available - cannot create visualizations")
            return self._create_basic_html_report(standardized_data, analysis_results)
        
        # Create dashboard with multiple subplots
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=('Voltage vs Time', 'Current vs Time', 'Temperature vs Time',
                           'Voltage Distribution', 'Current Distribution', 'Cycle Analysis'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Time series plots
        if 'Datetime' in data.columns and 'Voltage_V' in data.columns:
            # Limit data points for performance
            plot_data = data.head(5000) if len(data) > 5000 else data
            
            fig.add_trace(
                go.Scatter(x=plot_data['Datetime'], y=plot_data['Voltage_V'],
                          mode='lines', name='Voltage', line=dict(color='blue')),
                row=1, col=1
            )
        
        if 'Datetime' in data.columns and 'Current_A' in data.columns:
            plot_data = data.head(5000) if len(data) > 5000 else data
            
            fig.add_trace(
                go.Scatter(x=plot_data['Datetime'], y=plot_data['Current_A'],
                          mode='lines', name='Current', line=dict(color='red')),
                row=1, col=2
            )
        
        if 'Datetime' in data.columns and 'Temperature_C' in data.columns:
            plot_data = data.head(5000) if len(data) > 5000 else data
            
            fig.add_trace(
                go.Scatter(x=plot_data['Datetime'], y=plot_data['Temperature_C'],
                          mode='lines', name='Temperature', line=dict(color='green')),
                row=2, col=1
            )
        
        # Distribution plots
        if 'Voltage_V' in data.columns:
            fig.add_trace(
                go.Histogram(x=data['Voltage_V'], name='Voltage Dist', 
                           marker_color='lightblue', opacity=0.7),
                row=2, col=2
            )
        
        if 'Current_A' in data.columns:
            fig.add_trace(
                go.Histogram(x=data['Current_A'], name='Current Dist',
                           marker_color='lightcoral', opacity=0.7),
                row=3, col=1
            )
        
        # Cycle analysis
        if 'Cycle' in data.columns and 'Voltage_V' in data.columns:
            cycle_stats = data.groupby('Cycle')['Voltage_V'].agg(['mean', 'min', 'max']).reset_index()
            
            fig.add_trace(
                go.Scatter(x=cycle_stats['Cycle'], y=cycle_stats['mean'],
                          mode='lines+markers', name='Avg Voltage/Cycle',
                          line=dict(color='purple')),
                row=3, col=2
            )
        
        # Update layout
        fig.update_layout(
            height=1200,
            title_text="Battery Data Analysis Dashboard",
            showlegend=True,
            template=self.config.theme
        )
        
        # Create complete HTML page
        html_content = self._create_html_wrapper(
            fig.to_html(include_plotlyjs='cdn', div_id="main-dashboard"),
            standardized_data,
            analysis_results
        )
        
        logger.info("Interactive dashboard created")
        return html_content
    
    def _create_html_wrapper(self, 
                           plotly_html: str, 
                           standardized_data: StandardizedData,
                           analysis_results: Dict[str, AnalysisResult]) -> str:
        """Create complete HTML wrapper with styling and summary information."""
        
        # Extract key metrics for summary
        data = standardized_data.data
        summary_stats = {
            'total_records': len(data),
            'date_range': None,
            'voltage_range': None,
            'current_range': None,
            'format_type': standardized_data.format_type.value
        }
        
        if 'Datetime' in data.columns:
            datetime_col = pd.to_datetime(data['Datetime'], errors='coerce').dropna()
            if len(datetime_col) > 0:
                summary_stats['date_range'] = f"{datetime_col.min()} to {datetime_col.max()}"
        
        if 'Voltage_V' in data.columns:
            voltage_col = data['Voltage_V'].dropna()
            if len(voltage_col) > 0:
                summary_stats['voltage_range'] = f"{voltage_col.min():.3f}V - {voltage_col.max():.3f}V"
        
        if 'Current_A' in data.columns:
            current_col = data['Current_A'].dropna()
            if len(current_col) > 0:
                summary_stats['current_range'] = f"{current_col.min():.3f}A - {current_col.max():.3f}A"
        
        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Battery Data Analysis Report</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f8f9fa;
                    color: #333;
                }}
                .header {{
                    text-align: center;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 2.5em;
                    font-weight: 300;
                }}
                .header p {{
                    margin: 10px 0 0 0;
                    font-size: 1.1em;
                    opacity: 0.9;
                }}
                .summary-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin-bottom: 30px;
                }}
                .summary-card {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    border-left: 4px solid #667eea;
                }}
                .summary-card h3 {{
                    margin: 0 0 10px 0;
                    color: #667eea;
                    font-size: 1.1em;
                }}
                .summary-card p {{
                    margin: 0;
                    font-size: 1.2em;
                    font-weight: 500;
                }}
                .dashboard-container {{
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    padding: 20px;
                    margin-bottom: 30px;
                }}
                .analysis-summary {{
                    background: white;
                    border-radius: 10px;
                    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    padding: 20px;
                }}
                .analysis-item {{
                    margin-bottom: 15px;
                    padding: 15px;
                    background: #f8f9fa;
                    border-radius: 5px;
                    border-left: 3px solid #28a745;
                }}
                .analysis-item h4 {{
                    margin: 0 0 10px 0;
                    color: #28a745;
                }}
                .timestamp {{
                    text-align: center;
                    color: #666;
                    font-size: 0.9em;
                    margin-top: 20px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🔋 Battery Data Analysis Report</h1>
                <p>Generated on {datetime.now().strftime('%B %d, %Y at %H:%M:%S')}</p>
            </div>
            
            <div class="summary-grid">
                <div class="summary-card">
                    <h3>📊 Total Records</h3>
                    <p>{summary_stats['total_records']:,}</p>
                </div>
                <div class="summary-card">
                    <h3>📋 Data Format</h3>
                    <p>{summary_stats['format_type'].upper()}</p>
                </div>
                <div class="summary-card">
                    <h3>⚡ Voltage Range</h3>
                    <p>{summary_stats['voltage_range'] or 'N/A'}</p>
                </div>
                <div class="summary-card">
                    <h3>🔄 Current Range</h3>
                    <p>{summary_stats['current_range'] or 'N/A'}</p>
                </div>
                <div class="summary-card">
                    <h3>📅 Date Range</h3>
                    <p>{summary_stats['date_range'] or 'N/A'}</p>
                </div>
                <div class="summary-card">
                    <h3>📈 Analyses</h3>
                    <p>{len(analysis_results)} Completed</p>
                </div>
            </div>
            
            <div class="dashboard-container">
                <h2>📊 Interactive Data Visualization</h2>
                {plotly_html}
            </div>
            
            <div class="analysis-summary">
                <h2>🔍 Analysis Summary</h2>
                {self._generate_analysis_summary_html(analysis_results)}
            </div>
            
            <div class="timestamp">
                Report generated using Battery Data Preprocessor | Powered by Plotly & Playwright
            </div>
        </body>
        </html>
        """
        
        return html_template
    
    def _generate_analysis_summary_html(self, analysis_results: Dict[str, AnalysisResult]) -> str:
        """Generate HTML summary of analysis results."""
        if not analysis_results:
            return "<p>No analysis results available.</p>"
        
        html_parts = []
        
        for analysis_name, result in analysis_results.items():
            html_parts.append(f"""
            <div class="analysis-item">
                <h4>{analysis_name.replace('_', ' ').title()}</h4>
                <p><strong>Completed:</strong> {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p><strong>Method:</strong> {result.metadata.get('method', 'N/A')}</p>
            </div>
            """)
        
        return "".join(html_parts)
    
    def _create_basic_html_report(self, 
                                standardized_data: StandardizedData,
                                analysis_results: Dict[str, AnalysisResult]) -> str:
        """Create basic HTML report without Plotly (fallback)."""
        data = standardized_data.data
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Battery Data Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ text-align: center; color: #333; }}
                .summary {{ background: #f4f4f4; padding: 20px; border-radius: 8px; }}
                .data-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .data-table th, .data-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .data-table th {{ background-color: #4CAF50; color: white; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Battery Data Analysis Report</h1>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="summary">
                <h2>Data Summary</h2>
                <p><strong>Total Records:</strong> {len(data):,}</p>
                <p><strong>Columns:</strong> {len(data.columns)}</p>
                <p><strong>Format:</strong> {standardized_data.format_type.value.upper()}</p>
            </div>
            
            <h2>Data Preview</h2>
            <table class="data-table">
                <thead>
                    <tr>{''.join(f'<th>{col}</th>' for col in data.columns[:10])}</tr>
                </thead>
                <tbody>
                    {''.join('<tr>' + ''.join(f'<td>{val}</td>' for val in row[:10]) + '</tr>' 
                            for row in data.head(10).values)}
                </tbody>
            </table>
            
            <h2>Analysis Results</h2>
            <ul>
                {''.join(f'<li>{name.replace("_", " ").title()}: Completed at {result.timestamp}</li>' 
                        for name, result in analysis_results.items())}
            </ul>
        </body>
        </html>
        """
        
        return html_content
    
    async def capture_dashboard_screenshot(self, html_content: str, 
                                         output_path: Optional[Path] = None) -> Optional[Path]:
        """
        Capture screenshot of dashboard using Playwright.
        
        Args:
            html_content: HTML content to render
            output_path: Optional path for screenshot file
            
        Returns:
            Path to screenshot file if successful
        """
        if not PLAYWRIGHT_AVAILABLE or not self.browser:
            logger.error("Browser not available for screenshot capture")
            return None
        
        try:
            # Create temporary HTML file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
                f.write(html_content)
                temp_html_path = Path(f.name)
            
            # Navigate to HTML file
            await self.page.goto(f"file://{temp_html_path.absolute()}")
            
            # Wait for content to load
            await self.page.wait_for_timeout(3000)
            
            # Capture screenshot
            if output_path is None:
                output_path = Path(f"battery_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
            
            await self.page.screenshot(path=str(output_path), full_page=True)
            
            # Cleanup temporary file
            temp_html_path.unlink()
            
            logger.info(f"Dashboard screenshot captured: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to capture screenshot: {e}")
            return None
    
    async def generate_automated_report(self, 
                                      standardized_data: StandardizedData,
                                      analysis_results: Dict[str, AnalysisResult],
                                      output_dir: Optional[Path] = None) -> Dict[str, Path]:
        """
        Generate automated web report with screenshots.
        
        Args:
            standardized_data: Standardized battery data
            analysis_results: Analysis results
            output_dir: Output directory for files
            
        Returns:
            Dictionary mapping output types to file paths
        """
        if output_dir is None:
            output_dir = Path("battery_reports")
        
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        outputs = {}
        
        # Generate HTML dashboard
        html_content = self.create_interactive_dashboard(standardized_data, analysis_results)
        
        # Save HTML report
        html_path = output_dir / f"battery_report_{timestamp}.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        outputs['html'] = html_path
        
        # Capture screenshot if browser available
        if PLAYWRIGHT_AVAILABLE and await self.initialize_browser():
            screenshot_path = output_dir / f"battery_dashboard_{timestamp}.png"
            captured_path = await self.capture_dashboard_screenshot(html_content, screenshot_path)
            if captured_path:
                outputs['screenshot'] = captured_path
            
            await self.close_browser()
        
        logger.info(f"Automated report generated in {output_dir}")
        return outputs
    
    def open_report_in_browser(self, html_path: Path):
        """Open HTML report in default browser."""
        try:
            webbrowser.open(f"file://{html_path.absolute()}")
            logger.info(f"Report opened in browser: {html_path}")
        except Exception as e:
            logger.error(f"Failed to open report in browser: {e}")


class BatteryReportGenerator:
    """High-level interface for generating battery data reports."""
    
    def __init__(self):
        """Initialize report generator."""
        self.visualizer = WebVisualizer()
    
    async def generate_comprehensive_report(self,
                                          standardized_data: StandardizedData,
                                          output_dir: Optional[Path] = None,
                                          open_browser: bool = True) -> Dict[str, Path]:
        """
        Generate comprehensive battery data report.
        
        Args:
            standardized_data: Standardized battery data
            output_dir: Output directory
            open_browser: Whether to open report in browser
            
        Returns:
            Dictionary of generated file paths
        """
        logger.info("Generating comprehensive battery data report...")
        
        # Run analysis
        analyzer = BatteryDataAnalyzer(standardized_data.data, standardized_data.format_type.value)
        analysis_results = analyzer.run_comprehensive_analysis()
        
        # Generate report
        outputs = await self.visualizer.generate_automated_report(
            standardized_data, analysis_results, output_dir
        )
        
        # Open in browser if requested
        if open_browser and 'html' in outputs:
            self.visualizer.open_report_in_browser(outputs['html'])
        
        return outputs


# Factory function
def create_web_visualizer(config: Optional[VisualizationConfig] = None) -> WebVisualizer:
    """
    Factory function to create WebVisualizer instance.
    
    Args:
        config: Visualization configuration
        
    Returns:
        Configured WebVisualizer instance
    """
    return WebVisualizer(config)


# Example usage and testing
async def main():
    """Example usage of web visualizer."""
    import sys
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Create sample data for testing
    dates = pd.date_range('2024-01-01', periods=1000, freq='1min')
    sample_data = pd.DataFrame({
        'Datetime': dates,
        'Voltage_V': 3.7 + 0.5 * np.sin(np.linspace(0, 10, 1000)) + np.random.normal(0, 0.1, 1000),
        'Current_A': 2.0 + np.random.normal(0, 0.5, 1000),
        'Temperature_C': 25 + np.random.normal(0, 2, 1000),
        'Cycle': np.repeat(range(1, 11), 100)
    })
    
    # Create standardized data object
    standardized_data = StandardizedData(
        data=sample_data,
        format_type=DataFormat.TOYO,
        metadata={'test': True},
        raw_metadata={}
    )
    
    try:
        # Create report generator
        generator = BatteryReportGenerator()
        
        # Generate comprehensive report
        outputs = await generator.generate_comprehensive_report(
            standardized_data,
            output_dir=Path("test_reports"),
            open_browser=True
        )
        
        print("Report Generation Complete!")
        print(f"Generated files: {list(outputs.keys())}")
        for file_type, path in outputs.items():
            print(f"  {file_type}: {path}")
        
    except Exception as e:
        print(f"Error generating report: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())