from time import time as epoch
from datetime import datetime, timedelta
from tkinter import Event as TkEvent
from tkinter import ttk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
from typing import Any, Self
from collections.abc import Iterator
import tkinter as tk
import json

WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
PRIORITIES = ['black', '#005500', '#00BB00', '#00FF00', '#77DD00', '#AADD00', '#DDDD00', '#FFBB00', '#FF9900', '#FF6600', '#FF0000']

def stoi(s: str, empty=0) -> int:
    return empty if s == "" else int(s)

def get_week(date) -> tuple[datetime, datetime]:
    date -= timedelta(days=date.weekday())
    return (date, date + timedelta(days=6))

def get_first_day_of_month(date) -> datetime:
    return date - timedelta(days=date.day - 1)

def format_date(date) -> str:
    return date.strftime("%A %d %B %Y")

def ask_conflict():
    return messagebox.askokcancel(
        title="Schedule conflict",
        message="There is a conflict between the time of different events.\nRemove all other events in conflict?"
    )

def create_tooltip(master: tk.Widget, widget) -> tk.Toplevel:
    window = tk.Toplevel(master)
    window.wm_overrideredirect(True)
    
    delta_x = 10
    delta_y = 5
    widget: tk.Widget = widget(window)
    width = 5 * 2 + widget.winfo_reqwidth()
    height = 3 * 2 + widget.winfo_reqheight()
    mouse_x, mouse_y = master.winfo_pointerxy()
    x = mouse_x + delta_x
    y = mouse_y + delta_y
    if x + width > master.winfo_screenwidth() and y + height > master.winfo_screenheight():
        x = mouse_x - delta_x - width
        y = mouse_y - delta_y - height
    y = max(0, y)

    window.wm_geometry(f"+{x}+{y}")
    return window

def tooltip(master: tk.Widget, widget: 'TkWidget'):
    return Tooltip(master, lambda window: widget.pack_widget(window))

class TkWidget:
    pack: dict[str, Any]
    args: list[Any]
    kwargs: dict[str, Any]

    def __init__(self, cl, *args, pack = {}, **kwargs):
        self.cl = cl
        self.pack = pack
        self.args = args
        self.kwargs = kwargs
    
    def pack_widget(self, master: tk.Widget, **kwargs) -> tk.Widget:
        widget = self.cl(master, *self.args, **self.kwargs)
        widget.pack(**kwargs, **self.pack)
        return widget
    
    def grid_widget(self, master: tk.Widget, **kwargs) -> tk.Widget:
        widget = self.cl(master, *self.args, **self.kwargs)
        widget.grid(**kwargs, **self.pack)
        return widget
    
    def join(self, pack={}, *args, **kwargs) -> Self:
        return TkWidget(self.cl, *self.args, *args, pack={**self.pack, **pack}, **self.kwargs, **kwargs)
    
    def add_args(self, **kwargs):
        self.kwargs |= kwargs
    
    def add_pack(self, **kwargs):
        self.pack |= kwargs

class FrameBase(ttk.Frame):
    def __init__(self, master = None, **kwargs):
        super().__init__(master, **kwargs)
    
    def __iter__(self) -> Iterator[tk.Widget]:
        return iter(self.winfo_children())
    
    def pack(self, **kwargs):
        super().pack_configure(**kwargs)
        return self

    def grid(self, **kwargs):
        super().grid_configure(**kwargs)
        return self

class HFrame(FrameBase):
    def __init__(self, master = None, widgets: list[TkWidget] = [], pack_all={}, last_left=True, **kwargs):
        super().__init__(master, **kwargs)
        
        w = []
        
        for widget in widgets:
            if widget is not None:
                w.append(widget)

        for i, widget in enumerate(w):
            if last_left or i + 1 != len(w):
                widget = widget.join(pack={"side": tk.LEFT})
            
            widget.pack_widget(self, **pack_all)

class VFrame(FrameBase):
    def __init__(self, master = None, widgets: list[TkWidget] = [], pack_all={}, **kwargs):
        super().__init__(master, **kwargs)

        for widget in widgets:
            if widget is not None:
                widget.pack_widget(self, **pack_all)

class GridFrame(FrameBase):
    widgets: list[list[tk.Widget]]
    
    def __init__(self, master = None, widgets: list[list[TkWidget]] = [], pack_all={}, **kwargs):
        super().__init__(master, **kwargs)
        
        self.widgets = []

        for r in range(len(widgets)):
            a = []
            
            for c in range(len(widgets[r])):
                a.append(None if widgets[r][c] is None else widgets[r][c].grid_widget(self, row=r, column=c, **pack_all))
            
            self.widgets.append(a)
    
    def __iter__(self):
        return iter(self.widgets)

class Selector(tk.Radiobutton):
    def __init__(self, master, text, command=lambda _:(), variable="", value=None, selected=False):
        if value is None:
            value = text
        
        super().__init__(master, text=text, value=value, variable=variable, command=lambda:command(value), indicatoron=False, selectcolor="#AAAAAA", activebackground="#CCCCCC", relief=tk.FLAT, borderwidth=0)
        
        if selected:
            self.select()

class Tooltip:
    master: tk.Widget
    window: tk.Toplevel
    
    def __init__(self, master: tk.Widget, widget=lambda w: VFrame(w).pack()):
        master.bind("<Enter>", self.on_enter)
        master.bind("<Leave>", self.on_leave)
        master.bind("<ButtonPress>", self.on_leave)
        
        self.master = master
        self.id = None
        self.window = None
        self.widget = widget

    def on_enter(self, _=None):
        self.cancel()
        self.id = self.master.after(400, self.show)

    def on_leave(self, _=None):
        self.cancel()
        
        if self.window is not None:
            self.window.destroy()
            self.window = None

    def cancel(self):
        if self.id is not None:
            self.master.after_cancel(self.id)
            self.id = None

    def show(self):
        self.window = create_tooltip(self.master, self.widget)

class TreeGroup:
    selected: 'Tree'
    ids: int
    
    def __init__(self):
        self.selected = None
        self.ids = 0

class Tree(ttk.Treeview):
    window: tk.Toplevel
    widget: TkWidget
    selected: int
    selectable: bool
    group: TreeGroup
    group_id: int
    
    def __init__(self, master, rows, width, group: TreeGroup = None, on_select=lambda _:None, on_tooltip=lambda _:None, selectable=True):
        super().__init__(master, columns=(), height=rows, show='tree', selectmode="none", takefocus=selectable)
        self.column('#0', width=width)
        self.bind('<Motion>', self.motion)
        self.bind('<Button-1>', self.click)
        self.bind('<Leave>', self.cancel)
        self.tag_configure("selected", foreground="white", background="dark cyan")
        self.on_select = on_select
        self.on_tooltip = on_tooltip
        self.id = None
        self.window = None
        self.hover_row = -1
        self.selected = -1
        self.selectable = selectable
        self.group = group
        
        if group is not None:
            self.group_id = group.ids
            group.ids += 1

        for i in range(rows):
            self.insert("", tk.END, i)
    
    def cancel(self, _=None):
        if self.window is not None:
            self.window.destroy()
            self.window = None
        
        if self.id is not None:
            self.after_cancel(self.id)
            self.id = None
            self.hover_row = -1
    
    def motion(self, event: TkEvent):
        row = stoi(self.identify_row(event.y))
        
        if row != self.hover_row:
            self.cancel()
            self.hover_row = row
            self.widget = self.on_tooltip(row)
            
            if self.widget is not None:
                self.id = self.after(400, self.tooltip)
    
    def tooltip(self):
        self.window = create_tooltip(self, lambda window: self.widget.pack_widget(window))
    
    def click(self, event: TkEvent):
        if self.selectable:
            row = stoi(self.identify_row(event.y), -1)
            
            if self.selected != row:
                self.deselect()
                self.selected = row
                
                if self.group is not None and self.group.selected is not self:
                    if self.group.selected is not None:
                        self.group.selected.deselect()
                    self.group.selected = self
                
                if row != -1:
                    self.selected_tags = self.item(row)["tags"]
                    self.item(row, tags="selected")
                    self.on_select(row)
    
    def deselect(self, _=None):
        if self.selected != -1:
            self.item(self.selected, tags=self.selected_tags)
            self.selected = -1

class ViewTime:
    time: datetime
    
    def __init__(self):
        self.time = datetime.now()
        self.time -= timedelta(hours=self.time.hour, minutes=self.time.minute, seconds=self.time.second, microseconds=self.time.microsecond)

def calendar():
    def check_conflict(time: datetime, quarters: int):
        for _ in range(quarters):
            if time in time_map:
                return True
            
            time += timedelta(minutes=15)
        
        return False

    class Event:
        start: datetime
        hours: int
        minutes: int
        name: str
        description: str
        priority: int
        
        def __init__(self, start, hours, minutes, name, description, priority):
            self.start = start
            self.hours = hours
            self.minutes = minutes
            self.name = name
            self.description = description
            self.priority = priority
        
        def quarters(self) -> int:
            return self.hours * 4 + self.minutes
        
        def update(self, hours, minutes, name, description, priority):
            q = self.quarters()
            r = hours * 4 + minutes
            
            if r == 0:
                self.remove()
            else:
                t = self.start + timedelta(minutes=15 * q)
                
                if q > r:
                    for _ in range(q - r):
                        t -= timedelta(minutes=15)
                        time_map.pop(t)
                elif q < r:
                    if check_conflict(t, r - q) and not ask_conflict():
                        return
                    
                    event_id = time_map[self.start]
                    
                    for _ in range(r - q):
                        e = time_map.get(t)
                        
                        if e is not None:
                            schedule[e].remove()
                        
                        time_map[t] = event_id
                        t += timedelta(minutes=15)
                
                self.hours = hours
                self.minutes = minutes
                self.name = name
                self.description = description
                self.priority = priority
        
        def remove(self):
            t = self.start
            e = time_map[t]
            
            for _ in range(self.quarters()):
                time_map.pop(t)
                t += timedelta(minutes=15)
            
            schedule.pop(e)
        
        def color(self):
            return PRIORITIES[min(self.priority, len(PRIORITIES) - 1)]


    class Timetable(ttk.Frame):
        slots: list[Tree]
        selected: int

        def __init__(self, master=None, headings: list[TkWidget] = [], on_select=lambda:None, on_tooltip=lambda s, r:None, group: TreeGroup = None, **kwargs):
            super().__init__(master)

            frame = ttk.Frame(self)
            frame.pack()

            self.hours = Tree(frame, 24, 120, selectable=False)
            self.hours.grid(column=0, row=1)

            for (i, heading) in enumerate(headings):
                heading.grid_widget(frame, row=0, column=i + 1, **kwargs)
            
            self.slots = []
            self.selected = -1
            self.on_select = on_select
            self.on_tooltip = on_tooltip

            for i in range(len(headings)):
                slot = Tree(frame, 24, 120, group=group, on_select=lambda _:self.on_select(), on_tooltip=lambda r, i=i: self.on_tooltip(i, r))
                
                for p in PRIORITIES:
                    slot.tag_configure(p, foreground=p)
                
                slot.grid(column=i + 1, row=1)

                self.slots.append(slot)

            HFrame(self, [
                TkWidget(Selector, text="24 Hours", command=self.time_mode, value=False, variable=time_mode_var, selected=not time_mode_var.get()),
                TkWidget(Selector, text="AM / PM", command=self.time_mode, value=True, variable=time_mode_var, selected=time_mode_var.get()),
            ], pack_all={"fill": tk.X, "expand": True}).pack(fill=tk.X, pady=10)

            self.time_mode(time_mode_var.get())
        
        def time_mode(self, mode):
            for h in range(24):
                i = (h - 12) if h >= 12 else h
                if i == 0:
                    i = 12
                
                self.hours.item(h, text=f"{i:02}:00 {'p' if h >= 12 else 'a'}.m." if mode else f"{h:02}:00")
        
        def set_event(self, slot: int, index, event: Event):
            self.slots[slot].item(index, text=event.name, tags=event.color())

    def add_event(time: datetime, hours: int, minutes: int, name: str, description: str, priority: int):
        if check_conflict(time, hours * 4 + minutes) and not ask_conflict():
            return False

        event_id = epoch()
        schedule[event_id] = Event(time, hours, minutes, name, description, priority)

        for _ in range(hours * 4 + minutes):
            e = time_map.get(time)
            
            if e is not None:
                schedule[e].remove()

            time_map[time] = event_id
            time += timedelta(minutes=15)
        
        return True

    def event_tooltip(e: Event) -> TkWidget:
        if e is None: return None
        
        if e.hours == 0:
            duration = f"{int(e.minutes) * 15} minutes"
        elif e.minutes == 0:
            duration = f"{e.hours} hours"
        else:
            duration = f"{e.hours} hours {int(e.minutes) * 15} minutes"
        
        return TkWidget(
            VFrame, widgets=[
                TkWidget(ttk.Label, relief=tk.SOLID, background='white', text=e.name, foreground=e.color()),
                None if e.description == "" or str.isspace(e.description) else TkWidget(ttk.Label, relief=tk.SOLID, background='white', text=e.description),
                TkWidget(ttk.Label, relief=tk.SOLID, background='white', text=e.start.strftime("%H:%M")),
                TkWidget(ttk.Label, relief=tk.SOLID, background='white', text=duration),
            ], pack_all={"fill": tk.X}, style='Tooltip.TFrame', relief=tk.SOLID, padding=1
        )

    def update_view(mode = None, time=None):
        for c in list(calendar_frame.children.keys()):
            calendar_frame.children[c].destroy()

        if mode is None:
            mode = view_mode.get()

        if time is not None:
            view_time.time = time

        match mode:
            case "Daily":
                time_label.configure(text=format_date(view_time.time))
                daily.select()
                reset.configure(text="Today")

                event_var = tk.StringVar()
                duration_hour = tk.StringVar(value='0')
                duration_minutes = tk.StringVar(value='00')
                priority_var = tk.StringVar(value='0')
                visible = tk.BooleanVar()
                group = TreeGroup()

                def get_time(slot=-1, row=-1):
                    if slot == -1:
                        slot = group.selected.group_id
                    
                    if row == -1:
                        row = group.selected.selected
                    
                    return view_time.time + timedelta(hours=row, minutes=[0, 15, 30, 45][slot])
                
                def event_command():
                    if group.selected is not None:
                        n = event_var.get()
                        
                        if n == "" or str.isspace(n):
                            messagebox.showerror("Invalid name", "Please enter a valid name that contains more than just whitespaces")
                            return
                        
                        h = stoi(duration_hour.get())
                        m = int(duration_minutes.get()) // 15
                        
                        if h == 0 and m == 0:
                            messagebox.showerror("Invalid time", "Please enter time more than zero")
                            return
                        
                        time = get_time()
                        d = description.get("1.0", tk.END)
                        p = stoi(priority_var.get())
                        e = time_map.get(time)
                        
                        if e is not None:
                            e = schedule[e]
                            q = e.quarters()
                            e.update(h, m, n, d, p)
                            
                            if e.quarters() != q:
                                update_view()
                        elif add_event(time, h, m, n, d, p):
                            update_view()
                
                def remove_event():
                    if group.selected is not None:
                        e = time_map.get(get_time())
                        
                        if e is not None:
                            schedule[e].remove()
                            update_view()
                
                def on_select():
                    if group.selected is not None and group.selected.selected != -1:
                        if not visible.get():
                            frame.pack()
                            visible.set(True)
                        
                        e = time_map.get(get_time())
                        description.delete("1.0", tk.END)
                        
                        if e is not None:
                            e = schedule[e]
                            label.configure(text="Event details")
                            button.configure(text="Update")
                            event_var.set(e.name)
                            description.insert(tk.END, e.description)
                            duration_hour.set(str(e.hours))
                            duration_minutes.set(str(e.minutes * 15) if e.minutes != 0 else "00")
                            priority_var.set(str(e.priority))
                            remove.pack()
                        else:
                            label.configure(text="Add new event")
                            button.configure(text="Add event")
                            event_var.set("")
                            duration_hour.set('0')
                            duration_minutes.set('00')
                            priority_var.set('0')
                            remove.pack_forget()
                    elif visible.get():
                        frame.pack_forget()
                        visible.set(False)
                
                def on_tooltip(slot: int, row: int) -> TkWidget:
                    time = get_time(slot, row)
                    e = time_map.get(time)
                    return event_tooltip(e if e is None else schedule[e])
                
                timetable: Timetable
                timetable, frame = HFrame(calendar_frame, [
                    TkWidget(Timetable, headings=[TkWidget(ttk.Label, text=[":00 - :15", ":15 - :30", ":30 - :45", ":45 - :00"][i]) for i in range(4)], on_select=on_select, on_tooltip=on_tooltip, group=group),
                    TkWidget(VFrame, widgets=[
                        TkWidget(ttk.Label),
                        TkWidget(GridFrame, widgets=[
                            [
                                TkWidget(ttk.Label, text="Event:", pack={"sticky": tk.W, "padx": 10}),
                                TkWidget(ttk.Entry, textvariable=event_var, pack={"sticky": tk.NSEW}),
                            ],
                            [
                                TkWidget(ttk.Label, text="Description:", pack={"sticky": tk.W, "padx": 10}),
                                TkWidget(ScrolledText, height=3, width=45),
                            ],
                            [
                                TkWidget(ttk.Label, text="Duration:", pack={"sticky": tk.W, "padx": 10}),
                                TkWidget(HFrame, widgets=[
                                    TkWidget(ttk.Spinbox, from_=0, to_=float('inf'), justify=tk.RIGHT, textvariable=duration_hour, validate=tk.ALL, validatecommand=(int_only, '%P')),
                                    TkWidget(ttk.Label, text="hours", pack={"padx": 10}),
                                    TkWidget(ttk.OptionMenu, duration_minutes, "00", "00", "15", "30", "45"),
                                    TkWidget(ttk.Label, text="minutes", pack={"padx": 10}),
                                ], pack={"sticky": tk.W}),
                            ],
                            [
                                TkWidget(ttk.Label, text="Priority:", pack={"sticky": tk.W, "padx": 10}),
                                TkWidget(ttk.Spinbox, from_=0, to_=float('inf'), textvariable=priority_var, validate=tk.ALL, validatecommand=(int_only, '%P'), pack={"sticky": tk.NSEW}),
                            ],
                        ]),
                        TkWidget(HFrame, widgets=[
                            TkWidget(ttk.Button, command=event_command),
                            TkWidget(ttk.Button, text="Remove", command=remove_event),
                        ]),
                    ]),
                ], last_left=False).pack(fill=tk.X)
                
                label: ttk.Label
                description: ScrolledText
                button: ttk.Button
                remove: ttk.Button
                
                (
                    label,
                    (
                        (_, _),
                        (_, description),
                        (_, _),
                        (p_label, _),
                    ),
                    (button, remove),
                ) = frame
                
                tooltip(p_label, TkWidget(VFrame, style='Tooltip.TFrame', relief=tk.SOLID, widgets=[
                    TkWidget(ttk.Label, foreground=color, background='white', text=f"Priority {p}", pack={"fill": tk.X, "padx": 5, "pady": 3})
                for p, color in enumerate(PRIORITIES)]))
                
                frame.pack_forget()
                
                for hour in range(24):
                    for minute in range(4):
                        time = view_time.time + timedelta(hours=hour, minutes=minute * 15)
                        e = time_map.get(time)

                        if e is not None:
                            timetable.set_event(minute, hour, schedule[e])
            case "Weekly":
                (s, e) = get_week(view_time.time)
                time_label.configure(text=f"{format_date(s)} - {format_date(e)}")
                weekly.select()
                reset.configure(text="This Week")

                def heading(d):
                    day = s + timedelta(days=d)
                    return TkWidget(tk.Button, justify="center", text=f"{WEEKDAYS[d]}\n{day.year}-{day.month}-{day.day}", command=lambda d=day:update_view("Daily", d))
                
                def get_event(time: datetime) -> Event:
                    e = None
                    
                    for _ in range(4):
                        q = time_map.get(time)
                        
                        if q is not None:
                            q = schedule[q]
                            
                            if e is None or e.priority <= q.priority:
                                e = q
                        
                        time += timedelta(minutes=15)
                    
                    return e
                
                group = TreeGroup()
                timetable, _ = HFrame(calendar_frame, [
                    TkWidget(Timetable, headings=[heading(d) for d in range(7)], on_tooltip=lambda slot, row: event_tooltip(get_event(s + timedelta(days=slot, hours=row))), group=group, sticky=tk.NSEW),
                    TkWidget(HFrame),
                ], last_left=False).pack()
                
                t = s
                
                for d in range(7):
                    for h in range(24):
                        e = get_event(t)
                        
                        if e is not None:
                            timetable.set_event(d, h, e)
                        
                        t += timedelta(hours=1)
            case "Monthly":
                monthly.select()
                reset.configure(text="This Month")

                s = get_first_day_of_month(view_time.time)
                day = s
                month = s.month
                week = 1
                group = TreeGroup()
                frame = ttk.Frame(calendar_frame)
                frame.pack()
                
                for d, wd in enumerate(WEEKDAYS):
                    ttk.Label(frame, text=wd).grid(row=0, column=d)
                    frame.grid_columnconfigure(d, weight=1, uniform="frame")
                
                while True:
                    time = day
                    es: set[Event] = set()
                    
                    for _ in range(24 * 4):
                        e = time_map.get(time)
                        
                        if e is not None:
                            es.add(schedule[e])
                        
                        time += timedelta(minutes=15)
                    
                    es = sorted(es, key=lambda e: (e.priority, e.start))
                    es = es[-3:]
                    
                    tree: Tree
                    _, tree = VFrame(frame, widgets=[
                        TkWidget(ttk.Button, text=day.day, command=lambda d=day:update_view("Daily", d)),
                        TkWidget(Tree, 3, 50, group=group),
                    ], pack_all={"fill": tk.X}).grid(sticky=tk.NSEW, padx=1, column=day.weekday(), row=week)
                    
                    for p in PRIORITIES:
                        tree.tag_configure(p, foreground=p)
                    
                    for i, e in enumerate(es):
                        tree.item(i, text=e.name, tags=e.color())
                    
                    tree.on_tooltip = lambda row, es=es: event_tooltip(es[row] if row < len(es) else None)
                    
                    day += timedelta(days=1)

                    if day.month != month:
                        break

                    if day.weekday() == 0:
                        week += 1
                
                day = s
                
                for w in range(week):
                    ttk.Button(frame, text="View week", command=lambda w=day:update_view("Weekly", w)).grid(sticky=tk.NSEW, row=w + 1, column=7)
                    day += timedelta(weeks=1)
                
                time_label.configure(text=f"{format_date(s)} - {format_date(day - timedelta(days=1))}")

    time_map: dict[datetime, float] = {}
    schedule: dict[float, Event] = {}
    
    try:
        with open('calendar.json') as f:
            d = json.load(f)
            iso_map = d["map"]
            events = d["events"]
            
            for iso, e in iso_map.items():
                time_map[datetime.fromisoformat(iso)] = e
            
            for event_id, e in events.items():
                schedule[float(event_id)] = Event(
                    datetime.fromisoformat(e["start"]),
                    e["hours"],
                    e["minutes"],
                    e["name"],
                    e["description"],
                    e["priority"],
                )
    except FileNotFoundError:
        pass

    window = tk.Tk()
    window.minsize(1400, 900)
    window.title("Calendar")

    int_only = window.register(lambda s:s == "" or str.isdigit(s))

    view_time = ViewTime()
    view_mode = tk.StringVar()
    time_mode_var = tk.BooleanVar()

    def time_prev():
        old = view_time.time

        match view_mode.get():
            case "Daily":
                view_time.time -= timedelta(days=1)
            case "Weekly":
                view_time.time -= timedelta(weeks=1)
            case "Monthly":
                view_time.time = get_first_day_of_month(view_time.time)
                view_time.time -= timedelta(days=1)
                view_time.time = get_first_day_of_month(view_time.time)
        
        if old != view_time.time:
            update_view()

    def time_next():
        old = view_time.time

        match view_mode.get():
            case "Daily":
                view_time.time += timedelta(days=1)
            case "Weekly":
                view_time.time += timedelta(weeks=1)
            case "Monthly":
                month = view_time.time.month

                while view_time.time.month == month:
                    view_time.time += timedelta(days=1)
        
        if old != view_time.time:
            update_view()

    def reset_time():
        view_time.time = datetime.now()
        view_time.time -= timedelta(hours=view_time.time.hour, minutes=view_time.time.minute, seconds=view_time.time.second, microseconds=view_time.time.microsecond)
        update_view()

    root_frame = VFrame(window, padding=50, widgets=[
        TkWidget(ttk.Label, text="Calendar"),
        TkWidget(HFrame, widgets=[
            TkWidget(Selector, text="Daily", variable=view_mode, command=update_view, selected=True),
            TkWidget(Selector, text="Weekly", variable=view_mode, command=update_view),
            TkWidget(Selector, text="Monthly", variable=view_mode, command=update_view),
        ], pack_all={"fill": tk.X, "expand": True}, pack={"fill": tk.X}),
        TkWidget(VFrame, widgets=[
            TkWidget(VFrame, widgets=[
                TkWidget(ttk.Button, text="<-", command=time_prev, pack={"side": tk.LEFT}),
                TkWidget(ttk.Button, text="->", command=time_next, pack={"side": tk.RIGHT}),
                TkWidget(ttk.Label, pack={"expand": True, "padx": 10}),
            ], pack={"pady": 10}),
            TkWidget(tk.Button, relief=tk.SOLID, command=reset_time),
        ], pack={"fill": tk.X}),
        TkWidget(VFrame, pack={"fill": tk.BOTH, "expand": True}),
    ], pack_all={"pady": 10}).pack(fill=tk.BOTH, expand=True)

    daily: Selector
    weekly: Selector
    monthly: Selector
    time_frame: ttk.Frame
    time_label: ttk.Label
    reset: tk.Button
    calendar_frame: ttk.Frame
    (
        _,
        (daily, weekly, monthly),
        (time_frame, reset),
        calendar_frame,
    ) = root_frame
    _, _, time_label = time_frame

    update_view("Daily")

    style = ttk.Style()
    style.configure('Tooltip.TFrame', background='white')

    window.after(200, lambda: reset.place(anchor=tk.E, relx=1, rely=0.5, height=time_frame.winfo_height()))
    window.mainloop()
    
    iso_map = {}
    events = {}
    
    for d, e in time_map.items():
        iso_map[d.isoformat()] = e
    
    for event_id, e in schedule.items():
        d = e.__dict__
        d["start"] = d["start"].isoformat()
        events[event_id] = d
    
    with open('calendar.json', 'w') as f:
        json.dump({"map": iso_map, "events": events}, f, indent=4)

if __name__ == '__main__':
    calendar()
