"""
端口一致性检查脚本 — 确保所有配置文件和文档中引用的端口一致

使用方式：python scripts/check_port_consistency.py
退出码：0=一致，1=发现不一致
"""

import os
import re
import sys

EXPECTED_PORT = "8000"
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CHECK_FILES = [
    "backend/main.py",
    "backend/config.py",
    "backend/.env",
    "backend/.env.example",
    "frontend/vite.config.js",
    "frontend/.env",
    "frontend/.env.example",
    "README.md",
    "docs/部署指南.md",
    "docs/API接口文档.md",
]

def check_port_in_file(filepath: str) -> list[str]:
    issues = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return [f"  无法读取: {e}"]

    # 白名单端口（前端开发服务器等不应被视为不一致）
    WHITELIST_PORTS = ('5173',)

    for match in re.finditer(r'(?:localhost|127\.0\.0\.1|0\.0\.0\.0)[:=](\d{4})', content):
        port = match.group(1)
        if port != EXPECTED_PORT and port not in WHITELIST_PORTS:
            line_num = content[:match.start()].count('\n') + 1
            issues.append(f"  {filepath}:{line_num}  发现端口 {port}（期望 {EXPECTED_PORT}）")

    for match in re.finditer(r'port[=:]\s*(\d{4})', content, re.IGNORECASE):
        port = match.group(1)
        if port != EXPECTED_PORT and port not in WHITELIST_PORTS:
            line_num = content[:match.start()].count('\n') + 1
            issues.append(f"  {filepath}:{line_num}  发现端口配置 {port}（期望 {EXPECTED_PORT}）")

    return issues


def main():
    print(f"端口一致性检查 (期望端口: {EXPECTED_PORT})")
    print("=" * 50)

    all_issues = []
    root = PROJECT_ROOT

    for filepath in CHECK_FILES:
        full_path = os.path.join(root, filepath)
        if os.path.exists(full_path):
            issues = check_port_in_file(full_path)
            all_issues.extend(issues)
        else:
            print(f"  跳过（文件不存在）: {filepath}")

    if all_issues:
        print(f"\n发现 {len(all_issues)} 个不一致的端口引用:\n")
        for issue in all_issues:
            print(issue)
        print(f"\n请修正后重新运行检查。")
        sys.exit(1)
    else:
        print(f"\n[OK] 所有检查文件中的端口引用一致 (端口: {EXPECTED_PORT})")
        sys.exit(0)


if __name__ == "__main__":
    main()
