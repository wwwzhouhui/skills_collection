import os
import logging
from typing import Union, Dict, Any
from qcloud_cos import CosConfig, CosS3Client
from qcloud_cos.cos_exception import CosServiceError

# 配置日志
logger = logging.getLogger('TencentCOS')

class TencentCOSUploader:
    def __init__(self, region: str, secret_id: str, secret_key: str, bucket: str):
        """
        初始化腾讯云COS上传器
        :param region: 地域，例如 'ap-nanjing'
        :param secret_id: 腾讯云 SecretId
        :param secret_key: 腾讯云 SecretKey
        :param bucket: 存储桶名称
        """
        self.region = region
        self.bucket = bucket
        
        # 校验配置是否完整
        if not all([region, secret_id, secret_key, bucket]):
            logger.error("COS configuration incomplete.")
            self.client = None
            return

        try:
            # 1. 初始化配置
            config = CosConfig(
                Region=region, 
                SecretId=secret_id, 
                SecretKey=secret_key, 
                Token=None, 
                Scheme='https'
            )
            # 2. 初始化客户端 (复用连接)
            self.client = CosS3Client(config)
            logger.info(f"COS Client initialized for bucket: {bucket}")
        except Exception as e:
            logger.error(f"Failed to initialize COS client: {e}")
            self.client = None

    def _generate_url(self, key: str) -> str:
        """生成访问链接"""
        return f"https://{self.bucket}.cos.{self.region}.myqcloud.com/{key}"

    def upload_from_memory(self, file_content: bytes, file_name: str) -> Dict[str, Any]:
        """
        从内存(bytes)直接上传到 COS (对应你原代码中的 _upload_to_cos_from_memory)
        :param file_content: 二进制数据
        :param file_name: 目标文件名 (Key)
        """
        if not self.client:
            return {"success": False, "error": "COS client not initialized"}

        try:
            logger.info(f"Uploading memory bytes to COS: {file_name}...")
            response = self.client.put_object(
                Bucket=self.bucket,
                Body=file_content,
                Key=file_name,
                EnableMD5=False
            )
            
            # 检查 ETag 以确认上传成功
            if response and response.get('ETag'):
                url = self._generate_url(file_name)
                return {"success": True, "url": url, "etag": response['ETag']}
            else:
                return {"success": False, "error": f"Upload failed. Response: {response}"}

        except CosServiceError as e:
            return {"success": False, "error": f"COS Service Error: {e.get_error_code()} - {e.get_error_msg()}"}
        except Exception as e:
            return {"success": False, "error": f"Upload Exception: {str(e)}"}

    def upload_from_file(self, local_path: str, target_name: str = None) -> Dict[str, Any]:
        """
        上传本地文件到 COS
        :param local_path: 本地文件路径
        :param target_name: COS中的文件名，不填则使用本地文件名
        """
        if not self.client:
            return {"success": False, "error": "COS client not initialized"}
            
        if not os.path.exists(local_path):
            return {"success": False, "error": f"Local file not found: {local_path}"}

        key = target_name if target_name else os.path.basename(local_path)

        try:
            logger.info(f"Uploading local file {local_path} to COS: {key}...")
            response = self.client.upload_file(
                Bucket=self.bucket,
                LocalFilePath=local_path,
                Key=key,
                EnableMD5=False
            )
            url = self._generate_url(key)
            return {"success": True, "url": url}
            
        except Exception as e:
            return {"success": False, "error": f"Upload Exception: {str(e)}"}