from pydantic import BaseModel
from typing import Optional


class CreateRunRequest(BaseModel):
    seed: Optional[int] = None


class CreateExpeditionRequest(BaseModel):
    seed: Optional[int] = None
    chapters: Optional[int] = None  # 章节数（默认 3，上限见 service.MAX_CHAPTERS）


class AdvanceRequest(BaseModel):
    # 请求级幂等：同一令牌重复/并发提交返回首次响应，不会重复开章
    request_id: Optional[str] = None


class ActRequest(BaseModel):
    action: str
    node: Optional[str] = None
    card: Optional[str] = None
    target: Optional[str] = "enemy"
    option: Optional[int] = None
    growth_node: Optional[str] = None  # forge 动作用：成长树节点 id（2.3.0+）
    branch: Optional[str] = None  # forge 旧字段（兼容旧客户端/日志：等同 growth_node）
    kind: Optional[str] = None    # shop_buy 动作用：货架类别 card/relic
    sku: Optional[str] = None     # shop_buy/commission_accept 动作用：货架项/委托挂单项 id
    commission: Optional[str] = None  # commission_claim 动作用：委托实例 id
    # 并发控制（可选，老客户端不带也完全兼容）：
    request_id: Optional[str] = None   # 客户端生成的请求令牌：同令牌重复提交返回首次结果
    expected_rev: Optional[int] = None  # 所依据视口的存档版本；过期提交 -> 409
