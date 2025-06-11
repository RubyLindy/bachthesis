from copy import deepcopy

latest_context = ""
latest_hint = ""

def set_context(ctx):
    global latest_context
    latest_context = ctx

def get_context():
    return latest_context

def set_hint(hint):
    global latest_hint
    latest_hint = hint

def get_hint():
    return latest_hint

from copy import deepcopy

def generate_hint_from_file(puzzle_file="puzzle2.txt"):
    def is_valid(board, row, col, num):
        for i in range(9):
            if board[row][i] == num or board[i][col] == num:
                return False
        start_row, start_col = 3 * (row // 3), 3 * (col // 3)
        for i in range(3):
            for j in range(3):
                if board[start_row + i][start_col + j] == num:
                    return False
        return True

    def solve(board):
        for row in range(9):
            for col in range(9):
                if board[row][col] == 0:
                    for num in range(1, 10):
                        if is_valid(board, row, col, num):
                            board[row][col] = num
                            if solve(board):
                                return True
                            board[row][col] = 0
                    return False
        return True

    # Load board from file
    with open(puzzle_file, "r") as f:
        lines = f.readlines()

    board = []
    for line in lines:
        row = [int(c) for c in line.strip() if c.isdigit()]
        board.append(row)

    solved = deepcopy(board)
    if not solve(solved):
        return "No hints available. Puzzle may be complete or unsolvable."

    for i in range(9):
        for j in range(9):
            if board[i][j] == 0:
                return f"The correct next move is to place {solved[i][j]} at row {i+1}, column {j+1}."

    return "No empty cells found."