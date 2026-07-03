"""设备名称匹配引擎 — 将智能体返回的设备名称与系统设备库匹配

三级匹配策略：
1. 精确匹配：设备名完全一致
2. 同义词匹配：查同义词映射表
3. 模糊匹配：字符串包含 + 编辑距离相似度
"""

import logging
from typing import List, Dict, Optional
from difflib import SequenceMatcher

from sqlalchemy.orm import Session
from models import Device

logger = logging.getLogger(__name__)

# 相似度阈值
AUTO_MATCH_THRESHOLD = 0.85   # 高于此值自动匹配
CANDIDATE_THRESHOLD = 0.6     # 低于此值认为不匹配


class Candidate:
    """匹配候选"""

    def __init__(self, device_id: int, name: str, score: float):
        self.device_id = device_id
        self.name = name
        self.score = score

    def to_dict(self):
        return {"device_id": self.device_id, "name": self.name, "score": self.score}


class MatchResult:
    """设备匹配结果"""

    def __init__(self):
        self.total = 0
        self.matched = {}         # {原始名称: device_id}
        self.fuzzy_matched = {}   # {原始名称: [Candidate]}
        self.unmatched = []       # [名称]
        self.needs_confirmation = False
        self.confirmation_message = None
        self.can_proceed = True

    def to_dict(self):
        return {
            "total": self.total,
            "matched": self.matched,
            "fuzzy_matched": {k: [c.to_dict() for c in v] for k, v in self.fuzzy_matched.items()},
            "unmatched": self.unmatched,
            "needs_confirmation": self.needs_confirmation,
            "confirmation_message": self.confirmation_message,
            "can_proceed": self.can_proceed,
        }


class DeviceMatcher:
    """设备名称匹配引擎"""

    def __init__(self, db_session: Session):
        self.db = db_session
        self._load_device_data()
        self._load_synonyms()

    def _load_device_data(self):
        """从数据库加载设备列表"""
        devices = self.db.query(Device).all()
        self.device_names = [d.name for d in devices]
        self.device_map = {d.name: d.id for d in devices}

    def _load_synonyms(self):
        """从数据库加载同义词映射"""
        try:
            from models import DeviceSynonym
            synonyms = self.db.query(DeviceSynonym).all()
            self.synonym_map = {}
            for syn in synonyms:
                self.synonym_map[syn.synonym] = syn.device_id
        except Exception:
            # DeviceSynonym 表可能尚未创建
            self.synonym_map = {}

    def match(self, device_names: List[str]) -> MatchResult:
        """执行设备名称匹配"""
        result = MatchResult()
        result.total = len(device_names)

        if not device_names:
            result.can_proceed = False
            result.confirmation_message = "未指定要分析的设备。"
            return result

        # 去重
        unique_names = list(dict.fromkeys(device_names))

        for name in unique_names:
            name = name.strip()
            if not name:
                continue

            # 1. 精确匹配
            device_id = self._exact_match(name)
            if device_id:
                result.matched[name] = device_id
                continue

            # 2. 同义词匹配
            device_id = self._synonym_match(name)
            if device_id:
                result.matched[name] = device_id
                logger.info(f"[device_matcher] 同义词匹配: '{name}' → device_id={device_id}")
                continue

            # 3. 模糊匹配
            candidates = self._fuzzy_match(name)
            if candidates:
                if len(candidates) == 1 and candidates[0].score >= AUTO_MATCH_THRESHOLD:
                    # 高相似度单一候选，自动匹配
                    result.matched[name] = candidates[0].device_id
                    logger.info(f"[device_matcher] 自动模糊匹配: '{name}' → '{candidates[0].name}' (score={candidates[0].score})")
                elif len(candidates) == 1:
                    # 单一候选但相似度不够高，仍自动匹配
                    result.matched[name] = candidates[0].device_id
                    result.fuzzy_matched[name] = candidates
                    logger.info(f"[device_matcher] 模糊匹配(低置信度): '{name}' → '{candidates[0].name}' (score={candidates[0].score})")
                else:
                    # 多个候选，需要用户确认
                    result.fuzzy_matched[name] = candidates
                    result.needs_confirmation = True
                    result.can_proceed = False
                    logger.info(f"[device_matcher] 多候选需确认: '{name}' → {[c.name for c in candidates]}")
            else:
                # 未匹配
                result.unmatched.append(name)
                result.can_proceed = False
                logger.info(f"[device_matcher] 未匹配: '{name}'")

        # 生成确认提示
        if result.needs_confirmation:
            result.confirmation_message = self._build_confirmation_message(result)
        elif result.unmatched:
            result.confirmation_message = self._build_unmatched_message(result.unmatched)

        return result

    def _exact_match(self, name: str) -> Optional[int]:
        """精确匹配设备名称"""
        return self.device_map.get(name)

    def _synonym_match(self, name: str) -> Optional[int]:
        """同义词匹配"""
        return self.synonym_map.get(name)

    def _fuzzy_match(self, name: str) -> List[Candidate]:
        """模糊匹配，返回候选列表（按相似度降序）"""
        candidates = []
        for device_name in self.device_names:
            similarity = self._calculate_similarity(name, device_name)
            if similarity >= CANDIDATE_THRESHOLD:
                candidates.append(Candidate(
                    device_id=self.device_map[device_name],
                    name=device_name,
                    score=round(similarity, 2),
                ))

        candidates.sort(key=lambda x: x.score, reverse=True)
        return candidates[:5]

    def _calculate_similarity(self, name1: str, name2: str) -> float:
        """计算两个名称的相似度"""
        n1 = name1.lower().strip()
        n2 = name2.lower().strip()

        if n1 == n2:
            return 1.0

        # 包含匹配（权重较高）
        if n1 in n2 or n2 in n1:
            base_score = 0.8
            # 长度越接近，分数越高
            len_ratio = min(len(n1), len(n2)) / max(len(n1), len(n2))
            return base_score + 0.15 * len_ratio

        # 编辑距离相似度
        return SequenceMatcher(None, n1, n2).ratio()

    def _build_confirmation_message(self, result: MatchResult) -> str:
        """构建设备确认提示信息"""
        messages = []
        for name, candidates in result.fuzzy_matched.items():
            candidate_names = [f"「{c.name}」" for c in candidates]
            messages.append(f"您提到的「{name}」匹配到多个设备：{', '.join(candidate_names)}，请指定具体设备。")
        return "\n".join(messages)

    def _build_unmatched_message(self, unmatched: List[str]) -> str:
        """构建未匹配设备提示信息"""
        names = "、".join([f"「{n}」" for n in unmatched])
        return f"以下设备名称未在系统中找到：{names}，请确认设备名称是否正确。"

    def confirm_selection(self, selections: Dict[str, int]) -> dict:
        """用户确认选择后，将模糊匹配转为精确匹配

        selections: {"原始名称": device_id}
        """
        matched = {}
        for name, device_id in selections.items():
            # 验证 device_id 有效
            from models import Device
            device = self.db.query(Device).filter(Device.id == device_id).first()
            if device:
                matched[name] = device_id
            else:
                logger.warning(f"[device_matcher] 用户选择无效设备ID: {device_id}")
        return matched
