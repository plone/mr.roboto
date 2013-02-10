from datetime import datetime


def add_log(request, who, message):
    f = open(request.registry.settings['log_file'], 'w+')
    m = who + " " + message + str(datetime.now()) + '\n'
    f.write(m)
    f.close()

