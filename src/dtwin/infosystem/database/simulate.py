from datetime import datetime
from datetime import date
from copy import deepcopy
from random import randrange, choice
import pandas as pd
from collections import Counter
import random


class shared:
    timestamp = datetime.timestamp(datetime.now())
    # create N orders and deliveries, with 4*N packages
    N = 1
    event_count = 0
    # deliveries hesite
    esito = ["deliver", "undeliver"]


class Simulator(object):
    def __init__(self):
        self.timestamp = datetime.timestamp(datetime.now())
        # create N orders and deliveries, with 4*N packages
        self.N = 1
        self.event_count = 0
        # deliveries hesite
        self.esito = ["deliver", "undeliver"]
        self.order_id = 1
        self.package_id = 1
        self.delivery_id = 1

    # @property
    # def timestamp(self):
    #     return self._timestamp

    # @property
    # def N(self):
    #     return self._N

    # @property
    # def event_count(self):
    #     return self._event_count

    # @property
    # def esito(self):
    #     return self._esito

    def generate_event(self, activity, related_classes):
        self.event_count = self.event_count + 1
        act_duration = 24
        self.timestamp += act_duration

        this_timestamp = datetime.fromtimestamp(self.timestamp)

        base_event = {"event_id": "event_" + str(self.event_count), "event_activity": activity,
                      "event_timestamp": this_timestamp}

        ret = []
        for cl in related_classes.keys():
            for el in related_classes[cl]:
                this_event = deepcopy(base_event)
                if cl == "order":
                    this_event[cl] = "order_" + str(el)
                if cl == "package":
                    this_event[cl] = "package_" + str(el)
                if cl == "delivery":
                    this_event[cl] = "delivery_" + str(el)
                if cl == "back":
                    this_event[cl] = "back_" + str(el)

                ret.append(this_event)

        return ret

    def generate_case(self):
        list_events = []

        for d in range(self.N):

            income = randrange(100, 1000)
            costs = randrange(0, income)
            profit = income - costs

            event = self.generate_event("create", {"order": [self.order_id]})

            for i in range(len(event)):
                event[i]["event_income"] = income
                event[i]["event_costs"] = costs
                event[i]["event_profit"] = profit

            list_events = list_events + event

        i = 0
        while i < self.N:
            list_events = list_events + \
                self.generate_event(
                    "split", {"package": [8*self.order_id, 8*self.order_id + 1, 8*self.order_id + 2, 8*self.order_id + 3], "order": [self.order_id]})
            list_events = list_events + \
                self.generate_event(
                    "split", {"package": [8*self.order_id + 4, 8*self.order_id + 5, 8*self.order_id + 6, 8*self.order_id + 7], "order": [self.order_id+1]})

            i = i + 2

        i = 0
        while i < self.N:
            list_events = list_events + \
                self.generate_event(
                    "load", {"package": [8*self.order_id, 8*self.order_id + 1, 8*self.order_id + 4, 8*self.order_id + 5], "delivery": [self.order_id]})
            list_events = list_events + \
                self.generate_event(
                    "load", {"package": [8*self.order_id + 2, 8*self.order_id + 3, 8*self.order_id + 6, 8*self.order_id + 7], "delivery": [self.order_id+1]})

            i = i + 2

        i = 0
        while i < self.N:
            j = 0
            while True:
                esito = choice(self.esito)
                j = j + 1

                list_events = list_events + \
                    self.generate_event(
                        esito, {"package": [8*self.order_id, 8*self.order_id + 1, 8*self.order_id + 4, 8*self.order_id + 5], "delivery": [self.order_id]})
                list_events = list_events + \
                    self.generate_event(
                        esito, {"package": [8*self.order_id + 2, 8*self.order_id + 3, 8*self.order_id + 6, 8*self.order_id + 7], "delivery": [self.order_id+1]})

                list_events = list_events + self.generate_event("next",
                                                                {
                                                                    "delivery": [self.order_id]})
                list_events = list_events + self.generate_event("next",
                                                                {
                                                                    "delivery": [self.order_id + 1]})

                if not esito == "deliver":
                    r = random.random()
                    if r < 0.5:
                        list_events = list_events + self.generate_event("retry",
                                                                        {"package": [8 * self.order_id, 8 * self.order_id + 1, 8 * self.order_id + 4, 8 * self.order_id + 5],
                                                                         "delivery": [self.order_id]})
                        list_events = list_events + self.generate_event("retry",
                                                                        {"package": [8 * self.order_id + 2, 8 * self.order_id + 3, 8 * self.order_id + 6, 8 * self.order_id + 7],
                                                                         "delivery": [self.order_id + 1]})
                        continue
                    else:
                        list_events = list_events + self.generate_event("return", {"package": [
                            8 * self.order_id, 8 * self.order_id + 1, 8 * self.order_id + 4, 8 * self.order_id + 5, 8*self.order_id + 2, 8*self.order_id + 3, 8*self.order_id + 6, 8*self.order_id + 7]})
                        break
                else:
                    break

            i = i + 2

        for d in range(self.N):

            list_events = list_events + \
                self.generate_event("notify", {"order": [self.order_id]})

        i = 0
        while i < self.N:
            additional_fee = randrange(0, 200)
            event = self.generate_event(
                "bill", {"package": [8*self.order_id, 8*self.order_id + 1, 8*self.order_id + 2, 8*self.order_id + 3], "order": [self.order_id]})
            for j in range(len(event)):
                event[j]["event_add_fee"] = additional_fee
            list_events = list_events + event

            event = self.generate_event(
                "bill", {"package": [8*self.order_id + 4, 8*self.order_id + 5, 8*self.order_id + 6, 8*self.order_id + 7], "order": [self.order_id+1]})
            for j in range(len(event)):
                event[j]["event_add_fee"] = additional_fee
            list_events = list_events + event

            i = i + 2

        i = 0
        while i < self.N:
            list_events = list_events + \
                self.generate_event(
                    "finish", {"package": [8*self.order_id, 8*self.order_id + 1, 8*self.order_id + 4, 8*self.order_id + 5], "delivery": [self.order_id]})
            list_events = list_events + \
                self.generate_event(
                    "finish", {"package": [8*self.order_id + 2, 8*self.order_id + 3, 8*self.order_id + 6, 8*self.order_id + 7], "delivery": [self.order_id+1]})

            i = i + 2

        df = pd.DataFrame(list_events)
        df.type = "exploded"

        return df


# def generate_batch():
#     for i in range(24):
#         case_df = generate_case()


if __name__ == "__main__":
    engine = Simulator()
    engine.order_id = 0
    df = engine.generate_case()
    print(df)
    engine.order_id = 1
    df2 = engine.generate_case()
    print(df2)
