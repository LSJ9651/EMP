"""用户认证路由"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List, Optional
from database import get_db
from models import User, UserPermission
from utils.crypto import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["认证管理"])


def check_password(password: str, stored_hash: str) -> bool:
    """验证密码（bcrypt + SHA256 兼容）"""
    return verify_password(password, stored_hash)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str = None
    role: str = "operator"


@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """用户登录 — 返回用户信息 + 细粒度权限"""
    user = db.query(User).filter(User.username == data.username, User.is_active == True).first()
    if not user or not check_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 获取用户权限
    permissions = _get_user_permission_map(user.id, db)

    return {
        "code": 200,
        "data": {
            "id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "role": user.role,
            "permissions": permissions,  # { "module.feature": true, ... }
        },
        "message": "登录成功",
    }


def _get_user_permission_map(user_id: int, db: Session) -> dict:
    """获取用户权限扁平映射 { module.feature: is_granted }"""
    # admin 角色拥有所有权限
    user = db.query(User).filter(User.id == user_id).first()
    if user and user.role == "admin":
        result = {}
        for mod in PERMISSION_MODULES:
            for feat in mod["features"]:
                result[f"{mod['module']}.{feat['feature']}"] = True
        return result

    records = (
        db.query(UserPermission)
        .filter(UserPermission.user_id == user_id, UserPermission.is_granted == True)
        .all()
    )
    return {f"{r.module}.{r.feature}": True for r in records}


@router.get("/users")
def list_users(db: Session = Depends(get_db)):
    """获取用户列表"""
    users = db.query(User).order_by(User.id).all()
    return {
        "code": 200,
        "data": [
            {"id": u.id, "username": u.username, "display_name": u.display_name,
             "role": u.role, "is_active": u.is_active, "created_at": u.created_at.isoformat() if u.created_at else None}
            for u in users
        ],
        "message": "success",
    }


@router.post("/users")
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    """创建用户"""
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        display_name=data.display_name or data.username,
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"code": 200, "data": {"id": user.id}, "message": "用户创建成功"}


@router.put("/users/{user_id}")
def update_user(user_id: int, data: dict, db: Session = Depends(get_db)):
    """更新用户信息"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    for key in ["display_name", "role", "is_active"]:
        if key in data:
            setattr(user, key, data[key])
    if "password" in data:
        user.password_hash = hash_password(data["password"])
    db.commit()
    return {"code": 200, "message": "用户更新成功"}


# ──── 细粒度权限管理 ────

PERMISSION_MODULES = [
    {"module": "energy_monitoring", "label": "能耗监控", "icon": "Monitor",
     "features": [
         {"feature": "view", "label": "查看", "desc": "查看能耗监控仪表盘及实时数据"},
         {"feature": "export", "label": "导出", "desc": "导出能耗数据报表"},
     ]},
    {"module": "ai_analysis", "label": "AI分析", "icon": "Cpu",
     "features": [
         {"feature": "view", "label": "查看报告", "desc": "查看AI能耗分析报告"},
         {"feature": "execute", "label": "执行分析", "desc": "发起AI能耗分析与诊断"},
     ]},
    {"module": "scheduling", "label": "调度排产", "icon": "Timer",
     "features": [
         {"feature": "view", "label": "查看", "desc": "查看调度排产计划与结果"},
         {"feature": "execute", "label": "执行优化", "desc": "执行AI调度优化"},
         {"feature": "config", "label": "配置规则", "desc": "配置排产参数与调度规则"},
     ]},
    {"module": "reports", "label": "报表中心", "icon": "Document",
     "features": [
         {"feature": "view", "label": "查看报表", "desc": "查看各类能耗报表"},
         {"feature": "export", "label": "导出报表", "desc": "导出报表为Excel/CSV文件"},
         {"feature": "manage", "label": "订阅管理", "desc": "创建、编辑、删除报表订阅"},
     ]},
    {"module": "system", "label": "系统管理", "icon": "Setting",
     "features": [
         {"feature": "config", "label": "系统配置", "desc": "修改系统参数与AI配置"},
         {"feature": "user_manage", "label": "用户管理", "desc": "创建、编辑、删除用户"},
     ]},
    {"module": "knowledge_base", "label": "知识库管理", "icon": "FolderOpened",
     "features": [
         {"feature": "manage", "label": "管理知识库", "desc": "创建、编辑、删除知识库及上传文档"},
     ]},
]


@router.get("/permissions/modules")
def get_permission_modules():
    """获取权限模块与功能点定义"""
    return {"code": 200, "data": PERMISSION_MODULES, "message": "success"}


class PermissionItem(BaseModel):
    module: str
    feature: str
    is_granted: bool = True


class PermissionBatchUpdate(BaseModel):
    permissions: List[PermissionItem]


@router.get("/users/{user_id}/permissions")
def get_user_permissions(user_id: int, db: Session = Depends(get_db)):
    """获取用户细粒度权限列表"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 查询用户所有权限记录
    records = (
        db.query(UserPermission)
        .filter(UserPermission.user_id == user_id)
        .all()
    )
    granted_map = {(r.module, r.feature): r.is_granted for r in records}

    # 构建完整的权限矩阵（含未显式授权的默认值）
    modules = []
    for mod in PERMISSION_MODULES:
        features = []
        for feat in mod["features"]:
            key = (mod["module"], feat["feature"])
            features.append({
                "feature": feat["feature"],
                "label": feat["label"],
                "desc": feat["desc"],
                "is_granted": granted_map.get(key, False),
            })
        modules.append({
            "module": mod["module"],
            "label": mod["label"],
            "icon": mod["icon"],
            "features": features,
        })

    return {
        "code": 200,
        "data": {
            "user_id": user_id,
            "username": user.username,
            "role": user.role,
            "modules": modules,
        },
        "message": "success",
    }


@router.put("/users/{user_id}/permissions")
def update_user_permissions(
    user_id: int,
    body: PermissionBatchUpdate,
    db: Session = Depends(get_db),
):
    """批量更新用户细粒度权限（全量覆盖模式）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 删除旧权限记录
    db.query(UserPermission).filter(UserPermission.user_id == user_id).delete()

    # 插入新权限记录（仅保存 granted=true 的，减少存储）
    for item in body.permissions:
        if item.is_granted:
            perm = UserPermission(
                user_id=user_id,
                module=item.module,
                feature=item.feature,
                is_granted=True,
            )
            db.add(perm)

    db.commit()

    # 立即返回更新后的权限状态
    return get_user_permissions(user_id, db)
