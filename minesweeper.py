import tkinter as tk
from tkinter import messagebox
import random

class Minesweeper:
    """
    Tkinter를 사용하여 만든 지뢰찾기 게임 클래스.
    """
    def __init__(self, root, width=10, height=10, mines=10):
        self.root = root
        self.width = width
        self.height = height
        self.mines = mines

        # 게임 상태 변수
        self.flags = 0
        self.game_over = False
        self.first_click = True

        # 프레임 생성
        self.top_frame = tk.Frame(root)
        self.top_frame.pack()

        self.game_frame = tk.Frame(root)
        self.game_frame.pack()

        # UI 요소 생성
        self.flag_label = tk.Label(self.top_frame, text=f"깃발: {self.flags}/{self.mines}", font=("Arial", 12))
        self.flag_label.pack(side=tk.LEFT, padx=10)

        self.restart_button = tk.Button(self.top_frame, text="다시 시작", command=self.restart_game)
        self.restart_button.pack(side=tk.RIGHT, padx=10)
        
        # 게임 보드와 버튼 딕셔너리 초기화
        self.buttons = {}
        self.mine_locations = set()
        
        self.create_board()
        self.place_mines()

    def create_board(self):
        """게임 보드의 버튼들을 생성합니다."""
        for r in range(self.height):
            for c in range(self.width):
                btn = tk.Button(self.game_frame, width=3, height=1, font=("Arial", 10, "bold"))
                btn.grid(row=r, column=c)
                # 버튼에 좌클릭과 우클릭 이벤트를 바인딩합니다.
                # 람다 함수를 사용하여 각 버튼의 위치(r, c)를 전달합니다.
                btn.bind("<Button-1>", lambda e, r=r, c=c: self.on_left_click(r, c))
                btn.bind("<Button-3>", lambda e, r=r, c=c: self.on_right_click(r, c))
                self.buttons[(r, c)] = btn

    def place_mines(self):
        """지뢰를 무작위로 배치합니다."""
        self.mine_locations.clear()
        total_cells = self.width * self.height
        
        # 모든 셀의 좌표 리스트를 생성합니다.
        all_cells = [(r, c) for r in range(self.height) for c in range(self.width)]
        
        # 지뢰를 무작위로 선택합니다.
        self.mine_locations = set(random.sample(all_cells, self.mines))

    def restart_game(self):
        """게임을 초기 상태로 리셋합니다."""
        self.game_over = False
        self.first_click = True
        self.flags = 0
        self.update_flag_label()
        
        # 기존 버튼들을 초기화합니다.
        for (r, c), btn in self.buttons.items():
            btn.config(text="", state=tk.NORMAL, bg="SystemButtonFace", relief=tk.RAISED)

        self.place_mines()

    def get_neighbors(self, r, c):
        """지정된 셀의 주변 8개 이웃 셀의 좌표를 반환합니다."""
        neighbors = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.height and 0 <= nc < self.width:
                    neighbors.append((nr, nc))
        return neighbors

    def count_adjacent_mines(self, r, c):
        """주변 8개 셀에 포함된 지뢰의 개수를 계산합니다."""
        count = 0
        for nr, nc in self.get_neighbors(r, c):
            if (nr, nc) in self.mine_locations:
                count += 1
        return count

    def reveal_cell(self, r, c):
        """셀을 열고, 주변 지뢰 개수를 표시하거나 연쇄적으로 엽니다."""
        btn = self.buttons[(r, c)]
        if btn['state'] == tk.DISABLED:
            return

        btn.config(state=tk.DISABLED, relief=tk.SUNKEN, bg='light gray')

        adjacent_mines = self.count_adjacent_mines(r, c)

        if adjacent_mines > 0:
            # 주변 지뢰 개수에 따라 색상을 다르게 표시
            colors = {1: "blue", 2: "green", 3: "red", 4: "purple", 5: "maroon", 6: "turquoise", 7: "black", 8: "gray"}
            btn.config(text=str(adjacent_mines), disabledforeground=colors.get(adjacent_mines, "black"))
        else:
            # 주변에 지뢰가 없으면 이웃 셀들을 재귀적으로 엽니다 (Flood Fill)
            for nr, nc in self.get_neighbors(r, c):
                self.reveal_cell(nr, nc)
        
        self.check_win()

    def on_left_click(self, r, c):
        """마우스 좌클릭 이벤트 처리."""
        if self.game_over:
            return

        # 첫 번째 클릭이 지뢰인 경우, 지뢰 위치를 재설정
        if self.first_click:
            self.first_click = False
            if (r, c) in self.mine_locations:
                self.mine_locations.remove((r, c))
                
                # 새로운 지뢰 위치 찾기
                all_cells = [(row, col) for row in range(self.height) for col in range(self.width)]
                available_cells = list(set(all_cells) - self.mine_locations - {(r, c)})
                new_mine_location = random.choice(available_cells)
                self.mine_locations.add(new_mine_location)

        if (r, c) in self.mine_locations:
            self.show_game_over(win=False)
            return

        self.reveal_cell(r, c)

    def on_right_click(self, r, c):
        """마우스 우클릭 이벤트 처리 (깃발)."""
        if self.game_over:
            return

        btn = self.buttons[(r, c)]
        if btn['state'] == tk.DISABLED:
            return
        
        # 깃발 표시/제거 토글
        if btn['text'] == "🚩":
            btn.config(text="")
            self.flags -= 1
        else:
            if self.flags < self.mines:
                btn.config(text="🚩", foreground="red")
                self.flags += 1
        
        self.update_flag_label()

    def update_flag_label(self):
        """깃발 개수 레이블을 업데이트합니다."""
        self.flag_label.config(text=f"깃발: {self.flags}/{self.mines}")

    def check_win(self):
        """게임 승리 조건을 확인합니다."""
        opened_cells = 0
        for btn in self.buttons.values():
            if btn['state'] == tk.DISABLED:
                opened_cells += 1
        
        if opened_cells == (self.width * self.height - self.mines):
            self.show_game_over(win=True)

    def show_game_over(self, win):
        """게임 종료 처리 및 메시지 박스 표시."""
        self.game_over = True
        for (r, c), btn in self.buttons.items():
            if (r, c) in self.mine_locations:
                btn.config(text="💣", bg="red" if not win else "green")
            btn.config(state=tk.DISABLED)

        if win:
            messagebox.showinfo("지뢰찾기", "축하합니다! 모든 지뢰를 찾았습니다!")
        else:
            messagebox.showerror("지뢰찾기", "게임 오버! 지뢰를 밟았습니다.")


if __name__ == "__main__":
    root = tk.Tk()
    root.title("지뢰찾기")
    # 게임 난이도 설정: root, 가로, 세로, 지뢰 개수
    # 초급: 10, 10, 10
    # 중급: 16, 16, 40
    # 고급: 30, 16, 99
    game = Minesweeper(root, width=10, height=10, mines=10)
    root.mainloop()