"""
密码加密工具模块
使用 bcrypt 算法进行密码哈希和验证，同时兼容旧版 SHA256 格式
"""
import hashlib
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """对密码进行 bcrypt 哈希处理"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否匹配（bcrypt + SHA256 兼容）"""
    # 先尝试 bcrypt 验证
    try:
        if pwd_context.verify(plain_password, hashed_password):
            return True
    except Exception:
        pass
    # 向后兼容旧版 SHA256 格式（不含 $ 字符且长度为64的 hex 字符串）
    if '$' not in hashed_password and len(hashed_password) == 64:
        sha256_hash = hashlib.sha256(plain_password.encode()).hexdigest()
        return sha256_hash == hashed_password
    return False
