"""用户模型 — User, UserPermission"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from .base import Base


class User(Base):
    """用户认证表"""
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment="用户名")
    password_hash = Column(String(200), nullable=False, comment="密码哈希")
    display_name = Column(String(50), comment="显示名称")
    role = Column(String(20), default="operator", comment="角色：admin/scheduler/operator")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    permissions = relationship("UserPermission", back_populates="user", cascade="all, delete-orphan")


class UserPermission(Base):
    """用户细粒度权限表 — 按模块+功能点授权"""
    __tablename__ = "user_permissions"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    module = Column(String(50), nullable=False, comment="模块编码")
    feature = Column(String(50), nullable=False, comment="功能点编码")
    is_granted = Column(Boolean, default=True, comment="是否授权")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="permissions")

    __table_args__ = (
        Index("uq_user_module_feature", "user_id", "module", "feature", unique=True),
    )
