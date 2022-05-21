import torch


def is_gpu_enabled():
    print('GPU enabled:', torch.cuda.is_available())


def test_serialem_connection(ip: str, port: int):
    msg = 'Hello from smartscope'
    print(f'Testing connection to SerialEM by printing \"{msg}\" to the SerialEM log.')
    print(f'Using {ip}:{port}')
    import serialem as sem
    sem.ConnectToSEM(port, ip)
    sem.Echo(msg)
    sem.Exit(1)
    print('Finished, please look at the serialEM log for the message.')
