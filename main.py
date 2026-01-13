import sys
import math
import random
import pygame

# ----------------------------
# Constants
# ----------------------------
ROWS = 6
COLS = 7
CELL_SIZE = 100

TOP_BAR = 90
WIDTH = COLS * CELL_SIZE
HEIGHT = ROWS * CELL_SIZE + TOP_BAR
FPS = 60

# Colors
BLUE = (20, 60, 160)
BLACK = (15, 15, 20)
WHITE = (240, 240, 245)
RED = (220, 50, 50)
YELLOW = (240, 210, 60)

# Pieces
EMPTY = 0
P1 = 1
P2 = 2


class Board:
    def __init__(self, rows=ROWS, cols=COLS):
        self.rows = rows
        self.cols = cols
        self.grid = [[EMPTY for _ in range(cols)] for _ in range(rows)]

    def reset(self):
        for r in range(self.rows):
            for c in range(self.cols):
                self.grid[r][c] = EMPTY

    def is_valid_col(self, col: int) -> bool:
        return 0 <= col < self.cols and self.grid[0][col] == EMPTY

    def is_full(self) -> bool:
        return all(self.grid[0][c] != EMPTY for c in range(self.cols))

    def next_open_row(self, col: int):
        if not self.is_valid_col(col):
            return None
        for r in range(self.rows - 1, -1, -1):
            if self.grid[r][col] == EMPTY:
                return r
        return None

    def drop(self, col: int, piece: int):
        """Drops a piece in a column. Returns (row, col) if success, else None."""
        if not self.is_valid_col(col):
            return None

        for r in range(self.rows - 1, -1, -1):
            if self.grid[r][col] == EMPTY:
                self.grid[r][col] = piece
                return (r, col)
        return None

    def check_win(self, piece: int) -> bool:
        g = self.grid

        # Horizontal
        for r in range(self.rows):
            for c in range(self.cols - 3):
                if all(g[r][c+i] == piece for i in range(4)):
                    return True

        # Vertical
        for c in range(self.cols):
            for r in range(self.rows - 3):
                if all(g[r+i][c] == piece for i in range(4)):
                    return True

        # Diagonal down-right
        for r in range(self.rows - 3):
            for c in range(self.cols - 3):
                if all(g[r+i][c+i] == piece for i in range(4)):
                    return True

        # Diagonal up-right
        for r in range(3, self.rows):
            for c in range(self.cols - 3):
                if all(g[r-i][c+i] == piece for i in range(4)):
                    return True

        return False


class Game:
    def __init__(self):
        self.board = Board()
        self.current_player = P1
        self.game_over = False
        self.winner = None  # None, P1, or P2

    def restart(self):
        self.board.reset()
        self.current_player = P1
        self.game_over = False
        self.winner = None

    def play_move(self, col: int) -> str:
        """
        Tries to play a move in `col`.
        Returns: "invalid", "ok", "win", "draw"
        """
        if self.game_over:
            return "invalid"

        placed = self.board.drop(col, self.current_player)
        if placed is None:
            return "invalid"

        # Check win/draw
        if self.board.check_win(self.current_player):
            self.game_over = True
            self.winner = self.current_player
            return "win"

        if self.board.is_full():
            self.game_over = True
            self.winner = None
            return "draw"

        # Switch player
        self.current_player = P2 if self.current_player == P1 else P1
        return "ok"


class UI:
    def __init__(self, game: Game):
        self.game = game

        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Puissance 4 (OOP)")
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont("arial", 32, bold=True)
        self.menu_font = pygame.font.SysFont("arial", 42, bold=True)

        self.hover_col = 0  # column under mouse
        self.falling_piece = None  # dict with col, row, piece, y, v, target_y
        self.in_menu = True
        self.single_player = None
        self.ai_move_due_ms = None
        self.one_player_rect = pygame.Rect(0, 0, 0, 0)
        self.two_player_rect = pygame.Rect(0, 0, 0, 0)

        self.piece_radius = CELL_SIZE // 2 - 8
        self.piece_size = self.piece_radius * 2
        self.chip_images = {
            P1: pygame.transform.smoothscale(
                pygame.image.load("assets/chip1.png").convert_alpha(),
                (self.piece_size, self.piece_size),
            ),
            P2: pygame.transform.smoothscale(
                pygame.image.load("assets/chip2.png").convert_alpha(),
                (self.piece_size, self.piece_size),
            ),
        }

    def run(self):
        while True:
            self.clock.tick(FPS)
            self._handle_events()
            self._update_falling()
            self._update_ai()
            self._draw()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r and not self.in_menu:
                    self.game.restart()
                    self.game.current_player = random.choice([P1, P2])
                    if self.single_player and self.game.current_player == P2:
                        self._schedule_ai_move()

            if event.type == pygame.MOUSEMOTION:
                mx, _ = event.pos
                self.hover_col = max(0, min(COLS - 1, mx // CELL_SIZE))

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.in_menu:
                    self._handle_menu_click(event.pos)
                    continue
                if self.falling_piece is not None or self.game.game_over:
                    continue
                if self.single_player and (self.game.current_player == P2 or self.ai_move_due_ms):
                    continue
                if event.pos[1] <= TOP_BAR:
                    # click on top bar still counts; we use x for column
                    pass
                mx, _ = event.pos
                col = max(0, min(COLS - 1, mx // CELL_SIZE))
                row = self.game.board.next_open_row(col)
                if row is None:
                    continue
                start_y = TOP_BAR // 2 + 10
                target_y = TOP_BAR + row * CELL_SIZE + CELL_SIZE // 2
                self.falling_piece = {
                    "col": col,
                    "row": row,
                    "piece": self.game.current_player,
                    "y": float(start_y),
                    "v": 0.0,
                    "target_y": float(target_y),
                }

    def _update_falling(self):
        if self.falling_piece is None:
            return
        piece = self.falling_piece
        piece["v"] = min(piece["v"] + 2.5, 30.0)
        piece["y"] += piece["v"]
        if piece["y"] >= piece["target_y"]:
            piece["y"] = piece["target_y"]
            self.game.play_move(piece["col"])
            self.falling_piece = None
            if (
                self.single_player
                and not self.game.game_over
                and self.game.current_player == P2
            ):
                self._schedule_ai_move()

    def _schedule_ai_move(self):
        delay_ms = int(random.uniform(1.0, 5.0) * 1000)
        self.ai_move_due_ms = pygame.time.get_ticks() + delay_ms

    def _update_ai(self):
        if not self.single_player or self.game.game_over:
            return
        if self.falling_piece is not None:
            return
        if self.ai_move_due_ms is None:
            return
        if pygame.time.get_ticks() < self.ai_move_due_ms:
            return
        self.ai_move_due_ms = None
        col = self._ai_get_best_col()
        if col is None:
            return
        row = self.game.board.next_open_row(col)
        if row is None:
            return
        start_y = TOP_BAR // 2 + 10
        target_y = TOP_BAR + row * CELL_SIZE + CELL_SIZE // 2
        self.falling_piece = {
            "col": col,
            "row": row,
            "piece": self.game.current_player,
            "y": float(start_y),
            "v": 0.0,
            "target_y": float(target_y),
        }

    def _draw(self):
        # Background
        self.screen.fill(BLACK)

        if self.in_menu:
            self._draw_menu()
            pygame.display.flip()
            return

        # Top bar
        pygame.draw.rect(self.screen, (25, 25, 35), (0, 0, WIDTH, TOP_BAR))

        # Turn / win text
        if self.game.game_over:
            if self.game.winner == P1:
                msg = "RED wins! Press R to restart"
                color = RED
            elif self.game.winner == P2:
                msg = "YELLOW wins! Press R to restart"
                color = YELLOW
            else:
                msg = "Draw! Press R to restart"
                color = WHITE
        else:
            if self.game.current_player == P1:
                msg = "RED's turn"
                color = RED
            else:
                msg = "YELLOW's turn"
                color = YELLOW

        text = self.font.render(msg, True, color)
        self.screen.blit(text, (15, 25))

        # Hover preview piece
        if (
            not self.game.game_over
            and self.falling_piece is None
            and not (self.single_player and self.game.current_player == P2)
        ):
            x = self.hover_col * CELL_SIZE + CELL_SIZE // 2
            y = TOP_BAR // 2 + 10
            hover_img = self.chip_images[self.game.current_player]
            self._blit_center(hover_img, x, y)

        # Board area
        pygame.draw.rect(self.screen, BLUE, (0, TOP_BAR, WIDTH, HEIGHT - TOP_BAR))

        # Draw holes + pieces
        for r in range(ROWS):
            for c in range(COLS):
                x = c * CELL_SIZE + CELL_SIZE // 2
                y = TOP_BAR + r * CELL_SIZE + CELL_SIZE // 2

                # Hole
                pygame.draw.circle(self.screen, BLACK, (x, y), self.piece_radius)

                # Piece
                piece = self.game.board.grid[r][c]
                if piece in self.chip_images:
                    self._blit_center(self.chip_images[piece], x, y)

        if self.falling_piece is not None:
            fall = self.falling_piece
            x = fall["col"] * CELL_SIZE + CELL_SIZE // 2
            y = int(fall["y"])
            self._blit_center(self.chip_images[fall["piece"]], x, y)

        pygame.display.flip()

    def _blit_center(self, image, x, y):
        rect = image.get_rect(center=(x, y))
        self.screen.blit(image, rect)

    def _draw_menu(self):
        title = self.menu_font.render("Puissance 4", True, WHITE)
        self.screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 120))

        self.one_player_rect = pygame.Rect(WIDTH // 2 - 160, 260, 320, 70)
        self.two_player_rect = pygame.Rect(WIDTH // 2 - 160, 360, 320, 70)

        pygame.draw.rect(self.screen, (50, 50, 70), self.one_player_rect, border_radius=8)
        pygame.draw.rect(self.screen, (50, 50, 70), self.two_player_rect, border_radius=8)

        one_text = self.font.render("1 Player", True, WHITE)
        two_text = self.font.render("2 Players", True, WHITE)
        self._blit_center(one_text, self.one_player_rect.centerx, self.one_player_rect.centery)
        self._blit_center(two_text, self.two_player_rect.centerx, self.two_player_rect.centery)

    def _handle_menu_click(self, pos):
        if self.one_player_rect.collidepoint(pos):
            self.single_player = True
            self.in_menu = False
            self.game.restart()
            self.game.current_player = random.choice([P1, P2])
            if self.game.current_player == P2:
                self._schedule_ai_move()
        if self.two_player_rect.collidepoint(pos):
            self.single_player = False
            self.in_menu = False
            self.game.restart()
            self.game.current_player = random.choice([P1, P2])

    def _ai_get_best_col(self):
        grid = [row[:] for row in self.game.board.grid]
        depth = 4
        col, _ = self._minimax(grid, depth, -math.inf, math.inf, True)
        if col is None:
            valid_cols = self._get_valid_cols(grid)
            return random.choice(valid_cols) if valid_cols else None
        return col

    def _minimax(self, grid, depth, alpha, beta, maximizing):
        valid_cols = self._get_valid_cols(grid)
        terminal = self._is_terminal_node(grid)
        if depth == 0 or terminal:
            if terminal:
                if self._check_win_grid(grid, P2):
                    return None, 1000000
                if self._check_win_grid(grid, P1):
                    return None, -1000000
                return None, 0
            return None, self._score_position(grid, P2)

        if maximizing:
            value = -math.inf
            best_col = random.choice(valid_cols)
            for col in valid_cols:
                row = self._next_open_row_grid(grid, col)
                temp = [r[:] for r in grid]
                self._drop_in_grid(temp, row, col, P2)
                _, new_score = self._minimax(temp, depth - 1, alpha, beta, False)
                if new_score > value:
                    value = new_score
                    best_col = col
                alpha = max(alpha, value)
                if alpha >= beta:
                    break
            return best_col, value

        value = math.inf
        best_col = random.choice(valid_cols)
        for col in valid_cols:
            row = self._next_open_row_grid(grid, col)
            temp = [r[:] for r in grid]
            self._drop_in_grid(temp, row, col, P1)
            _, new_score = self._minimax(temp, depth - 1, alpha, beta, True)
            if new_score < value:
                value = new_score
                best_col = col
            beta = min(beta, value)
            if alpha >= beta:
                break
        return best_col, value

    def _is_terminal_node(self, grid):
        return (
            self._check_win_grid(grid, P1)
            or self._check_win_grid(grid, P2)
            or len(self._get_valid_cols(grid)) == 0
        )

    def _get_valid_cols(self, grid):
        return [c for c in range(COLS) if grid[0][c] == EMPTY]

    def _next_open_row_grid(self, grid, col):
        for r in range(ROWS - 1, -1, -1):
            if grid[r][col] == EMPTY:
                return r
        return None

    def _drop_in_grid(self, grid, row, col, piece):
        grid[row][col] = piece

    def _check_win_grid(self, grid, piece):
        for r in range(ROWS):
            for c in range(COLS - 3):
                if all(grid[r][c + i] == piece for i in range(4)):
                    return True
        for c in range(COLS):
            for r in range(ROWS - 3):
                if all(grid[r + i][c] == piece for i in range(4)):
                    return True
        for r in range(ROWS - 3):
            for c in range(COLS - 3):
                if all(grid[r + i][c + i] == piece for i in range(4)):
                    return True
        for r in range(3, ROWS):
            for c in range(COLS - 3):
                if all(grid[r - i][c + i] == piece for i in range(4)):
                    return True
        return False

    def _score_position(self, grid, piece):
        score = 0
        center_col = COLS // 2
        center_count = sum(1 for r in range(ROWS) if grid[r][center_col] == piece)
        score += center_count * 3

        for r in range(ROWS):
            row_array = [grid[r][c] for c in range(COLS)]
            for c in range(COLS - 3):
                window = row_array[c : c + 4]
                score += self._evaluate_window(window, piece)

        for c in range(COLS):
            col_array = [grid[r][c] for r in range(ROWS)]
            for r in range(ROWS - 3):
                window = col_array[r : r + 4]
                score += self._evaluate_window(window, piece)

        for r in range(ROWS - 3):
            for c in range(COLS - 3):
                window = [grid[r + i][c + i] for i in range(4)]
                score += self._evaluate_window(window, piece)

        for r in range(3, ROWS):
            for c in range(COLS - 3):
                window = [grid[r - i][c + i] for i in range(4)]
                score += self._evaluate_window(window, piece)

        return score

    def _evaluate_window(self, window, piece):
        score = 0
        opp_piece = P1 if piece == P2 else P2
        if window.count(piece) == 4:
            score += 100
        elif window.count(piece) == 3 and window.count(EMPTY) == 1:
            score += 5
        elif window.count(piece) == 2 and window.count(EMPTY) == 2:
            score += 2
        if window.count(opp_piece) == 3 and window.count(EMPTY) == 1:
            score -= 4
        return score


def main():
    game = Game()
    ui = UI(game)
    ui.run()


if __name__ == "__main__":
    main()
