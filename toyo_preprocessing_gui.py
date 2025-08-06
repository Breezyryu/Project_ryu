"""
Toyo Battery Data Preprocessing GUI Application

배터리 데이터 전처리를 위한 그래픽 사용자 인터페이스
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import queue
import sys
import os
from pathlib import Path
import json
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from preprocess import run_toyo_preprocessing, ToyoPreprocessingPipeline


class ToyoPreprocessingGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Toyo 배터리 데이터 전처리 시스템")
        self.root.geometry("900x700")
        
        # 설정 파일 경로
        self.config_file = Path.home() / ".toyo_preprocessing" / "config.json"
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        
        # 큐와 처리 스레드
        self.queue = queue.Queue()
        self.processing = False
        
        # UI 스타일 설정
        self.setup_styles()
        
        # UI 구성
        self.create_widgets()
        
        # 이전 설정 로드
        self.load_config()
        
        # 큐 모니터링 시작
        self.monitor_queue()
    
    def setup_styles(self):
        """UI 스타일 설정"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # 색상 정의
        self.colors = {
            'primary': '#2196F3',
            'success': '#4CAF50',
            'warning': '#FF9800',
            'error': '#F44336',
            'bg': '#F5F5F5',
            'fg': '#212121'
        }
        
        # 버튼 스타일
        style.configure('Primary.TButton',
                       background=self.colors['primary'],
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       padding=(10, 8))
        style.map('Primary.TButton',
                 background=[('active', '#1976D2')])
        
        style.configure('Success.TButton',
                       background=self.colors['success'],
                       foreground='white',
                       borderwidth=0,
                       focuscolor='none',
                       padding=(10, 8))
        style.map('Success.TButton',
                 background=[('active', '#388E3C')])
    
    def create_widgets(self):
        """UI 위젯 생성"""
        # 메인 컨테이너
        main_container = ttk.Frame(self.root, padding="10")
        main_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 타이틀
        title_label = ttk.Label(main_container, 
                               text="🔋 Toyo 배터리 데이터 전처리 시스템",
                               font=('Segoe UI', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # ========== 경로 설정 섹션 ==========
        path_frame = ttk.LabelFrame(main_container, text="📁 경로 설정", padding="10")
        path_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 입력 경로
        ttk.Label(path_frame, text="입력 경로 (Raw Data):").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.input_path_var = tk.StringVar()
        self.input_entry = ttk.Entry(path_frame, textvariable=self.input_path_var, width=60)
        self.input_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(path_frame, text="찾아보기...", 
                  command=self.browse_input_path).grid(row=0, column=2, padx=5, pady=5)
        
        # 출력 경로
        ttk.Label(path_frame, text="출력 경로 (Processed):").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.output_path_var = tk.StringVar()
        self.output_entry = ttk.Entry(path_frame, textvariable=self.output_path_var, width=60)
        self.output_entry.grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(path_frame, text="찾아보기...", 
                  command=self.browse_output_path).grid(row=1, column=2, padx=5, pady=5)
        
        # 자동 출력 경로 체크박스
        self.auto_output_var = tk.BooleanVar(value=True)
        self.auto_output_check = ttk.Checkbutton(
            path_frame, 
            text="자동 출력 경로 생성 (../../preprocess/입력폴더명)",
            variable=self.auto_output_var,
            command=self.toggle_auto_output
        )
        self.auto_output_check.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # ========== 처리 옵션 섹션 ==========
        options_frame = ttk.LabelFrame(main_container, text="⚙️ 처리 옵션", padding="10")
        options_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # 옵션 체크박스들
        self.force_reprocess_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="강제 재처리 (기존 결과 무시)",
                       variable=self.force_reprocess_var).grid(row=0, column=0, sticky=tk.W, pady=2)
        
        self.create_viz_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="시각화 생성",
                       variable=self.create_viz_var).grid(row=0, column=1, sticky=tk.W, pady=2)
        
        self.save_intermediate_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="중간 결과 저장",
                       variable=self.save_intermediate_var).grid(row=1, column=0, sticky=tk.W, pady=2)
        
        self.save_processed_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="처리된 데이터 저장",
                       variable=self.save_processed_var).grid(row=1, column=1, sticky=tk.W, pady=2)
        
        # ========== 처리 모드 섹션 ==========
        mode_frame = ttk.LabelFrame(main_container, text="🎯 처리 모드", padding="10")
        mode_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.mode_var = tk.StringVar(value="basic")
        modes = [
            ("기본 처리", "basic"),
            ("고급 처리", "advanced"),
            ("데이터 탐색만", "exploration"),
            ("개별 컴포넌트", "individual")
        ]
        
        for i, (text, value) in enumerate(modes):
            ttk.Radiobutton(mode_frame, text=text, variable=self.mode_var, 
                          value=value).grid(row=0, column=i, padx=10, pady=5)
        
        # ========== 실행 버튼 섹션 ==========
        button_frame = ttk.Frame(main_container)
        button_frame.grid(row=4, column=0, columnspan=3, pady=10)
        
        self.process_button = ttk.Button(button_frame, text="🚀 처리 시작", 
                                        style='Primary.TButton',
                                        command=self.start_processing)
        self.process_button.grid(row=0, column=0, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="⏹ 중지", 
                                      state='disabled',
                                      command=self.stop_processing)
        self.stop_button.grid(row=0, column=1, padx=5)
        
        self.clear_button = ttk.Button(button_frame, text="🗑️ 로그 지우기",
                                      command=self.clear_log)
        self.clear_button.grid(row=0, column=2, padx=5)
        
        # ========== 진행 상태 섹션 ==========
        progress_frame = ttk.LabelFrame(main_container, text="📊 진행 상태", padding="10")
        progress_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.progress_var = tk.StringVar(value="대기 중...")
        self.progress_label = ttk.Label(progress_frame, textvariable=self.progress_var)
        self.progress_label.grid(row=0, column=0, sticky=tk.W)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate', length=400)
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # ========== 로그 출력 섹션 ==========
        log_frame = ttk.LabelFrame(main_container, text="📝 처리 로그", padding="10")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=100, 
                                                  wrap=tk.WORD, font=('Consolas', 9))
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 텍스트 태그 설정 (색상 있는 로그)
        self.log_text.tag_config('INFO', foreground='black')
        self.log_text.tag_config('SUCCESS', foreground='green')
        self.log_text.tag_config('WARNING', foreground='orange')
        self.log_text.tag_config('ERROR', foreground='red')
        
        # Grid 가중치 설정
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_container.columnconfigure(0, weight=1)
        main_container.rowconfigure(6, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 입력 경로 변경 이벤트 바인딩
        self.input_path_var.trace('w', self.on_input_path_change)
    
    def browse_input_path(self):
        """입력 경로 선택"""
        path = filedialog.askdirectory(title="입력 데이터 폴더 선택")
        if path:
            self.input_path_var.set(path)
            self.log_message(f"입력 경로 설정: {path}", "INFO")
    
    def browse_output_path(self):
        """출력 경로 선택"""
        path = filedialog.askdirectory(title="출력 폴더 선택")
        if path:
            self.output_path_var.set(path)
            self.auto_output_var.set(False)
            self.log_message(f"출력 경로 설정: {path}", "INFO")
    
    def toggle_auto_output(self):
        """자동 출력 경로 토글"""
        if self.auto_output_var.get():
            self.output_entry.config(state='disabled')
            self.on_input_path_change()
        else:
            self.output_entry.config(state='normal')
    
    def on_input_path_change(self, *args):
        """입력 경로 변경 시 자동 출력 경로 업데이트"""
        if self.auto_output_var.get() and self.input_path_var.get():
            input_path = Path(self.input_path_var.get())
            output_path = Path("../../preprocess") / input_path.name
            self.output_path_var.set(str(output_path))
    
    def log_message(self, message, level="INFO"):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, formatted_message, level)
        self.log_text.see(tk.END)
        self.log_text.update()
    
    def clear_log(self):
        """로그 지우기"""
        self.log_text.delete(1.0, tk.END)
    
    def start_processing(self):
        """처리 시작"""
        # 입력 검증
        if not self.input_path_var.get():
            messagebox.showerror("오류", "입력 경로를 선택해주세요.")
            return
        
        input_path = Path(self.input_path_var.get())
        if not input_path.exists():
            messagebox.showerror("오류", f"입력 경로가 존재하지 않습니다:\n{input_path}")
            return
        
        # 출력 경로 설정
        if self.auto_output_var.get():
            output_path = Path("../../preprocess") / input_path.name
            output_path.mkdir(parents=True, exist_ok=True)
            self.output_path_var.set(str(output_path))
        else:
            if not self.output_path_var.get():
                messagebox.showerror("오류", "출력 경로를 선택해주세요.")
                return
            output_path = Path(self.output_path_var.get())
            output_path.mkdir(parents=True, exist_ok=True)
        
        # 설정 저장
        self.save_config()
        
        # UI 상태 변경
        self.processing = True
        self.process_button.config(state='disabled')
        self.stop_button.config(state='normal')
        self.progress_bar.start(10)
        self.progress_var.set("처리 중...")
        
        # 처리 스레드 시작
        thread = threading.Thread(target=self.run_processing, 
                                 args=(input_path, output_path))
        thread.daemon = True
        thread.start()
    
    def run_processing(self, input_path, output_path):
        """백그라운드에서 처리 실행"""
        try:
            self.queue.put(("LOG", "처리 시작...", "INFO"))
            self.queue.put(("LOG", f"입력 경로: {input_path}", "INFO"))
            self.queue.put(("LOG", f"출력 경로: {output_path}", "INFO"))
            self.queue.put(("LOG", f"처리 모드: {self.mode_var.get()}", "INFO"))
            
            mode = self.mode_var.get()
            
            if mode == "basic":
                # 기본 처리
                self.queue.put(("LOG", "기본 처리 모드 실행 중...", "INFO"))
                results = run_toyo_preprocessing(
                    src_path=str(input_path),
                    dst_path=str(output_path),
                    force_reprocess=self.force_reprocess_var.get(),
                    create_visualizations=self.create_viz_var.get()
                )
                
                # 결과 요약
                metadata = results.get('metadata', {})
                self.queue.put(("LOG", f"✅ 처리 완료!", "SUCCESS"))
                self.queue.put(("LOG", f"채널 수: {len(metadata.get('processed_channels', []))}", "SUCCESS"))
                self.queue.put(("LOG", f"처리 시간: {results.get('pipeline_duration', 0):.2f}초", "SUCCESS"))
                
            elif mode == "advanced":
                # 고급 처리
                self.queue.put(("LOG", "고급 처리 모드 실행 중...", "INFO"))
                pipeline = ToyoPreprocessingPipeline(str(input_path), str(output_path))
                
                # 데이터 요약 확인
                summary = pipeline.loader.get_data_summary()
                self.queue.put(("LOG", f"발견된 채널: {len(summary)}개", "INFO"))
                
                # 파이프라인 실행
                results = pipeline.run_complete_pipeline(
                    save_intermediate=self.save_intermediate_var.get(),
                    create_visualizations=self.create_viz_var.get(),
                    save_processed_data=self.save_processed_var.get()
                )
                
                self.queue.put(("LOG", "✅ 고급 처리 완료!", "SUCCESS"))
                
            elif mode == "exploration":
                # 데이터 탐색
                self.queue.put(("LOG", "데이터 탐색 모드 실행 중...", "INFO"))
                from preprocess import ToyoDataLoader
                
                loader = ToyoDataLoader(str(input_path))
                summary = loader.get_data_summary()
                
                self.queue.put(("LOG", f"총 채널 수: {len(summary)}", "INFO"))
                for channel, info in summary.items():
                    self.queue.put(("LOG", f"채널 {channel}: {info['data_files']} 파일", "INFO"))
                
                self.queue.put(("LOG", "✅ 데이터 탐색 완료!", "SUCCESS"))
            
            elif mode == "individual":
                # 개별 컴포넌트
                self.queue.put(("LOG", "개별 컴포넌트 모드 실행 중...", "INFO"))
                from preprocess import ToyoDataLoader, ToyoDataProcessor
                
                loader = ToyoDataLoader(str(input_path))
                channels = loader.get_channel_folders()
                
                if channels:
                    channel = channels[0]
                    self.queue.put(("LOG", f"첫 번째 채널 처리: {channel}", "INFO"))
                    
                    battery_data = loader.load_channel_data(channel)
                    self.queue.put(("LOG", f"로드된 데이터: {len(battery_data)} 레코드", "INFO"))
                    
                    processor = ToyoDataProcessor()
                    cleaned_data = processor.clean_and_convert_data(battery_data)
                    self.queue.put(("LOG", f"정제된 데이터: {len(cleaned_data)} 레코드", "INFO"))
                
                self.queue.put(("LOG", "✅ 개별 컴포넌트 처리 완료!", "SUCCESS"))
            
            self.queue.put(("COMPLETE", "처리가 성공적으로 완료되었습니다!", "SUCCESS"))
            
        except Exception as e:
            self.queue.put(("ERROR", f"처리 중 오류 발생: {str(e)}", "ERROR"))
        finally:
            self.queue.put(("DONE", "", ""))
    
    def stop_processing(self):
        """처리 중지"""
        self.processing = False
        self.log_message("사용자에 의해 중지됨", "WARNING")
        self.reset_ui_state()
    
    def reset_ui_state(self):
        """UI 상태 리셋"""
        self.process_button.config(state='normal')
        self.stop_button.config(state='disabled')
        self.progress_bar.stop()
        self.progress_var.set("대기 중...")
    
    def monitor_queue(self):
        """큐 모니터링"""
        try:
            while True:
                msg_type, message, level = self.queue.get_nowait()
                
                if msg_type == "LOG":
                    self.log_message(message, level)
                elif msg_type == "PROGRESS":
                    self.progress_var.set(message)
                elif msg_type == "COMPLETE":
                    self.log_message(message, level)
                    messagebox.showinfo("완료", message)
                elif msg_type == "ERROR":
                    self.log_message(message, level)
                    messagebox.showerror("오류", message)
                elif msg_type == "DONE":
                    self.reset_ui_state()
                    
        except queue.Empty:
            pass
        
        # 100ms 후 다시 확인
        self.root.after(100, self.monitor_queue)
    
    def save_config(self):
        """설정 저장"""
        config = {
            'input_path': self.input_path_var.get(),
            'output_path': self.output_path_var.get(),
            'auto_output': self.auto_output_var.get(),
            'force_reprocess': self.force_reprocess_var.get(),
            'create_viz': self.create_viz_var.get(),
            'save_intermediate': self.save_intermediate_var.get(),
            'save_processed': self.save_processed_var.get(),
            'mode': self.mode_var.get()
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(config, f, indent=2)
    
    def load_config(self):
        """설정 로드"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                
                self.input_path_var.set(config.get('input_path', ''))
                self.output_path_var.set(config.get('output_path', ''))
                self.auto_output_var.set(config.get('auto_output', True))
                self.force_reprocess_var.set(config.get('force_reprocess', False))
                self.create_viz_var.set(config.get('create_viz', True))
                self.save_intermediate_var.set(config.get('save_intermediate', True))
                self.save_processed_var.set(config.get('save_processed', True))
                self.mode_var.set(config.get('mode', 'basic'))
                
                self.toggle_auto_output()
                self.log_message("이전 설정을 불러왔습니다.", "INFO")
                
            except Exception as e:
                self.log_message(f"설정 로드 실패: {e}", "WARNING")


def main():
    """메인 함수"""
    root = tk.Tk()
    app = ToyoPreprocessingGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()