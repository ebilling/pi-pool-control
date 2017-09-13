import syslog
import traceback

def log(msg):
    info(msg)

def crit(msg):
    syslog.syslog(syslog.LOG_CRIT, msg)

def error(msg):
    syslog.syslog(syslog.LOG_ERR, msg)

def warn(msg):
    syslog.syslog(syslog.LOG_WARNING, msg)

def info(msg):
    syslog.syslog(syslog.LOG_INFO, msg)

def debug(msg):
    syslog.syslog(syslog.LOG_DEBUG, msg)

def trace(msg):
    s = "\n"
    tb = traceback.format_list(traceback.extract_stack())
    for line in tb[:len(tb)-3]:
        s += line
    debug(msg + s)

syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_USER)
