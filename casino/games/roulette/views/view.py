import time
import sys
import shutil
import re
import casino.utils as utils

from casino.types import GameContext
from casino.utils import clear_screen, cprint, cinput, display_topbar
from ..constants import ROWS, COLS, SEC_BTWN_SPIN

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def _visible_len(s: str) -> int:
    return len(ANSI_RE.sub("", s))


def cprint_ansi_center(line: str, end: str = "\n") -> None:
    """Center a string that may contain ANSI escape codes."""
    width = shutil.get_terminal_size().columns
    vis = _visible_len(line)
    pad_left = max(0, (width - vis) // 2)
    print((" " * pad_left) + line, end=end)


def cprint_table_center(block: str) -> None:
    lines = block.strip("\n").splitlines()
    term_width = shutil.get_terminal_size().columns

    max_len = max(_visible_len(line) for line in lines)
    pad_left = max(0, (term_width - max_len) // 2)

    for line in lines:
        padded_line = " " * pad_left + line
        print(f"{utils.theme['color']}{padded_line}{utils.theme['reset']}")


def render_cell(num_str: str, color: str) -> str:
    bg = {"black": "40",
          "red": "41",
          "green": "42"}
    return f"\x1b[{bg[color]}m\x1b[97m{num_str}\x1b[0m"


class RouletteView:
    """
    Contains the methods that draw roulette in the terminal: the top bar,
    the wheel and its spin animation, the betting table, and menus.

    Args:
        header_options (dict): Header passed to `display_topbar()`.
        table (str): The variant's betting table.
    """

    def __init__(self, header_options: dict, table: str) -> None:
        self.header_options = header_options
        self.table = table

    def display_topbar(self, ctx: GameContext) -> None:
        display_topbar(ctx.account, **self.header_options)

    def refresh_topbar(self, ctx: GameContext) -> None:
        # Number of lines occupied by the topbar: header (3 lines) + user/balance line + margin
        header_lines = len(self.header_options["header"].strip("\n").splitlines())
        margin = self.header_options.get("margin", 1)
        total_lines = header_lines + 1 + margin

        sys.stdout.write("\x1b[s")  # Save current cursor position
        sys.stdout.write("\x1b[H")  # Move cursor to top-left corner

        # Clear all topbar lines
        for _ in range(total_lines):
            sys.stdout.write("\x1b[2K")  # clear line
            sys.stdout.write("\x1b[1B")  # down 1 line

        # Move back to top-left and redraw the topbar
        sys.stdout.write("\x1b[H")
        self.display_topbar(ctx)

        # Restore cursor position so the rest of the screen stays intact
        sys.stdout.write("\x1b[u")
        sys.stdout.flush()

    def render_header(self, ctx: GameContext) -> None:
        clear_screen()
        self.display_topbar(ctx)

    def print_wheel(self, wheel, highlighted_num=None) -> None:
        # each empty spot is a single space and numbers take up 2
        grid = [[' ' for _ in range(COLS)] for _ in range(ROWS)]

        for (num_str, color, row, col) in wheel:
            if num_str != "00" and int(num_str.strip()) < 10:
                num_str = " " + num_str
            if highlighted_num is not None and num_str.strip() == highlighted_num.strip():
                # the spot in the column before and column after the number become *'s
                grid[row][col - 1] = "*"
                grid[row][col + 1] = "*"
            grid[row][col] = render_cell(num_str, color)

        wheel_lines = ["".join(row) for row in grid]
        # Center the wheel in the terminal
        for line in wheel_lines:
            cprint_ansi_center(line)

    def wheel_animation(self, ctx: GameContext, wheel, sequence,
                        sec_btwn_spins: float = SEC_BTWN_SPIN) -> None:
        for num in sequence:
            clear_screen()
            self.display_topbar(ctx)
            self.print_wheel(wheel, highlighted_num=num)
            time.sleep(sec_btwn_spins)

    def render_outside_bets_menu(self, ctx: GameContext) -> None:
        self.render_header(ctx)
        title = "Outside bets:"
        options = [
            "[1] Red / Black",
            "[2] Odd / Even",
            "[3] High / Low",
            "[4] Dozen",
            "[5] Column",
        ]

        content_width = max(len(title), *(len(o) for o in options))
        left_pad = 2
        right_pad = 2
        box_width = content_width + left_pad + right_pad

        cprint("┌" + "─" * box_width + "┐")
        cprint("│" + title.center(box_width) + "│")
        cprint("│" + " " * box_width + "│")

        for opt in options:
            line = " " * left_pad + opt.ljust(content_width) + " " * right_pad
            cprint("│" + line + "│")

        cprint("└" + "─" * box_width + "┘")

    def prompt_with_error(self, ctx: GameContext, prompt: str, validator, error_text: str,
                          render_table: bool = False,
                          transform=lambda s: s.strip().lower(),):
        last_error = ""
        while True:
            self.render_header(ctx)
            if render_table:
                cprint_table_center(self.table)
            if last_error:
                cprint(f"🤵: {last_error}")

            answer = transform(cinput(prompt))
            if validator(answer):
                return answer
            last_error = error_text
