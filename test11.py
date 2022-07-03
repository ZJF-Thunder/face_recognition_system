import torch
# CUDA_VISIBLE_DEVICES = 1
print(torch.cuda.is_available())   # cuda是否可用
print(torch.version.cuda)  # cuda版本
print(torch.cuda.current_device())   # 返回当前设备索引
print(torch.cuda.device_count())    # 返回GPU的数量
print(torch.cuda.get_device_name(0))   # 返回gpu名字，设备索引默认从0开始

print(torch.__version__)

print(torch.version.cuda)

print(torch.backends.cudnn.version())