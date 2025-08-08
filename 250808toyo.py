import os
import pandas as pd
import numpy as np
from pathlib import Path
import re
from typing import Dict, List, Tuple, Optional, Union, Literal
import warnings
from tqdm import tqdm
from datetime import datetime
warnings.filterwarnings('ignore')

# 타입 정의
DataType = Literal['toyo1', 'toyo2', 'pne']

class BatteryDataPreprocessor:
    """
    리튬이온배터리 성능/수명 측정 데이터 전처리 클래스
    지원하는 장비: Toyo1, Toyo2, PNE
    """
    
    def __init__(self, data_path: str) -> None:
        """
        초기화
        
        Args:
            data_path (str): 데이터가 저장된 루트 경로
        """
        # 경로 정리 (따옴표 제거 및 정규화)
        cleaned_path = data_path.strip().strip('"').strip("'")
        self.data_path = Path(cleaned_path).resolve()  # 절대 경로로 변환
        self.channels: Dict[str, pd.DataFrame] = {}
        self.capacity_logs: Dict[str, pd.DataFrame] = {}
        self.capacity_info = ""  # 용량 정보 저장
        self.data_type: Optional[DataType] = None  # 데이터 타입
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")  # 현재 시간
        
        print(f"입력 경로: {data_path}")
        print(f"정리된 경로: {cleaned_path}")
        print(f"절대 경로: {self.data_path}")
        print(f"경로 존재 여부: {self.data_path.exists()}")
        
        if not self.data_path.exists():
            # 상세한 오류 정보 제공
            parent_path = self.data_path.parent
            print(f"부모 경로: {parent_path}")
            print(f"부모 경로 존재 여부: {parent_path.exists()}")
            
            if parent_path.exists():
                print(f"부모 경로 내용:")
                try:
                    for item in parent_path.iterdir():
                        print(f"  - {item.name} ({'디렉토리' if item.is_dir() else '파일'})")
                except Exception as e:
                    print(f"  부모 경로 내용 확인 실패: {e}")
            
            raise FileNotFoundError(f"데이터 경로가 존재하지 않습니다: {self.data_path}")
        
        # 경로에서 용량 정보 추출
        self.capacity_info = self.extract_capacity_from_path(str(self.data_path))
        
        # 데이터 타입 자동 감지
        self.data_type = self.detect_equipment_type()
        
        print(f"추출된 용량 정보: {self.capacity_info}")
        print(f"감지된 장비 타입: {self.data_type}")
        print(f"처리 시작 시간: {self.timestamp}")
    
    def extract_capacity_from_path(self, path: str) -> str:
        """
        파일 경로에서 용량 정보를 추출
        
        Args:
            path (str): 파일 경로
            
        Returns:
            str: 추출된 용량 정보 (예: "4.57mAh")
        """
        # 여러 용량 패턴을 순서대로 시도
        patterns = [
            r'(\d+(?:\.\d+)?)\s*mAh',  # 4517mAh, 4.57mAh
            r'(\d+)-(\d+)\s*mAh',      # 4-58mAh
            r'(\d+(?:\.\d+)?)\s*Ah',   # 4.5Ah (Ah 단위)
            r'(\d+(?:\.\d+)?)\s*wh',   # Wh 단위 (소문자)
            r'(\d+(?:\.\d+)?)\s*Wh',   # Wh 단위 (대문자)
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, path, re.IGNORECASE)
            if matches:
                if len(matches[0]) == 2:  # 4-58mAh 케이스
                    # 첫 번째 숫자가 정수부, 두 번째 숫자가 소수부
                    integer_part = matches[0][0]
                    decimal_part = matches[0][1]
                    capacity = f"{integer_part}.{decimal_part}mAh"
                    print(f"용량 패턴 감지 (변환): {matches[0]} -> {capacity}")
                    return capacity
                else:  # 일반적인 케이스
                    capacity_value = matches[0] if isinstance(matches[0], str) else matches[0][0]
                    
                    # Ah를 mAh로 변환
                    if 'ah' in path.lower() and 'mah' not in path.lower():
                        try:
                            capacity_float = float(capacity_value) * 1000
                            capacity = f"{capacity_float:.0f}mAh"
                        except ValueError:
                            capacity = f"{capacity_value}Ah"
                    else:
                        capacity = f"{capacity_value}mAh"
                    
                    print(f"용량 패턴 감지: {capacity}")
                    return capacity
        
        # 패턴을 찾지 못한 경우
        print("용량 정보를 찾을 수 없습니다.")
        return "unknown_capacity"
    
    def detect_equipment_type(self) -> DataType:
        """
        장비 타입을 자동 감지 (Toyo1, Toyo2, PNE)
        
        Returns:
            DataType: 감지된 장비 타입
        """
        try:
            # PNE 타입 확인 (M01Ch로 시작하는 폴더 존재)
            for item in self.data_path.iterdir():
                if item.is_dir() and item.name.startswith('M01Ch'):
                    return 'pne'
            
            # Toyo 타입 확인 (숫자 폴더 존재)
            for item in self.data_path.iterdir():
                if item.is_dir() and item.name.isdigit():
                    # 첫 번째 숫자 폴더에서 샘플 파일 확인
                    sample_folder = item
                    sample_files = [f for f in sample_folder.iterdir() if re.match(r'^\d{6}$', f.name)]
                    
                    if sample_files:
                        # 첫 번째 파일의 헤더를 확인하여 Toyo1/Toyo2 구분
                        sample_file = sample_files[0]
                        try:
                            with open(sample_file, 'r', encoding='utf-8', errors='ignore') as f:
                                lines = f.readlines()
                                if len(lines) >= 2:
                                    header = lines[1].strip()  # 두 번째 줄이 실제 헤더
                                    if 'PassedDate' in header:
                                        return 'toyo1'
                                    else:
                                        return 'toyo2'
                        except:
                            pass
            
            # 기본값은 toyo2
            return 'toyo2'
            
        except Exception as e:
            print(f"장비 타입 감지 실패: {e}")
            return 'toyo2'
    
    def detect_channels(self) -> List[str]:
        """
        데이터 경로에서 채널 폴더들을 자동 감지
        
        Returns:
            List[str]: 채널 번호 리스트
        """
        channels = []
        
        print(f"경로 스캔 중: {self.data_path}")
        
        try:
            if self.data_type == 'pne':
                # PNE의 경우 M01Ch로 시작하는 폴더들 찾기
                for item in self.data_path.iterdir():
                    if item.is_dir() and item.name.startswith('M01Ch'):
                        channels.append(item.name)
                        print(f"PNE 채널 발견: {item.name}")
            else:
                # Toyo의 경우 숫자로 된 폴더들 찾기
                for item in self.data_path.iterdir():
                    if item.is_dir() and item.name.isdigit():
                        channels.append(item.name)
                        print(f"Toyo 채널 발견: {item.name}")
                
                channels.sort(key=int)  # 숫자 순으로 정렬
                
        except Exception as e:
            print(f"디렉토리 스캔 중 오류: {e}")
            return []
        
        print(f"감지된 채널: {channels}")
        return channels
    
    def get_data_files(self, channel_path: Path) -> List[str]:
        """
        채널 폴더에서 데이터 파일들을 찾아서 정렬된 리스트로 반환
        
        Args:
            channel_path (Path): 채널 폴더 경로
            
        Returns:
            List[str]: 정렬된 데이터 파일명 리스트
        """
        data_files = []
        
        try:
            if self.data_type == 'pne':
                # PNE의 경우 Restore 폴더 내의 CSV 파일들 찾기
                restore_path = channel_path / 'Restore'
                if restore_path.exists():
                    for file in restore_path.iterdir():
                        if file.is_file() and file.suffix == '.csv':
                            # ch03_SaveData0001.csv 형태의 파일들과 기타 파일들
                            if ('SaveData' in file.name and file.name.startswith('ch')) or \
                               file.name in ['savingFileIndex_start.csv', 'savingFileIndex_last.csv', 'ch03_SaveEndData.csv']:
                                data_files.append(file.name)
                                print(f"PNE 파일 발견: {file.name}")
            else:
                # Toyo의 경우 6자리 숫자 파일들 찾기
                for file in channel_path.iterdir():
                    if file.is_file() and re.match(r'^\d{6}$', file.name):
                        data_files.append(file.name)
        except Exception as e:
            print(f"데이터 파일 스캔 중 오류 ({channel_path}): {e}")
            return []
        
        # 숫자 순으로 정렬
        if self.data_type == 'pne':
            # PNE 파일들을 특별히 정렬 (SaveData 파일들을 숫자 순으로)
            save_data_files = [f for f in data_files if 'SaveData' in f and f.startswith('ch')]
            other_files = [f for f in data_files if f not in save_data_files]
            
            # SaveData 파일들을 숫자 순으로 정렬
            save_data_files.sort(key=lambda x: int(re.search(r'SaveData(\d+)', x).group(1)) if re.search(r'SaveData(\d+)', x) else 0)
            
            data_files = save_data_files + other_files
        else:
            data_files.sort()
        
        return data_files
    
    def get_toyo_columns(self, data_type: DataType) -> List[str]:
        """
        Toyo 데이터의 컬럼 정의를 반환
        
        Args:
            data_type: 'toyo1' 또는 'toyo2'
            
        Returns:
            List[str]: 컬럼명 리스트
        """
        if data_type == 'toyo1':
            return [
                'Date', 'Time', 'PassTime_Sec', 'Voltage_V', 'Current_mA',
                'Col5', 'Col6', 'Temp1_Deg', 'Col8', 'Col9', 'Col10', 'Col11',
                'Condition', 'Mode', 'Cycle', 'TotlCycle', 'PassedDate', 'Temp1_Deg_2'
            ]
        else:  # toyo2
            return [
                'Date', 'Time', 'PassTime_Sec', 'Voltage_V', 'Current_mA',
                'Col5', 'Col6', 'Temp1_Deg', 'Col8', 'Col9', 'Col10', 'Col11',
                'Condition', 'Mode', 'Cycle', 'TotlCycle', 'Temp1_Deg_2'
            ]
    
    def get_pne_columns(self) -> List[str]:
        """
        PNE 데이터의 컬럼 정의를 반환
        
        Returns:
            List[str]: 컬럼명 리스트
        """
        return [
            'Index', 'Default', 'Step_Type', 'ChgDchg', 'Current_App_Class', 'CCCV', 'EndState',
            'Step_Count', 'Voltage_uV', 'Current_uA', 'Chg_Capacity_uAh', 'Dchg_Capacity_uAh',
            'Chg_Power_mW', 'Dchg_Power_mW', 'Chg_WattHour_Wh', 'Dchg_WattHour_Wh',
            'Repeat_Pattern_Count', 'StepTime_100s', 'TotTime_day', 'TotTime_100s', 'Impedance',
            'Temperature1', 'Temperature2', 'Temperature3', 'Temperature4', 'Col25',
            'Repeat_Count', 'TotalCycle', 'Current_Cycle', 'Average_Voltage_uV', 'Average_Current_uA',
            'Col31', 'Col32', 'Date_YYYYMMDD', 'Time_HHmmssss', 'Col35', 'Col36', 'Col37',
            'Step_Col38', 'CC_Charge_Col39', 'CV_Col40', 'Discharge_Col41', 'Col42',
            'Average_Voltage_Section', 'Cumulative_Step', 'Voltage_Max_uV', 'Voltage_Min_uV'
        ]
    
    def clean_column_name(self, col_name: str) -> str:
        """
        컬럼명을 정리 (특수문자 제거, 공백 제거)
        
        Args:
            col_name (str): 원본 컬럼명
            
        Returns:
            str: 정리된 컬럼명
        """
        # 공백 제거
        clean_name = col_name.strip()
        
        # 특수문자를 언더스코어로 변경
        clean_name = re.sub(r'[\[\]\(\)]', '', clean_name)  # 대괄호, 소괄호 제거
        clean_name = re.sub(r'[^\w]', '_', clean_name)  # 특수문자를 언더스코어로
        clean_name = re.sub(r'_+', '_', clean_name)  # 연속된 언더스코어를 하나로
        clean_name = clean_name.strip('_')  # 시작/끝 언더스코어 제거
        
        return clean_name
    

    
    def filter_meaningful_columns(self, df: pd.DataFrame, verbose: bool = False) -> Tuple[pd.DataFrame, List[str], List[str]]:
        """
        의미있는 컬럼만 선택 (Col로 시작하는 컬럼과 빈 컬럼 제거)
        
        Args:
            df (pd.DataFrame): 입력 데이터프레임
            verbose (bool): 상세 로그 출력 여부
            
        Returns:
            Tuple[pd.DataFrame, List[str], List[str]]: (필터링된 데이터프레임, 원본 컬럼 리스트, 제거된 컬럼 리스트)
        """
        original_columns = list(df.columns)
        columns_to_remove = []
        
        for col in df.columns:
            # Col로 시작하는 컬럼 제거 (Col5, Col6, Col8 등) - PNE는 제외
            if self.data_type != 'pne' and col.startswith('Col') and len(col) > 3 and col[3:].isdigit():
                columns_to_remove.append(col)
                continue
            
            # 빈 컬럼 제거 (모든 값이 NaN이거나 빈 문자열)
            try:
                # Series의 모든 값이 NaN인지 확인
                is_all_na = df[col].isna().all()
                
                # 문자열로 변환 후 빈 문자열인지 확인 (NaN 값 처리)
                str_series = df[col].astype(str)
                is_all_empty = (str_series.str.strip() == '').all() or (str_series.str.strip() == 'nan').all()
                
                if is_all_na or is_all_empty:
                    columns_to_remove.append(col)
                    continue
            except Exception as e:
                # 예외 발생 시 해당 컬럼을 안전하게 유지
                if verbose:
                    print(f"컬럼 {col} 검사 중 오류: {e}")
                continue
            
            # 숫자로만 된 컬럼명 제거 (예: '0', '1' 등) - PNE는 제외
            if self.data_type != 'pne' and col.isdigit():
                columns_to_remove.append(col)
                continue
        
        if columns_to_remove:
            df_filtered = df.drop(columns=columns_to_remove)
            if verbose:
                print(f"제거되는 컬럼: {columns_to_remove}")
        else:
            df_filtered = df.copy()
        
        return df_filtered, original_columns, columns_to_remove
    
    def find_toyo_header_line(self, file_path: Path, verbose: bool = False) -> int:
        """
        Toyo 파일에서 실제 헤더가 있는 줄 번호를 찾기
        
        Args:
            file_path (Path): 데이터 파일 경로
            verbose (bool): 상세 로그 출력 여부
            
        Returns:
            int: 헤더 줄 번호 (0부터 시작)
        """
        try:
            encodings = ['utf-8', 'cp949', 'euc-kr', 'latin1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        lines = f.readlines()
                    
                    # 각 줄을 검사하여 헤더를 찾기
                    for i, line in enumerate(lines):
                        line = line.strip()
                        if not line:  # 빈 줄 건너뛰기
                            continue
                        
                        # Date로 시작하는 줄을 헤더로 인식
                        if line.startswith('Date') and 'Time' in line and 'Voltage' in line:
                            if verbose:
                                print(f"헤더 발견 (줄 {i+1}): {line[:50]}...")
                            return i
                    
                    # 헤더를 찾지 못한 경우, 마지막으로 시도 (일반적인 패턴)
                    for i, line in enumerate(lines):
                        line = line.strip()
                        if ',' in line and len(line.split(',')) > 10:  # 쉼표가 많은 줄
                            if any(keyword in line for keyword in ['Date', 'Voltage', 'Current', 'Time']):
                                if verbose:
                                    print(f"추정 헤더 발견 (줄 {i+1}): {line[:50]}...")
                                return i
                    
                    break
                except UnicodeDecodeError:
                    continue
            
            # 기본값: 3번째 줄 (인덱스 2)
            if verbose:
                print("헤더를 찾을 수 없어 기본값(3번째 줄) 사용")
            return 2
            
        except Exception as e:
            if verbose:
                print(f"헤더 찾기 실패 {file_path}: {e}")
            return 2
    
    def parse_toyo_data_file(self, file_path: Path) -> pd.DataFrame:
        """
        Toyo 데이터 파일을 파싱
        
        Args:
            file_path (Path): 데이터 파일 경로
            
        Returns:
            pd.DataFrame: 파싱된 데이터프레임
        """
        try:
            # 헤더 줄 번호 찾기
            header_line = self.find_toyo_header_line(file_path)
            
            # 여러 인코딩 시도하여 데이터 읽기
            encodings = ['utf-8', 'cp949', 'euc-kr', 'latin1']
            df: Optional[pd.DataFrame] = None
            
            for encoding in encodings:
                try:
                    # 찾은 헤더 줄부터 읽기
                    df = pd.read_csv(
                        str(file_path),
                        header=header_line,  # 동적으로 찾은 헤더 줄 사용
                        encoding=encoding,
                        on_bad_lines='skip'
                    )
                    break
                except (UnicodeDecodeError, pd.errors.ParserError):
                    continue
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 컬럼명 정리
            df.columns = [self.clean_column_name(str(col)) for col in df.columns]
            
            # 빈 행 제거
            df = df.dropna(how='all')
            
            # 의미있는 컬럼만 선택
            df_filtered, _, _ = self.filter_meaningful_columns(df, verbose=False)
            
            # 데이터 타입 변환
            numeric_columns = ['PassTime_Sec', 'Voltage_V', 'Current_mA', 
                             'Temp1_Deg', 'Condition', 'Mode', 'Cycle', 'TotlCycle']
            
            if self.data_type == 'toyo1':
                numeric_columns.append('PassedDate')
            
            for col in numeric_columns:
                if col in df_filtered.columns:
                    df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce')
            
            # 파일명 추가
            df_filtered['FileName'] = file_path.name
            
            return df_filtered
            
        except Exception as e:
            print(f"Toyo 파일 파싱 실패 {file_path}: {e}")
            return pd.DataFrame()
    
    def parse_pne_data_file(self, file_path: Path) -> pd.DataFrame:
        """
        PNE 데이터 파일을 파싱
        
        Args:
            file_path (Path): 데이터 파일 경로
            
        Returns:
            pd.DataFrame: 파싱된 데이터프레임
        """
        try:
            file_name = file_path.name
            
            # 파일 타입별로 다른 처리
            if 'SaveData' in file_name and file_name.startswith('ch'):
                # ch03_SaveData0001.csv 등의 메인 데이터 파일
                df = pd.read_csv(
                    str(file_path),
                    header=None,  # 헤더 없음
                    encoding='utf-8',
                    on_bad_lines='skip'
                )
                
                if df.empty:
                    return pd.DataFrame()
                
                # PNE 메인 데이터 컬럼명 적용
                pne_columns = self.get_pne_columns()
                if len(df.columns) >= len(pne_columns):
                    df.columns = pne_columns + [f'Extra_Col_{i}' for i in range(len(pne_columns), len(df.columns))]
                else:
                    df.columns = pne_columns[:len(df.columns)]
                
                # 주요 컬럼 데이터 타입 변환
                numeric_columns = [
                    'Index', 'Step_Type', 'Voltage_uV', 'Current_uA', 'Chg_Capacity_uAh', 
                    'Dchg_Capacity_uAh', 'Temperature1', 'Temperature2', 'TotalCycle', 'Current_Cycle'
                ]
                
                for col in numeric_columns:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                
            elif 'savingFileIndex_start' in file_name:
                # savingFileIndex_start.csv
                df = pd.read_csv(
                    str(file_path),
                    header=None,
                    encoding='utf-8',
                    on_bad_lines='skip'
                )
                
                if df.empty:
                    return pd.DataFrame()
                
                # 인덱스 파일 컬럼명
                index_columns = ['fileIndex', 'resultIndex', 'open_year', 'open_month', 'open_day']
                if len(df.columns) >= len(index_columns):
                    df.columns = index_columns + [f'Extra_Col_{i}' for i in range(len(index_columns), len(df.columns))]
                else:
                    df.columns = index_columns[:len(df.columns)]
                
            elif 'savingFileIndex_last' in file_name:
                # savingFileIndex_last.csv
                df = pd.read_csv(
                    str(file_path),
                    header=None,
                    encoding='utf-8',
                    on_bad_lines='skip'
                )
                
                if df.empty:
                    return pd.DataFrame()
                
                # 마지막 인덱스 파일 컬럼명
                last_index_columns = ['fileIndex', 'resultIndex', 'open_year', 'open_month', 'open_day']
                if len(df.columns) >= len(last_index_columns):
                    df.columns = last_index_columns + [f'Extra_Col_{i}' for i in range(len(last_index_columns), len(df.columns))]
                else:
                    df.columns = last_index_columns[:len(df.columns)]
                    
            elif 'SaveEndData' in file_name:
                # ch03_SaveEndData.csv
                df = pd.read_csv(
                    str(file_path),
                    header=None,
                    encoding='utf-8',
                    on_bad_lines='skip'
                )
                
                if df.empty:
                    return pd.DataFrame()
                
                # EndData는 메인 데이터와 동일한 구조로 가정
                pne_columns = self.get_pne_columns()
                if len(df.columns) >= len(pne_columns):
                    df.columns = pne_columns + [f'Extra_Col_{i}' for i in range(len(pne_columns), len(df.columns))]
                else:
                    df.columns = pne_columns[:len(df.columns)]
            
            else:
                # 기타 파일
                df = pd.read_csv(
                    str(file_path),
                    header=None,
                    encoding='utf-8',
                    on_bad_lines='skip'
                )
                
                if df.empty:
                    return pd.DataFrame()
            
            # 빈 행 제거
            df = df.dropna(how='all')
            
            # 파일명과 파일 타입 추가
            df['FileName'] = file_path.name
            df['FileType'] = self.get_pne_file_type(file_name)
            
            return df
            
        except Exception as e:
            print(f"PNE 파일 파싱 실패 {file_path}: {e}")
            return pd.DataFrame()
    
    def get_pne_file_type(self, file_name: str) -> str:
        """
        PNE 파일의 타입을 반환
        
        Args:
            file_name (str): 파일명
            
        Returns:
            str: 파일 타입
        """
        if 'SaveData' in file_name and file_name.startswith('ch'):
            return 'main_data'
        elif 'savingFileIndex_start' in file_name:
            return 'index_start'
        elif 'savingFileIndex_last' in file_name:
            return 'index_last'
        elif 'SaveEndData' in file_name:
            return 'end_data'
        else:
            return 'other'
    
    def parse_capacity_log(self, file_path: Path) -> pd.DataFrame:
        """
        CAPACITY.LOG 파일을 파싱 (Toyo만 해당)
        
        Args:
            file_path (Path): CAPACITY.LOG 파일 경로
            
        Returns:
            pd.DataFrame: 파싱된 용량 로그 데이터프레임
        """
        if self.data_type == 'pne':
            return pd.DataFrame()  # PNE는 CAPACITY.LOG가 없음
        
        try:
            # 여러 인코딩 시도
            encodings = ['utf-8', 'cp949', 'euc-kr', 'latin1']
            df: Optional[pd.DataFrame] = None
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(
                        str(file_path),
                        header=0,  # 첫 번째 줄을 헤더로 사용
                        encoding=encoding,
                        on_bad_lines='skip'
                    )
                    break
                except (UnicodeDecodeError, pd.errors.ParserError):
                    continue
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 컬럼명 정리
            df.columns = [self.clean_column_name(str(col)) for col in df.columns]
            
            # 빈 행 제거
            df = df.dropna(how='all')
            
            # 의미있는 컬럼만 선택
            df_filtered, _, _ = self.filter_meaningful_columns(df, verbose=False)
            
            # 컬럼명 매핑
            column_mapping = {
                'Cap_mAh': 'Cap_mAh',
                'Pow_mWh': 'Pow_mWh', 
                'AveVolt_V': 'AveVolt_V',
                'PeakVolt_V': 'PeakVolt_V',
                'PeakTemp_Deg': 'PeakTemp_Deg',
                'Ocv': 'Ocv_V'
            }
            
            # 컬럼명 변경
            for old_name, new_name in column_mapping.items():
                if old_name in df_filtered.columns:
                    df_filtered = df_filtered.rename(columns={old_name: new_name})
            
            # 데이터 타입 변환
            numeric_columns = ['Condition', 'Mode', 'Cycle', 'TotlCycle',
                             'Cap_mAh', 'Pow_mWh', 'AveVolt_V', 'PeakVolt_V',
                             'PeakTemp_Deg', 'Ocv_V']
            
            if self.data_type == 'toyo1':
                numeric_columns.extend(['DchCycle', 'PassedDate'])
            
            for col in numeric_columns:
                if col in df_filtered.columns:
                    df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce')
            
            return df_filtered
            
        except Exception as e:
            print(f"CAPACITY.LOG 파싱 실패 {file_path}: {e}")
            return pd.DataFrame()
    
    def process_channel(self, channel: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        특정 채널의 모든 데이터를 처리
        
        Args:
            channel (str): 채널 번호 또는 이름
            
        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: (통합 데이터, 용량 로그)
        """
        channel_path = self.data_path / channel
        print(f"\n채널 {channel} 처리 중...")
        print(f"채널 경로: {channel_path}")
        
        if not channel_path.exists():
            print(f"채널 경로가 존재하지 않습니다: {channel_path}")
            return pd.DataFrame(), pd.DataFrame()
        
        # 데이터 파일들 찾기
        data_files = self.get_data_files(channel_path)
        print(f"발견된 데이터 파일 수: {len(data_files)}")
        
        if not data_files:
            print(f"채널 {channel}에서 데이터 파일을 찾을 수 없습니다.")
            return pd.DataFrame(), pd.DataFrame()
        
        # 첫 번째 파일에서 헤더 위치 확인 (Toyo만, 한 번만 출력)
        header_line = 2  # 기본값
        if self.data_type in ['toyo1', 'toyo2'] and data_files:
            first_file_path = channel_path / data_files[0]
            header_line = self.find_toyo_header_line(first_file_path, verbose=True)
            print(f"Toyo 헤더 위치: 줄 {header_line + 1}")
        
        # 모든 데이터 파일 처리 (tqdm으로 진행률 표시)
        all_data: List[pd.DataFrame] = []
        pne_file_groups: Dict[str, List[pd.DataFrame]] = {
            'main_data': [],
            'index_start': [],
            'index_last': [],
            'end_data': [],
            'other': []
        }
        
        # tqdm을 사용한 진행률 표시
        with tqdm(total=len(data_files), desc=f"채널 {channel} 파일 처리", unit="파일") as pbar:
            for file_name in data_files:
                try:
                    if self.data_type == 'pne':
                        file_path = channel_path / 'Restore' / file_name
                        df = self.parse_pne_data_file(file_path)
                        
                        if not df.empty:
                            file_type = df['FileType'].iloc[0] if 'FileType' in df.columns else 'other'
                            pne_file_groups[file_type].append(df)
                            all_data.append(df)
                            pbar.set_postfix({"현재 파일": file_name[:20], "행 수": len(df)})
                    else:
                        file_path = channel_path / file_name
                        df = self.parse_toyo_data_file_with_header(file_path, header_line)
                        
                        if not df.empty:
                            all_data.append(df)
                            pbar.set_postfix({"현재 파일": file_name, "행 수": len(df)})
                            
                except Exception as e:
                    # 개별 파일 오류를 조용히 처리하고 계속 진행
                    pbar.set_postfix({"현재 파일": file_name, "상태": "오류"})
                
                pbar.update(1)
        
        # 데이터 통합
        if all_data:
            print("데이터 통합 중...")
            combined_data = pd.concat(all_data, ignore_index=True)
            print(f"통합된 데이터 행 수: {len(combined_data):,}")
            print(f"최종 컬럼 수: {len(combined_data.columns)}")
            
            # PNE의 경우 파일 타입별 통계 출력
            if self.data_type == 'pne':
                print("PNE 파일별 통계:")
                for file_type, dfs in pne_file_groups.items():
                    if dfs:
                        total_rows = sum(len(df) for df in dfs)
                        print(f"  - {file_type}: {len(dfs)}개 파일, {total_rows:,}행")
        else:
            combined_data = pd.DataFrame()
            print("처리된 데이터가 없습니다.")
        
        # CAPACITY.LOG 처리 (Toyo만)
        capacity_log = pd.DataFrame()
        if self.data_type in ['toyo1', 'toyo2']:
            capacity_log_path = channel_path / "CAPACITY.LOG"
            if capacity_log_path.exists():
                print("CAPACITY.LOG 처리 중...")
                capacity_log = self.parse_capacity_log(capacity_log_path)
                print(f"용량 로그 행 수: {len(capacity_log):,}")
            else:
                print("CAPACITY.LOG 파일을 찾을 수 없습니다.")
        
        return combined_data, capacity_log
    
    def parse_toyo_data_file_with_header(self, file_path: Path, header_line: int) -> pd.DataFrame:
        """
        미리 찾은 헤더 위치로 Toyo 데이터 파일을 파싱
        
        Args:
            file_path (Path): 데이터 파일 경로
            header_line (int): 헤더 줄 번호
            
        Returns:
            pd.DataFrame: 파싱된 데이터프레임
        """
        try:
            # 여러 인코딩 시도하여 데이터 읽기
            encodings = ['utf-8', 'cp949', 'euc-kr', 'latin1']
            df: Optional[pd.DataFrame] = None
            
            for encoding in encodings:
                try:
                    # 미리 찾은 헤더 줄부터 읽기
                    df = pd.read_csv(
                        str(file_path),
                        header=header_line,
                        encoding=encoding,
                        on_bad_lines='skip'
                    )
                    break
                except (UnicodeDecodeError, pd.errors.ParserError):
                    continue
            
            if df is None or df.empty:
                return pd.DataFrame()
            
            # 컬럼명 정리
            df.columns = [self.clean_column_name(str(col)) for col in df.columns]
            
            # 빈 행 제거
            df = df.dropna(how='all')
            
            # 의미있는 컬럼만 선택
            df_filtered, _, _ = self.filter_meaningful_columns(df, verbose=False)
            
            # 데이터 타입 변환
            numeric_columns = ['PassTime_Sec', 'Voltage_V', 'Current_mA', 
                             'Temp1_Deg', 'Condition', 'Mode', 'Cycle', 'TotlCycle']
            
            if self.data_type == 'toyo1':
                numeric_columns.append('PassedDate')
            
            for col in numeric_columns:
                if col in df_filtered.columns:
                    df_filtered[col] = pd.to_numeric(df_filtered[col], errors='coerce')
            
            # 파일명 추가
            df_filtered['FileName'] = file_path.name
            
            return df_filtered
            
        except Exception as e:
            # 조용히 실패하고 빈 DataFrame 반환
            return pd.DataFrame()
    
    def process_all_channels(self) -> Dict[str, Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        모든 채널의 데이터를 처리
        
        Returns:
            Dict[str, Tuple[pd.DataFrame, pd.DataFrame]]: 채널별 (데이터, 용량로그) 딕셔너리
        """
        channels = self.detect_channels()
        results: Dict[str, Tuple[pd.DataFrame, pd.DataFrame]] = {}
        
        if not channels:
            print("처리할 채널이 없습니다.")
            return results
        
        print(f"총 {len(channels)}개 채널 처리 시작")
        
        # 전체 채널에 대해 tqdm 진행률 표시
        with tqdm(total=len(channels), desc="전체 채널 처리", unit="채널") as pbar:
            for channel in channels:
                try:
                    pbar.set_description(f"채널 {channel} 처리 중")
                    data, capacity_log = self.process_channel(channel)
                    results[channel] = (data, capacity_log)
                    
                    # 메모리 관리를 위해 클래스 변수에도 저장
                    self.channels[channel] = data
                    self.capacity_logs[channel] = capacity_log
                    
                    # 처리 결과를 postfix에 표시
                    pbar.set_postfix({
                        "데이터 행": f"{len(data):,}" if not data.empty else "0",
                        "용량로그 행": f"{len(capacity_log):,}" if not capacity_log.empty else "0"
                    })
                    
                except Exception as e:
                    print(f"채널 {channel} 처리 중 오류 발생: {e}")
                    results[channel] = (pd.DataFrame(), pd.DataFrame())
                    pbar.set_postfix({"상태": "오류 발생"})
                
                pbar.update(1)
        
        print(f"\n전체 처리 완료!")
        return results
    
    def save_processed_data(self, output_path: str, file_format: str = 'csv') -> None:
        """
        처리된 데이터를 저장
        
        Args:
            output_path (str): 출력 경로
            file_format (str): 저장 형식 ('csv', 'excel', 'pickle')
        """
        output_dir = Path(output_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n데이터 저장 중... (형식: {file_format})")
        print(f"장비 타입: {self.data_type}")
        print(f"용량 정보: {self.capacity_info}")
        print(f"처리 시간: {self.timestamp}")
        
        # 저장할 총 파일 수 계산
        total_files = len(self.channels) * 2  # 데이터 + 용량로그 (Toyo의 경우)
        if self.data_type == 'pne':
            total_files = len(self.channels)  # PNE는 용량로그가 없음
        
        with tqdm(total=total_files, desc="파일 저장", unit="파일") as pbar:
            for channel in self.channels:
                # 메인 데이터 저장
                if not self.channels[channel].empty:
                    base_filename = f"{self.data_type}_ch{channel}_{self.capacity_info}_{self.timestamp}"
                    
                    if file_format == 'csv':
                        file_path = output_dir / f"{base_filename}_data.csv"
                        self.channels[channel].to_csv(str(file_path), index=False, encoding='utf-8-sig')
                    elif file_format == 'excel':
                        file_path = output_dir / f"{base_filename}_data.xlsx"
                        self.channels[channel].to_excel(str(file_path), index=False)
                    elif file_format == 'pickle':
                        file_path = output_dir / f"{base_filename}_data.pkl"
                        self.channels[channel].to_pickle(str(file_path))
                    
                    pbar.set_postfix({"저장 중": f"ch{channel}_데이터"})
                    pbar.update(1)
                
                # 용량 로그 저장 (Toyo만)
                if not self.capacity_logs[channel].empty:
                    base_filename = f"{self.data_type}_ch{channel}_{self.capacity_info}_{self.timestamp}"
                    
                    if file_format == 'csv':
                        file_path = output_dir / f"{base_filename}_capacity.csv"
                        self.capacity_logs[channel].to_csv(str(file_path), index=False, encoding='utf-8-sig')
                    elif file_format == 'excel':
                        file_path = output_dir / f"{base_filename}_capacity.xlsx"
                        self.capacity_logs[channel].to_excel(str(file_path), index=False)
                    elif file_format == 'pickle':
                        file_path = output_dir / f"{base_filename}_capacity.pkl"
                        self.capacity_logs[channel].to_pickle(str(file_path))
                    
                    pbar.set_postfix({"저장 중": f"ch{channel}_용량로그"})
                    pbar.update(1)
        
        print("저장 완료!")
        print(f"저장 위치: {output_dir}")
        
        # 저장된 파일 목록 출력
        print("\n저장된 파일들:")
        for file in sorted(output_dir.glob(f"*{self.timestamp}*")):
            file_size = file.stat().st_size / (1024 * 1024)  # MB 단위
            print(f"  - {file.name} ({file_size:.1f}MB)")
    
    def get_summary(self) -> Dict[str, Union[int, str, Dict[str, Dict[str, Union[int, str, Dict[str, str]]]]]]:
        """
        처리된 데이터의 요약 정보 반환
        
        Returns:
            Dict: 요약 정보
        """
        summary: Dict[str, Union[int, str, Dict[str, Dict[str, Union[int, str, Dict[str, str]]]]]] = {
            'equipment_type': self.data_type or 'unknown',
            'capacity_info': self.capacity_info,
            'total_channels': len(self.channels),
            'channels': {}
        }
        
        channels_info: Dict[str, Dict[str, Union[int, str, Dict[str, str]]]] = {}
        
        for channel in self.channels:
            channel_summary: Dict[str, Union[int, str, Dict[str, str]]] = {
                'data_rows': len(self.channels[channel]),
                'capacity_log_rows': len(self.capacity_logs[channel]),
                'date_range': None,
                'cycles': None
            }
            
            # 날짜 범위 (Date 컬럼이 있는 경우)
            date_columns = ['Date', 'Date_YYYYMMDD']
            for date_col in date_columns:
                if not self.channels[channel].empty and date_col in self.channels[channel].columns:
                    if date_col == 'Date_YYYYMMDD':
                        # PNE 형식의 날짜 처리
                        dates = pd.to_datetime(self.channels[channel][date_col], format='%Y%m%d', errors='coerce')
                    else:
                        dates = pd.to_datetime(self.channels[channel][date_col], errors='coerce')
                    
                    valid_dates = dates.dropna()
                    if not valid_dates.empty:
                        channel_summary['date_range'] = {
                            'start': valid_dates.min().strftime('%Y-%m-%d'),
                            'end': valid_dates.max().strftime('%Y-%m-%d')
                        }
                        break
            
            # 사이클 정보
            cycle_columns = ['Cycle', 'Current_Cycle', 'TotalCycle']
            for cycle_col in cycle_columns:
                if not self.channels[channel].empty and cycle_col in self.channels[channel].columns:
                    cycles = self.channels[channel][cycle_col].dropna()
                    if not cycles.empty:
                        channel_summary['cycles'] = {
                            'min': int(cycles.min()),
                            'max': int(cycles.max()),
                            'unique_count': cycles.nunique()
                        }
                        break
            
            channels_info[channel] = channel_summary
        
        summary['channels'] = channels_info
        return summary

# 사용 예시 함수
def main(data_path: str, output_path: Optional[str] = None) -> Optional[BatteryDataPreprocessor]:
    """
    메인 실행 함수
    
    Args:
        data_path (str): 입력 데이터 경로
        output_path (Optional[str]): 출력 경로 (None이면 저장하지 않음)
    
    Returns:
        Optional[BatteryDataPreprocessor]: 성공시 전처리기 객체, 실패시 None
    """
    try:
        # 전처리기 생성
        preprocessor = BatteryDataPreprocessor(data_path)
        
        # 모든 채널 처리
        results = preprocessor.process_all_channels()
        
        # 요약 정보 출력
        summary = preprocessor.get_summary()
        print("\n=== 처리 결과 요약 ===")
        print(f"장비 타입: {summary['equipment_type']}")
        print(f"용량 정보: {summary['capacity_info']}")
        print(f"총 채널 수: {summary['total_channels']}")
        
        channels = summary.get('channels', {})
        if isinstance(channels, dict):
            for channel, info in channels.items():
                if isinstance(info, dict):
                    print(f"\n채널 {channel}:")
                    print(f"  - 데이터 행 수: {info.get('data_rows', 0):,}")
                    print(f"  - 용량로그 행 수: {info.get('capacity_log_rows', 0):,}")
                    
                    date_range = info.get('date_range')
                    if date_range and isinstance(date_range, dict):
                        print(f"  - 날짜 범위: {date_range.get('start')} ~ {date_range.get('end')}")
                    
                    cycles = info.get('cycles')
                    if cycles and isinstance(cycles, dict):
                        print(f"  - 사이클 범위: {cycles.get('min')} ~ {cycles.get('max')} ({cycles.get('unique_count')} 개)")
        
        # 데이터 저장
        if output_path:
            preprocessor.save_processed_data(output_path, 'csv')
        
        return preprocessor
        
    except Exception as e:
        print(f"처리 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return None

# 실행 예시
if __name__ == "__main__":
    # 사용법
    print("=== 리튬이온배터리 데이터 전처리 ===")
    print("지원 장비: Toyo1, Toyo2, PNE")
    
    # 입력 경로 처리
    while True:
        data_path_input = input("데이터 폴더 경로를 입력하세요: ").strip()
        
        # 따옴표 제거 및 경로 정리
        cleaned_path = data_path_input.strip('"').strip("'")
        test_path = Path(cleaned_path)
        
        print(f"입력된 경로: {data_path_input}")
        print(f"정리된 경로: {cleaned_path}")
        print(f"절대 경로: {test_path.resolve()}")
        print(f"경로 존재 확인: {test_path.exists()}")
        
        if test_path.exists():
            data_path = cleaned_path
            break
        else:
            print(f"경로가 존재하지 않습니다!")
            print("올바른 경로를 입력해주세요.")
            
            # 부모 경로 확인
            parent = test_path.parent
            if parent.exists():
                print(f"부모 경로 '{parent}' 내용:")
                try:
                    items = list(parent.iterdir())[:10]  # 최대 10개만 표시
                    for item in items:
                        print(f"  - {item.name}")
                    if len(list(parent.iterdir())) > 10:
                        print(f"  ... 및 {len(list(parent.iterdir())) - 10}개 더")
                except:
                    print("  부모 경로 내용을 읽을 수 없습니다.")
    
    # 출력 경로 처리
    output_input = input("출력 폴더 경로를 입력하세요 (엔터시 저장 안함): ").strip().strip('"').strip("'")
    output_path = output_input if output_input else None
    
    # 전처리 실행
    preprocessor = main(data_path, output_path)
    
    if preprocessor:
        print("\n전처리 완료!")
        print("preprocessor.channels[채널번호]로 데이터에 접근할 수 있습니다.")
        if preprocessor.data_type in ['toyo1', 'toyo2']:
            print("preprocessor.capacity_logs[채널번호]로 용량로그에 접근할 수 있습니다.")
    else:
        print("전처리 실패!")