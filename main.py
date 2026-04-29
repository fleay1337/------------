import json
import os
from datetime import datetime
from collections import deque

# ==========================================
# MODEL (Модели данных и бизнес-логика)
# ==========================================

class Transaction:
    def __init__(self, trans_type, amount, description, date_str=None):
        self.trans_type = trans_type  # 'Пополнение', 'Снятие', 'Перевод'
        self.amount = amount
        self.description = description
        self.date = date_str if date_str else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self):
        return {
            "trans_type": self.trans_type,
            "amount": self.amount,
            "description": self.description,
            "date": self.date
        }

    @classmethod
    def from_dict(cls, data):
        return cls(data["trans_type"], data["amount"], data["description"], data["date"])


class TransactionHistoryQueue:
    def __init__(self):
        self.queue = deque()

    def enqueue(self, transaction):
        self.queue.append(transaction)

    def get_all(self):
        return list(self.queue)

    def filter_transactions(self, date=None, trans_type=None):
        filtered = list(self.queue)
        if date:
            filtered = [t for t in filtered if date in t.date]
        if trans_type:
            filtered = [t for t in filtered if t.trans_type.lower() == trans_type.lower()]
        return filtered

    def to_list(self):
        return [t.to_dict() for t in self.queue]

    @classmethod
    def from_list(cls, data_list):
        history = cls()
        for item in data_list:
            history.enqueue(Transaction.from_dict(item))
        return history


class Account:
    def __init__(self, account_id, owner, balance=0.0):
        self.account_id = account_id
        self.owner = owner
        self.balance = balance
        self.history = TransactionHistoryQueue()
        self.account_type = "Base"

    def deposit(self, amount):
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительной.")
        self.balance += amount
        self.history.enqueue(Transaction("Пополнение", amount, "Пополнение счета"))

    def withdraw(self, amount):
        if amount <= 0:
            raise ValueError("Сумма снятия должна быть положительной.")
        if amount > self.balance:
            raise ValueError("Недостаточно средств.")
        self.balance -= amount
        self.history.enqueue(Transaction("Снятие", amount, "Снятие со счета"))

    def get_balance(self):
        return self.balance

    def to_dict(self):
        return {
            "account_id": self.account_id,
            "owner": self.owner,
            "balance": self.balance,
            "account_type": self.account_type,
            "history": self.history.to_list()
        }


class CheckingAccount(Account):
    def __init__(self, account_id, owner, balance=0.0):
        super().__init__(account_id, owner, balance)
        self.account_type = "Checking"


class SavingsAccount(Account):
    def __init__(self, account_id, owner, balance=0.0, interest_rate=0.05):
        super().__init__(account_id, owner, balance)
        self.account_type = "Savings"
        self.interest_rate = interest_rate

    def to_dict(self):
        data = super().to_dict()
        data["interest_rate"] = self.interest_rate
        return data


class CreditAccount(Account):
    def __init__(self, account_id, owner, balance=0.0, credit_limit=1000.0):
        super().__init__(account_id, owner, balance)
        self.account_type = "Credit"
        self.credit_limit = credit_limit

    def withdraw(self, amount):
        if amount <= 0:
            raise ValueError("Сумма снятия должна быть положительной.")
        if self.balance - amount < -self.credit_limit:
            raise ValueError("Превышен кредитный лимит.")
        self.balance -= amount
        self.history.enqueue(Transaction("Снятие", amount, "Снятие кредитных средств"))

    def to_dict(self):
        data = super().to_dict()
        data["credit_limit"] = self.credit_limit
        return data


class BankModel:
    def __init__(self, data_file="bank_data.json"):
        self.accounts = {}
        self.data_file = data_file
        self.load_data()

    def add_account(self, account):
        if account.account_id in self.accounts:
            raise ValueError("Счет с таким ID уже существует.")
        self.accounts[account.account_id] = account
        self.save_data()

    def get_account(self, account_id):
        if account_id not in self.accounts:
            raise ValueError("Счет не найден.")
        return self.accounts[account_id]

    def transfer(self, from_id, to_id, amount):
        if amount <= 0:
            raise ValueError("Сумма перевода должна быть положительной.")
        acc_from = self.get_account(from_id)
        acc_to = self.get_account(to_id)
        
        # Снимаем сначала. Если будет ошибка, пополнения не произойдет
        acc_from.withdraw(amount)
        acc_to.balance += amount
        
        # Записываем транзакции
        acc_from.history.enqueue(Transaction("Перевод", amount, f"На счет {to_id}"))
        acc_to.history.enqueue(Transaction("Перевод", amount, f"Со счета {from_id}"))
        self.save_data()

    def save_data(self):
        data = {acc_id: acc.to_dict() for acc_id, acc in self.accounts.items()}
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def load_data(self):
        if not os.path.exists(self.data_file):
            return
        with open(self.data_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                for acc_id, acc_data in data.items():
                    acc_type = acc_data["account_type"]
                    if acc_type == "Checking":
                        acc = CheckingAccount(acc_id, acc_data["owner"], acc_data["balance"])
                    elif acc_type == "Savings":
                        acc = SavingsAccount(acc_id, acc_data["owner"], acc_data["balance"], acc_data.get("interest_rate", 0.05))
                    elif acc_type == "Credit":
                        acc = CreditAccount(acc_id, acc_data["owner"], acc_data["balance"], acc_data.get("credit_limit", 1000.0))
                    else:
                        continue
                    
                    acc.history = TransactionHistoryQueue.from_list(acc_data["history"])
                    self.accounts[acc_id] = acc
            except json.JSONDecodeError:
                pass


# ==========================================
# VIEW (Пользовательский интерфейс)
# ==========================================

class BankView:
    @staticmethod
    def show_menu():
        print("\n--- Система банковских счетов ---")
        print("1. Создать счет")
        print("2. Пополнить счет")
        print("3. Снять средства")
        print("4. Перевести средства")
        print("5. Проверить баланс")
        print("6. Просмотреть историю транзакций")
        print("0. Выход")
        return input("Выберите опцию: ")

    @staticmethod
    def get_input(prompt):
        return input(prompt)

    @staticmethod
    def show_message(msg):
        print(f"\n[ИНФО] {msg}")

    @staticmethod
    def show_error(msg):
        print(f"\n[ОШИБКА] {msg}")

    @staticmethod
    def show_transactions(transactions):
        if not transactions:
            print("Транзакции не найдены.")
            return
        print("\n--- История транзакций ---")
        for t in transactions:
            print(f"[{t.date}] {t.trans_type}: ${t.amount:.2f} ({t.description})")


# ==========================================
# CONTROLLER (Управление)
# ==========================================

class BankController:
    def __init__(self):
        self.model = BankModel()
        self.view = BankView()

    def run(self):
        while True:
            choice = self.view.show_menu()
            try:
                if choice == '1':
                    self.create_account()
                elif choice == '2':
                    self.perform_deposit()
                elif choice == '3':
                    self.perform_withdrawal()
                elif choice == '4':
                    self.perform_transfer()
                elif choice == '5':
                    self.check_balance()
                elif choice == '6':
                    self.view_history()
                elif choice == '0':
                    self.view.show_message("Выход из системы. До свидания!")
                    break
                else:
                    self.view.show_error("Неверная опция. Попробуйте снова.")
            except ValueError as e:
                self.view.show_error(str(e))
            except Exception as e:
                self.view.show_error(f"Произошла непредвиденная ошибка: {e}")

    def create_account(self):
        acc_type = self.view.get_input("Тип (1-Текущий, 2-Сберегательный, 3-Кредитный): ")
        acc_id = self.view.get_input("ID счета: ")
        owner = self.view.get_input("Имя владельца: ")
        
        if acc_type == '1':
            acc = CheckingAccount(acc_id, owner)
        elif acc_type == '2':
            acc = SavingsAccount(acc_id, owner)
        elif acc_type == '3':
            limit = float(self.view.get_input("Кредитный лимит (по умолчанию 1000): ") or 1000)
            acc = CreditAccount(acc_id, owner, credit_limit=limit)
        else:
            raise ValueError("Неверный тип счета.")
            
        self.model.add_account(acc)
        self.view.show_message(f"Счет {acc_id} успешно создан!")

    def perform_deposit(self):
        acc_id = self.view.get_input("ID счета: ")
        amount = float(self.view.get_input("Сумма для пополнения: "))
        acc = self.model.get_account(acc_id)
        acc.deposit(amount)
        self.model.save_data()
        self.view.show_message("Счет успешно пополнен.")

    def perform_withdrawal(self):
        acc_id = self.view.get_input("ID счета: ")
        amount = float(self.view.get_input("Сумма для снятия: "))
        acc = self.model.get_account(acc_id)
        acc.withdraw(amount)
        self.model.save_data()
        self.view.show_message("Средства успешно сняты.")

    def perform_transfer(self):
        from_id = self.view.get_input("ID счета отправителя: ")
        to_id = self.view.get_input("ID счета получателя: ")
        amount = float(self.view.get_input("Сумма для перевода: "))
        self.model.transfer(from_id, to_id, amount)
        self.view.show_message("Перевод успешно выполнен.")

    def check_balance(self):
        acc_id = self.view.get_input("ID счета: ")
        acc = self.model.get_account(acc_id)
        self.view.show_message(f"Текущий баланс счета {acc_id}: ${acc.get_balance():.2f}")

    def view_history(self):
        acc_id = self.view.get_input("ID счета: ")
        acc = self.model.get_account(acc_id)
        
        filter_date = self.view.get_input("Фильтр по дате (ГГГГ-ММ-ДД) или нажмите Enter для пропуска: ")
        filter_type = self.view.get_input("Фильтр по типу (Пополнение/Снятие/Перевод) или нажмите Enter для пропуска: ")
        
        transactions = acc.history.filter_transactions(
            date=filter_date if filter_date else None,
            trans_type=filter_type if filter_type else None
        )
        self.view.show_transactions(transactions)


if __name__ == "__main__":
    app = BankController()
    app.run()