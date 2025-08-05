"""
Toyo Battery Data Processor Module

This module provides functionality to clean, process, and analyze battery 
experimental data loaded in Toyo format.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
import logging
from datetime import datetime, timedelta
import warnings

logger = logging.getLogger(__name__)


class ToyoDataProcessor:
    """
    Data processor for Toyo format battery experimental data.
    
    Handles data cleaning, type conversion, feature extraction, and analysis
    for battery life prediction preprocessing.
    """
    
    def __init__(self):
        """Initialize the Toyo data processor."""
        self.processed_data = {}
        self.processed_capacity = {}
        self.summary_stats = {}
    
    def clean_and_convert_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and convert raw Toyo data to proper types.
        
        Args:
            df: Raw DataFrame from ToyoDataLoader
            
        Returns:
            Cleaned DataFrame with proper data types
        """
        if df.empty:
            logger.warning("Empty DataFrame provided for cleaning")
            return df
        
        df_clean = df.copy()
        
        try:
            # Create datetime column
            if 'Date' in df_clean.columns and 'Time' in df_clean.columns:
                df_clean['datetime'] = pd.to_datetime(
                    df_clean['Date'] + ' ' + df_clean['Time'], 
                    format='%Y/%m/%d %H:%M:%S',
                    errors='coerce'
                )
            
            # Convert numeric columns
            numeric_columns = {
                'PassTime[Sec]': 'pass_time_sec',
                'Voltage[V]': 'voltage_v',
                'Current[mA]': 'current_ma',
                'Temp1[Deg]': 'temperature_deg',
                'Condition': 'condition',
                'Mode': 'mode',
                'Cycle': 'cycle',
                'TotlCycle': 'total_cycle',
                'PassedDate': 'passed_date'
            }
            
            for old_col, new_col in numeric_columns.items():
                if old_col in df_clean.columns:
                    # Remove '+' signs and convert to numeric
                    values = df_clean[old_col].astype(str).str.replace('+', '').str.strip()
                    df_clean[new_col] = pd.to_numeric(values, errors='coerce')
            
            # Convert current from mA to A
            if 'current_ma' in df_clean.columns:
                df_clean['current_a'] = df_clean['current_ma'] / 1000.0
            
            # Calculate power (W = V * A)
            if 'voltage_v' in df_clean.columns and 'current_a' in df_clean.columns:
                df_clean['power_w'] = df_clean['voltage_v'] * df_clean['current_a']
            
            # Sort by datetime if available
            if 'datetime' in df_clean.columns:
                df_clean = df_clean.sort_values('datetime').reset_index(drop=True)
            
            logger.info(f"Cleaned data: {len(df_clean)} records")
            
        except Exception as e:
            logger.error(f"Error during data cleaning: {e}")
            return df
        
        return df_clean
    
    def clean_capacity_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and convert capacity log data.
        
        Args:
            df: Raw capacity DataFrame
            
        Returns:
            Cleaned capacity DataFrame
        """
        if df.empty:
            return df
        
        df_clean = df.copy()
        
        try:
            # Create datetime column
            if 'Date' in df_clean.columns and 'Time' in df_clean.columns:
                df_clean['datetime'] = pd.to_datetime(
                    df_clean['Date'] + ' ' + df_clean['Time'], 
                    format='%Y/%m/%d %H:%M:%S',
                    errors='coerce'
                )
            
            # Convert numeric columns
            numeric_columns = {
                'Condition': 'condition',
                'Mode': 'mode', 
                'Cycle': 'cycle',
                'TotlCycle': 'total_cycle',
                'Cap[mAh]': 'capacity_mah',
                'Pow[mWh]': 'power_mwh',
                'AveVolt[V]': 'avg_voltage_v',
                'PeakVolt[V]': 'peak_voltage_v',
                'PeakTemp[Deg]': 'peak_temp_deg',
                'Ocv': 'ocv_v',
                'DchCycle': 'discharge_cycle',
                'PassedDate': 'passed_date'
            }
            
            for old_col, new_col in numeric_columns.items():
                if old_col in df_clean.columns:
                    values = df_clean[old_col].astype(str).str.replace('+', '').str.strip()
                    values = values.replace('', np.nan)
                    df_clean[new_col] = pd.to_numeric(values, errors='coerce')
            
            # Parse time columns
            time_columns = ['PassTime', 'TotlPassTime']
            for col in time_columns:
                if col in df_clean.columns:
                    df_clean[f"{col.lower()}_seconds"] = df_clean[col].apply(
                        self._parse_time_to_seconds
                    )
            
            # Convert capacity from mAh to Ah
            if 'capacity_mah' in df_clean.columns:
                df_clean['capacity_ah'] = df_clean['capacity_mah'] / 1000.0
            
            # Sort by datetime and cycle
            if 'datetime' in df_clean.columns:
                df_clean = df_clean.sort_values(['datetime', 'cycle']).reset_index(drop=True)
            
            logger.info(f"Cleaned capacity data: {len(df_clean)} records")
            
        except Exception as e:
            logger.error(f"Error during capacity data cleaning: {e}")
            
        return df_clean
    
    def _parse_time_to_seconds(self, time_str: str) -> Optional[float]:
        """
        Parse time string (HH:MM:SS) to seconds.
        
        Args:
            time_str: Time string in HH:MM:SS format
            
        Returns:
            Time in seconds or None if parsing fails
        """
        try:
            if pd.isna(time_str) or time_str == '':
                return None
            
            time_str = str(time_str).strip()
            parts = time_str.split(':')
            
            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
            
        except Exception as e:
            logger.debug(f"Failed to parse time string '{time_str}': {e}")
        
        return None
    
    def extract_charge_discharge_cycles(self, df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Extract and separate charge and discharge cycles.
        
        Args:
            df: Cleaned battery data DataFrame
            
        Returns:
            Dictionary with 'charge' and 'discharge' DataFrames
        """
        cycles = {'charge': pd.DataFrame(), 'discharge': pd.DataFrame()}
        
        if df.empty or 'current_a' not in df.columns:
            logger.warning("Cannot extract cycles: missing current data")
            return cycles
        
        try:
            # Separate charge (positive current) and discharge (negative current)
            charge_mask = df['current_a'] > 0.001  # Small threshold to avoid noise
            discharge_mask = df['current_a'] < -0.001
            
            cycles['charge'] = df[charge_mask].copy()
            cycles['discharge'] = df[discharge_mask].copy()
            
            logger.info(f"Extracted {len(cycles['charge'])} charge points, "
                       f"{len(cycles['discharge'])} discharge points")
            
        except Exception as e:
            logger.error(f"Error extracting charge/discharge cycles: {e}")
        
        return cycles
    
    def calculate_capacity_fade(self, capacity_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate capacity fade over cycles.
        
        Args:
            capacity_df: Cleaned capacity DataFrame
            
        Returns:
            DataFrame with capacity fade analysis
        """
        if capacity_df.empty or 'capacity_ah' not in capacity_df.columns:
            logger.warning("Cannot calculate capacity fade: missing data")
            return pd.DataFrame()
        
        try:
            fade_df = capacity_df.copy()
            
            # Get discharge cycles only (typically condition = 2)
            discharge_cycles = fade_df[fade_df['condition'] == 2].copy()
            
            if discharge_cycles.empty:
                logger.warning("No discharge cycles found for capacity fade calculation")
                return pd.DataFrame()
            
            # Sort by cycle number
            discharge_cycles = discharge_cycles.sort_values('cycle').reset_index(drop=True)
            
            # Calculate capacity fade
            initial_capacity = discharge_cycles['capacity_ah'].iloc[0]
            discharge_cycles['capacity_retention'] = (
                discharge_cycles['capacity_ah'] / initial_capacity * 100
            )
            discharge_cycles['capacity_fade'] = (
                100 - discharge_cycles['capacity_retention']
            )
            
            # Calculate cycle-to-cycle fade rate
            discharge_cycles['fade_rate'] = discharge_cycles['capacity_fade'].diff()
            
            logger.info(f"Calculated capacity fade for {len(discharge_cycles)} cycles")
            
            return discharge_cycles
            
        except Exception as e:
            logger.error(f"Error calculating capacity fade: {e}")
            return pd.DataFrame()
    
    def extract_voltage_curves(self, df: pd.DataFrame) -> Dict[int, pd.DataFrame]:
        """
        Extract voltage curves for each cycle.
        
        Args:
            df: Cleaned battery data DataFrame
            
        Returns:
            Dictionary mapping cycle numbers to voltage curve DataFrames
        """
        curves = {}
        
        if df.empty or 'cycle' not in df.columns or 'voltage_v' not in df.columns:
            logger.warning("Cannot extract voltage curves: missing data")
            return curves
        
        try:
            # Group by cycle
            for cycle_num in df['cycle'].unique():
                if pd.isna(cycle_num):
                    continue
                
                cycle_data = df[df['cycle'] == cycle_num].copy()
                
                if not cycle_data.empty:
                    # Sort by time within cycle
                    if 'datetime' in cycle_data.columns:
                        cycle_data = cycle_data.sort_values('datetime')
                    elif 'pass_time_sec' in cycle_data.columns:
                        cycle_data = cycle_data.sort_values('pass_time_sec')
                    
                    curves[int(cycle_num)] = cycle_data
            
            logger.info(f"Extracted voltage curves for {len(curves)} cycles")
            
        except Exception as e:
            logger.error(f"Error extracting voltage curves: {e}")
        
        return curves
    
    def calculate_energy_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate energy-related metrics for each cycle.
        
        Args:
            df: Cleaned battery data DataFrame
            
        Returns:
            DataFrame with energy metrics per cycle
        """
        if df.empty:
            return pd.DataFrame()
        
        try:
            metrics = []
            
            # Group by cycle
            for cycle_num in df['cycle'].unique():
                if pd.isna(cycle_num):
                    continue
                
                cycle_data = df[df['cycle'] == cycle_num].copy()
                
                if cycle_data.empty:
                    continue
                
                # Calculate metrics for this cycle
                metric = {
                    'cycle': int(cycle_num),
                    'channel': cycle_data['channel'].iloc[0] if 'channel' in cycle_data.columns else None,
                    'avg_voltage': cycle_data['voltage_v'].mean() if 'voltage_v' in cycle_data.columns else None,
                    'max_voltage': cycle_data['voltage_v'].max() if 'voltage_v' in cycle_data.columns else None,
                    'min_voltage': cycle_data['voltage_v'].min() if 'voltage_v' in cycle_data.columns else None,
                    'avg_current': cycle_data['current_a'].mean() if 'current_a' in cycle_data.columns else None,
                    'max_current': cycle_data['current_a'].max() if 'current_a' in cycle_data.columns else None,
                    'min_current': cycle_data['current_a'].min() if 'current_a' in cycle_data.columns else None,
                    'avg_temperature': cycle_data['temperature_deg'].mean() if 'temperature_deg' in cycle_data.columns else None,
                    'max_temperature': cycle_data['temperature_deg'].max() if 'temperature_deg' in cycle_data.columns else None,
                    'total_time': cycle_data['pass_time_sec'].max() if 'pass_time_sec' in cycle_data.columns else None,
                    'data_points': len(cycle_data)
                }
                
                # Calculate energy if power data available
                if 'power_w' in cycle_data.columns and 'pass_time_sec' in cycle_data.columns:
                    # Simple trapezoidal integration for energy
                    time_diff = cycle_data['pass_time_sec'].diff().fillna(0)
                    energy_wh = (cycle_data['power_w'] * time_diff / 3600).sum()  # Convert to Wh
                    metric['energy_wh'] = energy_wh
                
                metrics.append(metric)
            
            metrics_df = pd.DataFrame(metrics)
            logger.info(f"Calculated energy metrics for {len(metrics_df)} cycles")
            
            return metrics_df
            
        except Exception as e:
            logger.error(f"Error calculating energy metrics: {e}")
            return pd.DataFrame()
    
    def process_channel_data(self, channel_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Process all channel data and extract features.
        
        Args:
            channel_data: Dictionary of channel DataFrames from loader
            
        Returns:
            Dictionary containing processed data and features
        """
        processed_results = {
            'cleaned_data': {},
            'charge_discharge_cycles': {},
            'voltage_curves': {},
            'energy_metrics': {},
            'summary': {}
        }
        
        for channel, df in channel_data.items():
            logger.info(f"Processing channel {channel}")
            
            try:
                # Clean data
                cleaned_df = self.clean_and_convert_data(df)
                processed_results['cleaned_data'][channel] = cleaned_df
                
                # Extract charge/discharge cycles
                cycles = self.extract_charge_discharge_cycles(cleaned_df)
                processed_results['charge_discharge_cycles'][channel] = cycles
                
                # Extract voltage curves
                curves = self.extract_voltage_curves(cleaned_df)
                processed_results['voltage_curves'][channel] = curves
                
                # Calculate energy metrics
                energy_metrics = self.calculate_energy_metrics(cleaned_df)
                processed_results['energy_metrics'][channel] = energy_metrics
                
                # Create summary
                summary = {
                    'total_records': len(cleaned_df),
                    'total_cycles': len(curves),
                    'charge_points': len(cycles['charge']),
                    'discharge_points': len(cycles['discharge']),
                    'time_span': None,
                    'voltage_range': None,
                    'current_range': None
                }
                
                if 'datetime' in cleaned_df.columns and not cleaned_df['datetime'].isna().all():
                    summary['time_span'] = (
                        cleaned_df['datetime'].max() - cleaned_df['datetime'].min()
                    ).total_seconds() / 3600  # hours
                
                if 'voltage_v' in cleaned_df.columns:
                    summary['voltage_range'] = (
                        cleaned_df['voltage_v'].min(), 
                        cleaned_df['voltage_v'].max()
                    )
                
                if 'current_a' in cleaned_df.columns:
                    summary['current_range'] = (
                        cleaned_df['current_a'].min(), 
                        cleaned_df['current_a'].max()
                    )
                
                processed_results['summary'][channel] = summary
                
                logger.info(f"Successfully processed channel {channel}")
                
            except Exception as e:
                logger.error(f"Error processing channel {channel}: {e}")
        
        return processed_results
    
    def process_capacity_data(self, capacity_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
        """
        Process capacity log data for all channels.
        
        Args:
            capacity_data: Dictionary of capacity DataFrames from loader
            
        Returns:
            Dictionary containing processed capacity data and fade analysis
        """
        processed_results = {
            'cleaned_capacity': {},
            'capacity_fade': {},
            'summary': {}
        }
        
        for channel, df in capacity_data.items():
            logger.info(f"Processing capacity data for channel {channel}")
            
            try:
                # Clean capacity data
                cleaned_df = self.clean_capacity_data(df)
                processed_results['cleaned_capacity'][channel] = cleaned_df
                
                # Calculate capacity fade
                fade_df = self.calculate_capacity_fade(cleaned_df)
                processed_results['capacity_fade'][channel] = fade_df
                
                # Create summary
                summary = {
                    'total_cycles': len(cleaned_df),
                    'discharge_cycles': len(fade_df),
                    'initial_capacity': None,
                    'final_capacity': None,
                    'total_fade': None,
                    'avg_fade_rate': None
                }
                
                if not fade_df.empty and 'capacity_ah' in fade_df.columns:
                    summary['initial_capacity'] = fade_df['capacity_ah'].iloc[0]
                    summary['final_capacity'] = fade_df['capacity_ah'].iloc[-1]
                    summary['total_fade'] = fade_df['capacity_fade'].iloc[-1]
                    summary['avg_fade_rate'] = fade_df['fade_rate'].mean()
                
                processed_results['summary'][channel] = summary
                
                logger.info(f"Successfully processed capacity data for channel {channel}")
                
            except Exception as e:
                logger.error(f"Error processing capacity data for channel {channel}: {e}")
        
        return processed_results