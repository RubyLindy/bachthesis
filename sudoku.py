import tkinter as tk
from tkinter import messagebox
from sudoku_context import set_context, set_hint
from copy import deepcopy


def get_next_correct_move_from_board(board):
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

    solved = deepcopy(board)
    if not solve(solved):
        return None

    for i in range(9):
        for j in range(9):
            if board[i][j] == 0:
                return (i, j, solved[i][j])
    return None


class SudokuUI:
    def __init__(self, root, puzzle_file="puzzle2.txt"):
        self.root = root
        self.root.title("Sudoku")

        self.entries = [[None for _ in range(9)] for _ in range(9)]
        self.puzzle = self.load_puzzle(puzzle_file)
        self.create_grid()

        check_button = tk.Button(self.root, text="Check Validity", command=self.check_valid)
        check_button.pack(pady=5)

        hint_button = tk.Button(self.root, text="Get Hint", command=self.show_hint)
        hint_button.pack(pady=5)

    def load_puzzle(self, filename):
        with open(filename, "r") as f:
            lines = f.readlines()

        puzzle = []
        for line in lines:
            row = [int(c) for c in line.strip() if c.isdigit()]
            if len(row) != 9:
                raise ValueError("Each line must contain exactly 9 digits")
            puzzle.append(row)

        if len(puzzle) != 9:
            raise ValueError("Puzzle must have exactly 9 lines")
        return puzzle

    def create_grid(self):
        board_frame = tk.Frame(self.root, bg="black")
        board_frame.pack(padx=10, pady=10)

        block_frames = [[None for _ in range(3)] for _ in range(3)]
        for block_row in range(3):
            for block_col in range(3):
                frame = tk.Frame(board_frame, bg="black", bd=2, relief="solid")
                frame.grid(row=block_row, column=block_col, padx=2, pady=2)
                block_frames[block_row][block_col] = frame

        for i in range(9):
            for j in range(9):
                block_row, block_col = i // 3, j // 3
                val = self.puzzle[i][j]
                entry = tk.Entry(
                    block_frames[block_row][block_col],
                    width=2,
                    font=('Arial', 18),
                    justify='center',
                    bd=1,
                    relief='solid',
                    disabledforeground="black"
                )
                if val != 0:
                    entry.insert(0, str(val))
                    entry.config(state='disabled')
                entry.grid(row=i % 3, column=j % 3, padx=1, pady=1)
                self.entries[i][j] = entry

    def get_board(self):
        board = []
        for i in range(9):
            row = []
            for j in range(9):
                val = self.entries[i][j].get()
                row.append(int(val) if val.isdigit() else 0)
            board.append(row)
        return board

    def check_valid(self):
        board = self.get_board()
        if self.is_valid_sudoku(board):
            messagebox.showinfo("Result", "This is a valid Sudoku board so far!")
        else:
            messagebox.showwarning("Result", "Invalid Sudoku setup!")

    def is_valid_sudoku(self, board):
        def is_valid_block(block):
            nums = [n for n in block if n != 0]
            return len(nums) == len(set(nums))

        for i in range(9):
            row = board[i]
            col = [board[j][i] for j in range(9)]
            if not is_valid_block(row) or not is_valid_block(col):
                return False

        for i in range(3):
            for j in range(3):
                block = [board[x][y] for x in range(i * 3, i * 3 + 3)
                                       for y in range(j * 3, j * 3 + 3)]
                if not is_valid_block(block):
                    return False

        return True

    def get_sudoku_context(self):
        board = self.get_board()
        context = "Current Sudoku board:\n"
        for row in board:
            context += " ".join(str(num) if num != 0 else "_" for num in row) + "\n"
        return context

    def update_context(self):
        ctx = self.get_sudoku_context()
        set_context(ctx)

    def show_hint(self):
        board = self.get_board()
        hint = get_next_correct_move_from_board(board)
        if hint:
            i, j, val = hint
            entry = self.entries[i][j]
            entry.delete(0, tk.END)
            entry.insert(0, str(val))
            entry.config(fg="blue")  # visually distinguish hint
        else:
            messagebox.showinfo("Hint", "No hints available. Puzzle may be complete or unsolvable.")


if __name__ == "__main__":
    root = tk.Tk()
    app = SudokuUI(root, puzzle_file="puzzle2.txt")
    root.mainloop()
