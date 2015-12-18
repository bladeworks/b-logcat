import click
import os
import sys
import re
import thread
from collections import namedtuple, deque
if os.name == 'posix' and sys.version_info[0] < 3:
    import subprocess32 as subprocess
else:
    import subprocess

fields = ("month", "day", "hour", "minute", "second", "ms", "pid", "tid", "level", "tag", "message")
Log = namedtuple('Log', fields)
p_log = re.compile(r'(?P<month>\d{2})-(?P<day>\d{2})\s(?P<hour>\d{2}):(?P<minute>\d{2}):(?P<second>\d{2})\.(?P<ms>\d{3})\s+(?P<pid>\d+)\s+(?P<tid>\d+)\s+(?P<level>\w)\s+(?P<tag>\w+)\s*:\s*(?P<message>.*)')

logs = deque(maxlen=5000)
log_levels = ('F', 'E', 'W', 'I', 'D', 'V')
log_to_int = dict(zip(log_levels, range(6)))
prev_log = None
append_show = True

command_str = None
my_filter = {}
KEY_LEVEL, KEY_GREP, KEY_PID, KEY_TAG = 'level', 'search', 'pid', 'tag'
pid_str = None

is_active = True

@click.command()
@click.option('--android_home', envvar='ANDROID_HOME', type=click.Path(exists=True, dir_okay=True),
        help='Specify the ANDROID_HOME or get from the envs.')
@click.option('--pid', help='Only show the log for the specified application id.')
@click.option('--tag', help='Only show the log with the specified tag.')
def cli(android_home, pid, tag):
    """ A tool to capture android log and filter data easily.

    Available runtime command including (just type the command and press ENTER):

    \b
    F or f: show log with level fatal
    E or e: show log with level error and above
    W or w: show log with level warning and above
    I or i: show log with level info and above
    D or d: show log with level debug and above
    V or v: show log with level verbose and above
    r: reset the filter and show all the logs
    s: show the filter applied
    /xxx: search log with string xxx
    pid=xxx: show log for the specified application with id xxx
    tag=xxx: show log with tag xxx
    """
    check_android_env(android_home)
    global adb
    adb="{}/platform-tools/adb".format(android_home)
    check_connected_devices()
    if pid:
        _pid = get_pid(pid)
        if _pid:
            my_filter[KEY_PID] = _pid
    if tag:
        my_filter[KEY_TAG] = tag
    thread.start_new_thread(show_log, ())
    while is_active:
        global command_str
        global append_show, prev_log
        prev_log = None
        command_str = raw_input()
        if is_active and _init_command():
            clear_and_filter_logs()

def clear_and_filter_logs():
    append_show = False
    click.clear()
    for log in list(logs):
        _echo_line(log)
    append_show = True

def show_log():
    with subprocess.Popen([adb, 'logcat', '-v', 'threadtime'], stdout=subprocess.PIPE, bufsize=1, universal_newlines=True) as proc:
        while proc.poll() is None:
            line = proc.stdout.readline()
            if line:
                _show_line(line.strip())
    global is_active
    is_active = False
    _error("The adb was disconnected. Please press ENTER to exit the app.")

def check_connected_devices():
    output = subprocess.check_output([adb, 'devices'])

def get_pid(application_id):
    output = subprocess.check_output([adb, 'shell', 'ps'])
    p = re.compile(r'\w*\s*(?P<pid>\d+).*{}'.format(application_id))
    r = p.search(output)
    if r and r.group:
        pid = r.group('pid')
        global pid_str
        pid_str = application_id
    else:
        pid = None
    return pid

def check_android_env(android_home):
    if not android_home:
        _error("ANDROID_HOME is not defined. Please use --android_home option.")
        sys.exit(1)
    else:
        _info("ANDROID_HOME is set to {}".format(android_home))

def _error(s):
    click.echo(click.style(s, fg='white', bg='red', bold=True))

def _info(s):
    click.echo(click.style(s, fg='white', bg='blue', bold=True))

level_render = {
    'F': {'fg': 'red', 'bg': 'white'},
    'E': {'fg': 'red', 'bg': 'black'},
    'W': {'fg': 'yellow', 'bg': 'black'},
    'I': {'fg': 'blue', 'bg': 'black'},
    'D': {'fg': 'green', 'bg': 'black'},
    'V': {'fg': 'white', 'bg': 'black'},
}

def _show_line(line):
    search = p_log.search(line)
    if search and search.group:
        g = search.group
        log = Log(*[g(attr) for attr in fields])
        logs.append(log)
        if append_show:
            _echo_line(log)

def _init_command():
    if command_str:
        if command_str.upper() == 'R':
            _info("Reset the filter now.")
            global my_filter
            my_filter = {}
            return True
        if command_str.upper() == 'S':
            if not my_filter:
                _info("No filter applied now.")
            else:
                _info("Filter applied:")
                for k, v in my_filter.iteritems():
                    if k == KEY_PID:
                        _info("{}: {}({})".format(k, pid_str, v))
                    else:
                        _info("{}: {}".format(k, v))
            return False
        if command_str.upper() in log_levels:
            my_filter[KEY_LEVEL] = command_str.upper()
            return True
        if command_str.startswith('pid='):
            pid = get_pid(command_str.partition('=')[2].strip())
            if pid is None:
                _error('The app with {} is not running! Please try to input another filter.'.format(command_str))
                my_filter.pop(KEY_PID, None)
                return False
            my_filter[KEY_PID] = pid
            return True
        if command_str.startswith('/'):
            if len(command_str) > 1:
                my_filter[KEY_GREP] = command_str[1:]
            else:
                my_filter.pop(KEY_GREP, None)
            return True
        if command_str.startswith('tag='):
            tag=command_str.partition('=')[2].strip()
            if tag:
                my_filter[KEY_TAG] = tag
                return True
            return False
    return False

def _filter(log):
    if my_filter:
        if KEY_LEVEL in my_filter:
            if log_to_int[my_filter[KEY_LEVEL]] < log_to_int[log.level]:
                return False
        if KEY_GREP in my_filter:
            if my_filter[KEY_GREP].lower() not in log.message.lower():
                return False
        if KEY_PID in my_filter:
            if log.pid != my_filter[KEY_PID]:
                return False
        if KEY_TAG in my_filter:
            if log.tag.lower() != my_filter[KEY_TAG].lower():
                return False
    return True

def _reformat_log(log):
    return ("{}-{} {}:{}:{}.{} {} {} {} {}:".format(log.month, log.day, log.hour, log.minute, log.second, log.ms, log.pid.rjust(5), log.tid.rjust(5), log.level, log.tag), log.message)

def _echo_line(log):
    if _filter(log):
        global prev_log
        format_log = _reformat_log(log)
        if prev_log and prev_log[0] == format_log[0]:
            msg = click.style("{} {}".format(" "*len(format_log[0]), format_log[1]), **level_render[log.level])
        else:
            msg = click.style("{} {}".format(*format_log), **level_render[log.level])
        click.echo(msg)
        prev_log = format_log
