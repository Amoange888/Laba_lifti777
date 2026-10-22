
import enum
import tkinter as tk

# ============================================================
#  КОНФИГ
# ============================================================
CYCLE_MS = 100
PHYSICS_MS = 16

TOTAL_FLOORS = 9
CABIN_SPEED = 1.1
DOOR_SPEED = 0.05
WAIT_TICKS = 25

WIDTH, HEIGHT = 1000, 720

FLOOR_H = 56
FLOOR_GAP = 4
SHAFT_X = 100
SHAFT_W = 320
SHAFT_TOP = 110
SHAFT_H = TOTAL_FLOORS * (FLOOR_H + FLOOR_GAP) - FLOOR_GAP

PANEL_X = 620
PANEL_Y = 110
PANEL_W = 340
PANEL_H = SHAFT_H

# ---- Палитра ----
BG          = "#1b2230"
BG_PANEL    = "#242c3d"
PANEL_EDGE  = "#3a4560"

TEXT        = "#e8eef7"
TEXT_DIM    = "#8493ac"
ACCENT      = "#54c8d4"
ACCENT_DK   = "#2e8b96"

SHAFT_BG    = "#0f141d"
SHAFT_EDGE  = "#3a4560"
FLOOR_LINE  = "#2a3444"
FLOOR_BG    = "#1a2130"

CABIN_BG    = "#cfd6e2"
CABIN_EDGE  = "#f0f4fa"
DOOR_L      = "#4a86c8"
DOOR_R      = "#3a72b0"

BTN_OFF     = "#2f3a4d"
BTN_OFF_ED  = "#4a566e"
BTN_ON      = "#f0ad4e"
BTN_ON_ED   = "#c98a2e"
BTN_DIS     = "#1f2733"
BTN_DIS_ED  = "#2a3444"

ARROW       = "#f0ad4e"
RED         = "#e74c3c"


# ============================================================
#  FSM
# ============================================================
class State(enum.Enum):
    IDLE = 0
    MOVING_UP = 1
    MOVING_DOWN = 2
    DOOR_OPENING = 3
    WAITING = 4
    DOOR_CLOSING = 5


# ============================================================
#  МОДЕЛЬ
# ============================================================
class Elevator:
    def __init__(self):
        self.running = False
        self.state = State.IDLE
        self.cycle_counter = 0

        self.current_floor = 1
        self.cabin_y = 0.0
        self.cabin_target_y = 0.0
        self.door_pos = 0.0
        self.direction = "NONE"
        self.wait_timer = 0

        self.cabin_requests = [False] * (TOTAL_FLOORS + 1)
        self.floor_up = [False] * (TOTAL_FLOORS + 1)
        self.floor_down = [False] * (TOTAL_FLOORS + 1)

        self.next_floor = None

    def toggle_start(self):
        if not self.running:
            self.running = True
            self.state = State.IDLE
            self.direction = "NONE"
            self.door_pos = 0.0
            self.wait_timer = 0
            self.next_floor = None
            self.cabin_target_y = self.cabin_y
        else:
            self.running = False

    def press_cabin(self, floor):
        if not self.running or floor < 1 or floor > TOTAL_FLOORS:
            return
        if floor == self.current_floor:
            return
        self.cabin_requests[floor] = True

    def press_floor_up(self, floor):
        if not self.running or floor >= TOTAL_FLOORS:
            return
        if floor == self.current_floor and self.state == State.IDLE:
            self._open_doors_here()
            return
        self.floor_up[floor] = True

    def press_floor_down(self, floor):
        if not self.running or floor <= 1:
            return
        if floor == self.current_floor and self.state == State.IDLE:
            self._open_doors_here()
            return
        self.floor_down[floor] = True

    def _open_doors_here(self):
        if self.state == State.IDLE and self.door_pos == 0.0:
            self.state = State.DOOR_OPENING

    def step(self):
        if not self.running:
            return
        self.cycle_counter += 1

        s = self.state
        if s == State.IDLE:
            self._state_idle()
        elif s == State.MOVING_UP:
            self._state_moving_up()
        elif s == State.MOVING_DOWN:
            self._state_moving_down()
        elif s == State.DOOR_OPENING:
            self._state_door_opening()
        elif s == State.WAITING:
            self._state_waiting()
        elif s == State.DOOR_CLOSING:
            self._state_door_closing()

    def update_physics(self):
        if not self.running:
            return

        dy = self.cabin_target_y - self.cabin_y
        if abs(dy) <= CABIN_SPEED:
            self.cabin_y = self.cabin_target_y
        else:
            self.cabin_y += CABIN_SPEED if dy > 0 else -CABIN_SPEED

        if self.state == State.DOOR_OPENING:
            self.door_pos = min(1.0, self.door_pos + DOOR_SPEED)
        elif self.state == State.DOOR_CLOSING:
            self.door_pos = max(0.0, self.door_pos - DOOR_SPEED)

    def _state_idle(self):
        any_above = any(self._any_request(f)
                        for f in range(self.current_floor + 1,
                                       TOTAL_FLOORS + 1))
        any_below = any(self._any_request(f)
                        for f in range(1, self.current_floor))

        if any_above and any_below:
            if self.direction == "DOWN":
                self._go_down()
            else:
                self._go_up()
        elif any_above:
            self._go_up()
        elif any_below:
            self._go_down()
        else:
            self.direction = "NONE"
            self.next_floor = None

    def _go_up(self):
        self.direction = "UP"
        self.next_floor = self.current_floor + 1
        self.cabin_target_y = float(floor_to_y(self.next_floor))
        self.state = State.MOVING_UP

    def _go_down(self):
        self.direction = "DOWN"
        self.next_floor = self.current_floor - 1
        self.cabin_target_y = float(floor_to_y(self.next_floor))
        self.state = State.MOVING_DOWN

    def _state_moving_up(self):
        if abs(self.cabin_y - self.cabin_target_y) > 0.5:
            return

        self.cabin_y = self.cabin_target_y
        self.current_floor = self.next_floor
        f = self.current_floor

        if self._has_request_up(f):
            self._clear_requests_up(f)
            self.state = State.DOOR_OPENING
        elif not self._any_request_above(f):
            if self._any_request(f):
                self._clear_requests_all(f)
                self.state = State.DOOR_OPENING
            else:
                self.state = State.IDLE
        else:
            self.next_floor = f + 1
            if self.next_floor > TOTAL_FLOORS:
                self.state = State.IDLE
                return
            self.cabin_target_y = float(floor_to_y(self.next_floor))

    def _state_moving_down(self):
        if abs(self.cabin_y - self.cabin_target_y) > 0.5:
            return

        self.cabin_y = self.cabin_target_y
        self.current_floor = self.next_floor
        f = self.current_floor

        if self._has_request_down(f):
            self._clear_requests_down(f)
            self.state = State.DOOR_OPENING
        elif not self._any_request_below(f):
            if self._any_request(f):
                self._clear_requests_all(f)
                self.state = State.DOOR_OPENING
            else:
                self.state = State.IDLE
        else:
            self.next_floor = f - 1
            if self.next_floor < 1:
                self.state = State.IDLE
                return
            self.cabin_target_y = float(floor_to_y(self.next_floor))

    def _state_door_opening(self):
        if self.door_pos >= 1.0:
            self.door_pos = 1.0
            self.wait_timer = 0
            self.state = State.WAITING

    def _state_waiting(self):
        self.wait_timer += 1
        if self.wait_timer >= WAIT_TICKS:
            self.state = State.DOOR_CLOSING

    def _state_door_closing(self):
        if self.door_pos <= 0.0:
            self.door_pos = 0.0
            self.state = State.IDLE

    def _any_request(self, floor):
        return (self.cabin_requests[floor]
                or self.floor_up[floor]
                or self.floor_down[floor])

    def _has_request_up(self, floor):
        return self.cabin_requests[floor] or self.floor_up[floor]

    def _has_request_down(self, floor):
        return self.cabin_requests[floor] or self.floor_down[floor]

    def _any_request_above(self, floor):
        return any(self._any_request(f)
                   for f in range(floor + 1, TOTAL_FLOORS + 1))

    def _any_request_below(self, floor):
        return any(self._any_request(f) for f in range(1, floor))

    def _clear_requests_up(self, floor):
        self.cabin_requests[floor] = False
        self.floor_up[floor] = False

    def _clear_requests_down(self, floor):
        self.cabin_requests[floor] = False
        self.floor_down[floor] = False

    def _clear_requests_all(self, floor):
        self.cabin_requests[floor] = False
        self.floor_up[floor] = False
        self.floor_down[floor] = False


# ============================================================
#  Координаты
# ============================================================
def floor_to_y(floor):
    """
    Y внутри шахты.
    ВАЖНО: 0 — НИЗ шахты (1-й этаж), SHAFT_H — ВЕРХ (9-й этаж).
    То есть чем выше этаж, тем больше Y.
    """
    y1 = FLOOR_H / 2                 # 1-й этаж — у самого низа
    return y1 + (floor - 1) * (FLOOR_H + FLOOR_GAP)


# ============================================================
#  ПРИЛОЖЕНИЕ
# ============================================================
class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Управление лифтом (9 этажей)")
        self.root.geometry(f"{WIDTH}x{HEIGHT}")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self.elevator = Elevator()
        self.elevator.cabin_y = float(floor_to_y(1))
        self.elevator.cabin_target_y = self.elevator.cabin_y

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT,
                                bg=BG, highlightthickness=0)
        self.canvas.pack()

        self.hover_zone = None
        self._build_clickables()

        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Motion>", self.on_motion)

        self.last_cycle_time = 0
        self.last_physics_time = 0
        self.tick()

    def _build_clickables(self):
        self.cabin_btn_zones = self._compute_cabin_button_zones()

    def _compute_cabin_button_zones(self):
        """Кнопки в кабине: 9 сверху, 1 снизу."""
        zones = []
        btn_w = 140
        btn_h = 40
        gap = 8
        for i, floor in enumerate(range(TOTAL_FLOORS, 0, -1)):
            x1 = PANEL_X + (PANEL_W - btn_w) // 2
            y1 = PANEL_Y + 50 + i * (btn_h + gap)
            x2 = x1 + btn_w
            y2 = y1 + btn_h
            zones.append((floor, x1, y1, x2, y2))
        return zones

    def _call_zones(self):
        """▲▼ справа от шахты. f=1 внизу, f=9 вверху."""
        zones = []
        btn_w = 34
        btn_h = 22
        gap = 4
        bx = SHAFT_X + SHAFT_W + 12

        for f in range(1, TOTAL_FLOORS + 1):
            # экранный Y центра этажа f
            yc = SHAFT_TOP + SHAFT_H - floor_to_y(f)
            if f < TOTAL_FLOORS:
                zones.append((f, "up", bx, yc - btn_h - gap // 2,
                              bx + btn_w, yc - gap // 2))
            if f > 1:
                zones.append((f, "down", bx, yc + gap // 2,
                              bx + btn_w, yc + btn_h + gap // 2))
        return zones

    def on_click(self, event):
        x, y = event.x, event.y

        if 30 <= x <= 190 and 30 <= y <= 76:
            self.elevator.toggle_start()
            return

        for floor, x1, y1, x2, y2 in self.cabin_btn_zones:
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.elevator.press_cabin(floor)
                return

        for floor, kind, x1, y1, x2, y2 in self._call_zones():
            if x1 <= x <= x2 and y1 <= y <= y2:
                if kind == "up":
                    self.elevator.press_floor_up(floor)
                else:
                    self.elevator.press_floor_down(floor)
                return

    def on_motion(self, event):
        x, y = event.x, event.y
        self.hover_zone = None

        if 30 <= x <= 190 and 30 <= y <= 76:
            self.hover_zone = "start"
            self.canvas.config(cursor="hand2")
            return

        for floor, x1, y1, x2, y2 in self.cabin_btn_zones:
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.hover_zone = f"cab_{floor}"
                self.canvas.config(cursor="hand2")
                return

        for floor, kind, x1, y1, x2, y2 in self._call_zones():
            if x1 <= x <= x2 and y1 <= y <= y2:
                self.hover_zone = f"call_{kind}_{floor}"
                self.canvas.config(cursor="hand2")
                return

        self.canvas.config(cursor="")

    def tick(self):
        now = self._now_ms()

        if now - self.last_cycle_time >= CYCLE_MS:
            self.elevator.step()
            self.last_cycle_time = now

        if now - self.last_physics_time >= PHYSICS_MS:
            self.elevator.update_physics()
            self.last_physics_time = now

        self.draw()
        self.root.after(16, self.tick)

    def _now_ms(self):
        return int(self.root.tk.call('clock', 'milliseconds'))

    # ---------- отрисовка ----------
    def draw(self):
        c = self.canvas
        c.delete("all")
        e = self.elevator

        c.create_rectangle(0, 0, WIDTH, 100,
                           fill=BG_PANEL, outline="")
        c.create_line(0, 100, WIDTH, 100, fill=PANEL_EDGE, width=1)

        c.create_text(WIDTH // 2, 22,
                      text="УПРАВЛЕНИЕ ЛИФТОМ · 9 ЭТАЖЕЙ",
                      fill=TEXT, font=("Segoe UI", 14, "bold"))
        c.create_text(WIDTH // 2, 46,
                      text=f"состояние: {self._state_ru(e.state)}   "
                           f"·   этаж: {e.current_floor}   "
                           f"·   направление: {self._dir_ru(e.direction)}",
                      fill=TEXT_DIM, font=("Segoe UI", 10))
        c.create_text(WIDTH // 2, 70,
                      text=f"циклов: {e.cycle_counter}",
                      fill=ACCENT, font=("Segoe UI", 12, "bold"))

        self._button(30, 30, 190, 76,
                     "ПАУЗА" if e.running else "ЗАПУСК",
                     accent=True,
                     hover=(self.hover_zone == "start"))

        self._draw_shaft()
        self._draw_cabin_panel()

    def _state_ru(self, state):
        return {
            State.IDLE: "ВЫБОР НАПРАВЛЕНИЯ",
            State.MOVING_UP: "ДВИЖЕНИЕ ВВЕРХ",
            State.MOVING_DOWN: "ДВИЖЕНИЕ ВНИЗ",
            State.DOOR_OPENING: "ОТКРЫТИЕ ДВЕРЕЙ",
            State.WAITING: "ОЖИДАНИЕ",
            State.DOOR_CLOSING: "ЗАКРЫТИЕ ДВЕРЕЙ",
        }.get(state, "—")

    def _dir_ru(self, d):
        return {"UP": "ВВЕРХ", "DOWN": "ВНИЗ", "NONE": "—"}.get(d, "—")

    def _draw_shaft(self):
        c = self.canvas

        c.create_rectangle(SHAFT_X, SHAFT_TOP,
                           SHAFT_X + SHAFT_W, SHAFT_TOP + SHAFT_H,
                           fill=SHAFT_BG, outline=SHAFT_EDGE, width=2)

        for f in range(1, TOTAL_FLOORS + 1):
            yc_in_shaft = floor_to_y(f)            # 0=низ, больше=выше
            yc = SHAFT_TOP + SHAFT_H - yc_in_shaft # экран

            top = yc - FLOOR_H // 2
            c.create_rectangle(SHAFT_X + 2, top,
                               SHAFT_X + SHAFT_W - 2, top + FLOOR_H,
                               fill=FLOOR_BG, outline="")
            c.create_line(SHAFT_X + 2, top + FLOOR_H,
                          SHAFT_X + SHAFT_W - 2, top + FLOOR_H,
                          fill=FLOOR_LINE, width=2)
            c.create_text(SHAFT_X - 25, yc,
                          text=str(f), fill=TEXT,
                          font=("Segoe UI", 14, "bold"))

        for floor, kind, x1, y1, x2, y2 in self._call_zones():
            active = (self.elevator.floor_up[floor] if kind == "up"
                      else self.elevator.floor_down[floor])
            enabled = self.elevator.running
            hover = (self.hover_zone == f"call_{kind}_{floor}")
            self._call_button(x1, y1, x2, y2, kind,
                              active, enabled, hover)

        self._draw_cabin()

    def _draw_cabin(self):
        c = self.canvas
        e = self.elevator

        yc_in_shaft = e.cabin_y
        yc = SHAFT_TOP + SHAFT_H - yc_in_shaft

        cabin_w = 160
        cabin_h = FLOOR_H - 8
        cabin_x = SHAFT_X + SHAFT_W // 2 - cabin_w // 2
        cabin_y = yc - cabin_h // 2

        c.create_rectangle(cabin_x + 3, cabin_y + 4,
                           cabin_x + cabin_w + 3, cabin_y + cabin_h + 4,
                           fill="#0a0e14", outline="")
        c.create_rectangle(cabin_x, cabin_y,
                           cabin_x + cabin_w, cabin_y + cabin_h,
                           fill=CABIN_BG, outline=CABIN_EDGE, width=3)

        gap = int(e.door_pos * (cabin_w - 12))
        half = (cabin_w - 12 - gap) // 2
        c.create_rectangle(cabin_x + 6, cabin_y + 6,
                           cabin_x + 6 + half, cabin_y + cabin_h - 6,
                           fill=DOOR_L, outline="")
        c.create_rectangle(cabin_x + 6 + half + gap, cabin_y + 6,
                           cabin_x + cabin_w - 6, cabin_y + cabin_h - 6,
                           fill=DOOR_R, outline="")

        if e.direction == "UP":
            self._draw_arrow(cabin_x + cabin_w + 18,
                             cabin_y + cabin_h // 2, "UP")
        elif e.direction == "DOWN":
            self._draw_arrow(cabin_x + cabin_w + 18,
                             cabin_y + cabin_h // 2, "DOWN")

    def _draw_arrow(self, x, y, d):
        c = self.canvas
        if d == "UP":
            c.create_polygon(x, y - 10, x - 7, y + 5, x + 7, y + 5,
                             fill=ARROW, outline="")
        else:
            c.create_polygon(x, y + 10, x - 7, y - 5, x + 7, y - 5,
                             fill=ARROW, outline="")

    def _draw_cabin_panel(self):
        c = self.canvas
        c.create_rectangle(PANEL_X, PANEL_Y,
                           PANEL_X + PANEL_W, PANEL_Y + PANEL_H,
                           fill=BG_PANEL, outline=PANEL_EDGE, width=2)
        c.create_text(PANEL_X + PANEL_W // 2, PANEL_Y + 25,
                      text="КНОПКИ В ЛИФТЕ",
                      fill=ACCENT, font=("Segoe UI", 13, "bold"))

        enabled = self.elevator.running
        for floor, x1, y1, x2, y2 in self.cabin_btn_zones:
            active = self.elevator.cabin_requests[floor]
            hover = (self.hover_zone == f"cab_{floor}")
            self._cabin_button(x1, y1, x2, y2, floor,
                               active, enabled, hover)

    def _cabin_button(self, x1, y1, x2, y2, floor,
                      active, enabled, hover):
        c = self.canvas
        if not enabled:
            bg = BTN_DIS
            edge = BTN_DIS_ED
            fg = TEXT_DIM
        elif active:
            bg = BTN_ON
            edge = BTN_ON_ED
            fg = "#3a2a0a"
        else:
            bg = BTN_OFF
            edge = BTN_OFF_ED
            fg = TEXT
            if hover:
                bg = "#3a4660"

        c.create_rectangle(x1, y1, x2, y2,
                           fill=bg, outline=edge, width=2)
        c.create_text((x1 + x2) // 2, (y1 + y2) // 2,
                      text=str(floor), fill=fg,
                      font=("Segoe UI", 13, "bold"))

    def _call_button(self, x1, y1, x2, y2, kind,
                     active, enabled, hover):
        c = self.canvas
        if not enabled:
            bg = BTN_DIS
            edge = BTN_DIS_ED
            fg = TEXT_DIM
        elif active:
            bg = BTN_ON
            edge = BTN_ON_ED
            fg = "#3a2a0a"
        else:
            bg = BTN_OFF
            edge = BTN_OFF_ED
            fg = TEXT
            if hover:
                bg = "#3a4660"

        c.create_rectangle(x1, y1, x2, y2,
                           fill=bg, outline=edge, width=2)
        arrow = "▲" if kind == "up" else "▼"
        c.create_text((x1 + x2) // 2, (y1 + y2) // 2,
                      text=arrow, fill=fg,
                      font=("Segoe UI", 12, "bold"))

    def _button(self, x1, y1, x2, y2, text,
                accent=False, danger=False, hover=False):
        c = self.canvas
        if danger:
            bg = "#a83a3a" if hover else "#8a3030"
            edge = RED
            fg = "#ffdede"
        elif accent:
            bg = ACCENT_DK if hover else ACCENT
            edge = "#7fe0e8"
            fg = "#0a1a1c"
        else:
            bg = BTN_OFF
            edge = BTN_OFF_ED
            fg = TEXT
            if hover:
                bg = "#3a4660"

        c.create_rectangle(x1 + 2, y1 + 3, x2 + 2, y2 + 3,
                           fill="#0a0e14", outline="")
        c.create_rectangle(x1, y1, x2, y2,
                           fill=bg, outline=edge, width=2)
        c.create_text((x1 + x2) // 2, (y1 + y2) // 2,
                      text=text, fill=fg,
                      font=("Segoe UI", 11, "bold"))


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()  
