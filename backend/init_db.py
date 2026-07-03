"""数据库初始化脚本 — 建表 + 默认管理员账户

注意：这是 main.py 在 lifespan 启动时导入的模块，用于自动建表和创建管理员。
      更完整的种子数据脚本见 scripts/init_db.py。
"""
from database import engine, get_db_session
from models import Base, User
from utils.crypto import hash_password
from utils.logger import setup_logger

logger = setup_logger("init_db")


def init_database():
    """创建所有表并初始化默认数据"""
    # 建表
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表已创建")

    # 初始化默认管理员
    db = get_db_session()
    try:
        existing = db.query(User).filter(User.username == "admin").first()
        if not existing:
            admin = User(
                username="admin",
                password_hash=hash_password("admin123"),
                display_name="管理员",
                role="admin",
            )
            db.add(admin)
            db.commit()
            logger.info("默认管理员账户已创建 (admin / admin123)")
        else:
            logger.info("管理员账户已存在，跳过")
    finally:
        db.close()
