import torch

def is_gpu_enabled():
    print('GPU enabled:', torch.cuda.is_available())