import json


def record_event(file_name, record):
    with open(file_name, 'r+') as file:
        # First we load existing data into a dict.
        file_data = json.load(file)
        # Join new_dat3a with file_data
        file_data["ocel:events"].update(record)
        # Sets file's current position at offset.
        file.seek(0)
        # convert back to json.
        json.dump(file_data, file, indent=4)


def record_object(file_name, info):
    with open(file_name, 'r+') as file:
        # First we load existing data into a dict.
        file_data = json.load(file)
        # Join new_dat3a with file_data
        file_data["ocel:objects"].update(info)
        # Sets file's current position at offset.
        file.seek(0)
        # convert back to json.
        json.dump(file_data, file, indent=4)


def record_process_instance(file_name, pi):
    order_info = pi.order.get_info()
    record_object(file_name, order_info)
    for item in pi.items:
        item_info = item.get_info()
        record_object(file_name, item_info)
    route_info = pi.route.get_info()
    record_object(file_name, route_info)


def append_list_as_row(file_name, list_of_elem):
    # Open file in append mode
    with open(file_name, 'a+', newline='') as write_obj:
        # Create a writer object from csv module
        csv_writer = csv.writer(write_obj)
        # Add contents of list as last row in the csv file
        csv_writer.writerow(list_of_elem)
