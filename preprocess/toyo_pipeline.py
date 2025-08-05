"""
Toyo Battery Data Preprocessing Pipeline

This module provides the main pipeline function to orchestrate the complete
preprocessing workflow for Toyo format battery experimental data.
"""

import os
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import logging
import json
from datetime import datetime
import shutil

from .toyo_data_loader import ToyoDataLoader
from .toyo_data_processor import ToyoDataProcessor
from .toyo_visualizer import ToyoVisualizer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ToyoPreprocessingPipeline:
    """
    Complete preprocessing pipeline for Toyo battery experimental data.
    
    Orchestrates data loading, processing, analysis, and visualization
    for battery life prediction preprocessing.
    """
    
    def __init__(self, src_path: str, dst_path: str):
        """
        Initialize the preprocessing pipeline.
        
        Args:
            src_path: Source path containing raw Toyo data
            dst_path: Destination path for processed data and outputs
        """
        self.src_path = Path(src_path)
        self.dst_path = Path(dst_path)
        
        # Validate paths
        if not self.src_path.exists():
            raise ValueError(f"Source path does not exist: {src_path}")
        
        # Create destination directory
        self.dst_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.loader = ToyoDataLoader(str(self.src_path))
        self.processor = ToyoDataProcessor()
        self.visualizer = ToyoVisualizer()
        
        # Storage for processed data
        self.raw_data = {}
        self.capacity_data = {}
        self.processed_data = {}
        self.processed_capacity = {}
        self.pipeline_metadata = {}
        
        logger.info(f"Pipeline initialized - Source: {src_path}, Destination: {dst_path}")
    
    def run_complete_pipeline(
        self,
        save_intermediate: bool = True,
        create_visualizations: bool = True,
        save_processed_data: bool = True
    ) -> Dict[str, Any]:
        """
        Run the complete preprocessing pipeline.
        
        Args:
            save_intermediate: Whether to save intermediate processing results
            create_visualizations: Whether to create visualization plots
            save_processed_data: Whether to save final processed data
            
        Returns:
            Dictionary containing all processed data and metadata
        """
        pipeline_start = datetime.now()
        logger.info("Starting complete Toyo preprocessing pipeline")
        
        try:
            # Step 1: Load raw data
            logger.info("Step 1: Loading raw data...")
            self._load_raw_data()
            
            # Step 2: Process data
            logger.info("Step 2: Processing data...")
            self._process_data()
            
            # Step 3: Save intermediate results
            if save_intermediate:
                logger.info("Step 3: Saving intermediate results...")
                self._save_intermediate_results()
            
            # Step 4: Create visualizations
            if create_visualizations:
                logger.info("Step 4: Creating visualizations...")
                self._create_visualizations()
            
            # Step 5: Save processed data
            if save_processed_data:
                logger.info("Step 5: Saving processed data...")
                self._save_processed_data()
            
            # Step 6: Generate summary report
            logger.info("Step 6: Generating summary report...")
            self._generate_summary_report()
            
            pipeline_end = datetime.now()
            pipeline_duration = (pipeline_end - pipeline_start).total_seconds()
            
            logger.info(f"Pipeline completed successfully in {pipeline_duration:.2f} seconds")
            
            # Compile results
            results = {
                'raw_data': self.raw_data,
                'capacity_data': self.capacity_data,
                'processed_data': self.processed_data,
                'processed_capacity': self.processed_capacity,
                'metadata': self.pipeline_metadata,
                'pipeline_duration': pipeline_duration,
                'output_directory': str(self.dst_path)
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}")
            raise
    
    def _load_raw_data(self):
        """Load all raw data from source directory."""
        try:
            # Get data summary
            summary = self.loader.get_data_summary()
            logger.info(f"Found {len(summary)} channels: {list(summary.keys())}")
            
            # Load all channel data
            self.raw_data = self.loader.load_all_channels()
            logger.info(f"Loaded raw data for {len(self.raw_data)} channels")
            
            # Load capacity data
            self.capacity_data = self.loader.load_all_capacity_logs()
            logger.info(f"Loaded capacity data for {len(self.capacity_data)} channels")
            
            # Store metadata
            self.pipeline_metadata['data_summary'] = summary
            self.pipeline_metadata['channels_loaded'] = list(self.raw_data.keys())
            self.pipeline_metadata['capacity_channels'] = list(self.capacity_data.keys())
            
        except Exception as e:
            logger.error(f"Error loading raw data: {e}")
            raise
    
    def _process_data(self):
        """Process all loaded data."""
        try:
            # Process main battery data
            if self.raw_data:
                self.processed_data = self.processor.process_channel_data(self.raw_data)
                logger.info("Battery data processing completed")
            
            # Process capacity data
            if self.capacity_data:
                self.processed_capacity = self.processor.process_capacity_data(self.capacity_data)
                logger.info("Capacity data processing completed")
            
            # Update metadata
            self.pipeline_metadata['processing_completed'] = True
            self.pipeline_metadata['processed_channels'] = list(
                self.processed_data.get('cleaned_data', {}).keys()
            )
            
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            raise
    
    def _save_intermediate_results(self):
        """Save intermediate processing results."""
        try:
            intermediate_dir = self.dst_path / "intermediate"
            intermediate_dir.mkdir(exist_ok=True)
            
            # Save cleaned data for each channel
            cleaned_data = self.processed_data.get('cleaned_data', {})
            for channel, df in cleaned_data.items():
                if not df.empty:
                    file_path = intermediate_dir / f"cleaned_data_channel_{channel}.csv"
                    df.to_csv(file_path, index=False)
                    logger.debug(f"Saved cleaned data for channel {channel}")
            
            # Save capacity data
            cleaned_capacity = self.processed_capacity.get('cleaned_capacity', {})
            for channel, df in cleaned_capacity.items():
                if not df.empty:
                    file_path = intermediate_dir / f"capacity_data_channel_{channel}.csv"
                    df.to_csv(file_path, index=False)
                    logger.debug(f"Saved capacity data for channel {channel}")
            
            # Save energy metrics
            energy_metrics = self.processed_data.get('energy_metrics', {})
            for channel, df in energy_metrics.items():
                if not df.empty:
                    file_path = intermediate_dir / f"energy_metrics_channel_{channel}.csv"
                    df.to_csv(file_path, index=False)
                    logger.debug(f"Saved energy metrics for channel {channel}")
            
            logger.info(f"Intermediate results saved to {intermediate_dir}")
            
        except Exception as e:
            logger.error(f"Error saving intermediate results: {e}")
    
    def _create_visualizations(self):
        """Create all visualization plots."""
        try:
            viz_dir = self.dst_path / "visualizations"
            viz_dir.mkdir(exist_ok=True)
            
            # Create comprehensive report
            saved_plots = self.visualizer.create_comprehensive_report(
                self.processed_data,
                self.processed_capacity,
                str(viz_dir)
            )
            
            self.pipeline_metadata['visualization_files'] = saved_plots
            logger.info(f"Created {len(saved_plots)} visualization plots in {viz_dir}")
            
        except Exception as e:
            logger.error(f"Error creating visualizations: {e}")
    
    def _save_processed_data(self):
        """Save final processed data."""
        try:
            processed_dir = self.dst_path / "processed"
            processed_dir.mkdir(exist_ok=True)
            
            # Save combined data for all channels
            all_cleaned_data = []
            cleaned_data = self.processed_data.get('cleaned_data', {})
            
            for channel, df in cleaned_data.items():
                if not df.empty:
                    df_copy = df.copy()
                    df_copy['channel'] = channel
                    all_cleaned_data.append(df_copy)
            
            if all_cleaned_data:
                combined_df = pd.concat(all_cleaned_data, ignore_index=True)
                combined_file = processed_dir / "combined_battery_data.csv"
                combined_df.to_csv(combined_file, index=False)
                logger.info(f"Saved combined battery data: {len(combined_df)} records")
            
            # Save combined capacity data
            all_capacity_data = []
            capacity_fade = self.processed_capacity.get('capacity_fade', {})
            
            for channel, df in capacity_fade.items():
                if not df.empty:
                    df_copy = df.copy()
                    df_copy['channel'] = channel
                    all_capacity_data.append(df_copy)
            
            if all_capacity_data:
                combined_capacity = pd.concat(all_capacity_data, ignore_index=True)
                capacity_file = processed_dir / "combined_capacity_data.csv"
                combined_capacity.to_csv(capacity_file, index=False)
                logger.info(f"Saved combined capacity data: {len(combined_capacity)} records")
            
            # Save summary statistics
            summary_file = processed_dir / "processing_summary.json"
            with open(summary_file, 'w') as f:
                # Make metadata JSON serializable
                serializable_metadata = self._make_json_serializable(self.pipeline_metadata)
                json.dump(serializable_metadata, f, indent=2)
            
            logger.info(f"Processed data saved to {processed_dir}")
            
        except Exception as e:
            logger.error(f"Error saving processed data: {e}")
    
    def _generate_summary_report(self):
        """Generate a comprehensive summary report."""
        try:
            report_file = self.dst_path / "preprocessing_report.md"
            
            with open(report_file, 'w') as f:
                f.write("# Toyo Battery Data Preprocessing Report\n\n")
                f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Data summary
                f.write("## Data Summary\n\n")
                f.write(f"- Source Path: `{self.src_path}`\n")
                f.write(f"- Destination Path: `{self.dst_path}`\n")
                f.write(f"- Channels Found: {len(self.pipeline_metadata.get('channels_loaded', []))}\n")
                f.write(f"- Channels Processed: {len(self.pipeline_metadata.get('processed_channels', []))}\n\n")
                
                # Channel details
                f.write("### Channel Details\n\n")
                summary = self.processed_data.get('summary', {})
                for channel, stats in summary.items():
                    f.write(f"**Channel {channel}:**\n")
                    f.write(f"- Total Records: {stats.get('total_records', 'N/A'):,}\n")
                    f.write(f"- Total Cycles: {stats.get('total_cycles', 'N/A')}\n")
                    f.write(f"- Charge Points: {stats.get('charge_points', 'N/A'):,}\n")
                    f.write(f"- Discharge Points: {stats.get('discharge_points', 'N/A'):,}\n")
                    
                    v_range = stats.get('voltage_range')
                    if v_range:
                        f.write(f"- Voltage Range: {v_range[0]:.3f} - {v_range[1]:.3f} V\n")
                    
                    c_range = stats.get('current_range')
                    if c_range:
                        f.write(f"- Current Range: {c_range[0]:.3f} - {c_range[1]:.3f} A\n")
                    
                    f.write("\n")
                
                # Capacity fade summary
                f.write("### Capacity Fade Analysis\n\n")
                capacity_summary = self.processed_capacity.get('summary', {})
                for channel, stats in capacity_summary.items():
                    f.write(f"**Channel {channel}:**\n")
                    f.write(f"- Discharge Cycles: {stats.get('discharge_cycles', 'N/A')}\n")
                    
                    initial_cap = stats.get('initial_capacity')
                    if initial_cap:
                        f.write(f"- Initial Capacity: {initial_cap:.3f} Ah\n")
                    
                    final_cap = stats.get('final_capacity')
                    if final_cap:
                        f.write(f"- Final Capacity: {final_cap:.3f} Ah\n")
                    
                    total_fade = stats.get('total_fade')
                    if total_fade:
                        f.write(f"- Total Capacity Fade: {total_fade:.2f}%\n")
                    
                    f.write("\n")
                
                # Files generated
                f.write("## Generated Files\n\n")
                f.write("### Processed Data\n")
                f.write("- `processed/combined_battery_data.csv` - Combined cleaned battery data\n")
                f.write("- `processed/combined_capacity_data.csv` - Combined capacity fade data\n")
                f.write("- `processed/processing_summary.json` - Processing metadata\n\n")
                
                f.write("### Visualizations\n")
                viz_files = self.pipeline_metadata.get('visualization_files', {})
                for plot_name, file_path in viz_files.items():
                    f.write(f"- `{Path(file_path).name}` - {plot_name.replace('_', ' ').title()}\n")
                f.write("\n")
                
                f.write("### Intermediate Files\n")
                f.write("- `intermediate/` directory contains cleaned data by channel\n\n")
                
                # Processing statistics
                duration = self.pipeline_metadata.get('pipeline_duration', 0)
                f.write(f"## Processing Statistics\n\n")
                f.write(f"- Total Processing Time: {duration:.2f} seconds\n")
                f.write(f"- Average Time per Channel: {duration/max(len(self.raw_data), 1):.2f} seconds\n\n")
                
                f.write("---\n")
                f.write("*Report generated by Toyo Battery Data Preprocessing Pipeline*\n")
            
            logger.info(f"Summary report saved to {report_file}")
            
        except Exception as e:
            logger.error(f"Error generating summary report: {e}")
    
    def _make_json_serializable(self, obj: Any) -> Any:
        """Convert object to JSON serializable format."""
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, tuple):
            return list(obj)
        elif isinstance(obj, (np.integer, np.int64)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        else:
            return obj
    
    def load_existing_results(self) -> Optional[Dict[str, Any]]:
        """
        Load existing preprocessing results if available.
        
        Returns:
            Dictionary containing loaded results or None if not found
        """
        try:
            summary_file = self.dst_path / "processed" / "processing_summary.json"
            
            if not summary_file.exists():
                logger.info("No existing results found")
                return None
            
            with open(summary_file, 'r') as f:
                metadata = json.load(f)
            
            # Load combined data files
            processed_dir = self.dst_path / "processed"
            results = {'metadata': metadata}
            
            # Load combined battery data
            battery_file = processed_dir / "combined_battery_data.csv"
            if battery_file.exists():
                results['combined_battery_data'] = pd.read_csv(battery_file)
            
            # Load combined capacity data
            capacity_file = processed_dir / "combined_capacity_data.csv"
            if capacity_file.exists():
                results['combined_capacity_data'] = pd.read_csv(capacity_file)
            
            logger.info("Existing results loaded successfully")
            return results
            
        except Exception as e:
            logger.error(f"Error loading existing results: {e}")
            return None


def run_toyo_preprocessing(
    src_path: str,
    dst_path: str,
    force_reprocess: bool = False,
    create_visualizations: bool = True
) -> Dict[str, Any]:
    """
    Convenience function to run Toyo battery data preprocessing.
    
    Args:
        src_path: Source path containing raw Toyo data  
        dst_path: Destination path for processed data and outputs
        force_reprocess: Force reprocessing even if results exist
        create_visualizations: Whether to create visualization plots
        
    Returns:
        Dictionary containing all processed data and metadata
    """
    logger.info("Starting Toyo battery data preprocessing")
    
    # Initialize pipeline
    pipeline = ToyoPreprocessingPipeline(src_path, dst_path)
    
    # Check for existing results
    if not force_reprocess:
        existing_results = pipeline.load_existing_results()
        if existing_results:
            logger.info("Using existing preprocessing results")
            return existing_results
    
    # Run complete pipeline
    results = pipeline.run_complete_pipeline(
        save_intermediate=True,
        create_visualizations=create_visualizations,
        save_processed_data=True
    )
    
    logger.info("Toyo preprocessing completed successfully")
    return results


if __name__ == "__main__":
    # Example usage
    import argparse
    
    parser = argparse.ArgumentParser(description='Toyo Battery Data Preprocessing Pipeline')
    parser.add_argument('--src', required=True, help='Source data directory')
    parser.add_argument('--dst', required=True, help='Destination directory')
    parser.add_argument('--force', action='store_true', help='Force reprocessing')
    parser.add_argument('--no-viz', action='store_true', help='Skip visualizations')
    
    args = parser.parse_args()
    
    # Run preprocessing
    results = run_toyo_preprocessing(
        src_path=args.src,
        dst_path=args.dst,
        force_reprocess=args.force,
        create_visualizations=not args.no_viz
    )
    
    print(f"Preprocessing completed. Results saved to: {args.dst}")
    print(f"Processed {len(results.get('metadata', {}).get('processed_channels', []))} channels")