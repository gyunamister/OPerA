def apply(config, pi):
    if pi.order.placement == None:
        return pi.order, "place_order", "po_machine", [pi.order.oid] + [item.oid for item in pi.items]
    elif pi.order.invoice == None:
        return pi.order, "send_invoice", "si_machine", [pi.order.oid]
    elif pi.order.notification == None:
        if pi.order.price >= config["Minimum-Notification-Price"]:
            return pi.order, "send_notification", "sn_machine", [pi.order.oid]
        else:
            return pi.order, "skip_send_notification", None, [pi.order.oid]
    elif any(item.approved == None for item in pi.items):
        for item in pi.items:
            if item.approved == None:
                if item.quantity >= config["Minimum-Approval-Quantity"]:
                    return item, "check_availability_with_approval", "ap_machine", [item.oid]
                else:
                    return item, "check_availability", None, [item.oid]
    elif any(item.picking == None for item in pi.items):
        for item in pi.items:
            if item.picking == None:
                return item, "pick_item", "pi_machine", [item.oid]
    elif pi.order.payment == None:
        return pi.order, "collect_payment", "cp_machine", [pi.order.oid]
    elif pi.route.start == None:
        return pi.route, "start_route", "sr_machine", [pi.route.oid] + [item.oid for item in pi.items]
    elif pi.route.end == None:
        return pi.route, "end_route", "er_machine", [pi.route.oid] + [item.oid for item in pi.items]
    else:
        return None, None, None, None
