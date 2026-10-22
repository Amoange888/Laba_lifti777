import tkinter as tk
from tkinter import ttk
import time
from threading import Thread, Lock

class PumpSystem:
    def __init__(self):
        self.capacity = 500.0
        self.level = 0.0
        self.pump_rate = 10.0
        self.drain_rate = 0.0
        self.max_drain = 20.0           
        self.pumps = {
            0: {"name": "Насос A", "runtime": 0.0, "broken": False, "active": False},
            1: {"name": "Насос B", "runtime": 0.0, "broken": False, "active": False},
            2: {"name": "Насос C", "runtime": 0.0, "broken": False, "active": False},
        }
        self.lock = Lock()

    def get_working_pumps(self):
        return [i for i, p in self.pumps.items() if not p["broken"]]

    def select_active_pumps(self):
        working = self.get_working_pumps()
        if len(working) < 2:
            return working
        return sorted(working, key=lambda i: self.pumps[i]["runtime"])[:2]

    def update_active(self, need_pumps: bool):
        for p in self.pumps.values():
            p["active"] = False
        if not need_pumps:
            return []
        active = self.select_active_pumps()
        for i in active:
            self.pumps[i]["active"] = True
        return active

    def break_pump(self, idx):
        with self.lock:
            self.pumps[idx]["broken"] = True
            self.pumps[idx]["active"] = False

    def repair_pump(self, idx):
        with self.lock:
            self.pumps[idx]["broken"] = False

    def step(self, dt_minutes):
        with self.lock:
            need_pumps = (self.level < self.capacity) or (self.drain_rate > 0)

            active = self.update_active(need_pumps)
            inflow = len(active) * self.pump_rate
            outflow = self.drain_rate

            net = (inflow - outflow) * dt_minutes
            self.level = max(0.0, min(self.capacity, self.level + net))

            for i in active:
                self.pumps[i]["runtime"] += dt_minutes

            return inflow, outflow

    def set_drain_rate(self, rate):
        with self.lock:
            self.drain_rate = max(0.0, min(self.max_drain, rate))

    def reset_runtimes(self):
        with self.lock:
            for p in self.pumps.values():
                p["runtime"] = 0.0

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Система насосов + кран")
        self.root.geometry("800x620")
        self.root.resizable(False, False)

        self.system = PumpSystem()
        self.stop_flag = False
        self.create_widgets()
        self.update_gui()

    def create_widgets(self):
        frame_tank = ttk.LabelFrame(self.root, text="Резервуар", padding=10)
        frame_tank.pack(fill="x", padx=10, pady=5)

        self.level_var = tk.StringVar(value="0.0 / 500 л")
        ttk.Label(frame_tank, textvariable=self.level_var, font=("Arial", 14, "bold")).pack()

        self.progress = ttk.Progressbar(frame_tank, length=520, maximum=500)
        self.progress.pack(pady=5)

        self.canvas = tk.Canvas(frame_tank, width=540, height=120, bg="#e0e0e0")
        self.canvas.pack(pady=5)
        self.canvas.create_rectangle(10, 10, 530, 110, outline="#333", width=3)
        self.water = self.canvas.create_rectangle(12, 110, 528, 110, fill="#4fc3f7", outline="")

        frame_drain = ttk.LabelFrame(self.root, text="Кран (максимум 20 л/мин = 2 насоса)", padding=10)
        frame_drain.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_drain, text="Расход крана:").pack(side="left")
        self.drain_var = tk.DoubleVar(value=0.0)
        ttk.Scale(frame_drain, from_=0, to=20, variable=self.drain_var,
                  orient="horizontal", length=300, command=self.on_drain_change).pack(side="left", padx=10)
        self.drain_label = ttk.Label(frame_drain, text="0.0 л/мин", width=12)
        self.drain_label.pack(side="left")

        frame_pumps = ttk.LabelFrame(self.root, text="Насосы (по 10 л/мин)", padding=10)
        frame_pumps.pack(fill="x", padx=10, pady=5)

        self.pump_labels = {}
        self.pump_status = {}
        self.btn_break = {}
        self.btn_repair = {}

        for i in range(3):
            row = ttk.Frame(frame_pumps)
            row.pack(fill="x", pady=3)

            ttk.Label(row, text=f"{self.system.pumps[i]['name']}:", width=12).pack(side="left")
            status = ttk.Label(row, text="Стоп", width=14, foreground="gray")
            status.pack(side="left", padx=5)
            self.pump_status[i] = status

            runtime = ttk.Label(row, text="0.0 мин", width=12)
            runtime.pack(side="left")
            self.pump_labels[i] = runtime

            btn_b = ttk.Button(row, text="Сломать", width=10, command=lambda idx=i: self.break_pump(idx))
            btn_b.pack(side="left", padx=5)
            self.btn_break[i] = btn_b

            btn_r = ttk.Button(row, text="Починить", width=10, state="disabled", command=lambda idx=i: self.repair_pump(idx))
            btn_r.pack(side="left")
            self.btn_repair[i] = btn_r

        frame_ctrl = ttk.Frame(self.root, padding=10)
        frame_ctrl.pack(fill="x")

        self.btn_start = ttk.Button(frame_ctrl, text="▶ Старт", command=self.start_sim)
        self.btn_start.pack(side="left", padx=5)

        self.btn_stop = ttk.Button(frame_ctrl, text="⏹ Стоп", command=self.stop_sim, state="disabled")
        self.btn_stop.pack(side="left", padx=5)

        ttk.Button(frame_ctrl, text="Сбросить время", command=self.reset_time).pack(side="left", padx=5)

        ttk.Label(frame_ctrl, text="Скорость:").pack(side="left", padx=(20, 5))
        self.speed_var = tk.DoubleVar(value=1.0)
        ttk.Scale(frame_ctrl, from_=0.2, to=5.0, variable=self.speed_var, orient="horizontal", length=120).pack(side="left")

        self.info_var = tk.StringVar(value="Готов. Нажмите Старт.")
        ttk.Label(self.root, textvariable=self.info_var, font=("Arial", 10), foreground="#0ceb04").pack(pady=5)

        self.flow_var = tk.StringVar(value="Приток: 0  |  Слив: 0  |  Баланс: 0")
        ttk.Label(self.root, textvariable=self.flow_var, font=("Arial", 10)).pack()

    def on_drain_change(self, value):
        rate = float(value)
        self.system.set_drain_rate(rate)
        self.drain_label.config(text=f"{rate:.1f} л/мин")

    def break_pump(self, idx):
        self.system.break_pump(idx)
        self.btn_break[idx].config(state="disabled")
        self.btn_repair[idx].config(state="normal")
        self.info_var.set(f"{self.system.pumps[idx]['name']} сломан")

    def repair_pump(self, idx):
        self.system.repair_pump(idx)
        self.btn_break[idx].config(state="normal")
        self.btn_repair[idx].config(state="disabled")
        self.info_var.set(f"{self.system.pumps[idx]['name']} починен")

    def reset_time(self):
        self.system.reset_runtimes()
        self.info_var.set("Время сброшено")

    def start_sim(self):
        self.stop_flag = False
        self.btn_start.config(state="disabled")
        self.btn_stop.config(state="normal")
        self.info_var.set("Работает...")
        Thread(target=self.simulation_loop, daemon=True).start()

    def stop_sim(self):
        self.stop_flag = True
        self.btn_start.config(state="normal")
        self.btn_stop.config(state="disabled")
        self.info_var.set("Остановлено")

    def simulation_loop(self):
        last = time.time()
        while not self.stop_flag:
            now = time.time()
            dt = (now - last) * self.speed_var.get()
            last = now

            inflow, outflow = self.system.step(dt)
            balance = inflow - outflow
            text = f"Приток: {inflow:.1f} л/мин  |  Слив: {outflow:.1f} л/мин  |  Баланс: {balance:+.1f} л/мин"
            self.root.after(0, lambda t=text: self.flow_var.set(t))
            time.sleep(0.05)

    def update_gui(self):
        level = self.system.level
        self.level_var.set(f"{level:.1f} / 500 л ({level/5:.1f}%)")
        self.progress["value"] = level

        h = int((level / 500) * 98)
        self.canvas.coords(self.water, 12, 110 - h, 528, 110)

        for i, p in self.system.pumps.items():
            self.pump_labels[i].config(text=f"{p['runtime']:.1f} мин")
            if p["broken"]:
                self.pump_status[i].config(text="СЛОМАН", foreground="red")
            elif p["active"]:
                self.pump_status[i].config(text="▶ Работает", foreground="green")
            else:
                self.pump_status[i].config(text="Стоп", foreground="gray")

        self.root.after(100, self.update_gui)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()