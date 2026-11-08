from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import StringProperty, NumericProperty
from kivy.uix.filechooser import FileChooserListView
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDIconButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.pickers import MDDatePicker
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.fitimage import FitImage
from kivymd.toast import toast

import database as db
import csv
import os
import shutil
from datetime import datetime

STATUS_PENDING = "В ожидании"
STATUS_DONE = "Выполнено"
STATUSES = [STATUS_PENDING, STATUS_DONE]
STATUS_COLORS = {STATUS_PENDING: [1.0, 0.6, 0.0, 1], STATUS_DONE: [0.2, 0.7, 0.3, 1]}
STATUS_ICONS = {STATUS_PENDING: "clock-outline", STATUS_DONE: "check-circle"}
SORT_OPTIONS = {
    "new": "Сначала новые", "old": "Сначала старые",
    "price_asc": "Цена ↑", "price_desc": "Цена ↓",
    "date_asc": "Дата ↑", "date_desc": "Дата ↓",
    "name_asc": "Название А-Я", "status": "По статусу",
}
DEFAULT_CATEGORIES = ["Клиенты", "Свои", "На продажу", "Прочее"]

KV = '''
<CarItem>:
    orientation: "vertical"
    size_hint_y: None
    height: dp(140) if root.photo else dp(120)
    padding: dp(10)
    spacing: dp(6)
    radius: [12]
    elevation: 2
    md_bg_color: 1, 1, 1, 1

    MDBoxLayout:
        orientation: "horizontal"
        spacing: dp(10)
        size_hint_y: None
        height: dp(90)

        FitImage:
            source: root.photo if root.photo else ""
            size_hint: (None, None)
            size: (dp(70), dp(70))
            radius: [8]
            opacity: 1 if root.photo else 0

        MDBoxLayout:
            orientation: "vertical"
            spacing: dp(2)

            MDLabel:
                text: root.car_name
                bold: True
                font_style: "Subtitle1"
                theme_text_color: "Primary"
                shorten: True

            MDLabel:
                text: f"{root.price} ₽  •  {root.date}"
                font_style: "Caption"
                theme_text_color: "Secondary"
                shorten: True

            MDLabel:
                text: root.vin if root.vin else ""
                font_style: "Caption"
                theme_text_color: "Hint"
                shorten: True

            MDLabel:
                text: root.note if root.note else ""
                font_style: "Caption"
                theme_text_color: "Secondary"
                shorten: True
                opacity: 1 if root.note else 0

        MDBoxLayout:
            orientation: "vertical"
            size_hint_x: None
            width: dp(40)
            spacing: dp(2)

            MDIconButton:
                icon: "pencil"
                theme_text_color: "Custom"
                text_color: 0.2, 0.5, 0.9, 1
                on_release: app.open_edit_dialog(root.car_id)

            MDIconButton:
                icon: "delete"
                theme_text_color: "Custom"
                text_color: 0.9, 0.3, 0.3, 1
                on_release: app.confirm_delete(root.car_id)

    MDBoxLayout:
        orientation: "horizontal"
        spacing: dp(6)
        size_hint_y: None
        height: dp(36)

        MDIcon:
            icon: root.status_icon
            theme_text_color: "Custom"
            text_color: root.status_color
            size_hint_x: None
            width: dp(24)

        MDLabel:
            text: root.status
            theme_text_color: "Custom"
            text_color: root.status_color
            font_style: "Caption"

        Widget:

        MDIconButton:
            icon: "swap-horizontal"
            theme_text_color: "Custom"
            text_color: 0.2, 0.5, 0.9, 1
            size_hint_x: None
            width: dp(36)
            on_release: app.quick_toggle_status(root.car_id)

        MDIconButton:
            icon: "history"
            theme_text_color: "Custom"
            text_color: 0.5, 0.5, 0.5, 1
            size_hint_x: None
            width: dp(36)
            on_release: app.show_history(root.car_id)

        MDIconButton:
            icon: "content-copy"
            theme_text_color: "Custom"
            text_color: 0.5, 0.5, 0.5, 1
            size_hint_x: None
            width: dp(36)
            on_release: app.duplicate_car(root.car_id)


<CarListScreen>:
    name: "list"

    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "🚗 Учёт авто"
            md_bg_color: app.theme_cls.primaryColor
            right_action_items: [["plus", lambda x: app.open_add_dialog()], ["chart-bar", lambda x: app.go_stats()], ["download", lambda x: app.export_csv()], ["dots-vertical", lambda x: app.open_main_menu(x)]]

        MDBoxLayout:
            orientation: "horizontal"
            size_hint_y: None
            height: dp(60)
            padding: dp(10)
            spacing: dp(6)

            MDTextField:
                id: search_field
                hint_text: "🔍 Поиск (имя / VIN)"
                mode: "round"
                size_hint_x: 0.55
                on_text: app.apply_filters()

            MDTextField:
                id: status_field
                text: "Все"
                hint_text: "Статус"
                mode: "round"
                readonly: True
                size_hint_x: 0.22
                on_focus: app.open_status_filter(self) if self.focus else None

            MDTextField:
                id: sort_field
                text: "Сначала новые"
                hint_text: "Сорт."
                mode: "round"
                readonly: True
                size_hint_x: 0.23
                on_focus: app.open_sort_menu(self) if self.focus else None

        ScrollView:
            MDBoxLayout:
                id: car_list
                orientation: "vertical"
                spacing: dp(8)
                padding: dp(10)
                size_hint_y: None
                height: self.minimum_height

        MDLabel:
            id: empty_label
            text: "Пока нет записей. Нажмите + чтобы добавить"
            halign: "center"
            theme_text_color: "Secondary"
            size_hint_y: None
            height: dp(50) if not app.cars_count else 0


<StatsScreen>:
    name: "stats"

    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "📊 Статистика"
            md_bg_color: app.theme_cls.primaryColor
            left_action_items: [["arrow-left", lambda x: app.go_list()]]

        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: dp(15)
                spacing: dp(15)
                size_hint_y: None
                height: self.minimum_height

                MDCard:
                    orientation: "vertical"
                    padding: dp(15)
                    spacing: dp(5)
                    radius: [16]
                    elevation: 3
                    size_hint_y: None
                    height: dp(120)
                    md_bg_color: 0.2, 0.5, 0.9, 1
                    MDLabel:
                        text: "Всего автомобилей"
                        theme_text_color: "Custom"
                        text_color: 1,1,1,1
                    MDLabel:
                        text: str(app.stats.get("total", 0))
                        theme_text_color: "Custom"
                        text_color: 1,1,1,1
                        font_style: "H3"
                    MDLabel:
                        text: f"Сумма: {app.fmt_money(app.stats.get('total_sum', 0))}"
                        theme_text_color: "Custom"
                        text_color: 1,1,1,0.9

                MDCard:
                    orientation: "vertical"
                    padding: dp(15)
                    spacing: dp(5)
                    radius: [16]
                    elevation: 3
                    size_hint_y: None
                    height: dp(120)
                    md_bg_color: 1.0, 0.6, 0.0, 1
                    MDLabel:
                        text: "🟠 В ожидании"
                        theme_text_color: "Custom"
                        text_color: 1,1,1,1
                    MDLabel:
                        text: str(app.stats.get("pending", 0))
                        theme_text_color: "Custom"
                        text_color: 1,1,1,1
                        font_style: "H3"
                    MDLabel:
                        text: f"Сумма: {app.fmt_money(app.stats.get('pending_sum', 0))}"
                        theme_text_color: "Custom"
                        text_color: 1,1,1,0.9

                MDCard:
                    orientation: "vertical"
                    padding: dp(15)
                    spacing: dp(5)
                    radius: [16]
                    elevation: 3
                    size_hint_y: None
                    height: dp(120)
                    md_bg_color: 0.2, 0.7, 0.3, 1
                    MDLabel:
                        text: "🟢 Выполнено"
                        theme_text_color: "Custom"
                        text_color: 1,1,1,1
                    MDLabel:
                        text: str(app.stats.get("done", 0))
                        theme_text_color: "Custom"
                        text_color: 1,1,1,1
                        font_style: "H3"
                    MDLabel:
                        text: f"Сумма: {app.fmt_money(app.stats.get('done_sum', 0))}"
                        theme_text_color: "Custom"
                        text_color: 1,1,1,0.9

                MDCard:
                    orientation: "vertical"
                    padding: dp(15)
                    spacing: dp(5)
                    radius: [16]
                    elevation: 2
                    size_hint_y: None
                    height: dp(110)
                    md_bg_color: 0.95, 0.95, 0.95, 1
                    MDLabel:
                        text: "📅 Ближайший срок"
                        theme_text_color: "Primary"
                    MDLabel:
                        id: nearest_label
                        text: app.nearest_text()
                        theme_text_color: "Secondary"

                MDRaisedButton:
                    text: "СБРОСИТЬ ФИЛЬТРЫ"
                    pos_hint: {"center_x": .5}
                    on_release: app.reset_filters()

MDScreenManager:
    CarListScreen:
    StatsScreen:
'''

class CarItem(MDCard):
    car_id = NumericProperty(0)
    car_name = StringProperty("")
    price = StringProperty("")
    date = StringProperty("")
    status = StringProperty("")
    note = StringProperty("")
    vin = StringProperty("")
    category = StringProperty("")
    photo = StringProperty("")
    icon_name = StringProperty("clock-outline")
    status_color = StringProperty("orange")
    status_icon = StringProperty("clock-outline")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.status_color = STATUS_COLORS.get(self.status, [1.0, 0.6, 0.0, 1])
        self.status_icon = STATUS_ICONS.get(self.status, "clock-outline")
        if self.photo and not os.path.exists(self.photo):
            self.photo = ""

class CarListScreen(MDScreen): pass
class StatsScreen(MDScreen): pass

class CarApp(MDApp):
    dialog = None; menu = None; filter_menu = None; sort_menu = None; category_menu = None
    editing_id = None; cars_count = 0; selected_status = STATUS_PENDING; selected_category = ""; photo_path = ""; stats = {}; dark_mode = False

    def build(self):
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        db.init_db()
        return Builder.load_string(KV)

    def on_start(self):
        self.refresh_list()

    def fmt_money(self, val):
        try: return f"{val:,.0f}".replace(",", " ") + " ₽"
        except: return "0 ₽"

    def nearest_text(self):
        n = self.stats.get("nearest")
        if not n: return "Нет ближайших задач"
        name, date = n
        try:
            d = datetime.strptime(date, "%Y-%m-%d").date()
            days = (d - datetime.now().date()).days
            suffix = "сегодня" if days == 0 else "завтра" if days == 1 else f"через {days} дн."
            return f"{name}\n{date}  ({suffix})"
        except: return f"{name}\n{date}"

    def refresh_list(self):
        screen = self.root.get_screen("list")
        screen.ids.car_list.clear_widgets()
        search = screen.ids.search_field.text
        status = screen.ids.status_field.text
        sort_label = screen.ids.sort_field.text
        sort_key = "new"
        for k, v in SORT_OPTIONS.items():
            if v == sort_label: sort_key = k; break
        cars = db.get_cars(search, status, self.selected_category, sort_key)
        self.cars_count = len(cars)
        screen.ids.empty_label.height = dp(50) if not cars else 0
        for row in cars:
            car_id, name, price, date, st, note, vin, cat, photo = row
            item = CarItem(car_id=car_id, car_name=name, price=f"{price:,.0f}".replace(",", " "), date=date, status=st, note=note or "", vin=vin or "", category=cat or "", photo=photo or "")
            screen.ids.car_list.add_widget(item)

    def apply_filters(self): self.refresh_list()

    def reset_filters(self):
        self.selected_category = ""
        screen = self.root.get_screen("list")
        screen.ids.search_field.text = ""
        screen.ids.status_field.text = "Все"
        screen.ids.sort_field.text = "Сначала новые"
        self.refresh_list()

    def open_add_dialog(self):
        self.editing_id = None; self.photo_path = ""; self.selected_status = STATUS_PENDING; self.selected_category = ""
        self._build_form("Новый автомобиль", "", "", "", STATUS_PENDING, "", "", "", "")

    def open_edit_dialog(self, car_id):
        row = db.get_car(car_id)
        if not row: return
        self.editing_id = car_id
        _, name, price, date, status, note, vin, cat, photo = row
        self.photo_path = photo or ""
        self.selected_status = status if status in STATUSES else STATUS_PENDING
        self.selected_category = cat or ""
        self._build_form("Редактировать", name, str(price), date, self.selected_status, note, vin, cat, photo)

    def _build_form(self, title, name, price, date, status, note, vin, cat, photo):
        self.field_name = MDTextField(hint_text="Название *", text=name)
        self.field_price = MDTextField(hint_text="Цена (₽) *", text=price, input_filter="float")
        self.field_date = MDTextField(hint_text="Дата *", text=date, readonly=True)
        self.field_date.bind(focus=self.on_date_focus)
        self.field_note = MDTextField(hint_text="Комментарий", text=note)
        self.field_vin = MDTextField(hint_text="VIN / госномер", text=vin)
        self.field_cat = MDTextField(hint_text="Категория", text=cat, readonly=True)
        self.field_cat.bind(focus=self.on_category_focus)

        self.btn_p = MDRaisedButton(text="В ожидании", on_release=lambda x: self.set_status(STATUS_PENDING))
        self.btn_d = MDRaisedButton(text="Выполнено", on_release=lambda x: self.set_status(STATUS_DONE))
        status_box = MDBoxLayout(orientation="horizontal", spacing="8dp", size_hint_y=None, height="48dp")
        status_box.add_widget(self.btn_p); status_box.add_widget(self.btn_d)
        self._update_status_buttons()

        self.photo_label = MDLabel(text="📷 Фото: " + ("выбрано" if photo else "нет"), size_hint_y=None, height="36dp")
        photo_box = MDBoxLayout(size_hint_y=None, height="48dp", spacing="6dp")
        photo_box.add_widget(self.photo_label)
        photo_box.add_widget(MDRaisedButton(text="ВЫБРАТЬ", on_release=lambda x: self.pick_photo()))
        photo_box.add_widget(MDFlatButton(text="ОЧИСТИТЬ", on_release=lambda x: self.clear_photo()))

        content = MDBoxLayout(orientation="vertical", spacing="10dp", size_hint_y=None, height="460dp", padding="12dp")
        for w in [self.field_name, self.field_price, self.field_date, self.field_vin, self.field_cat, status_box, self.field_note, photo_box]:
            content.add_widget(w)

        btn_text = "ОБНОВИТЬ" if self.editing_id else "ДОБАВИТЬ"
        self.dialog = MDDialog(title=title, type="custom", content_cls=content, buttons=[MDFlatButton(text="ОТМЕНА", on_release=lambda x: self.dialog.dismiss()), MDRaisedButton(text=btn_text, on_release=self.save_car)])
        self.dialog.open()

    def _update_status_buttons(self):
        if self.selected_status == STATUS_PENDING:
            self.btn_p.md_bg_color = [1.0, 0.6, 0.0, 1]; self.btn_p.text_color = [1, 1, 1, 1]
            self.btn_d.md_bg_color = [0.9, 0.9, 0.9, 1]; self.btn_d.text_color = [0.3, 0.3, 0.3, 1]
        else:
            self.btn_d.md_bg_color = [0.2, 0.7, 0.3, 1]; self.btn_d.text_color = [1, 1, 1, 1]
            self.btn_p.md_bg_color = [0.9, 0.9, 0.9, 1]; self.btn_p.text_color = [0.3, 0.3, 0.3, 1]

    def set_status(self, status):
        self.selected_status = status
        self._update_status_buttons()

    def on_date_focus(self, instance, value):
        if value:
            picker = MDDatePicker()
            picker.bind(on_save=self.set_date)
            picker.open()
            instance.focus = False

    def set_date(self, instance, value, date_range):
        self.field_date.text = value.strftime("%Y-%m-%d")

    def on_category_focus(self, instance, value):
        if value:
            cats = list(set(DEFAULT_CATEGORIES) | set(db.get_categories())) + ["Без категории"]
            items = [{"text": c, "viewclass": "OneLineListItem", "on_release": lambda x=c: self.set_category(x)} for c in cats]
            self.category_menu = MDDropdownMenu(caller=instance, items=items, width_mult=5)
            self.category_menu.open()
            instance.focus = False

    def set_category(self, cat):
        if cat == "Без категории": cat = ""
        self.selected_category = cat
        self.field_cat.text = cat
        self.category_menu.dismiss()

    def pick_photo(self):
        self._file_chooser = FileChooserListView(path=os.path.expanduser("~"), filters=["*.png", "*.jpg", "*.jpeg"])
        self._file_dialog = MDDialog(title="Выбери фото", type="custom", content_cls=self._file_chooser, size_hint=(0.9, 0.8), buttons=[MDFlatButton(text="ОТМЕНА", on_release=lambda x: self._file_dialog.dismiss()), MDRaisedButton(text="ВЫБРАТЬ", on_release=self._set_photo)])
        self._file_dialog.open()

    def _set_photo(self, *args):
        sel = self._file_chooser.selection
        if sel:
            src = sel[0]
            try:
                dst_dir = os.path.join(self.user_data_dir, "photos")
                os.makedirs(dst_dir, exist_ok=True)
                fname = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{os.path.basename(src)}"
                dst = os.path.join(dst_dir, fname)
                shutil.copy2(src, dst)
                self.photo_path = dst
                self.photo_label.text = "📷 Фото: выбрано"
            except Exception as e: self.show_error(f"Ошибка копирования фото:\n{e}")
        self._file_dialog.dismiss()

    def clear_photo(self):
        self.photo_path = ""
        self.photo_label.text = "📷 Фото: нет"

    def save_car(self, *args):
        name = self.field_name.text.strip(); price_str = self.field_price.text.strip(); date = self.field_date.text.strip()
        status = self.selected_status; note = self.field_note.text.strip(); vin = self.field_vin.text.strip()
        cat = self.selected_category; photo = self.photo_path
        if not name or not price_str or not date:
            self.show_error("Заполните обязательные поля!"); return
        try: price = float(price_str.replace(",", "."))
        except ValueError: self.show_error("Цена должна быть числом!"); return
        if self.editing_id: db.update_car(self.editing_id, name, price, date, status, note, vin, cat, photo)
        else: db.add_car(name, price, date, status, note, vin, cat, photo)
        self.dialog.dismiss(); self.refresh_list()

    def quick_toggle_status(self, car_id):
        new = db.toggle_status(car_id)
        if new:
            self.refresh_list(); toast(f"Статус: {new}")

    def duplicate_car(self, car_id):
        row = db.get_car(car_id)
        if not row: return
        _, name, price, date, status, note, vin, cat, photo = row
        db.add_car(f"{name} (копия)", price, date, STATUS_PENDING, note, vin, cat, photo)
        self.refresh_list(); toast("Дубликат создан")

    def confirm_delete(self, car_id):
        d = MDDialog(text="Удалить эту запись?", buttons=[MDFlatButton(text="НЕТ", on_release=lambda x: d.dismiss()), MDRaisedButton(text="ДА", on_release=lambda x: self._do_delete(d, car_id))])
        d.open()

    def _do_delete(self, dialog, car_id):
        dialog.dismiss(); db.delete_car(car_id); self.refresh_list()

    def open_status_filter(self, field):
        items = [{"text": "Все", "viewclass": "OneLineListItem", "on_release": lambda x="Все": self._set_status_filter(x)}]
        items += [{"text": s, "viewclass": "OneLineListItem", "on_release": lambda x=s: self._set_status_filter(x)} for s in STATUSES]
        self.filter_menu = MDDropdownMenu(caller=field, items=items, width_mult=4)
        self.filter_menu.open(); field.focus = False

    def _set_status_filter(self, status):
        self.root.get_screen("list").ids.status_field.text = status
        self.filter_menu.dismiss(); self.refresh_list()

    def open_sort_menu(self, field):
        items = [{"text": label, "viewclass": "OneLineListItem", "on_release": lambda x=label: self._set_sort(x)} for label in SORT_OPTIONS.values()]
        self.sort_menu = MDDropdownMenu(caller=field, items=items, width_mult=4)
        self.sort_menu.open(); field.focus = False

    def _set_sort(self, label):
        self.root.get_screen("list").ids.sort_field.text = label
        self.sort_menu.dismiss(); self.refresh_list()

    def open_main_menu(self, caller):
        items = [
            {"text": "📊 Статистика", "viewclass": "OneLineListItem", "on_release": lambda: self._menu_action(self.go_stats)},
            {"text": ("🌙 Тёмная тема" if not self.dark_mode else "☀️ Светлая тема"), "viewclass": "OneLineListItem", "on_release": lambda: self._menu_action(self.toggle_theme)},
            {"text": "💾 Резервная копия", "viewclass": "OneLineListItem", "on_release": lambda: self._menu_action(self.backup_db)},
            {"text": "📥 Восстановить", "viewclass": "OneLineListItem", "on_release": lambda: self._menu_action(self.restore_db)},
            {"text": "🕓 История", "viewclass": "OneLineListItem", "on_release": lambda: self._menu_action(self.show_history)},
        ]
        self.menu = MDDropdownMenu(caller=caller, items=items, width_mult=5)
        self.menu.open()

    def _menu_action(self, fn):
        self.menu.dismiss(); fn()

    def go_stats(self):
        self.stats = db.get_stats()
        self.root.current = "stats"

    def go_list(self): self.root.current = "list"

    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.theme_cls.theme_style = "Dark" if self.dark_mode else "Light"
        toast("Тёмная тема" if self.dark_mode else "Светлая тема")

    def show_history(self, car_id=None):
        rows = db.get_history(car_id if car_id else None)
        if not rows: self.show_error("История пуста"); return
        text = "".join([f"• [{ts}] {action}: {details}\n" for action, details, ts in rows[:30]])
        d = MDDialog(title="🕓 История", text=text, buttons=[MDFlatButton(text="OK", on_release=lambda x: d.dismiss())])
        d.open()

    def export_csv(self):
        screen = self.root.get_screen("list")
        sort_key = "new"
        for k, v in SORT_OPTIONS.items():
            if v == screen.ids.sort_field.text: sort_key = k; break
        cars = db.get_cars(screen.ids.search_field.text, screen.ids.status_field.text, self.selected_category, sort_key)
        if not cars: self.show_error("Нечего экспортировать!"); return
        fname = f"cars_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try: path = os.path.join(self.user_data_dir, fname)
        except: path = fname
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["ID", "Название", "Цена", "Дата", "Статус", "VIN", "Категория", "Заметка"])
            for r in cars: w.writerow([r[0], r[1], r[2], r[3], r[4], r[6], r[7], r[5]])
        self.show_ok(f"CSV сохранён:\n{path}")

    def backup_db(self):
        try:
            src = db.DB_NAME; fname = f"cars_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            dst = os.path.join(self.user_data_dir, fname); shutil.copy2(src, dst)
            self.show_ok(f"Копия сохранена:\n{dst}")
        except Exception as e: self.show_error(f"Ошибка: {e}")

    def restore_db(self):
        self._chooser = FileChooserListView(path=os.path.expanduser("~"), filters=["*.db"])
        self._restore_dialog = MDDialog(title="Выбери файл .db", type="custom", content_cls=self._chooser, size_hint=(0.9, 0.8), buttons=[MDFlatButton(text="ОТМЕНА", on_release=lambda x: self._restore_dialog.dismiss()), MDRaisedButton(text="ВОССТАНОВИТЬ", on_release=self._do_restore)])
        self._restore_dialog.open()

    def _do_restore(self, *args):
        sel = self._chooser.selection
        if sel:
            try:
                shutil.copy2(sel[0], db.DB_NAME); db.init_db(); self.refresh_list(); self.show_ok("База восстановлена")
            except Exception as e: self.show_error(f"Ошибка: {e}")
        self._restore_dialog.dismiss()

    def show_error(self, text):
        d = MDDialog(text=text, buttons=[MDFlatButton(text="OK", on_release=lambda x: d.dismiss())])
        d.open()

    def show_ok(self, text):
        d = MDDialog(title="Готово", text=text, buttons=[MDFlatButton(text="OK", on_release=lambda x: d.dismiss())])
        d.open()

if __name__ == "__main__":
    CarApp().run()
