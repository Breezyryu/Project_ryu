"""
Example Usage of Toyo Battery Data Preprocessing Pipeline

This example demonstrates how to use the Toyo preprocessing pipeline
for battery life prediction data preparation.
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from preprocess import run_toyo_preprocessing, ToyoPreprocessingPipeline

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_basic_usage():
    """
    Example of basic pipeline usage with convenience function.
    """
    print("=== Basic Usage Example ===")
    
    # Define paths (these would be your actual data paths)
    src_path = "../../data/raw"  # Your raw Toyo data directory
    dst_path = "../../data/processed"  # Output directory for processed data
    
    try:
        # Run the complete preprocessing pipeline
        results = run_toyo_preprocessing(
            src_path=src_path,
            dst_path=dst_path,
            force_reprocess=False,  # Use existing results if available
            create_visualizations=True
        )
        
        # Print summary
        metadata = results.get('metadata', {})
        print(f"✅ Processing completed successfully!")
        print(f"📊 Channels processed: {len(metadata.get('processed_channels', []))}")
        print(f"⏱️  Processing time: {results.get('pipeline_duration', 0):.2f} seconds")
        print(f"📁 Output directory: {results.get('output_directory')}")
        
        # Access processed data
        if 'combined_battery_data' in results:
            combined_data = results['combined_battery_data']
            print(f"📈 Combined battery data: {len(combined_data)} records")
        
        if 'combined_capacity_data' in results:
            capacity_data = results['combined_capacity_data']
            print(f"🔋 Capacity data: {len(capacity_data)} cycles")
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        logger.error(f"Processing failed: {e}")


def example_advanced_usage():
    """
    Example of advanced pipeline usage with custom configuration.
    """
    print("\n=== Advanced Usage Example ===")
    
    src_path = "../../data/raw"
    dst_path = "../../data/processed_advanced"
    
    try:
        # Initialize pipeline with custom configuration
        pipeline = ToyoPreprocessingPipeline(src_path, dst_path)
        
        # Check data summary before processing
        summary = pipeline.loader.get_data_summary()
        print(f"📋 Data summary: {len(summary)} channels found")
        
        for channel, info in summary.items():
            print(f"  Channel {channel}: {info['data_files']} files, "
                  f"Capacity log: {info['capacity_log']}")
        
        # Run pipeline with custom options
        results = pipeline.run_complete_pipeline(
            save_intermediate=True,      # Save intermediate processing steps
            create_visualizations=True,  # Create comprehensive plots
            save_processed_data=True     # Save final processed data
        )
        
        # Access detailed results
        processed_data = results['processed_data']
        capacity_data = results['processed_capacity']
        
        # Print detailed statistics
        print(f"✅ Advanced processing completed!")
        
        # Channel-specific analysis
        for channel in processed_data.get('summary', {}).keys():
            stats = processed_data['summary'][channel]
            print(f"\n📊 Channel {channel} Statistics:")
            print(f"  - Total Records: {stats.get('total_records', 'N/A'):,}")
            print(f"  - Total Cycles: {stats.get('total_cycles', 'N/A')}")
            print(f"  - Charge Points: {stats.get('charge_points', 'N/A'):,}")
            print(f"  - Discharge Points: {stats.get('discharge_points', 'N/A'):,}")
            
            v_range = stats.get('voltage_range')
            if v_range:
                print(f"  - Voltage Range: {v_range[0]:.3f} - {v_range[1]:.3f} V")
            
            time_span = stats.get('time_span')
            if time_span:
                print(f"  - Time Span: {time_span:.1f} hours")
        
        # Capacity fade analysis
        print(f"\n🔋 Capacity Fade Analysis:")
        for channel, fade_stats in capacity_data.get('summary', {}).items():
            print(f"  Channel {channel}:")
            initial_cap = fade_stats.get('initial_capacity')
            final_cap = fade_stats.get('final_capacity')
            total_fade = fade_stats.get('total_fade')
            
            if initial_cap and final_cap and total_fade:
                print(f"    Initial: {initial_cap:.3f} Ah → Final: {final_cap:.3f} Ah")
                print(f"    Total Fade: {total_fade:.2f}%")
        
    except Exception as e:
        print(f"❌ Error during advanced processing: {e}")
        logger.error(f"Advanced processing failed: {e}")


def example_individual_components():
    """
    Example showing how to use individual components separately.
    """
    print("\n=== Individual Components Example ===")
    
    src_path = "../../data/raw"
    
    try:
        # Step 1: Load data
        print("📥 Loading data...")
        from preprocess import ToyoDataLoader
        
        loader = ToyoDataLoader(src_path)
        channels = loader.get_channel_folders()
        print(f"Found channels: {channels}")
        
        # Load data for first channel (if available)
        if channels:
            channel = channels[0]
            print(f"Loading data for channel {channel}...")
            
            # Load main battery data
            battery_data = loader.load_channel_data(channel)
            print(f"Loaded {len(battery_data)} battery records")
            
            # Load capacity data
            capacity_data = loader.load_capacity_log(channel)
            if capacity_data is not None:
                print(f"Loaded {len(capacity_data)} capacity records")
            
            # Step 2: Process data
            print("🔄 Processing data...")
            from preprocess import ToyoDataProcessor
            
            processor = ToyoDataProcessor()
            
            # Clean the data
            cleaned_data = processor.clean_and_convert_data(battery_data)
            print(f"Cleaned data: {len(cleaned_data)} records")
            
            # Extract charge/discharge cycles
            cycles = processor.extract_charge_discharge_cycles(cleaned_data)
            print(f"Charge points: {len(cycles['charge'])}")
            print(f"Discharge points: {len(cycles['discharge'])}")
            
            # Calculate energy metrics
            energy_metrics = processor.calculate_energy_metrics(cleaned_data)
            print(f"Energy metrics calculated for {len(energy_metrics)} cycles")
            
            # Step 3: Create visualizations
            print("📊 Creating visualizations...")
            from preprocess import ToyoVisualizer
            
            visualizer = ToyoVisualizer()
            
            # Extract voltage curves
            voltage_curves = processor.extract_voltage_curves(cleaned_data)
            
            # Create voltage curves plot (first 5 cycles)
            if voltage_curves:
                fig = visualizer.plot_voltage_curves(
                    voltage_curves, 
                    channel, 
                    cycles_to_plot=list(voltage_curves.keys())[:5]
                )
                print(f"Created voltage curves plot for {len(voltage_curves)} cycles")
                
                # Note: In real usage, you would save the plot:
                # fig.savefig(f'voltage_curves_channel_{channel}.png')
        
        print("✅ Individual components example completed!")
        
    except Exception as e:
        print(f"❌ Error in individual components example: {e}")
        logger.error(f"Individual components example failed: {e}")


def example_data_exploration():
    """
    Example showing data exploration capabilities.
    """
    print("\n=== Data Exploration Example ===")
    
    src_path = "../../data/raw"
    
    try:
        from preprocess import ToyoDataLoader
        
        loader = ToyoDataLoader(src_path)
        
        # Get comprehensive data summary
        summary = loader.get_data_summary()
        
        print("📊 Data Exploration Results:")
        print(f"Total channels found: {len(summary)}")
        
        for channel, info in summary.items():
            print(f"\n📁 Channel {channel}:")
            print(f"  Path: {info['path']}")
            print(f"  Data files: {info['data_files']}")
            print(f"  Capacity log: {info['capacity_log']}")
            
            # Try to load a sample of data for analysis
            try:
                sample_data = loader.load_channel_data(channel)
                if not sample_data.empty:
                    print(f"  Sample data loaded: {len(sample_data)} records")
                    
                    # Show data structure
                    print(f"  Columns: {list(sample_data.columns)}")
                    
                    # Show date range if available
                    if 'Date' in sample_data.columns and 'Time' in sample_data.columns:
                        first_date = sample_data['Date'].iloc[0] if len(sample_data) > 0 else 'N/A'
                        last_date = sample_data['Date'].iloc[-1] if len(sample_data) > 0 else 'N/A'
                        print(f"  Date range: {first_date} to {last_date}")
                else:
                    print("  ⚠️  No data could be loaded")
                    
            except Exception as e:
                print(f"  ❌ Error loading sample: {e}")
        
        print("\n✅ Data exploration completed!")
        
    except Exception as e:
        print(f"❌ Error during data exploration: {e}")
        logger.error(f"Data exploration failed: {e}")


def main():
    """
    Main function demonstrating all examples.
    """
    print("🔋 Toyo Battery Data Preprocessing Examples")
    print("=" * 50)
    
    # Note: These examples assume your data directory structure
    # Modify the paths according to your actual data location
    
    print("ℹ️  Note: These examples use placeholder paths.")
    print("   Please update the paths to point to your actual Toyo data directories.")
    print("   Expected structure:")
    print("   ../../data/raw/")
    print("   ├── 93/")
    print("   │   ├── 000001")
    print("   │   ├── 000002")
    print("   │   └── CAPACITY.LOG")
    print("   ├── 86/")
    print("   └── ...")
    print()
    
    # Run examples (commented out to avoid errors when actual data isn't available)
    
    # Uncomment these lines when you have actual Toyo data:
    # example_data_exploration()
    # example_basic_usage() 
    # example_advanced_usage()
    # example_individual_components()
    
    print("💡 To run these examples with your data:")
    print("   1. Update the src_path variables to point to your Toyo data directory")
    print("   2. Uncomment the example function calls above")
    print("   3. Run this script again")
    
    print("\n🚀 Example code is ready to use!")


if __name__ == "__main__":
    main()