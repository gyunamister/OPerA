from simpy import Resource


class ActivityRepository(object):
    def __init__(self, env, t_inter):
        self.env = env
        self.po_time = 6
        self.ap_time = 6
        self.si_time = 6
        self.pi_time = 3
        self.sn_time = 12
        self.cp_time = 6
        self.sr_time = 3
        self.er_time = 3
        self.po_machine = Resource(env, int(self.po_time/t_inter)+1)
        self.si_machine = Resource(env, int(self.si_time/t_inter)+1)
        # self.sn_machine = Resource(env, int(self.sn_time/t_inter)+1)
        self.sn_machine = Resource(env, int(self.sn_time/(t_inter*2)))
        self.cp_machine = Resource(env, int(self.cp_time/t_inter)+1)
        self.ap_machine = Resource(env, int(self.ap_time/t_inter)+1)
        self.pi_machine = Resource(env, int(self.pi_time/t_inter)+1)
        self.sr_machine = Resource(env, int(self.sr_time/t_inter)+1)
        self.er_machine = Resource(env, int(self.er_time/t_inter)+1)

    def place_order(self, obj):
        request = self.po_machine.request()
        yield request
        yield self.env.timeout(self.po_time)
        obj.placement = True
        self.po_machine.release(request)

    def check_availability_with_approval(self, obj):
        request = self.ap_machine.request()
        yield request
        yield self.env.timeout(self.ap_time)
        obj.approved = True
        self.ap_machine.release(request)

    def check_availability(self, obj):
        yield self.env.timeout(0)
        obj.approved = True

    def send_invoice(self, obj):
        request = self.si_machine.request()
        yield request
        yield self.env.timeout(self.si_time)
        obj.invoice = True
        self.si_machine.release(request)

    def pick_item(self, obj):
        request = self.pi_machine.request()
        yield request
        yield self.env.timeout(self.pi_time)
        obj.picking = True
        self.pi_machine.release(request)

    def send_notification(self, obj):
        request = self.sn_machine.request()
        yield request
        yield self.env.timeout(self.sn_time)
        obj.notification = True
        self.sn_machine.release(request)

    def skip_send_notification(self, obj):
        yield self.env.timeout(0)
        obj.notification = True

    def collect_payment(self, obj):
        request = self.cp_machine.request()
        yield request
        yield self.env.timeout(self.cp_time)
        obj.payment = True
        self.cp_machine.release(request)

    def start_route(self, obj):
        request = self.sr_machine.request()
        yield request
        yield self.env.timeout(self.sr_time)
        obj.start = True
        self.sr_machine.release(request)

    def end_route(self, obj):
        request = self.er_machine.request()
        yield request
        yield self.env.timeout(self.er_time)
        obj.end = True
        self.er_machine.release(request)
