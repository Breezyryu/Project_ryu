import os
import pandas as pd
import numpy as np
from pathlib import Path
import re
from typing import Dict, List, Tuple, Optional, Union
import warnings
warnings.filterwarnings('ignore')

class BatteryDataPreprocessor:
    """
    리튬이온배터리 성능/수명 측정 데이터 전처리 클래스
    """
    
    def __init__(self, data_path: str):
        """
        초기화
        
        Args:
            data_path (str): 데이터가 저장된 루트 경로
        """
        self.data_path = Path(data_path)
        self.channels: Dict[str, pd.DataFrame] = {}
        self.capacity_logs: Dict[str, pd.DataFrame] = {}
        
        if not self.data_path.exists():
            raise FileNotFoundError(f"데이터 경로가 존재하지 않습니다: {data_path}")
        
        print(f"데이터 경로 확인: {self.data_path}")
        print(f"경로 존재 여부: {self.data_path.exists()}")
    
    def detect_channels(self) -> List[str]:
        """
        데이터 경로에서 채널 폴더들을 자동 감지
        
        Returns:
            List[str]: 채널 번호 리스트
        """
        channels = []
        
        print(f"경로 스캔 중: {self.data_path}")
        
        try:
            for item in self.data_path.iterdir():
                print(f"발견된 항목: {item.name}, 디렉토리: {item.is_dir()}, 숫자: {item.name.isdigit()}")
                if item.is_dir() and item.name.isdigit():
                    channels.append(item.name)
        except Exception as e:
            print(f"디렉토리 스캔 중 오류: {e}")
            return []
        
        channels.sort(key=int)  # 숫자 순으로 정렬
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
            for file in channel_path.iterdir():
                if file.is_file() and re.match(r'^\d{6}$', file.name):
                    data_files.append(file.name)
        except Exception as e:
            print(f"데이터 파일 스캔 중 오류 ({channel_path}): {e}")
            return []
        
        # 숫자 순으로 정렬
        data_files.sort()
        return data_files
    
    def detect_data_format(self, file_path: Path) -> str:
        """
        데이터 파일의 형식을 감지 (Toyo1 vs Toyo2)
        
        Args:
            file_path (Path): 데이터 파일 경로
            
        Returns:
            str: 'toyo1' 또는 'toyo2'
        """
        try:
            # 여러 인코딩 시도
            encodings = ['utf-8', 'cp949', 'euc-kr', 'latin1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        header = f.readline().strip()
                    break
                except UnicodeDecodeError:
                    continue
            else:
                # 모든 인코딩 실패시 바이너리로 읽어서 처리
                with open(file_path, 'rb') as f:
                    header = f.readline().decode('utf-8', errors='ignore').strip()
            
            # PassedDate 컬럼이 있으면 Toyo1, 없으면 Toyo2
            if 'PassedDate' in header:
                return 'toyo1'
            else:
                return 'toyo2'
        except Exception as e:
            print(f"파일 형식 감지 실패 {file_path}: {e}")
            return 'toyo1'  # 기본값
    
    def parse_data_file(self, file_path: Path, data_format: str) -> pd.DataFrame:
        """
        개별 데이터 파일을 파싱
        
        Args:
            file_path (Path): 데이터 파일 경로
            data_format (str): 데이터 형식 ('toyo1' 또는 'toyo2')
            
        Returns:
            pd.DataFrame: 파싱된 데이터프레임
        """
        try:
            if data_format == 'toyo1':
                # Toyo1 형식의 컬럼
                columns = [
                    'Date', 'Time', 'PassTime[Sec]', 'Voltage[V]', 'Current[mA]',
                    'Col5', 'Col6', 'Temp1[Deg]', 'Col8', 'Col9', 'Col10', 'Col11',
                    'Condition', 'Mode', 'Cycle', 'TotlCycle', 'PassedDate', 'Temp1[Deg]_2'
                ]
            else:
                # Toyo2 형식의 컬럼
                columns = [
                    'Date', 'Time', 'PassTime[Sec]', 'Voltage[V]', 'Current[mA]',
                    'Col5', 'Col6', 'Temp1[Deg]', 'Col8', 'Col9', 'Col10', 'Col11',
                    'Condition', 'Mode', 'Cycle', 'TotlCycle', 'Temp1[Deg]_2'
                ]
            
            # 여러 인코딩 시도하여 데이터 읽기
            encodings = ['utf-8', 'cp949', 'euc-kr', 'latin1']
            df = pd.DataFrame()
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(
                        str(file_path),  # Path 객체를 문자열로 변환
                        header=0, 
                        names=columns,
                        encoding=encoding,
                        on_bad_lines='skip'  # 잘못된 라인 건너뛰기
                    )
                    break
                except (UnicodeDecodeError, pd.errors.ParserError):
                    continue
            
            if df.empty:
                print(f"파일 읽기 실패: {file_path}")
                return pd.DataFrame()
            
            # 빈 행 제거
            df = df.dropna(how='all')
            
            # 데이터 타입 변환
            numeric_columns = ['PassTime[Sec]', 'Voltage[V]', 'Current[mA]', 
                             'Temp1[Deg]', 'Condition', 'Mode', 'Cycle', 'TotlCycle']
            
            if data_format == 'toyo1':
                numeric_columns.append('PassedDate')
            
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # 파일명 추가
            df['FileName'] = file_path.name
            
            return df
            
        except Exception as e:
            print(f"파일 파싱 실패 {file_path}: {e}")
            return pd.DataFrame()
    
    def parse_capacity_log(self, file_path: Path, data_format: str) -> pd.DataFrame:
        """
        CAPACITY.LOG 파일을 파싱
        
        Args:
            file_path (Path): CAPACITY.LOG 파일 경로
            data_format (str): 데이터 형식
            
        Returns:
            pd.DataFrame: 파싱된 용량 로그 데이터프레임
        """
        try:
            if data_format == 'toyo1':
                columns = [
                    'Date', 'Time', 'Condition', 'Mode', 'Cycle', 'TotlCycle',
                    'Cap[mAh]', 'PassTime', 'TotlPassTime', 'Pow[mWh]',
                    'AveVolt[V]', 'PeakVolt[V]', 'Col12', 'PeakTemp[Deg]',
                    'Ocv', 'Col15', 'Finish', 'DchCycle', 'PassedDate'
                ]
            else:
                columns = [
                    'Date', 'Time', 'Condition', 'Mode', 'Cycle', 'TotlCycle',
                    'Cap[mAh]', 'PassTime', 'TotlPassTime', 'Pow[mWh]',
                    'AveVolt[V]', 'PeakVolt[V]', 'Col12', 'PeakTemp[Deg]',
                    'Ocv', 'Col15', 'Finish'
                ]
            
            # 여러 인코딩 시도
            encodings = ['utf-8', 'cp949', 'euc-kr', 'latin1']
            df = pd.DataFrame()
            
            for encoding in encodings:
                try:
                    df = pd.read_csv(
                        str(file_path),  # Path 객체를 문자열로 변환
                        header=0,
                        names=columns,
                        encoding=encoding,
                        on_bad_lines='skip'
                    )
                    break
                except (UnicodeDecodeError, pd.errors.ParserError):
                    continue
            
            if df.empty:
                print(f"CAPACITY.LOG 읽기 실패: {file_path}")
                return pd.DataFrame()
            
            # 빈 행 제거
            df = df.dropna(how='all')
            
            # 데이터 타입 변환
            numeric_columns = ['Condition', 'Mode', 'Cycle', 'TotlCycle',
                             'Cap[mAh]', 'Pow[mWh]', 'AveVolt[V]', 'PeakVolt[V]',
                             'PeakTemp[Deg]', 'Ocv']
            
            if data_format == 'toyo1':
                numeric_columns.extend(['DchCycle', 'PassedDate'])
            
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
            
        except Exception as e:
            print(f"CAPACITY.LOG 파싱 실패 {file_path}: {e}")
            return pd.DataFrame()
    
    def process_channel(self, channel: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        특정 채널의 모든 데이터를 처리
        
        Args:
            channel (str): 채널 번호
            
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
        
        # 첫 번째 파일로 데이터 형식 감지
        first_file_path = channel_path / data_files[0]
        data_format = self.detect_data_format(first_file_path)
        print(f"감지된 데이터 형식: {data_format}")
        
        # 모든 데이터 파일 처리
        all_data = []
        for i, file_name in enumerate(data_files):
            file_path = channel_path / file_name
            df = self.parse_data_file(file_path, data_format)
            
            if not df.empty:
                all_data.append(df)
            
            # 진행상황 표시
            if (i + 1) % 100 == 0 or i == len(data_files) - 1:
                print(f"  진행률: {i+1}/{len(data_files)} ({(i+1)/len(data_files)*100:.1f}%)")
        
        # 데이터 통합
        if all_data:
            combined_data = pd.concat(all_data, ignore_index=True)
            print(f"통합된 데이터 행 수: {len(combined_data)}")
        else:
            combined_data = pd.DataFrame()
            print("처리된 데이터가 없습니다.")
        
        # CAPACITY.LOG 처리
        capacity_log_path = channel_path / "CAPACITY.LOG"
        if capacity_log_path.exists():
            capacity_log = self.parse_capacity_log(capacity_log_path, data_format)
            print(f"용량 로그 행 수: {len(capacity_log)}")
        else:
            capacity_log = pd.DataFrame()
            print("CAPACITY.LOG 파일을 찾을 수 없습니다.")
        
        return combined_data, capacity_log
    
    def process_all_channels(self) -> Dict[str, Tuple[pd.DataFrame, pd.DataFrame]]:
        """
        모든 채널의 데이터를 처리
        
        Returns:
            Dict[str, Tuple[pd.DataFrame, pd.DataFrame]]: 채널별 (데이터, 용량로그) 딕셔너리
        """
        channels = self.detect_channels()
        results = {}
        
        if not channels:
            print("처리할 채널이 없습니다.")
            return results
        
        print(f"총 {len(channels)}개 채널 처리 시작")
        
        for channel in channels:
            try:
                data, capacity_log = self.process_channel(channel)
                results[channel] = (data, capacity_log)
                
                # 메모리 관리를 위해 클래스 변수에도 저장
                self.channels[channel] = data
                self.capacity_logs[channel] = capacity_log
                
            except Exception as e:
                print(f"채널 {channel} 처리 중 오류 발생: {e}")
                results[channel] = (pd.DataFrame(), pd.DataFrame())
        
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
        
        for channel in self.channels:
            # 메인 데이터 저장
            if not self.channels[channel].empty:
                if file_format == 'csv':
                    file_path = output_dir / f"channel_{channel}_data.csv"
                    self.channels[channel].to_csv(str(file_path), index=False, encoding='utf-8-sig')
                elif file_format == 'excel':
                    file_path = output_dir / f"channel_{channel}_data.xlsx"
                    self.channels[channel].to_excel(str(file_path), index=False)
                elif file_format == 'pickle':
                    file_path = output_dir / f"channel_{channel}_data.pkl"
                    self.channels[channel].to_pickle(str(file_path))
                
                print(f"  채널 {channel} 데이터 저장: {file_path}")
            
            # 용량 로그 저장
            if not self.capacity_logs[channel].empty:
                if file_format == 'csv':
                    file_path = output_dir / f"channel_{channel}_capacity.csv"
                    self.capacity_logs[channel].to_csv(str(file_path), index=False, encoding='utf-8-sig')
                elif file_format == 'excel':
                    file_path = output_dir / f"channel_{channel}_capacity.xlsx"
                    self.capacity_logs[channel].to_excel(str(file_path), index=False)
                elif file_format == 'pickle':
                    file_path = output_dir / f"channel_{channel}_capacity.pkl"
                    self.capacity_logs[channel].to_pickle(str(file_path))
                
                print(f"  채널 {channel} 용량로그 저장: {file_path}")
        
        print("저장 완료!")
    
    def get_summary(self) -> Dict:
        """
        처리된 데이터의 요약 정보 반환
        
        Returns:
            Dict: 요약 정보
        """
        summary = {
            'total_channels': len(self.channels),
            'channels': {}
        }
        
        for channel in self.channels:
            channel_summary = {
                'data_rows': len(self.channels[channel]),
                'capacity_log_rows': len(self.capacity_logs[channel]),
                'date_range': None,
                'cycles': None
            }
            
            # 날짜 범위
            if not self.channels[channel].empty and 'Date' in self.channels[channel].columns:
                dates = pd.to_datetime(self.channels[channel]['Date'], errors='coerce')
                valid_dates = dates.dropna()
                if not valid_dates.empty:
                    channel_summary['date_range'] = {
                        'start': valid_dates.min().strftime('%Y-%m-%d'),
                        'end': valid_dates.max().strftime('%Y-%m-%d')
                    }
            
            # 사이클 정보
            if not self.channels[channel].empty and 'Cycle' in self.channels[channel].columns:
                cycles = self.channels[channel]['Cycle'].dropna()
                if not cycles.empty:
                    channel_summary['cycles'] = {
                        'min': int(cycles.min()),
                        'max': int(cycles.max()),
                        'unique_count': cycles.nunique()
                    }
            
            summary['channels'][channel] = channel_summary
        
        return summary

# 사용 예시 함수
def main(data_path: str, output_path: Optional[str] = None) -> Optional['BatteryDataPreprocessor']:
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
        print(f"총 채널 수: {summary['total_channels']}")
        
        for channel, info in summary['channels'].items():
            print(f"\n채널 {channel}:")
            print(f"  - 데이터 행 수: {info['data_rows']:,}")
            print(f"  - 용량로그 행 수: {info['capacity_log_rows']:,}")
            if info['date_range']:
                print(f"  - 날짜 범위: {info['date_range']['start']} ~ {info['date_range']['end']}")
            if info['cycles']:
                print(f"  - 사이클 범위: {info['cycles']['min']} ~ {info['cycles']['max']} ({info['cycles']['unique_count']} 개)")
        
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
    
    # 입력 경로 처리
    while True:
        data_path = input("데이터 폴더 경로를 입력하세요: ").strip().strip('"').strip("'")
        if data_path and Path(data_path).exists():
            break
        else:
            print(f"경로가 존재하지 않습니다: {data_path}")
            print("올바른 경로를 입력해주세요.")
    
    # 출력 경로 처리
    output_input = input("출력 폴더 경로를 입력하세요 (엔터시 저장 안함): ").strip().strip('"').strip("'")
    output_path = output_input if output_input else None
    
    # 전처리 실행
    preprocessor = main(data_path, output_path)
    
    if preprocessor:
        print("\n전처리 완료!")
        print("preprocessor.channels[채널번호]로 데이터에 접근할 수 있습니다.")
        print("preprocessor.capacity_logs[채널번호]로 용량로그에 접근할 수 있습니다.")
    else:
        print("전처리 실패!")