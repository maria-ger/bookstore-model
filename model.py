import random
import numpy as np
import scipy.stats as sps
import json

class Experiment:

    def __init__(self, model_period, step, delivery_time_range, 
                 order_items_range, item_size_range, newbook_chance,
                 markup_percent, markup_percent_new, markup_new_period,
                 order_flow_density, book_limit, assortment):
        # текущий день
        self.cur_day = 0
        # период моделирования в днях
        self.model_period = model_period
        # шаг моделирования в днях
        self.step = step
        # наценка на книги
        self.markup_percent = markup_percent
        # наценка на новые книги
        self.markup_percent_new = markup_percent_new
        # сколько дней книга является новой
        self.markup_new_period = markup_new_period
        # число книг в топе продаж
        self.top_n = 10
        # состояние ассортимента
        self.assortment = assortment
        # установка наценок на новые/нет книги
        for item in self.assortment:
            if item.get_book().check_new():
                item.set_markup(self.markup_percent_new)
            else:
                item.set_markup(self.markup_percent)
        # товаров в заказе от до
        self.order_items_range = order_items_range
        # единиц товара в заказе от до
        self.item_size_range = item_size_range
        # вероятность новой книге в заказе (чаще не новых)
        self.newbook_chance = newbook_chance
        # коэф-т плотности потока заказов
        self.order_flow_density = order_flow_density
        # состояние магазина
        self.store = BookStore(self.assortment, delivery_time_range, book_limit)

    # случайный набор заказов
    def generate_orders(self):
        # плотность потока заказов зависит от разнообразия ассортимента
        orders = []
        diversity = sum(1 if item.is_available() else 0 for item in self.assortment)
        with open("order_data.json", encoding="UTF-8") as file:
            clients = json.load(file)
        for i in range(round(self.order_flow_density * diversity)):
            # выбор данных о заказчике
            client_data = random.choice(clients)
            needed_info = random.randint(0, 2)
            info = []
            if needed_info == 0 or needed_info == 2:
                info.append(client_data["phone_number"])
            if needed_info == 1 or needed_info == 2:
                info.append(client_data["email"])
            book_list = []
            # выбор сколько в заказе новых/нет книг
            gen = sps.binom(n=1,p=self.newbook_chance)
            min_items, max_items = self.order_items_range
            isnew_list = gen.rvs(random.randint(min_items, max_items))
            for isnew in isnew_list:
                # выбор конкретных книг
                book_item = random.choice(list(filter(lambda item: 
                                            item.get_book().check_new() == isnew and
                                            not self.already_ordered(item.get_book(), book_list),
                                            self.assortment)))
                item_size_min, item_size_max = self.item_size_range
                item = ItemBook(book_item.get_book(), 
                                quantity=random.randint(item_size_min, item_size_max))
                book_list.append(item)
            # формирование заказа
            order = Order(client_data["surname"], info, book_list)
            orders.append(order)
        return orders
    
    def get_orders(self):
        return self.store.get_orders()
    
    def get_pub_requests(self):
        return self.store.get_pub_requests()

    # проверка, что книга уже была заказана
    def already_ordered(self, book, book_list):
        for item in book_list:
            if item.get_book() == book:
                return True
        return False

    # до конца эксперимента
    def run(self):
        while self.cur_day < self.model_period:
            self.update()

    # шаг модели (обновление состояния)
    def update(self):
        end = min(self.cur_day + self.step, self.model_period)
        for i in range(self.cur_day, end):
            self.markup_new_period -= 1
            if self.markup_new_period == 0:
                self.store.change_markup(self.markup_percent)
            orders = self.generate_orders()
            self.assortment = self.store.workday(orders)
        self.cur_day = end

    def get_assortment(self):
        return self.assortment
    
    def get_cur_day(self):
        return self.cur_day
    
    def get_stats(self):
        return (self.store.top_sales(self.top_n),
                self.store.subject_sales(),
                self.store.collect_statistics())

    def stop(self):
        return self.cur_day == self.model_period

class BookStore:
    
    def __init__(self, assortment, delivery_time_range, book_limit):
        self.assortment = assortment #list[item]
        self.sales = []
        self.new_orders = []
        self.orders = []
        self.pub_requests = []
        self.delivery_time_range = delivery_time_range
        self.book_limit = book_limit
        # работа магазина: выручка, получено заказов, выполнено заказов, составлено заявок, выполнено заявок
        self.work_stat = [0, 0, 0, 0, 0]

    def workday(self, new_orders):
        self.work_stat[1] += len(new_orders)
        # удаление уже выполненных заказов и заявок
        if self.orders != []:
            self.orders = list(filter(lambda order: not order.get_status(), self.orders))
        if self.pub_requests != []:
            self.pub_requests = list(filter(lambda request: not request.is_ready(), self.pub_requests))
        # проверить, если появились выполненные заявки
        self.check_pub_requests()
        # выполнить оставшиеся с прошлого дня заказы
        for order in self.orders:
            self.process_order(order)
        # выполнить новые заказы
        for order in new_orders:
            self.process_order(order, True)
        # проверка ассортимента -> составление заявок
        self.check_assortment(self.book_limit)
        self.work_stat[2] += len(list(filter(lambda order: order.get_status(), self.orders)))
        self.work_stat[4] += len(list(filter(lambda request: request.is_ready(), self.pub_requests)))
        return self.assortment

    def check_assortment(self, limit):
        # проверка кол-ва экземпляров книг (порог)
        for shop_item in self.assortment:
            in_stock = shop_item.get_quantity()
            # меньше порога -> запрос в изд-во
            if shop_item.is_available() and in_stock < limit:
                extra = max(shop_item.get_rating(), limit - in_stock)
                self.form_pub_request(shop_item.get_book(), extra)
                self.work_stat[3] += 1

    # изменение наценки на книгу
    def change_markup(self, markup):
        for item in self.assortment:
            if item.get_book().check_new():
                item.set_markup(markup)

    # проданные книги заносятся в список
    def sale(self, item, quantity):
        found = False
        for i, sold_item in enumerate(self.sales):
            if sold_item[0] == item.get_book():
                found = True
                self.sales[i] = (sold_item[0], 
                                 sold_item[1] + quantity, 
                                 sold_item[2] + item.cost() * quantity)
                break
        if not found:
            self.sales.append((item.get_book(), quantity, item.cost() * quantity))
        self.work_stat[0] += item.cost() * quantity

    # обработка заказа
    def process_order(self, order, is_new=False):
        # если книга в наличии, то запись о продаже
        # иначе сохранение в спец списке заказов (данные покупателя)
        if is_new:
            self.orders.append(order)
        for order_item in order.get_book_list():
            request = order_item.get_quantity()
            for shop_item in self.assortment:
                # проверка наличия книги в магазине
                if order_item.get_book() == shop_item.get_book() and shop_item.is_available():
                    if is_new:
                        shop_item.increase_rating(request)
                    in_stock = shop_item.get_quantity()
                    can_sale = min(in_stock, request)
                    # уменьшение кол-ва книг в магазине и в заказе
                    shop_item.change_quantity(-can_sale)
                    order_item.change_quantity(-can_sale)
                    if can_sale:
                        self.sale(shop_item, can_sale)
                    # заявки в изд-ва на недостающие книги 
                    rest = request - can_sale
                    if rest:
                        self.form_pub_request(order_item.get_book(), rest)
                    break
                elif order_item.get_book() == shop_item.get_book():
                    if is_new:
                        shop_item.increase_rating(request)
                    # заявки в изд-ва на недостающие книги 
                    self.form_pub_request(order_item.get_book(), request)
                    break
        order.check_status()
    
    # составление заявки в издательство
    def form_pub_request(self, book, quantity):
        found = False
        publisher = book.get_publisher()
        # добавление книги к существующей заявке в это же изд-во
        for request in self.pub_requests:
            if publisher == request.get_publisher() and request.created_today():
                for item in request.get_book_list():
                    if item.get_book() == book:
                        item.change_quantity(quantity)
                        found = True
                        break
                if not found:
                    request.add_book(book, quantity)
                found = True
                break
        # иначе создание новой заявки
        if not found:
            time_min, time_max = self.delivery_time_range
            time = random.randint(time_min, time_max)
            new_request = PublishRequest(publisher, [], time)
            new_request.add_book(book, quantity)
            self.pub_requests.append(new_request)

    # проверка выполненных заявок
    def check_pub_requests(self):
        for request in self.pub_requests:
            request.update_time()
            request.update_status()
            if request.is_ready():
                self.fulfil_pub_request(request)

    # выполнение заявки в изд-во
    # пополнение ассортимента
    def fulfil_pub_request(self, request):
        for item in request.get_book_list():
            for shop_item in self.assortment:
                if item.get_book() == shop_item.get_book():
                    quantity = item.get_quantity()
                    if shop_item.is_available():
                        shop_item.change_quantity(quantity)
                    else:
                        shop_item.make_available(quantity)
                    break

    def get_orders(self):
        return self.orders

    def get_pub_requests(self):
        return self.pub_requests
    
    # топ книг по рейтингу
    def top_sales(self, n):
        assortment = sorted(self.assortment, key=lambda item: item.get_rating(), reverse=True)
        top = []
        for i in range(n):
            item = assortment[i]
            top.append((item.get_book(), item.get_rating()))
        return top

    # топ проданных книг по тематикам
    def subject_sales(self):
        subjects = []
        for item in self.assortment:
            subjects.append(item.get_book().get_subject())
        subjects = set(subjects)
        subject_sales = []
        for subject in subjects:
            subject_sales.append((subject, 0))
        for book, num, _ in self.sales:
            found = False
            for i in range(len(subject_sales)):
                subject = subject_sales[i][0]
                if subject == book.get_subject():
                    subject_sales[i] = (subject, subject_sales[i][1] + num)
                    found = True
                    break
            if not found:
                subject_sales.append((book.get_subject(), num))
        return sorted(subject_sales, key=lambda sale: sale[1], reverse=True)

    def collect_statistics(self):
        return self.work_stat
    

class Order:

    def __init__(self, surname, info, book_list):
        self.surname = surname
        self.info = info
        self.book_list = book_list
        self.status = False
        self.requested = []
        for item in book_list:
            self.requested.append(item.get_quantity())

    def get_book_list(self):
        return self.book_list

    # проверка статуса готовности заказа
    def check_status(self):
        left_books = 0
        for item in self.book_list:
            left_books += item.get_quantity()
        if not left_books:
            self.status = True
        
    def get_status(self):
        return self.status
    
    def printable_view(self):
        s = "Фамилия: "+self.surname +"\nДанные: "
        for i in self.info:
            s += i + " "
        s += "\nКниги:\n"
        i = 0
        for item in self.book_list:
            book = item.get_book()
            for a in book.get_author():
                s += a + ", "
            s.rstrip(", ")
            s += f" \"{book.get_title()}\": {item.get_quantity()}/{self.requested[i]}\n"
            i += 1
        if self.status:
            s += "Статус: выполнен"
        else: 
            s += "Статус: не выполнен"
        return s


class PublishRequest:

    def __init__(self, publisher, book_list, delivery_time):
        self.publisher = publisher
        self.book_list = book_list
        self.delivery_time = delivery_time
        self.delivery_cntr = delivery_time
        self.status = False
    
    def get_publisher(self):
        return self.publisher
    
    def get_book_list(self):
        return self.book_list
    
    # добавление книги в заявку
    def add_book(self, book, quantity):
        item = ItemBook(book=book, quantity=quantity)
        self.book_list.append(item)
    
    def created_today(self):
        return self.delivery_time == self.delivery_cntr

    # обновление счетчика времени заявки
    def update_time(self):
        self.delivery_cntr -= 1

    # обновление статуса готовности заявки
    def update_status(self):
        if self.delivery_cntr == 0:
            self.status = True

    def is_ready(self):
        return self.status
    
    def printable_view(self):
        s = "Издательство: "+self.publisher +"\nКниги:\n"
        for item in self.book_list:
            book = item.get_book()
            for a in book.get_author():
                s += a + ", "
            s.rstrip(", ")
            s += f" \"{book.get_title()}\": {item.get_quantity()}\n"
        if self.status:
            s += "Статус: выполнена"
        else: 
            s += "Статус: не выполнена"
        return s


class ItemBook:
    
    def __init__(self, book, price=None, retail_markup=None, available=False, quantity=0):
        self.book = book
        self.available = available
        self.quantity = quantity
        self.price = price
        self.retail_markup = retail_markup
        self.demand_rating = 0

    def get_rating(self):
        return self.demand_rating

    def increase_rating(self, q):
        self.demand_rating += q

    def is_available(self):
        return self.available

    def make_available(self, q):
        self.available = True
        self.quantity += q

    def get_quantity(self):
        return self.quantity

    def change_quantity(self, q):
        self.quantity += q

    def set_markup(self, markup):
        self.retail_markup = markup

    def cost(self):
        return round(self.price * (1 + self.retail_markup / 100), 2)

    def get_book(self):
        return self.book
    
    def printable_view(self):
        s = self.book.printable_view()
        if self.retail_markup is None:
            s += f"\n{self.price}р."
        else:
            s += f"\n{self.cost()}р."
        return s
        

class Book:
    
    def __init__(self, authors, is_new=None, title=None, publisher=None, 
                 year=None, pages=None, subject=None, category=None):
        self.authors = authors
        self.title = title
        self.publisher = publisher
        self.year = year
        self.is_new = is_new
        self.pages = pages
        self.subject = subject
        self.category = category

    def __eq__(self, other):
        if (self.authors == other.authors and 
            self.title == other.title and
            self.publisher == other.publisher and
            self.year == other.year):
            return True
        elif (self.authors == other.authors and 
              other.is_new and self.is_new):
            return True

    def get_author(self):
        return self.authors
    
    def get_title(self):
        return self.title
    
    def get_publisher(self):
        return self.publisher
    
    def get_subject(self):
        return self.subject
    
    def check_new(self):
        return self.is_new
    
    def printable_view(self):
        s = ""
        for author in self.authors:
            s += f"{author}, "
        s.rstrip(", ")
        s += f"\n\"{self.title}\"\n{self.publisher},{self.year},{self.pages}стр"
        return s
    
    def short_print(self):
        s = ""
        for author in self.authors:
            s += f"{author}, "
        s.rstrip(", ")
        s += f"\n\"{self.title}\""
        return s