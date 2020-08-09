class Calculator:
    def __init__(self):
        pass

    def get_percentage_change(self, current_price, prev_price):
        return self.get_total_change(current_price, prev_price) / float(prev_price) * 100

    def get_total_change(self, current_price, prev_price):
        return float(current_price) - float(prev_price)

    def get_percentage_by_total(self, total_amount, price):
        return float(total_amount)/float(price)

    def get_amount_by_percentage(self, percentage, total_amount):
        return float(total_amount) * float(percentage)