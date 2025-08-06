"""
Base GUI Components and Architecture

확장 가능한 GUI 기반 클래스 및 공통 컴포넌트
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import json
from pathlib import Path
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List


class BaseGUIComponent(ABC):
    """GUI 컴포넌트 기본 클래스"""
    
    def __init__(self, parent, **kwargs):
        self.parent = parent
        self.config = kwargs
        self.setup_component()
    
    @abstractmethod
    def setup_component(self):
        """컴포넌트 설정"""
        pass
    
    @abstractmethod
    def get_frame(self) -> ttk.Frame:
        """컴포넌트 프레임 반환"""
        pass


class ConfigManager:
    """설정 관리 클래스"""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            self.config_dir = Path.home() / ".toyo_preprocessing"
        else:
            self.config_dir = Path(config_dir)
        
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self.profiles_file = self.config_dir / "profiles.json"
        
        self.current_config = self.load_config()
        self.profiles = self.load_profiles()
    
    def load_config(self) -> Dict[str, Any]:
        """설정 로드"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return self.get_default_config()
    
    def save_config(self, config: Dict[str, Any] = None):
        """설정 저장"""
        if config is None:
            config = self.current_config
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def get_default_config(self) -> Dict[str, Any]:
        """기본 설정"""
        return {
            'input_path': '',
            'output_path': '',
            'auto_output': True,
            'force_reprocess': False,
            'create_viz': True,
            'save_intermediate': True,
            'save_processed': True,
            'mode': 'basic',
            'window_geometry': '900x700',
            'theme': 'clam',
            'log_level': 'INFO'
        }
    
    def load_profiles(self) -> Dict[str, Any]:
        """프로파일 로드"""
        if self.profiles_file.exists():
            try:
                with open(self.profiles_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"default": self.get_default_config()}
    
    def save_profiles(self):
        """프로파일 저장"""
        with open(self.profiles_file, 'w', encoding='utf-8') as f:
            json.dump(self.profiles, f, indent=2, ensure_ascii=False)
    
    def create_profile(self, name: str, config: Dict[str, Any]):
        """새 프로파일 생성"""
        self.profiles[name] = config.copy()
        self.save_profiles()
    
    def load_profile(self, name: str) -> Dict[str, Any]:
        """프로파일 로드"""
        return self.profiles.get(name, self.get_default_config()).copy()
    
    def delete_profile(self, name: str):
        """프로파일 삭제"""
        if name != "default" and name in self.profiles:
            del self.profiles[name]
            self.save_profiles()


class TaskQueue:
    """작업 큐 관리"""
    
    def __init__(self):
        self.queue = queue.Queue()
        self.processing = False
        self.current_task = None
        self.callbacks: Dict[str, Callable] = {}
    
    def add_callback(self, msg_type: str, callback: Callable):
        """콜백 추가"""
        self.callbacks[msg_type] = callback
    
    def put(self, msg_type: str, message: str, level: str = "INFO", data: Any = None):
        """메시지 추가"""
        self.queue.put((msg_type, message, level, data))
    
    def process_messages(self):
        """메시지 처리"""
        try:
            while True:
                msg_type, message, level, data = self.queue.get_nowait()
                
                if msg_type in self.callbacks:
                    self.callbacks[msg_type](message, level, data)
                    
        except queue.Empty:
            pass


class ProcessingThread(threading.Thread):
    """백그라운드 처리 스레드"""
    
    def __init__(self, task_queue: TaskQueue, target_func: Callable, *args, **kwargs):
        super().__init__(daemon=True)
        self.task_queue = task_queue
        self.target_func = target_func
        self.args = args
        self.kwargs = kwargs
        self.stop_event = threading.Event()
    
    def run(self):
        """스레드 실행"""
        try:
            self.task_queue.processing = True
            self.target_func(self.task_queue, self.stop_event, *self.args, **self.kwargs)
        except Exception as e:
            self.task_queue.put("ERROR", f"처리 중 오류 발생: {str(e)}", "ERROR")
        finally:
            self.task_queue.processing = False
            self.task_queue.put("DONE", "처리 완료", "INFO")
    
    def stop(self):
        """스레드 중지"""
        self.stop_event.set()


class StyleManager:
    """UI 스타일 관리"""
    
    def __init__(self):
        self.style = ttk.Style()
        self.colors = {
            'primary': '#2196F3',
            'success': '#4CAF50',
            'warning': '#FF9800',
            'error': '#F44336',
            'info': '#2196F3',
            'bg': '#F5F5F5',
            'fg': '#212121',
            'bg_dark': '#263238',
            'fg_dark': '#FFFFFF'
        }
        self.setup_styles()
    
    def setup_styles(self):
        """스타일 설정"""
        # 기본 테마 설정
        self.style.theme_use('clam')
        
        # 버튼 스타일
        button_styles = [
            ('Primary.TButton', self.colors['primary'], '#1976D2'),
            ('Success.TButton', self.colors['success'], '#388E3C'),
            ('Warning.TButton', self.colors['warning'], '#F57C00'),
            ('Error.TButton', self.colors['error'], '#D32F2F')
        ]
        
        for style_name, bg_color, active_color in button_styles:
            self.style.configure(style_name,
                               background=bg_color,
                               foreground='white',
                               borderwidth=0,
                               focuscolor='none',
                               padding=(10, 8))
            self.style.map(style_name,
                         background=[('active', active_color)])
        
        # 프레임 스타일
        self.style.configure('Card.TFrame',
                           relief='raised',
                           borderwidth=1,
                           padding=10)
        
        # 라벨 스타일
        self.style.configure('Title.TLabel',
                           font=('Segoe UI', 16, 'bold'))
        self.style.configure('Subtitle.TLabel',
                           font=('Segoe UI', 12, 'bold'))
        self.style.configure('Caption.TLabel',
                           font=('Segoe UI', 9),
                           foreground='#666666')


class LogManager:
    """로그 관리 클래스"""
    
    def __init__(self, log_widget, max_lines: int = 1000):
        self.log_widget = log_widget
        self.max_lines = max_lines
        self.setup_tags()
    
    def setup_tags(self):
        """로그 태그 설정"""
        tags = {
            'INFO': {'foreground': 'black'},
            'SUCCESS': {'foreground': '#4CAF50'},
            'WARNING': {'foreground': '#FF9800'},
            'ERROR': {'foreground': '#F44336'},
            'DEBUG': {'foreground': '#666666'}
        }
        
        for tag, config in tags.items():
            self.log_widget.tag_config(tag, **config)
    
    def log(self, message: str, level: str = "INFO"):
        """로그 메시지 추가"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_widget.insert(tk.END, formatted_message, level)
        self.log_widget.see(tk.END)
        
        # 최대 라인 수 제한
        lines = self.log_widget.get("1.0", tk.END).count('\n')
        if lines > self.max_lines:
            excess = lines - self.max_lines
            self.log_widget.delete("1.0", f"{excess}.0")
        
        self.log_widget.update()
    
    def clear(self):
        """로그 지우기"""
        self.log_widget.delete(1.0, tk.END)


class ValidationMixin:
    """입력 유효성 검사 믹스인"""
    
    @staticmethod
    def validate_path(path: str) -> tuple[bool, str]:
        """경로 유효성 검사"""
        if not path:
            return False, "경로가 비어있습니다."
        
        path_obj = Path(path)
        if not path_obj.exists():
            return False, f"경로가 존재하지 않습니다: {path}"
        
        if not path_obj.is_dir():
            return False, f"디렉토리가 아닙니다: {path}"
        
        return True, ""
    
    @staticmethod
    def validate_required_field(value: str, field_name: str) -> tuple[bool, str]:
        """필수 필드 검사"""
        if not value or value.strip() == "":
            return False, f"{field_name}은(는) 필수입니다."
        return True, ""


class EventManager:
    """이벤트 관리 클래스"""
    
    def __init__(self):
        self.events: Dict[str, List[Callable]] = {}
    
    def subscribe(self, event_name: str, callback: Callable):
        """이벤트 구독"""
        if event_name not in self.events:
            self.events[event_name] = []
        self.events[event_name].append(callback)
    
    def unsubscribe(self, event_name: str, callback: Callable):
        """이벤트 구독 취소"""
        if event_name in self.events and callback in self.events[event_name]:
            self.events[event_name].remove(callback)
    
    def emit(self, event_name: str, *args, **kwargs):
        """이벤트 발생"""
        if event_name in self.events:
            for callback in self.events[event_name]:
                try:
                    callback(*args, **kwargs)
                except Exception as e:
                    print(f"이벤트 콜백 오류: {e}")


class ProgressTracker:
    """진행 상태 추적"""
    
    def __init__(self, total_steps: int = 0):
        self.total_steps = total_steps
        self.current_step = 0
        self.step_info = {}
        self.callbacks = []
    
    def add_callback(self, callback: Callable):
        """콜백 추가"""
        self.callbacks.append(callback)
    
    def set_total_steps(self, total: int):
        """전체 단계 수 설정"""
        self.total_steps = total
        self._notify()
    
    def update_step(self, step: int, info: str = ""):
        """현재 단계 업데이트"""
        self.current_step = step
        if info:
            self.step_info[step] = info
        self._notify()
    
    def next_step(self, info: str = ""):
        """다음 단계로"""
        self.update_step(self.current_step + 1, info)
    
    def get_progress(self) -> float:
        """진행률 반환 (0.0 ~ 1.0)"""
        if self.total_steps == 0:
            return 0.0
        return min(self.current_step / self.total_steps, 1.0)
    
    def get_progress_text(self) -> str:
        """진행률 텍스트 반환"""
        if self.total_steps == 0:
            return "진행률 계산 중..."
        
        progress = self.get_progress() * 100
        current_info = self.step_info.get(self.current_step, "")
        
        if current_info:
            return f"{progress:.1f}% - {current_info}"
        return f"{progress:.1f}% ({self.current_step}/{self.total_steps})"
    
    def _notify(self):
        """콜백 호출"""
        for callback in self.callbacks:
            try:
                callback(self)
            except Exception as e:
                print(f"진행 상태 콜백 오류: {e}")