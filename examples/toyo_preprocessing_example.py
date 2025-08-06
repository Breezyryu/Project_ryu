"""
Example Usage of Toyo Battery Data Preprocessing Pipeline

This example demonstrates how to use the Toyo preprocessing pipeline
for battery life prediction data preparation.
"""

import os
import sys
import logging
import argparse
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


def example_basic_usage(src_path=None, dst_path=None):
    """
    Example of basic pipeline usage with convenience function.
    
    Args:
        src_path: Path to raw data directory (can be absolute or relative)
        dst_path: Path to output directory (can be absolute or relative)
    """
    print("=== Basic Usage Example ===")
    
    # Use provided paths or defaults
    if src_path is None:
        src_path = "../../data/raw"  # Default relative path
    if dst_path is None:
        dst_path = "../../data/processed"  # Default output directory
    
    # Convert to Path objects to handle both absolute and relative paths
    src_path = Path(src_path)
    dst_path = Path(dst_path)
    
    print(f"📁 Source path: {src_path.absolute()}")
    print(f"📁 Output path: {dst_path.absolute()}")
    
    try:
        # Run the complete preprocessing pipeline
        results = run_toyo_preprocessing(
            src_path=str(src_path),
            dst_path=str(dst_path),
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


def example_advanced_usage(src_path=None, dst_path=None):
    """
    Example of advanced pipeline usage with custom configuration.
    
    Args:
        src_path: Path to raw data directory (can be absolute or relative)
        dst_path: Path to output directory (can be absolute or relative)
    """
    print("\n=== Advanced Usage Example ===")
    
    # Use provided paths or defaults
    if src_path is None:
        src_path = "../../data/raw"  # Default relative path
    if dst_path is None:
        dst_path = "../../data/processed_advanced"  # Default output directory
    
    # Convert to Path objects
    src_path = Path(src_path)
    dst_path = Path(dst_path)
    
    print(f"📁 Source path: {src_path.absolute()}")
    print(f"📁 Output path: {dst_path.absolute()}")
    
    try:
        # Initialize pipeline with custom configuration
        pipeline = ToyoPreprocessingPipeline(str(src_path), str(dst_path))
        
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


def example_individual_components(src_path=None):
    """
    Example showing how to use individual components separately.
    
    Args:
        src_path: Path to raw data directory (can be absolute or relative)
    """
    print("\n=== Individual Components Example ===")
    
    # Use provided path or default
    if src_path is None:
        src_path = "../../data/raw"  # Default relative path
    
    # Convert to Path object
    src_path = Path(src_path)
    print(f"📁 Source path: {src_path.absolute()}")
    
    try:
        # Step 1: Load data
        print("📥 Loading data...")
        from preprocess import ToyoDataLoader
        
        loader = ToyoDataLoader(str(src_path))
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


def example_data_exploration(src_path=None):
    """
    Example showing data exploration capabilities.
    
    Args:
        src_path: Path to raw data directory (can be absolute or relative)
    """
    print("\n=== Data Exploration Example ===")
    
    # Use provided path or default
    if src_path is None:
        src_path = "../../data/raw"  # Default relative path
    
    # Convert to Path object
    src_path = Path(src_path)
    print(f"📁 Source path: {src_path.absolute()}")
    
    try:
        from preprocess import ToyoDataLoader
        
        loader = ToyoDataLoader(str(src_path))
        
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
    # Create argument parser
    parser = argparse.ArgumentParser(
        description="Toyo Battery Data Preprocessing Examples",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
          # Use absolute path for raw data:
          python toyo_preprocessing_example.py --src C:/data/toyo/raw --dst C:/data/toyo/processed
          
          # Use only source path (output will be in default location):
          python toyo_preprocessing_example.py --src /home/user/toyo_data
          
          # Run specific example:
          python toyo_preprocessing_example.py --src C:/data/raw --example basic
        """
    )
    
    parser.add_argument(
        '--src', '--source',
        type=str,
        help='Path to raw Toyo data directory (absolute or relative)',
        default=None
    )
    
    parser.add_argument(
        '--dst', '--destination',
        type=str,
        help='Path to output directory for processed data (absolute or relative)',
        default=None
    )
    
    parser.add_argument(
        '--example',
        type=str,
        choices=['basic', 'advanced', 'individual', 'exploration', 'all'],
        default='all',
        help='Which example to run (default: all)'
    )
    
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force reprocessing even if processed data exists'
    )
    
    args = parser.parse_args()
    
    print("🔋 Toyo Battery Data Preprocessing Examples")
    print("=" * 50)
    
    # Check if source path is provided
    if args.src:
        src_path = Path(args.src)
        if not src_path.exists():
            print(f"❌ Error: Source path does not exist: {src_path}")
            print("   Please provide a valid path to your Toyo data directory.")
            return
        
        print(f"✅ Using source path: {src_path.absolute()}")
        
        # Set destination path
        if args.dst:
            dst_path = Path(args.dst)
        else:
            # Default: create output folder based on input folder name
            # ../../preprocess/입력폴더명
            input_folder_name = src_path.name  # Get the last part of the path
            dst_path = Path("../../preprocess") / input_folder_name
            
            # Create the directory if it doesn't exist
            dst_path.mkdir(parents=True, exist_ok=True)
        
        print(f"✅ Using output path: {dst_path.absolute()}")
        print(f"   (Created from input folder: {src_path.name})")
        print()
        
        # Run selected examples
        if args.example == 'basic' or args.example == 'all':
            example_basic_usage(src_path, dst_path)
        
        if args.example == 'advanced' or args.example == 'all':
            example_advanced_usage(src_path, dst_path)
        
        if args.example == 'individual' or args.example == 'all':
            example_individual_components(src_path)
        
        if args.example == 'exploration' or args.example == 'all':
            example_data_exploration(src_path)
        
    else:
        # No source path provided, show help
        print("ℹ️  No source path provided. Showing usage information:")
        print()
        print("To run examples with your data, provide the path to your raw data directory:")
        print("  python toyo_preprocessing_example.py --src <path_to_raw_data>")
        print()
        print("Examples:")
        print("  # Windows absolute path:")
        print("  python toyo_preprocessing_example.py --src C:/Users/YourName/toyo_data/raw")
        print()
        print("  # Linux/Mac absolute path:")
        print("  python toyo_preprocessing_example.py --src /home/username/toyo_data/raw")
        print()
        print("  # Relative path:")
        print("  python toyo_preprocessing_example.py --src ../../data/raw")
        print()
        print("Expected Toyo data directory structure:")
        print("  your_data_path/")
        print("  ├── 93/")
        print("  │   ├── 000001")
        print("  │   ├── 000002")
        print("  │   └── CAPACITY.LOG")
        print("  ├── 86/")
        print("  └── ...")
        print()
        print("For more options, run: python toyo_preprocessing_example.py --help")


if __name__ == "__main__":
    main()