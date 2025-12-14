from cos_utils import TencentCOSUploader

# 替换为你的配置
CONFIG = {
    "region": "ap-nanjing",
    "secret_id": "AKID0036B78*******9qPl", 
    "secret_key": "IZhavCLI6********TUOFvS",
    "bucket": "dify-1258720957"
}

uploader = TencentCOSUploader(**CONFIG)

# 测试1: 内存上传 (模拟文本转语音后的数据)
text_data = b"Hello, this is a test upload from memory."
res_mem = uploader.upload_from_memory(text_data, "test_memory.txt")
print("内存上传结果:", res_mem)

# 测试2: 文件上传
with open("test_local.txt", "w") as f:
    f.write("Local file content")
res_file = uploader.upload_from_file("test_local.txt", "folder/test_local_file.txt")
print("文件上传结果:", res_file)