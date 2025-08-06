"""
Basic Usage Example for Battery Data Preprocessor

This example demonstrates the basic usage of the battery data preprocessing system
including data loading, analysis, and visualization.
"""

import asyncio
import pandas as pd
from pathlib import Path
import logging
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from preprocess.loaders import create_unified_loader, DataFormat
from preprocess.analysis.battery_analyzer import create_battery_analyzer
from automation.web_visualizer import BatteryReportGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def example_1_basic_data_loading():
    """Example 1: Basic data loading with automatic format detection."""
    print("="*60)
    print("EXAMPLE 1: Basic Data Loading")
    print("="*60)
    
    # Example data path (replace with your actual data path)
    data_path = input("Enter path to your battery data directory: ")
    
    if not data_path.strip():
        print("No path provided, creating sample data...")
        return create_sample_data()
    
    try:
        # Create unified loader with automatic format detection
        loader = create_unified_loader(data_path)
        
        # Get summary information
        summary = loader.get_summary()
        print(f"\nData Summary:")
        print(f"  Format: {summary['format']}")
        print(f"  Files/Directories: {summary.get('total_test_files', summary.get('total_directories', 'N/A'))}")
        
        # Load standardized data
        print("\nLoading standardized data...")
        standardized_data = loader.load_data()
        
        print(f"  Records: {len(standardized_data.data):,}")
        print(f"  Columns: {len(standardized_data.data.columns)}")
        print(f"  Date range: {standardized_data.metadata.get('date_range', 'N/A')}")
        
        return standardized_data
        
    except Exception as e:
        print(f"Error loading data: {e}")
        print("Creating sample data instead...")
        return create_sample_data()

def create_sample_data():
    """Create sample battery data for demonstration."""
    print("Creating sample battery data...")
    
    import numpy as np
    
    # Generate 1000 data points over 24 hours
    dates = pd.date_range('2024-01-01', periods=1000, freq='1T')  # 1-minute intervals
    
    # Simulate realistic battery data
    time_hours = np.linspace(0, 24, 1000)
    
    # Voltage: starts at 4.2V, decreases during discharge cycles
    voltage_base = 4.2 - 0.5 * (time_hours / 24)  # Gradual decrease
    voltage_noise = np.random.normal(0, 0.05, 1000)  # Measurement noise
    voltage = voltage_base + voltage_noise
    
    # Current: alternating charge/discharge cycles
    current = 2.0 * np.sin(time_hours * np.pi / 6) + np.random.normal(0, 0.3, 1000)
    
    # Temperature: varies with current
    temperature = 25 + np.abs(current) * 2 + np.random.normal(0, 1, 1000)
    
    # Cycle numbers
    cycle = np.floor(time_hours / 4).astype(int) + 1  # 4-hour cycles
    
    sample_data = pd.DataFrame({
        'Datetime': dates,
        'Voltage_V': voltage,
        'Current_A': current,
        'Temperature_C': temperature,
        'Cycle': cycle
    })
    
    # Create standardized data object
    from preprocess.loaders.unified_loader import StandardizedData
    
    standardized_data = StandardizedData(
        data=sample_data,
        format_type=DataFormat.TOYO,
        metadata={
            'format': 'sample',
            'total_records': len(sample_data),
            'date_range': (sample_data['Datetime'].min(), sample_data['Datetime'].max())
        },
        raw_metadata={'sample': True}
    )
    
    print(f"  Sample data created: {len(sample_data):,} records")
    print(f"  Time span: {sample_data['Datetime'].iloc[-1] - sample_data['Datetime'].iloc[0]}")
    
    return standardized_data

def example_2_data_analysis(standardized_data):
    """Example 2: Comprehensive data analysis."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Data Analysis")
    print("="*60)
    
    # Create analyzer
    analyzer = create_battery_analyzer(
        standardized_data.data, 
        standardized_data.format_type.value
    )
    
    # Run comprehensive analysis
    print("Running comprehensive analysis...")
    analysis_results = analyzer.run_comprehensive_analysis()
    
    print(f"\nAnalysis completed: {len(analysis_results)} analyses performed")
    
    # Display validation results
    if analyzer.validation_result:
        validation = analyzer.validation_result
        print(f"\nData Quality Assessment:")
        print(f"  Status: {'✅ VALID' if validation.is_valid else '❌ INVALID'}")
        print(f"  Quality Score: {validation.quality_score:.1f}%")
        print(f"  Issues: {len(validation.issues)}")
        print(f"  Warnings: {len(validation.warnings)}")
        
        if validation.issues:
            print("  Critical Issues:")
            for issue in validation.issues[:3]:  # Show first 3
                print(f"    • {issue}")
        
        if validation.recommendations:
            print("  Recommendations:")
            for rec in validation.recommendations[:2]:  # Show first 2
                print(f"    • {rec}")
    
    # Display key analysis results
    for analysis_name, result in analysis_results.items():
        print(f"\n{analysis_name.replace('_', ' ').title()}:")
        print(f"  Completed: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Method: {result.metadata.get('method', 'N/A')}")
        
        # Show some key results based on analysis type
        if analysis_name == 'basic_statistics' and 'descriptive' in result.results:
            stats = result.results['descriptive']
            for var, var_stats in list(stats.items())[:2]:  # Show first 2 variables
                print(f"    {var}: Mean={var_stats['mean']:.3f}, Std={var_stats['std']:.3f}")
        
        elif analysis_name == 'anomaly_detection' and 'statistical_outliers' in result.results:
            outliers = result.results['statistical_outliers']
            total_outliers = sum(var_data.get('z_score_outliers', 0) 
                               for var_data in outliers.values())
            print(f"    Total outliers detected: {total_outliers}")
    
    return analysis_results

async def example_3_web_visualization(standardized_data, analysis_results):
    """Example 3: Web-based visualization and reporting."""
    print("\n" + "="*60)
    print("EXAMPLE 3: Web Visualization")
    print("="*60)
    
    try:
        # Create report generator
        generator = BatteryReportGenerator()
        
        # Generate comprehensive report
        print("Generating interactive web report...")
        output_dir = Path("example_reports")
        output_dir.mkdir(exist_ok=True)
        
        outputs = await generator.generate_comprehensive_report(
            standardized_data,
            output_dir=output_dir,
            open_browser=True  # Set to False if you don't want to auto-open browser
        )
        
        print(f"\nReport generated successfully!")
        print(f"Output directory: {output_dir.absolute()}")
        
        for file_type, file_path in outputs.items():
            print(f"  {file_type.upper()}: {file_path.name}")
        
        if 'html' in outputs:
            print(f"\n📖 Open this file in your browser:")
            print(f"  file://{outputs['html'].absolute()}")
        
        return outputs
        
    except Exception as e:
        print(f"❌ Error generating web visualization: {e}")
        print("💡 Install plotly and playwright for full functionality:")
        print("   pip install plotly playwright")
        print("   playwright install")
        return {}

def example_4_data_export(standardized_data):
    """Example 4: Data export in different formats."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Data Export")
    print("="*60)
    
    # Create exports directory
    export_dir = Path("example_exports")
    export_dir.mkdir(exist_ok=True)
    
    data = standardized_data.data
    timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
    
    # Export to different formats
    formats = {
        'csv': lambda df, path: df.to_csv(path, index=False),
        'parquet': lambda df, path: df.to_parquet(path, index=False),
        'json': lambda df, path: df.to_json(path, orient='records', date_format='iso')
    }
    
    exported_files = {}
    
    for format_name, export_func in formats.items():
        try:
            file_path = export_dir / f"battery_data_{timestamp}.{format_name}"
            export_func(data, file_path)
            exported_files[format_name] = file_path
            
            file_size = file_path.stat().st_size / 1024  # KB
            print(f"  ✅ {format_name.upper()}: {file_path.name} ({file_size:.1f} KB)")
            
        except Exception as e:
            print(f"  ❌ {format_name.upper()}: Failed - {e}")
    
    print(f"\nExported files saved to: {export_dir.absolute()}")
    return exported_files

def example_5_capacity_analysis(standardized_data):
    """Example 5: Specific capacity analysis (if available)."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Capacity Analysis")
    print("="*60)
    
    data = standardized_data.data
    
    # Check if capacity data is available
    capacity_columns = ['Chg_Capacity_mAh', 'Dchg_Capacity_mAh', 'Cap[mAh]']
    available_capacity_cols = [col for col in capacity_columns if col in data.columns]
    
    if not available_capacity_cols:
        print("⚠️  No capacity data columns found in the dataset")
        print("💡 Capacity analysis requires columns like 'Chg_Capacity_mAh' or 'Cap[mAh]'")
        
        # Simulate capacity data from voltage for demonstration
        if 'Voltage_V' in data.columns and 'Cycle' in data.columns:
            print("\n🔧 Simulating capacity data from voltage...")
            
            # Group by cycle and calculate "capacity" metrics
            cycle_analysis = data.groupby('Cycle').agg({
                'Voltage_V': ['mean', 'min', 'max'],
                'Current_A': ['mean', 'min', 'max'],
                'Datetime': ['first', 'last']
            }).round(3)
            
            cycle_analysis.columns = ['_'.join(col).strip() for col in cycle_analysis.columns]
            cycle_analysis['duration_hours'] = (
                cycle_analysis['Datetime_last'] - cycle_analysis['Datetime_first']
            ).dt.total_seconds() / 3600
            
            print("\nCycle Summary (first 5 cycles):")
            print(cycle_analysis[['Voltage_V_mean', 'Current_A_mean', 'duration_hours']].head())
            
            # Simple capacity estimation (demonstration only)
            estimated_capacity = cycle_analysis['Current_A_mean'].abs() * cycle_analysis['duration_hours']
            cycle_analysis['estimated_capacity_Ah'] = estimated_capacity
            
            print(f"\nEstimated capacity range: {estimated_capacity.min():.2f} - {estimated_capacity.max():.2f} Ah")
            
        return cycle_analysis if 'cycle_analysis' in locals() else None
    
    else:
        print(f"✅ Found capacity columns: {available_capacity_cols}")
        
        # Analyze available capacity data
        capacity_stats = {}
        for col in available_capacity_cols:
            capacity_data = data[col].dropna()
            if len(capacity_data) > 0:
                capacity_stats[col] = {
                    'mean': capacity_data.mean(),
                    'std': capacity_data.std(),
                    'min': capacity_data.min(),
                    'max': capacity_data.max(),
                    'count': len(capacity_data)
                }
                
                print(f"\n{col} Statistics:")
                print(f"  Mean: {capacity_stats[col]['mean']:.2f} mAh")
                print(f"  Std:  {capacity_stats[col]['std']:.2f} mAh")
                print(f"  Range: {capacity_stats[col]['min']:.2f} - {capacity_stats[col]['max']:.2f} mAh")
        
        return capacity_stats

async def main():
    """Main function to run all examples."""
    print("🔋 Battery Data Preprocessor - Basic Usage Examples")
    print("="*60)
    print("This example demonstrates the key features of the battery data preprocessing system.")
    print("Follow the prompts to explore different functionalities.\n")
    
    try:
        # Example 1: Data Loading
        standardized_data = example_1_basic_data_loading()
        
        if standardized_data is None:
            print("❌ Could not load or create data. Exiting.")
            return
        
        # Example 2: Data Analysis
        analysis_results = example_2_data_analysis(standardized_data)
        
        # Example 3: Web Visualization (async)
        web_outputs = await example_3_web_visualization(standardized_data, analysis_results)
        
        # Example 4: Data Export
        export_outputs = example_4_data_export(standardized_data)
        
        # Example 5: Capacity Analysis
        capacity_results = example_5_capacity_analysis(standardized_data)
        
        # Summary
        print("\n" + "="*60)
        print("EXAMPLES COMPLETED SUCCESSFULLY! 🎉")
        print("="*60)
        print("Generated outputs:")
        
        if web_outputs:
            print("📊 Web Reports:")
            for file_type, path in web_outputs.items():
                print(f"   {path}")
        
        if export_outputs:
            print("📁 Exported Data:")
            for format_name, path in export_outputs.items():
                print(f"   {path}")
        
        print("\n💡 Next steps:")
        print("• Explore the generated HTML report for interactive visualizations")
        print("• Use the exported data files in your analysis workflows")
        print("• Adapt this example code for your specific battery data")
        print("• Check the documentation for advanced features")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during examples: {e}")
        logger.exception("Error in main examples")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())