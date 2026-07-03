"""权限控制中间件 — 基于角色的访问控制 + 细粒度权限"""

from fastapi import HTTPException, Depends, Header
from sqlalchemy.orm import Session
from database import get_db
from models import User, UserPermission

# 角色权限矩阵（基础层）
PERMISSIONS = {
    "admin": [
        "execute_workflow", "view_history", "config_ai", "batch_workflow",
        "manage_devices", "manage_tariffs", "manage_alerts", "manage_reports",
    ],
    "dispatcher": [
        "execute_workflow", "view_history", "batch_workflow",
        "manage_devices", "manage_tariffs", "manage_alerts", "manage_reports",
    ],
    "operator": ["execute_workflow", "view_history"],
    "viewer": ["view_history"],
}

# 细粒度权限 action → (module, feature) 映射
ACTION_TO_PERMISSION = {
    "execute_workflow": ("scheduling", "execute"),
    "view_history": ("reports", "view"),
    "config_ai": ("system", "config"),
    "batch_workflow": ("scheduling", "execute"),
    "manage_devices": ("system", "user_manage"),
    "manage_tariffs": ("system", "user_manage"),
    "manage_alerts": ("system", "user_manage"),
    "manage_reports": ("reports", "manage"),
}


def get_current_user_role(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> str:
    """从请求头解析用户角色"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    token = authorization.replace("Bearer ", "")
    # 简化实现：token 格式为 "role:user_id"
    try:
        role, user_id = token.split(":", 1)
        # 验证用户存在
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise HTTPException(status_code=401, detail="用户不存在")
        return role
    except ValueError:
        raise HTTPException(status_code=401, detail="无效的认证令牌")


def get_current_user_id(
    authorization: str = Header(None),
    db: Session = Depends(get_db),
) -> int:
    """获取当前用户ID"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未提供认证令牌")
    token = authorization.replace("Bearer ", "")
    try:
        role, user_id = token.split(":", 1)
        return int(user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="无效的认证令牌")


def check_granular_permission(user_id: int, action: str, db: Session) -> bool:
    """检查用户是否具有指定操作的细粒度权限"""
    mapping = ACTION_TO_PERMISSION.get(action)
    if not mapping:
        return False
    module, feature = mapping
    record = (
        db.query(UserPermission)
        .filter(
            UserPermission.user_id == user_id,
            UserPermission.module == module,
            UserPermission.feature == feature,
            UserPermission.is_granted == True,
        )
        .first()
    )
    return record is not None


def require_permission(action: str):
    """依赖注入工厂：要求当前用户具有指定权限

    检查顺序：
    1. admin 角色 → 直接放行
    2. 角色基础权限 → 检查 PERMISSIONS 矩阵
    3. 细粒度权限 → 检查 user_permissions 表
    """

    def checker(
        role: str = Depends(get_current_user_role),
        db: Session = Depends(get_db),
    ) -> str:
        # admin 角色拥有所有权限
        if role == "admin":
            return role

        # 检查角色基础权限
        allowed = PERMISSIONS.get(role, [])
        if action in allowed:
            return role

        # 检查细粒度权限
        try:
            user_id = get_current_user_id()
            if check_granular_permission(user_id, action, db):
                return role
        except HTTPException:
            pass

        raise HTTPException(
            status_code=403,
            detail=f"权限不足：角色 {role} 不具备 {action} 权限",
        )
    return checker


# 便捷依赖
require_execute = require_permission("execute_workflow")
require_view = require_permission("view_history")
require_admin = require_permission("config_ai")
