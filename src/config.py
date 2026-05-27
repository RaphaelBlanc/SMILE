import os
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCREEN_WIDTH  = 1920
SCREEN_HEIGHT = 1072
def format_time(ms):
    if ms is None:
        return "--:--.---"
    ms = int(ms)
    minutes = ms // 60000
    seconds = (ms % 60000) // 1000
    millis = ms % 1000
    return f"{minutes:02d}:{seconds:02d}.{millis:03d}"
