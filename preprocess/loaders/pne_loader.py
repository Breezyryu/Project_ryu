"""
PNE Battery Data Loader

Loads and processes PNE format battery testing data.
Structure: data_path/M01Ch003[003]/Restore/ch03_SaveData*.csv + index files
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Iterator
from dataclasses import dataclass
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)

# PNE column mapping based on the documented structure
PNE_COLUMN_MAP = {
    0: 'Index',
    1: 'Default',
    2: 'Step_type',  # 1:충전, 2:방전, 3:휴지, 4:OCV, 5:Impedance, 8:loop
    3: 'ChgDchg',    # 1:CV, 2:CC, 255:rest
    4: 'Current_classification',  # 1:전류 비인가 직전, 2:전류인가
    5: 'CCCV',       # 0:CC, 1:CV
    6: 'EndState',   # 0:Pattern시작, 64:휴지, 65:CC, 66:CV, 69:Pattern종료, 78:용량
    7: 'Step_count',
    8: 'Voltage_uV',
    9: 'Current_uA',
    10: 'Chg_Capacity_uAh',
    11: 'Dchg_Capacity_uAh',
    12: 'Chg_Power_mW',
    13: 'Dchg_Power_mW',
    14: 'Chg_WattHour_Wh',
    15: 'Dchg_WattHour_Wh',
    16: 'Repeat_pattern_count',
    17: 'StepTime_centisec',
    18: 'TotTime_day',
    19: 'TotTime_centisec',
    20: 'Impedance',
    21: 'Temperature1',
    22: 'Temperature2',
    23: 'Temperature3',
    24: 'Temperature4',
    25: 'Unknown25',
    26: 'Repeat_count',
    27: 'TotalCycle',
    28: 'Current_Cycle',
    29: 'Average_Voltage_uV',
    30: 'Average_Current_uA',
    31: 'Unknown31',
    32: 'CV_section',
    33: 'Date_YYYYMMDD',
    34: 'Time_centisec',
    35: 'Unknown35',
    36: 'Unknown36',
    37: 'Unknown37',
    38: 'Step_specific',
    39: 'CC_charge',
    40: 'CV_section2',
    41: 'Discharge',
    42: 'Unknown42',
    43: 'Average_Voltage_section',
    44: 'Cumulative_step',
    45: 'Voltage_max_uV',
    46: 'Voltage_min_uV'
}

@dataclass
class PNETestData:
    """Container for PNE test data from CSV files."""
    data: pd.DataFrame
    metadata: Dict
    file_path: Path
    file_index: int
    
    def __post_init__(self):
        """Validate data integrity after initialization."""
        if self.data.empty:
            raise ValueError(f"Empty data in {self.file_path}")

@dataclass
class PNEIndexData:
    """Container for PNE index data (start/last files)."""
    data: pd.DataFrame
    metadata: Dict
    file_path: Path
    index_type: str  # 'start' or 'last'

@dataclass
class PNEChannelData:
    """Container for all data from a PNE channel directory."""
    test_files: List[PNETestData]
    start_index: Optional[PNEIndexData]
    last_index: Optional[PNEIndexData]
    metadata: Dict
    channel_path: Path

class PNEDataLoader:
    """
    Load and process PNE format battery testing data.
    
    Handles channel-based directory structure with CSV test data files
    and index files for tracking file ranges.
    """
    
    def __init__(self, data_path: Union[str, Path]):
        """
        Initialize PNE data loader.
        
        Args:
            data_path: Path to PNE data directory containing channel folders
        """
        self.data_path = Path(data_path)
        self._validate_data_path()
        
    def _validate_data_path(self):
        """Validate that the data path exists and contains expected structure."""
        if not self.data_path.exists():
            raise FileNotFoundError(f"Data path does not exist: {self.data_path}")
        
        # Check for channel directories (M01Ch003[003]/, etc.)
        channel_dirs = [d for d in self.data_path.iterdir() 
                       if d.is_dir() and 'Ch' in d.name]
        
        if not channel_dirs:
            # Also check for Pattern directory as mentioned in spec
            pattern_dir = self.data_path / 'Pattern'
            if pattern_dir.exists():
                logger.info(f"Found Pattern directory: {pattern_dir}")
            else:
                raise ValueError(f"No channel directories or Pattern directory found in {self.data_path}")
        else:
            logger.info(f"Found {len(channel_dirs)} channel directories: {[d.name for d in channel_dirs]}")
    
    def _parse_channel_name(self, channel_dir: Path) -> Dict[str, str]:
        """
        Parse channel directory name to extract channel info.
        
        Args:
            channel_dir: Path to channel directory (e.g., M01Ch003[003])
            
        Returns:
            Dictionary with parsed channel information
        """
        dir_name = channel_dir.name
        
        # Pattern: M01Ch003[003] or similar
        match = re.match(r'(M\d+)Ch(\d+)\[(\d+)\]', dir_name)
        if match:
            return {
                'module': match.group(1),
                'channel_num': match.group(2),
                'channel_id': match.group(3),
                'full_name': dir_name
            }
        else:
            # Fallback for non-standard naming
            return {
                'module': 'unknown',
                'channel_num': 'unknown',
                'channel_id': 'unknown', 
                'full_name': dir_name
            }
    
    def _load_test_file(self, file_path: Path) -> PNETestData:
        """
        Load individual PNE test CSV file.
        
        Args:
            file_path: Path to CSV test file
            
        Returns:
            PNETestData object containing parsed data
        """
        try:
            # Read CSV with no header, as PNE files don't have column names
            data = pd.read_csv(file_path, header=None, low_memory=False)
            
            # Apply column mapping if we have enough columns
            if len(data.columns) <= len(PNE_COLUMN_MAP):
                column_names = [PNE_COLUMN_MAP.get(i, f'Unknown_{i}') 
                              for i in range(len(data.columns))]
                data.columns = column_names
            else:
                logger.warning(f"File {file_path} has more columns than expected: {len(data.columns)}")
            
            # Convert key numeric columns
            numeric_conversions = {
                'Voltage_uV': lambda x: x / 1_000_000,  # Convert µV to V
                'Current_uA': lambda x: x / 1_000_000,  # Convert µA to A
                'Chg_Capacity_uAh': lambda x: x / 1000,  # Convert µAh to mAh
                'Dchg_Capacity_uAh': lambda x: x / 1000,  # Convert µAh to mAh
                'Average_Voltage_uV': lambda x: x / 1_000_000,  # Convert µV to V
                'Average_Current_uA': lambda x: x / 1_000_000,  # Convert µA to A
                'Voltage_max_uV': lambda x: x / 1_000_000,  # Convert µV to V
                'Voltage_min_uV': lambda x: x / 1_000_000   # Convert µV to V
            }
            
            for col, conversion_func in numeric_conversions.items():
                if col in data.columns:
                    data[f'{col.replace("_uV", "_V").replace("_uA", "_A").replace("_uAh", "_mAh")}'] = \
                        pd.to_numeric(data[col], errors='coerce').apply(conversion_func)
            
            # Parse date and time
            if 'Date_YYYYMMDD' in data.columns and 'Time_centisec' in data.columns:
                # Convert date from YYYYMMDD format
                data['Date'] = pd.to_datetime(data['Date_YYYYMMDD'], format='%Y%m%d', errors='coerce')
                
                # Convert time from centiseconds to datetime
                data['Time_seconds'] = data['Time_centisec'] / 100
                data['Datetime'] = data['Date'] + pd.to_timedelta(data['Time_seconds'], unit='s')
            
            # Parse step types and states
            if 'Step_type' in data.columns:
                step_type_map = {1: 'Charge', 2: 'Discharge', 3: 'Rest', 4: 'OCV', 5: 'Impedance', 8: 'Loop'}
                data['Step_type_name'] = data['Step_type'].map(step_type_map)
            
            if 'ChgDchg' in data.columns:
                chgdchg_map = {1: 'CV', 2: 'CC', 255: 'Rest'}
                data['ChgDchg_name'] = data['ChgDchg'].map(chgdchg_map)
            
            # Extract file index from filename
            file_index = self._extract_file_index(file_path)
            
            # Create metadata
            metadata = {
                'file_name': file_path.name,
                'file_index': file_index,
                'total_records': len(data),
                'date_range': (data['Datetime'].min(), data['Datetime'].max()) if 'Datetime' in data else None,
                'voltage_range': (data['Voltage_V'].min(), data['Voltage_V'].max()) if 'Voltage_V' in data else None,
                'current_range': (data['Current_A'].min(), data['Current_A'].max()) if 'Current_A' in data else None,
                'cycle_range': (data['Current_Cycle'].min(), data['Current_Cycle'].max()) if 'Current_Cycle' in data else None
            }
            
            return PNETestData(data=data, metadata=metadata, file_path=file_path, file_index=file_index)
            
        except Exception as e:
            logger.error(f"Error loading PNE test file {file_path}: {e}")
            raise
    
    def _extract_file_index(self, file_path: Path) -> int:
        """
        Extract file index from PNE filename (e.g., ch03_SaveData0001.csv -> 1).
        
        Args:
            file_path: Path to PNE file
            
        Returns:
            File index number
        """
        filename = file_path.stem
        match = re.search(r'(\d+)', filename)
        return int(match.group(1)) if match else 0
    
    def _load_index_file(self, file_path: Path, index_type: str) -> PNEIndexData:
        """
        Load PNE index file (start or last).
        
        Args:
            file_path: Path to index file
            index_type: Either 'start' or 'last'
            
        Returns:
            PNEIndexData object containing parsed index data
        """
        try:
            # Read CSV with no header
            data = pd.read_csv(file_path, header=None)
            
            # Expected columns: fileIndex, resultIndex, open_year, open_month, open_day
            expected_columns = ['fileIndex', 'resultIndex', 'open_year', 'open_month', 'open_day']
            if len(data.columns) >= len(expected_columns):
                data.columns = expected_columns[:len(data.columns)]
            
            # Convert year to full year (24 -> 2024)
            if 'open_year' in data.columns:
                data['open_year_full'] = data['open_year'].apply(lambda x: x + 2000 if x < 100 else x)
                
                # Create datetime from year, month, day
                data['open_date'] = pd.to_datetime(
                    data[['open_year_full', 'open_month', 'open_day']].rename(columns={
                        'open_year_full': 'year', 'open_month': 'month', 'open_day': 'day'
                    }), errors='coerce'
                )
            
            metadata = {
                'file_name': file_path.name,
                'index_type': index_type,
                'total_entries': len(data),
                'file_index_range': (data['fileIndex'].min(), data['fileIndex'].max()) if 'fileIndex' in data else None,
                'date_range': (data['open_date'].min(), data['open_date'].max()) if 'open_date' in data else None
            }
            
            return PNEIndexData(data=data, metadata=metadata, file_path=file_path, index_type=index_type)
            
        except Exception as e:
            logger.error(f"Error loading PNE index file {file_path}: {e}")
            raise
    
    def load_channel_directory(self, channel_dir: Path) -> PNEChannelData:
        """
        Load all data from a PNE channel directory.
        
        Args:
            channel_dir: Path to channel directory
            
        Returns:
            PNEChannelData object containing all loaded data
        """
        restore_dir = channel_dir / 'Restore'
        if not restore_dir.exists():
            raise FileNotFoundError(f"Restore directory not found: {restore_dir}")
        
        test_files = []
        start_index = None
        last_index = None
        
        # Load test data files
        test_file_pattern = re.compile(r'ch\d+_SaveData\d+\.csv')
        test_file_paths = [f for f in restore_dir.iterdir() 
                          if f.is_file() and test_file_pattern.match(f.name)]
        test_file_paths.sort(key=self._extract_file_index)
        
        for file_path in test_file_paths:
            try:
                test_data = self._load_test_file(file_path)
                test_files.append(test_data)
            except Exception as e:
                logger.error(f"Failed to load test file {file_path}: {e}")
                continue
        
        # Load index files
        start_index_file = restore_dir / 'savingFileIndex_start.csv'
        if start_index_file.exists():
            try:
                start_index = self._load_index_file(start_index_file, 'start')
            except Exception as e:
                logger.error(f"Failed to load start index file: {e}")
        
        last_index_file = restore_dir / 'savingFileIndex_last.csv'
        if last_index_file.exists():
            try:
                last_index = self._load_index_file(last_index_file, 'last')
            except Exception as e:
                logger.error(f"Failed to load last index file: {e}")
        
        # Create channel metadata
        channel_info = self._parse_channel_name(channel_dir)
        metadata = {
            'channel_info': channel_info,
            'test_file_count': len(test_files),
            'has_start_index': start_index is not None,
            'has_last_index': last_index is not None,
            'total_records': sum(tf.metadata['total_records'] for tf in test_files)
        }
        
        # Add data range information if available
        if test_files:
            all_date_ranges = [tf.metadata['date_range'] for tf in test_files 
                              if tf.metadata['date_range'] and tf.metadata['date_range'][0] is not None]
            if all_date_ranges:
                all_start_dates = [dr[0] for dr in all_date_ranges]
                all_end_dates = [dr[1] for dr in all_date_ranges]
                metadata['overall_date_range'] = (min(all_start_dates), max(all_end_dates))
        
        return PNEChannelData(
            test_files=test_files,
            start_index=start_index,
            last_index=last_index,
            metadata=metadata,
            channel_path=channel_dir
        )
    
    def load_all_channels(self) -> Dict[str, PNEChannelData]:
        """
        Load data from all channel directories.
        
        Returns:
            Dictionary with channel names as keys, containing all loaded data
        """
        all_data = {}
        
        # Get all channel directories
        channel_dirs = [d for d in self.data_path.iterdir() 
                       if d.is_dir() and 'Ch' in d.name]
        channel_dirs.sort(key=lambda x: x.name)
        
        for channel_dir in channel_dirs:
            logger.info(f"Loading channel: {channel_dir.name}")
            try:
                channel_data = self.load_channel_directory(channel_dir)
                all_data[channel_dir.name] = channel_data
                
                # Log summary
                test_count = len(channel_data.test_files)
                total_records = channel_data.metadata['total_records']
                logger.info(f"Loaded {test_count} test files with {total_records} total records")
                
            except Exception as e:
                logger.error(f"Failed to load channel {channel_dir}: {e}")
                continue
        
        return all_data
    
    def get_combined_data(self, channels: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Get combined data from specified channels or all channels.
        
        Args:
            channels: List of channel names to include. If None, include all.
            
        Returns:
            Combined DataFrame with data from all specified channels
        """
        all_data = self.load_all_channels()
        
        if channels is None:
            channels = list(all_data.keys())
        
        combined_dfs = []
        
        for channel_name in channels:
            if channel_name not in all_data:
                logger.warning(f"Channel {channel_name} not found")
                continue
            
            channel_data = all_data[channel_name]
            
            # Combine all test files for this channel
            channel_dfs = []
            for test_file in channel_data.test_files:
                df = test_file.data.copy()
                df['Channel'] = channel_name
                df['File_index'] = test_file.file_index
                channel_dfs.append(df)
            
            if channel_dfs:
                channel_combined = pd.concat(channel_dfs, ignore_index=True)
                combined_dfs.append(channel_combined)
        
        if combined_dfs:
            return pd.concat(combined_dfs, ignore_index=True)
        else:
            return pd.DataFrame()
    
    def get_summary_statistics(self) -> Dict:
        """
        Get summary statistics for all loaded data.
        
        Returns:
            Dictionary containing summary statistics
        """
        all_data = self.load_all_channels()
        
        summary = {
            'total_channels': len(all_data),
            'total_test_files': sum(len(data.test_files) for data in all_data.values()),
            'total_records': sum(data.metadata['total_records'] for data in all_data.values()),
            'channels_with_start_index': sum(1 for data in all_data.values() 
                                            if data.metadata['has_start_index']),
            'channels_with_last_index': sum(1 for data in all_data.values() 
                                           if data.metadata['has_last_index']),
            'channel_details': {}
        }
        
        for channel_name, channel_data in all_data.items():
            detail = {
                'test_files': len(channel_data.test_files),
                'total_records': channel_data.metadata['total_records'],
                'has_start_index': channel_data.metadata['has_start_index'],
                'has_last_index': channel_data.metadata['has_last_index'],
                'channel_info': channel_data.metadata['channel_info']
            }
            
            # Add date range if available
            if 'overall_date_range' in channel_data.metadata:
                detail['date_range'] = channel_data.metadata['overall_date_range']
            
            summary['channel_details'][channel_name] = detail
        
        return summary


def create_pne_loader(data_path: Union[str, Path]) -> PNEDataLoader:
    """
    Factory function to create a PNEDataLoader instance.
    
    Args:
        data_path: Path to PNE data directory
        
    Returns:
        Configured PNEDataLoader instance
    """
    return PNEDataLoader(data_path)


# Example usage and validation
if __name__ == "__main__":
    import sys
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
    
    # Example usage
    if len(sys.argv) > 1:
        data_path = sys.argv[1]
        
        try:
            loader = create_pne_loader(data_path)
            summary = loader.get_summary_statistics()
            
            print(f"Data Summary:")
            print(f"Total Channels: {summary['total_channels']}")
            print(f"Total Test Files: {summary['total_test_files']}")
            print(f"Total Records: {summary['total_records']:,}")
            print(f"Channels with Start Index: {summary['channels_with_start_index']}")
            print(f"Channels with Last Index: {summary['channels_with_last_index']}")
            
            # Show combined data sample
            combined_data = loader.get_combined_data()
            if not combined_data.empty:
                print(f"\nCombined Data Shape: {combined_data.shape}")
                print(f"Columns: {list(combined_data.columns)}")
                print("\nFirst 5 rows:")
                print(combined_data.head())
            
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
    else:
        print("Usage: python pne_loader.py <data_path>")
        print("Example: python pne_loader.py /path/to/pne/data")