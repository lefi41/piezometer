import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import os
import json
from datetime import datetime

class TabletPiezometerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Field Piezometer Pro - Tablet Touch Ready")
        
        # 태블릿 해상도에 맞춰 크기 조절 (가로 850, 세로 950)
        self.root.geometry("850x950")
        self.root.configure(bg="#F5F7FA")
        
        self.base_dir = "Sites_Data"
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

        self.calib_rows = []
        self.current_lgf_field = 0.0
        self.create_widgets()

    def create_widgets(self):
        # 1. 상단 타이틀 바
        header = tk.Frame(self.root, bg="#1E293B", height=70)
        header.pack(fill="x", side="top")
        tk.Label(header, text="지하수위계 현장 캘리브레이션 시스템", font=("맑은 고딕", 18, "bold"), 
                 bg="#1E293B", fg="white").pack(pady=20)

        # 2. 메인 스크롤 영역 설정
        self.main_container = tk.Canvas(self.root, bg="#F5F7FA", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.main_container.yview)
        self.scrollable_frame = tk.Frame(self.main_container, bg="#F5F7FA")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_container.configure(scrollregion=self.main_container.bbox("all"))
        )

        # 캔버스 중앙에 내용 프레임 배치
        self.canvas_window = self.main_container.create_window((425, 0), window=self.scrollable_frame, anchor="n")
        self.main_container.configure(yscrollcommand=self.scrollbar.set)

        # 터치 스크롤 바인딩 (태블릿 핵심 기능)
        self.main_container.bind("<Button-1>", self._on_touch_start)
        self.main_container.bind("<B1-Motion>", self._on_touch_drag)
        self.main_container.bind_all("<MouseWheel>", self._on_mousewheel)

        self.main_container.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # 3. 실제 카드들이 담길 내부 컨테이너 (너비 고정하여 중앙 정렬)
        inner_content = tk.Frame(self.scrollable_frame, bg="#F5F7FA")
        inner_content.pack(padx=20, pady=10, expand=True)

        # --- [카드 1: 현장 및 관리] ---
        card1 = self.create_card(inner_content, "현장 및 관리")
        sub1 = tk.Frame(card1, bg="white")
        sub1.pack(pady=5)
        self.combo_site = ttk.Combobox(sub1, font=("맑은 고딕", 12), state="readonly", width=25)
        self.combo_site.grid(row=0, column=0, padx=10, pady=10)
        self.update_site_list()
        
        btn_f = tk.Frame(sub1, bg="white")
        btn_f.grid(row=0, column=1)
        tk.Button(btn_f, text="+ 새 현장", command=self.add_site, bg="#3B82F6", fg="white", relief="flat", font=("맑은 고딕", 10, "bold"), padx=15).pack(side="left", padx=5)
        tk.Button(btn_f, text="TXT 내보내기", command=self.export_to_txt, bg="#8B5CF6", fg="white", relief="flat", font=("맑은 고딕", 10, "bold"), padx=15).pack(side="left", padx=5)

        # --- [카드 2: 수위계 제원] ---
        card2 = self.create_card(inner_content, "수위계 제원 정보")
        sub2 = tk.Frame(card2, bg="white")
        sub2.pack()
        specs = ["관리번호:", "수위계 S/N:", "천공심도(m):", "수위(m):", "설치위치(m):"]
        self.entries_info = {}
        for i, label in enumerate(specs):
            r, c = divmod(i, 2)
            f = tk.Frame(sub2, bg="white")
            f.grid(row=r, column=c, padx=20, pady=5)
            tk.Label(f, text=label, bg="white", font=("맑은 고딕", 10)).pack(anchor="w")
            ent = tk.Entry(f, font=("맑은 고딕", 12), bg="#F8FAFC", relief="solid", borderwidth=1, width=25)
            ent.pack(pady=2)
            self.entries_info[label] = ent

        # --- [카드 3: 성적서 LGF 비교] ---
        card3 = self.create_card(inner_content, "성적서(Spec) 정보 및 비교")
        sub3 = tk.Frame(card3, bg="white")
        sub3.pack()
        tk.Label(sub3, text="성적서 L.G.F", bg="white", font=("맑은 고딕", 10)).grid(row=0, column=0, sticky="w", padx=15)
        self.ent_spec_lgf = tk.Entry(sub3, font=("맑은 고딕", 13, "bold"), bg="#FFFBEB", fg="#B45309", relief="solid", borderwidth=1, width=25, justify="center")
        self.ent_spec_lgf.grid(row=1, column=0, padx=15, pady=5)
        self.lbl_compare = tk.Label(sub3, text="성적서 대비 일치율: - %", font=("맑은 고딕", 12, "bold"), bg="white", fg="#059669")
        self.lbl_compare.grid(row=1, column=1, padx=20)

        # --- [카드 4: 단계별 측정] ---
        card4 = self.create_card(inner_content, "설치 단계별 V/W 측정값")
        sub4 = tk.Frame(card4, bg="white")
        sub4.pack()
        stages = ["설치 전 측정치", "설치 후 측정치", "초기치"]
        self.entries_base = {}
        for c, h in enumerate(["구분", "Digits (Hz²/1000)", "온도 (℃)"]):
            tk.Label(sub4, text=h, bg="white", font=("맑은 고딕", 10, "bold"), fg="#64748B").grid(row=0, column=c, padx=20, pady=5)
        for i, stage in enumerate(stages):
            tk.Label(sub4, text=stage, bg="white", font=("맑은 고딕", 10)).grid(row=i+1, column=0, padx=20, pady=5)
            ed = tk.Entry(sub4, font=("맑은 고딕", 12), bg="#F1F5F9", relief="flat", width=18, justify="center")
            ed.grid(row=i+1, column=1, padx=5, pady=2)
            et = tk.Entry(sub4, font=("맑은 고딕", 12), bg="#F1F5F9", relief="flat", width=18, justify="center")
            et.grid(row=i+1, column=2, padx=5, pady=2)
            self.entries_base[stage] = {"Digits": ed, "Temp": et}

        # --- [카드 5: 캘리브레이션 측정] ---
        card5 = self.create_card(inner_content, "현장 L.G.F 도출 측정 (1m 간격)")
        sub5_btn = tk.Frame(card5, bg="white")
        sub5_btn.pack(pady=5)
        tk.Button(sub5_btn, text="행 추가 +", command=self.add_calib_row, bg="#E2E8F0", relief="flat", padx=15).pack(side="left", padx=10)
        tk.Button(sub5_btn, text="행 삭제 -", command=self.remove_calib_row, bg="#E2E8F0", relief="flat", padx=15).pack(side="left", padx=10)
        self.calib_container = tk.Frame(card5, bg="white")
        self.calib_container.pack(pady=10)
        tk.Label(self.calib_container, text="수심(m)", bg="white", font=("맑은 고딕", 9, "bold"), width=15).grid(row=0, column=0)
        tk.Label(self.calib_container, text="측정 Digits", bg="white", font=("맑은 고딕", 9, "bold"), width=20).grid(row=0, column=1)
        for _ in range(5): self.add_calib_row()

        # 4. 결과 출력 및 하단 액션 버튼
        action_frame = tk.Frame(inner_content, bg="#F5F7FA")
        action_frame.pack(fill="x", pady=25)
        tk.Button(action_frame, text="L.G.F 계산 및 비교 실행", command=self.calculate_lgf, bg="#0F172A", fg="white", font=("맑은 고딕", 13, "bold"), height=2, width=35).pack()
        self.lbl_result = tk.Label(action_frame, text="현장 계산 L.G.F : -", font=("맑은 고딕", 15, "bold"), bg="#F5F7FA", fg="#EF4444")
        self.lbl_result.pack(pady=10)

        footer_btns = tk.Frame(inner_content, bg="#F5F7FA")
        footer_btns.pack(fill="x", pady=10)
        tk.Button(footer_btns, text="데이터 저장", command=self.save_data, bg="#22C55E", fg="white", font=("맑은 고딕", 11, "bold"), width=15, height=2).pack(side="left", padx=15)
        tk.Button(footer_btns, text="목록보기/삭제", command=self.load_data_dialog, bg="#F59E0B", fg="white", font=("맑은 고딕", 11, "bold"), width=15, height=2).pack(side="left", padx=15)
        tk.Button(footer_btns, text="초기화", command=self.clear_all, bg="#64748B", fg="white", font=("맑은 고딕", 11, "bold"), width=10, height=2).pack(side="right", padx=15)

    # --- 유틸리티 및 디자인 함수 ---
    def create_card(self, parent, title):
        container = tk.Frame(parent, bg="#F5F7FA")
        container.pack(fill="x", pady=10)
        card = tk.Frame(container, bg="white", highlightbackground="#E2E8F0", highlightthickness=1)
        card.pack(fill="x", ipadx=15, ipady=15)
        tk.Label(card, text=title, bg="white", font=("맑은 고딕", 12, "bold"), fg="#1E293B").pack(pady=(5, 15))
        return card

    # --- 태블릿 터치 스크롤 제어 로직 ---
    def _on_touch_start(self, event):
        self.main_container.scan_mark(event.x, event.y)

    def _on_touch_drag(self, event):
        self.main_container.scan_dragto(event.x, event.y, gain=1)

    def _on_mousewheel(self, event):
        self.main_container.yview_scroll(int(-1*(event.delta/120)), "units")

    # --- 비즈니스 로직 ---
    def update_site_list(self):
        sites = [d for d in os.listdir(self.base_dir) if os.path.isdir(os.path.join(self.base_dir, d))]
        self.combo_site['values'] = sites
        if sites: self.combo_site.current(0)

    def add_site(self):
        name = simpledialog.askstring("현장 추가", "현장명을 입력하세요:")
        if name:
            path = os.path.join(self.base_dir, name)
            if not os.path.exists(path): os.makedirs(path)
            self.update_site_list()
            self.combo_site.set(name)

    def add_calib_row(self):
        idx = len(self.calib_rows) + 1
        e1 = tk.Entry(self.calib_container, font=("맑은 고딕", 12), justify="center", bg="#F8FAFC", width=15)
        e1.grid(row=idx, column=0, padx=5, pady=3)
        e2 = tk.Entry(self.calib_container, font=("맑은 고딕", 12), justify="center", bg="#F8FAFC", width=20)
        e2.grid(row=idx, column=1, padx=5, pady=3)
        self.calib_rows.append((e1, e2))

    def remove_calib_row(self):
        if len(self.calib_rows) > 1:
            e1, e2 = self.calib_rows.pop()
            e1.destroy(); e2.destroy()

    def calculate_lgf(self):
        try:
            depths, digits = [], []
            for d_e, dig_e in self.calib_rows:
                if d_e.get() and dig_e.get():
                    depths.append(float(d_e.get()))
                    digits.append(float(dig_e.get()))
            if len(depths) < 2:
                messagebox.showwarning("입력 부족", "데이터를 2개 이상 입력하세요.")
                return
            base_d, base_dig = depths[0], digits[0]
            lgfs = []
            for i in range(1, len(depths)):
                dp = (depths[i] - base_d) * 0.1
                dd = digits[i] - base_dig
                if dd != 0: lgfs.append(dp / dd)
            self.current_lgf_field = sum(lgfs) / len(lgfs)
            self.lbl_result.config(text=f"현장 계산 L.G.F : {self.current_lgf_field:.7f}")
            spec_val = self.ent_spec_lgf.get()
            if spec_val:
                spec_lgf = float(spec_val)
                match_rate = (min(abs(spec_lgf), abs(self.current_lgf_field)) / max(abs(spec_lgf), abs(self.current_lgf_field))) * 100
                self.lbl_compare.config(text=f"성적서 대비 일치율: {match_rate:.2f} %")
                self.lbl_compare.config(fg="#059669" if match_rate >= 90 else "#EF4444")
        except: messagebox.showerror("오류", "숫자 형식을 확인하세요.")

    def save_data(self):
        site = self.combo_site.get()
        mng_no = self.entries_info["관리번호:"].get().strip()
        if not site or not mng_no:
            messagebox.showwarning("필수", "현장명과 관리번호를 입력하세요.")
            return
        data = {
            "info": {k: v.get() for k, v in self.entries_info.items()},
            "spec_lgf": self.ent_spec_lgf.get(),
            "base": {k: {"Digits": v["Digits"].get(), "Temp": v["Temp"].get()} for k, v in self.entries_base.items()},
            "calib": [{"depth": d.get(), "digits": dig.get()} for d, dig in self.calib_rows],
            "field_lgf": self.current_lgf_field
        }
        with open(os.path.join(self.base_dir, site, f"{mng_no}.json"), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        messagebox.showinfo("저장 완료", f"{mng_no} 데이터가 저장되었습니다.")

    def export_to_txt(self):
        site = self.combo_site.get()
        if not site: return
        site_path = os.path.join(self.base_dir, site)
        files = [f for f in os.listdir(site_path) if f.endswith('.json')]
        if not files:
            messagebox.showinfo("알림", "저장된 데이터가 없습니다.")
            return
        now = datetime.now().strftime("%Y%m%d_%H%M")
        export_file = f"{site}_일괄데이터_{now}.txt"
        with open(export_file, 'w', encoding='utf-8') as out:
            out.write(f"=== {site} 지하수위계 일괄 데이터 ===\n\n")
            for f_name in files:
                with open(os.path.join(site_path, f_name), 'r', encoding='utf-8') as f:
                    d = json.load(f)
                out.write(f"■ 관리번호: {d['info'].get('관리번호:', 'N/A')}\n")
                out.write(f"S/N: {d['info'].get('수위계 S/N:', '')} | 현장LGF: {d.get('field_lgf', 0):.7f}\n")
                out.write(f"성적서LGF: {d.get('spec_lgf', '미입력')}\n")
                out.write(f"------------------------------------------\n")
        messagebox.showinfo("내보내기 성공", f"'{export_file}' 파일이 생성되었습니다.")

    def load_data_dialog(self):
        site = self.combo_site.get()
        if not site: return
        site_path = os.path.join(self.base_dir, site)
        files = [f.replace('.json', '') for f in os.listdir(site_path) if f.endswith('.json')]
        win = tk.Toplevel(self.root)
        win.title("데이터 목록")
        win.geometry("400x550")
        lb = tk.Listbox(win, font=("맑은 고딕", 11)); lb.pack(fill="both", expand=True, padx=20, pady=20)
        for f in files: lb.insert(tk.END, f)
        
        def do_load():
            if not lb.curselection(): return
            name = lb.get(lb.curselection())
            with open(os.path.join(site_path, f"{name}.json"), 'r', encoding='utf-8') as f:
                d = json.load(f)
            self.clear_all()
            for k, v in d["info"].items(): 
                if k in self.entries_info: self.entries_info[k].insert(0, v)
            self.ent_spec_lgf.insert(0, d.get("spec_lgf", ""))
            for k, v in d["base"].items():
                if k in self.entries_base:
                    self.entries_base[k]["Digits"].insert(0, v["Digits"])
                    self.entries_base[k]["Temp"].insert(0, v["Temp"])
            cal_d = d["calib"]
            while len(self.calib_rows) < len(cal_d): self.add_calib_row()
            for i, row in enumerate(cal_d):
                self.calib_rows[i][0].insert(0, row["depth"])
                self.calib_rows[i][1].insert(0, row["digits"])
            self.current_lgf_field = d.get("field_lgf", 0)
            self.lbl_result.config(text=f"현장 계산 L.G.F : {self.current_lgf_field:.7f}")
            win.destroy()

        def do_del():
            if not lb.curselection(): return
            name = lb.get(lb.curselection())
            if messagebox.askyesno("삭제", f"{name} 데이터를 삭제하시겠습니까?"):
                os.remove(os.path.join(site_path, f"{name}.json"))
                lb.delete(lb.curselection())

        tk.Button(win, text="데이터 불러오기", command=do_load, bg="#3B82F6", fg="white", font=("맑은 고딕", 10, "bold"), height=2).pack(fill="x", padx=30, pady=5)
        tk.Button(win, text="데이터 삭제", command=do_del, bg="#EF4444", fg="white", font=("맑은 고딕", 10), height=1).pack(fill="x", padx=30, pady=5)

    def clear_all(self):
        for e in self.entries_info.values(): e.delete(0, tk.END)
        self.ent_spec_lgf.delete(0, tk.END)
        self.lbl_compare.config(text="성적서 대비 일치율: - %", fg="#059669")
        for d in self.entries_base.values():
            d["Digits"].delete(0, tk.END); d["Temp"].delete(0, tk.END)
        while len(self.calib_rows) > 5: self.remove_calib_row()
        for e1, e2 in self.calib_rows: e1.delete(0, tk.END); e2.delete(0, tk.END)
        self.lbl_result.config(text="현장 계산 L.G.F : -")

if __name__ == "__main__":
    root = tk.Tk()
    app = TabletPiezometerApp(root)
    root.mainloop()
