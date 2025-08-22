"""Configuration settings for Airdancer using pydantic_settings"""

from urllib.parse import urlparse
from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings


class MQTTConfig(BaseModel):
    """MQTT connection configuration"""

    host: str = "localhost"
    port: int = 1883
    username: str | None = None
    password: str | None = None
    use_tls: bool = False

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    @classmethod
    def from_url(cls, url: str) -> "MQTTConfig":
        """Create MQTTConfig from URL string"""
        parsed = urlparse(url)

        # Set default port and TLS based on scheme
        port = parsed.port
        use_tls = False

        if port is None:
            if parsed.scheme == "mqtts":
                port = 8883
                use_tls = True
            else:
                port = 1883

        # Enable TLS for mqtts:// even if port is explicitly specified
        if parsed.scheme == "mqtts":
            use_tls = True

        return cls(
            host=parsed.hostname or "localhost",
            port=port,
            username=parsed.username,
            password=parsed.password,
            use_tls=use_tls,
        )


class SlackConfig(BaseModel):
    """Slack API configuration"""

    bot_token: str
    app_token: str

    @field_validator("bot_token", "app_token")
    @classmethod
    def validate_tokens(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Token cannot be empty")
        return v.strip()


class AppConfig(BaseSettings):
    """Main application configuration"""

    # Slack configuration
    slack_bot_token: str
    slack_app_token: str

    # Admin configuration
    admin_user: str | None = None

    # Database configuration
    database_path: str = "airdancer.db"

    # Application settings
    debug: bool = False

    # MQTT URL (if provided, will be parsed into mqtt config)
    mqtt_url: str | None = None
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None

    class Config:
        env_prefix: str = "DANCER_"
        case_sensitive: bool = False

    @property
    def slack(self) -> SlackConfig:
        """Get Slack configuration"""
        return SlackConfig(
            bot_token=self.slack_bot_token, app_token=self.slack_app_token
        )

    @property
    def mqtt(self) -> MQTTConfig:
        """Get MQTT configuration"""
        if self.mqtt_url:
            # Parse from URL first, then override with individual settings
            config = MQTTConfig.from_url(self.mqtt_url)

            # Override with individual environment variables if provided
            if self.mqtt_username:
                config.username = self.mqtt_username
            if self.mqtt_password:
                config.password = self.mqtt_password

            return config
        else:
            # Use individual settings
            return MQTTConfig(
                host=self.mqtt_host,
                port=self.mqtt_port,
                username=self.mqtt_username,
                password=self.mqtt_password,
                use_tls=False,  # Only set via URL scheme
            )

    @field_validator("slack_bot_token", "slack_app_token")
    @classmethod
    def validate_slack_tokens(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Slack tokens cannot be empty")
        return v.strip()

    @field_validator("database_path")
    @classmethod
    def validate_database_path(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Database path cannot be empty")
        return v.strip()
