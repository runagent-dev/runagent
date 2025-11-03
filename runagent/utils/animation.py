# runagent/utils/animation.py - Subtle Robotic Runner

import time
import threading
from rich.console import Console
from rich.live import Live
from rich.text import Text
from rich.align import Align
from rich.panel import Panel

console = Console()

class SubtleRoboticRunner:
    """Subtle robotic runner animation with 🤖 as hat in a square field"""
    
    def __init__(self):
        self.running = False
        self.thread = None
        
        # Simple square field with robot-hat runner
        self.field_frames = [
            # Frame 1
            """
    ┌─────────────────────────────────┐
    │                                 │
    │  🤖                             │
    │  🏃‍♂️                             │
    │                                 │
    │         RunAgent                │
    │         Starting...             │
    │                                 │
    └─────────────────────────────────┘
            """,
            # Frame 2
            """
    ┌─────────────────────────────────┐
    │                                 │
    │     🤖                          │
    │     🏃‍♂️                          │
    │                                 │
    │         RunAgent                │
    │         Starting...             │
    │                                 │
    └─────────────────────────────────┘
            """,
            # Frame 3
            """
    ┌─────────────────────────────────┐
    │                                 │
    │        🤖                       │
    │        🏃‍♂️                       │
    │                                 │
    │         RunAgent                │
    │         Starting...             │
    │                                 │
    └─────────────────────────────────┘
            """,
            # Frame 4
            """
    ┌─────────────────────────────────┐
    │                                 │
    │           🤖                    │
    │           🏃‍♂️                    │
    │                                 │
    │         RunAgent                │
    │         Starting...             │
    │                                 │
    └─────────────────────────────────┘
            """,
            # Frame 5
            """
    ┌─────────────────────────────────┐
    │                                 │
    │              🤖                 │
    │              🏃‍♂️                 │
    │                                 │
    │         RunAgent                │
    │         Starting...             │
    │                                 │
    └─────────────────────────────────┘
            """,
            # Frame 6
            """
    ┌─────────────────────────────────┐
    │                                 │
    │                 🤖              │
    │                 🏃‍♂️              │
    │                                 │
    │         RunAgent                │
    │         Starting...             │
    │                                 │
    └─────────────────────────────────┘
            """,
            # Frame 7
            """
    ┌─────────────────────────────────┐
    │                                 │
    │                    🤖           │
    │                    🏃‍♂️           │
    │                                 │
    │         RunAgent                │
    │         Starting...             │
    │                                 │
    └─────────────────────────────────┘
            """,
            # Frame 8
            """
    ┌─────────────────────────────────┐
    │                                 │
    │                       🤖        │
    │                       🏃‍♂️        │
    │                                 │
    │         RunAgent                │
    │         Starting...             │
    │                                 │
    └─────────────────────────────────┘
            """,
        ]
        
        # Alternative: ASCII art version
        self.ascii_frames = [
            # Frame 1
            """
    ┌─────────────────────────────────┐
    │                                 │
    │  🤖                             │
    │  /|\\                            │
    │  / \\                            │
    │                                 │
    │         RunAgent                │
    │         Initializing...         │
    │                                 │
    └─────────────────────────────────┘
            """,
            # Frame 2
            """
    ┌─────────────────────────────────┐
    │                                 │
    │     🤖                          │
    │     /|\\                         │
    │     /  \\                        │
    │                                 │
    │         RunAgent                │
    │         Initializing...         │
    │                                 │
    └─────────────────────────────────┘
            """,
            # Frame 3
            """
    ┌─────────────────────────────────┐
    │                                 │
    │        🤖                       │
    │        /|\\                      │
    │        \\  /                     │
    │                                 │
    │         RunAgent                │
    │         Initializing...         │
    │                                 │
    └─────────────────────────────────┘
            """,
            # Frame 4
            """
    ┌─────────────────────────────────┐
    │                                 │
    │           🤖                    │
    │           /|\\                   │
    │           / \\                   │
    │                                 │
    │         RunAgent                │
    │         Initializing...         │
    │                                 │
    └─────────────────────────────────┘
            """,
        ]
        
        # Minimal version
        self.minimal_frames = [
            """
    ╭─────────────────────────────────╮
    │                                 │
    │  🤖                             │
    │  🏃‍♂️                             │
    │                                 │
    │            RunAgent             │
    │                                 │
    ╰─────────────────────────────────╯
            """,
            """
    ╭─────────────────────────────────╮
    │                                 │
    │      🤖                         │
    │      🏃‍♂️                         │
    │                                 │
    │            RunAgent             │
    │                                 │
    ╰─────────────────────────────────╯
            """,
            """
    ╭─────────────────────────────────╮
    │                                 │
    │          🤖                     │
    │          🏃‍♂️                     │
    │                                 │
    │            RunAgent             │
    │                                 │
    ╰─────────────────────────────────╯
            """,
            """
    ╭─────────────────────────────────╮
    │                                 │
    │              🤖                 │
    │              🏃‍♂️                 │
    │                                 │
    │            RunAgent             │
    │                                 │
    ╰─────────────────────────────────╯
            """,
            """
    ╭─────────────────────────────────╮
    │                                 │
    │                  🤖             │
    │                  🏃‍♂️             │
    │                                 │
    │            RunAgent             │
    │                                 │
    ╰─────────────────────────────────╯
            """,
            """
    ╭─────────────────────────────────╮
    │                                 │
    │                      🤖         │
    │                      🏃‍♂️         │
    │                                 │
    │            RunAgent             │
    │                                 │
    ╰─────────────────────────────────╯
            """,
        ]
    
    def _animate(self, duration=3.0, style="field"):
        """Run the subtle animation"""
        frame_map = {
            "field": self.field_frames,
            "ascii": self.ascii_frames,
            "minimal": self.minimal_frames
        }
        
        frames = frame_map.get(style, self.field_frames)
        start_time = time.time()
        frame_index = 0
        
        with Live(console=console, refresh_per_second=3) as live:
            while self.running and (time.time() - start_time < duration):
                frame_content = frames[frame_index % len(frames)]
                
                # Simple styling based on type
                if style == "minimal":
                    panel = Panel(
                        Align.center(Text(frame_content, style="cyan")),
                        border_style="dim",
                        title="",
                        title_align="center"
                    )
                else:
                    panel = Panel(
                        Align.center(Text(frame_content, style="blue")),
                        border_style="dim blue",
                        title="",
                        title_align="center"
                    )
                
                live.update(panel)
                frame_index += 1
                time.sleep(0.4)  # Smooth but not too fast
    
    def start(self, duration=3.0, style="field"):
        """Start the animation"""
        if self.running:
            return
            
        self.running = True
        self.thread = threading.Thread(
            target=self._animate, 
            args=(duration, style),
            daemon=True
        )
        self.thread.start()
    
    def stop(self):
        """Stop the animation"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)


# Simple function to use in serve command
def show_subtle_robotic_runner(duration=2.5, style="field"):
    """Show subtle robotic runner animation"""
    animation = SubtleRoboticRunner()
    animation.start(duration=duration, style=style)
    
    if animation.thread:
        animation.thread.join()
    
    # Don't clear terminal - maintain continuity


# Even simpler version for quick startup
class QuickRunner:
    """Very simple robotic runner"""
    
    def __init__(self):
        self.running = False
        self.thread = None
    
    def _animate(self, duration=2.0):
        frames = [
            "   🤖\n   🏃‍♂️  RunAgent",
            "     🤖\n     🏃‍♂️  RunAgent", 
            "       🤖\n       🏃‍♂️  RunAgent",
            "         🤖\n         🏃‍♂️  RunAgent",
        ]
        
        start_time = time.time()
        frame_index = 0
        
        with Live(console=console, refresh_per_second=4) as live:
            while self.running and (time.time() - start_time < duration):
                content = frames[frame_index % len(frames)]
                
                panel = Panel(
                    Align.center(Text(content, style="bright_blue")),
                    border_style="dim",
                    title="",
                )
                
                live.update(panel)
                frame_index += 1
                time.sleep(0.3)
    
    def start(self, duration=2.0):
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._animate, args=(duration,), daemon=True)
        self.thread.start()
    
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)


def show_quick_runner(duration=2.0):
    """Show quick simple runner"""
    runner = QuickRunner()
    runner.start(duration)
    
    if runner.thread:
        runner.thread.join()
    
    # Don't clear terminal - maintain continuity