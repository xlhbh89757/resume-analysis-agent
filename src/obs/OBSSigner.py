import hmac
import hashlib
import base64
import urllib.parse
import time

class OBSSigner:
    """华为云OBS预签名URL生成工具类"""
    
    def __init__(self, access_key, secret_key, bucket, host=""):
        """
        初始化OBS签名工具
        
        Args:
            access_key (str): 访问密钥ID
            secret_key (str): 秘密访问密钥
            bucket (str): 存储桶名称
            host (str, optional): OBS服务域名，默认自己设置
        """
        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.host = host
        self.endpoint = f"https://{bucket}.{host}"
    
    def _sign_with_hmac_sha1(self, canonical_string):
        """使用HMAC-SHA1算法生成签名"""
        try:
            # 创建HMAC-SHA1密钥
            signing_key = self.secret_key.encode('utf-8')
            
            # 初始化HMAC对象
            hmac_obj = hmac.new(signing_key, canonical_string.encode('utf-8'), hashlib.sha1)
            
            # 计算摘要并转换为Base64
            digest = hmac_obj.digest()
            return base64.b64encode(digest).decode('utf-8')
        except Exception as e:
            # 异常处理可根据需要扩展
            raise Exception(f"签名过程发生错误: {str(e)}")
    
    def _encode_url_string(self, path):
        """
        对URL进行特殊编码处理
        
        先进行标准URL编码，再替换特殊字符：
        '+' -> '%20'
        '%7E' -> '~'
        '*' -> '%2A'
        """
        try:
            # 先进行标准URL编码
            encoded = urllib.parse.quote(path, safe='')
            # 替换特殊字符处理
            return encoded.replace('+', '%20').replace('%7E', '~').replace('*', '%2A')
        except Exception as e:
            raise Exception(f"URL编码失败: {str(e)}")
    
    def _get_expire_timestamp(self, expire_seconds):
        """基于当前时间戳增加指定秒数后返回新时间戳"""
        return int(time.time() + expire_seconds)
    
    def generate_presigned_url(self, object_key, http_method="GET", expire_seconds=3600):
        """
        生成预签名URL
        
        Args:
            object_key (str): 对象键（路径）
            http_method (str, optional): HTTP方法，默认为"GET"
            expire_seconds (int, optional): URL有效期（秒），默认为3600秒
            
        Returns:
            str: 生成的预签名URL
        """
        # 生成过期时间戳
        expire_timestamp = self._get_expire_timestamp(expire_seconds)
        
        # 构建规范字符串
        canonical_string = f"{http_method}\n\n\n{expire_timestamp}\n/{self.bucket}/{object_key}"
        
        # 生成签名并编码
        signature = self._encode_url_string(self._sign_with_hmac_sha1(canonical_string))
        
        # 构建完整URL
        url = (f"{self.endpoint}/{object_key}"
               f"?AccessKeyId={self.access_key}"
               f"&Expires={expire_timestamp}"
               f"&Signature={signature}")
        
        return url    
