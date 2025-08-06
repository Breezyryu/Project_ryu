"""
Unified Battery Data Loader

Unified interface for loading different battery data formats (Toyo, PNE)
with automatic format detection and standardized output.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Literal
from dataclasses import dataclass
from enum import Enum
import logging

from .toyo_loader import ToyoDataLoader, create_toyo_loader
from .pne_loader import PNEDataLoader, create_pne_loader

logger = logging.getLogger(__name__)

class DataFormat(Enum):
    """Supported battery data formats."""
    TOYO = "toyo"
    PNE = "pne"
    UNKNOWN = "unknown"

@dataclass
class StandardizedData:
    """Standardized battery data container."""
    data: pd.DataFrame
    format_type: DataFormat
    metadata: Dict[str, Any]
    raw_metadata: Dict[str, Any]
    
    def __post_init__(self):
        """Validate standardized data after initialization."""
        required_columns = ['Datetime', 'Voltage_V', 'Current_A', 'Cycle']
        missing_cols = [col for col in required_columns if col not in self.data.columns]
        if missing_cols:
            logger.warning(f"Missing standardized columns: {missing_cols}")

class UnifiedDataLoader:
    """
    Unified interface for loading different battery data formats.
    
    Automatically detects format type and provides standardized output
    for downstream processing and analysis.
    """
    
    def __init__(self, data_path: Union[str, Path], format_hint: Optional[DataFormat] = None):
        """
        Initialize unified data loader.
        
        Args:
            data_path: Path to data directory
            format_hint: Optional hint for data format to skip auto-detection
        """
        self.data_path = Path(data_path)
        self.format_hint = format_hint
        self.detected_format = None
        self.loader = None
        
        # Auto-detect and initialize appropriate loader
        self._initialize_loader()
    
    def _detect_format(self) -> DataFormat:
        """
        Automatically detect data format based on directory structure.
        
        Returns:
            Detected format type
        """
        if self.format_hint:
            logger.info(f"Using format hint: {self.format_hint}")
            return self.format_hint
        
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data path does not exist: {self.data_path}")
        
        # Check for Toyo format indicators
        toyo_indicators = 0
        numbered_dirs = [d for d in self.data_path.iterdir() 
                        if d.is_dir() and d.name.isdigit()]
        if numbered_dirs:
            toyo_indicators += 2
            
            # Check for CAPACITY.LOG files
            for num_dir in numbered_dirs[:3]:  # Check first 3 directories
                if (num_dir / 'CAPACITY.LOG').exists():
                    toyo_indicators += 1
                
                # Check for numbered test files
                test_files = [f for f in num_dir.iterdir() 
                             if f.is_file() and f.name.isdigit()]
                if test_files:
                    toyo_indicators += 1
        
        # Check for PNE format indicators
        pne_indicators = 0
        channel_dirs = [d for d in self.data_path.iterdir() 
                       if d.is_dir() and 'Ch' in d.name]
        if channel_dirs:
            pne_indicators += 2
            
            # Check for Restore directories with expected file patterns
            for ch_dir in channel_dirs[:3]:  # Check first 3 directories
                restore_dir = ch_dir / 'Restore'
                if restore_dir.exists():
                    pne_indicators += 1
                    
                    # Check for PNE-style CSV files
                    save_data_files = [f for f in restore_dir.iterdir() 
                                     if f.name.startswith('ch') and f.name.endswith('.csv')]
                    if save_data_files:
                        pne_indicators += 1
                    
                    # Check for index files
                    if (restore_dir / 'savingFileIndex_start.csv').exists():
                        pne_indicators += 1
        
        # Check for Pattern directory (PNE specific)
        if (self.data_path / 'Pattern').exists():
            pne_indicators += 1
        
        # Determine format based on indicators
        if pne_indicators > toyo_indicators:
            detected = DataFormat.PNE
        elif toyo_indicators > pne_indicators:
            detected = DataFormat.TOYO
        else:
            detected = DataFormat.UNKNOWN
        
        logger.info(f"Format detection - Toyo indicators: {toyo_indicators}, "
                   f"PNE indicators: {pne_indicators}, Detected: {detected}")
        
        return detected
    
    def _initialize_loader(self):
        """Initialize the appropriate data loader based on detected format."""
        self.detected_format = self._detect_format()
        
        if self.detected_format == DataFormat.TOYO:
            self.loader = create_toyo_loader(self.data_path)
            logger.info("Initialized Toyo data loader")
            
        elif self.detected_format == DataFormat.PNE:
            self.loader = create_pne_loader(self.data_path)
            logger.info("Initialized PNE data loader")
            
        else:
            raise ValueError(f"Unsupported or undetected data format at {self.data_path}")
    
    def _standardize_toyo_data(self, toyo_data: Dict) -> StandardizedData:
        """
        Convert Toyo format data to standardized format.
        
        Args:
            toyo_data: Raw Toyo data from loader
            
        Returns:
            Standardized data container
        """
        # Combine test data from all directories
        all_test_data = []
        all_capacity_data = []
        
        for dir_name, dir_data in toyo_data.items():
            # Process individual test files
            for test_file in dir_data['test_data']:
                df = test_file.data.copy()
                df['Directory'] = dir_name
                df['Source_file'] = test_file.file_path.name
                all_test_data.append(df)
            
            # Process capacity data
            if dir_data['capacity_data']:
                cap_df = dir_data['capacity_data'].data.copy()
                cap_df['Directory'] = dir_name
                all_capacity_data.append(cap_df)
        
        # Combine all data
        combined_test = pd.concat(all_test_data, ignore_index=True) if all_test_data else pd.DataFrame()
        combined_capacity = pd.concat(all_capacity_data, ignore_index=True) if all_capacity_data else pd.DataFrame()
        
        # Create standardized columns
        standardized_data = combined_test.copy() if not combined_test.empty else pd.DataFrame()
        
        # Standard column mapping for Toyo
        if not standardized_data.empty:
            column_mapping = {
                'Datetime': 'Datetime',
                'Voltage[V]': 'Voltage_V',
                'Current[mA]': 'Current_mA',
                'Temp1[Deg]': 'Temperature_C',
                'Condition': 'Condition',
                'Mode': 'Mode',
                'Cycle': 'Cycle'
            }
            
            for old_col, new_col in column_mapping.items():
                if old_col in standardized_data.columns:
                    if old_col != new_col:
                        standardized_data[new_col] = standardized_data[old_col]
            
            # Convert current from mA to A
            if 'Current_mA' in standardized_data.columns:
                standardized_data['Current_A'] = standardized_data['Current_mA'] / 1000
            
            # Ensure required columns exist
            if 'Cycle' not in standardized_data.columns:
                standardized_data['Cycle'] = 1  # Default cycle if not available
        
        # Create metadata
        metadata = {
            'format': DataFormat.TOYO,
            'total_records': len(standardized_data),
            'directories': list(toyo_data.keys()),
            'date_range': (standardized_data['Datetime'].min(), 
                          standardized_data['Datetime'].max()) if 'Datetime' in standardized_data.columns else None,
            'has_capacity_data': not combined_capacity.empty,
            'capacity_records': len(combined_capacity)
        }
        
        # Include capacity data in metadata if available
        raw_metadata = {
            'toyo_data': toyo_data,
            'capacity_data': combined_capacity if not combined_capacity.empty else None
        }
        
        return StandardizedData(
            data=standardized_data,
            format_type=DataFormat.TOYO,
            metadata=metadata,
            raw_metadata=raw_metadata
        )
    
    def _standardize_pne_data(self, pne_data: Dict) -> StandardizedData:
        """
        Convert PNE format data to standardized format.
        
        Args:
            pne_data: Raw PNE data from loader
            
        Returns:
            Standardized data container
        """
        all_channel_data = []
        
        for channel_name, channel_data in pne_data.items():
            for test_file in channel_data.test_files:
                df = test_file.data.copy()
                df['Channel'] = channel_name
                df['File_index'] = test_file.file_index
                all_channel_data.append(df)
        
        # Combine all channel data
        combined_data = pd.concat(all_channel_data, ignore_index=True) if all_channel_data else pd.DataFrame()
        
        # Create standardized columns
        standardized_data = combined_data.copy() if not combined_data.empty else pd.DataFrame()
        
        # Standard column mapping for PNE
        if not standardized_data.empty:
            column_mapping = {
                'Datetime': 'Datetime',
                'Voltage_V': 'Voltage_V',
                'Current_A': 'Current_A',
                'Temperature1': 'Temperature_C',
                'Current_Cycle': 'Cycle',
                'Step_type_name': 'Step_type'
            }
            
            for old_col, new_col in column_mapping.items():
                if old_col in standardized_data.columns:
                    if old_col != new_col:
                        standardized_data[new_col] = standardized_data[old_col]
            
            # Ensure required columns exist
            if 'Cycle' not in standardized_data.columns:
                if 'Current_Cycle' in standardized_data.columns:
                    standardized_data['Cycle'] = standardized_data['Current_Cycle']
                else:
                    standardized_data['Cycle'] = 1  # Default cycle
        
        # Create metadata
        metadata = {
            'format': DataFormat.PNE,
            'total_records': len(standardized_data),
            'channels': list(pne_data.keys()),
            'date_range': (standardized_data['Datetime'].min(), 
                          standardized_data['Datetime'].max()) if 'Datetime' in standardized_data.columns else None,
            'total_test_files': sum(len(ch.test_files) for ch in pne_data.values())
        }
        
        raw_metadata = {
            'pne_data': pne_data
        }
        
        return StandardizedData(
            data=standardized_data,
            format_type=DataFormat.PNE,
            metadata=metadata,
            raw_metadata=raw_metadata
        )
    
    def load_data(self) -> StandardizedData:
        """
        Load data using the appropriate loader and return standardized format.
        
        Returns:
            Standardized data container
        """
        if self.detected_format == DataFormat.TOYO:
            raw_data = self.loader.load_all_data()
            return self._standardize_toyo_data(raw_data)
            
        elif self.detected_format == DataFormat.PNE:
            raw_data = self.loader.load_all_channels()
            return self._standardize_pne_data(raw_data)
            
        else:
            raise ValueError(f"Cannot load data for format: {self.detected_format}")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for the data.
        
        Returns:
            Dictionary containing summary information
        """
        if self.detected_format == DataFormat.TOYO:
            toyo_summary = self.loader.get_summary_statistics()
            return {
                'format': DataFormat.TOYO.value,
                'format_version': toyo_summary.get('format_version'),
                'total_directories': toyo_summary['total_directories'],
                'total_test_files': toyo_summary['total_test_files'],
                'directories_with_capacity': toyo_summary['directories_with_capacity'],
                'details': toyo_summary['directory_details']
            }
            
        elif self.detected_format == DataFormat.PNE:
            pne_summary = self.loader.get_summary_statistics()
            return {
                'format': DataFormat.PNE.value,
                'total_channels': pne_summary['total_channels'],
                'total_test_files': pne_summary['total_test_files'],
                'total_records': pne_summary['total_records'],
                'channels_with_start_index': pne_summary['channels_with_start_index'],
                'channels_with_last_index': pne_summary['channels_with_last_index'],
                'details': pne_summary['channel_details']
            }
            
        else:
            return {'format': DataFormat.UNKNOWN.value, 'error': 'Unsupported format'}
    
    def get_capacity_data(self) -> Optional[pd.DataFrame]:
        """
        Get capacity/cycle data if available.
        
        Returns:
            DataFrame with capacity data or None if not available
        """
        if self.detected_format == DataFormat.TOYO:
            return self.loader.get_combined_capacity_data()
            
        elif self.detected_format == DataFormat.PNE:
            # For PNE, extract capacity data from test files
            standardized = self.load_data()
            if 'Chg_Capacity_mAh' in standardized.data.columns:
                capacity_data = standardized.data.groupby(['Channel', 'Cycle']).agg({
                    'Chg_Capacity_mAh': 'max',
                    'Dchg_Capacity_mAh': 'max',
                    'Datetime': 'first',
                    'Voltage_V': 'mean',
                    'Temperature_C': 'mean'
                }).reset_index()
                return capacity_data
            else:
                return None
        
        return None
    
    def export_standardized_data(self, output_path: Union[str, Path], 
                                format: Literal['csv', 'parquet', 'hdf5'] = 'csv') -> Path:
        """
        Export standardized data to specified format.
        
        Args:
            output_path: Output file path
            format: Output format ('csv', 'parquet', 'hdf5')
            
        Returns:
            Path to exported file
        """
        output_path = Path(output_path)
        standardized = self.load_data()
        
        if format == 'csv':
            if not output_path.suffix:
                output_path = output_path.with_suffix('.csv')
            standardized.data.to_csv(output_path, index=False)
            
        elif format == 'parquet':
            if not output_path.suffix:
                output_path = output_path.with_suffix('.parquet')
            standardized.data.to_parquet(output_path, index=False)
            
        elif format == 'hdf5':
            if not output_path.suffix:
                output_path = output_path.with_suffix('.h5')
            standardized.data.to_hdf(output_path, key='data', mode='w')
            
        else:
            raise ValueError(f"Unsupported export format: {format}")
        
        logger.info(f"Exported standardized data to {output_path}")
        return output_path


def create_unified_loader(data_path: Union[str, Path], 
                         format_hint: Optional[DataFormat] = None) -> UnifiedDataLoader:
    """
    Factory function to create a UnifiedDataLoader instance.
    
    Args:
        data_path: Path to data directory
        format_hint: Optional format hint to skip auto-detection
        
    Returns:
        Configured UnifiedDataLoader instance
    """
    return UnifiedDataLoader(data_path, format_hint)


# Example usage and validation
if __name__ == "__main__":
    import sys
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Example usage
    if len(sys.argv) > 1:
        data_path = sys.argv[1]
        
        try:
            # Create unified loader
            loader = create_unified_loader(data_path)
            
            # Get summary
            summary = loader.get_summary()
            print("Data Summary:")
            for key, value in summary.items():
                if key != 'details':
                    print(f"  {key}: {value}")
            
            # Load standardized data
            standardized = loader.load_data()
            print(f"\nStandardized Data:")
            print(f"  Format: {standardized.format_type}")
            print(f"  Shape: {standardized.data.shape}")
            print(f"  Columns: {list(standardized.data.columns)}")
            
            # Show sample data
            if not standardized.data.empty:
                print("\nFirst 5 rows:")
                print(standardized.data.head())
            
            # Show capacity data if available
            capacity_data = loader.get_capacity_data()
            if capacity_data is not None and not capacity_data.empty:
                print(f"\nCapacity Data Shape: {capacity_data.shape}")
                print("First 5 rows of capacity data:")
                print(capacity_data.head())
            
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        print("Usage: python unified_loader.py <data_path>")
        print("Example: python unified_loader.py /path/to/battery/data")