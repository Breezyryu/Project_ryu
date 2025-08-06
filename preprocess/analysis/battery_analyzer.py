"""
Battery Data Analyzer with Sequential Thinking Integration

Advanced analysis tools for battery testing data including:
- Data quality validation
- Anomaly detection
- Performance metrics calculation
- Degradation analysis
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging
from scipy import stats
from scipy.signal import find_peaks, savgol_filter
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

@dataclass
class AnalysisResult:
    """Container for analysis results."""
    analysis_type: str
    results: Dict[str, Any]
    metadata: Dict[str, Any]
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            'analysis_type': self.analysis_type,
            'results': self.results,
            'metadata': self.metadata,
            'timestamp': self.timestamp.isoformat()
        }

@dataclass
class ValidationResult:
    """Container for data validation results."""
    is_valid: bool
    issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    quality_score: float  # 0-100 scale
    
    def summary(self) -> str:
        """Get summary of validation results."""
        status = "VALID" if self.is_valid else "INVALID"
        return f"Status: {status}, Quality Score: {self.quality_score:.1f}%, Issues: {len(self.issues)}, Warnings: {len(self.warnings)}"

class BatteryDataAnalyzer:
    """
    Comprehensive battery data analyzer with sequential thinking approach.
    
    Implements systematic analysis workflow:
    1. Data Quality Validation
    2. Basic Statistical Analysis
    3. Electrochemical Analysis
    4. Anomaly Detection
    5. Performance Metrics
    6. Degradation Analysis
    """
    
    def __init__(self, data: pd.DataFrame, format_type: str = 'unknown'):
        """
        Initialize battery data analyzer.
        
        Args:
            data: Standardized battery data DataFrame
            format_type: Original data format type
        """
        self.data = data.copy()
        self.format_type = format_type
        self.analysis_results = {}
        self.validation_result = None
        
        # Configure analysis parameters
        self.config = {
            'voltage_limits': (2.5, 4.5),  # V
            'current_limits': (-10.0, 10.0),  # A
            'temperature_limits': (-20, 80),  # °C
            'time_gap_threshold': timedelta(hours=1),
            'outlier_threshold': 3.0,  # Standard deviations
            'min_cycle_points': 10
        }
        
        logger.info(f"Initialized BatteryDataAnalyzer with {len(data)} records")
    
    def validate_data_quality(self) -> ValidationResult:
        """
        Comprehensive data quality validation using sequential analysis.
        
        Returns:
            ValidationResult with detailed quality assessment
        """
        logger.info("Starting data quality validation...")
        
        issues = []
        warnings = []
        recommendations = []
        quality_metrics = {}
        
        # Step 1: Basic data integrity checks
        if self.data.empty:
            issues.append("Dataset is empty")
            return ValidationResult(False, issues, warnings, recommendations, 0.0)
        
        # Step 2: Required columns validation
        required_columns = ['Datetime', 'Voltage_V', 'Current_A']
        missing_columns = [col for col in required_columns if col not in self.data.columns]
        
        if missing_columns:
            issues.append(f"Missing required columns: {missing_columns}")
        
        quality_metrics['column_completeness'] = (len(required_columns) - len(missing_columns)) / len(required_columns) * 100
        
        # Step 3: Data completeness analysis
        total_records = len(self.data)
        completeness_scores = {}
        
        for col in self.data.columns:
            non_null_count = self.data[col].count()
            completeness_scores[col] = (non_null_count / total_records) * 100
            
            if completeness_scores[col] < 90 and col in required_columns:
                issues.append(f"Column '{col}' has {100-completeness_scores[col]:.1f}% missing data")
            elif completeness_scores[col] < 50:
                warnings.append(f"Column '{col}' has {100-completeness_scores[col]:.1f}% missing data")
        
        quality_metrics['avg_completeness'] = np.mean(list(completeness_scores.values()))
        
        # Step 4: Value range validation
        if 'Voltage_V' in self.data.columns:
            voltage_data = self.data['Voltage_V'].dropna()
            voltage_min, voltage_max = self.config['voltage_limits']
            
            out_of_range_voltage = ((voltage_data < voltage_min) | (voltage_data > voltage_max)).sum()
            if out_of_range_voltage > 0:
                pct_out_range = (out_of_range_voltage / len(voltage_data)) * 100
                if pct_out_range > 1:
                    issues.append(f"Voltage out of range ({voltage_min}-{voltage_max}V): {pct_out_range:.1f}%")
                else:
                    warnings.append(f"Voltage out of range: {out_of_range_voltage} points ({pct_out_range:.2f}%)")
            
            quality_metrics['voltage_range_compliance'] = ((voltage_data >= voltage_min) & (voltage_data <= voltage_max)).mean() * 100
        
        # Step 5: Temporal consistency validation
        if 'Datetime' in self.data.columns:
            datetime_data = pd.to_datetime(self.data['Datetime'], errors='coerce')
            
            # Check for null datetimes
            null_datetimes = datetime_data.isnull().sum()
            if null_datetimes > 0:
                warnings.append(f"Invalid datetime values: {null_datetimes}")
            
            # Check temporal ordering
            valid_datetimes = datetime_data.dropna().sort_values()
            if len(valid_datetimes) > 1:
                # Check for large time gaps
                time_diffs = valid_datetimes.diff().dropna()
                large_gaps = (time_diffs > self.config['time_gap_threshold']).sum()
                
                if large_gaps > 0:
                    warnings.append(f"Large time gaps detected: {large_gaps} instances")
                
                # Check for duplicate timestamps
                duplicate_times = valid_datetimes.duplicated().sum()
                if duplicate_times > 0:
                    warnings.append(f"Duplicate timestamps: {duplicate_times}")
                
                quality_metrics['temporal_consistency'] = max(0, 100 - (large_gaps + duplicate_times) / len(valid_datetimes) * 100)
        
        # Step 6: Statistical outlier detection
        numeric_columns = self.data.select_dtypes(include=[np.number]).columns
        outlier_counts = {}
        
        for col in numeric_columns:
            if col in ['Voltage_V', 'Current_A', 'Temperature_C']:
                data_col = self.data[col].dropna()
                if len(data_col) > 0:
                    z_scores = np.abs(stats.zscore(data_col))
                    outliers = (z_scores > self.config['outlier_threshold']).sum()
                    outlier_counts[col] = outliers
                    
                    if outliers > len(data_col) * 0.05:  # More than 5% outliers
                        warnings.append(f"High outlier count in {col}: {outliers} ({outliers/len(data_col)*100:.1f}%)")
        
        quality_metrics['outlier_rate'] = np.mean(list(outlier_counts.values())) / len(self.data) * 100 if outlier_counts else 0
        
        # Step 7: Generate recommendations
        if quality_metrics.get('avg_completeness', 0) < 95:
            recommendations.append("Consider data imputation or filtering for missing values")
        
        if quality_metrics.get('outlier_rate', 0) > 2:
            recommendations.append("Investigate and potentially filter outliers")
        
        if len(warnings) > 5:
            recommendations.append("Multiple data quality issues detected - recommend thorough data cleaning")
        
        # Step 8: Calculate overall quality score
        score_components = [
            quality_metrics.get('column_completeness', 0) * 0.3,
            quality_metrics.get('avg_completeness', 0) * 0.3,
            quality_metrics.get('voltage_range_compliance', 100) * 0.2,
            quality_metrics.get('temporal_consistency', 100) * 0.1,
            max(0, 100 - quality_metrics.get('outlier_rate', 0) * 10) * 0.1
        ]
        
        overall_quality_score = sum(score_components)
        
        # Determine validity
        is_valid = (len(issues) == 0 and overall_quality_score >= 70)
        
        self.validation_result = ValidationResult(
            is_valid=is_valid,
            issues=issues,
            warnings=warnings,
            recommendations=recommendations,
            quality_score=overall_quality_score
        )
        
        logger.info(f"Data validation complete: {self.validation_result.summary()}")
        return self.validation_result
    
    def analyze_basic_statistics(self) -> AnalysisResult:
        """
        Calculate basic statistical measures for battery data.
        
        Returns:
            AnalysisResult with statistical summary
        """
        logger.info("Calculating basic statistics...")
        
        numeric_columns = self.data.select_dtypes(include=[np.number]).columns
        stats_results = {}
        
        # Overall statistics
        stats_results['general'] = {
            'total_records': len(self.data),
            'time_span_hours': None,
            'unique_cycles': None
        }
        
        # Time span calculation
        if 'Datetime' in self.data.columns:
            datetime_data = pd.to_datetime(self.data['Datetime'], errors='coerce').dropna()
            if len(datetime_data) > 1:
                time_span = datetime_data.max() - datetime_data.min()
                stats_results['general']['time_span_hours'] = time_span.total_seconds() / 3600
        
        # Cycle information
        if 'Cycle' in self.data.columns:
            stats_results['general']['unique_cycles'] = self.data['Cycle'].nunique()
        
        # Descriptive statistics for key variables
        key_variables = ['Voltage_V', 'Current_A', 'Temperature_C']
        stats_results['descriptive'] = {}
        
        for var in key_variables:
            if var in numeric_columns:
                data_col = self.data[var].dropna()
                if len(data_col) > 0:
                    stats_results['descriptive'][var] = {
                        'count': len(data_col),
                        'mean': float(data_col.mean()),
                        'std': float(data_col.std()),
                        'min': float(data_col.min()),
                        'max': float(data_col.max()),
                        'median': float(data_col.median()),
                        'q25': float(data_col.quantile(0.25)),
                        'q75': float(data_col.quantile(0.75)),
                        'skewness': float(stats.skew(data_col)),
                        'kurtosis': float(stats.kurtosis(data_col))
                    }
        
        # Correlation analysis
        correlation_vars = [col for col in key_variables if col in numeric_columns]
        if len(correlation_vars) > 1:
            corr_matrix = self.data[correlation_vars].corr()
            stats_results['correlations'] = corr_matrix.to_dict()
        
        result = AnalysisResult(
            analysis_type='basic_statistics',
            results=stats_results,
            metadata={'method': 'descriptive_statistics', 'variables_analyzed': list(numeric_columns)},
            timestamp=datetime.now()
        )
        
        self.analysis_results['basic_statistics'] = result
        logger.info(f"Basic statistics analysis complete: {len(numeric_columns)} variables analyzed")
        return result
    
    def analyze_electrochemical_behavior(self) -> AnalysisResult:
        """
        Analyze electrochemical behavior patterns.
        
        Returns:
            AnalysisResult with electrochemical analysis
        """
        logger.info("Analyzing electrochemical behavior...")
        
        electrochem_results = {}
        
        # Voltage analysis
        if 'Voltage_V' in self.data.columns:
            voltage_data = self.data['Voltage_V'].dropna()
            
            electrochem_results['voltage_analysis'] = {
                'operating_range': {
                    'min_voltage': float(voltage_data.min()),
                    'max_voltage': float(voltage_data.max()),
                    'voltage_range': float(voltage_data.max() - voltage_data.min())
                },
                'distribution_analysis': {
                    'most_common_voltage_range': None,
                    'voltage_variability': float(voltage_data.std())
                }
            }
            
            # Find most common voltage range (binning)
            hist, bin_edges = np.histogram(voltage_data, bins=20)
            max_bin_idx = np.argmax(hist)
            most_common_range = (bin_edges[max_bin_idx], bin_edges[max_bin_idx + 1])
            electrochem_results['voltage_analysis']['distribution_analysis']['most_common_voltage_range'] = most_common_range
        
        # Current analysis
        if 'Current_A' in self.data.columns:
            current_data = self.data['Current_A'].dropna()
            
            # Identify charge/discharge phases
            charge_current = current_data[current_data > 0]
            discharge_current = current_data[current_data < 0]
            rest_current = current_data[abs(current_data) < 0.01]  # Near zero current
            
            electrochem_results['current_analysis'] = {
                'charge_statistics': {
                    'mean_charge_current': float(charge_current.mean()) if len(charge_current) > 0 else 0,
                    'max_charge_current': float(charge_current.max()) if len(charge_current) > 0 else 0,
                    'charge_duration_pct': len(charge_current) / len(current_data) * 100
                },
                'discharge_statistics': {
                    'mean_discharge_current': float(discharge_current.mean()) if len(discharge_current) > 0 else 0,
                    'max_discharge_current': float(discharge_current.min()) if len(discharge_current) > 0 else 0,
                    'discharge_duration_pct': len(discharge_current) / len(current_data) * 100
                },
                'rest_statistics': {
                    'rest_duration_pct': len(rest_current) / len(current_data) * 100
                }
            }
        
        # Cycle analysis (if cycle data available)
        if 'Cycle' in self.data.columns and 'Voltage_V' in self.data.columns:
            cycle_analysis = self._analyze_cycle_patterns()
            electrochem_results['cycle_analysis'] = cycle_analysis
        
        # Power analysis
        if 'Voltage_V' in self.data.columns and 'Current_A' in self.data.columns:
            voltage = self.data['Voltage_V'].fillna(0)
            current = self.data['Current_A'].fillna(0)
            power = voltage * current
            
            electrochem_results['power_analysis'] = {
                'max_charge_power': float(power[power > 0].max()) if (power > 0).any() else 0,
                'max_discharge_power': float(power[power < 0].min()) if (power < 0).any() else 0,
                'average_power': float(power.mean()),
                'power_variability': float(power.std())
            }
        
        result = AnalysisResult(
            analysis_type='electrochemical_behavior',
            results=electrochem_results,
            metadata={'method': 'electrochemical_analysis', 'data_format': self.format_type},
            timestamp=datetime.now()
        )
        
        self.analysis_results['electrochemical_behavior'] = result
        logger.info("Electrochemical behavior analysis complete")
        return result
    
    def _analyze_cycle_patterns(self) -> Dict[str, Any]:
        """Analyze cycling patterns in the data."""
        cycle_patterns = {}
        
        # Group data by cycle
        cycle_groups = self.data.groupby('Cycle')
        cycle_summaries = []
        
        for cycle_num, cycle_data in cycle_groups:
            if len(cycle_data) < self.config['min_cycle_points']:
                continue
            
            summary = {
                'cycle_number': cycle_num,
                'data_points': len(cycle_data),
                'duration_minutes': None,
                'voltage_range': None,
                'current_profile': None
            }
            
            # Duration calculation
            if 'Datetime' in cycle_data.columns:
                datetime_data = pd.to_datetime(cycle_data['Datetime'], errors='coerce').dropna()
                if len(datetime_data) > 1:
                    duration = datetime_data.max() - datetime_data.min()
                    summary['duration_minutes'] = duration.total_seconds() / 60
            
            # Voltage range
            if 'Voltage_V' in cycle_data.columns:
                voltage_data = cycle_data['Voltage_V'].dropna()
                if len(voltage_data) > 0:
                    summary['voltage_range'] = {
                        'min': float(voltage_data.min()),
                        'max': float(voltage_data.max()),
                        'range': float(voltage_data.max() - voltage_data.min())
                    }
            
            # Current profile identification
            if 'Current_A' in cycle_data.columns:
                current_data = cycle_data['Current_A'].dropna()
                if len(current_data) > 0:
                    pos_current = (current_data > 0.01).sum()
                    neg_current = (current_data < -0.01).sum()
                    zero_current = (abs(current_data) <= 0.01).sum()
                    
                    total_points = len(current_data)
                    summary['current_profile'] = {
                        'charge_pct': pos_current / total_points * 100,
                        'discharge_pct': neg_current / total_points * 100,
                        'rest_pct': zero_current / total_points * 100
                    }
            
            cycle_summaries.append(summary)
        
        cycle_patterns['individual_cycles'] = cycle_summaries[:10]  # Limit to first 10 cycles
        cycle_patterns['cycle_statistics'] = {
            'total_cycles_analyzed': len(cycle_summaries),
            'avg_cycle_duration_min': np.mean([c['duration_minutes'] for c in cycle_summaries 
                                             if c['duration_minutes'] is not None]) if cycle_summaries else None,
            'avg_data_points_per_cycle': np.mean([c['data_points'] for c in cycle_summaries]) if cycle_summaries else None
        }
        
        return cycle_patterns
    
    def detect_anomalies(self) -> AnalysisResult:
        """
        Detect anomalies in battery data using statistical methods.
        
        Returns:
            AnalysisResult with anomaly detection results
        """
        logger.info("Detecting anomalies...")
        
        anomaly_results = {}
        
        # Statistical outlier detection
        key_variables = ['Voltage_V', 'Current_A', 'Temperature_C']
        outlier_analysis = {}
        
        for var in key_variables:
            if var in self.data.columns:
                data_col = self.data[var].dropna()
                if len(data_col) > 0:
                    # Z-score method
                    z_scores = np.abs(stats.zscore(data_col))
                    z_outliers = z_scores > self.config['outlier_threshold']
                    
                    # IQR method
                    Q1 = data_col.quantile(0.25)
                    Q3 = data_col.quantile(0.75)
                    IQR = Q3 - Q1
                    iqr_outliers = (data_col < (Q1 - 1.5 * IQR)) | (data_col > (Q3 + 1.5 * IQR))
                    
                    outlier_analysis[var] = {
                        'z_score_outliers': int(z_outliers.sum()),
                        'z_score_outlier_pct': float(z_outliers.mean() * 100),
                        'iqr_outliers': int(iqr_outliers.sum()),
                        'iqr_outlier_pct': float(iqr_outliers.mean() * 100),
                        'outlier_indices': self.data.index[z_outliers | iqr_outliers].tolist()[:10]  # First 10 indices
                    }
        
        anomaly_results['statistical_outliers'] = outlier_analysis
        
        # Temporal anomalies
        if 'Datetime' in self.data.columns:
            temporal_anomalies = self._detect_temporal_anomalies()
            anomaly_results['temporal_anomalies'] = temporal_anomalies
        
        # Voltage jump detection
        if 'Voltage_V' in self.data.columns:
            voltage_jumps = self._detect_voltage_jumps()
            anomaly_results['voltage_jumps'] = voltage_jumps
        
        result = AnalysisResult(
            analysis_type='anomaly_detection',
            results=anomaly_results,
            metadata={'method': 'statistical_outlier_detection', 'threshold': self.config['outlier_threshold']},
            timestamp=datetime.now()
        )
        
        self.analysis_results['anomaly_detection'] = result
        logger.info("Anomaly detection complete")
        return result
    
    def _detect_temporal_anomalies(self) -> Dict[str, Any]:
        """Detect temporal anomalies in the data."""
        temporal_results = {}
        
        datetime_data = pd.to_datetime(self.data['Datetime'], errors='coerce')
        valid_datetime = datetime_data.dropna().sort_values()
        
        if len(valid_datetime) > 1:
            # Time gap analysis
            time_diffs = valid_datetime.diff().dropna()
            median_diff = time_diffs.median()
            
            # Find unusually large gaps
            large_gaps = time_diffs > (median_diff * 10)
            
            temporal_results = {
                'total_time_gaps': len(time_diffs),
                'median_time_gap_minutes': median_diff.total_seconds() / 60,
                'large_gaps_detected': int(large_gaps.sum()),
                'max_gap_hours': time_diffs.max().total_seconds() / 3600 if len(time_diffs) > 0 else 0
            }
        
        return temporal_results
    
    def _detect_voltage_jumps(self) -> Dict[str, Any]:
        """Detect sudden voltage jumps that might indicate measurement errors."""
        voltage_jump_results = {}
        
        voltage_data = self.data['Voltage_V'].dropna()
        
        if len(voltage_data) > 1:
            # Calculate voltage differences
            voltage_diff = voltage_data.diff().dropna()
            voltage_diff_abs = voltage_diff.abs()
            
            # Define jump threshold as 3 times the standard deviation
            jump_threshold = voltage_diff_abs.std() * 3
            
            # Detect jumps
            voltage_jumps = voltage_diff_abs > jump_threshold
            
            voltage_jump_results = {
                'jump_threshold_V': float(jump_threshold),
                'jumps_detected': int(voltage_jumps.sum()),
                'max_jump_V': float(voltage_diff_abs.max()),
                'jump_indices': voltage_data.index[voltage_jumps].tolist()[:10]  # First 10 indices
            }
        
        return voltage_jump_results
    
    def calculate_performance_metrics(self) -> AnalysisResult:
        """
        Calculate key battery performance metrics.
        
        Returns:
            AnalysisResult with performance metrics
        """
        logger.info("Calculating performance metrics...")
        
        performance_results = {}
        
        # Capacity analysis (if capacity data available)
        if 'Chg_Capacity_mAh' in self.data.columns:
            capacity_metrics = self._calculate_capacity_metrics()
            performance_results['capacity_metrics'] = capacity_metrics
        
        # Energy analysis
        if all(col in self.data.columns for col in ['Voltage_V', 'Current_A', 'Datetime']):
            energy_metrics = self._calculate_energy_metrics()
            performance_results['energy_metrics'] = energy_metrics
        
        # Efficiency analysis
        if all(col in self.data.columns for col in ['Chg_Capacity_mAh', 'Dchg_Capacity_mAh']):
            efficiency_metrics = self._calculate_efficiency_metrics()
            performance_results['efficiency_metrics'] = efficiency_metrics
        
        # Temperature performance
        if 'Temperature_C' in self.data.columns:
            temperature_metrics = self._calculate_temperature_performance()
            performance_results['temperature_performance'] = temperature_metrics
        
        result = AnalysisResult(
            analysis_type='performance_metrics',
            results=performance_results,
            metadata={'method': 'battery_performance_calculation'},
            timestamp=datetime.now()
        )
        
        self.analysis_results['performance_metrics'] = result
        logger.info("Performance metrics calculation complete")
        return result
    
    def _calculate_capacity_metrics(self) -> Dict[str, Any]:
        """Calculate capacity-related performance metrics."""
        capacity_results = {}
        
        # Charge capacity analysis
        if 'Chg_Capacity_mAh' in self.data.columns:
            chg_capacity = self.data['Chg_Capacity_mAh'].dropna()
            capacity_results['charge_capacity'] = {
                'mean_mAh': float(chg_capacity.mean()),
                'std_mAh': float(chg_capacity.std()),
                'max_mAh': float(chg_capacity.max()),
                'min_mAh': float(chg_capacity.min())
            }
        
        # Discharge capacity analysis
        if 'Dchg_Capacity_mAh' in self.data.columns:
            dchg_capacity = self.data['Dchg_Capacity_mAh'].dropna()
            capacity_results['discharge_capacity'] = {
                'mean_mAh': float(dchg_capacity.mean()),
                'std_mAh': float(dchg_capacity.std()),
                'max_mAh': float(dchg_capacity.max()),
                'min_mAh': float(dchg_capacity.min())
            }
        
        return capacity_results
    
    def _calculate_energy_metrics(self) -> Dict[str, Any]:
        """Calculate energy-related metrics."""
        energy_results = {}
        
        # Calculate instantaneous power
        voltage = self.data['Voltage_V'].fillna(0)
        current = self.data['Current_A'].fillna(0)
        power = voltage * current
        
        # Basic energy statistics
        energy_results['power_statistics'] = {
            'mean_power_W': float(power.mean()),
            'max_power_W': float(power.max()),
            'min_power_W': float(power.min()),
            'power_range_W': float(power.max() - power.min())
        }
        
        return energy_results
    
    def _calculate_efficiency_metrics(self) -> Dict[str, Any]:
        """Calculate efficiency metrics."""
        efficiency_results = {}
        
        chg_capacity = self.data['Chg_Capacity_mAh'].dropna()
        dchg_capacity = self.data['Dchg_Capacity_mAh'].dropna()
        
        if len(chg_capacity) > 0 and len(dchg_capacity) > 0:
            # Coulombic efficiency (assuming paired charge/discharge data)
            if len(chg_capacity) == len(dchg_capacity):
                coulombic_efficiency = (dchg_capacity / chg_capacity * 100).dropna()
                
                efficiency_results['coulombic_efficiency'] = {
                    'mean_pct': float(coulombic_efficiency.mean()),
                    'std_pct': float(coulombic_efficiency.std()),
                    'min_pct': float(coulombic_efficiency.min()),
                    'max_pct': float(coulombic_efficiency.max())
                }
        
        return efficiency_results
    
    def _calculate_temperature_performance(self) -> Dict[str, Any]:
        """Calculate temperature-related performance metrics."""
        temp_results = {}
        
        temperature = self.data['Temperature_C'].dropna()
        
        if len(temperature) > 0:
            temp_results['temperature_statistics'] = {
                'mean_C': float(temperature.mean()),
                'std_C': float(temperature.std()),
                'min_C': float(temperature.min()),
                'max_C': float(temperature.max()),
                'range_C': float(temperature.max() - temperature.min())
            }
            
            # Temperature stability analysis
            temp_diff = temperature.diff().dropna().abs()
            temp_results['temperature_stability'] = {
                'mean_variation_C': float(temp_diff.mean()),
                'max_variation_C': float(temp_diff.max()),
                'stability_score': max(0, 100 - temp_diff.mean() * 10)  # Arbitrary scoring
            }
        
        return temp_results
    
    def run_comprehensive_analysis(self) -> Dict[str, AnalysisResult]:
        """
        Run complete sequential analysis pipeline.
        
        Returns:
            Dictionary of all analysis results
        """
        logger.info("Starting comprehensive analysis pipeline...")
        
        # Step 1: Data Quality Validation
        self.validate_data_quality()
        
        if not self.validation_result.is_valid:
            logger.warning("Data validation failed - proceeding with analysis but results may be unreliable")
        
        # Step 2: Basic Statistical Analysis
        self.analyze_basic_statistics()
        
        # Step 3: Electrochemical Analysis
        self.analyze_electrochemical_behavior()
        
        # Step 4: Anomaly Detection
        self.detect_anomalies()
        
        # Step 5: Performance Metrics
        self.calculate_performance_metrics()
        
        logger.info("Comprehensive analysis pipeline complete")
        return self.analysis_results
    
    def generate_analysis_report(self) -> str:
        """
        Generate a comprehensive analysis report.
        
        Returns:
            Formatted text report of all analyses
        """
        if not self.analysis_results:
            self.run_comprehensive_analysis()
        
        report_lines = [
            "="*60,
            "BATTERY DATA ANALYSIS REPORT",
            "="*60,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Data Format: {self.format_type}",
            f"Total Records: {len(self.data):,}",
            ""
        ]
        
        # Data Quality Section
        if self.validation_result:
            report_lines.extend([
                "DATA QUALITY ASSESSMENT",
                "-"*30,
                f"Overall Status: {'VALID' if self.validation_result.is_valid else 'INVALID'}",
                f"Quality Score: {self.validation_result.quality_score:.1f}%",
                f"Issues Found: {len(self.validation_result.issues)}",
                f"Warnings: {len(self.validation_result.warnings)}",
                ""
            ])
            
            if self.validation_result.issues:
                report_lines.append("Critical Issues:")
                for issue in self.validation_result.issues:
                    report_lines.append(f"  • {issue}")
                report_lines.append("")
        
        # Add results from each analysis
        for analysis_name, result in self.analysis_results.items():
            report_lines.extend([
                f"{analysis_name.upper().replace('_', ' ')}",
                "-" * 30
            ])
            
            # Add key findings based on analysis type
            if analysis_name == 'basic_statistics':
                stats = result.results
                report_lines.append(f"Time Span: {stats['general'].get('time_span_hours', 'N/A')} hours")
                report_lines.append(f"Unique Cycles: {stats['general'].get('unique_cycles', 'N/A')}")
                
                if 'descriptive' in stats:
                    for var, var_stats in stats['descriptive'].items():
                        report_lines.append(f"{var}: Mean={var_stats['mean']:.3f}, Std={var_stats['std']:.3f}")
            
            elif analysis_name == 'anomaly_detection':
                anomalies = result.results
                if 'statistical_outliers' in anomalies:
                    total_outliers = sum(var_data['z_score_outliers'] 
                                       for var_data in anomalies['statistical_outliers'].values())
                    report_lines.append(f"Total Statistical Outliers: {total_outliers}")
            
            report_lines.append("")
        
        return "\n".join(report_lines)


def create_battery_analyzer(data: pd.DataFrame, format_type: str = 'unknown') -> BatteryDataAnalyzer:
    """
    Factory function to create a BatteryDataAnalyzer instance.
    
    Args:
        data: Standardized battery data DataFrame
        format_type: Original data format type
        
    Returns:
        Configured BatteryDataAnalyzer instance
    """
    return BatteryDataAnalyzer(data, format_type)


# Example usage and testing
if __name__ == "__main__":
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
    
    # Add some outliers
    sample_data.loc[100:102, 'Voltage_V'] = 5.0  # Voltage outliers
    sample_data.loc[500:502, 'Current_A'] = 10.0  # Current outliers
    
    try:
        # Create analyzer
        analyzer = create_battery_analyzer(sample_data, 'test')
        
        # Run comprehensive analysis
        results = analyzer.run_comprehensive_analysis()
        
        print("Analysis Results Summary:")
        print(f"Number of analyses completed: {len(results)}")
        
        # Generate and print report
        report = analyzer.generate_analysis_report()
        print("\n" + report)
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        sys.exit(1)