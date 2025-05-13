import random

COLORS = [
    "\033[31m",  # Red
    "\033[32m",  # Green
    "\033[33m",  # Yellow
    "\033[34m",  # Blue
    "\033[35m",  # Magenta
    "\033[36m",  # Cyan
]

RESET_COLOR = "\033[0m"
_last_color = None

def get_colored_text(text):
    """
    Returns the given text wrapped in a random ANSI color escape code,
    ensuring that the same color is not used consecutively.
    """
    global _last_color
    available_colors = [c for c in COLORS if c != _last_color]
    color = random.choice(available_colors)
    _last_color = color
    return f"{color}{text}{RESET_COLOR}"