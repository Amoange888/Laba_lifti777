

import tkinter as tk
CYCLE_MS = 100
PUMP_RATE = 2.0
LEAK_STEP = 1.0
LEAK_MAX = 4
INITIAL_LEVEL = 77.0
LEVEL_START_1 = 50
LEVEL_START_2 = 25
LEVEL_STOP = 100

WIDTH, HEIGHT = 1000, 680

# ---- Палитра ----
BG          = "#141922"
BG_PANEL    = "#1e2633"
PANEL_EDGE  = "#2f3b4d"

TEXT        = "#e6edf5"
TEXT_DIM    = "#7a8ca3"
ACCENT      = "#3fc1c9"

TANK_BG     = "#0d131c"
TANK_EDGE   = "#3a4a60"
WATER       = "#2e8bc0"
WATER_HI    = "#4fb3e8"
WATER_DARK  = "#1c5f8a"

PIPE        = "#3a4a60"
PIPE_HI     = "#5b6f8a"

PUMP_OFF    = "#2a3444"
PUMP_OFF_E  = "#4a5a74"
PUMP_ON     = "#2ecc71"
PUMP_ON_E   = "#1f9c52"
PUMP_ERR    = "#e74c3c"
PUMP_ERR_E  = "#a02a1e"

BTN         = "#2a3444"
BTN_HOVER   = "#38465a"
BTN_EDGE    = "#4a5a74"
BTN_ACTIVE  = "#3fc1c9"
BTN_ACTIVE_DK = "#2a8b92"
BTN_DANGER  = "#8a3030"
BTN_DANGER_H = "#a83a3a"

RED         = "#e74c3c"
GREEN       = "#2ecc71"


# ============================================================
#  МОДЕЛЬ
# ============================================================
class Pump:
    def __init__(self, pid):
        self.id = pid
        self.running = False
        self.error = False
        self.work_time = 0


class PumpSystem:
    def __init__(self):
        self.pumps = [Pump(1), Pump(2), Pump(3)]
        self.level = INITIAL_LEVEL
        self.cycle_counter = 0
        self.leak = 3
        self.started = False
        self.system_error = False

    def step(self):
        if not self.started:
            return
        self.cycle_counter += 1

        for p in self.pumps:
            if p.running and not p.error:
                p.work_time += 1

        for p in self.pumps:
            if p.running and p.error:
                p.running = False

        running = sum(1 for p in self.pumps if p.running)
        self.level += running * PUMP_RATE - self.leak * LEAK_STEP
        self.level = max(0.0, min(100.0, self.level))

        self._control()

    def _control(self):
        if not any(not p.error for p in self.pumps):
            self.system_error = True
            for p in self.pumps:
                p.running = False
            return
        self.system_error = False

        if self.level >= LEVEL_STOP:
            for p in self.pumps:
                p.running = False
            return

        running = sum(1 for p in self.pumps if p.running)

        if self.level < LEVEL_START_1 and running == 0:
            if self._start_one():
                running += 1
        if self.level < LEVEL_START_2 and running < 2:
            self._start_one()

    def _start_one(self):
        candidates = [p for p in self.pumps if not p.error and not p.running]
        if not candidates:
            return False
        pump = min(candidates, key=lambda p: p.work_time)
        pump.running = True
        return True

    def toggle_error(self, idx):
        p = self.pumps[idx]
        p.error = not p.error
        if p.error:
            p.running = False

    def toggle_start(self):
        self.started = not self.started

    def leak_up(self):
        if self.leak < LEAK_MAX:
            self.leak += 1

    def leak_down(self):
        if self.leak > 0:
            self.leak -= 1


# ============================================================
#  UI — координаты (фиксированная сетка)
# ============================================================
# Верхняя полоса (заголовок + кнопка + счётчики)
TOP_H = 80

# Левая панель: БАК
TANK_PANEL = (20, 100, 280, 660)     # x1, y1, x2, y2
TANK_X, TANK_Y = 60, 160
TANK_W, TANK_H = 170, 440

# Правая панель: НАСОСЫ (низ)
PUMPS_PANEL = (620, 420, 980, 660)
PUMP_W, PUMP_H = 100, 60
PUMP_Y = 480
PUMP_XS = [645, 755, 865]            # левые края насосов
ERR_BTN_Y = PUMP_Y + PUMP_H + 16
ERR_BTN_H = 32

# Правая панель: РАСХОД (верх)
LEAK_PANEL = (620, 100, 980, 400)
LEAK_P_X1, LEAK_P_Y1, LEAK_P_X2, LEAK_P_Y2 = LEAK_PANEL

# Кнопка "Запуск"
START_RECT = (30, 20, 180, 62)

# Счётчики в верхней полосе
STAT_CYCLE_RECT = (400, 20, 620, 62)
STAT_STATE_RECT = (640, 20, 860, 62)


# ============================================================
#  ПРИЛОЖЕНИЕ
# ============================================================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Система управления насосами")
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self.system = PumpSystem()

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT,
                                bg=BG, highlightthickness=0)
        self.canvas.pack()

        self.clickables = []
        self._build_clickables()

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_motion)
        self.hover_zone = None

        self.tick()

    # --------------------------------------------------------
    #  Зоны кликов
    # --------------------------------------------------------
    def _build_clickables(self):
        # Запуск
        self.clickables.append(("start", *START_RECT, self.on_start))

        # Стрелки расхода
        cx = (LEAK_P_X1 + LEAK_P_X2) // 2

        up_y1 = LEAK_P_Y1 + 60
        up_y2 = up_y1 + 44
        self.clickables.append(
            ("leak_up", cx - 45, up_y1, cx + 45, up_y2, self.on_leak_up))

        down_y2 = LEAK_P_Y2 - 20
        down_y1 = down_y2 - 44
        self.clickables.append(
            ("leak_down", cx - 45, down_y1, cx + 45, down_y2,
             self.on_leak_down))

        # Кнопки "Ошибка" под насосами
        for i, x in enumerate(PUMP_XS):
            self.clickables.append((
                f"err_{i}",
                x, ERR_BTN_Y,
                x + PUMP_W, ERR_BTN_Y + ERR_BTN_H,
                (lambda idx=i: self.on_error(idx))))

    def on_click(self, event):
        for name, x1, y1, x2, y2, cb in self.clickables:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                cb()
                return

    def on_motion(self, event):
        self.hover_zone = None
        for name, x1, y1, x2, y2, cb in self.clickables:
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.hover_zone = name
                self.canvas.config(cursor="hand2")
                return
        self.canvas.config(cursor="")

    # --------------------------------------------------------
    #  Обработчики
    # --------------------------------------------------------
    def on_start(self):
        self.system.toggle_start()

    def on_error(self, idx):
        self.system.toggle_error(idx)

    def on_leak_up(self):
        self.system.leak_up()

    def on_leak_down(self):
        self.system.leak_down()

    # --------------------------------------------------------
    #  Цикл
    # --------------------------------------------------------
    def tick(self):
        self.system.step()
        self.draw()
        self.root.after(CYCLE_MS, self.tick)

    # --------------------------------------------------------
    #  Отрисовка
    # --------------------------------------------------------
    def draw(self):
        c = self.canvas
        c.delete("all")
        sys = self.system

        # ---- верхняя полоса ----
        c.create_rectangle(0, 0, WIDTH, TOP_H,
                           fill=BG_PANEL, outline="")
        c.create_line(0, TOP_H, WIDTH, TOP_H,
                      fill=PANEL_EDGE, width=1)

        # заголовок (по центру верхней полосы, но чтобы не мешал — сверху)
        c.create_text(WIDTH // 2, 16,
                      text="СИСТЕМА УПРАВЛЕНИЯ НАСОСАМИ",
                      fill=TEXT, font=("Segoe UI", 12, "bold"))

        # кнопка Запуск
        start_label = "ПАУЗА" if sys.started else "ЗАПУСК"
        self._button(*START_RECT, start_label,
                     accent=True, hover=(self.hover_zone == "start"))

        # счётчики
        self._stat_box(*STAT_CYCLE_RECT, "ЦИКЛОВ", str(sys.cycle_counter))
        self._stat_box(*STAT_STATE_RECT, "СОСТОЯНИЕ",
                       "РАБОТА" if sys.started else "СТОП")

        # ---- панели ----
        self._panel(*TANK_PANEL)
        self._panel(*PUMPS_PANEL)
        self._panel(*LEAK_PANEL)

        # =========================================================
        #  ТРУБЫ
        # =========================================================
        bus_y = 400                       # высота горизонтальной шины
        bus_x_left = PUMP_XS[0] + PUMP_W // 2
        bus_x_right = TANK_X + TANK_W + 40

        # 1) от насосов вверх до шины
        for x in PUMP_XS:
            cx = x + PUMP_W // 2
            c.create_line(cx, PUMP_Y, cx, bus_y, fill=PIPE, width=9)
            c.create_line(cx, PUMP_Y, cx, bus_y, fill=PIPE_HI, width=4)

        # 2) горизонтальная шина
        c.create_line(bus_x_left, bus_y, bus_x_right, bus_y,
                      fill=PIPE, width=9)
        c.create_line(bus_x_left, bus_y, bus_x_right, bus_y,
                      fill=PIPE_HI, width=4)

        # 3) от шины к баку — по вертикали вверх, затем в бак сбоку
        tank_mid_y = TANK_Y + TANK_H // 2
        c.create_line(bus_x_right, bus_y, bus_x_right, tank_mid_y,
                      fill=PIPE, width=9)
        c.create_line(bus_x_right, bus_y, bus_x_right, tank_mid_y,
                      fill=PIPE_HI, width=4)
        c.create_line(TANK_X + TANK_W, tank_mid_y, bus_x_right, tank_mid_y,
                      fill=PIPE, width=9)
        c.create_line(TANK_X + TANK_W, tank_mid_y, bus_x_right, tank_mid_y,
                      fill=PIPE_HI, width=4)

        # 4) выход из бака — снизу
        out_x = TANK_X + TANK_W // 2
        out_y = TANK_Y + TANK_H
        c.create_line(out_x, out_y, out_x, out_y + 40,
                      fill=PIPE, width=9)
        c.create_line(out_x, out_y, out_x, out_y + 40,
                      fill=PIPE_HI, width=4)
        c.create_line(out_x, out_y + 40, out_x + 90, out_y + 40,
                      fill=PIPE, width=9)
        c.create_line(out_x, out_y + 40, out_x + 90, out_y + 40,
                      fill=PIPE_HI, width=4)
        c.create_line(out_x + 90, out_y + 40, out_x + 90, out_y + 70,
                      fill=PIPE, width=9)
        c.create_line(out_x + 90, out_y + 40, out_x + 90, out_y + 70,
                      fill=PIPE_HI, width=4)

        # =========================================================
        #  БАК
        # =========================================================
        c.create_rectangle(TANK_X - 2, TANK_Y - 2,
                           TANK_X + TANK_W + 2, TANK_Y + TANK_H + 2,
                           fill=TANK_BG, outline=TANK_EDGE, width=2)

        fill_h = int((TANK_H - 4) * sys.level / 100.0)
        if fill_h > 0:
            x1 = TANK_X + 2
            x2 = TANK_X + TANK_W - 2
            y1 = TANK_Y + TANK_H - 2 - fill_h
            y2 = TANK_Y + TANK_H - 2
            c.create_rectangle(x1, y1, x2, y2, fill=WATER, outline="")
            c.create_rectangle(x1, y1, x2, y1 + 5,
                               fill=WATER_HI, outline="")
            c.create_rectangle(x1, y2 - 3, x2, y2,
                               fill=WATER_DARK, outline="")

        # шкала справа от бака
        for pct in (0, 25, 50, 75, 100):
            y = TANK_Y + TANK_H - int(TANK_H * pct / 100.0)
            c.create_line(TANK_X + TANK_W + 2, y,
                          TANK_X + TANK_W + 12, y,
                          fill=TANK_EDGE, width=2)
            c.create_text(TANK_X + TANK_W + 32, y,
                          text=f"{pct}%",
                          fill=TEXT_DIM,
                          font=("Segoe UI", 9, "bold"))

        # подпись над баком
        c.create_text(TANK_X + TANK_W // 2, TANK_Y - 35,
                      text="БАК", fill=ACCENT,
                      font=("Segoe UI", 12, "bold"))
        c.create_text(TANK_X + TANK_W // 2, TANK_Y - 15,
                      text=f"{int(sys.level)} %", fill=TEXT,
                      font=("Segoe UI", 11, "bold"))

        # =========================================================
        #  НАСОСЫ
        # =========================================================
        for i, x in enumerate(PUMP_XS):
            p = sys.pumps[i]
            if p.error:
                body, edge = PUMP_ERR, PUMP_ERR_E
            elif p.running:
                body, edge = PUMP_ON, PUMP_ON_E
            else:
                body, edge = PUMP_OFF, PUMP_OFF_E

            if p.running and not p.error:
                c.create_rectangle(x - 3, PUMP_Y - 3,
                                   x + PUMP_W + 3, PUMP_Y + PUMP_H + 3,
                                   outline=GREEN, width=2)

            c.create_rectangle(x, PUMP_Y,
                               x + PUMP_W, PUMP_Y + PUMP_H,
                               fill=body, outline=edge, width=2)

            # индикатор
            c.create_oval(x + 10, PUMP_Y + 10,
                          x + 24, PUMP_Y + 24,
                          fill="#ffffff" if (p.running and not p.error) else "#1a2028",
                          outline=edge, width=2)

            # номер
            c.create_text(x + PUMP_W // 2 + 6, PUMP_Y + PUMP_H // 2,
                          text=str(p.id), fill=TEXT,
                          font=("Segoe UI", 18, "bold"))

            # наработка над насосом
            c.create_text(x + PUMP_W // 2, PUMP_Y - 14,
                          text=f"наработка: {p.work_time}",
                          fill=TEXT_DIM,
                          font=("Segoe UI", 9, "bold"))

            # кнопка "Ошибка / Сброс"
            self._button(
                x, ERR_BTN_Y,
                x + PUMP_W, ERR_BTN_Y + ERR_BTN_H,
                "Сброс" if p.error else "Ошибка",
                danger=p.error,
                hover=(self.hover_zone == f"err_{i}"))

        # =========================================================
        #  ПАНЕЛЬ РАСХОДА
        # =========================================================
        self._draw_leak_panel(sys)

        # ---- ошибка системы ----
        if sys.system_error:
            c.create_rectangle(WIDTH // 2 - 160, HEIGHT - 32,
                               WIDTH // 2 + 160, HEIGHT - 6,
                               fill="#3a1a1a", outline=RED, width=2)
            c.create_text(WIDTH // 2, HEIGHT - 19,
                          text="⚠ ВСЕ НАСОСЫ НЕИСПРАВНЫ",
                          fill=RED,
                          font=("Segoe UI", 11, "bold"))

    # --------------------------------------------------------
    #  Вспомогательные рисовалки
    # --------------------------------------------------------
    def _panel(self, x1, y1, x2, y2):
        self.canvas.create_rectangle(x1, y1, x2, y2,
                                     fill=BG_PANEL, outline=PANEL_EDGE,
                                     width=1)

    def _button(self, x1, y1, x2, y2, text,
                accent=False, danger=False, hover=False):
        c = self.canvas
        if danger:
            bg = BTN_DANGER_H if hover else BTN_DANGER
            edge = RED
            fg = "#ffdede"
        elif accent:
            bg = BTN_ACTIVE_DK if hover else BTN_ACTIVE
            edge = "#6ee6ec"
            fg = "#0a1a1c"
        else:
            bg = BTN_HOVER if hover else BTN
            edge = BTN_EDGE
            fg = TEXT

        c.create_rectangle(x1 + 2, y1 + 2, x2 + 2, y2 + 2,
                           fill="#0a0e14", outline="")
        c.create_rectangle(x1, y1, x2, y2,
                           fill=bg, outline=edge, width=2)
        c.create_text((x1 + x2) // 2, (y1 + y2) // 2,
                      text=text, fill=fg,
                      font=("Segoe UI", 11, "bold"))

    def _stat_box(self, x1, y1, x2, y2, label, value):
        c = self.canvas
        c.create_rectangle(x1, y1, x2, y2,
                           fill=BG, outline=PANEL_EDGE, width=1)
        c.create_text((x1 + x2) // 2, y1 + 12,
                      text=label, fill=TEXT_DIM,
                      font=("Segoe UI", 8, "bold"))
        c.create_text((x1 + x2) // 2, (y1 + y2) // 2 + 10,
                      text=value, fill=ACCENT,
                      font=("Segoe UI", 16, "bold"))

    def _draw_leak_panel(self, sys):
        c = self.canvas
        x0, y0 = LEAK_P_X1, LEAK_P_Y1
        x1, y1 = LEAK_P_X2, LEAK_P_Y2
        cx = (x0 + x1) // 2

        c.create_text(cx, y0 + 22,
                      text="РАСХОД ВОДЫ", fill=ACCENT,
                      font=("Segoe UI", 12, "bold"))

        up_y1 = y0 + 55
        up_y2 = up_y1 + 44
        self._button(cx - 45, up_y1, cx + 45, up_y2, "▲",
                     hover=(self.hover_zone == "leak_up"))

        down_y2 = y1 - 18
        down_y1 = down_y2 - 44
        self._button(cx - 45, down_y1, cx + 45, down_y2, "▼",
                     hover=(self.hover_zone == "leak_down"))

        # значение
        mid_y = (up_y2 + down_y1) // 2
        c.create_text(cx, mid_y - 8,
                      text=str(sys.leak), fill=WATER_HI,
                      font=("Segoe UI", 40, "bold"))
        c.create_text(cx, mid_y + 30,
                      text=f"из {LEAK_MAX}", fill=TEXT_DIM,
                      font=("Segoe UI", 9))

        # индикатор-полоски
        bar_y = mid_y + 52
        seg_w = (x1 - x0 - 60) / LEAK_MAX
        for i in range(LEAK_MAX):
            sx = x0 + 30 + i * seg_w
            color = WATER if i < sys.leak else "#25303f"
            c.create_rectangle(sx + 2, bar_y,
                               sx + seg_w - 2, bar_y + 9,
                               fill=color, outline=PANEL_EDGE)


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
