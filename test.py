from os import putenv
# putenv("HSA_OVERRIDE_GFX_VERSION", "11.0.0") 
import torch

cuda_dev = -1
if torch.cuda.device_count() > 0:
    print([ f"name {torch.cuda.get_device_properties(x).name} total_memory {torch.cuda.get_device_properties(x).total_memory}" for x in range(torch.cuda.device_count()) ])
    arr = [ torch.cuda.get_device_properties(x).total_memory for x in range(torch.cuda.device_count()) ]
    cuda_dev = arr.index(max(arr))
torch.cuda.set_device(cuda_dev)
torch.cuda.empty_cache()
print(f"dev number: {cuda_dev}")

#putenv("ROCR_VISIBLE_DEVICES", "0")
#import torch # the ENV var should precede torch import

