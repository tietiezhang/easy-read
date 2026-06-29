from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProviderConfig(BaseModel):
    """API 服务商配置。

    一个 provider 表示一个 API 服务入口，例如某个 OpenAI-compatible 中转站。
    """

    model_config = ConfigDict(extra="allow")

    type: str
    base_url: str
    api_key_env: str | None = None
    headers: dict[str, str] = Field(default_factory=dict)


class RequestConfig(BaseModel):
    """模型请求控制参数。

    这些参数不直接进入模型请求体，用于控制网络请求、失败重试等行为。
    """

    model_config = ConfigDict(extra="allow")

    timeout: int = 300
    retry: int = 3


class ModelProfileConfig(BaseModel):
    """模型配置档案。

    一个 model_profile 对应某个阶段实际使用的一组模型调用配置。
    """

    model_config = ConfigDict(extra="allow")

    provider: str
    model: str
    endpoint: str = "/chat/completions"
    request: RequestConfig = Field(default_factory=RequestConfig)
    body: dict[str, Any] = Field(default_factory=dict)


class ApiConfig(BaseModel):
    """API 配置文件结构。

    providers 保存 API 服务入口。
    model_profiles 保存不同阶段可引用的模型配置。
    """

    providers: dict[str, ProviderConfig] = Field(default_factory=dict)
    model_profiles: dict[str, ModelProfileConfig] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_model_profile_providers(self) -> "ApiConfig":
        """校验 model_profile 引用的 provider 是否存在。

        Returns:
            ApiConfig: 校验后的 API 配置对象。

        Raises:
            ValueError: 当 model_profile 引用了不存在的 provider 时抛出。
        """
        missing_providers: list[str] = []

        for profile_name, profile in self.model_profiles.items():
            if profile.provider not in self.providers:
                missing_providers.append(f"{profile_name} -> {profile.provider}")

        if missing_providers:
            joined = ", ".join(missing_providers)
            raise ValueError(f"model_profiles 引用了不存在的 provider: {joined}")

        return self


class ProjectConfig(BaseModel):
    """项目流程配置。

    项目配置按阶段组织，具体字段由各阶段读取。
    """

    model_config = ConfigDict(extra="allow")

    raw: dict[str, Any] = Field(default_factory=dict)

    def get_stage_config(self, stage_name: str) -> dict[str, Any]:
        """获取指定阶段的配置。

        Args:
            stage_name: 阶段名称，例如 06 translate。

        Returns:
            dict[str, Any]: 阶段配置；如果不存在，则返回空字典。
        """
        stage_config = self.raw.get(stage_name, {})
        if isinstance(stage_config, dict):
            return stage_config
        return {}
