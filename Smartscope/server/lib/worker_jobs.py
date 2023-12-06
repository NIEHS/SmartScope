import subprocess as sub
import shlex
import os
import logging

logger = logging.getLogger(__name__)


def send_to_worker(hostname: str, script: str, \
        arguments: list = [], kw_arguments: dict = dict(), \
        communicate=False, timeout=15):
    cmd = f'{script}'
    for i in arguments:
        cmd += f' {i}'
    for k, v in kw_arguments.items():
        cmd += f' --{k} {v}'

    stdout = sub.PIPE
    stderr = sub.PIPE
    env = None
    if hostname != 'localhost':
        command = f"""ssh {hostname} '{cmd}' """

    else:
        command = cmd
        if not communicate:
            # command = f"bash -i SmartscopeLaunch.sh '{cmd}'"
            stdout = sub.DEVNULL
            stderr = sub.DEVNULL

    logger.info(command)
    # print(os.environ)

    proc = sub.Popen(shlex.split(command), stdout=stdout, stderr=stderr, env=env)
    # print('Command executed')
    if communicate:
        try:
            outs, errs = proc.communicate(timeout=timeout)
        except sub.TimeoutExpired:
            proc.kill()
            outs, errs = proc.communicate()
        logger.info(f'OUTPUT: {outs}\nERRORS: {errs}')
        return outs, errs
