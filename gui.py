import sys
from PySide6 import QtCore, QtWidgets, QtGui
from PySide6.QtCore import Qt
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from model import *

class ValidationError(Exception):
    pass

class SuccessDialog(QDialog):
     def __init__(self):
        super().__init__()

        self.setWindowTitle("Сообщение")

        button = QPushButton("Заново")
        button_ok = QPushButton("Ок")
        self.buttonBox = QDialogButtonBox()
        self.buttonBox.addButton(button_ok, QDialogButtonBox.RejectRole)
        self.buttonBox.addButton(button, QDialogButtonBox.AcceptRole)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        message = QLabel("Моделирование завершено!")
        layout.addWidget(message)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)
        

class ErrorDialog(QDialog):
    def __init__(self, text):
        super().__init__()

        self.setWindowTitle("Ошибка!")

        button = QPushButton("Закрыть")

        self.buttonBox = QDialogButtonBox()
        self.buttonBox.addButton(button, QDialogButtonBox.RejectRole)
        self.buttonBox.rejected.connect(self.reject)

        layout = QVBoxLayout()
        message = QLabel(text)
        layout.addWidget(message)
        layout.addWidget(self.buttonBox)
        self.setLayout(layout)


class Window(QMainWindow):
    def __init__(self):
        super(Window, self).__init__()

        self.model = None

        self.setWindowTitle("Книжный магазин")

        # блок параметров
        algn = Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignCenter
        self.params = QGroupBox("Параметры")
        self.params.setMaximumHeight(500)
        self.params.setMaximumWidth(360)
        params_layout = QGridLayout(self.params)
        self.model_period = QLineEdit()
        self.model_period.setText('10')
        self.model_period.setMaximumWidth(50)
        params_layout.addWidget(QLabel('Период моделирования (в днях)\nmin:10, max:30', alignment=algn), 0, 0,1,3)
        params_layout.addWidget(self.model_period, 0, 3, 1, 2)
        self.step = QSpinBox() 
        self.step.setMinimum(1)
        self.step.setMaximum(3)
        params_layout.addWidget(QLabel('Шаг моделирования (в днях)\nmin:1, max:3',alignment=algn), 1, 0, 1,3)
        params_layout.addWidget(self.step, 1, 3, 1, 2)
        self.markup_percent = QLineEdit()
        self.markup_percent.setText('5')
        self.markup_percent.setMaximumWidth(50)
        params_layout.addWidget(QLabel('Розничная наценка (%)\nmin:0, max:20', alignment=algn), 2, 0,1,3)
        params_layout.addWidget(self.markup_percent, 2, 3, 1, 2)
        self.markup_percent_new = QLineEdit()
        self.markup_percent_new.setText('10')
        self.markup_percent_new.setMaximumWidth(50)
        params_layout.addWidget(QLabel('Розничная наценка на новые книги (%)\nmin:0, max:30',alignment=algn), 3, 0, 1,3)
        params_layout.addWidget(self.markup_percent_new, 3, 3, 1, 2)
        self.markup_new_period = QLineEdit()
        self.markup_new_period.setText('7')
        self.markup_new_period.setMaximumWidth(50)
        params_layout.addWidget(QLabel('Период наценки на новые книги (в днях)\nmin:5, max:15',alignment=algn), 4, 0, 1,3)
        params_layout.addWidget(self.markup_new_period, 4, 3, 1, 2)
        self.book_limit = QSpinBox() 
        self.book_limit.setMinimum(3)
        self.book_limit.setMaximum(5)
        params_layout.addWidget(QLabel('Нижний порог числа экземпляров книг \n в магазине (шт.)\nmin:3, max:5',alignment=algn), 5, 0, 1,3)
        params_layout.addWidget(self.book_limit, 5, 3,1,2)
        params_layout.addWidget(QLabel('Срок доставки книг (в днях)\nmin:1, max:7', alignment=algn), 6, 0)
        self.time_min = QLineEdit()
        self.time_min.setText('3')
        self.time_min.setMaximumWidth(30)
        params_layout.addWidget(QLabel('от', alignment=algn), 6, 1)
        params_layout.addWidget(self.time_min, 6, 2)
        self.time_max = QLineEdit()
        self.time_max.setText('7')
        self.time_max.setMaximumWidth(30)
        params_layout.addWidget(QLabel('до', alignment=algn), 6, 3)
        params_layout.addWidget(self.time_max, 6, 4)
        params_layout.addWidget(QLabel('Коэф-т плотности потока заказов\nmin:0.5, max:3',alignment=algn), 7, 0, 1,3)
        self.order_flow_density = QLineEdit()
        self.order_flow_density.setText('2')
        self.order_flow_density.setMaximumWidth(50)
        params_layout.addWidget(self.order_flow_density, 7, 3,1,2)
        params_layout.addWidget(QLabel('Вероятность новой книги в заказе\nmin:0, max:1',alignment=algn), 8, 0, 1,3)
        self.newbook_chance = QLineEdit()
        self.newbook_chance.setText('0.7')
        self.newbook_chance.setMaximumWidth(50)
        params_layout.addWidget(self.newbook_chance, 8, 3,1,2)
        params_layout.addWidget(QLabel('Число товаров в заказе (шт.)\nmin:1, max:5', alignment=algn), 9, 0)
        self.order_items_min = QLineEdit()
        self.order_items_min.setText('1')
        self.order_items_min.setMaximumWidth(30)
        params_layout.addWidget(QLabel('от', alignment=algn),9, 1)
        params_layout.addWidget(self.order_items_min, 9, 2)
        self.order_items_max = QLineEdit()
        self.order_items_max.setText('3')
        self.order_items_max.setMaximumWidth(30)
        params_layout.addWidget(QLabel('до', alignment=algn), 9, 3)
        params_layout.addWidget(self.order_items_max, 9, 4)
        params_layout.addWidget(QLabel('Число экземпляров товара (шт.)\nmin:1, max:5', alignment=algn), 10, 0)
        self.item_size_min = QLineEdit()
        self.item_size_min.setText('1')
        self.item_size_min.setMaximumWidth(30)
        params_layout.addWidget(QLabel('от', alignment=algn),10, 1)
        params_layout.addWidget(self.item_size_min, 10, 2)
        self.item_size_max = QLineEdit()
        self.item_size_max.setText('2')
        self.item_size_max.setMaximumWidth(30)
        params_layout.addWidget(QLabel('до', alignment=algn), 10, 3)
        params_layout.addWidget(self.item_size_max, 10, 4)
        params_layout.addWidget(QLabel("Ассортимент задается в соотв. вкладке", 
                                       alignment=Qt.AlignmentFlag.AlignCenter), 12,0,1,5)
        self.params.setLayout(params_layout)

        
        layout = QHBoxLayout()

        # параметры + блок кнопок
        layout1 = QVBoxLayout()
        layout1.addWidget(self.params)
        self.button1 = QPushButton('Старт')
        self.button1.setMinimumSize(150,50)
        self.button1.clicked.connect(self.button1_clicked)
        layout1.addWidget(self.button1, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.button2 = QPushButton('Шаг')
        self.button2.setMinimumSize(150,50)
        self.button2.clicked.connect(self.button2_clicked)
        layout1.addWidget(self.button2, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.button3 = QPushButton('В конец')
        self.button3.setMinimumSize(150,50)
        self.button3.clicked.connect(self.button3_clicked)
        layout1.addWidget(self.button3, alignment=Qt.AlignmentFlag.AlignHCenter)
        self.button4 = QPushButton('Выход')
        self.button4.setMinimumSize(150,50)
        self.button4.clicked.connect(self.button4_clicked)
        layout1.addWidget(self.button4, alignment=Qt.AlignmentFlag.AlignHCenter)

        # задание начального ассортимента
        self.assortment = []
        with open("books.json", encoding="UTF-8") as file:
            books_dicts = json.load(file)
        for d in books_dicts:
            book = Book(authors=d["authors"],
                        title=d["title"],
                        publisher=d["publisher"],
                        year=d["year"],
                        is_new=d["is_new"],
                        pages=d["pages"],
                        subject=d["subject"],
                        category=d["category"])
            item = ItemBook(book=book,
                            price=d["price"])
            self.assortment.append(item)
        self.assortment = sorted(self.assortment, key=lambda item:item.get_book().get_author()[0])

        # вкладки с ассортиментом, заказами и заявками
        tabs = QTabWidget()
        tab1 = QScrollArea()
        tab1.setMinimumWidth(430)
        books_form = QFormLayout()
        books_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        self.quantities = []
        self.item_labels = []
        for item in self.assortment:
            q = QLineEdit()
            q.setText(str(random.randint(0, 10)))
            q.setMaximumWidth(50)
            self.quantities.append(q)
            label = QLabel(item.printable_view())
            books_form.addRow(label, q)
            self.item_labels.append(label)
        w = QWidget()
        w.setLayout(books_form)
        tab1.setWidget(w)
        tabs.addTab(tab1, "Ассортимент")
        self.tab2 = QScrollArea()
        tabs.addTab(self.tab2, "Заказы")
        self.tab3 = QScrollArea()
        tabs.addTab(self.tab3, "Заявки")

        # сбор статистики
        stats = QGroupBox("Статистика")
        stats_layout = QVBoxLayout(stats)
        # таблица топ книг
        self.top = QTableWidget()
        self.top.setColumnCount(2)
        self.top.setHorizontalHeaderLabels(["Книга", "Рейтинг спроса"])
        stats_layout.addWidget(QLabel('Топ продаваемых книг'))
        stats_layout.addWidget(self.top)
         # таблица топ книг по темам
        self.topics = QTableWidget()
        self.topics.setColumnCount(2)
        self.topics.setHorizontalHeaderLabels(["Тематика", "Кол-во книг"])
        stats_layout.addWidget(QLabel('Топ продаваемых книг по темам'))
        stats_layout.addWidget(self.topics)
        # данные о работе магазина
        self.income = QLabel()
        stats_layout.addWidget(self.income)
        self.received_orders = QLabel()
        stats_layout.addWidget(self.received_orders)
        self.completed_orders = QLabel()
        stats_layout.addWidget(self.completed_orders)
        self.created_requests = QLabel()
        stats_layout.addWidget(self.created_requests)
        self.completed_requests = QLabel()
        stats_layout.addWidget(self.completed_requests)
        stats.setLayout(stats_layout)

        # главные компонеты окна
        layout.addLayout(layout1)
        layout.addWidget(tabs)
        layout.addWidget(stats)
        
        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

    # кнопка 1: инициализация модели
    def button1_clicked(self):
        try:
            i = 0
            for item in self.assortment:
                q_text = self.quantities[i].text()
                q = int(q_text)
                if q > 0:
                    item.make_available(q)
                elif q < 0:
                    raise ValidationError('Параметры должны быть положительными числами!')
                self.quantities[i].setDisabled(True)
                i += 1
            self.check_params()
            item_size = sorted([int(self.item_size_min.text()), int(self.item_size_max.text())])
            order_items = sorted([int(self.order_items_min.text()), int(self.order_items_max.text())])
            time = sorted([int(self.time_min.text()), int(self.time_max.text())])
            self.model = Experiment(int(self.model_period.text()),
                                    self.step.value(),
                                    (time[0], time[1]),
                                    (order_items[0], order_items[1]),
                                    (item_size[0], item_size[1]),
                                    float(self.newbook_chance.text()),
                                    float(self.markup_percent.text()),
                                    float(self.markup_percent_new.text()),
                                    int(self.markup_new_period.text()),
                                    float(self.order_flow_density.text()),
                                    self.book_limit.value(),
                                    self.assortment)
            self.params.setDisabled(True)
        except ValueError:
            dlg = ErrorDialog("Некорректные параметры!")
            dlg.exec()
        except ValidationError as e:
            dlg = ErrorDialog(str(e))
            dlg.exec()

    # кнопка 2: шаг моделирования
    def button2_clicked(self):
        if self.model is None:
            dlg = ErrorDialog("Модель не запущена!")
            dlg.exec()
        elif self.model.stop():
            dlg = SuccessDialog()
            dlg.exec()
            if dlg.result() == QDialog.Accepted:
                self.setWindowTitle("Книжный магазин")
                self.model = None
                self.params.setEnabled(True)
                for q in self.quantities:
                    q.setEnabled(True)
                    q.clear()
                    q.setText(str(random.randint(0,10)))
        else:
            self.model.update()
            self.update_widgets()

    # кнопка 3: в конец моделирования
    def button3_clicked(self):
        if self.model is None:
            dlg = ErrorDialog("Модель не запущена!")
            dlg.exec()
        else:
            self.model.run()
            self.update_widgets()
            dlg = SuccessDialog()
            dlg.exec()
            if dlg.result() == QDialog.Accepted:
                self.setWindowTitle("Книжный магазин")
                self.model = None
                self.params.setEnabled(True)
                for q in self.quantities:
                    q.setEnabled(True)
                    q.clear()
                    q.setText(str(random.randint(0,10)))

    # кнопка 4: выход
    def button4_clicked(self):
        sys.exit()

     # обновленное отображение ассортимента, заказов и заявок
    def update_widgets(self):
        self.setWindowTitle(f"Книжный магазин - День {self.model.get_cur_day()}")
        # ассортимент
        i = 0
        for item in self.model.get_assortment():
            self.item_labels[i].setText(item.printable_view())
            self.quantities[i].setText(str(item.get_quantity()))
            i += 1
        # заказы
        l1 = QVBoxLayout()
        for order in self.model.get_orders():
            l1.addWidget(QLabel(order.printable_view()))
        w1 = QWidget()
        w1.setLayout(l1)
        # заявки
        self.tab2.setWidget(w1)
        l2 = QVBoxLayout()
        for request in self.model.get_pub_requests():
            l2.addWidget(QLabel(request.printable_view()))
        w2= QWidget()
        w2.setLayout(l2)
        self.tab3.setWidget(w2)
        # статистика
        top_sales, subject_sales, work = self.model.get_stats()
        self.top.clearContents()
        self.top.setRowCount(len(top_sales))
        i = 0
        for book, rating in top_sales:
            self.top.setItem(i, 0, QTableWidgetItem(book.short_print()))
            self.top.setItem(i, 1, QTableWidgetItem(str(rating)))
            i += 1
        self.top.resizeColumnsToContents()
        self.top.resizeRowsToContents()
        self.topics.clearContents()
        self.topics.setRowCount(len(subject_sales))
        i = 0
        for subject, num in subject_sales:
            self.topics.setItem(i, 0, QTableWidgetItem(subject))
            self.topics.setItem(i, 1, QTableWidgetItem(str(num)))
            i += 1
        self.topics.resizeColumnsToContents()
        self.topics.resizeRowsToContents()
        self.income.setText(f"Выручка: {round(work[0], 2)}р.")
        self.received_orders.setText(f"Получено заказов: {work[1]}")
        self.completed_orders.setText(f"Выполнено заказов: {work[2]}")
        self.created_requests.setText(f"Составлено заявок: {work[3]}")
        self.completed_requests.setText(f"Выполнено заявок: {work[4]}")

    # проверка корректности введенных параметров моделирования
    def check_params(self):
        if (int(self.model_period.text()) not in range(5,31)
           or int(self.time_min.text()) not in range(1,8) 
           or int(self.time_max.text()) not in range(1,8) 
           or int(self.order_items_min.text()) not in range(1,6)  
           or int(self.order_items_max.text()) not in range(1,6) 
           or int(self.item_size_min.text()) not in range(1,6) 
           or int(self.item_size_max.text()) not in range(1,6) 
           or float(self.newbook_chance.text()) <= 0 
           or float(self.markup_percent.text()) <= 0 or float(self.markup_percent.text()) > 20
           or float(self.markup_percent_new.text()) <= 0 or float(self.markup_percent_new.text()) > 30
           or int(self.markup_new_period.text()) not in range(5,16)
           or float(self.order_flow_density.text()) < 0.5 or float(self.order_flow_density.text()) > 3):
            raise ValidationError('Нарушены диапазоны значений параметров!')
        if float(self.newbook_chance.text()) > 1:
            raise ValidationError('Вероятность не может быть больше 1!')                    
        if float(self.markup_percent.text()) >= float(self.markup_percent_new.text()):
            raise ValidationError('Наценка на новые книги должна быть больше обычной!')
    

if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    app.setWindowIcon(QtGui.QIcon('logo.png'))

    widget = Window()
    widget.resize(1500, 800)
    widget.show()

    sys.exit(app.exec())